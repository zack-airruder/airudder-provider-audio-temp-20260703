# Pre-Push Value and Information Audit

Date: 2026-07-03

## Scope

Audited the displayed report before pushing the main page:

- `professional-provider-evaluation.html`
- `recalibrated-business-evaluation-data.json`
- `recalibrated-business-evaluation.csv`
- Desktop GitHub working copy: `/Users/zackloo/Desktop/airudder-provider-audio-temp-20260703/index.html`

## Audit Rule

- AI Rudder rows use the final AI Rudder audited score from the recalibrated data.
- Competitor rows use the latest-run competitor score from the source data.
- Region and robot tables must show individual call scores, not provider averages.
- Visible report text must not show average-score language, basis labels, best-audio-sample labels, or confusing scoring jargon.

## Result

Final audit result: `421` checks passed, `0` findings.

## Fixes Applied During Audit

- Removed visible scoring jargon: `recalibrated`, `raw latest-run`, and `raw`.
- Corrected `Airudder` spelling to `AI Rudder`.
- Fixed the region detail table `Main gap` column to use each row's audited `main_gap` value directly instead of recomputing the weakest dimension for display.

## Confirmed Checks

- `32` total evaluated calls.
- `17` AI Rudder rows.
- `15` competitor rows.
- No visible `avg`, `average`, `basis`, `best audio sample`, `what we learned`, `reply timing`, or `Audio file` column.
- Region summary table has `8` rows and uses individual top call examples.
- Every region detail table row matches the source JSON score, dimensions, source label, suite ID, and main gap.
- All `32` call detail rows match the source JSON identity and score.
- Local report audio references exist under `audio/`.
- GitHub working copy uses raw GitHub audio URLs.

## Region Top Calls

| Region | Score | Top call | Source | Suite |
|---|---:|---|---|---|
| ID | 7.3 | OB_CL_BA_ID_INDIHOME_PraNPCCT0_Qwen | AI Rudder | ID-C |
| TH | 5.5 | TH_DAX_Thai_PTP100_Prod | AI Rudder | TH-C |
| PH | 4.2 | M1_L2_PH_PH_The_360_DM2_High | AI Rudder | PH-B |
| MY | 6.3 | 竞品Seavoice（双语） | Competitors | MY-E |
| VN | 6.8 | IB_VN_VI_Duy_Logistics | AI Rudder | VN-C |
| Multi-Language | 8.2 | M1_L2_SG_EN_Far_UOB_Demo_Flash | AI Rudder | Multi-Language-B |
| MX | 7.1 | M1_L2_MX_ES_Jsu_Stori_DM2_v2 | AI Rudder | MX-B |
| BR | 7.8 | PO_DC_BR_PR_Jeni_SHEIN_DM2_B | AI Rudder | BR-B |

## Push Status

Not pushed and not uploaded during this audit.
