#!/usr/bin/env bash
# assemble_all_fragments.sh
# Assembles front_matter.md + all chapters + all appendices into
# pgs_practioner_guide_all_chapters.md
#
# Usage: ./assemble_all_fragments.sh

set -euo pipefail

GUIDE_DIR="$(pwd)"
OUTPUT="$GUIDE_DIR/pgs_practioner_guide_all_chapters.md"

echo "Assembling practitioner guide..."
echo "  Source dir : $GUIDE_DIR"
echo "  Output     : $OUTPUT"

{
  # --- Front matter (title page, abstract, dedication) ---
  cat "$GUIDE_DIR/front_matter.md"
  printf '\n\n'

  # --- Table of Contents
  #     H1 heading triggers the Lua filter page break (before this heading).
  #     Raw OpenXML TOC field uses \h so entries are hyperlinks in Word and PDF export.
  #     Open the DOCX in Word and right-click the placeholder to update the field.
  printf '# Table of Contents\n\n'
  printf '```{=openxml}\n'
  printf '<w:p>\n'
  printf '  <w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>\n'
  printf '  <w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r>\n'
  printf '  <w:r><w:fldChar w:fldCharType="separate"/></w:r>\n'
  printf '  <w:r><w:t>Open in Word and right-click here, then select Update Field to generate the Table of Contents.</w:t></w:r>\n'
  printf '  <w:r><w:fldChar w:fldCharType="end"/></w:r>\n'
  printf '</w:p>\n'
  printf '```\n\n'

  # --- Chapter 00: strip the legacy title preamble baked into the file
  #     (everything before the "# Chapter 00" heading is replaced by front_matter)
  awk '/^# Chapter 00/,0' "$GUIDE_DIR/ch00_introduction_and_orientation_v0.md"
  printf '\n\n'

  # --- Chapters 01–18 ---
  for prefix in \
    ch01 ch02 ch03 ch04 ch05 ch06 ch07 ch08 ch09 \
    ch10 ch11 ch12 ch13 ch14 ch15 ch16 ch17 ch18
  do
    file=$(ls "$GUIDE_DIR/${prefix}_"*.md 2>/dev/null | head -1 || true)
    if [[ -z "$file" ]]; then
      echo "WARNING: no file found for prefix '${prefix}'" >&2
      continue
    fi
    cat "$file"
    printf '\n\n'
  done

  # --- Appendices A–D ---
  for prefix in appendix_a appendix_b appendix_c appendix_d; do
    file=$(ls "$GUIDE_DIR/${prefix}_"*.md 2>/dev/null | head -1 || true)
    if [[ -z "$file" ]]; then
      echo "WARNING: no file found for prefix '${prefix}'" >&2
      continue
    fi
    cat "$file"
    printf '\n\n'
  done

} > "$OUTPUT"

LINE_COUNT=$(wc -l < "$OUTPUT")
echo "Done. Lines written: $LINE_COUNT"
echo "  $OUTPUT"
