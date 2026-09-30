# OneTTS uv 现代 Python 工具链与环境管理指南 (UV_GUIDE)

本文档系统性整理了在 OneTTS 项目开发及日常 Python 环境管理中，使用 **`uv`**（基于 Rust 构建的超高速 Python 包与环境管理器）的核心操作与标准工作流。

---

## 目录
- [一、OneTTS 纯 uv 极速开发标准工作流](#一onetts-纯-uv-极速开发标准工作流)
- [二、包与依赖管理 (`uv add` / `uv sync` / `uv run`)](#二包与依赖管理-uv-add--uv-sync--uv-run)
- [三、临时执行与 CLI 工具 (`uvx` / `uv tool`)](#三临时执行与-cli-工具-uvx--uv-tool)
- [四、Python 版本管理 (`uv python`)](#四python-版本管理-uv-python)

---

## 一、OneTTS 纯 uv 极速开发标准工作流

在已安装 `uv` 的开发机上，推荐采用全新的零激活直接执行工作流：

```bash
# 1. 克隆进入工程目录
cd OneTTS

# 2. 一键创建虚拟环境并锁定安装所有开发依赖
uv sync --extra dev

# 3. 极速启动 OneTTS 后端服务（免手动 source 激活）
uv run uvicorn server.main:app --host 0.0.0.0 --port 8030

# 4. 执行自动化单元测试
uv run pytest -m "not integration"

# 5. 执行 CLI 快速测试合成
uv run python cli/tts_cli.py "欢迎使用 OneTTS 语音合成引擎！" -v alloy -o test.mp3
```

---

## 二、包与依赖管理 (`uv add` / `uv sync` / `uv run`)

### 1. 新增/删除依赖
```bash
# 新增生产依赖（自动写入 pyproject.toml 并更新 uv.lock）
uv add edge-tts

# 新增开发/测试依赖
uv add --dev pytest-cov

# 移除依赖
uv remove edge-tts
```

### 2. 多机器环境对齐与复现
```bash
# 严格按照 uv.lock 确定性安装全部依赖（毫秒级）
uv sync --frozen --extra dev
```

### 3. 导出标准 requirements.txt
```bash
uv export --format requirements-txt --no-dev -o requirements.txt
```

---

## 三、临时执行与 CLI 工具 (`uvx` / `uv tool`)

### 1. 临时沙盒运行 (`uvx`)
无需安装到当前环境，临时拉取并执行：
```bash
# 免安装快速下载 HuggingFace 模型权重
uvx --from huggingface_hub hf download hexgrad/Kokoro-82M --local-dir ./data/models/
```

### 2. 全局独立环境工具 (`uv tool`)
```bash
# 全局安装 ruff 或 black 代码格式化工具
uv tool install ruff
ruff check server/
```

---

## 四、Python 版本管理 (`uv python`)

```bash
# 查看本地与已下载解释器
uv python list

# 一键下载安装 Python 3.12 官方纯净解释器
uv python install 3.12

# 固定当前项目使用 Python 3.12
uv python pin 3.12
```
