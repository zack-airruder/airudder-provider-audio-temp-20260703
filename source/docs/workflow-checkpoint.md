# CHECKPOINT: Gemini 3.5 Flash 32-Audio Evaluation

Goal:
Produce a complete second 32-audio Signal Room assessment round using Deepgram STT plus Zenlayer `gemini-3.5-flash`, then package it into leadership-facing HTML and DOCX artifacts.

Project/repo:
`/Users/zackloo/Documents/Versus`

Run ID:
`audio-eval-32-gemini-3.5-flash-20260702T101627Z`

Files changed:
- `tools/anthropomorphism-analyzer/run_audio_eval_round.py`
- `tools/anthropomorphism-analyzer/analyzer.py`
- `tools/anthropomorphism-analyzer/llm.py`
- `tools/anthropomorphism-analyzer/tests/test_audio_eval_round.py`
- `tools/anthropomorphism-analyzer/tests/test_core.py`
- `strategy.md`
- `tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/`

Artifacts produced:
- `/Users/zackloo/Documents/Versus/tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/batch-anthropomorphism-final-32.json`
- `/Users/zackloo/Documents/Versus/tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/report-data.json`
- `/Users/zackloo/Documents/Versus/tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/source-aligned-comparison-data.json`
- `/Users/zackloo/Documents/Versus/tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/model-delta-gemini-3.5-flash-vs-baseline.json`
- `/Users/zackloo/Documents/Versus/tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/standard-evaluation-report.html`
- `/Users/zackloo/Documents/Versus/tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/professional-provider-evaluation.html`
- `/Users/zackloo/Documents/Versus/tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/professional-provider-evaluation-document-twin.docx`
- `/Users/zackloo/Documents/Versus/tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/assets/contact-center-faded-bg.png`

Commands run:
- `ZENLAYER_AI_GATEWAY_MODEL=gemini-3.5-flash python3 tools/anthropomorphism-analyzer/run_audio_eval_round.py --index tools/call-log-dashboard/data/evaluation-suite/audio_paths_32_index.json --output-dir tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash --provider zenlayer --model gemini-3.5-flash --stt-provider deepgram --workers 1 --csv --html`
- `afconvert -f WAVE -d LEI16@16000 -c 1 .../TH-E_1_竞品LLM-Botnoi.m4a .../retry-media/TH-E_1_竞品LLM-Botnoi.normalized.wav`
- `ZENLAYER_AI_GATEWAY_MODEL=gemini-3.5-flash python3 tools/anthropomorphism-analyzer/run_audio_eval_round.py --index .../retry-index-my-d2-ms.json --output-dir .../retry-my-d2-ms --provider zenlayer --model gemini-3.5-flash --stt-provider deepgram --language ms-MY --workers 1 --csv --html --no-cache`
- `/Users/zackloo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 .../build_document_twin.py`
- `/Users/zackloo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 /Users/zackloo/.codex/plugins/cache/openai-primary-runtime/documents/26.630.12135/skills/documents/render_docx.py .../professional-provider-evaluation-document-twin.docx --output_dir .../docx-render --emit_pdf`
- `python3 -m unittest discover -s tools/anthropomorphism-analyzer/tests -v`

Result:
`input_count=32`, `scored_count=32`, `missing_count=0`, `failures=0`, average score `4.70`.

Key decisions:
- Used the curated 32-file index only; avoided recursive folder scan.
- Used `gemini-3.5-flash` because `gemini-3.1-pro` was unavailable through Zenlayer.
- Kept comparison fair: AI Rudder and competitor files are compared only on shared audio evidence.
- Fixed `TH-E_1_竞品LLM-Botnoi.m4a` by scoring a normalized 16 kHz mono WAV retry copy.
- Fixed `MY-D_2_竞品LLM-Revocall(双语).m4a` by retrying Deepgram with explicit Malay language hint `ms-MY`.
- Created a faded contact-center background image via built-in image generation and stored it in the report bundle.
- Created a Word-native DOCX twin using the Documents workflow and visually verified rendered pages.

Known risks:
- Generated report outputs are runtime artifacts and may be large for source control.
- Scores are evaluator/model outputs; model deltas should not be treated as product regressions without evidence review.
- Competitor recordings are media-only, so full business QA should not be mixed into headline comparisons.

Not done:
- No media re-download.
- No full BigJSON business scoring.
- No Google Docs import/upload.
- No git commit or staging.

Remote/API/browser actions:
- Deepgram STT calls.
- Zenlayer AI Gateway calls using `gemini-3.5-flash`.
- Built-in image generation for the faded contact-center background.
- Local browser/render checks for HTML and DOCX.

Next recommended prompt:
`Review the Gemini 3.5 Flash 32-audio report bundle and produce a leadership summary that explains what changed after fixing the two retry files, with 3 recommendations for AI Rudder product improvement. Use the fixed 32/32 artifacts only.`

Suggested next agent:
Evaluation reviewer / leadership report writer.

---

# CHECKPOINT: Recalibrated Business Evaluation

Goal:
Revisit the 32-call evaluation because the strict human-likeness scoring was too harsh for leadership review.

Project/repo:
`/Users/zackloo/Documents/Versus`

