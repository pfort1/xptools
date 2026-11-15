#!/usr/bin/env python3
"""Normalize a WED earth.wed.xml so re-saves can be compared across runs.

WED stores UI session state inside the document. That state changes every run
even when the scenery is untouched, so it is removed here. Everything else,
including all geometry, properties and the semantic doc prefs, is kept
byte-for-byte (line endings included).

Removed (one rule per volatile field):
  1. <!-- written by WED x.y.z -->        build version; changes on version bumps
  2. <selection> ... </selection>, <selection/>, <sel id="..."/>
                                          current selection (WED_Select)
  3. <pref name="map/...">                map view extent and layer toggles (WEDMap)
  4. <pref name="window/...">             window position, size, splitters (WEDWindows)
  5. <pref name="map_preview_window/..."> 3D preview window camera and geometry
  6. <pref name="PropertyPaneN/...">      property pane open/closed state

Kept on purpose: doc/* (export_target, xml_compatibility) and export/last
(the DSF tiles written by the last export), because they affect or describe output.

Usage:
  python normalize_wed_xml.py earth.wed.xml              > normalized to stdout
  python normalize_wed_xml.py earth.wed.xml -o out.xml   > normalized to a file
"""
import argparse
import re
import sys

DROP_LINE = re.compile(
    rb'^\s*(?:'
    rb'<!-- written by WED [^>]*-->'
    rb'|<selection\s*/>'
    rb'|<sel id="[^"]*"\s*/>'
    rb'|<pref name="(?:map|window|map_preview_window|PropertyPane\d*)/[^"]*"[^>]*/>'
    rb')\s*$'
)
SEL_OPEN = re.compile(rb'^\s*<selection>\s*$')
SEL_CLOSE = re.compile(rb'^\s*</selection>\s*$')


def normalize(data: bytes) -> bytes:
    out = []
    in_selection = False
    for line in data.splitlines(keepends=True):
        if in_selection:
            if SEL_CLOSE.match(line):
                in_selection = False
            continue
        if SEL_OPEN.match(line):
            in_selection = True
            continue
        if DROP_LINE.match(line):
            continue
        out.append(line)
    if in_selection:
        sys.exit("error: unterminated <selection> block")
    return b''.join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('xml', help='path to earth.wed.xml')
    ap.add_argument('-o', '--output', help='write here instead of stdout')
    args = ap.parse_args()
    with open(args.xml, 'rb') as f:
        result = normalize(f.read())
    if args.output:
        with open(args.output, 'wb') as f:
            f.write(result)
    else:
        sys.stdout.buffer.write(result)


if __name__ == '__main__':
    main()
