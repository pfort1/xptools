# WED core extraction plan (wed_foundation / wed_core / wed_ui_legacy)

## Context
You're deciding whether to build a new scenery editor on WED's domain core (things, entities, document, archive, undo, import/export) and replace only the UI. This plan checks the dependency picture, proposes a CMake split that keeps `WED` building at every step, and orders the work into small steps with a risk level for each.
Decisions so far: (a) WEDMap tools stay in `wed_ui_legacy` for now. (b) Core interfaces stay toolkit-agnostic: plain C++ hooks, no Qt or ImGui types.
Branch: `my-experiments`. Every step lands as its own commit, and `master` is not touched.

---

## 1. Your findings, verified

| Your claim | Verdict | Evidence |
|---|---|---|
| WED is one flat `WED_SOURCES` list in one `add_executable` | ✅ True | `cmake/WED.cmake:32-551, 704-715`. `WED_TerPlacement` is listed twice (lines 128 and 178), which is harmless. |
| Core depends on the GUI toolkit only lightly (Broadcaster, Listener, Messages, Unicode, MemoryHog, Prefs, Destroyable/Timer) | ⚠️ **Understated** | The GUI_* *toolkit* coupling is roughly as you said. But the core also includes **WEDMap and WEDWindows headers**: `WED_ToolUtils.h` in 28 files under the core dirs (≈22 after excluding the misfiled UI files ValidateList, AptImportDialog, MetadataUpdate, GatewayImport/Export), `WED_GroupCommands.h`, `WED_ConvertCommands.h`, `WED_Menus.h` (metadata enums plus `WED_GetTargetMenuName`), `WED_UIDefs.h`, `WED_MapZoomerNew.h`, `WED_PreviewLayer.h` and `WED_DrawUtils.h`. The good news is that almost everything the core uses from these is pure document logic sitting in UI files (§2). |
| Vestigial includes in WED_Validate.cpp and WED_AptIE.cpp | ⚠️ Partly | `WED_Validate.cpp:68` uses `wed_AddMetaData*` (real), and `:3107` does `new WED_ValidateDialog` (a real UI call). `WED_AptIE.cpp:61` uses `gApplication` as the dialog parent (real). The truly vestigial ones are `GL/glu.h` in `WED_GISUtils.cpp:18-20`, `WED_ToolUtils.h` in `WED_GISLine_Width.cpp` and `WED_GISPoint_HeadingWidthLength.cpp`, and `WED_UIDefs.h` in GatewayExport, GatewayImport and SceneryPackExport. |
| `WED_Document.cpp` uses GUI_Prefs plus one `GUI_SetFontSizes` call | ⚠️ Understated | Also: base classes `GUI_Destroyable` and `GUI_Broadcaster` (`WED_Document.h:68`), seven blocking dialogs (`:115,277,327,353,388,446,474`), `WED_GetWorld` (WEDMap) and `WED_Repair` (WEDWindows). It also hosts 6 of the 7 UI/pref globals (`:62-67`). |
| UI files misfiled in WEDCore and WEDImportExport | ✅ True, plus more | Also: `WED_MetadataUpdate.cpp` (a GUI_FormWindow), the dialog halves of `WED_GatewayImport/Export.cpp`, and `WED_MakeOrthos`/`WED_MakeTerrain` in `WED_Orthophoto.cpp` (file dialogs and zoomer). |
| GL in the core is limited to TexMgr, FacadePreview, TCEDebugLayer, GISUtils and AppMain | ✅ Mostly | `WED_GISUtils` makes no GL calls. **New:** `WED_ResourceMgr.h:88` includes `WED_FacadePreview.h`, because the facade data structs (`REN_*`) and the GL renderer `draw_facade` share one file. `WED_ValidateATCRunwayChecks.cpp:913` calls `layer_group_for_string`, a pure function that lives in GL-heavy `WED_PreviewLayer.cpp:482`. |

