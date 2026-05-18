#!/usr/bin/env python3
"""
generate_docx.py
Convert pgs_practioner_guide_all_chapters.md to a formatted DOCX using pandoc.

Features:
  - Table of contents (depth 2)
  - Page break before each main section (H1 heading)
  - Centered page numbers in the footer

Requirements:
  - pandoc must be installed (https://pandoc.org/installing.html)
  - python-docx (optional) — used for footer page numbers;
    if not available, a note is printed and the step is skipped

Usage:
  python generate_docx.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

GUIDE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_MD  = os.path.join(GUIDE_DIR, "pgs_practioner_guide_all_chapters.md")
OUTPUT_DOCX = os.path.join(GUIDE_DIR, "pgs_practioner_guide_all_chapters.docx")

# ---------------------------------------------------------------------------
# Lua filter: insert a page break in DOCX before every H1 except the first
# ---------------------------------------------------------------------------
LUA_FILTER = """\
local first_h1 = true

function Header(elem)
  if elem.level == 1 then
    if first_h1 then
      first_h1 = false
      return elem
    end
    local page_break = pandoc.RawBlock(
      'openxml',
      '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
    )
    return {page_break, elem}
  end
end
"""


def check_pandoc():
    path = shutil.which("pandoc")
    if path is None:
        print("ERROR: pandoc not found.")
        print()
        print("Install pandoc before running this script:")
        print("  macOS  : brew install pandoc")
        print("  Ubuntu : sudo apt install pandoc")
        print("  Windows: https://pandoc.org/installing.html")
        sys.exit(1)
    result = subprocess.run(["pandoc", "--version"], capture_output=True, text=True)
    version_line = result.stdout.splitlines()[0] if result.stdout else "unknown"
    print(f"pandoc found: {version_line}")
    return path


def run_pandoc(lua_filter_path):
    cmd = [
        "pandoc",
        INPUT_MD,
        "--from", "markdown-yaml_metadata_block",
        "--to", "docx",
        "--lua-filter", lua_filter_path,
        "--output", OUTPUT_DOCX,
    ]
    print(f"\nRunning: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR: pandoc failed.")
        if result.stderr:
            print(result.stderr)
        sys.exit(1)
    print(f"pandoc succeeded.")
    print(f"  Output: {OUTPUT_DOCX}")


def add_page_numbers(docx_path):
    """Print manual instructions for adding centered page numbers."""
    print("\nPage numbers — add manually in Word or LibreOffice Writer:")
    print("  Word        : Insert → Header & Footer → Page Number → Bottom of Page → Plain Number 2")
    print("  LibreOffice : Insert → Header and Footer → Footer → Default Page Style,")
    print("                then Insert → Field → Page Number (center the footer paragraph)")


def main():
    print("=== generate_docx.py ===\n")

    # 1. Check pandoc
    check_pandoc()

    # 2. Check input file
    if not os.path.isfile(INPUT_MD):
        print(f"ERROR: input file not found: {INPUT_MD}")
        print("Run assemble_all_fragments.sh first.")
        sys.exit(1)

    # 3. Write Lua filter to a temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".lua", delete=False, prefix="pgs_pagebreak_"
    ) as fh:
        fh.write(LUA_FILTER)
        lua_filter_path = fh.name

    try:
        # 4. Run pandoc
        run_pandoc(lua_filter_path)
    finally:
        os.unlink(lua_filter_path)

    # 5. Add page numbers via python-docx (gracefully optional)
    add_page_numbers(OUTPUT_DOCX)

    print(f"\nDone: {OUTPUT_DOCX}")


if __name__ == "__main__":
    main()
