import argparse
import base64
import os
import subprocess
import tempfile
import difflib
import io
import fitz
import numpy as np
from PIL import Image


class Block:
    def __init__(self, image, page_num, block_idx, top_padding=0, bottom_padding=0):
        self.image = image
        self.page_num = page_num
        self.block_idx = block_idx
        self.top_padding = top_padding
        self.bottom_padding = bottom_padding
        self.hash = self._compute_hash(image)

    def _compute_hash(self, img):
        # 8x8 average hash
        img = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
        pixels = np.array(img)
        avg = pixels.mean()
        diff = pixels > avg
        return diff.flatten()

    def get_base64(self):
        buffered = io.BytesIO()
        self.image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()


def get_hamming_distance(hash1, hash2):
    return np.count_nonzero(hash1 != hash2)


def get_similarity(hash1, hash2):
    distance = get_hamming_distance(hash1, hash2)
    return 1.0 - (distance / 64.0)


def extract_blocks(pdf_path, dpi=150):
    doc = fitz.open(pdf_path)
    blocks = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        arr = np.array(img)

        # Detect background color
        corners = [arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]]
        bg_color = corners[0]

        is_bg = np.all(arr == bg_color, axis=2)
        rows_is_bg = np.all(is_bg, axis=1)

        # Segmentation settings
        min_gap = 10  # pixels of white space to split blocks
        min_block_height = 5

        page_blocks = []
        last_block_end = 0
        start_row = None
        current_gap = 0

        for r in range(len(rows_is_bg)):
            if not rows_is_bg[r]:
                if start_row is None:
                    start_row = r
                current_gap = 0
            else:
                if start_row is not None:
                    current_gap += 1
                    if current_gap >= min_gap:
                        # End of a block (paragraph)
                        block_height = (r - current_gap + 1) - start_row
                        if block_height >= min_block_height:
                            padding = start_row - last_block_end
                            if page_blocks:
                                page_blocks[-1].bottom_padding = padding

                            block_img = img.crop(
                                (0, start_row, pix.width, r - current_gap + 1)
                            )
                            new_block = Block(
                                block_img, page_num, len(blocks), top_padding=padding
                            )
                            page_blocks.append(new_block)
                            blocks.append(new_block)
                            last_block_end = r - current_gap + 1

                        start_row = None
                        current_gap = 0

        if start_row is not None:
            padding = start_row - last_block_end
            if page_blocks:
                page_blocks[-1].bottom_padding = padding
            block_img = img.crop((0, start_row, pix.width, len(rows_is_bg)))
            new_block = Block(block_img, page_num, len(blocks), top_padding=padding)
            page_blocks.append(new_block)
            blocks.append(new_block)
            last_block_end = len(rows_is_bg)

        # Set final block's bottom padding for the page
        if page_blocks:
            page_blocks[-1].bottom_padding = len(rows_is_bg) - last_block_end

    return blocks


