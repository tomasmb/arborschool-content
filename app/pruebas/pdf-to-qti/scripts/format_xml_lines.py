#!/usr/bin/env python3
"""
Format XML files to ensure lines are under 150 characters.

This script formats XML by:
1. Parsing the XML structure
2. Pretty-printing with proper indentation
3. Breaking long attribute lists across multiple lines
4. Breaking simple text content (without nested elements) across lines
5. Shortening very long alt attributes when necessary
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


def shorten_long_alt_text(alt_text: str, max_length: int = 120) -> str:
    """
    Shorten alt text if it's extremely long.
    Keeps the essential information but truncates if necessary.
    """
    if len(alt_text) <= max_length:
        return alt_text

    # Try to keep the first part and add "..."
    break_point = max_length - 10  # Leave room for "..."
    # Try to break at sentence end
    sentence_end = alt_text.rfind('.', 0, break_point)
    if sentence_end > max_length * 0.7:
        return alt_text[:sentence_end + 1] + "..."
    # Otherwise break at word boundary
    word_end = alt_text.rfind(' ', 0, break_point)
    if word_end > max_length * 0.7:
        return alt_text[:word_end] + "..."
    # Last resort: truncate
    return alt_text[:break_point] + "..."


def format_xml_file(filepath: Path, max_line_length: int = 120) -> tuple[bool, int]:
    """
    Format XML file to ensure lines are under max_line_length.
    
    Returns:
        (success, max_line_length_found)
    """
    try:
        # Parse XML
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Shorten very long alt attributes
        for img in root.iter():
            if 'img' in img.tag.lower():
                alt = img.get('alt')
                if alt and len(alt) > max_line_length - 30:
                    shortened = shorten_long_alt_text(alt, max_line_length - 30)
                    img.set('alt', shortened)

        # Format with indentation
        ET.indent(tree, space='  ')

        # Convert to string
        xml_str = ET.tostring(root, encoding='unicode', method='xml')

        # Remove namespace prefixes that ET might add
        xml_str = re.sub(r'xmlns:ns\d+="[^"]*"\s*', '', xml_str)
        xml_str = re.sub(r'<ns\d+:([^>\s]+)', r'<\1', xml_str)
        xml_str = re.sub(r'</ns\d+:([^>\s]+)', r'</\1', xml_str)

        # Process lines to break long ones
        output_lines = []
        for line in xml_str.split('\n'):
            line = line.rstrip()
            if not line.strip():
                continue

            # Break long lines
            if len(line) > max_line_length:
                broken = break_long_line_safe(line, max_line_length)
                output_lines.extend(broken)
            else:
                output_lines.append(line)

        # Write formatted XML
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write('\n'.join(output_lines) + '\n')

        # Verify
        all_lines = ['<?xml version="1.0" encoding="utf-8"?>'] + output_lines
        max_len = max(len(line) for line in all_lines)

        return True, max_len
    except Exception as e:
        print(f"Error formatting {filepath}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False, 0


def break_long_line_safe(line: str, max_length: int) -> list[str]:
    """Break a long XML line safely, preserving XML structure."""
    # Check if it's a tag with attributes (self-closing or opening)
    tag_match = re.match(r'^(\s*)(<[^\s>]+)(.*?)(/?>)$', line)
    if tag_match:
        return break_tag_line(line, max_length)

    # Check if it's simple text content: <tag>text only</tag> (no nested elements)
    # Only break if there are NO nested tags in the text
    text_match = re.match(r'^(\s*)(<([^>]+)>)(.*?)(</\3>)$', line)
    if text_match:
        indent, open_tag, tag_name, text_content, close_tag = text_match.groups()
        text_stripped = text_content.strip()

        # Only break if text has NO nested XML elements
        if '<' not in text_stripped and '>' not in text_stripped:
            # Simple text only - safe to break
            if len(text_stripped) > max_length - len(indent) - len(open_tag) - len(close_tag):
                words = text_stripped.split()
                if len(words) > 1:
                    lines = [indent + open_tag]
                    current = indent + '  '
                    for word in words:
                        test = current + (' ' if current.strip() else '') + word
                        if len(test) > max_length - len(close_tag) - 5 and current.strip():
                            lines.append(current.rstrip())
                            current = indent + '  ' + word
                        else:
                            current = test if current.strip() else indent + '  ' + word
                    lines.append(current + close_tag)
                    return lines

    # For lines with mixed content (text + nested elements), don't break
    # They might be slightly over 150 chars but breaking would corrupt XML
    return [line]


def break_tag_line(line: str, max_length: int) -> list[str]:
    """Break a long XML tag line with attributes into multiple lines."""
    match = re.match(r'^(\s*)(<[^\s>]+)(.*?)(/?>)$', line)
    if not match:
        return [line]

    indent, tag_name, attrs_str, closing = match.groups()
    indent_str = indent
    attr_indent = indent_str + '  '

    # Extract attributes
    attr_pattern = r'(\S+=(?:"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'))'
    attrs = re.findall(attr_pattern, attrs_str)

    if not attrs:
        return [line]

    # If the whole tag fits, return as-is
    if len(line) <= max_length:
        return [line]

    # Break into multiple lines - put each attribute on its own line
    lines = [indent_str + tag_name]
    for attr in attrs:
        lines.append(attr_indent + attr)

    if lines:
        lines[-1] += closing

    return lines


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: format_xml_lines.py <file1.xml> [file2.xml ...]")
        sys.exit(1)

    files = [Path(f) for f in sys.argv[1:]]
    max_line_length = 120  # Aim for ~100, but allow up to 120

    all_good = True
    for filepath in files:
        if not filepath.exists():
            print(f"❌ {filepath}: File not found")
            all_good = False
            continue

        success, max_len = format_xml_file(filepath, max_line_length)
        if success:
            status = "✅" if max_len <= 150 else "⚠️"
            print(f"{status} {filepath}: max={max_len} chars")
            if max_len > 150:
                all_good = False
        else:
            print(f"❌ {filepath}: Failed to format")
            all_good = False

    if all_good:
        print("\n✅ All files comply with 150 character limit!")
        sys.exit(0)
    else:
        print("\n⚠️ Some lines still exceed 150 characters")
        sys.exit(1)


if __name__ == '__main__':
    main()
