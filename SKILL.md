---
name: local-audio-transcription
description: Locally transcribe audio with faster-whisper for three scenarios. Use for Chinese personal monologues that need faithful expression of the user's views and reasoning; Japanese dialogue, especially student/teacher discussions, that needs bilingual transcription, chronological Chinese reconstruction, feedback and action items; and Japanese single-speaker lectures that need bilingual transcription and study notes. Supports local m4a, mp3, wav, and aac files.
---

# Local Audio Transcription

Keep speech recognition local. Never upload audio to a cloud speech-to-text service unless the user explicitly approves that upload. Model or dependency downloads may use the network but do not upload the audio.

## Select a mode

- Use `zh-monologue` for the user's all-Chinese personal monologue expressing views and ideas. Deliver a faithful readable transcript and a Chinese summary of the views and reasoning.
- Use `ja-dialogue` for Japanese dialogue, especially conversations with a teacher. Deliver the Japanese transcript, Chinese translation, and a detailed chronological reconstruction in Chinese.
- Use `ja-lecture` for Japanese single-speaker exposition, especially class recordings. Deliver a chronological Japanese transcript with Chinese translation, followed by thematic study notes. Preserve brief classroom questions and answers within this mode; use `ja-dialogue` when the recording is primarily an exchange.
- Use `auto` only when the scenario is unknown. Infer language from the transcript, then use the user's context and conversational structure to choose the delivery contract. Japanese language alone does not distinguish a dialogue from a lecture.

Do not ask the user to choose a mode when their request already makes it clear.

## Run the local transcription

1. Resolve the user-provided audio path with `-LiteralPath` when using PowerShell. Keep the source file untouched.
2. Prefer the existing interpreter at `E:\chat\.venv-whisper\Scripts\python.exe` when present; otherwise locate a Python environment containing `faster-whisper`.
3. Run the bundled script directly on the original file. It inspects the source, creates a temporary ASCII-path PCM WAV, splits it at exact frame boundaries, selects CPU/GPU automatically, and writes uniquely named raw outputs. If automatic CUDA selection fails during model initialization or lazy segment iteration, let the script discard any partial GPU result and restart once with CPU `int8`.

Chinese monologue:

```powershell
& 'E:\chat\.venv-whisper\Scripts\python.exe' '<skill-dir>\scripts\transcribe_local.py' --audio '<audio-path>' --out-dir '<output-dir>' --mode zh-monologue --model medium
```

Japanese dialogue:

```powershell
& 'E:\chat\.venv-whisper\Scripts\python.exe' '<skill-dir>\scripts\transcribe_local.py' --audio '<audio-path>' --out-dir '<output-dir>' --mode ja-dialogue --model medium
```

Use `small` only for a fast draft. For important or difficult audio, prefer `medium`; retry only unclear sections with a larger available model if the added time is justified. Pass expected names and specialist terms with `--initial-prompt`. Use `--word-timestamps` only when fine-grained alignment is needed. VAD is enabled by default to suppress silence hallucinations; retry with `--no-vad` if genuinely quiet speech appears to be missing.

Japanese lecture:

```powershell
& 'E:\chat\.venv-whisper\Scripts\python.exe' '<skill-dir>\scripts\transcribe_local.py' --audio '<audio-path>' --out-dir '<output-dir>' --mode ja-lecture --model medium
```

The script generates timestamped raw transcription and metadata only. Produce the translation, reconstruction, summary, or study notes separately according to the selected delivery contract.

If installation or model download needs network access, explain that only dependencies/model files are downloaded. Do not claim the whole workflow is offline when Codex later processes the transcript: the audio stays local, while transcript text may be handled by the current Codex service unless a local text model is used.

## Preserve evidence

Treat the generated `.txt` and `.json` as immutable raw evidence. Never replace them with a cleaned version. Save the interpreted result as a separate Markdown file beside them and link both raw and interpreted outputs.

Use timestamps to check suspicious passages. Mark uncertain words as `[听不清]`, `[可能是：…]`, or `[需确认]`. Never silently invent missing speech or “correct” a term merely because it sounds plausible.

Do not claim true speaker diarization. Infer roles only from greetings, turn-taking, content, honorifics, and context. Label uncertain assignments as `我（推断）` / `老师（推断）`; if evidence is insufficient, use `说话者A` / `说话者B`.

## Delivery contract: Chinese monologue

