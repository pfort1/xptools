# Step 0 golden outputs (baseline WED, unmodified)

Produced 2026-11-15 by `vs_build\Release\WED.exe` (WED 2.7.3-r1, built from commit 0137e80cd).
Each fixture was run twice in fresh WED processes from a pristine copy:
Open package → rename and restore one item → Save → Export Scenery Pack.
**Only files that came out byte-identical across both runs from unedited input are kept.**
Hashes are in `SHA256SUMS.txt`.

| Fixture (package) | Export target | Kept |
|---|---|---|
| `test/wgs84` → `zz_WEDtest_wgs84` | 6 = X-Plane 12.00 | apt.dat, validation_report.txt, 5 DSFs |
| `test/dsf_export/uv_mapping.xml` → `zz_WEDtest_dsf_export` | 4 = X-Plane 11.00 | apt.dat, validation_report.txt, 3 DSFs |

## Not kept (pending a clean run 3)
- `wgs84/earth.wed.xml`, `wgs84/.../+71+025.dsf`: run 1 contained accidental edits, so only one clean run exists.
- `dsf_export/earth.wed.xml`, `dsf_export/.../+44-124.dsf`: both runs moved draped-orthophoto vertices 8374/8379.

## Comparing re-saved earth.wed.xml in the future
WED stores UI session state in the document, which differs every run even without edits.
Ignore these lines when diffing:
- `<!-- written by WED x.y.z -->`
- `<selection>` / `<sel id=…/>`
- `<pref name="map/…">` (map view extent) and `<pref name="window/…">` (window position, splitters)

## Version strings (stable per build, change on version bump)
- XML comment (`WED_Document.cpp:806`), apt.dat header (`AptIO.cpp:1302,1304`),
  DSF `sim/creation_agent` (`WED_DSFExport.cpp:2165,2295`).
