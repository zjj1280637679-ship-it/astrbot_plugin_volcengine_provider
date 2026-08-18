<h1 align="center">火山方舟双通道模型供应商</h1>
<p align="center"><strong>普通 Ark API 与 Agent Plan 两条计费通道互不混线；同一个主模型直接处理文本、图片、QQ 语音与受信视频。</strong></p>

[![Version](https://img.shields.io/badge/version-0.1.31_candidate-orange)](CHANGELOG.md)
[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.26.1-6b63ff)](https://github.com/AstrBotDevs/AstrBot)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 当前状态

| 对象 | 当前结论 |
|---|---|
| 你可以安装的稳定版 | **0.1.30**；安装源为 `runtime` 分支 |
| 活跃发布候选 | **0.1.31**；正在把 0.1.28–0.1.30 的 runtime 直改重新收编进 main 的正规发布链，并修复已确认回归 |
| 0.1.31 修复范围 | main/runtime 重新单向收敛；图片压缩最长边真正生效并 fail-closed；缓存耗时覆盖整次请求；缓存汇总按 channel+model 分桶；已知模型上下文上限真正写入 AstrBot `max_context_tokens`；运行包重新包含 `_conf_schema.json` 与 README |
| 外部分发 | AstrBot 商场刷新、真实 Windows/Launcher 重装仍属于外部观察项，不由仓库 CI 代替 |

机器与维护者读取的唯一当前状态是 [`docs/PROJECT_STATE.json`](docs/PROJECT_STATE.json)。
任何涉及 Video / `modalities` / Provider Source / 模型卡 UI 的修改，继续遵守
[`docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`](docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md)。

> **不要安装当前 0.1.31 候选分支。** 用户安装仍使用 `runtime`；候选通过完整门禁并由发布器晋升后，`runtime` 才会更新。

## 两张供应商卡

| 类型 | 固定端点 | 密钥 | 模型名 |
|---|---|---|---|
| `volcengine_ark_chat_completion` | `https://ark.cn-beijing.volces.com/api/v3` | 普通方舟推理 API Key | 官方模型 ID / 接入点 ID |
| `volcengine_agent_plan_chat_completion` | `https://ark.cn-beijing.volces.com/api/plan/v3` | Agent Plan 专属 API Key | AstrBot 内显示为 `agentplan/...` |

插件内部不会把普通 API 的失败请求自动改发到 Agent Plan，反之亦然。若你把两类模型主动混进 AstrBot
`fallback_chat_models`，那属于宿主全局 fallback 行为。

Agent Plan 的 `agentplan/` 只是 AstrBot 本地命名空间，发送给火山前会自动移除。

## 核心能力

- **图片**：沿 AstrBot 原生图片链进入当前主模型。超过插件图片字节上限时才进入压缩路径；进入后输出必须同时满足字节上限与最长边目标，否则请求停止，不发送超限图片。
- **QQ 语音**：由 AstrBot MediaResolver 解析后，插件最终规范化为 16 kHz / 单声道 / PCM16 WAV，再作为 Ark `input_audio` 交给当前主模型。
- **视频**：`视频 / Video` 仍是单模型卡原生 capability。只有当前火山模型卡的 `modalities` 包含 `video` 时，本轮受信附件才转换为 `video_url`。
- **严格对象级隔离**：OpenAI、xAI、Gemini、DeepSeek 等 foreign 模型卡不出现插件 Video 或 `volcengine_*` 私有行。
- **逐模型请求设置**：保留视频质量、Thinking Mode、Reasoning Effort、Temperature、Top P、Max Output Tokens、Stop、Frequency/Presence Penalty 与 `custom_extra_body`。
- **媒体护栏**：音频/视频大小与转码超时、超限图片压缩参数均由插件配置控制。
- **缓存观测**：从上游 `usage.prompt_tokens_details.cached_tokens` 记录真实命中；每次请求一条明细，每 N 次按 `channel + model` 独立汇总。
- **上下文提示**：对已知模型族，在 Provider 初始化时写入 `max_context_tokens`，从而真正影响 AstrBot 主 Agent 的上下文 guard；用户显式配置的正值优先，未知模型继续由 AstrBot fallback 管理。

## 安装稳定版

稳定安装源始终是 `runtime`：

```text
https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider/tree/runtime
```

下载 `runtime` 分支 ZIP，解压后把唯一插件目录放到 AstrBot `data/plugins/`，然后完整重启 AstrBot。

不要把 `main` 仓库 ZIP 当成用户安装包。`main` 包含测试、CI、合同和开发资料；正式运行包由 allow-list 生成并通过门禁后晋升到 `runtime`。

## 插件配置

`_conf_schema.json` 随运行包分发，WebUI 可配置：

| 配置项 | 默认 | 作用 |
|---|---:|---|
| `audio_max_mb` | 25 | 归一化 WAV 上限 |
| `audio_transcode_timeout_seconds` | 120 | 音频 ffmpeg 墙钟上限 |
| `video_max_mb` | 200 | 本地视频输入上限 |
| `video_transcode_timeout_seconds` | 300 | 压缩视频 ffmpeg 墙钟上限 |
| `image_compress_enabled` | true | 超限图片自动压缩 |
| `image_max_mb` | 5 | 图片触发压缩的字节上限 |
| `image_compress_max_size` | 1280 | 压缩后最长边目标 |
| `image_compress_quality` | 85 | JPEG 初始质量 |
| `cache_log_enabled` | true | 缓存命中日志开关 |
| `cache_log_every` | 10 | 每 N 次按 channel+model 汇总 |

这些配置是**传输与观测策略**，不是永久模型能力真值。

## 上下文与缓存

0.1.31 不再在“已经超限以后”只打印一个更大的数字。

对于已知模型族，插件在 Provider 构造阶段设置 AstrBot 真正读取的 `provider_config["max_context_tokens"]`：

- `deepseek-v4*`、`glm-5*`、`glm-4*` → 1,048,576
- `doubao*`、`kimi*`、`minimax*` → 262,144
- 未知模型 / `ep-*` → 不猜，继续使用 AstrBot 自己的 fallback 或用户显式配置

若上游在已设置提示后仍返回 context-length error，插件只记录诊断，历史缩减与 retry 仍由 AstrBot 原生策略负责。

缓存日志中的 `ms` 从 0.1.31 起覆盖 `_query` / `_query_stream` 的完整请求生命周期，而不是只统计 completion 对象解析耗时。

## 视频模型卡合同

Video 的产品真值仍然只有一个：

```text
当前具体模型卡 modalities 是否包含 video
```

不是 Provider Source 总开关，不是共享 schema 全局注入，也不是隐藏字段替代品。

合同同时要求：

1. Ark / Agent Plan 正确模型卡出现 Video；
2. foreign 卡不出现；
3. 保存重开保持；
4. 运行行为与当前卡选择一致；
5. 插件释放后公共界面与宿主 callable 无残留。

## 失败边界

- 本地媒体解析、压缩、转码或序列化失败：fail closed，不伪装成“模型不支持”。
- 远程 HTTP(S) 视频：保持 Ark 服务端拉取语义，本地无法预知文件大小。
- 超限图片：一旦进入压缩链，若无法同时满足字节上限与最长边要求，停止本轮请求。
- 上下文模型族未知：不猜上限。
- 两条火山通道：不跨通道静默回退。

## 开发与发布

开发真值必须在 `main`；`runtime` 只能由发布器从 main 的 allow-list 运行包生成。

0.1.31 的修复目标就是恢复这一单向关系：

```text
main
  → Runtime Distribution Gate
  → immutable candidate
  → native install matrix
  → exact leased promotion
  → runtime
```

任何再次直接在 `runtime` 上开发而不回灌 main 的做法都视为发布拓扑回归。
