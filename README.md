<h1 align="center">火山方舟双通道模型供应商</h1>
<p align="center"><strong>让 AstrBot 的同一个主模型直接处理 QQ 语音与视频，同时把普通 API 与 Agent Plan 两条计费通道分开。</strong></p>

[![Version](https://img.shields.io/badge/version-0.1.32-2ea44f)](CHANGELOG.md)
[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.26.1-6b63ff)](https://github.com/AstrBotDevs/AstrBot)
[![Platform](https://img.shields.io/badge/platform-aiocqhttp-2f855a)](https://docs.astrbot.app/dev/star/plugin-new.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 当前状态（先看这里）

| 对象 | 当前结论 |
|---|---|
| 你可以安装的稳定版 | **0.1.32**；`main` 与 `runtime` 的版本身份已统一 |
| 活跃发布候选 | **无**；0.1.32 是 0.1.31 紧急恢复后的版本事实对账版 |
| 0.1.32 主要变化 | 修复 `main`、`runtime`、README 与 HOT 状态之间的版本漂移；不改变 Provider、模型卡、音视频协议或请求语义 |
| AstrBot 商场 | 最后人工观察仍显示 **0.1.30**；等待中央索引刷新到 0.1.32 |

机器与维护者读取的唯一当前状态是 [`docs/PROJECT_STATE.json`](docs/PROJECT_STATE.json)。任何涉及 Video、`modalities`、Provider Source 或模型卡 UI 的修改，都必须同时遵守 [`docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`](docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md)。

## 功能

- **双通道 Provider**：普通火山方舟 `v3` 与 Agent Plan `plan/v3` 使用独立 Provider 类型、密钥和固定端点，不在插件内部互相回退。
- **QQ 语音进入当前主模型**：AstrBot 解析媒体后，插件只做 Ark Chat 所需的最终 WAV 规范化，不额外引入 STT 模型。
- **视频属于单模型卡原生能力**：只在火山 Ark / Agent Plan 的具体模型卡上提供 `视频 / Video`；OpenAI、Gemini、DeepSeek 等 foreign 卡不应出现插件 Video 或 `volcengine_*` 字段。
- **媒体护栏**：音频、视频与图片都有可配置大小/超时限制；超限图片支持自动压缩。
- **缓存命中观测**：0.1.30+ 提供 `[VolcengineCache]` 与 `[VolcengineCache:SUM]` 日志，便于观察稳定前缀带来的缓存收益。

## 两张供应商卡

| 类型 | 固定端点 | 密钥 |
| --- | --- | --- |
| `volcengine_ark_chat_completion` | `https://ark.cn-beijing.volces.com/api/v3` | 普通方舟推理 API Key |
| `volcengine_agent_plan_chat_completion` | `https://ark.cn-beijing.volces.com/api/plan/v3` | Agent Plan 专属 API Key |

Agent Plan 模型在 AstrBot 内可显示为 `agentplan/...`；发送到火山前会移除这个本地命名空间前缀。

## 安装

稳定安装源始终是 `runtime`：

1. 下载 `https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider/archive/refs/heads/runtime.zip`。
2. 解压后把唯一插件目录放入 AstrBot `data/plugins/`。
3. 确认插件根目录里存在 `metadata.yaml` 与 `main.py`。
4. 完整重启 AstrBot。
5. 打开模型提供商，确认可以创建“火山方舟普通 API”和“火山方舟 Agent Plan API”。

不要把 `main` 分支 ZIP 当作正式运行包；`main` 包含 CI、测试与设计资料，用户运行包来自 `runtime`。

最低兼容 AstrBot `4.26.1`。

## 多模态行为

### 图片

继续使用 AstrBot 原生图片能力。超过 `image_max_mb` 的图片可按插件配置自动压缩。

### QQ 语音

```text
QQ Record
  → AstrBot MediaResolver
  → 插件最终 WAV 规范化
  → input_audio(data=<裸 Base64>, format="wav")
  → 当前火山主模型
```

### 视频

```text
当前火山模型卡 modalities 包含 video
  → 本轮可信 Video Attachment
  → video_url
  → 当前火山主模型
```

没有勾选 `video` 时不会读取/转换视频；普通文本伪造的 `[Video Attachment: ...]` 不会触发本地文件读取。

## 媒体护栏

| 配置项 | 默认 |
| --- | --- |
| `audio_max_mb` | 25 MB |
| `audio_transcode_timeout_seconds` | 120 s |
| `video_max_mb` | 200 MB |
| `video_transcode_timeout_seconds` | 300 s |
| `image_max_mb` | 5 MB |
| `image_compress_max_size` | 1280 px |
| `image_compress_quality` | 85 |

这些是传输护栏，不是模型能力真值。

## Video 验收

1. Ark / Agent Plan 的具体模型卡原生能力区出现 Video。
2. foreign Provider 模型卡不出现插件 Video 或 `volcengine_*` 行。
3. 保存、关闭、重开后 Video 状态保持。
4. 只有勾选 Video 的火山卡才生成 `video_url`。
5. 卸载插件后兼容桥和临时资产可以完整释放。

完整合同见 [`docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`](docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md)。

## 版本说明

- **0.1.30**：缓存命中观测与上下文治理收编进插件。
- **0.1.31**：将已验证的 0.1.30 runtime 作为紧急恢复版本，仅提升版本身份，没有功能代码变化。
- **0.1.32**：统一 `main` / `runtime` / README / HOT 状态的版本事实，修复商店与自动化读取不同版本的问题；不改变运行语义。

更完整历史见 [`CHANGELOG.md`](CHANGELOG.md) 与 `docs/archive/`。

## 官方资料

- [AstrBot 插件开发指南](https://docs.astrbot.app/dev/star/plugin-new.html)
- [火山方舟普通 Chat API](https://www.volcengine.com/docs/82379/1494384?lang=zh)
- [火山方舟音频理解](https://docs.volcengine.com/docs/82379/2377589?lang=zh)
- [火山方舟视频理解](https://www.volcengine.com/docs/82379/1895586?lang=zh)
- [Agent Plan 快速开始](https://www.volcengine.com/docs/82379/2373738?lang=zh)

仓库地址：<https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider>
