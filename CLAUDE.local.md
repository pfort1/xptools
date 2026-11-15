# Local notes (branch my-experiments)

- **Core extraction plan:** `docs/EXTRACTION_PLAN.md` — plan to split WED into
  `wed_foundation` / `wed_core` (headless) / `wed_ui_legacy` while the `WED` executable
  keeps building. Reference only; execute one numbered step at a time, and only when asked.
- Status: step 0 done; step 1 not started. Baseline Release build OK (2026-11-15): `.\cmake.ps1` then
  `cmake --build vs_build --config Release --target WED` → `vs_build\Release\WED.exe`,
  0 errors, 7954 warnings (C4244/C4250/C4267 dominate). All 16 step 0 goldens recorded in
  `goldens/step0/` (see its README); XMLs are compared after `goldens/normalize_wed_xml.py`.
  Test packages live in X-Plane 12 `Custom Scenery\zz_WEDtest_*`.
- Build env gotchas: shells started before the toolchain install need PATH reloaded from
  Machine+User; the Windows Store `python` alias breaks Conan's freetype (Meson) build.
