<h1 align="center">火山方舟双通道模型供应商</h1>
<p align="center"><strong>让 AstrBot 的同一个主模型真正听懂 QQ 语音、看懂视频，同时把普通 API 与 Agent Plan 的计费通道彻底分开。</strong></p>

[![Version](https://img.shields.io/badge/version-0.1.25_candidate-d69e2e)](CHANGELOG.md)
[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.26.1-6b63ff)](https://github.com/AstrBotDevs/AstrBot)
[![Platform](https://img.shields.io/badge/platform-aiocqhttp-2f855a)](https://docs.astrbot.app/dev/star/plugin-new.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 当前状态（先看这里）

| 对象 | 当前结论 |
|---|---|
| 你可以安装的稳定版 | **0.1.24**；`runtime` 已由受控发布器晋升到 0.1.24（`c32214e`），主仓 `main` 与 `runtime` 版本一致 |
| 活跃发布候选 | **0.1.25**；只加固媒体传输路径、不改任何 UI/路由语义：视频压缩有 300 秒墙钟超时、所有本地视频物化路径在 Base64 膨胀前强制火山方舟 200 MB 输入上限、超时或取消时必杀 ffmpeg（视频压缩与音频 WAV 归一化两条路径），并补 `-nostdin` |
| 0.1.25 主要变化 | 修复鲁棒性缺口：视频压缩不再可能无限挂起；超大/空视频在进内存前被拒绝；请求被取消不再遗留僵尸 ffmpeg 进程。新增 `tests/test_video_transport_guards.py` 固化这些合同并进入 Runtime Distribution Gate |
| AstrBot 商场与 Windows 安装 | 外部分发仍单独记账；0.1.25 未经发布器和真实重装前，不把商场/Windows/Launcher 视为已验证 |

机器与维护者读取的唯一当前状态是 [`docs/PROJECT_STATE.json`](docs/PROJECT_STATE.json)。任何涉及 Video、`modalities`、Provider Source 或模型卡 UI 的修改，都必须同时遵守 [`docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`](docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md)。

> **0.1.25 的关键边界：Video / 视频仍属于单个模型卡的原生“模型能力”选择区，不属于 Provider Source 页面；而且只属于火山方舟普通 API / Agent Plan 这两类 Source 的模型卡。**
>
> 首选路径是编译产物桥：只有当同一个 served bundle 同时暴露三个已知结构边界（模型卡私有 metadata clone、新建卡数据对象构造器、宿主复选框标签渲染器）时，才在已知 `selectedProviderSource.type` 的**单模型卡私有 clone**上补 Video、显示插件行并注入新建卡默认值。新增的运行时组件桥是第二路径：它在具体 AstrBotConfig 模型卡组件出现后，只依据 `provider_source_id → Source type` 判定所有权，仅改写火山卡的普通响应式数据。两个桥都不存在时，插件宁可让火山卡暂时没有 Video，也不会碰任何 foreign 卡。

交流与反馈：**QQ 群 916646029**

## 你会得到什么

- **QQ 语音直接交给当前主模型**：Silk、AMR 等常见输入经 AstrBot 媒体解析后，由插件做火山 Chat 所需的最后一公里 WAV 规范化，再进入同一条主对话；不需要额外 STT 或第二个转录模型。
- **视频是模型卡原生能力项**：在火山 Ark / Agent Plan 的具体模型卡里，`文本 / 图像 / 音频 / 工具使用` 同层级会出现 `视频 / Video`。每张卡独立勾选、独立保存。
- **开关与运行行为一致**：当前火山模型卡包含 `modalities: video` 时，本轮受信视频附件才转换为火山 `video_url`；关闭后不会走视频转换链。
- **严格对象级隔离**：OpenAI、xAI、Gemini、DeepSeek 等 foreign 卡在共享 schema、served 资产、活动对话框、保存边界与落盘配置五个层面都不出现插件 Video 或 `volcengine_*` 行；不再有 0.1.23 那种"foreign 卡短暂多一个 Video"的降级副作用。
- **保留丰富模型卡设置**：0.1.19+ 的视频质量（压缩/原画）、思考模式、Reasoning Effort、Temperature、Top P、Max Output Tokens、Stop、Frequency/Presence Penalty 与 `custom_extra_body` 兼容入口继续保留。
- **普通 API / Agent Plan 计费隔离**：两条通道使用独立 Provider 类型、固定端点和独立密钥；插件内部不会把一条失败请求自动改发到另一条。
- **QQ 音视频失败时不装懂**：媒体解析或 Ark payload 组装失败会明确停止；本地传输失败不会被写成“模型永久不支持该能力”。
- **可卸载**：Dashboard/service 兼容桥与运行时索引桥都可逆，释放后恢复宿主原 callable，并清理插件临时 Dashboard 资产；当前合同已在 AstrBot 4.27.3 自动验证。

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

当前可安装稳定 `runtime` 为 0.1.24；**0.1.25 候选在受控发布器完成前不要当成稳定安装包。** 发布完成后，`runtime` 会由 Runtime Distribution Gate 接受的同一份 allow-list 运行包自动晋升，仓库状态也会再更新为 0.1.25 stable。

稳定运行包的明确安装来源始终是 `runtime`：

1. 下载 [runtime.zip](https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider/archive/refs/heads/runtime.zip)。
2. 解压后，把其中唯一的插件目录放到 AstrBot `data/plugins/`；确认 `metadata.yaml` 与 `main.py` 位于插件根目录。
3. 完整关闭并重新启动 AstrBot。
4. 打开 `模型提供商`，确认能创建“火山方舟普通 API”和“火山方舟 Agent Plan API”。

> 不要把 `main` 分支仓库 ZIP 当成正式安装包。`main` 包含 CI、测试和设计资料；用户运行包来自经过 allow-list 生成与验证的 `runtime` 分支。

最低兼容版本为 AstrBot `4.26.1`。插件不设置未来小版本上限，但 AstrBot 更新后仍应以真实兼容测试为准。

## 配置普通方舟 API

1. 新建 `volcengine_ark_chat_completion` Provider Source。
2. 填写普通方舟推理 API Key。
3. 在线获取模型列表，或手动填写官方模型 ID / 推理接入点 ID（如 `ep-...`）。
4. 新建或编辑**具体模型卡**。
5. 在模型卡原生“模型能力 / modalities”区域按实际需要勾选 `文本`、`图像`、`音频`、`工具使用`，以及本插件在当前火山卡提供的 `视频 / Video`。
6. 保存模型卡。关闭再打开编辑页后，Video 必须保持原值；如果不能保持，应视为回归，而不是改用 Source 页面总开关绕过。

普通通道使用当前 Key 请求同一 `api_base` 下的 `/models`。上游明确返回的模态、工具、reasoning、上下文或输出限制只作为当前 Source 的反馈证据，不会自动变成跨供应商的永久能力真值。

## 配置 Agent Plan

1. 新建 `volcengine_agent_plan_chat_completion` Provider Source。
2. 填写 **Agent Plan 专属 API Key**，不要填普通方舟或 Coding Plan Key。
3. 选择带 `agentplan/` 前缀的套餐模型，或手动填写新的官方 model-name。
4. 新建或编辑具体模型卡。
5. 需要视频时，仍然只在该模型卡原生能力区勾选 `视频 / Video`；没有第二套 Agent Plan 视频总开关。

Agent Plan 推理 Key 没有可依赖的 OpenAI 风格 `/models` 能力接口。插件因此只提供候选 model-name，不向用户索要高权限云 AK/SK 来伪造一张模型能力真值表。

## 多模态路径

### 图片

继续使用 AstrBot 原生图片能力。模型卡勾选“图像”后，本轮图片沿宿主原生 Chat Provider 路径进入当前模型。

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

插件不再复制 AstrBot 的通用 Silk/媒体基础设施，只负责火山协议的最后约束。

### 视频

模型卡勾选 `视频 / Video` 后，本次消息或本次引用中的**受信 AstrBot 视频附件**会转换为火山官方 `video_url` 内容块：

```text
当前模型卡 modalities 包含 video
  → AstrBot 本轮可信 Video Attachment
  → HTTP(S) / data URL 直接使用，或 MediaResolver 解析本地引用
  → video_url
  → 当前火山主模型
```

如果当前模型卡没有 `video`：

```text
当前模型卡 modalities 不包含 video
  → 不执行视频读取/转换
  → 请求中只保留 [Video] 占位
```

你手动输入一个看起来像 `[Video Attachment: ...]` 的普通文本不会触发本地文件读取。插件只接受 AstrBot 同时通过 `extra_user_content_parts` 交付的本轮受信附件句柄。

## 模型卡高级请求设置

火山已保存模型卡还可以拥有插件自己的逐模型请求字段，例如视频质量、思考模式、Reasoning Effort、Temperature、Top P、Max Output Tokens、Stop、Frequency Penalty、Presence Penalty 等。它们属于**请求配置**，不是模型能力结论，也不能替代原生 Video 能力对勾。

未知或模型专属请求参数继续使用 AstrBot 原生 `custom_extra_body`；明确横向字段只在用户实际填写时覆盖同名自定义值。

## Video 验收

当前 AstrBot/Dashboard 兼容时，按五项联合验收：

1. **正确对象出现**：Ark / Agent Plan 的单模型卡原生能力区有且只有一个 Video；其下方的插件请求行（视频质量、思考模式等）可见。
2. **错误对象不出现**：OpenAI、xAI、Gemini、DeepSeek 等 foreign Provider 模型卡没有插件 Video，也没有任何 `volcengine_*` 行；Source 页面也没有退役的总开关/模型选择器替代它。
3. **保存重开不丢失**：保存、关闭、重开、Dashboard 刷新、AstrBot 重启或兼容更新后仍恢复当前火山卡原值。
4. **运行行为与选择一致**：火山卡勾选才生成 `video_url`；关闭不走视频转换。
5. **卸载/释放无插件残留**：插件兼容桥释放后恢复 AstrBot 宿主方法与静态资源解析，并删除插件临时资产。

不存在"投递降级路径"：0.1.23 的有标记共享 schema fallback 已退役，0.1.24 起任何共享 `modalities` 注入都是回归。

完整合同见 [`docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`](docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md)。0.1.22 的精确路径已知正确源码仍冻结在：

```text
archive/model-card-video-known-good-0.1.22
```

## 真实验证边界

0.1.25 候选不是只靠源码推理确认：

- **传输守卫合同**：新增 `tests/test_video_transport_guards.py` 进入 Runtime Distribution Gate，覆盖 Base64 data URL 上限、超大/空本地视频在 Base64 膨胀前被拒绝、压缩转码超时杀进程、视频/音频两条转码路径取消杀进程；全部十四个打包单元/合同脚本在真实 AstrBot 运行时通过。
- **真实 ffmpeg 压缩正/反向合同**：Gate 内使用系统 ffmpeg 现场生成测试视频、走 `Compressed` 转码、再由 ffmpeg 完整解码生成结果，验证守卫没有破坏压缩输出。
- **0.1.24 基线（稳定版）**：真实同源差分证明 AstrBot 原生 OpenAI Source 与插件 Ark Source 同端点同模型时，OpenAI 模型卡只有 Text/Image/Audio/Tool use，插件 Ark 额外有 Video；foreign 卡（含真实 DeepSeek 差分）在五个层面零插件痕迹。

这些证据证明的是候选仓库与对应 AstrBot 版本下的功能边界；它们**不自动证明**某个外部浏览器缓存、AstrBot 商场或真实用户机器已经安装到同一包。0.1.25 发布后仍需要真实仓库名重装观察。

## 历史方案说明

### 0.1.18 Source 视频 UI —— 已退役

0.1.18 曾把视频配置放到火山 Provider Source 页面，用“显示逐模型视频选项”与模型选择器写回每卡布尔值。这个方案是历史过渡层，**不是当前行为**。后续排错或 AI 重构不得把它恢复成现行入口。

### 0.1.20 未发布实验 —— 其正确代码已由 0.1.22 恢复

0.1.20 的实验分支曾正确找到“模型对话框私有 schema clone + 已知 selected Source type”这个作用域，但最后的旧验收错误要求已经退役的 `_volcengine_video_input_mode_ui` 行，导致实验被错误判负且未发布。0.1.22 从该历史提交恢复正确运行代码，并把验收改为直接验证原生 Video 的保存/重开；0.1.23 补充过共享 schema 投递兜底，但该兜底会在精确桥未执行时给 foreign 卡带来短暂视觉污染，0.1.24 将其退役并恢复为严格对象级隔离。

更早版本的设计、迁移和证据请看 [`CHANGELOG.md`](CHANGELOG.md)、[`docs/TEST_HISTORY.md`](docs/TEST_HISTORY.md) 与 `docs/archive/`。README 只描述当前用户行为，不再把退役 UI 当成现行说明。

## 常见问题

### 获取模型列表很少

先确认你编辑的是普通方舟 Source，而不是 Agent Plan；普通通道会按当前普通推理 Key 在线读取 `/models`。凭据本身权限受限时，只会看到它实际可访问的模型。

### QQ 语音返回 `not of valid wav format`

确认版本至少为 `0.1.9`，并在替换插件目录后完整重启 AstrBot。当前版本会按真实媒体内容走 AstrBot resolver，并在发送前统一满足 Ark Chat WAV 约束。

### 模型没有看见视频

1. 打开**当前使用的那张火山模型卡**，不要去 Source 页面找视频总开关。
2. 确认模型卡原生能力区的 `视频 / Video` 已勾选并保存。
3. 关闭模型卡再重开，确认 Video 仍处于同一状态。
4. 完整重启 AstrBot 后重新加载 Dashboard；0.1.24 的运行时组件桥会在具体模型卡对话框出现后按 Source 类型适配，必要时硬刷新页面（Ctrl+F5）以放弃缓存的旧 bundle。
5. 确认视频属于本轮消息或本轮引用。
6. 再看 AstrBot 媒体日志；如果视频在形成 Provider 句柄之前已经失败，聊天 Provider 无法从普通文本反推出原视频。

### 火山模型卡没有 Video，但 OpenAI/Gemini 反而出现了 Video

0.1.24 起不存在共享 fallback，所以这是**失败**而不是降级副作用：

- 确认实际安装的分支是 `runtime` 且 `metadata.yaml` 版本为 0.1.24 及以上；
- 查看插件启动日志中四个桥的状态：`dashboard_bridge`、`model_fields_bridge`、`dashboard_asset_wrapper`、`dashboard_runtime_index_bridge` 应均为 `active`；
- foreign 卡出现插件 Video 或 `volcengine_*` 行，或火山卡没有 Video，都应作为回归报告（QQ 群 916646029），不要尝试用 Source 页面总开关绕过。

精确兼容路径的目标始终是：OpenAI/Gemini 等 foreign 卡无任何插件痕迹，火山 Ark/Agent Plan 卡有 Video。

### 明明选择 Agent Plan 却产生普通 API 调用

检查当前会话 Provider ID 和 AstrBot 全局 `fallback_chat_models`。插件不会跨通道回退，但宿主按用户配置的全局 fallback 仍有独立执行权。

## 实现审计入口

核心职责分布：

```text
main.py
  └─ 插件生命周期；安装/释放 Dashboard、运行时索引与日志兼容桥

providers.py
  ├─ 两张 Provider 卡与固定端点
  ├─ Agent Plan 本地命名空间
  └─ 调用 audio / video adapter 与逐模型请求覆盖

adapters/
  ├─ audio.py                  Ark 最终 WAV + input_audio（25 MB 上限、120 s 超时、取消杀进程）
  ├─ video.py                  本轮可信视频 + video_url / off（200 MB 上限、300 s 超时、取消杀进程）
  └─ logging.py                音视频敏感请求日志脱敏

capabilities/
  ├─ dashboard_asset_bridge.py  编译产物三边界私有 clone 补丁（首选路径）
  ├─ dashboard_runtime_bridge.py 运行时组件桥：仅适配 owned 具体模型卡实例
  ├─ model_fields_bridge.py    owned 模型卡投影/保存，foreign 丰富字段清理
  ├─ model_fields.py           modalities ↔ 逐卡兼容运行镜像 + 0.1.19 请求字段
  └─ model_scope.py            provider_source_id → Source type 所有权解析

registry.py
  └─ Provider 注册保护与 AstrBot 服务层可逆兼容桥
```

最重要的审计原则是：**共享 `provider.items.modalities` 永远不能成为新的跨供应商能力真值。** 0.1.24 起任何共享 schema Video 注入（包括 0.1.23 的有标记 fallback）都是回归；Video 只能加在具体 owned 模型卡对象上（私有 clone 或运行时组件实例），foreign 卡必须在共享 schema、served 资产、活动对话框、保存边界与落盘配置五个层面保持零插件痕迹。

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
- [豆包搜索](https://www.volcengine.com/docs/82379/2301412?lang=zh)
- [火山方舟 Python SDK（Apache-2.0）](https://github.com/volcengine/volcengine-python-sdk)
- [火山方舟 Ark CLI](https://github.com/volcengine/ark-cli)

仓库地址：<https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider>
