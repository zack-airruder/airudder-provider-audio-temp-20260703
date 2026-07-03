# Scoring Criteria and Evaluation Basis

This note explains how the call scores are produced, what each scoring category means, and how the LLM arrives at the final result.

## Source of Truth

The evaluation uses the anthropomorphism scoring rubric in:

- `tools/anthropomorphism-analyzer/rubric.py`
- `tools/anthropomorphism-analyzer/analyzer.py`

The latest 32-call run artifacts are:

- `batch-anthropomorphism-final-32.json`
- `batch-anthropomorphism.csv`
- `full/*-report.json`

The scoring model for the latest run was `gemini-3.5-flash` through Zenlayer, with Deepgram used for STT and timing evidence.

## How One Call Is Scored

For each audio file, the evaluator follows this flow:

1. Analyze the waveform for objective signals.
   - Turn-taking gaps
   - Dead air
   - Overlaps
   - Latency before agent replies
   - Interruption behavior

2. Build an LLM prompt from the rubric.
   - The prompt includes the five scoring dimensions.
   - It includes what to listen for in each dimension.
   - It includes measured timing signals, and instructs the LLM to trust those signals for timing.

3. The LLM listens to the call and returns structured JSON.
   - `overall_score`
   - five dimension scores
   - strengths
   - weaknesses
   - timestamped evidence
   - recommended fixes
   - transcript with speaker labels and latency tags

4. The system validates and normalizes the result.
   - Missing dimension scores are flagged.
   - Scores are clamped to `0-10`.
   - If no `overall_score` is returned, weighted score is used as fallback.

## Prompt Structure Used For Scoring

The scoring prompt should be structured as follows:

```text
You are a senior conversational-voice QA analyst for an outbound AI voicebot platform.

You will LISTEN to a raw call recording and evaluate how ANTHROPOMORPHIC (human-like) the conversation is, using the 5-dimension Anthropomorphism Solutions framework.

When the conversation is AI-to-human, judge the AI agent.
When it is human-to-human, treat the human agent as the reference gold standard.

Work from the replay itself:
- prosody
- timing
- breathing
- overlaps
- silences
- emotion
- not just the words

Use measured waveform signals for timing/latency.

Score five dimensions:

1. Voice / Timbre

Evaluation basis:
- Is pronunciation clear?
- Does the voice sound natural or synthetic?
- Is the speaking rate too rushed?
- Are there natural pauses and breathing?
- Does pitch move naturally, or is it flat?
- Are there audio artifacts, clipping, abrupt cut-offs, or metallic tone?
- Does the voice persona fit the business scenario?

2. Opening

Evaluation basis:
- How fast does the robot speak after pickup?
- Is time-to-first-word under roughly 0.8s?
- Does it greet naturally?
- Does it confirm identity cleanly?
- Does it avoid dumping a long script immediately?
- Does it personalize the call with name, product, or context?
- If the customer is silent, does it recover naturally?

3. Speaking Style / Conversation Flow

Evaluation basis:
- Does the robot listen before continuing?
- Does it answer the customer's actual question?
- Does it avoid long monologues?
- Does it split long information into shorter turns?
- Does it echo-confirm important details such as amount, date, or promise-to-pay?
- Does it use natural transition words?
- Does it avoid repeating the same sentence or connector?
- Does it show empathy when the customer gives a reason, objection, or emotional response?

4. Latency / Reply Timing

Evaluation basis:
- How long does the robot wait before replying?
- Are simple confirmations fast enough?
- Are complex lookups masked with natural filler?
- Is there dead air?
- Does the robot recover after no-input silence?
- Are denials or refusals too instant and robotic?

5. Interrupt / Exception Handling

Evaluation basis:
- Does the robot stop when interrupted?
- Does it recover after false interruption?
- Does it use short hand-back tokens like "yes?" or "what happened?"
- Does it handle mishearing with a short reprompt?
- Does it avoid long apology loops?
- Does it handle angry or hostile customers properly?
- Does it recover from soft rejection?

For each dimension:
- give a 0-10 score
- give a rating
- list strengths
- list weaknesses
- provide timestamped evidence
- provide concrete advice

Return one JSON object only.
No markdown.
No commentary.
```

## Score Meaning

All scores are `0-10`.

| Score | Meaning |
|---:|---|
| 9-10 | Excellent, very human-like |
| 7-8 | Good, usable and natural in most moments |
| 5-6 | Fair, usable but clearly robotic in parts |
| 3-4 | Weak, many robotic or flow-breaking issues |
| 0-2 | Poor, broken or not suitable as a natural voicebot example |

Higher score means the robot sounds more human-like and handles the call more naturally.

## Scoring Categories and Weight Logic

Each scoring category is defined once below, together with its evaluation basis and why its weight is set that way. The weights add up to `100%`.

| Category | Weight | What it mainly decides |
|---|---:|---|
| Voice / Timbre | 15% | Whether the robot sounds acceptable and role-appropriate |
| Opening | 15% | Whether the call starts naturally and earns enough trust to continue |
| Speaking Style / Conversation Flow | 30% | Whether the robot can hold a real two-way conversation |
| Latency / Reply Timing | 20% | Whether the robot feels responsive in real time |
| Interrupt / Exception Handling | 20% | Whether the robot can recover when the call goes off-script |

### 1. Voice / Timbre: 15%

This measures how the robot voice itself sounds. It is important because poor pronunciation, robotic tone, or audio artifacts can damage trust immediately.

Evaluation basis:

