# OneTTS: 统一多引擎语音合成 (TTS) 聚合服务

OneTTS 是一个开箱即用、高性能的语音合成 (Text-to-Speech) 引擎聚合网关与服务。它原生兼容 **OpenAI `/v1/audio/speech`** 接口协议，并支持多款开源与商业级 TTS 后端插件式接入。

---

## ✨ 核心特性

- **完全兼容 OpenAI 协议**：无缝替代 `/v1/audio/speech`、`/v1/models` 以及 `/v1/audio/voices`，零改动接入 Dify、FastGPT、DuRT、Open WebUI 等生态。
- **多引擎无缝聚合**：
  - **Edge-TTS**：内置开箱即用，零显卡/零算力消耗，覆盖微软 Azure 优质中英日韩及方言音色。
  - **Kokoro-82M**：超轻量 ONNX 本地神经网络发音引擎。
  - **OpenAI 代理**：支持转发与中继官方或第三方兼容 TTS 服务。
- **极速低延迟流式响应**：智能句子切片与 HTTP Chunked 流式传输，首字音频延迟（TTFT）$< \mathbf{200ms}$。
- **智能 MD5 音频缓存**：重复请求秒级命中本地缓存，节省计算资源与带宽。
- **开箱即用容器编排**：提供 CPU 与 GPU 双版本 Dockerfile 与 docker-compose 一键启动。

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd OneTTS

# 使用 uv 一键创建环境并安装所有依赖（含开发/测试依赖）
uv sync --extra dev
```

### 2. 启动服务

```bash
# 使用 uv run 免激活极速启动
uv run uvicorn server.main:app --host 0.0.0.0 --port 8030
```

服务默认运行在 `http://localhost:8030`，访问 `http://localhost:8030/docs` 查看交互式 API 文档。

### 3. 运行测试

```bash
uv run pytest
```

---

## 📡 API 调用示例

### 文本朗读 / 语音合成

```bash
curl http://localhost:8030/v1/audio/speech \
  -H "Authorization: Bearer sk-onetts-v1-k9L3mX8QZ2sT4vA7wE1rY6u" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "欢迎使用 OneTTS 统一语音合成引擎！",
    "voice": "alloy",
    "response_format": "mp3"
  }' \
  --output speech.mp3
```

### 查询可用音色列表

```bash
curl http://localhost:8030/v1/audio/voices \
  -H "Authorization: Bearer sk-onetts-v1-k9L3mX8QZ2sT4vA7wE1rY6u"
```

---

## 🐳 Docker 部署

```bash
# 使用 Docker Compose 一键启动
docker compose up -d
```
