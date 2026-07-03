# Hybrid Scoring Audit: AI Rudder Recalibrated, Competitors Raw

Source artifacts:
- `batch-anthropomorphism-final-32.json`
- `batch-anthropomorphism.csv`
- `full/*-report.json`

Scoring rule:
- AI Rudder calls use the recalibrated business/practical voicebot score.
- Competitor calls use the original latest-run raw Gemini score.
- Agent value is the average score across calls for that same agent/robot under the above rule.
- Representative sample is the highest-scoring call for that agent under the same rule and is used for playable audio.

Overall raw average across all calls: `4.70`
Overall hybrid average across all calls: `5.36`

## Region Winners

| Region | Winner | Source | Calls | Agent score | Raw avg | Recal avg | Representative audio sample |
|---|---|---:|---:|---:|---:|---:|---|
| Multi-Language | 竞品EIS | Competitors | 1 | 7.20 | 7.20 | 8.00 | `Multi-Language-D_1_竞品LLM-EIS.mp3` |
| BR | PO_DC_BR_PR_Jeni_SHEIN_DM2_B | AI Rudder | 1 | 7.80 | 6.80 | 7.80 | `1d90c46116244eee8e485d0016b99dc9.wav` |
| MX | M1_L2_MX_ES_Jsu_Stori_DM2_v2 | AI Rudder | 1 | 7.10 | 6.30 | 7.10 | `49e24746b71449bfbe2421e6789a8b2b.wav` |
| ID | OB_CL_BA_ID_INDIHOME_PraNPCCT0_Qwen | AI Rudder | 1 | 7.30 | 6.20 | 7.30 | `aead7856624f4b5cbb64e34230f4aaa5.wav` |
| MY | 竞品Seavoice（双语） | Competitors | 1 | 6.30 | 6.30 | 7.20 | `MY-E_1_竞品LLM-Seavoice(双语).mp3` |
| VN | IB_VN_VI_Duy_Logistics | AI Rudder | 1 | 6.80 | 5.50 | 6.80 | `03163f0a9a7f4aa1b23ccd457d1e6c6f.wav` |
| TH | TH_DAX_Thai_PTP100_Prod | AI Rudder | 1 | 5.50 | 5.00 | 5.50 | `1da381b6d1614491b253fa6763ffae98.wav` |
| PH | M1_L2_PH_PH_The_360_DM2_High | AI Rudder | 1 | 4.20 | 2.80 | 4.20 | `60e150657b62473bb37ef674f4b23e2a.wav` |

## Multi-Language

| Rank | Agent / robot | Source | Calls | Score used | Raw avg | Recal avg | Basis | Representative sample |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | 竞品EIS | Competitors | 1 | 7.20 | 7.20 | 8.00 | Raw | `Multi-Language-D_1_竞品LLM-EIS.mp3` |
| 2 | M1_L2_SG_EN_Far_UOB_Demo_Flash | AI Rudder | 2 | 6.90 | 5.60 | 6.90 | Recalibrated | `3ac8118ac7154807a70ffaa6f3845d25.wav` |

## BR

| Rank | Agent / robot | Source | Calls | Score used | Raw avg | Recal avg | Basis | Representative sample |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | PO_DC_BR_PR_Jeni_SHEIN_DM2_B | AI Rudder | 1 | 7.80 | 6.80 | 7.80 | Recalibrated | `1d90c46116244eee8e485d0016b99dc9.wav` |
| 2 | CL_BR_PT_mat_CredSystem | AI Rudder | 1 | 6.70 | 5.60 | 6.70 | Recalibrated | `808bbab1cf1040368c5055f56cc86a56.wav` |
| 3 | M1_L2_BR_PT_Gil_DIDI_M25_S1 | AI Rudder | 1 | 6.50 | 5.20 | 6.50 | Recalibrated | `e456a69ddda54dd8a9ecbf145ee1080e.wav` |
| 4 | https://newup.tech/en | Competitors | 1 | 5.60 | 5.60 | 6.60 | Raw | `BR-E_1_https_newup.tech_en.mpeg` |

## MX

| Rank | Agent / robot | Source | Calls | Score used | Raw avg | Recal avg | Basis | Representative sample |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | M1_L2_MX_ES_Jsu_Stori_DM2_v2 | AI Rudder | 1 | 7.10 | 6.30 | 7.10 | Recalibrated | `49e24746b71449bfbe2421e6789a8b2b.wav` |
| 2 | M1_L2_MX_ES_Jess_Bankaya_UberProCard_CL | AI Rudder | 1 | 6.50 | 5.40 | 6.50 | Recalibrated | `910c30c0c299424b8878e6b373604f30.wav` |
| 3 | 竞品Jekka.ai | Competitors | 1 | 5.20 | 5.20 | 6.50 | Raw | `MX-D_1_竞品LLM-Jekka.ai.wav` |

## ID

