# Local Audio Transcription Skill

一个面向 Codex 的本地音频转写 skill，使用 `faster-whisper` 在用户机器上完成语音识别，并针对中文用户提供两种主要工作模式：

- 中文独白：完整转写、可读整理、内容总结、要点与待办。
- 日文对话：日文转写、中文翻译、详细聊天过程、老师意见、决定与待办。

它特别适合个人语音记录、毕业设计讨论、研究指导、课堂录音和师生面谈。

## 主要特点

- 音频识别在本机运行，不依赖云端语音识别 API。
- 支持 `.m4a`、`.mp3`、`.wav`、`.aac` 等常见格式。
- 自动检查音频格式、时长、采样率和声道。
- 自动转换为临时的 16 kHz 单声道 PCM WAV，不修改原始音频。
- 按准确的音频帧分段，避免长录音时间戳逐渐漂移。
- 自动选择 CPU 或 NVIDIA GPU；GPU 初始化或首次转写失败时，从头回退到 CPU `int8`。
- 默认使用 VAD 过滤静音幻听，可为音量很小的录音关闭 VAD。
- 每次生成唯一文件名，不覆盖以前的转写结果。
- 原始转写与 AI 整理稿分开保存，方便复查。

## 仓库结构

推荐使用下面的发布结构，让仓库文档与可安装 skill 保持分离：

```text
repository-root/
├── README.md
└── skill/
    └── local-audio-transcription/
        ├── SKILL.md
        ├── agents/
        │   └── openai.yaml
        └── scripts/
            └── transcribe_local.py
```

安装时只需要复制 `skill/local-audio-transcription` 目录，不需要把仓库的 README 一起复制到 Codex skills 目录。

## 环境要求

- Python 3.10 或更高版本
- `ffmpeg` 和 `ffprobe`
- `faster-whisper`
- 可选：支持 CUDA 的 NVIDIA GPU

首次使用某个 Whisper 模型时通常需要联网下载模型文件。模型下载不会上传音频。

## 安装依赖

### Windows PowerShell

```powershell
python -m venv .venv-whisper
& '.\.venv-whisper\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv-whisper\Scripts\python.exe' -m pip install faster-whisper
```

安装 `ffmpeg` 后，确保下面两个命令能在终端中找到：

```powershell
Get-Command ffmpeg, ffprobe
```

### macOS 或 Linux

```bash
python3 -m venv .venv-whisper
source .venv-whisper/bin/activate
python -m pip install --upgrade pip
python -m pip install faster-whisper
```

请同时通过系统包管理器安装 `ffmpeg`。

## 安装到 Codex

克隆或下载本仓库后，将 skill 目录复制到个人 Codex skills 目录。

Windows：

```powershell
Copy-Item -Recurse -LiteralPath '.\skill\local-audio-transcription' -Destination "$env:USERPROFILE\.codex\skills\local-audio-transcription"
```

macOS 或 Linux：

```bash
cp -R ./skill/local-audio-transcription ~/.codex/skills/local-audio-transcription
```

重新打开 Codex 任务后，可以通过 `$local-audio-transcription` 显式调用，也可以直接用自然语言描述音频任务。

## 普通用户怎么使用

把音频文件附加到任务中，或提供本地文件路径，然后直接说出你的需求。

### 场景一：中文独白

```text
这是我自己说的中文录音，请帮我转写并总结。
```

也可以提出更具体的要求：

```text
帮我完整转写这段中文录音，整理成通顺的文字，再总结主要观点和待办事项。听不清的地方不要猜，请标出时间。
```

预期得到：

1. 内容概述
2. 完整整理稿
3. 要点与结论
4. 待办事项
5. 带时间戳的不确定内容

### 场景二：日文师生对话

```text
这是我和老师的日文对话，请转写并翻译成中文，详细告诉我聊天过程，让我可以用中文把这段对话还原出来。
```

预期得到：

1. 对话背景与最终结果
2. 按时间顺序展开的详细中文还原
3. 带时间戳和说话者的日中对照转写
4. 老师提出的意见、批评和建议
5. 已经决定的事项、下一步任务和待确认问题
6. 听不清或说话者无法确定的部分

这里的目标不是只给一段简短摘要，而是保留问题、回答、纠正、举例、态度变化和行动安排，使用户能够用中文重新讲述整段对话。

## 手动运行转写脚本

Codex 通常会自动运行脚本。需要调试或单独使用转写器时，也可以手动执行。

### 中文独白

