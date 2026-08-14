<h1 align="center">火山方舟双通道模型供应商</h1>
<p align="center"><strong>让 AstrBot 的同一个主模型真正听懂 QQ 语音、看懂视频，同时把普通 API 与 Agent Plan 的计费通道彻底分开。</strong></p>

[![Version](https://img.shields.io/badge/version-0.1.23_candidate-d69e2e)](CHANGELOG.md)
[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.26.1-6b63ff)](https://github.com/AstrBotDevs/AstrBot)
[![Platform](https://img.shields.io/badge/platform-aiocqhttp-2f855a)](https://docs.astrbot.app/dev/star/plugin-new.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 当前状态（先看这里）

| 对象 | 当前结论 |
|---|---|
| 你可以安装的稳定版 | **0.1.22**；安装用 `runtime` 仍是已验证稳定基线，直到 0.1.23 发布器完成晋升 |
| 活跃发布候选 | **0.1.23**；真实同源 A/B、0.1.19 丰富功能回归、模型卡 Video 合同与 Runtime Distribution Gate 已通过，待合并 main 并由受控发布器晋升 `runtime` |
| 0.1.23 主要变化 | 保留 0.1.22 精确 Source-scoped 模型卡 Video 路径，同时加入**有标记、可逆、foreign 保存剥离**的共享 schema 兜底，并给兼容 Dashboard bundle 加内容哈希查询参数，避免已缓存旧 JS 导致火山卡完全没有 Video |
| AstrBot 商场与 Windows 安装 | 外部分发仍单独记账；0.1.23 未经发布器和真实重装前，不把商场/Windows/Launcher 视为已验证 |

机器与维护者读取的唯一当前状态是 [`docs/PROJECT_STATE.json`](docs/PROJECT_STATE.json)。任何涉及 Video、`modalities`、Provider Source 或模型卡 UI 的修改，都必须同时遵守 [`docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`](docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md)。

> **0.1.23 的关键边界：Video / 视频仍属于单个模型卡的原生“模型能力”选择区，不属于 Provider Source 页面。**
>
> 首选路径仍是在已知 `selectedProviderSource.type` 的**单模型卡私有 schema clone**里，只给火山方舟普通 API / Agent Plan 补 Video。0.1.23 额外允许一个有明确 marker 的共享 schema Video 作为**投递兜底**：精确前端桥正常加载时，foreign 私有 clone 会移除这枚 fallback；如果前端桥没有执行，foreign 页面最坏可能短暂多出一个 Video，但保存边界会在持久化前剥掉它，因此不会变成 foreign 配置或请求行为。这个有界副作用用于避免火山卡再次“完全没有 Video”。

交流与反馈：**QQ 群 916646029**

## 你会得到什么

- **QQ 语音直接交给当前主模型**：Silk、AMR 等常见输入经 AstrBot 媒体解析后，由插件做火山 Chat 所需的最后一公里 WAV 规范化，再进入同一条主对话；不需要额外 STT 或第二个转录模型。
- **视频是模型卡原生能力项**：在火山 Ark / Agent Plan 的具体模型卡里，`文本 / 图像 / 音频 / 工具使用` 同层级会出现 `视频 / Video`。每张卡独立勾选、独立保存。
- **开关与运行行为一致**：当前火山模型卡包含 `modalities: video` 时，本轮受信视频附件才转换为火山 `video_url`；关闭后不会走视频转换链。
- **精确隔离优先、投递可降级**：兼容 Dashboard 上 OpenAI、xAI、Gemini 等 foreign 卡仍应没有插件 Video；若精确前端桥未执行，fallback 允许短暂视觉污染，但 foreign create/update 会在持久化前移除 `video`，插件也不会接管 foreign 请求。
- **保留丰富模型卡设置**：0.1.19+ 的视频质量（压缩/原画）、思考模式、Reasoning Effort、Temperature、Top P、Max Output Tokens、Stop、Frequency/Presence Penalty 与 `custom_extra_body` 兼容入口继续保留。
- **普通 API / Agent Plan 计费隔离**：两条通道使用独立 Provider 类型、固定端点和独立密钥；插件内部不会把一条失败请求自动改发到另一条。
- **QQ 音视频失败时不装懂**：媒体解析或 Ark payload 组装失败会明确停止；本地传输失败不会被写成“模型永久不支持该能力”。
- **可卸载**：Dashboard/service 兼容桥与 fallback 都可逆，释放后恢复宿主原 callable，并清理插件临时 Dashboard 资产；当前合同已在 AstrBot 4.27.3 自动验证。

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

当前可安装稳定 `runtime` 仍为 0.1.22；**0.1.23 候选在受控发布器完成前不要当成稳定安装包。** 发布完成后，`runtime` 会由 Runtime Distribution Gate 接受的同一份 allow-list 运行包自动晋升，仓库状态也会再更新为 0.1.23 stable。

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

### 首选精确路径

当前 AstrBot/Dashboard 与精确 bridge 兼容时，仍按五项联合验收：

1. **正确对象出现**：Ark / Agent Plan 的单模型卡原生能力区有且只有一个 Video。
2. **错误对象不出现**：OpenAI、xAI、Gemini 等 foreign Provider 模型卡没有插件 fallback Video；Source 页面也没有退役的总开关/模型选择器替代它。
3. **保存重开不丢失**：保存、关闭、重开、Dashboard 刷新、AstrBot 重启或兼容更新后仍恢复当前火山卡原值。
4. **运行行为与选择一致**：火山卡勾选才生成 `video_url`；关闭不走视频转换。
5. **卸载/释放无插件残留**：插件兼容桥释放后恢复 AstrBot 宿主方法与静态资源解析，并删除插件临时资产与 fallback 元数据。

### 投递降级路径

若精确 frontend bridge 没有执行，0.1.23 允许共享 schema 中保留**一枚有 marker 的 fallback Video**，以保证火山卡不再完全丢失按钮。这时 foreign 卡可能短暂看到 Video，但必须满足：foreign 保存前剥离 `video`、不生成插件运行镜像、不进入插件视频请求链、卸载后恢复宿主。未来 AstrBot 自己原生提供且没有 plugin marker 的 Video 不得被删除。

完整合同见 [`docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`](docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md)。0.1.22 的精确路径已知正确源码仍冻结在：

```text
archive/model-card-video-known-good-0.1.22
```

## 真实验证边界

0.1.23 候选不是只靠源码推理确认：

- **真实同源差分**：AstrBot `4.27.3` 中，AstrBot 原生 OpenAI Source 与插件 Ark Source 使用同一个 `https://ark.cn-beijing.volces.com/api/v3`、同一个真实非空 Key 和同一个真实模型 `deepseek-r1-250120`；两边 `/models` 各返回 129 个模型且 129 个全部重合。OpenAI 模型卡 DOM 只有 Text/Image/Audio/Tool use，插件 Ark 则额外有 Video；Ark 勾选保存重开后仍为 true，OpenAI 落盘没有插件 Video 状态。
- **0.1.19 Compatibility Baseline**：真实 AstrBot `4.27.2` Dashboard 回归仍通过，保护视频质量、思考与采样等丰富模型字段不被本次 UI 修复删除。
- **Model-card Video Contract**：真实 AstrBot `4.27.3` Dashboard 通过新 fallback/cache-bust 纯逻辑合同、运行开关、卸载恢复和五条件浏览器矩阵。
- **Runtime Distribution Gate**：AstrBot `4.26.1` / `4.27.2` 最小运行包加载与现有 Provider/媒体/Dashboard 合同全部通过。

这些证据证明的是候选仓库与对应 AstrBot 版本下的功能边界；它们**不自动证明**某个外部浏览器缓存、AstrBot 商场或真实用户机器已经安装到同一包。0.1.23 发布后仍需要真实仓库名重装观察。

## 历史方案说明

### 0.1.18 Source 视频 UI —— 已退役

0.1.18 曾把视频配置放到火山 Provider Source 页面，用“显示逐模型视频选项”与模型选择器写回每卡布尔值。这个方案是历史过渡层，**不是当前行为**。后续排错或 AI 重构不得把它恢复成现行入口。

### 0.1.20 未发布实验 —— 其正确代码已由 0.1.22 恢复

0.1.20 的实验分支曾正确找到“模型对话框私有 schema clone + 已知 selected Source type”这个作用域，但最后的旧验收错误要求已经退役的 `_volcengine_video_input_mode_ui` 行，导致实验被错误判负且未发布。0.1.22 从该历史提交恢复正确运行代码，并把验收改为直接验证原生 Video 的保存/重开；0.1.23 不替换这条精确路径，只补充投递鲁棒性层。

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
4. 完整重启 AstrBot 后重新加载 Dashboard；0.1.23 会给兼容 bundle 使用内容哈希查询参数，正常情况下浏览器应重新请求补丁后的资源。
5. 确认视频属于本轮消息或本轮引用。
6. 再看 AstrBot 媒体日志；如果视频在形成 Provider 句柄之前已经失败，聊天 Provider 无法从普通文本反推出原视频。

### 火山模型卡没有 Video，但 OpenAI/Gemini 反而出现了 Video

先区分两种情况：

- **foreign 有 Video、火山也有 Video**：说明共享 fallback 正在工作，但精确私有-clone bridge 没有执行。这是 0.1.23 允许的降级视觉副作用；foreign 保存边界应剥掉 Video，不能形成插件运行状态。
- **foreign 有 Video、火山仍没有 Video**：这是失败，说明连 fallback 投递都没有进入当前 Dashboard/schema 路径，应检查实际安装分支、插件启动日志和 Dashboard 服务路径。

精确兼容路径的目标仍然是 OpenAI/Gemini 无插件 fallback Video、火山 Ark/Agent Plan 有 Video。

### 明明选择 Agent Plan 却产生普通 API 调用

检查当前会话 Provider ID 和 AstrBot 全局 `fallback_chat_models`。插件不会跨通道回退，但宿主按用户配置的全局 fallback 仍有独立执行权。

## 实现审计入口

核心职责分布：

```text
main.py
  └─ 插件生命周期；安装/释放 Dashboard、Video fallback 与日志兼容桥

providers.py
  ├─ 两张 Provider 卡与固定端点
  ├─ Agent Plan 本地命名空间
  └─ 调用 audio / video adapter 与逐模型请求覆盖

adapters/
  ├─ audio.py                  Ark 最终 WAV + input_audio
  ├─ video.py                  本轮可信视频 + video_url / off
  └─ logging.py                音视频敏感请求日志脱敏

capabilities/
  ├─ video_modality_fallback.py 有 marker 的共享 Video 投递兜底 + foreign 保存剥离
  ├─ dashboard_asset_bridge.py 私有模型对话框 Source-scoped 清理/投影 + bundle cache-bust
  ├─ model_fields_bridge.py    owned 模型卡投影/保存，foreign 丰富字段清理
  ├─ model_fields.py           modalities ↔ 逐卡兼容运行镜像 + 0.1.19 请求字段
  └─ model_scope.py            provider_source_id → Source type 所有权解析

registry.py
  └─ Provider 注册保护与 AstrBot 服务层可逆兼容桥
```

最重要的审计原则是：**共享 `provider.items.modalities` 不能成为新的跨供应商能力真值。** 0.1.23 唯一允许的共享 Video 注入必须带插件 fallback marker、可逆、被精确 private-clone bridge 在 foreign 卡移除，并在 foreign create/update 持久化边界再次剥离；任何没有这些限制的全局注入都仍然是回归。

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
