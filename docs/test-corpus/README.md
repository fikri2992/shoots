# Photography test corpus

Thirteen still Images for exercising ingestion, visual Analysis, Inspiration browsing, and Android presentation. None of these files is the Photographer's Shot. Import every item with `source_role=inspiration` so it cannot update the Technique Map, Tendency Profile, Change, or Journey.

## Online Inspiration

| File | Analysis stress | Creator | License | Source |
| --- | --- | --- | --- | --- |
| `01-panning-cyclist.jpg` | Panning, subject sharpness, motion blur | Sumita Roy Dutta | CC BY-SA 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Panning_of_cyclist_during_new_normal_days_of_COVID-19_pandemic_in_Delhi_IMG_20210411_190309.jpg) |
| `02-leading-lines-road.jpg` | Leading lines and depth | Imranrashid26 | CC BY-SA 3.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Leading_Lines.JPG) |
| `03-window-portrait.jpg` | Window light, portrait placement, shallow depth | Andrey Maximov | CC BY 2.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Portrait_at_the_window.jpg) |
| `04-sunset-silhouette.jpg` | Silhouette and warm color | Ykphotography | CC BY-SA 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Silhouette_sunset_photography.jpg) |
| `05-blue-hour-city.jpg` | Blue hour and long exposure | Lies Thru a Lens | CC BY 2.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:The_Blue_Hour_(15488802674).jpg) |
| `06-complementary-colors.jpg` | Complementary color separation | Robertgombos | CC BY-SA 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Complementary_colors_(example).jpg) |
| `07-rainy-night-street.jpg` | Night street light and wet reflections | Vyacheslav Argenberg | CC BY 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Delhi,_India,_Rain,_Street_at_night.jpg) |
| `08-window-shadow.jpg` | Hard shadow and negative space | Muntaqibah | CC BY 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Light_through_the_window.jpg) |
| `09-flower-bokeh.jpg` | Bokeh and shallow depth | Jonas Eppler | CC BY-SA 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Violett_flower_with_Bokeh_effect.jpg) |
| `10-frame-within-frame.jpg` | Frame within frame | Mahi zahidi | CC BY-SA 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Frame_within_frame.jpg) |

The blue-hour file is Wikimedia's 1280-pixel derivative because Commons rate-limited the original download. The other nine are unchanged originals.

## Generated Intent

Generated with the built-in image-generation tool. These are synthetic test inputs. Their written Intent is test metadata, not Photographer Intent.

| File | Written Intent | Analysis stress |
| --- | --- | --- |
| `11-intent-doorway-hard-light.png` | Use the doorway as a frame and let one hard sunbeam define the subject without lifting the shadows. | Frame within frame, hard light, low key, negative space |
| `12-intent-panning-cyclist.png` | Track the cyclist so the rider remains readable while the street streaks horizontally. | Panning versus camera-shake risk, travel space, mixed color temperature |
| `13-intent-color-market.png` | Let one red umbrella carry the frame through color separation and a layered diagonal aisle. | Complementary color, subject separation, layers, diagonal depth |

## Run record

- Corpus created: 2026-08-28
- Intended source role: `inspiration`
- Android import: 13 of 13 uploaded; all 13 retain `source_role=inspiration`.
- Snapshot isolation: 13 recent Inspiration items and 0 Photographer Shots.
- Android integration: `CorpusImportIntegrationTest` passed against real MediaStore, Room, WorkManager, and the running backend.
- Production behaviour: Inspiration ingestion stores the original and source role but does not currently start an Analyst Run. This corpus therefore exercises import, Archive, and inspection UI without changing Photographer memory.
- Isolated real-model quality run: all 13 inputs reached the actual Ingest and Analyst path without Photographer writes. The initial sequential report recorded 176 passing checks, 5 failing checks, 4 human-review prompts, and 2 transient Analyst task-group errors.
- Retry: both errored inputs completed. `online-complementary-colors` passed; `online-blue-hour-city` completed but missed the expected `blue_hour` Technique.
- Genuine misses retained: `online-frame-within-frame` missed `frame_within_frame`; two generated receipts leaked bare internal grid-column letters into visible copy. These are quality findings, not import failures.
- Reports: [`learning-quality.json`](results/learning-quality.json) and [`retry-errors.json`](results/retry-errors.json).
- Android visual proof: [`android-guide-corpus.png`](results/android-guide-corpus.png).
- Visual Mark replay: all 13 completed Analyses were reprojected through the new per-step mark contract. Every mark used valid cells; every located Keep, Notice, Try, and Check passed its mark-support check. The earlier Technique and copy-quality misses remain visible rather than being reclassified.
- Visual Mark reports: [`learning-quality-visual-marks.json`](results/learning-quality-visual-marks.json) and [`retry-errors-visual-marks.json`](results/retry-errors-visual-marks.json).
- Story screenshots: [`leading line`](results/android-market-leading-line.png) and [`located tarp`](results/android-market-tarp-region.png).
- Visual Evidence renderer: all 57 still Techniques resolve to a finite strategy. Real corpus checks render hue, saturation, luminance, sharpness, flat-area noise, edge-verified paths, panning direction, and YuNet face/eye artifacts; the flower example correctly falls back from unsupported bokeh discs to a sharpness map. Report and images: [`visual-evidence`](results/visual-evidence/report.json).
- Android artifact proof: [`measured hue map`](results/android-measured-artifact.png) switches to the clean Shot; [`relational pair`](results/android-pair-regions.png) keeps the umbrella and foreground separate instead of flattening them into one box.
- Local existing-Analysis backfill: 23 of 23 still Shots updated without Gemini reruns or failures. A bounded four-worker render reduced a forced rerun from about 100 seconds to 44.5 seconds.
- Post-schema real-Gemini gate: window portrait, panning cyclist, and colour market all completed through Ingest, the three-lens panel, grouped Visual Regions/Paths, deterministic artifacts, and the Shot Teaching Receipt. Result: 71 passed checks, 0 failed, 2 human-review prompts, and 0 errored cases. The market retained two leading paths plus foreground/midground/background; panning retained sharp/blurred regions and measured a 179.2° dominant direction; the portrait retained sharp/blurred and frame/subject regions plus YuNet landmarks. Report: [`visual-evidence-real-model.json`](results/visual-evidence-real-model.json).
- Android regression gate: 38 instrumentation tests passed on `Shoots_API_36`; human-gated corpus/sign-in cases skipped unless their explicit arguments are supplied. A separate disposable local-device session then passed the real WorkManager → HTTP snapshot → Room flow and was immediately revoked. Normal Google-only local auth was restored afterward.
