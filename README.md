<h1 align="center">火山方舟双通道模型供应商</h1>
<p align="center"><strong>让 AstrBot 的同一个主模型真正听懂 QQ 语音、看懂视频，同时把普通 API 与 Agent Plan 的计费通道彻底分开。</strong></p>

[![Version](https://img.shields.io/badge/version-0.1.30-2ea44f)](CHANGELOG.md)
[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.26.1-6b63ff)](https://github.com/AstrBotDevs/AstrBot)
[![Platform](https://img.shields.io/badge/platform-aiocqhttp-2f855a)](https://docs.astrbot.app/dev/star/plugin-new.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 你会得到什么

- **QQ 语音直接交给当前主模型**：Silk、AMR 等常见输入经 AstrBot 媒体解析后，由插件做火山 Chat 所需的最后一公里 WAV 规范化，再进入同一条主对话；不需要额外 STT 或第二个转录模型。
- **视频是模型卡原生能力项**：在火山 Ark / Agent Plan 的具体模型卡里，`文本 / 图像 / 音频 / 工具使用` 同层级会出现 `视频 / Video`。每张卡独立勾选、独立保存。
- **开关与运行行为一致**：当前火山模型卡包含 `modalities: video` 时，本轮受信视频附件才转换为火山 `video_url`；关闭后不会走视频转换链。
- **严格对象级隔离**：OpenAI、xAI、Gemini、DeepSeek 等 foreign 卡在共享 schema、served 资产、活动对话框、保存边界与落盘配置五个层面都不出现插件 Video 或 `volcengine_*` 行。
- **保留丰富模型卡设置**：0.1.19+ 的视频质量（压缩/原画）、思考模式、Reasoning Effort、Temperature、Top P、Max Output Tokens、Stop、Frequency/Presence Penalty 与 `custom_extra_body` 兼容入口继续保留。
- **普通 API / Agent Plan 计费隔离**：两条通道使用独立 Provider 类型、固定端点和独立密钥；插件内部不会把一条失败请求自动改发到另一条。
- **QQ 音视频失败时不装懂**：媒体解析或 Ark payload 组装失败会明确停止；本地传输失败不会被写成“模型永久不支持该能力”。
- **可卸载**：Dashboard/service 兼容桥与运行时索引桥都可逆，释放后恢复宿主原 callable，并清理插件临时 Dashboard 资产。

## 先认清两张供应商卡

| 类型 | 固定端点 | 密钥 | 模型名 |
| --- | --- | --- | --- |
| `volcengine_ark_chat_completion` | `https://ark.cn-beijing.volces.com/api/v3` | 普通方舟推理 API Key | 官方模型 ID 或接入点 ID |
| `volcengine_agent_plan_chat_completion` | `https://ark.cn-beijing.volces.com/api/plan/v3` | Agent Plan 专属 API Key | AstrBot 内显示为 `agentplan/...` |

Agent Plan 的 `agentplan/` 只是 AstrBot 本地命名空间，发送给火山前会自动移除。例如：

```text
AstrBot：agentplan/doubao-seed-2.1-turbo
                     │ 发送前移除本地前缀
                     ▼
火山方舟：doubao-seed-2.1-turbo
```

> **请留意 AstrBot 自己的全局 fallback。** 插件内部不跨通道回退，但如果你主动把普通方舟模型和 Agent Plan 模型混进 AstrBot 的 `fallback_chat_models`，宿主仍可以按你的全局配置切换。

## 安装

稳定运行包的明确安装来源是 `runtime` 分支：

1. 下载 [runtime.zip](https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider/archive/refs/heads/runtime.zip)。
2. 解压后，把其中唯一的插件目录放到 AstrBot `data/plugins/`；确认 `metadata.yaml` 与 `main.py` 位于插件根目录。
3. 完整关闭并重新启动 AstrBot。
4. 打开 `模型提供商`，确认能创建“火山方舟普通 API”和“火山方舟 Agent Plan API”。

> 不要把 `main` 分支仓库 ZIP 当成正式安装包。`main` 包含 CI、测试和设计资料；用户运行包来自经过验证的 `runtime` 分支。

最低兼容版本为 AstrBot `4.26.1`。

## 配置普通方舟 API

1. 新建 `volcengine_ark_chat_completion` Provider Source。
2. 填写普通方舟推理 API Key。
3. 在线获取模型列表，或手动填写官方模型 ID / 推理接入点 ID（如 `ep-...`）。
4. 新建或编辑**具体模型卡**。
5. 在模型卡原生“模型能力 / modalities”区域按实际需要勾选 `文本`、`图像`、`音频`、`工具使用`，以及本插件在当前火山卡提供的 `视频 / Video`。
6. 保存模型卡。关闭再打开编辑页后，Video 必须保持原值。

## 配置 Agent Plan

1. 新建 `volcengine_agent_plan_chat_completion` Provider Source。
2. 填写 **Agent Plan 专属 API Key**，不要填普通方舟或 Coding Plan Key。
3. 选择带 `agentplan/` 前缀的套餐模型，或手动填写新的官方 model-name。
4. 新建或编辑具体模型卡。
5. 需要视频时，仍然只在该模型卡原生能力区勾选 `视频 / Video`。

## 媒体输入上限与超限图片压缩（0.1.28+）

插件在 WebUI 的插件配置页提供一组可调媒体护栏，全部可改、可关：

| 配置项 | 默认 | 作用 |
| --- | --- | --- |
| `audio_max_mb` | 25 | 归一化后的 WAV 超过该值拒绝发送（范围 1-100） |
| `audio_transcode_timeout_seconds` | 120 | ffmpeg 音频转换墙钟上限（10-3600） |
| `video_max_mb` | 200 | 超过该值的视频附件拒绝发送（1-4096） |
| `video_transcode_timeout_seconds` | 300 | 压缩模式 ffmpeg 视频转码墙钟上限（30-7200） |
| `image_compress_enabled` | true | 超限图片自动降分辨率压缩到上限以内 |
| `image_max_mb` | 5 | 超过该值的图片触发压缩（1-100；火山方舟单图约 5MB 上限） |
| `image_compress_max_size` | 1280 | 压缩后最长边像素（256-8192） |
| `image_compress_quality` | 85 | 压缩 JPEG 质量（30-100）；仍超限时逐级降质重试 |

> 这些是**传输护栏**，不是模型能力结论。它们只负责在 Base64 膨胀前拒绝超大输入、或把超限图片压到火山可接受范围，避免请求被上游拒绝或无限挂起。

## 缓存命中强化（0.1.30+）

火山方舟对稳定前缀自动做隐式缓存计费：同一渠道、同一模型、对话头不变时，重复输入会按缓存命中打折计费。这个插件把缓存命中做成**可观测、可管理**的能力，仿照 DeepSeek Harness 的缓存诊断方式：

- **每次对话自动打缓存日志**：`[VolcengineCache] channel=plan/v3 model=... in=49988 cached=49152 (98.3%) uncached=836 out=387 rsn=214 ms=74219`。一眼看出输入多少、命中多少、命中率多高、输出了多少（含 reasoning token 与耗时）。
- **每 N 次汇总一条**：`[VolcengineCache:SUM] calls=10 in=... cached=... (x%) out=...`，默认每 10 次一条，方便按批次看趋势。
- **上下文错误不盲目丢历史**：上下文长度超限时，先按模型解析已知上限（deepseek-v4 系 / glm 系 → 1M，doubao / kimi / minimax → 256K），把诊断写进缓存日志再交给 AstrBot 重试。保持长对话前缀稳定，本身就是缓存高命中的前提。
- **WebUI 可关可调**：插件配置页的 `cache_log_enabled` 关闭日志，`cache_log_every` 调整汇总频率。

### 实验数据节选（真实运行）

以下来自 0.1.30 开发前 AstrBot 真实日志中的 33 条 `[VolcengineCache]` 记录：

| 渠道 | 模型 | 记录数 | 平均命中 | 加权命中 |
| --- | --- | --- | --- | --- |
| Agent Plan (`plan/v3`) | agentplan/ark-code-latest | 24 | 83.1% | 85.9% |
| 普通 API (`v3`) | 同一模型（含冷启动） | 6 | 37.2% | 43.3% |
| 图片说明 | doubao-seed-2-0-mini | 3 | 0% | 独立缓存域 |

- Agent Plan 渠道最近 6 条记录稳定在 **97.1%–97.9%**（如 `in=49988 cached=49152 (98.3%)`），说明主对话前缀稳定后命中率逼近隐式缓存上限。
- 普通 API 首轮冷启动（cached=0）会明显拉低平均，稳定后同样走高；图片说明走独立的 tiny 输入，缓存收益本就微不足道。
- 上下文治理同时生效：日志中出现 `[VolcengineCache] guard 128000 -> 1048576 (resolved model=deepseek-v4-flash-ga-260731)`，即模型解析把保守默认 128K 抬升到该模型的真实 1M 上限，避免长对话被截断、破坏前缀。

> 这些是真实计费命中的观测，不是估算：`cached` 来自上游响应 `prompt_tokens_details.cached_tokens`。命中率 = cached / (cached + uncached)。

## 多模态路径

### 图片

继续使用 AstrBot 原生图片能力。模型卡勾选“图像”后，本轮图片沿宿主原生 Chat Provider 路径进入当前模型。超大图片由 0.1.28+ 的自动压缩护栏按配置处理。

### QQ 语音

模型卡勾选“音频”后，QQ 语音走下面这条主模型路径：

```text
QQ Record
  → AstrBot audio_urls
  → AstrBot MediaResolver 解析 / 解码
  → 插件做 Ark Chat 最终 WAV 规范化
  → 16 kHz、单声道、16-bit PCM WAV
  → RIFF/WAVE 与 25 MB 上限校验
  → input_audio(data=<裸 Base64>, format="wav")
  → 当前主聊天模型
```

### 视频

模型卡勾选 `视频 / Video` 后，本次消息或本次引用中的**受信 AstrBot 视频附件**会转换为火山官方 `video_url` 内容块：

```text
当前模型卡 modalities 包含 video
  → AstrBot 本轮可信 Video Attachment
  → HTTP(S) / data URL 直接使用，或 MediaResolver 解析本地引用
  → video_url
  → 当前火山主模型
```

如果当前模型卡没有 `video`，则不执行视频读取/转换，请求中只保留 `[Video]` 占位。手动输入一个看起来像 `[Video Attachment: ...]` 的普通文本不会触发本地文件读取。

## 常见问题

### 获取模型列表很少

先确认你编辑的是普通方舟 Source，而不是 Agent Plan；普通通道会按当前普通推理 Key 在线读取 `/models`。凭据本身权限受限时，只会看到它实际可访问的模型。

### QQ 语音返回 `not of valid wav format`

确认版本至少为 `0.1.9`，并在替换插件目录后完整重启 AstrBot。当前版本会按真实媒体内容走 AstrBot resolver，并在发送前统一满足 Ark Chat WAV 约束。

### 模型没有看见视频

1. 打开**当前使用的那张火山模型卡**，不要去 Source 页面找视频总开关。
2. 确认模型卡原生能力区的 `视频 / Video` 已勾选并保存。
3. 关闭模型卡再重开，确认 Video 仍处于同一状态。
4. 完整重启 AstrBot 后重新加载 Dashboard，必要时硬刷新页面（Ctrl+F5）以放弃缓存的旧 bundle。
5. 确认视频属于本轮消息或本轮引用。
6. 再看 AstrBot 媒体日志；如果视频在形成 Provider 句柄之前已经失败，聊天 Provider 无法从普通文本反推出原视频。

### 火山模型卡没有 Video，但 OpenAI/Gemini 反而出现了 Video

这是**失败**而不是降级副作用：

- 确认实际安装的分支是 `runtime` 且 `metadata.yaml` 版本为 0.1.24 及以上；
- 查看插件启动日志中四个桥的状态：`dashboard_bridge`、`model_fields_bridge`、`dashboard_asset_wrapper`、`dashboard_runtime_index_bridge` 应均为 `active`；
- foreign 卡出现插件 Video 或 `volcengine_*` 行，或火山卡没有 Video，都应作为回归报告（QQ 群 916646029）。

### 明明选择 Agent Plan 却产生普通 API 调用

检查当前会话 Provider ID 和 AstrBot 全局 `fallback_chat_models`。插件不会跨通道回退，但宿主按用户配置的全局 fallback 仍有独立执行权。

## 隐私、日志与费用

插件不保存额外密钥副本，也不会把 Authorization Header、API Key、签名视频 URL 或音频 Base64 写入自己的持久日志。OpenAI SDK DEBUG 请求体中的视频 URL / 音频 Base64 有插件级脱敏过滤。

普通 API 与 Agent Plan 都可能产生真实费用。Agent Plan 受套餐与 AFP 规则约束；如果你在火山控制台开启超额后付费，套餐耗尽后仍可能产生账单。插件只保证自身两条固定端点不混线，不替你修改账户扣费策略。

## 官方资料

- [AstrBot 插件开发指南](https://docs.astrbot.app/dev/star/plugin-new.html)
- [火山方舟普通 Chat API](https://www.volcengine.com/docs/82379/1494384?lang=zh)
- [火山方舟音频理解](https://docs.volcengine.com/docs/82379/2377589?lang=zh)
- [火山方舟视频理解](https://www.volcengine.com/docs/82379/1895586?lang=zh)
- [Agent Plan 快速开始](https://www.volcengine.com/docs/82379/2373738?lang=zh)
- [Agent Plan 套餐概览](https://www.volcengine.com/docs/82379/2366394?lang=zh)
- [Agent Plan / Coding Plan 专用条款](https://www.volcengine.com/docs/82379/2278469?lang=zh)
- [火山方舟 Python SDK（Apache-2.0）](https://github.com/volcengine/volcengine-python-sdk)
- [火山方舟 Ark CLI](https://github.com/volcengine/ark-cli)

仓库地址：<https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider>