| Rank | Agent / robot | Source | Calls | Score used | Raw avg | Recal avg | Basis | Representative sample |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | OB_CL_BA_ID_INDIHOME_PraNPCCT0_Qwen | AI Rudder | 1 | 7.30 | 6.20 | 7.30 | Recalibrated | `aead7856624f4b5cbb64e34230f4aaa5.wav` |
| 2 | M0_L2_ID_BA_Fin_Kuainiu_DM2_DPD1 | AI Rudder | 1 | 6.40 | 5.50 | 6.40 | Recalibrated | `70bd84b859c74eb59647504826fe158b.wav` |
| 3 | 竞品Dyna | Competitors | 3 | 5.07 | 5.07 | 6.43 | Raw | `ID-D_3_竞品LLM-Dyna.wav` |

### ID Call-Level Detail

| Agent / robot | Source | File | Raw | Recalibrated | Score used | Basis |
|---|---:|---|---:|---:|---:|---|
| OB_CL_BA_ID_INDIHOME_PraNPCCT0_Qwen | AI Rudder | `aead7856624f4b5cbb64e34230f4aaa5.wav` | 6.2 | 7.3 | 7.3 | Recalibrated |
| M0_L2_ID_BA_Fin_Kuainiu_DM2_DPD1 | AI Rudder | `70bd84b859c74eb59647504826fe158b.wav` | 5.5 | 6.4 | 6.4 | Recalibrated |
| 竞品Dyna | Competitors | `ID-D_3_竞品LLM-Dyna.wav` | 6.2 | 7.6 | 6.2 | Raw |
| 竞品Dyna | Competitors | `ID-D_1_竞品LLM-Dyna.wav` | 4.5 | 5.7 | 4.5 | Raw |
| 竞品Dyna | Competitors | `ID-D_2_竞品LLM-Dyna.wav` | 4.5 | 6.0 | 4.5 | Raw |

## MY

| Rank | Agent / robot | Source | Calls | Score used | Raw avg | Recal avg | Basis | Representative sample |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | 竞品Seavoice（双语） | Competitors | 1 | 6.30 | 6.30 | 7.20 | Raw | `MY-E_1_竞品LLM-Seavoice(双语).mp3` |
| 2 | PO_MY_MS_EN_Far_AeonCredit_PF_DM2 | AI Rudder | 1 | 6.20 | 2.60 | 6.20 | Recalibrated | `ed00bb77fc7045be93c3d70a66e94be2.wav` |
| 3 | MY_EN_MS_CL_UOB_Far | AI Rudder | 1 | 6.10 | 5.10 | 6.10 | Recalibrated | `8f0a5462c45a4740b2afc59a7df19e4a.wav` |
| 4 | 竞品Revocall（双语） | Competitors | 2 | 4.05 | 4.05 | 5.20 | Raw | `MY-D_1_竞品LLM-Revocall(双语).m4a` |

## VN

| Rank | Agent / robot | Source | Calls | Score used | Raw avg | Recal avg | Basis | Representative sample |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | IB_VN_VI_Duy_Logistics | AI Rudder | 1 | 6.80 | 5.50 | 6.80 | Recalibrated | `03163f0a9a7f4aa1b23ccd457d1e6c6f.wav` |
| 2 | M1_L2_VN_VI_Nhi_Timo_M25 | AI Rudder | 1 | 6.00 | 4.80 | 6.00 | Recalibrated | `7fc6761420dc470d84d804fa732fa0a9.wav` |
| 3 | 竞品FPT | Competitors | 2 | 4.20 | 4.20 | 5.20 | Raw | `VN-D_2_竞品NLU-FPT.m4a` |

## TH

| Rank | Agent / robot | Source | Calls | Score used | Raw avg | Recal avg | Basis | Representative sample |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | TH_DAX_Thai_PTP100_Prod | AI Rudder | 1 | 5.50 | 5.00 | 5.50 | Recalibrated | `1da381b6d1614491b253fa6763ffae98.wav` |
| 2 | COD_TH_TH_Jan_KEX_M25_B | AI Rudder | 1 | 4.10 | 3.20 | 4.10 | Recalibrated | `60a92007151c49e4a4e8a3687626c8c4.wav` |
| 3 | 竞品Botnoi | Competitors | 1 | 3.50 | 3.50 | 4.70 | Raw | `TH-E_1_竞品LLM-Botnoi.m4a` |
| 4 | 竞品94 | Competitors | 2 | 2.35 | 2.35 | 3.15 | Raw | `TH-D_2_竞品LLM-94.wav` |

## PH

| Rank | Agent / robot | Source | Calls | Score used | Raw avg | Recal avg | Basis | Representative sample |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | M1_L2_PH_PH_The_360_DM2_High | AI Rudder | 1 | 4.20 | 2.80 | 4.20 | Recalibrated | `60e150657b62473bb37ef674f4b23e2a.wav` |
| 2 | M1_L2_PH_PH_360Kredi_Female | AI Rudder | 1 | 3.90 | 2.40 | 3.90 | Recalibrated | `2169614a155e4f7eb5ebf038a9f77614.wav` |
| 3 | 竞品WIZ | Competitors | 1 | 2.50 | 2.50 | 4.10 | Raw | `PH-D_1_竞品NLU-WIZ.m4a` |