def generate_html(blocks_a, blocks_b, opcodes, output_path, dpi=150):
    # Scale from raster pixels (DPI) to PDF points (72 DPI)
    scale = 72.0 / dpi

    html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>PDF Visual Diff</title>
    <style>
        * {
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: white;
            margin: 0;
            padding: 0;
        }
        header {
            width: 100%;
            height: 60px;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .toggle-container {
            display: flex;
            background: #f1f1f1;
            padding: 4px;
            border-radius: 30px;
            gap: 4px;
        }
        .toggle-btn {
            border: none;
            background: none;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.2s ease;
            color: #666;
        }
        .toggle-btn.active {
            background: white;
            color: #000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .diff-container {
            display: grid;
            grid-template-columns: 1fr 2fr 2fr 1fr;
            width: 100%;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .diff-container.unified {
            grid-template-columns: 1fr 4fr 1fr;
        }
        .row {
            display: contents;
        }
        .block {
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
        }
        .block:hover::after {
            content: "";
            position: absolute;
            inset: 0;
            background-color: #0001;
        }
        .block img {
            max-width: 100%;
            height: auto;
        }
        .margin {
            background: transparent;
        }
        .equal {
            background-color: transparent;
        }
        .delete::after, .replace-old::after {
            content: "";
            position: absolute;
            inset: 0;
            background-color: #f002;
        }
        .delete:hover::after,
        .replace-old:hover::after {
            background-color: #f003;
        }
        .insert::after, .replace-new::after {
            content: "";
            position: absolute;
            inset: 0;
            background-color: #0f02;
        }
        .insert:hover::after,
        .replace-new:hover::after {
            background-color: #0f03;
        }
        .span-2 {
            grid-column: span 2;
        }
        
        .page-break {
            grid-column: 1 / -1;
            position: relative;
            height: 1px;
            background: #ddd;
            margin: 0.25rem 0;
            display: flex;
            align-items: center;
            padding: 0 0.25rem;
        }

        .page-break.unified { 
            justify-content: center;
        }

        .page-break.left { 
            justify-content: start;
        }

        .page-break.right { 
            justify-content: end;
        }

        .page-break-label {
            position: absolute;
            padding: 0.25rem 0.5rem;
            background-color: #fff;
            color: #888;
            font-size: 9px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 2px;
            white-space: nowrap;
            
            border: 1px solid #ddd;
            border-radius: 30px;

            transition: background-color 0.1s ease-in-out;

            z-index: 10;

            &:hover {
                color: #444;
            }
        }
        
        /* Unified View Specifics */
        .diff-container.unified .margin { display: none; }
        .diff-container.unified .block { grid-column: 2; width: 100%; }
        .diff-container.unified .span-2 { grid-column: 2; }
        .diff-container.unified .page-break { grid-column: 2; }
        .diff-container.unified .page-break.left, 
        .diff-container.unified .page-break.right { grid-column: 2; }
    </style>
</head>
<body>
    <header>
        <div class="toggle-container">
            <button class="toggle-btn active" id="btn-split" onclick="setView('split')">Split View</button>
            <button class="toggle-btn" id="btn-unified" onclick="setView('unified')">Unified View</button>
        </div>
    </header>
    <div class="diff-container" id="container">
        {{CONTENT}}
    </div>
    <script>
        function setView(view) {
            const container = document.getElementById('container');
            const btnSplit = document.getElementById('btn-split');
            const btnUnified = document.getElementById('btn-unified');
            
            if (view === 'unified') {
                container.classList.add('unified');
                btnUnified.classList.add('active');
                btnSplit.classList.remove('active');
            } else {
                container.classList.remove('unified');
                btnSplit.classList.add('active');
                btnUnified.classList.remove('active');
            }
        }
    </script>
</body>
</html>
"""
    content = []
    last_page_a = 0
    last_page_b = 0

    def check_page_break(page_a=None, page_b=None):
        nonlocal last_page_a, last_page_b
        res = []
        triggered_a = page_a is not None and page_a > last_page_a
        triggered_b = page_b is not None and page_b > last_page_b

        if triggered_a and triggered_b and page_a == page_b:
            res.append(
                f'<div class="page-break unified"><span class="page-break-label">Page {page_a + 1}</span></div>'
            )
        else:
            if triggered_a:
                res.append(
                    f'<div class="page-break left"><span class="page-break-label">Page {page_a + 1}</span></div>'
                )
            if triggered_b:
                res.append(
                    f'<div class="page-break right"><span class="page-break-label">Page {page_b + 1}</span></div>'
                )

        if triggered_a:
            last_page_a = page_a
        if triggered_b:
            last_page_b = page_b

        return res

    def render_block(block, extra_classes="", pt=None):
        if block is None:
            return '<div class="margin span-2"></div>'

        padding_top_px = pt if pt is not None else block.top_padding
        padding_top_pt = padding_top_px * scale

        return f"""
        <div class="block {extra_classes} span-2" style="padding-top: {padding_top_pt}pt">
          <img src="data:image/png;base64,{block.get_base64()}">
        </div>
        """

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for k in range(i2 - i1):
                block_a, block_b = blocks_a[i1 + k], blocks_b[j1 + k]
                content.extend(check_page_break(block_a.page_num, block_b.page_num))

                pt = min(block_a.top_padding, block_b.top_padding)
                content.append(f"""
                <div class="row">
                  <div class="margin"></div>
                  {render_block(block_a, "equal", pt=pt)}
                  <div class="margin"></div>
                </div>
                """)

        elif tag == "delete":
            for k in range(i1, i2):
                block = blocks_a[k]
                content.extend(check_page_break(page_a=block.page_num))
                content.append(f"""
                <div class="row">
                  {render_block(block, "delete")}
                  <div class="margin span-2"></div>
                </div>
                """)

        elif tag == "insert":
            for k in range(j1, j2):
                block = blocks_b[k]
                content.extend(check_page_break(page_b=block.page_num))
                content.append(f"""
                <div class="row">
                  <div class="margin span-2"></div>
                  {render_block(block, "insert")}
                </div>
                """)

        elif tag == "replace":
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                block_a = blocks_a[i1 + k] if i1 + k < i2 else None
                block_b = blocks_b[j1 + k] if j1 + k < j2 else None

                content.extend(
                    check_page_break(
                        page_a=block_a.page_num if block_a else None,
                        page_b=block_b.page_num if block_b else None,
                    )
                )

                # Use min padding if both blocks exist, otherwise use either
                pt = (
                    min(block_a.top_padding, block_b.top_padding)
                    if (block_a and block_b)
                    else (block_a or block_b).top_padding
                )

                content.append(f"""
                <div class="row">
                  {render_block(block_a, "replace-old", pt=pt)}
                  {render_block(block_b, "replace-new", pt=pt)}
                </div>
                """)
    # Final bottom padding
    if blocks_a and blocks_b:
        pb = min(blocks_a[-1].bottom_padding, blocks_b[-1].bottom_padding)
        content.append(f'<div style="height: {pb * scale}pt"></div>')

    final_html = html_template.replace("{{CONTENT}}", "\n".join(content))
    with open(output_path, "w") as f:
        f.write(final_html)


def main():
    parser = argparse.ArgumentParser(description="Visual PDF Diff Tool")
    parser.add_argument("pdf1", help="Path to the first (old) PDF")
    parser.add_argument("pdf2", help="Path to the second (new) PDF")
    parser.add_argument(
        "-o", "--output", default="diff.html", help="Path to the output HTML file"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the report in Chromium and save to /tmp",
    )
    parser.add_argument("--dpi", type=int, default=150, help="DPI for rasterization")

    args = parser.parse_args()

    print(f"Extracting blocks from {args.pdf1}...")
    blocks_a = extract_blocks(args.pdf1, dpi=args.dpi)
    print(f"Extracting blocks from {args.pdf2}...")
    blocks_b = extract_blocks(args.pdf2, dpi=args.dpi)

    print(f"Comparing {len(blocks_a)} vs {len(blocks_b)} blocks...")
    hashes_a = [b.hash.tobytes() for b in blocks_a]
    hashes_b = [b.hash.tobytes() for b in blocks_b]

    matcher = difflib.SequenceMatcher(None, hashes_a, hashes_b)
    opcodes = matcher.get_opcodes()

    output_path = args.output
    if args.open:
        fd, output_path = tempfile.mkstemp(suffix="-pdf-diff.html")
        os.close(fd)

    print(f"Generating diff report: {output_path}...")
    generate_html(blocks_a, blocks_b, opcodes, output_path, dpi=args.dpi)

    if args.open:
        browsers = [
            "chromium",
            "google-chrome",
        ]
        launched = False
        for b in browsers:
            try:
                subprocess.Popen(
                    [b, f"--app=file://{output_path}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(f"Opening in {b} (app mode)...")
                launched = True
                break
            except FileNotFoundError:
                continue

        if not launched:
            print("No Chromium-based browser found. Opening in default browser...")
            import webbrowser

            webbrowser.open(f"file://{output_path}")

    print("Done!")


if __name__ == "__main__":
    main()
