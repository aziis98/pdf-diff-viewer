# PDF Visual Diff

![Visual Diff Example](docs/example-1.png)

A high-performance CLI tool designed for precise visual comparison of PDF documents. It automates the process of identifying deletions, insertions, and modifications by analyzing the visual layout rather than just the underlying text stream.

## Key Features

- **Visual Block Segmentation**: Intelligently segments PDF pages into logical content blocks based on background color analysis.
- **Robust Diffing Engine**: Leverages an 8x8 average visual hashing algorithm combined with `difflib.SequenceMatcher` to find optimal alignments between document versions.
- **Optically Correct Layout**: Tracks original document spacing in PDF points (`pt`) to ensure the generated diff maintains the exact visual rhythm and proportions of the source files.
- **Interactive Web Report**:
  - **Dual View Modes**: Switch between a side-by-side **Split View** and a vertically stacked **Unified View**.
  - **Smart Highlights**: Uses semi-transparent overlays (`#f002` / `#0f02`) for a modern, non-obstructive diff visualization.
  - **Side-Aware Page Breaks**: Provides precise markers for page boundaries that adapt based on whether the break occurs in one or both documents.
- **Chromium Integration**: Built-in `--open` flag to quickly render and view reports in Chromium's app mode.

## Quick Run (One-off)

You can run the tool directly from GitHub without cloning or installing:

```bash
uvx --from git+https://github.com/aziis98/pdf-diff-viewer.git pdf-diff-viewer --open <old.pdf> <new.pdf>
```

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable dependency management. You don't need to install packages manually.

```bash
# Sync dependencies and set up the virtual environment
uv sync
```

## Usage

Run the tool using `uv run`:

```bash
uv run python main.py <old.pdf> <new.pdf> -o report.html
```

### Auto-Open Mode

To generate a temporary report and open it immediately in Chromium:

```bash
uv run python main.py --open <old.pdf> <new.pdf>
```

## How It Works

1. **Rasterization**: Pages are rendered at a configurable DPI (default: 150).
2. **Segmentation**: The tool identifies horizontal gaps to slice the document into discrete blocks.
3. **Hashing**: Each block is converted to an 8x8 bitmask representing its visual essence.
4. **Alignment**: The sequences of hashes are compared to find the most logical set of changes.
5. **Generation**: A self-contained HTML file is produced with all assets embedded as Base64 strings.

---

_Developed with a focus on visual fidelity and a professional user experience._