Other surprises:
- `WEDNetwork` live-collab is **not built**: only `RAII_Classes.cpp` is compiled, and `WITHNWLINK` is off.
- **No automated tests exist.** CI only builds, and the `test/` fixtures are manual visual checks in X-Plane.
- **No headless load/save path exists.** The only creator of a `WED_Document` is `WED_StartWindow.cpp:370`.

---

## 2. Remaining dependencies of the core (full inventory)

### 2a. Headless-safe already (go to foundation unchanged)
GUI_Broadcaster, GUI_Listener, GUI_Messages.h, GUI_MemoryHog, GUI_Unicode; Utils: AssertUtils, CmdLine, MemFileUtils, FileUtils, GISUtils, BitmapUtils, CompGeomUtils, EndianUtils, md5, XChunkyFileUtils, zip, unzip, CSVParser, STLUtils; Obj: XObjDefs, XObjReadWrite, ObjPointPool; DSF/*, DSF2Text, tri_stripper; Network: b64, curl_http; WEDNetwork/RAII_Classes; XESCore: AptIO, DEMDefs; lzma19, libtess2.

### 2b. Needs a small change to become headless
| File | Problem | Fix |
|---|---|---|
| `Utils/MatrixUtils.h` (and ObjUtils through it) | includes gl.h only for `GLdouble`/`GLboolean` | Use `double`/`bool`, or a local typedef |
| `Utils/BWImage.cpp` | unused gl.h | Delete the include |
| `WEDCore/WED_GISUtils.cpp:18-20` | unused glu.h | Delete the include |
| `Obj/XDefs.h:250` (force-included) | `extern FILE* gLogFile`, defined in `WED_AppMain.cpp:141` | Move the definition into foundation |
| `Utils/PlatformUtils.*` | Paths (`GetApplicationPath`, `GetCacheFolder`, `DIR_STR`) are mixed with dialogs (`DoUserAlert`, `ConfirmMessage`, `DoSaveDiscardDialog`, `GetFilePathFromUser`). The Linux dialogs are FLTK (`PlatformUtils.lin.cpp:179`). | Split into a paths file (foundation) and `PlatformDialogs.*` (ui_legacy). Foundation gets a **hook table** with the same function names: the default writes to stderr and returns the default answer, and the legacy UI installs the real dialogs at startup. Call sites don't change. |
| `GUI/GUI_Prefs.cpp` | only UI use is `DoUserAlert` on write failure | Goes to foundation as-is once the alert hook exists |
| `GUI/GUI_Destroyable.cpp` | `AsyncDestroy` uses `GUI_Timer` (FLTK, Win32 `SetTimer` or CFRunLoop) | Keep the class name in foundation. Replace the timer with a `DeferredDelete_Schedule` hook plus `DeferredDelete_Drain()`. The legacy UI installs a GUI_Timer-based scheduler; a headless host calls `Drain()`. |
| `DSF/DSFLibWrite.cpp:1088` | `DoUserAlert` under `#if WED` | Solved by the alert hook |

### 2c. Core → UI-file coupling (pure logic stuck in UI files)
| Used from | Core usage | Fix |
|---|---|---|
| `WEDMap/WED_ToolUtils.cpp` | Getters (`WED_GetWorld/Select/ResourceMgr/LibraryMgr/TexMgr`), hierarchy, airport and runway helpers, `Iterate_*` | Move the file to `WEDCore/` **except** the drag-and-drop block (lines 715-750: `WED_RegisterDND`, `WED_DoDragSelection`, `WED_IsDragSelection`), which goes to a new `WEDMap/WED_ToolDnD.cpp`. Drop the `GUI_Pane.h`/`GUI_Clipboard.h`/`GUI_Defs.h` includes. |
| `WEDWindows/WED_GroupCommands.cpp` (5.3k lines, includes the zoomer and MarqueeTool) | `WED_Repair`, `WED_select_doubles`, `WED_RecursiveDelete`, `WED_DoDuplicate`, `wed_upgrade_ramps`, `wed_break_apart_special_agps`, `WED_CanReplaceVehicleObj`/`WED_DoReplaceVehicleObj`, `WED_DoConvertToJW`, `WED_DoMowGrass` | Move these nine functions (and their static helpers) into a new `WEDCore/WED_DocOps.{h,cpp}`. `WED_GroupCommands.h` includes `WED_DocOps.h`, so UI callers don't change. |
| `WEDWindows/WED_ConvertCommands.cpp` | `WED_DoConvertTo`, `WED_DoConvertToForest` | The file includes no GUI headers, so move it whole to `WEDCore/` |
| `WEDWindows/WED_Menus.h` | `wed_AddMetaData*` enum (Validate, Airport, MetaData*, GatewayExport, SceneryPackExport); `WED_GetTargetMenuName` (`SceneryPackExport.cpp:694`) | Move the enum into `WED_MetaDataKeys.h` with the same values (they are menu command IDs offset from `GUI_APP_MENUS`=2000), and include it from `WED_Menus.h`. Add a core `WED_GetExportTargetName()` string table, which the menus then use too. |
| `WEDWindows/WED_UIDefs.h` | `FILE_DIALOG_*` constants passed to file dialogs | Move to foundation next to the dialog hooks |
| `WEDMap/WED_PreviewLayer.cpp:482` | `layer_group_for_string` | Move to a new `WEDCore/WED_LayerGroups.cpp` |
| `WEDEntities/WED_FacadePreview.{h,cpp}` | ResourceMgr needs the `REN_*`/`fac_info_t` structs and `height_desc_for_facade`; `draw_facade` is GL | Split into `WEDCore/WED_FacadeDefs.{h,cpp}` (structs, `height_desc_for_facade`, parsing helpers) and `WEDMap/WED_FacadeDraw.cpp` (GL) |
| `WEDMap/WED_MapZoomerNew.h` in `WED_Orthophoto.cpp` | `WED_RingfromImage` uses zoomer bounds | Pass a `Bbox2` instead. Move `WED_MakeOrthos`/`WED_MakeTerrain` (dialog commands) to ui_legacy. |

### 2d. GL in the core
| Item | Fix |
|---|---|
| `WED_TexMgr` (`glGenTextures` at `:105`), owned by `WED_Document.cpp:87-89` | Move to ui_legacy. `WED_Document` gets its `ITexMgr` from a factory hook. Add a headless `WED_TexInfoMgr` (BitmapUtils header read, no upload) so `GetTexInfo` in `WED_Orthophoto.cpp:190` and `WED_OrthoExport.cpp:253` keeps working. |
| `WED_FacadePreview` draw half | See §2c |
| `WED_TCEDebugLayer` | UI file misplaced in WEDCore; move to `WEDTCE/` |

---

## 3. Target CMake split

Mechanics:
- Start with **OBJECT libraries** so link order and the existing violations can't break the build.
- Switch to STATIC once layering is clean.
- `wed_foundation` carries the shared `INTERFACE` settings: `BASIC_PLATFORM_DEFINES`, `WED=1`, `USE_JPEG`, `USE_TIF`, the force-included `XDefs.h`, and the third-party libraries except GL, GLEW, FreeType and FLTK.
- **Include directories enforce the layering**: `wed_core` does not get `src/GUI`, `src/UI`, `src/WEDMap`, `src/WEDWindows`, `src/WEDLibrary`, `src/WEDProperties` or `src/WEDTCE`.
- The five headless GUI_* files are moved (`git mv`) to `src/Foundation/`, so the GUI include dir isn't needed. Legacy code includes them by bare name, so no source edits are needed.

| Target | Contents |
|---|---|
| **wed_foundation** | Everything in §2a and §2b; new `src/Foundation/` (GUI_Broadcaster, Listener, Messages, MemoryHog, Unicode, Destroyable, Prefs); PlatformUtils paths + hook table; `WED_UIDefs.h`; `gLogFile`. Links: expat, zlib, png, jpeg, tiff, geotiff, proj, squish, curl, jsoncpp. **No** GL, GLEW, FreeType or FLTK. |
| **wed_core** | `src/Interfaces/`. WEDCore: Archive, Assert, Buffer, Clipping, Document, EnumSystem, Errors, FastBuffer, Globals, GISUtils, HierarchyUtils, LibraryMgr, PackageMgr, Persistent, PropertyHelper, ResourceMgr, Sign_Parser, Orthophoto (core half), UndoLayer, UndoMgr, Validate (engine), ValidateATCRunwayChecks, XMLReader, XMLWriter, plus the new **ToolUtils, DocOps, ConvertCommands, LayerGroups, FacadeDefs, TexInfoMgr, CoreInit**. All of WEDEntities except FacadePreview's draw half. WEDImportExport: AptIE (engine), DSFImport, DSFExport, SceneryImport, SceneryPackExport, OrthoExport, MetaDataKeys, MetaDataDefaults. WEDFileCache/*. |
| **wed_ui_legacy** | `src/GUI/*` (remainder), `src/UI/XWin*`, PlatformDialogs.*, TexUtils, ObjDraw, OGLE, WEDMap/*, WEDTCE/* (+ TCEDebugLayer), WEDProperties/*, WEDLibrary/*, WEDWindows/*, WED_TexMgr, WED_Application, WED_ValidateList, WED_AptImportDialog, WED_AptTable, WED_ICAOTable, WED_VerTable, WED_MetadataUpdate, WED_GatewayImport, WED_GatewayExport (whole files for now, see §5), the UI halves of AptIE/Orthophoto/Validate (`WED_DoImportApt`, `WED_MakeOrthos`, `WED_ValidateDoc` dialog launch). Links: GL, GLEW, FreeType, FLTK/egl (Linux), comctl32, Carbon/AppKit. |
| **WED** (exe) | `WED_AppMain.cpp`, platform resources (`.rc`, xib, objcopy embedding). Links ui_legacy, core and foundation. |
| **wed_core_smoke** (new, headless) | A ~150-line CLI linking only core + foundation (§4, step 3). It is both the test harness and the proof that the layering holds: **any leftover UI dependency shows up as a link error**. |

---

## 4. Ranked steps (each builds `WED` on its own; one commit per step)

Verification legend:
- **B** = build WED with `cmake.ps1` (Windows; ideally Linux too, since FLTK leaks only show up there).
- **M** = manual run: open the `test/wgs84` package, save, export pack, and compare the outputs against the **golden outputs from step 0**.
- **S** = `wed_core_smoke` run against the fixtures, outputs diffed against goldens.

| # | Step | Risk | Verify |
|---|---|---|---|
| 0 | **Baseline.** Build unmodified WED. Golden outputs carry `WED_VERSION_STRING` (XML comment `WED_Document.cpp:806`, DSF `sim/creation_agent` `WED_DSFExport.cpp:2165,2295`, apt.dat header `AptIO.cpp:1302,1304`): stable per build, changes on version bumps. Fixtures must be placed under an X-Plane `Custom Scenery` folder to open. For `test/wgs84/earth.wed.xml` and `test/dsf_export/uv_mapping.xml` (renamed), save the re-saved `earth.wed.xml`, exported `apt.dat`, and DSF → `DSF2Text` text dumps as golden outputs (stored outside `test/` or on a branch-only path). | Low | B, M |
| 1 | CMake only: split `WED_SOURCES` into three OBJECT libraries with the same include dirs and flags, and remove the duplicate TerPlacement entry. | Low | B; the binary should behave identically |
| 2 | Remove the vestigial includes (glu in GISUtils, gl.h in BWImage, ToolUtils in 2 entities, UIDefs in 3 IE files, duplicate includes); MatrixUtils GL types → plain types. | Low | B |
| 3 | Add the foundation hook table (alert, confirm, save/discard, file-path, deferred-delete scheduler); legacy installs the real implementations in `WED_AppMain`. Move `gLogFile` into foundation. Add `WED_CoreInit()`, extracted from `WED_AppMain.cpp:240-253` (AssertInit, ENUM_Init, REGISTER_LIST, FileCache init). | Med (init order) | B, M (dialogs still appear in WED) |
| 4 | Split PlatformUtils into paths and dialogs; GUI_Destroyable runs on the scheduler hook; move the five headless GUI files + Destroyable + Prefs into `src/Foundation/`. | Med (deferred delete timing on window close) | B, M: close a doc and a window, quit with unsaved changes |
| 5 | Move ToolUtils into WEDCore (drag-and-drop → `WED_ToolDnD.cpp`); ConvertCommands into WEDCore; create `WED_DocOps` from the nine GroupCommands functions. | Med (big mechanical move; static helpers shared within GroupCommands) | B, M: Repair on load, export pack with JW/vehicle conversions |
| 6 | Metadata enum → `WED_MetaDataKeys.h`; `WED_GetExportTargetName` table; `layer_group_for_string` → `WED_LayerGroups.cpp`. | Low | B, M: the export menu labels are unchanged |
| 7 | Split FacadePreview into FacadeDefs (core) and FacadeDraw (WEDMap). | Med | B, M: facade preview in the map and the library pane |
| 8 | ITexMgr factory hook in `WED_Document`; WED_TexMgr → ui_legacy; add `WED_TexInfoMgr`; `WED_RingfromImage` takes a `Bbox2`; MakeOrthos/MakeTerrain → ui_legacy. | Med-High (ortho import paths) | B, M with the `test/tiff_import/*.tif` howto |
| 9 | WED_Document: move `GUI_SetFontSizes` and the UI-only globals (`gFontSize`, `gInfoDMS`, `gCustomSlippyMap`, `gModeratorMode`) to `WED_Application`; **move `export_target` persistence from `WED_DocumentWindow.cpp:674,711-715` into `WED_Document`** save/load. | **High** (behaviour change to a semantic global) | B, M: change the target, save, reopen; Validate results match the goldens |
| 10 | Validate: split the engine from the `WED_ValidateDialog` launch (`WED_Validate.cpp:3107`); move the misfiled UI files (ValidateList, AptImportDialog, the three tables, MetadataUpdate, TCEDebugLayer, Application) to ui_legacy target and directories. | Med | B, M: Validate with errors opens the list |
| 11 | Tighten `wed_core` include dirs (drop GUI/WEDMap/WEDWindows…). Build `wed_core_smoke`: CoreInit, open package, save, `WED_AptExport`, `WED_ExportPackToPath`, `WED_ValidateApt(skipErrorDialog=true)`. Fix residual link errors. | Med-High (unknown residue; Gateway files likely the worst) | B, **S**: diff against goldens. This step proves the split works. |
| 12 | Convert OBJECT → STATIC libraries; optional `add_test` for the smoke run; CI job building `wed_core_smoke` on Linux (catches FLTK leaks). | Low | B, S, CI |

Deferred (not needed for the split): separating Gateway Import/Export engines from their dialogs (HTTP and JSON logic are interleaved with GUI_Timer polling); making `WED_Runway::PropEditCallback`'s `ConfirmMessage` (`WED_Runway.cpp:582`) non-blocking; removing the dead `WITHNWLINK` code.

---

## 5. Reuse vs rewrite: honest assessment

**Reuse the core.** It is the valuable part. The pieces that are expensive to recreate:
- the property-reflection, XML and undo machinery (`WED_Thing`, `WED_PropertyHelper`, `WED_Archive`, `WED_UndoMgr`)
- around 60 entity types with years of apt.dat/DSF edge cases
- validation (about 3k lines of Gateway rules)
- the DSF and apt.dat writers

Most coupling is *misplacement* rather than entanglement, so §4 is mostly mechanical. Rough estimate: **2–4 focused weeks to reach step 11**, and Gateway is the wildcard.

Harder than it looks:
1. **Semantic globals.**
   - `gIsFeet` changes values *inside* `WED_PropDoubleTextMeters::Get/SetProperty` (`WED_PropertyHelper.cpp:503-519`). Any scripted or API client reads feet or metres depending on a UI pref. The long-term fix is for the core to always use metres and the UI to convert.
   - `gExportTarget` (about 60 reads) changes validation and export, and today it is persisted only by the document window.
   - `gOrthoExport` switches DDS vs PNG.
2. **Process-wide singletons.** `gPackageMgr` (a stack object in `WED_AppMain.cpp:205`), `gFileCache`, the static class factory (`WED_Persistent.cpp:88`), enum tables, and `sGlobalPrefs`/`sDocuments` in `WED_Document.cpp:69-70`. Several documents in one process mostly work today, but nothing is thread-safe, and there are function-local statics in the `PropEditCallback`s of Runway, TaxiRoute, FacadeNode and DrapedOrthophoto.
3. **Blocking dialogs inside domain logic.** These include a property setter (`WED_Runway.cpp:582`) and the document constructor (`WED_Document.cpp:115`, which asks whether to import an existing apt.dat or DSF). The hook keeps them compiling, but a modern async UI will want these turned into return values or events. That is real redesign work, done function by function.
4. **Coarse change notification.** The UI learns about changes only through `msg_ArchiveChanged` on undo commit, without saying what changed. A new UI with incremental views (a tree or a GPU map) will need a finer-grained change feed. This is new code, though it can live on top of `WED_UndoLayer`.
5. **The rendering is not reusable.** All map, preview and facade drawing is legacy fixed-function GL inside WEDMap. A new UI must reimplement rendering from the entity and GIS interfaces. The *editing* logic in the map tools also stays in legacy (decision a), so expect to rewrite or port the tool state machines later.
6. **No test net.** Every step relies on golden-output diffs that you have to create in step 0, and `wed_core_smoke` becomes the first automated test. Without it, regressions in export are silent.
7. **Gateway Import/Export** mixes networking, JSON, dialog state and `GUI_Timer` polling in single files (`WED_GatewayExport.cpp:249`, `WED_GatewayImport.cpp:200`). It is the least extractable core feature, so plan to rewrite its flow around the reusable pieces (`curl_http`, `WED_FileCache`, `WED_ExportPackToPath`).

**Bottom line:** reuse the core. It is cleaner underneath than the include graph suggests. Rewrite the UI, rendering and Gateway workflow. Budget explicit design time for points 1, 3 and 4. They are not extraction problems but API problems a new UI will hit right away.

## Critical files
- `cmake/WED.cmake`
- `src/WEDCore/WED_AppMain.cpp`
- `src/WEDCore/WED_Document.{h,cpp}`
- `src/WEDMap/WED_ToolUtils.cpp`
- `src/WEDWindows/WED_GroupCommands.cpp`
- `src/WEDWindows/WED_Menus.h`
- `src/WEDEntities/WED_FacadePreview.*`
- `src/WEDCore/WED_TexMgr.cpp`
- `src/WEDCore/WED_Validate.cpp`
- `src/WEDCore/WED_Orthophoto.cpp`
- `src/Utils/PlatformUtils.*`
- `src/GUI/GUI_Destroyable.cpp`
- `src/GUI/GUI_Prefs.cpp`
- `src/Obj/XDefs.h`
- `src/WEDWindows/WED_DocumentWindow.cpp:674,711-715`

## Verification (whole plan)
Golden outputs from step 0 (re-saved XML, apt.dat, DSF2Text dumps of exported DSFs) are diffed after every step: manually through WED for steps 1–10, and automatically through `wed_core_smoke` from step 11. Each step must also pass a Windows build with `cmake.ps1`, and a Linux build where available.