Create `<run-name>_中文整理.md` containing:

1. `内容概述` — a compact explanation of what the recording is about.
2. `完整整理稿` — a readable, faithful transcript in the original order; remove filler only when meaning is unchanged.
3. `要点与结论` — key views, their reasons, explicit conclusions and decisions; include `待办事项` when actions were stated.
4. `不确定内容` — timestamped unclear or potentially misrecognized passages.

Do not summarize away important details. If the recording is short, include the entire cleaned transcript before the summary.

Preserve the user's voice, stance, reservations, uncertainty, and meaningful self-corrections. Do not turn tentative ideas into firm conclusions or add arguments and opinions the user never expressed. Remove only filler and repetitions whose removal leaves the meaning unchanged; substantial rewriting requires a separate user request.

## Delivery contract: Japanese dialogue

Create `<run-name>_日文对话中文还原.md`. The goal is to let the user reconstruct the conversation in Chinese, not merely understand its topic. Include:

1. `对话背景与结果` — participants, topic, outcome, and unresolved questions.
2. `详细聊天过程（中文还原）` — chronological, turn-by-turn Chinese reconstruction. Preserve questions, answers, corrections, examples, reservations, changes of mind, and transitions. Keep enough detail that the user could retell the conversation in Chinese.
3. `日中对照转写` — timestamp, inferred speaker, corrected Japanese, and faithful Chinese translation for each meaningful turn. Merge only adjacent fragments from the same turn; do not over-compress.
4. `老师的意见` — requests, criticism, advice, evaluation, and expected next steps, separated from the user's own statements.
5. `决定、待办与待确认` — explicit decisions, action items, deadlines if stated, and unresolved points.
6. `听不清或角色不确定处` — timestamps and alternative interpretations.

Translate meaning faithfully rather than polishing it into advice that was never said. Keep important Japanese terms in parentheses after the Chinese translation when terminology matters.

## Delivery contract: Japanese lecture

Create `<run-name>_日文课堂中文整理.md`. The goal is to understand the class, review its content, and find passages for replay. Include:

1. `课程概述` — the topic and scope; include course, lecturer, and date only when supported by the recording or user-provided context.
2. `按授课顺序的日中对照转写` — timestamp, Japanese transcript, and faithful Chinese translation for each meaningful passage. Preserve definitions, reasoning steps, examples, qualifications, corrections, and brief classroom questions and answers. Split long lectures at topic transitions without replacing the complete content with notes.
3. `分主题课堂笔记` — organize the concepts, explanations, reasoning, and examples for review. Distinguish what the teacher said from your own synthesis; keep any supplementary explanation explicitly separate from recorded content.
4. `术语与老师强调的重点` — Japanese terms with Chinese equivalents and timestamped definitions or examples; label a point as teacher-emphasized only when the recording supports it. Do not invent exam predictions.
5. `作业、安排与待确认` — assignments, deadlines, readings, and unresolved questions only when stated; if none were stated, say so.
6. `听不清或理解不确定处` — timestamps, uncertain wording or interpretation, and alternatives when justified.

Preserve important formulas, conditions, units, numbers, and distinctions. Do not reconstruct an unseen slide, diagram, or board formula from a vague reference; mark the missing visual context. For brief questions and answers, distinguish turns and mark inferred roles rather than treating all speech as the lecturer's.

## Quality loop

Before delivery:

- Compare the summary or translation against the raw timestamped transcript.
- Check that negation, numbers, dates, names, thesis/research terms, and who requested what are preserved.
- For Chinese monologues, check that the user's stance and degree of certainty have not changed. For lectures, check definitions, reasoning, examples, formulas, assignments, and that teacher statements remain distinguishable from study-note synthesis.
- Retranscribe only suspect time ranges when language detection, silence hallucination, or terminology is unreliable.
- State whether role labels are inferred and whether any material section remains uncertain.

## Failure handling

- If `ffmpeg`, `ffprobe`, `faster-whisper`, or a model is missing, report the missing component precisely and offer to install/download it.
- If CUDA is detected but a runtime library such as `cublas64_12.dll` is missing, allow automatic CPU fallback. If an older script still fails, rerun explicitly with `--device cpu --compute-type int8`.
- If a model download is blocked by network restrictions, request approval for the download and clarify that the audio is not uploaded.
- If no audio file was supplied or its path cannot be resolved, ask for the file/path instead of guessing.
