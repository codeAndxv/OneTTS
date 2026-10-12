# OneTTS: 双轨 API 架构与专属高级扩展体系规范白皮书

本文档定义了 **OneTTS** 语音合成统一网关的完整 API 架构体系。系统采用**双轨接口设计原则**，全局由 `/v1/` 统一版本命名空间收敛管理。

---

## 目录

1. [设计理念与双轨原则](#1-设计理念与双轨原则)
2. [全局版本命名空间与鉴权规范](#2-全局版本命名空间与鉴权规范)
3. [轨道一：OpenAI 标准兼容体系 (/v1/audio/...)](#3-轨道一openai-标准兼容体系-v1audio)
   - [3.1 POST /v1/audio/speech (标准合成)](#31-post-v1audiospeech-标准合成)
   - [3.2 GET /v1/models 与 GET /v1/audio/voices](#32-get-v1models-与-get-v1audiovoices)
   - [3.3 隐式透传与优雅降级规则](#33-隐式透传与优雅降级规则)
4. [轨道二：OneTTS 专属高级扩展体系 (/v1/tts/...)](#4-轨道二onetts-专属高级扩展体系-v1tts)
   - [4.1 POST /v1/tts/generate (高级结构化合成 & 同步字幕)](#41-post-v1ttsgenerate-高级结构化合成--同步字幕)
   - [4.2 异步长文演播与多角色剧本任务 (/v1/tts/tasks)](#42-异步长文演播与多角色剧本任务-v1ttstasks)
   - [4.3 声音克隆与专属声音资产库 (/v1/tts/clones)](#43-声音克隆与专属声音资产库-v1ttsclones)
   - [4.4 WebSocket 全双工实时流式推流 (/v1/tts/realtime)](#44-websocket-全双工实时流式推流-v1ttsrealtime)
5. [底层引擎架构重构 (BaseTTSEngine & TTSContext)](#5-底层引擎架构重构-basettsengine--ttscontext)
6. [数据持久化表结构设计 (ORM)](#6-数据持久化表结构设计-orm)

---

## 1. 设计理念与双轨原则

OneTTS 的核心使命是成为 AI 工作流（如 DuRT 桌面客户端、剪辑工作流、长文小说演播）与通用 Agent 体系的**语音合成中枢底座**。为了兼顾三方生态的通用兼容性与专业多媒体工作流的深度能力，系统划分为两条清晰的 API 轨道：

```
                                  OneTTS Gateway (:8020)
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
          【轨道一：OpenAI 兼容轨】                      【轨道二：OneTTS 专属扩展轨】
          前缀: /v1/audio/..., /v1/models               前缀: /v1/tts/...
          面向: Dify, NextChat, Open-WebUI              面向: DuRT 桌面端、长篇小说、视频剪辑
          特点: 100% 遵守官方规范，直出音频              特点: 支持字幕生成、声音克隆、长文任务、实时流
```

---

## 2. 全局版本命名空间与鉴权规范

### 2.1 统一基址 (Base URL)
所有 API 严格归一在 `/v1` 命名空间下。客户端配置 Base URL 统一定义为：
```text
http://<host>:<port>/v1
```

### 2.2 统一鉴权
所有端点均支持双通道 API Key 校验：
- **Header 方式 A**：`Authorization: Bearer <api_key>`
- **Header 方式 B**：`X-API-Key: <api_key>`

---

## 3. 轨道一：OpenAI 标准兼容体系 (`/v1/audio/...`)

面向第三方生态客户端，保证零改动无缝接入。

### 3.1 `POST /v1/audio/speech`
OpenAI 官方标准接口。

#### 请求体 (JSON)
| 字段 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `model` | string | 是 | `edgetts` | 模型名称或 Provider（如 `tts-1`, `edgetts`, `kokoro`） |
| `input` | string | 是 | - | 待朗读文本，最大 8192 字符 |
| `voice` | string | 否 | `alloy` | 发音人名称或别名（如 `alloy`, `zh-CN-XiaoxiaoNeural`） |
| `response_format`| string | 否 | `mp3` | 输出编码格式：`mp3`, `opus`, `aac`, `flac`, `wav`, `pcm` |
| `speed` | float | 否 | `1.0` | 语速倍率，范围 `0.25` ~ `4.0` |
| `stream` | bool | 否 | `false` | 是否开启 HTTP Chunked 数据流边生成边吐出音频 |

#### 响应
- HTTP 200，`Content-Type: audio/mpeg`（根据 `response_format` 返回对应 MIME 类型），响应体为纯音频二进制流。

### 3.2 辅助标准查询端点
- **`GET /v1/models`**：符合 OpenAI 标准的数据模型列表。
- **`GET /v1/audio/voices`**：当前系统中所有可用的发音人列表与对应语言。
- **`GET /v1/providers`**：所有 TTS Provider 运行状态与健康度（对齐 OneASR）。

### 3.3 隐式透传与优雅降级规则
若高级第三方客户端在 `POST /v1/audio/speech` 中额外携带了扩展字段（如 `prompt_audio`, `language`, `emotion`），OneTTS 会在后端自动提取并尝试生效，绝不会因为多余字段抛出 Pydantic 校验错误（Extra fields allowed）。

---

## 4. 轨道二：OneTTS 专属高级扩展体系 (`/v1/tts/...`)

专为专业多媒体工作流、桌面端 `DuRT`、字幕生成与长文演播定制。

### 4.1 `POST /v1/tts/generate` (高级结构化合成 & 同步字幕)

在一次请求中，同时获取高质量音频与**精准对齐的字幕数据（SRT/VTT/时间戳数组）**。

#### 请求体 (JSON)
```json
{
  "model": "edgetts",
  "text": "新年的第一天我的班是夜班。这是我第一次上夜班，为了防止上班出错，我一直在不停地问我的夜班同事一些问题。",
  "voice": "zh-CN-XiaoxiaoNeural",
  "response_format": "mp3",
  "speed": 1.0,
  "pitch": 0.0,
  "volume": 1.0,
  "language": "zh",
  "emotion": "neutral",
  "prompt_audio": null,
  "prompt_text": null,
  "clone_voice_id": null,
  "with_subtitles": true,
  "output_mode": "json"
}
```

#### 参数明细
| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `text` | string | 必填 | 待合成文本内容 |
| `voice` | string | `alloy` | 预设音色、别名或自定义克隆音色 ID |
| `speed` | float | `1.0` | 语速微调 (0.25 ~ 4.0) |
| `pitch` | float | `0.0` | 音高微调百分比 (-50.0 ~ +50.0，如 +10 代表升调 10%) |
| `volume` | float | `1.0` | 音量倍率 (0.1 ~ 2.0) |
| `language` | string | `auto` | 明确指定语种（`zh`, `en`, `ja`, `yue` 等），防止多语言模型误判 |
| `emotion` | string | `neutral` | 情感风格（`happy`, `sad`, `angry`, `whisper`, `storytelling` 等） |
| `prompt_audio` | string | null | 临时零样本克隆参考音频（URL 或 Base64 编码二进制） |
| `prompt_text` | string | null | 参考音频对应的台词文本 |
| `clone_voice_id`| string | null | 引用已在音色库注册的持久化克隆声音 ID |
| `with_subtitles`| bool | `true` | 是否生成句级/词级时间戳与 SRT 字幕 |
| `output_mode` | string | `json` | `json` 返回含 Base64 音频与字幕元数据；`audio` 直接返回纯音频二进制（字幕写入 Header） |

#### 结构化 JSON 响应示例 (`output_mode: "json"`)
```json
{
  "audio_base64": "//uQxAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AA...",
  "audio_format": "mp3",
  "audio_duration_seconds": 9.45,
  "sample_rate": 24000,
  "subtitles": [
    {
      "index": 1,
      "text": "新年的第一天我的班是夜班。",
      "start_time": "00:00:00,000",
      "end_time": "00:00:02,850",
      "start_seconds": 0.0,
      "end_seconds": 2.85
    },
    {
      "index": 2,
      "text": "这是我第一次上夜班，为了防止上班出错，",
      "start_time": "00:00:02,950",
      "end_time": "00:00:05,900",
      "start_seconds": 2.95,
      "end_seconds": 5.90
    },
    {
      "index": 3,
      "text": "我一直在不停地问我的夜班同事一些问题。",
      "start_time": "00:00:06,000",
      "end_time": "00:00:09,450",
      "start_seconds": 6.0,
      "end_seconds": 9.45
    }
  ],
  "srt_content": "1\n00:00:00,000 --> 00:00:02,850\n新年的第一天我的班是夜班。\n\n2\n00:00:02,950 --> 00:00:05,900\n这是我第一次上夜班，为了防止上班出错，\n\n3\n00:00:06,000 --> 00:00:09,450\n我一直在不停地问我的夜班同事一些问题。\n",
  "vtt_content": "WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.850\n新年的第一天我的班是夜班。\n\n..."
}
```

---

### 4.2 异步长文演播与多角色剧本任务 (`/v1/tts/tasks`)

专为上万字小说、长文报道、分角色广播剧打造的异步任务系统。

#### 1. 创建异步任务：`POST /v1/tts/tasks`
支持单篇超长文本模式，或多角色剧本数组模式：
```json
{
  "title": "三体第一章演播",
  "model": "edgetts",
  "default_voice": "zh-CN-YunxiNeural",
  "response_format": "mp3",
  "with_subtitles": true,
  "dialogue": [
    { "speaker": "旁白", "voice": "zh-CN-YunxiNeural", "text": "汪淼觉得，纳米中心周围的世界有些不对劲。" },
    { "speaker": "申玉菲", "voice": "zh-CN-XiaoxiaoNeural", "text": "倒计时到零以后，会发生什么？" },
    { "speaker": "汪淼", "voice": "zh-CN-YunjianNeural", "text": "不知道，也许是我自己的心跳停止吧。" }
  ],
  "webhook_url": "https://example.com/api/tts/callback"
}
```
**响应**：
```json
{
  "task_id": "tts_task_9a7b2c8e1f",
  "status": "pending",
  "message": "Task queued successfully",
  "created_at": 1728710400
}
```

#### 2. 查询任务列表：`GET /v1/tts/tasks`
- 支持 Query 参数：`status` (`pending`, `running`, `completed`, `failed`), `page`, `page_size`。

#### 3. 查询任务详情与进度：`GET /v1/tts/tasks/{id}`
**响应**：
```json
{
  "task_id": "tts_task_9a7b2c8e1f",
  "title": "三体第一章演播",
  "status": "running",
  "progress": 66.7,
  "total_segments": 3,
  "completed_segments": 2,
  "duration_seconds": 18.5,
  "error_message": null,
  "created_at": 1728710400,
  "updated_at": 1728710408
}
```

#### 4. 取消任务：`POST /v1/tts/tasks/{id}/cancel`
- 立即终止后台队列中排队或执行中的切片，释放显存与算力。

#### 5. 产物打包下载：`GET /v1/tts/tasks/{id}/download`
- Query 参数：`format` (`audio` 单纯完整合并音频, `zip` 包含音频 + 配套 `.srt` + `.vtt` 的压缩包)。

---

### 4.3 声音克隆与专属声音资产库 (`/v1/tts/clones`)

将常用的零样本克隆参考音频沉淀为持久化资产，避免重复上传。

#### 1. 注册专属克隆声音：`POST /v1/tts/clones`
- **Content-Type**: `multipart/form-data`
- **表单字段**：
  - `name`: 专属声音名称（如“老杜播客原音”）
  - `description`: 描述说明
  - `prompt_text`: 录音中的台词文本（重要：用于音素对其）
  - `audio_file`: 5~15 秒无杂音清晰人声 WAV/MP3 文件
  - `language`: 音频母语（`zh`, `en`, 等）
**响应**：
```json
{
  "clone_voice_id": "clone_dudu_001",
  "name": "老杜播客原音",
  "language": "zh",
  "sample_url": "/v1/tts/clones/clone_dudu_001/sample",
  "created_at": 1728710500
}
```

#### 2. 获取克隆声音列表：`GET /v1/tts/clones`
- 返回当前数据库中已注册的所有克隆声音资产。

#### 3. 删除克隆声音：`DELETE /v1/tts/clones/{id}`
- 删除数据库记录并清理底层的声学特征与样本缓存。

#### 4. 试听样本：`GET /v1/tts/clones/{id}/sample`
- 试听注册时上传的原始音频。

---

### 4.4 WebSocket 全双工实时流式推流 (`/v1/tts/realtime`)

专为大模型全双工语音 Agent 打造，实现首包延迟 < 200ms 的实时语音流。

#### 1. 连接地址
`ws://<host>:<port>/v1/tts/realtime?api_key=...&voice=zh-CN-XiaoxiaoNeural&format=pcm`

#### 2. 客户端向服务端发送的事件 (JSON)
- **增量文本注入**：
  ```json
  { "type": "text.append", "delta": "您好，很高兴为您服务！" }
  ```
- **强制句尾提交（即刻冲刷）**：
  ```json
  { "type": "text.flush" }
  ```
- **用户打断（Barge-in / Cancel）**：
  ```json
  { "type": "interrupt" }
  ```
  服务端收到后立即丢弃未发出的音频缓冲区，并暂停当前生成。

#### 3. 服务端向客户端返回的事件
- **音频帧推流 (Binary 或 JSON Base64)**：
  ```json
  { "type": "audio.delta", "delta_base64": "...", "format": "pcm", "sample_rate": 24000 }
  ```
- **句子与时间轴事件**：
  ```json
  { "type": "sentence.start", "text": "您好，很高兴为您服务！", "timestamp_ms": 0 }
  { "type": "sentence.end", "timestamp_ms": 1850 }
  ```

---

## 5. 底层引擎架构重构 (BaseTTSEngine & TTSContext)

为了原生支持上述双轨 API，底层引擎适配器需由简单的纯文本传参升级为携带统一上下文对象的规范：

```python
@dataclass
class TTSContext:
    """统一语音合成上下文参数包。"""
    text: str
    voice: str
    speed: float = 1.0
    pitch: float = 0.0
    volume: float = 1.0
    language: str | None = None
    emotion: str | None = None
    prompt_audio_bytes: bytes | None = None
    prompt_text: str | None = None
    with_subtitles: bool = False
    response_format: str = "mp3"
```

各引擎各取所需：
- `EdgeTTSEngine`：利用 SSML 动态拼接 `<prosody pitch="+10%" rate="+0%" volume="+0%">` 与 `<express-as style="...">`；
- `KokoroEngine`：利用指定 language 代码加载不同的 Phoneme G2P 模块；
- `CosyVoiceEngine`：加载 `prompt_audio_bytes` 提取 Flow Matching 声学提示嵌入。

---

## 6. 数据持久化表结构设计 (ORM)

通过 SQLite/SQLAlchemy 新增两张核心数据表：

### 6.1 `tts_tasks` 表 (异步任务持久化)
- `id` (VARCHAR PK): 任务唯一 ID（如 `tts_task_...`）
- `title` (VARCHAR): 任务标题
- `model` (VARCHAR): 所用模型
- `voice` (VARCHAR): 默认音色
- `status` (VARCHAR): `pending` / `running` / `completed` / `failed` / `cancelled`
- `progress` (FLOAT): 0.0 ~ 100.0
- `dialogue_json` (TEXT): 剧本与多角色段落 JSON
- `audio_path` (VARCHAR): 合并后的成品音频路径
- `srt_path` (VARCHAR): 配套生成的字幕文件路径
- `duration_seconds` (FLOAT): 成品时长
- `error_message` (TEXT): 错误原因
- `created_at`, `updated_at`: 时间戳

### 6.2 `voice_clones` 表 (声音克隆资产持久化)
- `id` (VARCHAR PK): 唯一 ID（如 `clone_...`）
- `name` (VARCHAR): 音色名称
- `description` (TEXT): 说明
- `language` (VARCHAR): 语种
- `prompt_text` (TEXT): 参考音频台词
- `audio_path` (VARCHAR): 样本音频存储路径
- `created_at`: 创建时间

---

至此，OneTTS 的双轨 API 架构规范已全景式固化完毕，指导后续代码的分步落地。
