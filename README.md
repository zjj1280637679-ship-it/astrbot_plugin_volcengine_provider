<h1 align="center">火山方舟双通道模型供应商</h1>
<p align="center"><strong>普通 Ark API 与 Agent Plan 两条计费通道互不混线；同一个主模型直接处理文本、图片、QQ 语音与受信视频。</strong></p>

[![Version](https://img.shields.io/badge/version-0.1.31_candidate-orange)](CHANGELOG.md)
[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.26.1-6b63ff)](https://github.com/AstrBotDevs/AstrBot)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 0.1.31 发布迁移

0.1.31 用来把 0.1.28–0.1.30 曾直接落在 `runtime` 的功能重新收编进 `main → Gate → Publisher → runtime` 正规链，并修复这批改动里已经确认的回归。发布状态的机器真值只看 [`docs/PROJECT_STATE.json`](docs/PROJECT_STATE.json)。

### 候选验证阶段

| 对象 | 状态 |
|---|---|
| 你可以安装的稳定版 | **0.1.30**；用户继续安装 `runtime` |
| 活跃发布候选 | **0.1.31**；候选分支只用于验证，不作为用户安装源 |

### 完整门禁通过并由发布器晋升后的收敛状态

| 对象 | 状态 |
|---|---|
| 你可以安装的稳定版 | **0.1.31**；只有 `runtime` 被精确晋升后这一行才成立 |
| 活跃发布候选 | **无**；发布后的 HOT 状态归位只改开发资料，不再改运行包 README |

0.1.31 的修复范围：main/runtime 重新单向收敛；图片压缩最长边真正生效并在 Base64 膨胀前执行；音频转码输出先做 stat 上限检查再读入；缓存耗时覆盖整次请求、汇总按 channel+model 分桶；插件配置热重载后重建现有火山 Provider；上下文治理从“按模型名猜能力”改为**前反馈 → 请求 → 后反馈 → 下一次前反馈**的证据闭环；运行包重新包含 `_conf_schema.json` 与 README。

任何涉及 Video / `modalities` / Provider Source / 模型卡 UI 的修改，继续遵守 [`docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`](docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md)。

> 在 0.1.31 尚未由发布器晋升时，不要安装候选分支。用户安装源始终是 `runtime`。

## 两张供应商卡

| 类型 | 固定端点 | 密钥 | 模型名 |
|---|---|---|---|
| `volcengine_ark_chat_completion` | `https://ark.cn-beijing.volces.com/api/v3` | 普通方舟推理 API Key | 官方模型 ID / 接入点 ID |
| `volcengine_agent_plan_chat_completion` | `https://ark.cn-beijing.volces.com/api/plan/v3` | Agent Plan 专属 API Key | AstrBot 内显示为 `agentplan/...` |

插件内部不会把普通 API 的失败请求自动改发到 Agent Plan，反之亦然。若你把两类模型主动混进 AstrBot `fallback_chat_models`，那属于宿主全局 fallback 行为。

Agent Plan 的 `agentplan/` 只是 AstrBot 本地命名空间，发送给火山前会自动移除。

## 核心能力

- **图片**：插件接管火山 Provider 的图片 materialize 节点。超限本地/远端图片在原始字节变成 Base64 前直接从物化文件压缩；透明图转 JPEG 时以白底合成。压缩结果必须同时满足字节上限与最长边目标，否则请求停止。
- **QQ 语音**：由 AstrBot MediaResolver 解析后，插件最终规范化为 16 kHz / 单声道 / PCM16 WAV；转码结果先检查文件大小，再读取和 Base64。
- **视频**：`视频 / Video` 仍是单模型卡原生 capability。只有当前火山模型卡的 `modalities` 包含 `video` 时，本轮受信附件才转换为 `video_url`。
- **严格对象级隔离**：OpenAI、xAI、Gemini、DeepSeek 等 foreign 模型卡不出现插件 Video 或 `volcengine_*` 私有行。
- **逐模型请求设置**：保留视频质量、Thinking Mode、Reasoning Effort、Temperature、Top P、Max Output Tokens、Stop、Frequency/Presence Penalty 与 `custom_extra_body`。
- **媒体护栏**：音频/视频大小与转码超时、超限图片压缩参数均由插件配置控制。
- **缓存观测**：从上游 `usage.prompt_tokens_details.cached_tokens` 记录真实命中；每次请求一条明细，每 N 次按 `channel + model` 独立汇总。观测策略改变时旧汇总桶清零，避免跨生命周期混样本。
- **反馈驱动上下文**：插件不再根据 `deepseek* / glm* / doubao* / ark-code-latest` 等名字写静态能力表。上下文 guard 只接受明确的前反馈和实际请求后的后反馈。

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

这些配置是**传输与观测策略**，不是永久模型能力真值。AstrBot 保存插件配置会触发插件热重载；0.1.31 会在该转换点重新构造当前已加载的 Ark / Agent Plan Provider，使下一请求绑定新策略，而不是要求“保存成功”替代“实际生效”的确认。

## 上下文：前反馈与后反馈

0.1.31 撤回 0.1.30 和早期候选中“看模型名前缀，把 128K 自动抬到 256K/1M”的方案。原因不是某个模型一定没有更大窗口，而是**模型名只是对象标签，不是能力证据**：同名路由可以换后端，接入点 ID 也不包含窗口事实，未来模型修订同样会让静态表过期。

现在的闭环是：

```text
前反馈
  ↓
本轮上下文 guard
  ↓
实际请求到上游
  ↓
后反馈
  ↓
下一轮重新作为前反馈判决
```

### 前反馈

请求前只接受当前对象上能明确取得的证据：

- 普通 Ark `/models` 本次实时回执中的 `token_limits.context_window` 等明确字段；
- AstrBot 已经投影到具体模型卡的正值 `max_context_tokens`；
- 用户在具体模型卡上的显式配置；
- AstrBot 当前宿主元数据或 fallback 所给出的 guard。

这里没有“看到 `deepseek` 就算 1M”或“看到 `doubao` 就算 256K”的分支。`ark-code-latest`、`ep-*`、动态路由别名也一样：没有反馈就不猜。

### 后反馈

请求真的到达上游后，结果才产生新的证据：

- **成功**：只证明这次实际输入/输出规模被接受，因此只记作“至少能到这里”的下界；成功一次不能反推出最大窗口。
- **上下文拒绝但没有明确上限**：只说明这次请求失败，不能从 `requested_tokens`、HTTP 400、模型名或其它数字臆测窗口；guard 不改。
- **上游明确反馈最大上下文窗口**：这属于直接后反馈，可以纠正当前实例里的旧 guard，既可以向上也可以向下。
- 如果本轮明确请求了 `max_tokens`、`max_completion_tokens`、模型卡 `Max Output Tokens` 或等价显式输出额度，换算输入历史 guard 时会给这部分输出留下空间；没有明确输出额度时不凭空编一个 reserve。

后反馈只作用于**当前 Provider 实例的运行证据**。它不会写成按模型名永久保存的能力事实；插件热重载、Provider 重建、AstrBot 重启后，都要从当时的新前反馈重新开始。

因此：

```text
同一个模型名 + 不同后反馈 → 可以得到不同下一轮 guard
不同模型名 + 同一份明确反馈 → 可以得到相同 guard
模型名本身 → 永远不能决定 guard
```

当前失败请求仍由 AstrBot 原生历史缩减与 retry 处理；插件的后反馈主要约束**下一次请求**。缓存日志中的 `ms` 从 0.1.31 起覆盖 `_query` / `_query_stream` 的完整请求生命周期，而不是只统计 completion 对象解析耗时。

## 生命周期确认合同

0.1.31 的阻断测试不再把一次成功外推到整个生命周期。关键不变量会在不同状态点重新判决：

```text
初始安装
  → 创建/保存模型卡
  → Dashboard 刷新
  → 插件配置热重载
  → 现有火山 Provider 重新绑定新策略
  → AstrBot 整进程重启
  → 同版本插件目录替换 + 重启
  → 卸载 + 重启
```

上下文反馈也遵守同一合同：

```text
本轮前反馈成立 ≠ 下一生命周期仍成立
一次成功后反馈 ≠ 已知最大窗口
一次拒绝 ≠ 已知最大窗口
Provider 重建前的后反馈 ≠ 重建后的永久事实
```

这些确认不可互相替代。例如：

```text
配置保存成功 ≠ Provider 已使用新配置
插件 reload 成功 ≠ 下一请求已绑定新模块
本地 payload 合法 ≠ 上游接受
一次运行成功 ≠ restart/update 后仍成立
```

历史 0.1.25 的视频大小、空文件、data URL、ffmpeg timeout/cancel 等负路径合同也单独保留；新增测试不得通过“改写同一个测试文件”把旧确认悄悄覆盖掉。

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
- 超限图片：在 Base64 前进入压缩链；若无法同时满足字节上限与最长边要求，停止本轮请求。
- 动态模型路由 / 接入点 / 宿主未知模型：不由插件按名称猜上下文窗口；只有明确反馈才能改变运行 guard。
- 两条火山通道：不跨通道静默回退。

## 开发与发布

开发真值必须在 `main`；`runtime` 只能由发布器从 main 的 allow-list 运行包生成。

```text
main
  → Runtime Distribution Gate
  → immutable candidate
  → native install matrix
  → exact leased promotion
  → runtime
```

任何再次直接在 `runtime` 上开发而不回灌 main 的做法都视为发布拓扑回归。
