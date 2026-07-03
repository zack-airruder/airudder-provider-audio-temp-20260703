# Airudder Provider Evaluation Report

Saved project package for the 32-call Airudder vs competing-products provider evaluation.

## Main Files

- `index.html` - playable standalone report for GitHub/Feishu use. Audio players point to GitHub raw audio URLs.
- `audio/` - the 32 audio files referenced by the report.
- `assets/` - visual assets used by the report page.
- `source/` - source material used to build and audit the report.

## Source Package

- `source/build_recalibrated_evaluation.py` - report builder.
- `source/kb-123.md` - robot type mapping used for LLM/NLU labels.
- `source/data/recalibrated-business-evaluation-data.json` - current structured scoring data.
- `source/data/recalibrated-business-evaluation.csv` - current scoring table.
- `source/data/batch-anthropomorphism-final-32.json` - 32-call source index.
- `source/full-reports/` - per-call evaluation JSON reports.
- `source/docs/` - audit notes, scoring notes, model delta notes, and workflow checkpoint.

## Current Report Notes

- The country/company table groups by country and company.
- If a company has multiple robot/audio samples in a country, the table shows the best individual call score.
- Robot type labels are simplified to `LLM`, `NLU`, or `Unknown`.
- The Feishu-safe version uses the same `index.html` content with GitHub raw audio URLs.
