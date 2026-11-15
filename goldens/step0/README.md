# Step 0 golden outputs (baseline WED, unmodified)

Produced 2026-11-15 by `vs_build\Release\WED.exe` (WED 2.7.3-r1, built from commit 0137e80cd).
Each fixture was opened from a pristine copy in a fresh WED process, then:
rename one row **in the hierarchy pane** and type the original name back → Save → Export Scenery Pack.
**Every file here came out identical across two clean runs** (runs 3 and 4; wgs84 also run 2).
Hashes are in `SHA256SUMS.txt`.

| Fixture (package) | Export target | Files |
|---|---|---|
| `test/wgs84` → `zz_WEDtest_wgs84` | 6 = X-Plane 12.00 | earth.wed.normalized.xml, apt.dat, validation_report.txt, 6 DSFs |
| `test/dsf_export/uv_mapping.xml` → `zz_WEDtest_dsf_export` | 4 = X-Plane 11.00 | earth.wed.normalized.xml, apt.dat, validation_report.txt, 4 DSFs |

## How to compare a new run
- **DSFs, apt.dat, validation_report.txt:** compare raw bytes (`cmp`, or the hashes).
- **earth.wed.xml:** normalize first, then compare bytes:
  `python ../normalize_wed_xml.py <package>/earth.wed.xml -o new.xml`
  The script drops UI session state that WED saves into the document and that changes every run
  (selection, `map/*`, `window/*`, `map_preview_window/*`, `PropertyPaneN/*` prefs, and the
  `written by WED` version comment). See the script's docstring for the exact rules.
- Keep the order **Save, then Export**: the saved `export/last` pref depends on it.
- Don't click in the map while dirtying the document: a 1-pixel drag moves a vertex and changes
  both the XML and the DSF for that tile (this happened in runs 1 and 2).

## Version strings (stable per build, change on version bump)
apt.dat header (`AptIO.cpp:1302,1304`) and DSF `sim/creation_agent` (`WED_DSFExport.cpp:2165,2295`)
contain `2.7.3-r1`, so a version bump changes those files. The XML comment is already normalized away.

## Note on dsf_export
`uv_mapping.xml` is an older-format file. Re-saving rewrites its layout (attribute order, dropped
empty `<sources/>`/`<viewers/>`, number formatting) while keeping the same 79 objects, so the
golden is the re-saved form, not the original fixture.