```powershell
& '.\.venv-whisper\Scripts\python.exe' `
  '.\skill\local-audio-transcription\scripts\transcribe_local.py' `
  --audio 'D:\audio\my-note.m4a' `
  --out-dir 'D:\audio\output' `
  --mode zh-monologue `
  --model medium
```

### 日文对话

```powershell
& '.\.venv-whisper\Scripts\python.exe' `
  '.\skill\local-audio-transcription\scripts\transcribe_local.py' `
  --audio 'D:\audio\teacher-meeting.m4a' `
  --out-dir 'D:\audio\output' `
  --mode ja-dialogue `
  --model medium
```

常用参数：

| 参数 | 作用 |
|---|---|
| `--mode zh-monologue` | 固定按中文独白识别 |
| `--mode ja-dialogue` | 固定按日文对话识别 |
| `--model small` | 更快的草稿转写 |
| `--model medium` | 更适合重要的中文或日文录音 |
| `--initial-prompt "姓名, 专业术语"` | 提示可能出现的人名和术语 |
| `--word-timestamps` | 输出词级时间戳 |
| `--no-vad` | 保留很轻的声音；也可能增加静音幻听 |
| `--device cpu` | 强制使用 CPU |
| `--device cuda` | 强制使用 NVIDIA GPU |
| `--inspect-only` | 只检查音频，不加载 Whisper 模型 |

自动模式检测到 NVIDIA GPU、但 CUDA 运行库不完整时，脚本会丢弃可能存在的部分 GPU 结果，并从头使用 CPU `int8` 重跑。需要完全规避 GPU 探测时，可直接添加：

```text
--device cpu --compute-type int8
```

## 输出文件

转写脚本会生成两个不会被后续整理覆盖的原始文件：

```text
<audio>_<mode>_<timestamp>.txt
<audio>_<mode>_<timestamp>.json
```

- `.txt`：适合阅读的带时间戳原始转写。
- `.json`：音频信息、运行参数、语言检测、分段信息、置信度和原始片段。

AI 应另外生成整理结果：

```text
<run-name>_中文整理.md
<run-name>_日文对话中文还原.md
```

不要用整理稿覆盖 `.txt` 或 `.json` 原始证据。

## 如果你是 AI：应该怎么做

当用户提供音频并要求转写、总结或翻译时，按以下协议执行。

### 1. 判断模式

- 用户自己的全中文录音：使用 `zh-monologue`。
- 用户与老师的日文对话：使用 `ja-dialogue`。
- 用户已经说清楚场景时，不要再次要求其选择模式。
- 场景确实不明时才使用 `auto`，并根据识别结果决定交付格式。

### 2. 保证音频隐私

- 优先使用本地 `faster-whisper`。
- 未经用户明确同意，不得把音频上传到云端语音识别服务。
- 如果需要下载 Python 包或 Whisper 模型，说明这是下载依赖或模型，不是上传音频。
- 不要把“音频本地识别”夸大成“整个流程完全离线”：如果使用在线 AI 做总结和翻译，转写文字仍可能由当前 AI 服务处理。

### 3. 检查并转写

1. 确认文件存在并可读取。
2. 检查格式、时长、采样率、声道和音频流。
3. 保留原文件，让脚本在临时目录中完成标准化。
4. 根据场景运行：

```powershell
& '<python-with-faster-whisper>' `
  '<skill-dir>\scripts\transcribe_local.py' `
  --audio '<audio-path>' `
  --out-dir '<output-dir>' `
  --mode '<zh-monologue-or-ja-dialogue>' `
  --model medium
