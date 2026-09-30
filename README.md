# OneTTS: Unified Text-to-Speech (TTS) Aggregation Service

<p align="center">
  <img src="./docs/assets/OneTTS.svg" width="128" alt="OneTTS Logo">
</p>

OneTTS is an enterprise-grade, high-performance Text-to-Speech (TTS) engine aggregation gateway. It provides full compatibility with the **OpenAI `/v1/audio/speech`** standard while supporting multiple pluggable open-source and commercial TTS backends.

[中文文档](README_CN.md)

---

## ✨ Features

- **OpenAI Standard Compatibility**: Drop-in replacement for `/v1/audio/speech`, `/v1/models`, and `/v1/audio/voices`.
- **Multi-Engine Aggregation**:
  - **Edge-TTS**: Built-in, zero-GPU required, hundreds of Microsoft Azure Neural voices out-of-the-box.
  - **Kokoro-82M**: Ultra-lightweight, high-speed ONNX local neural voice synthesis.
  - **OpenAI Relay**: Forward requests to OpenAI or third-party compatible TTS APIs.
- **Ultra-Low Latency Streaming**: Pipeline text chunking & HTTP Chunked audio streaming for sub-200ms TTFT (Time-To-First-Audio).
- **Intelligent Audio Caching**: MD5 parameter hashing to eliminate redundant computations.
- **Zero-Friction Deployment**: Pre-built Docker CPU & GPU images with Docker Compose.

---

## 🚀 Quick Start

### 1. Installation

```bash
cd OneTTS

# Create virtual environment and install dependencies using uv
uv sync --extra dev
```

### 2. Start the Server

```bash
# Instant start with uv run
uv run uvicorn server.main:app --host 0.0.0.0 --port 8030
```

The service will be live at `http://localhost:8030`. Interactive Swagger docs available at `http://localhost:8030/docs`.

### 3. Run Tests

```bash
uv run pytest
```

---

## 📡 API Usage Example

### Speech Synthesis (OpenAI Format)

```bash
curl http://localhost:8030/v1/audio/speech \
  -H "Authorization: Bearer sk-onetts-v1-k9L3mX8QZ2sT4vA7wE1rY6u" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Welcome to OneTTS unified speech synthesis service!",
    "voice": "alloy",
    "response_format": "mp3"
  }' \
  --output speech.mp3
```

### List Voices

```bash
curl http://localhost:8030/v1/audio/voices \
  -H "Authorization: Bearer sk-onetts-v1-k9L3mX8QZ2sT4vA7wE1rY6u"
```

---

## 🐳 Docker Deployment

```bash
# Start with Docker Compose
docker compose up -d
```

---

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.