Files changed:
- `tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/build_recalibrated_evaluation.py`
- `tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/workflow-checkpoint.md`

Artifacts produced:
- `tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/recalibrated-business-evaluation.html`
- `tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/professional-provider-evaluation.html`
- `tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/recalibrated-business-evaluation-data.json`
- `tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/recalibrated-business-evaluation.csv`

Commands run:
- `python3 tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/build_recalibrated_evaluation.py`
- `python3 -m py_compile tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/build_recalibrated_evaluation.py`

Result:
- Original strict average: `4.70`.
- Revised practical voicebot average: `5.89`.
- `19/32` calls now score good or better under the business-usability lens.
- AI Rudder average moves from `4.92` to `6.17`; competitor average moves from `4.45` to `5.57`.

Key decisions:
- Preserve raw Gemini 3.5 Flash scores as strict human-likeness scores.
- Add a separate calibrated score rather than silently overwriting the original run.
- Give more credit for clear openings, task movement, understandable flow, and recoverable imperfections.
- Keep genuinely broken calls capped so the recalibration does not turn bad calls into good calls.
- `PO_MY_MS_EN_Far_AeonCredit_PF_DM2` is treated as STT-limited because the expected language is `ms-MY` but Deepgram detected `id`; self-answering/loop penalties are discounted unless confirmed by cleaner Malay STT or manual listening.
- `professional-provider-evaluation.html` now presents the latest-lens values as the canonical professional report, without reader-facing raw/revised/recalibration wording.
- High-end CMO/CPO rebuild completed for `professional-provider-evaluation.html`.
- The report now leads with leadership readout, showcase proof, provider position, market map, and risk focus before the appendix.
- The 32-file appendix is decision-oriented instead of technical: each row shows leadership use and a plain product priority, with long VAD/end-of-speech repair text removed from the HTML.
- Verified generated HTML contains latest values (`5.89` average, `19/32` good or better, `PO_MY_MS_EN_Far_AeonCredit_PF_DM2` at `6.2`) and no reader-facing raw/revised/recalibrated/strict framing.
- Restored strategy and flow after user feedback: the report now reads as decision -> strategy flow -> regional readiness comparison -> showcase proof -> provider position -> market map -> risk focus -> appendix.
- Region comparison now includes market average, good-call coverage, AI Rudder average, competitor average, best example, and strategic action for each region.
- Rebuilt `professional-provider-evaluation.html` again to align with the canonical professional format from `deepgram-audio-eval-32/professional-provider-evaluation.html`, matching the Feishu reference style requested by the user.
- New generated structure: professional evaluation meaning -> evaluation strategy -> result learnings -> region/provider results -> all 32 expandable call evaluations -> recommended next move.
- The report now has 14 sections, 32 expandable call rows, 42 tables, five score-part evidence cards per call, transcript samples, highlights, red flags, advice, and region/provider tables.
- The previous compact leadership page is no longer used; `main()` now calls `write_reference_aligned_html(data)`.
- Verified generated HTML title and headings match the canonical structure. Playwright is not installed in this repo, so screenshot verification was not completed in this pass.
- Region section updated per user request: removed reader-facing strategy labels such as `Selective proof`, `Repair lane`, `Scale story`, `Controlled pilot`, and `Flagship demo lane`.
- Region cards now use pure region titles (`ID`, `TH`, `PH`, `MY`, `VN`, `Multi-Language`, `MX`, `BR`), list robots in the region, highlight the best robot, and show `What's good`, `What needs attention`, and `What to improve`.

Known risks:
- This is a deterministic recalibration over existing Gemini evidence, not a fresh model re-judge.
- Playwright was available but its browser binary was missing, so browser screenshot QA was not completed.

Not done:
- Rebuilt DOCX for the recalibrated report.
- Uploaded recalibrated files to Feishu.

Remote/API/browser actions:
- No remote scoring calls.
- No Feishu upload in this pass.

Next recommended prompt:
`Turn recalibrated-business-evaluation.html into a matching DOCX and upload both recalibrated files to the same Feishu folder.`

Suggested next agent:
Evaluation reviewer / document publisher.

---

# CHECKPOINT: Professional Report Audio Playback Update

Goal:
Make `professional-provider-evaluation.html` cleaner and replayable from the local report folder.

Files changed:
- `tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/build_recalibrated_evaluation.py`
- `tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/professional-provider-evaluation.html`
- `tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/recalibrated-business-evaluation.html`
- `tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/audio/`

Changes made:
- Removed the AI Rudder and Competitors summary cards from the `What we learned` section.
- Added an `Audio` column to the region summary table.
- Added an `Audio` column to each per-region provider table.
- Copied all 32 source audio files into the report folder under `audio/`.
- Audio filenames are hash-prefixed to avoid collisions from sanitized non-ASCII competitor filenames.

Verification:
- `python3 tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/build_recalibrated_evaluation.py`
- `python3 -m py_compile tools/call-log-dashboard/data/evaluation-suite/deepgram-audio-eval-32-gemini-3.5-flash/build_recalibrated_evaluation.py`
- Verified copied audio file count: `32`.
- Verified generated HTML has `34` audio controls and no visible AI Rudder/Competitors summary cards.