```

5. 如果已知姓名或专业术语，使用 `--initial-prompt`。
6. 只对可疑时间段重新识别，不要无理由重复处理整段长音频。

### 4. 保留原始证据

- 把生成的 `.txt` 和 `.json` 视为不可修改的原始结果。
- 整理、纠错、翻译和总结写到新的 Markdown 文件。
- 所有重要纠正必须能够回到时间戳核验。
- 听不清时写 `[听不清]`；可能听成某词时写 `[可能是：……]`；需要用户核实时写 `[需确认]`。
- 不得为了让文字更通顺而编造录音中不存在的内容。

### 5. 中文独白的交付格式

至少包含：

1. `内容概述`
2. `完整整理稿`
3. `要点与结论`
4. `待办事项`（录音中存在时）
5. `不确定内容`

整理时可以去除不影响意思的口头填充词，但必须保留原本的观点、因果关系、否定、数字、日期和要求。短录音应优先完整呈现整理稿，再给摘要。

### 6. 日文对话的交付格式

至少包含：

1. `对话背景与结果`
2. `详细聊天过程（中文还原）`
3. `日中对照转写`
4. `老师的意见`
5. `决定、待办与待确认`
6. `听不清或角色不确定处`

详细聊天过程必须按时间顺序保留双方的提问、回答、纠正、举例、保留意见、结论和话题转换。不要把一段较长的讨论压缩成几句泛泛总结。

日中对照建议采用以下格式：

| 时间 | 说话者 | 日文转写 | 中文翻译 |
|---|---|---|---|
| 00:00–00:12 | 我（推断） | …… | …… |
| 00:12–00:28 | 老师（推断） | …… | …… |

翻译应忠实表达原意。重要专业词可以在中文后保留日文原词，不得把原本没有说过的建议添加到老师名下。

### 7. 谨慎处理说话者

本 skill 默认不做严格的声纹分离。AI 只能根据称呼、敬语、内容、轮次和上下文推断角色。

- 判断较明确时：使用 `我（推断）`、`老师（推断）`。
- 证据不足时：使用 `说话者A`、`说话者B`。
- 不得声称已经进行了真实的声纹识别或精确 diarization。

### 8. 交付前复核

重点核对：

- 否定词是否丢失；
- 数字、日期、人数和截止时间是否准确；
- 人名、研究术语和专有名词是否可能误识别；
- 谁提出了什么要求；
- 老师的意见与用户自己的想法是否混淆；
- 中文还原是否包含足够细节；
- 不确定内容是否已经明确标注。

最后同时链接原始转写文件和整理后的 Markdown 文件，并说明角色标签是否为推断、是否仍有重要片段无法确认。

## 隐私说明

语音识别阶段在本机执行，脚本不会主动将音频发送到云端转写 API。但需要注意：

- 首次安装依赖或下载模型需要联网。
- 使用 Codex 或其他在线 AI 做总结、整理和翻译时，转写文字可能由相应 AI 服务处理。
- 如需完全本地处理，应使用本地文本模型完成转写后的总结和翻译。
- 请勿将包含隐私的录音、原始转写或模型缓存提交到公开 Git 仓库。

## 已知限制

- 转写准确率受口音、语速、背景噪声、麦克风距离和多人重叠说话影响。
- 中文和日文混合讲话可能需要对困难片段分别指定语言重新识别。
- 角色区分是上下文推断，不是真实声纹 diarization。
- 脚本负责本地转写；中文总结和日文翻译由调用它的 AI 或其他文本处理工具完成。
- Whisper 的原始输出只能视为草稿，重要谈话仍应结合时间戳复查。

## 常见问题

### 为什么第一次运行比较慢？

首次使用会下载并加载 Whisper 模型。CPU 上的 `medium` 模型也可能需要较长时间。

### 为什么提示缺少 `cublas64_12.dll`？

系统可能检测到了 NVIDIA GPU，但没有安装与当前 CTranslate2 兼容的 CUDA 运行库。新版脚本会在 GPU 初始化或实际转写阶段失败后自动从头改用 CPU `int8`。如果仍需手动处理，请添加 `--device cpu --compute-type int8`。

### 为什么静音处出现了重复文字？

这通常是语音识别幻听。当前脚本默认开启 VAD。如果录音仍包含长时间静音，可核对这些片段并删除确认无声的结果。

### 为什么安静的讲话没有被识别？

尝试使用 `--no-vad` 重新识别对应时间段，同时注意检查可能增加的静音幻听。

### 能否准确区分我和老师？

不能保证。本 skill 默认根据语境推断角色，不执行严格的声纹识别。

### 可以完全离线吗？

模型和依赖下载完成后，语音识别可以离线运行。若总结与翻译由在线 AI 完成，转写文字的后处理则不是完全离线。

## 实机验证

已使用一段 128.6793 秒的中文单人 MP3 完成真实验证：

- 模型：`medium`
- 设备：CPU
- 计算类型：`int8`
- 识别结果：4 个带时间戳片段
- 交付结果：原始 `.txt`、元数据 `.json` 与独立中文整理稿均正常生成

同一环境能够发现 NVIDIA GPU，但因缺少 `cublas64_12.dll` 无法执行 CUDA 推理；显式 CPU `int8` 已验证可以稳定完成。该反馈促成了整段转写级别的自动 CPU 回退，而不再只处理模型初始化失败。

## 发布前建议

公开发布前，请确认仓库没有包含：

- `.venv-whisper/`
- Whisper 模型缓存
- 用户录音
- 原始转写结果
- 临时 WAV 文件
- 含个人信息的测试数据

建议为仓库选择明确的开源许可证，并在提交前添加适当的 `.gitignore`。
