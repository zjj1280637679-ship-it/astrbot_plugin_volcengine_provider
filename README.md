<h1 align="center">火山方舟双通道模型供应商</h1>
<p align="center"><strong>让 AstrBot 的当前主模型直接处理 QQ 语音与视频，并把普通 Ark API 与 Agent Plan 两条计费通道彻底分开。</strong></p>

[![Version](https://img.shields.io/badge/version-0.1.34-2ea44f)](CHANGELOG.md)
[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.26.1-6b63ff)](https://github.com/AstrBotDevs/AstrBot)
[![Platform](https://img.shields.io/badge/platform-aiocqhttp-2f855a)](https://docs.astrbot.app/dev/star/plugin-new.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 当前发布状态

| 对象 | 状态 |
| --- | --- |
| 稳定版本 | **0.1.34**：默认分支恢复完整运行代码，并修复 AstrBot 4.27.4 模型卡 Video 消失 |
| 历史恢复基线 | **0.1.32**（旧 `runtime` 只作恢复证据，不再是安装源） |
| 0.1.33 | 默认分支发布身份存在，但运行文件不完整，已失效，不应继续安装 |
| 安装源 | 仅使用默认分支 `main` 的仓库根地址；AstrBot Cloud 市场收录仍需单独审核 |

机器可读的当前状态见 [`docs/PROJECT_STATE.json`](docs/PROJECT_STATE.json)。

## 功能

- **双通道 Provider**：普通火山方舟 `v3` 与 Agent Plan `plan/v3` 使用独立 Provider 类型、密钥和固定端点；插件不会把失败请求偷偷改发到另一条计费通道。
- **QQ 语音进入当前主模型**：AstrBot 解析媒体后，插件只做 Ark Chat 需要的 WAV 规范化，不要求额外配置 STT 或第二套对话模型。
- **单模型卡 Video**：只在火山 Ark / Agent Plan 的具体模型卡原生 `modalities` 区域显示 `视频 / Video`；OpenAI、Gemini、xAI、DeepSeek 等 foreign 卡保持干净。
- **视频请求跟随勾选状态**：只有当前火山模型卡包含 `video` 时，本轮或本轮引用中的可信视频附件才转换为 `video_url`。
- **媒体护栏**：音频、视频的大小/转码超时可配置；超限图片可自动压缩。
- **缓存命中观测**：提供 `[VolcengineCache]` 与 `[VolcengineCache:SUM]` 日志，观察上游 `cached_tokens` 和上下文溢出。

## 安装与更新

标准仓库地址：

`https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider`

完成 GitHub 合并并经 AstrBot Cloud 审核收录后，才可通过 AstrBot 插件市场安装；也可让 AstrBot 从上面的仓库根地址安装。默认分支 `main` 必须同时包含 `metadata.yaml`、`main.py`、`_conf_schema.json` 与全部运行模块。

不要使用旧的 `/tree/runtime` 地址；该分支只保留历史恢复证据，不接收新版本。

最低兼容 AstrBot `4.26.1`，当前声明范围为 `>=4.26.1`；本次实际回归覆盖 4.27.3 / 4.27.4，不以未经验证的未来版本为由增加硬拒载。插件依赖 AstrBot 自带的 `ffmpeg`、Pillow 和 OpenAI 适配层，不需要另建运行服务。

## 两张供应商卡

| 类型 | 固定端点 | 使用的凭据 |
| --- | --- | --- |
| `volcengine_ark_chat_completion` | `https://ark.cn-beijing.volces.com/api/v3` | 普通方舟推理 API Key |
| `volcengine_agent_plan_chat_completion` | `https://ark.cn-beijing.volces.com/api/plan/v3` | Agent Plan 专属 API Key |

Agent Plan 模型在 AstrBot 内可显示为 `agentplan/...`；发送到火山前会移除这个本地命名空间前缀。密钥由 AstrBot 的 Provider 配置管理，不要写进插件文件或 GitHub 仓库。

## 多模态行为

### 图片

继续使用 AstrBot 原生图片消息结构。超过 `image_max_mb` 的本地或 `data:` 图片可在请求前缩小并转换为 JPEG；远程 HTTP(S) 图片 URL 保持由 Ark 服务端拉取。

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
  → Original 或 Compressed 传输
  → video_url
  → 当前火山主模型
```

没有勾选 Video 时不会读取或转换附件。普通文本伪造的 `[Video Attachment: ...]` 不会触发本地文件读取。

## 插件配置

| 配置项 | 默认值 | 说明 |
| --- | ---: | --- |
| `audio_max_mb` | 25 | 归一化后音频输入上限 |
| `audio_transcode_timeout_seconds` | 120 | ffmpeg 音频转码墙钟上限 |
| `video_max_mb` | 200 | 视频输入与压缩结果上限 |
| `video_transcode_timeout_seconds` | 300 | Compressed 视频转码墙钟上限 |
| `image_compress_enabled` | true | 是否压缩超限图片 |
| `image_max_mb` | 5 | 单图压缩触发/目标上限 |
| `image_compress_max_size` | 1280 | 压缩后最长边像素 |
| `image_compress_quality` | 85 | 首轮 JPEG 质量 |
| `cache_log_enabled` | true | 是否记录缓存命中明细 |
| `cache_log_every` | 10 | 每 N 次请求记录汇总 |

这些值是本地传输护栏，不是模型能力数据库。模型是否实际接受某种输入，仍以对应模型、端点和账号的当前上游反馈为准。

## Video 验收合同

1. Ark 与 Agent Plan 的具体模型卡各出现且只出现一个 Video 选项。
2. foreign Provider 模型卡不出现插件 Video 或 `volcengine_*` 行。
3. 保存、关闭、重开以及 AstrBot 重启后，当前卡的 Video 状态保持。
4. 只有勾选 Video 的火山卡才生成 `video_url`。
5. 卸载插件并重启后，兼容桥和临时资产完整释放。

完整合同见 [`docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`](docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md)。

## 0.1.34

- 把 0.1.28—0.1.30 已发布但曾遗漏于默认分支的配置 schema、媒体限制、图片压缩、缓存观测代码完整收回 `main`。
- 兼容 AstrBot 4.27.3 与 4.27.4 的模型卡构建器，恢复火山模型卡原生 Video 选项。
- 保持对象级隔离、保存/重开、运行时开关和卸载恢复合同，不更改 Provider 固定端点或跨通道路由。
- 退役旧的双分支发布工具；默认 `main` 成为唯一安装与版本真值。

完整历史见 [`CHANGELOG.md`](CHANGELOG.md)。

## 官方资料

- [AstrBot 插件开发指南](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot 插件发布](https://docs.astrbot.app/dev/star/plugin-publish.html)
- [火山方舟普通 Chat API](https://www.volcengine.com/docs/82379/1494384?lang=zh)
- [火山方舟音频理解](https://docs.volcengine.com/docs/82379/2377589?lang=zh)
- [火山方舟视频理解](https://www.volcengine.com/docs/82379/1895586?lang=zh)
- [Agent Plan 快速开始](https://www.volcengine.com/docs/82379/2373738?lang=zh)

反馈 QQ 群：916646029