- Is pronunciation clear?
- Does the voice sound natural or synthetic?
- Is the speaking rate too rushed?
- Are there natural pauses and breathing?
- Does pitch move naturally, or is it flat?
- Are there audio artifacts, clipping, abrupt cut-offs, or metallic tone?
- Does the voice persona fit the business scenario?

Weight logic:

Voice gets `15%` because it is an entry condition, not the whole conversation. If the voice is bad, the call suffers immediately. But once the voice is clear enough, the bigger performance difference comes from whether the robot listens, responds, and recovers. A good voice cannot save a robot that ignores the customer or repeats scripts.

### 2. Opening: 15%

This measures the first few seconds of the call. It matters because the opening affects whether the customer stays on the line and whether the robot sounds trustworthy at the start.

Evaluation basis:

- How fast does the robot speak after pickup?
- Is time-to-first-word under roughly `0.8s`?
- Does it greet naturally?
- Does it confirm identity cleanly?
- Does it avoid dumping a long script immediately?
- Does it personalize the call with name, product, or context?
- If the customer is silent, does the robot recover naturally?

Weight logic:

Opening gets `15%` because it is important but limited to the beginning of the call. A robot can open well and still fail later through dead air, repetition, poor objection handling, or weak interruption recovery. So it should matter, but it should not dominate the total score.

### 3. Speaking Style / Conversation Flow: 30%

This measures whether the robot can hold a real conversation instead of reading a broadcast script. It is the highest-weight category because it has the widest impact on naturalness, customer trust, and business outcome.

Evaluation basis:

- Does the robot listen before continuing?
- Does it answer the customer’s actual question?
- Does it avoid long monologues?
- Does it split long information into shorter turns?
- Does it echo-confirm important details such as amount, date, or promise-to-pay?
- Does it use natural transition words?
- Does it avoid repeating the same sentence or connector?
- Does it show empathy when the customer gives a reason, objection, or emotional response?

Weight logic:

Conversation flow gets `30%` because this is where most real call failures happen. A clear voice and good opening do not matter much if the robot ignores what the customer said, repeats the same offer, reads a 30-second monologue, or fails to answer the actual question. This category directly affects whether the call feels like a two-way interaction and whether the task can be completed.

### 4. Latency / Reply Timing: 20%

This measures the timing of replies, not speaking speed. It checks whether the robot responds at a natural pace and avoids awkward silence.

Evaluation basis:

- How long does the robot wait before replying?
- Are simple confirmations fast enough?
- Are complex lookups masked with natural filler?
- Is there dead air?
- Does the robot recover after no-input silence?
- Are denials or refusals too instant and robotic?

Timing expectations:

- Simple confirmation: around `0.5s`
- Standard Q&A: around `0.8-1.2s`
- Query/database lookup: can be longer, but should be masked
- Long silence with no filler is strongly penalized

Weight logic:

Reply timing gets `20%` because dead air is one of the clearest robot signals in a phone call. Customers cannot see the system thinking. If the robot stays silent too long, the customer may repeat themselves, interrupt, or hang up. It is weighted below conversation flow because timing alone does not prove understanding, but it is weighted above voice/opening because bad timing can break every turn.

### 5. Interrupt / Exception Handling: 20%

This measures how the robot handles messy real-world moments: interruption, silence, refusal, mishearing, anger, or unexpected answers.

Evaluation basis:

- Does the robot stop when interrupted?
- Does it recover after false interruption?
- Does it use short hand-back tokens like “yes?” or “what happened?”
- Does it handle mishearing with a short reprompt?
- Does it avoid long apology loops?
- Does it handle angry or hostile customers properly?
- Does it recover from soft rejection?

Weight logic:

Interrupt and exception handling gets `20%` because real calls rarely follow the perfect script. A bot that only works when the customer behaves exactly as expected may look fine in a clean demo but fail in production. This category is weighted the same as reply timing because both are live-call control problems: timing measures responsiveness, while exception handling measures recovery.

## Overall Score

The LLM returns a holistic `overall_score`.

The system also calculates a `weighted_score` from the five dimension scores:

| Dimension | Weight |
|---|---:|
| Voice / Timbre | 15% |
| Opening | 15% |
| Speaking Style / Conversation Flow | 30% |
| Latency / Reply Timing | 20% |
| Interrupt / Exception Handling | 20% |

If the LLM does not return a valid `overall_score`, the system falls back to the weighted score.

## What Evidence the LLM Must Provide

For each dimension, the LLM must provide:

- Numeric score
- Rating
- Strengths
- Weaknesses
- Timestamped evidence
- Advice tied to the framework

Evidence should include:

- Timestamp
- Speaker
- Original quote
- English translation for non-English calls
- Explanation of why the moment matters

This is why the score should not be treated as a blind number. Each score is expected to be backed by call evidence.

## Important Guardrails

- Use the latest scoring run consistently across AI Rudder and competitor calls.
- Do not let one high sample represent an entire multi-call robot unless the report says it is the best sample.
- If an agent has multiple calls, show:
  - number of calls
  - average score
  - representative audio sample
- Use `Reply Timing` instead of `Speed`.
- Keep source labels clear: `AI Rudder` vs `Competitors`.

## Practical Report Recommendation

For the next HTML report, use these columns:

| Column | Meaning |
|---|---|
| Region | Market/locale |
| Agent / Robot | Robot name |
| Source | AI Rudder or Competitor |
| Calls | Number of evaluated call examples |
| Average Score | Average score for that agent/robot |
| Best Sample Score | Highest-scoring call example for that agent/robot |
| Representative Audio | Playable sample for that agent |

This makes the scoring method auditable and prevents the Dyna-style confusion from happening again.
