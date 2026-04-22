# PDF Visual Diff - Agent Directives

These are the core rules and project information that all agents MUST follow when working on this repository.

## Operational Rules

- **CRITICAL**: Never use the `browser_subagent` tool. All verification and research must be done via command-line tools or manual reporting.
- **Dependency Management**: Prefer `uv` for all operations. Use `uv sync` to manage environment and `uv run` to execute scripts.
- **Python Stack**: Use `pymupdf` (fitz) for PDF operations and `PIL` (Pillow) + `numpy` for image processing. Using `reportlab` for generation is also supported.
- **Algorithm**:
  1. Rasterize PDF pages at a specific DPI (default: 150).
  2. Segment pages into horizontal blocks by identifying gaps in the background color.
  3. Generate an 8x8 average visual hash for each block.
  4. Use `difflib.SequenceMatcher` to find the optimal alignment between document blocks.

## UI & Output Standards

- **Vertical Flow**: The output is a single-page HTML file with a vertical flow of blocks.
- **Centered Identity**: When blocks are identical (`equal`), display a single centered block spanning the middle two columns of the 4-column grid.
- **Side-by-Side Diff**: When blocks differ (`delete`, `insert`, `replace`), show them side-by-side using the full width of the grid.
- **Aesthetics**:
  - Full-width layout with `width: 100%` and no page margins.
  - Pure white background for the page.
  - No borders around blocks; use **semi-transparent overlays** (`::after`) instead.
  - **Red Tint** (`#f004`) for deleted content.
  - **Green Tint** (`#0f04`) for inserted content.
- **Self-Contained**: All images must be embedded as Base64-encoded strings.

## CLI Interface

Standard usage patterns:

- `uv run python main.py <old.pdf> <new.pdf> -o <report.html>`
- `uv run python main.py <old.pdf> <new.pdf> --open` (Launch in Chromium app mode)
- `uvx --from git+<repo_url> pdf-diff-viewer <old.pdf> <new.pdf>` (One-off remote run)
