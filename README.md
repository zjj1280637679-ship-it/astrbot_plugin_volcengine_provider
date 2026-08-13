<h1 align="center">火山方舟双通道模型供应商</h1>
<p align="center"><strong>别让你的 AI 在 QQ 里只会看字：让它真正听懂语音，也看懂视频。</strong></p>

[![Version](https://img.shields.io/badge/version-0.1.19-e85d3f)](CHANGELOG.md)
[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.26.1-6b63ff)](https://github.com/AstrBotDevs/AstrBot)
[![Platform](https://img.shields.io/badge/platform-aiocqhttp-2f855a)](https://docs.astrbot.app/dev/star/plugin-new.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 当前状态（先看这里）

| 对象 | 当前结论 |
|---|---|
| 你可以安装的稳定版 | **0.1.19**；稳定包来源是 `runtime`，入口可以是 AstrBot 商店或 `runtime.zip` |
| 活跃发布候选 | **无** |
| 0.1.20 原生 Video 勾选实验 | 已停止、未合并、未发布；不要当成更新版 |
| AstrBot 商场与 Windows 安装 | 商场已显示并提供 **v0.1.19**；Windows 商场安装和运行效果仍须实机验收 |

机器与维护者读取的唯一当前状态是 [`docs/PROJECT_STATE.json`](docs/PROJECT_STATE.json)；实验失败与稳定发布成功是两个不同对象，不能相互覆盖。

装上这款插件，QQ 语音会在可靠转换后，连同完整聊天上下文交给你正在使用的火山方舟主模型；本轮发送或引用的视频，也能由同一个模型看懂并继续回应。你不需要另配 STT、转录模型，也不用再搭建一条互相失忆的旁路。

插件同时为 AstrBot 补齐普通 API 与 Agent Plan 两张独立供应商卡：图片、音频与工具继续使用 AstrBot 原生模型能力；视频请求通道仍逐模型保存，但在对应火山供应商 Source 页面集中勾选；密钥、端点与计费互不混线。让你的 AstrBot 不只是“接入火山方舟”，而是真正在 QQ 对话中获得听、看、理解与回应的能力。

交流与反馈：**QQ 群 916646029**

## 你会得到什么

- **QQ 语音真正交给主模型理解**：Silk、AMR 等 QQ 常见输入会先规范化成可靠 WAV，再随完整上下文进入同一个聊天模型；不是旁路转录，也不需要另配 STT。
- **当前视频直接进入火山协议**：在对应火山供应商 Source 打开“显示逐模型视频选项”，勾选当前模型并保存后，本次发送或引用的视频会转换为官方 `video_url` 内容块，让主模型在同一轮对话里看见动态内容。
- **听、看、回答仍是一条主对话**：语音、视频、图片、文字和工具结果共享 AstrBot 组装的完整上下文，不会拆成互相失忆的多个模型流程。
- **不污染 AstrBot 的公共能力轴**：图片、音频与工具仍按 AstrBot 原生模型卡配置；AstrBot 当前还没有原生 `video` modality，因此插件不修改 `modalities`，也不再把视频字段放进通用模型卡。每个火山 Source 只在自己的页面显示一个持久的“显示逐模型视频选项”开关；打开后出现该 Source 当前模型卡的复选列表，保存时写回各模型卡自己的 `volcengine_video_input_enabled`。关闭显示开关只隐藏列表，不清除已选项，也不停止这些模型的视频转发；其他 Provider 不出现这些字段。
- **两条不会混线的计费通道**：普通 API 与 Agent Plan 分别使用独立供应商类型、固定端点和独立密钥。
- **完整的模型选择**：普通 API 在线读取当前密钥真正可见的模型；Agent Plan 提供带 `agentplan/` 前缀的套餐模型候选。
- **失败时不装懂**：附件进入插件后若解析或验证失败，本次请求会明确停止，不会把没看见、没听见伪装成理解成功。
- **随时可以移除**：全部实现都在本插件目录中，不依赖其他第三方插件，也没有驻留在 AstrBot 外部的裸脚本。

## 先认清两张供应商卡

| 你看到的类型 | 固定端点 | 你应该填写的密钥 | 本地模型名 |
| --- | --- | --- | --- |
| `volcengine_ark_chat_completion` | `https://ark.cn-beijing.volces.com/api/v3` | 普通方舟推理 API Key | 官方模型 ID 或接入点 ID |
| `volcengine_agent_plan_chat_completion` | `https://ark.cn-beijing.volces.com/api/plan/v3` | Agent Plan 专属 API Key | `agentplan/...` |

你在 AstrBot 中看到的 Agent Plan 模型会带本地前缀：

```text
AstrBot：agentplan/doubao-seed-2.1-turbo
                     │ 发送前只移除本地命名空间
                     ▼
火山方舟：doubao-seed-2.1-turbo
```

`agentplan/` 不会原样发给火山。它只帮助你和 AstrBot 分清两条计费路线。

> **请留意 AstrBot 的全局回退链。** 插件内部绝不会把 Agent Plan 的失败请求改发到普通 API，但如果你自己把普通方舟模型加入同一会话的 `fallback_chat_models`，AstrBot 仍可能按全局配置跨通道回退。需要严格隔离计费时，请不要混放。

## 安装

`0.1.19` 已在仓库、经过门禁验证的 `runtime` 分支和 AstrBot 商店版本列表发布。商店是安装入口，`runtime` 是稳定包来源；商店标签本身不能代替下载件和运行效果验收。如果商店安装不可用，请按下面的最小运行包手动安装：

1. 下载 [runtime.zip](https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider/archive/refs/heads/runtime.zip)。
2. 解压 ZIP，把其中唯一的插件目录放入 AstrBot 的 `data/plugins/`；不要把 ZIP 原样塞进插件目录，也不要额外套一层目录。确认 `metadata.yaml` 与 `main.py` 位于插件目录根部。
3. 完整关闭并重新启动 AstrBot。
4. 打开 `模型提供商 → 对话 → 新增`。
5. 确认列表里出现“火山方舟普通 API”和“火山方舟 Agent Plan API”。

> 不要下载 `main` 分支 ZIP 作为插件安装包。GitHub 默认仓库页的 `Code → Download ZIP` 指向开发仓库，其中包含 CI、测试和内部说明；用户安装包只来自经过验证的 `runtime` 分支。

插件最低支持 AstrBot `4.26.1`，不再人为设置未来版本上限；后续 AstrBot 新版本只要相关 Provider API 保持兼容即可继续使用。

当前 AstrBot 的 Provider 类型注册表没有安全的插件级热卸载钩子，所以安装、更新、禁用或卸载后都应完整重启。只刷新网页不能证明新版本已经生效。

## 接通普通方舟 API

1. 新增 `volcengine_ark_chat_completion`。
2. 填写你的普通方舟推理 API Key。
3. 获取模型列表，或手动填写官方模型 ID / 推理接入点 ID（`ep-...`）。
4. 图片、音频与工具仍在具体模型卡按实际情况配置；需要视频时，回到当前火山供应商 Source，打开“显示逐模型视频选项”，在“启用视频请求通道的模型”里勾选目标模型卡并保存。这个选择只是请求传输设置，不是模型能力结论。
5. 保存后，把该模型卡选为当前聊天模型并测试。以后关闭“显示逐模型视频选项”只会隐藏复选列表，已保存的选择和运行状态保持不变；重新打开即可继续调整。旧版视频字段和旧插件曾写入的 `modalities: video` 会一次性迁移为新的逐模型卡传输开关；AstrBot `modalities` 本身保持不动。

普通通道会使用你当前填写的推理 Key 调用同一 `api_base` 下的 `/models`，不会再用离线白名单把结果截成少数几项。若 `/models` 明确返回模态、工具、reasoning、上下文或输出限制，这些字段只作为**当前这一轮 Source 回执**展示：缺失字段保持未反馈；明确返回的字段（包括 `False`）只在本次模型列表响应中替换同名旧展示值，读取后即丢弃，不写回 AstrBot 全局模型元数据。

## 接通 Agent Plan

1. 新增 `volcengine_agent_plan_chat_completion`。
2. 填写你的 **Agent Plan 专属 API Key**；不要填普通方舟或 Coding Plan Key。
3. 选择一个带 `agentplan/` 的套餐模型。
4. 如果你希望使用控制台托管路由，可以选择 `agentplan/ark-code-latest`；它代表可变路由，不是固定模型。
5. 图片、音频与工具继续沿 AstrBot 原生模型卡反馈配置；需要视频时，在当前 Agent Plan 供应商 Source 打开“显示逐模型视频选项”，勾选目标模型卡并保存。这个选择不作为模型能力先验；以后隐藏选择区也不会清除或停用它。

Agent Plan 没有可由专属推理 Key 读取的 OpenAI 风格 `/models`。官方 `ListArkAgentPlanModel` 控制面接口需要权限更广的云账号 AK/SK，而且只返回 ModelID，不能证明模态、工具和长度能力。为了不给你索要不必要的高权限凭据，插件只提供控制台可见 model-name 候选并允许手动填写新模型，不再按 model ID 预填能力。

## 让模型看懂图片、QQ 语音和视频

### 图片

你继续使用 AstrBot 原生图片能力即可。模型卡勾选“图像”后，当前图片会沿原生 Chat Provider 路径进入模型；插件不复制图片下载、缓存或历史管理设施。

### QQ 语音

在模型卡勾选“音频”后，你本轮发送或引用的 QQ 语音会随主对话上下文进入所选模型：

```text
QQ Record
  → AstrBot audio_urls
  → AstrBot MediaResolver 按真实内容解析 / 解码（含 Tencent Silk）
  → 已符合 Ark 约束的 WAV 直接通过；否则只做最后一公里重采样
  → 16 kHz、单声道、16-bit PCM WAV
  → RIFF/WAVE 与 25 MB 上限校验
  → input_audio(data=<裸 Base64>, format="wav")
  → 你的当前主聊天模型
```

你不需要另配全局 STT，也不会多出第二个负责转录的语言模型。音频是什么格式、Tencent Silk 怎样解码等通用媒体工作交给 AstrBot `MediaResolver`；插件只负责火山方舟额外要求的最终 WAV 约束，不再复制宿主的 Silk 检测和解码流程。

### 视频

在对应火山供应商 Source 打开“显示逐模型视频选项”、勾选当前模型卡并保存后，本次消息或本次引用中的受信视频附件会转换为火山官方 `video_url`。显示开关只管配置区是否可见：关闭后已勾选模型仍照常转发视频，重新打开时原选择仍在。HTTP(S) 视频保持远程引用，本地路径、`file://` 与 Base64 引用通过 AstrBot 原生 `MediaResolver` 转成带 MIME 的 data URL。

你手打一个像路径的字符串、旧历史里只剩下的附件标记，都不会让插件打开本地文件。需要模型在后续独立回合重新观看时，请重新引用或附加原视频。

如果音频/视频在 QQ/NapCat/AstrBot 媒体解析或 Ark payload 组装阶段失败，插件会把它标成 `input_transport`：这表示有效请求**尚未到达模型**，模型能力仍未知。若火山 API 已返回模态拒绝或其他上游错误，则继续沿 AstrBot/OpenAI SDK 原生错误链处理。插件只区分失败发生在哪一层，不把一次失败写成永久能力结论，也不自行接管 fallback。

## 0.1.18：视频选项只属于当前火山 Source

- 通用模型卡不再承载插件视频字段；每个火山 Ark / Agent Plan Source 各自提供“显示逐模型视频选项”开关与只包含本 Source 模型卡的选择列表，外国 Source 不显示这些控件。
- 显示开关只控制列表是否可见。关闭后已保存的逐模型选择与视频转发状态继续保留，重新打开即可继续调整。
- Source 保存把临时选择写回每张模型卡的 `volcengine_video_input_enabled`。若宿主 upsert 抛错，插件会恢复调用前的 Source/模型卡与 manager 镜像；考虑到 AstrBot 可能已经写盘、只在后续 Provider reload 失败，还会调用宿主 `save_config()` 补偿回滚，并尽力按旧快照重新加载该 Source 的 Provider 实例。4.26.1/4.27.2 回归已覆盖 post-save reload 失败与 Source rename 失败时的内存、落盘、manager 和旧 Provider reload 恢复调用。回滚写或旧实例重载若再次失败，原始宿主异常仍是主错误并附带说明，不伪称所有状态已恢复。从 0.1.17 升级时只迁移与卡片 Source 身份精确匹配的旧布尔值。
- 这套 Source 配置与保存语义已通过 AstrBot `4.26.1` / `4.27.2` 服务矩阵，并在真实 `4.27.2` Dashboard DOM 中验证 Ark、Agent Plan、外国 Source 与通用模型弹窗的隔离、隐藏和重开保留行为。

## 0.1.16：运行证据不是产品接口替身

- **交互不等于判断。** 一次请求成功只说明该条件下路径成功，一次请求失败也只说明该条件下存在失败；没有额外证据时，两者都不能升级成模型永久能力结论。
- **raw Ark 测试只负责下游协议归因。** 直接发送 WAV、MP4/data URL 或其他合成 fixture，可以帮助判断 Ark payload 是否成立，但不能替代 `QQ → NapCat/OneBot → AstrBot → MediaResolver → plugin adapter → Ark/model` 的真实产品接口。
- **不要为了测试绿灯改坏 QQ。** 一个不等价裸媒体 fixture 如果失败，首先检查测试条件是否等价；禁止为了让 CI 通过而放宽生产 adapter，导致“直接 API 测试成功、QQ 实际不可用”。
- **历史媒体验收按影响重验。** 已验证的 QQ 定向音频/视频链记录在 `docs/TEST_HISTORY.md`；只有媒体 adapter、AstrBot 媒体契约、Ark 音视频 payload 或 QQ/NapCat 输入语义发生相关变化时，才按 `docs/REGRESSION_SCOPE.md` 重新跑完整 QQ 等价链。
- **当前运行证据用于归因，不写成真理。** 普通 Ark 当前 `/models`、文本和同字节 PNG 图片已经完成 raw-vs-plugin 对照；Agent Plan 在使用普通 Ark 凭据时 raw/plugin 同时落在同一认证边界。这些结果只说明当前运行条件，不触发模型能力数据库或插件自有 fallback。
- 项目的 AI/维护入口见 `AGENTS.md`、`docs/AI_RULES.md`、`docs/KNOWLEDGE_BOUNDARY.md`、`docs/TEST_HISTORY.md`、`docs/REGRESSION_SCOPE.md` 与 `docs/PROJECT_STATE.json`。这些文件只负责解释和导航，不是运行时控制面。

## 0.1.15：请求通道不是能力真值表

- AstrBot 模型卡上的图片、音频、工具等信息继续由 AstrBot 管理；没有某个标注只代表当前没有反馈，不自动等于不支持。
- 视频在 AstrBot 4.27 还没有原生反馈选项，因此插件仍以逐模型卡 `volcengine_video_input_enabled` 控制 Ark `video_url` 是否发送，不写 `modalities`，也不替模型下能力结论。当前配置入口位于火山供应商 Source：持久显示开关只控制选择区可见性，临时复选列表按 Source 的真实身份和模型卡 ID 投影，保存后写回逐模型正式字段并删除临时键；外国 Provider 看不到这些字段。
- 普通 Ark `/models` 只贡献当前这一轮 Source 的稀疏反馈：请求前清旧值、并发请求隔离、读取一次即消费；当前回执明确字段可在本次响应覆盖同名旧展示值，但绝不写全局模型元数据。Agent Plan 只提供 model-name 候选，不维护跨模型厂商的能力先验表。

## 0.1.14 的工程结构

0.1.13 先把控制权还给 AstrBot；0.1.14 再让源码结构与这条职责边界一致。目标不是把文件切得越多越好，而是让每个模块只有一个主要变化原因，同时让 Provider 保持为薄调度层。

```text
插件入口 main.py
  └─ 显式加载 Provider 注册

providers.py
  ├─ 两张 Provider 卡与固定端点
  ├─ Agent Plan 本地命名空间
  ├─ 调用 AstrBot 原生 Provider 生命周期
  └─ 只保留 audio / video 的宿主 hook

adapters/
  ├─ audio.py     Ark 最终 WAV 不变量 + input_audio
  ├─ video.py     本轮可信视频边界 + video_url
  └─ logging.py   OpenAI SDK 音视频日志脱敏

metadata/
  ├─ ark.py        当前 /models 回执 → Source-scoped 单次反馈
  └─ agent_plan.py Agent Plan model-name 候选；不维护 model-ID 能力先验

capabilities/
  ├─ SEMANTICS.json      机器可读语义边界
  ├─ model_scope.py      逐模型卡视频请求传输设置与迁移语义
  └─ source_hints.py     当前 Source 回执的临时展示上下文

compatibility/astrbot.py
  └─ 只放可删除的 AstrBot 临时兼容 shim

registry.py
  └─ Provider 注册保护 + 当前 AstrBot Dashboard/schema 兼容桥
```

这次还收紧了初始化粒度：普通 `import astrbot_plugin_volcengine_provider.metadata.ark`、`adapters.audio` 等工具模块不会再隐式注册 Provider；只有 AstrBot 的插件入口 `main.py` 明确加载 `providers.py` 时才产生注册副作用。为了兼容已有调用，`from astrbot_plugin_volcengine_provider import ProviderVolcengineArk` 仍可使用，但改为按需惰性加载。

拆分在 `providers.py` 约 10 KB 时停止。剩余内容——固定端点、Provider 默认配置、Agent Plan 名称转换、普通 Ark 模型发现和两张 Provider 类——共享同一个“Provider 身份与调度”变化原因；继续拆成 `base.py / ark.py / agent_plan.py` 只会增加跳转成本，没有新的职责收益。`registry.py` 也保持单文件，因为注册保护与 schema 桥同属 AstrBot 宿主集成边界。

0.1.14 没有新增 retry、模型轮换、媒体下载器或第二套生命周期。相反，架构测试明确禁止 metadata、logging、media adapter 反向依赖 Provider/retry/key pool；Agent Plan 外部事实还显式记录了核对日期与来源类型。

历史兼容矩阵曾同时在 AstrBot `4.26.1` 与 `4.27.2` 验证 Provider 注册、标准 WAV 快路径、真实合成 Tencent Silk、视频可信附件边界、普通 Ark `/models` 与真实 Chat Completions，因此最低版本仍保持 `>=4.26.1`。0.1.16 对媒体路径是否需要完整重验，按 `docs/REGRESSION_SCOPE.md` 的依赖影响判断，而不是用不等价裸 fixture 替代。

## 插件不会替你做的决定

- 不根据模型名称猜测图片、音频、视频或工具能力。
- 不因为额度不足自动从 Agent Plan 切到普通按量 API。
- 不替你打开 Agent Plan 的“超额后付费”。
- 不把 Seedream、Seedance、TTS、ASR 或向量模型塞进语言模型列表。
- 不偷偷给聊天卡注入豆包搜索；豆包搜索是独立 API / MCP / Skill 能力，应由独立插件接入。
- 不把 Responses API 内置工具假装成 Chat Function Calling 工具。
- 不接管 AstrBot 原生流式、重试、工具结果回传或全局回退策略。

这种谨慎默认意味着：未知模型未标注的能力保持“未反馈”，你再按 AstrBot 原生模型卡、已有反馈和实际请求结果调整配置。对供应商协议来说，少勾一项只会暂时少一种能力，乱勾一项却可能直接让请求失败或走错计费语境。

## 遇到问题时这样检查

### 获取模型列表很少

先确认你编辑的是普通方舟供应商，而不是 Agent Plan 卡；普通通道应使用普通推理 Key 在线读取 `/models`。如果你填写的是接入点权限受限的 Key，列表只会展示该凭据真正可见的结果。

### QQ 语音返回 `not of valid wav format`

确认插件版本至少为 `0.1.9`，并在替换插件目录后完整重启 AstrBot。旧版本可能因临时文件后缀误判，把 AMR 字节标成 WAV。新版本会按内容识别并统一转码。

### 模型没有看见视频

先到当前火山供应商 Source 打开“显示逐模型视频选项”，确认当前模型卡已在“启用视频请求通道的模型”中勾选并保存；显示开关之后可以关闭，不影响已保存选择。再确认视频属于本次消息或本次引用。随后查看 AstrBot 媒体转换日志：如果附件在形成 Provider 句柄之前就失败，聊天 Provider 无法从普通文本中反推出原视频。

### 明明选择 Agent Plan 却产生普通 API 调用

检查当前会话使用的 Provider ID 和 AstrBot 全局 `fallback_chat_models`。插件不会跨通道回退，但你配置的全局回退链仍有自己的执行权。

## 如果你想审计实现

在运行时对话热路径上，插件只在音频与视频两个地方补充 AstrBot 与 Ark 之间的协议差异：

```text
普通文本 / 图片 / 工具 ──────────────→ AstrBot 原生 Chat 适配器
重试 / Key 轮换 / 全局回退 ─────────→ AstrBot 原生 Provider 生命周期
当前 QQ 语音 + audio 已启用 ────────→ AstrBot MediaResolver → Ark 最终 WAV 校验 → input_audio
当前受信视频 + 火山视频输入已开启 ───→ AstrBot MediaResolver → 火山 video_url
附件解析或校验失败 ─────────────────→ 显式停止，不降级装懂
```

普通 API 与 Agent Plan 共用同一个视频句柄和同一个音频规范化句柄，只在固定 Base URL 与本地模型前缀上分叉。这样你只需要审计一套多模态协议，不会遇到两份状态机分别漂移。

当前 `/models` 反馈遵循“上游明确返回什么，就只展示本轮明确返回的什么”的规则：

- `modalities.input_modalities` / `output_modalities`；
- `token_limits.context_window` / `max_output_token_length`；
- `features.tools.function_calling`；
- 明确的思考能力字段。

这些字段是当前 Source 的单次反馈，不自动持久化成模型卡能力真值，也不授权插件自动开关运行路径。AstrBot 当前的公共 `modalities` 仍只有文本、图片、音频与工具，没有原生视频能力轴；插件因此只为自己的 Source 提供逐模型视频请求通道的配置入口，正式值仍保存在每张模型卡，不修改公共 `modalities`、AstrBot 源码或 Dashboard 文件。未来宿主提供原生 video capability 后，这层桥可以直接收缩或移除。

## 已完成的真实验收与当前证据

### 历史产品链证据

- 普通 API 与 Agent Plan 曾使用同一个 4 秒红蓝顺序视频完成 Chat Completions 真请求，返回 HTTP 200，并正确识别颜色顺序。
- 一条曾触发 WAV 格式错误的真实 QQ Tencent Silk 语音，曾被规范化为 16 kHz、单声道、16-bit PCM WAV；同一语音的合规 WAV 通过普通方舟 Chat Completions 返回 HTTP 200。
- AstrBot `4.26.1` 与 `4.27.2` 的兼容矩阵曾覆盖真实合成 Tencent Silk、视频可信附件桥、Provider 注册等宿主路径。

这些是历史条件下的验证资产；何时必须重验见 `docs/TEST_HISTORY.md` 与 `docs/REGRESSION_SCOPE.md`。

### 0.1.16 当前运行归因证据

- 当前普通 Ark `/models`、文本以及同字节 PNG 图片完成 raw-vs-plugin 对照；这些结果用于确认下游协议/插件路径，而不是生成永久模型能力表。
- 当前普通 Ark 凭据调用 Agent Plan 时，raw 与插件路径同时落在同一认证/账户边界，因此不会为了让 CI 变绿而修改 Agent Plan Provider。
- 直接 WAV/视频等裸 fixture 若与 QQ 输入条件不等价，不作为 QQ 产品链是否可用的单独裁决依据。

### 0.1.18 Source 视频 UI 证据

- 新的 Source 页面视频选择保存语义已在 AstrBot `4.26.1` 与 `4.27.2` 的真实服务矩阵通过 L3 验证；2026-08-12 又在真实 AstrBot `4.27.2` Dashboard DOM 完成 L4 观察：Ark / Agent Plan Source 各只出现 1 个显示开关，展开后分别只列出自己的 2 / 1 张模型卡；外国 Source 为 0 个开关、0 个选择器；关闭会隐藏列表，再打开时选择仍保留且过程没有产生 API 请求；三类通用模型弹窗都没有 canonical、旧临时或新临时视频字段，浏览器 `pageErrors=[]`。这是界面呈现证据，不是模型能力或完整视频链证据。
- PR #4 已 squash 合并到 `main` 提交 `22444f47154f4f88ff3157d6e6ffcce9ad2689f0`，主门禁与发布器的发布前/发布后 4 格原生安装验证均通过。稳定 `runtime` 提交为 `4586aa2eb573eb97a72baaaa152c727e3b35530e`：21 个运行文件与门禁产物逐文件一致，`metadata.yaml` 报告 `0.1.18`。这些结果证明仓库与运行分发层发布完成；不代替 AstrBot 商店刷新或真实 Windows 商店安装观察。
- PR #5 随后在 `main` 提交 `9feb0d5902f4bdc88ea69b08f6d3bee25fcf8f2e` 修复发布后的候选分支清理执行环境；主门禁 `31590820116` 与无内容变化发布器 `31590908018` 均成功。发布器确认运行包树未变化，因此未重复晋升，只清除了残留候选分支；当前没有 `runtime-candidate-*` 分支。

### 0.1.19 模型设置与发布证据

- 火山 Ark / Agent Plan 已保存模型卡的双语横向请求设置已在 AstrBot `4.26.1` / `4.27.2` 最小运行包合同中通过；真实 `4.27.2` Dashboard 证据确认火山模型显示并持久化这些字段、外国 Provider 不泄漏字段，0.1.18 Source 视频开关与选择器保持不变。压缩视频正向合同使用真实 ffmpeg 编码与完整解码，不调用付费火山 API。
- PR #8 已合并到 `main` 提交 `9f406dda365213685f7c67d04b3d0cac583fb153`；主门禁 `31630774583` 与发布器 `31630921686`（第 4 次尝试）均成功。发布器的发布前、发布后原生安装矩阵各 4 格全部通过，稳定 `runtime` 提交为 `d7dc0f171cca237304b24604137659bc98a3d962`，树为 `d394a878ee250c6d6d116b9a954589ab0df59ae2`，`metadata.yaml` 报告 `0.1.19`，且当前没有候选分支残留。这些结果证明仓库与运行分发层发布完成；不代替 AstrBot 商店刷新或真实 Windows 商店安装观察。

真实额度测试默认跳过，只有显式注入临时环境变量时才运行。测试代码不会主动读取正式配置或保存密钥。

## 隐私、日志与费用

插件不读取浏览器凭据，不保存额外密钥副本，也不会把 Authorization Header、API Key、签名视频 URL 或音频 Base64 写入自己的日志。音频规范化日志只记录安全引用描述、格式与字节数，不计算或记录音频内容哈希。

普通 API 与 Agent Plan 都可能消耗真实额度。Agent Plan 使用 AFP，并受套餐时间窗口约束；如果你在控制台开启“超额后付费”，套餐耗尽后仍可能产生账单。插件只保证请求走你选择的固定端点，不替你管理账户额度与扣费开关。

## 官方资料

- [AstrBot 插件开发指南](https://docs.astrbot.app/dev/star/plugin-new.html)
- [火山方舟普通 Chat API](https://www.volcengine.com/docs/82379/1494384?lang=zh)
- [火山方舟音频理解](https://docs.volcengine.com/docs/82379/2377589?lang=zh)
- [火山方舟视频理解](https://www.volcengine.com/docs/82379/1895586?lang=zh)
- [Agent Plan 快速开始](https://www.volcengine.com/docs/82379/2373738?lang=zh)
- [Agent Plan 套餐概览](https://www.volcengine.com/docs/82379/2366394?lang=zh)
- [Agent Plan / Coding Plan 专用条款](https://www.volcengine.com/docs/82379/2278469?lang=zh)
- [豆包搜索](https://www.volcengine.com/docs/82379/2301412?lang=zh)
- [火山方舟 Python SDK（Apache-2.0）](https://github.com/volcengine/volcengine-python-sdk)
- [火山方舟 Ark CLI](https://github.com/volcengine/ark-cli)

仓库地址：<https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider>
