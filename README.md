<h1 align="center">火山方舟双通道模型供应商</h1>
<p align="center"><strong>别让你的 AI 在 QQ 里只会看字：让它真正听懂语音，也看懂视频。</strong></p>

[![Version](https://img.shields.io/badge/version-0.1.13-e85d3f)](CHANGELOG.md)
[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.26.1-6b63ff)](https://github.com/AstrBotDevs/AstrBot)
[![Platform](https://img.shields.io/badge/platform-aiocqhttp%20%7C%20webchat-2f855a)](https://docs.astrbot.app/dev/star/plugin-new.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

装上这款插件，QQ 语音会在可靠转换后，连同完整聊天上下文交给你正在使用的火山方舟主模型；本轮发送或引用的视频，也能由同一个模型看懂并继续回应。你不需要另配 STT、转录模型，也不用再搭建一条互相失忆的旁路。

插件同时为 AstrBot 补齐普通 API 与 Agent Plan 两张独立供应商卡：图片、音频与工具继续使用 AstrBot 原生模型能力，视频则使用只属于火山供应商源的开关；密钥、端点与计费互不混线。让你的 AstrBot 不只是“接入火山方舟”，而是真正在 QQ 对话中获得听、看、理解与回应的能力。

交流与反馈：**QQ 群 916646029**

## 你会得到什么

- **QQ 语音真正交给主模型理解**：Silk、AMR 等 QQ 常见输入会先规范化成可靠 WAV，再随完整上下文进入同一个聊天模型；不是旁路转录，也不需要另配 STT。
- **当前视频直接进入火山协议**：在对应火山供应商源开启“视频输入”后，本次发送或引用的视频会转换为官方 `video_url` 内容块，让主模型在同一轮对话里看见动态内容。
- **听、看、回答仍是一条主对话**：语音、视频、图片、文字和工具结果共享 AstrBot 组装的完整上下文，不会拆成互相失忆的多个模型流程。
- **不污染 AstrBot 的公共能力轴**：图片、音频与工具仍按 AstrBot 原生模型卡配置；AstrBot 当前还没有原生 `video` modality，因此插件只给自己的两种火山供应商源增加“视频输入”布尔开关，不给其他 Provider 塞第五个公共选项。
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

1. 把解压后的插件目录放入 AstrBot 的 `data/plugins/`；不要把 ZIP 原样塞进插件目录。
2. 完整关闭并重新启动 AstrBot。
3. 打开 `模型提供商 → 对话 → 新增`。
4. 确认列表里出现“火山方舟普通 API”和“火山方舟 Agent Plan API”。

插件最低支持 AstrBot `4.26.1`，不再人为设置未来版本上限；后续 AstrBot 新版本只要相关 Provider API 保持兼容即可继续使用。

当前 AstrBot 的 Provider 类型注册表没有安全的插件级热卸载钩子，所以安装、更新、禁用或卸载后都应完整重启。只刷新网页不能证明新版本已经生效。

## 接通普通方舟 API

1. 新增 `volcengine_ark_chat_completion`。
2. 填写你的普通方舟推理 API Key。
3. 获取模型列表，或手动填写官方模型 ID / 推理接入点 ID（`ep-...`）。
4. 打开具体模型的编辑卡，按该模型实际能力配置图片、音频与工具；需要视频时，在这张火山供应商源的高级设置里开启“视频输入”。
5. 保存后，把这张模型卡选为当前聊天模型并测试。旧版已经保存的 `modalities: video` 会继续作为兼容回退读取。

普通通道会使用你当前填写的推理 Key 调用同一 `api_base` 下的 `/models`，不会再用离线白名单把结果截成少数几项。若上游返回模型能力、上下文或输出限制，插件会把这些字段转换为 AstrBot 原生模型元数据；上游没有明确声明的能力则不替你猜。

## 接通 Agent Plan

1. 新增 `volcengine_agent_plan_chat_completion`。
2. 填写你的 **Agent Plan 专属 API Key**；不要填普通方舟或 Coding Plan Key。
3. 选择一个带 `agentplan/` 的套餐模型。
4. 如果你希望使用控制台托管路由，可以选择 `agentplan/ark-code-latest`；它代表可变路由，不是固定模型。
5. 图片、音频与工具继续按模型真实能力配置；需要视频时，在这张 Agent Plan 供应商源的高级设置里开启“视频输入”。旧版 `modalities: video` 配置继续兼容。

Agent Plan 没有可由专属推理 Key 读取的 OpenAI 风格 `/models`。官方 `ListArkAgentPlanModel` 控制面接口需要权限更广的云账号 AK/SK，而且只返回 ModelID，不能证明模态、工具和长度能力。为了不给你索要不必要的高权限凭据，插件提供经过官方套餐表核对的候选，也允许你手动填写新模型。

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

在对应火山供应商源开启“视频输入”后，本次消息或本次引用中的受信视频附件会转换为火山官方 `video_url`。HTTP(S) 视频保持远程引用，本地路径、`file://` 与 Base64 引用通过 AstrBot 原生 `MediaResolver` 转成带 MIME 的 data URL。

你手打一个像路径的字符串、旧历史里只剩下的附件标记，都不会让插件打开本地文件。需要模型在后续独立回合重新观看时，请重新引用或附加原视频。

## 0.1.13 的职责边界整理

这一版专门检查“插件是否在替 AstrBot 做 AstrBot 已经会做的事”。结果是：

- **429 与 Key 轮换回归 AstrBot**：插件不再删除 Key、随机选 Key、sleep 或维护自己的 429 恢复状态；只对 AstrBot 原生日志中的 Key 前缀做脱敏。
- **Tencent Silk / 通用音频解析回归 AstrBot**：插件不再自己读 Silk 魔数或直接调用 Silk 解码器，统一通过 `MediaResolver(media_type="audio", target_format="wav")`；只有 Ark 要求的 16 kHz / 单声道 / 16-bit PCM / 25 MB 校验仍属于插件。
- **已合规 WAV 不再无条件 ffmpeg**：已经满足 Ark 约束的 WAV 直接通过，避免一次没有意义的子进程启动和重编码。
- **视频能力不再污染所有 Provider**：不再给 AstrBot 公共 `modalities` 追加 `video`，只给两张火山供应商源提供专属布尔开关，并兼容旧版 `modalities: video`。
- **日志脱敏改为结构化 copy-on-write**：不再先把包含大 Base64 的 SDK 请求整体渲染成字符串再做正则。8 MiB 合成音频日志基准从约 299 ms / 64 MB 峰值额外内存降到约 0.12 ms / 0.001 MB。

这次审计也发现了两个宿主层热路径：AstrBot 的 OpenAI Provider 会再次 materialize 已组装图片；429 请求还会叠加 AstrBot retry 与 OpenAI SDK retry。插件没有为这两点另建旁路，因为它们属于宿主/SDK 生命周期，应在对应层修复。

## 插件不会替你做的决定

- 不根据模型名称猜测图片、音频、视频或工具能力。
- 不因为额度不足自动从 Agent Plan 切到普通按量 API。
- 不替你打开 Agent Plan 的“超额后付费”。
- 不把 Seedream、Seedance、TTS、ASR 或向量模型塞进语言模型列表。
- 不偷偷给聊天卡注入豆包搜索；豆包搜索是独立 API / MCP / Skill 能力，应由独立插件接入。
- 不把 Responses API 内置工具假装成 Chat Function Calling 工具。
- 不接管 AstrBot 原生流式、重试、工具结果回传或全局回退策略。

这种谨慎默认意味着：未知模型的新卡先只有文本能力，你再按真实情况手动勾选。对供应商协议来说，少勾一项只会暂时少一种能力，乱勾一项却可能直接让请求失败或走错计费语境。

## 遇到问题时这样检查

### 获取模型列表很少

先确认你编辑的是普通方舟供应商，而不是 Agent Plan 卡；普通通道应使用普通推理 Key 在线读取 `/models`。如果你填写的是接入点权限受限的 Key，列表只会展示该凭据真正可见的结果。

### QQ 语音返回 `not of valid wav format`

确认插件版本至少为 `0.1.9`，并在替换插件目录后完整重启 AstrBot。旧版本可能因临时文件后缀误判，把 AMR 字节标成 WAV。新版本会按内容识别并统一转码。

### 模型没有看见视频

先确认对应火山供应商源的“视频输入”已开启，再确认视频属于本次消息或本次引用。随后查看 AstrBot 媒体转换日志：如果附件在形成 Provider 句柄之前就失败，聊天 Provider 无法从普通文本中反推出原视频。

### 明明选择 Agent Plan 却产生普通 API 调用

检查当前会话使用的 Provider ID 和 AstrBot 全局 `fallback_chat_models`。插件不会跨通道回退，但你配置的全局回退链仍有自己的执行权。

## 如果你想审计实现

插件只在两个地方扩展 AstrBot 原生边界：

```text
普通文本 / 图片 / 工具 ──────────────→ AstrBot 原生 Chat 适配器
重试 / Key 轮换 / 全局回退 ─────────→ AstrBot 原生 Provider 生命周期
当前 QQ 语音 + audio 已启用 ────────→ AstrBot MediaResolver → Ark 最终 WAV 校验 → input_audio
当前受信视频 + 火山视频输入已开启 ───→ AstrBot MediaResolver → 火山 video_url
附件解析或校验失败 ─────────────────→ 显式停止，不降级装懂
```

普通 API 与 Agent Plan 共用同一个视频句柄和同一个音频规范化句柄，只在固定 Base URL 与本地模型前缀上分叉。这样你只需要审计一套多模态协议，不会遇到两份状态机分别漂移。

模型元数据遵循“上游明确声明才自动勾选”的规则：

- `modalities.input_modalities` / `output_modalities`；
- `token_limits.context_window` / `max_output_token_length`；
- `features.tools.function_calling`；
- 明确的思考能力或最大思考长度字段。

AstrBot 当前的公共 `modalities` 仍只有文本、图片、音频与工具，没有原生视频能力轴。插件因此只在自身生命周期内给两个火山 Provider 类型补充专属“视频输入”字段，不修改公共 `modalities`、AstrBot 源码或 Dashboard 文件；未来宿主提供原生 video capability 后，这层桥可以直接收缩或移除。

## 已完成的真实验收

- 普通 API 与 Agent Plan 均使用 4 秒红蓝顺序视频完成 Chat Completions 真请求，返回 HTTP 200，并正确识别颜色顺序。
- 一条曾触发 WAV 格式错误的真实 QQ Tencent Silk 语音，已被规范化为 16 kHz、单声道、16-bit PCM WAV。
- 同一语音通过普通方舟模型完成真实 Chat Completions 请求并返回 HTTP 200。
- 视频 URL 与音频 Base64 在 DEBUG 请求日志中分别显示为 `[REDACTED_VIDEO_URL]` 与 `[REDACTED_AUDIO_BASE64]`。

真实额度测试默认跳过，只有你显式注入临时环境变量时才运行。测试代码不会主动读取正式配置或保存密钥。

## 隐私、日志与费用

插件不读取浏览器凭据，不保存额外密钥副本，也不会把 Authorization Header、API Key、签名视频 URL 或音频 Base64 写入自己的日志。音频规范化日志只记录安全引用描述、格式、字节数和短哈希。

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