# 更新记录

## 0.1.17

- 修复商店发行边界：不再把整个开发仓库直接当作用户安装包。开发态 `main` 与运行态 `runtime` 分离，插件市场 `repo` 绑定稳定的 `runtime` 分支。
- 新增白名单式最小运行包构建器，只收集 `metadata.yaml`、插件入口/Provider/registry、必要 Python 包、`logo.png` 与 `LICENSE`；`.github`、tests、docs、证据、治理、模型研究、实验素材和发布工具默认全部不进入用户包。
- 新增发行物秘密扫描、禁用路径检查、异常体积检查和 ZIP 清单；项目内部运行包预算设为 2 MiB，低于 AstrBot 市场公开的 16 MiB 上限，用于尽早发现误把开发仓库打包的回归。
- 新增“实际发行物”双版本加载门：生成后的最小包分别在 AstrBot 4.26.1 与 4.27.2 中通过 AstrBot 自身插件检查器、Python 编译和干净数据目录加载，而不是继续拿开发 checkout 代替用户收到的包。
- 新增 `runtime` 分支发布流水线：main 合并后由 CI 从白名单重新生成运行态分支，再下载真实 branch archive 做一次商店等价结构检查。开发文件新增到 main 不会自动扩大用户包。
- 记录本次实际错误模式：仓库 ZIP 中 `.github/workflows/**` 进入商店包，Windows 解压中途失败并留下半安装目录，随后重装出现文件名/目录冲突；同时确认“开发可解释性”属于开发仓库，不应通过把 AI/测试/架构资料塞进运行包来实现。
- 本版本不改变 0.1.16 的 Provider、音频、视频、能力反馈、migration 或 AstrBot fallback/retry 语义；变化集中在发行/安装边界。

## 0.1.16

- 将 0.1.15 的能力/反馈边界收敛为可发布状态：继续把 `volcengine_video_input_enabled` 定义为逐模型卡**请求传输开关**，不写入 AstrBot `modalities`，也不把开关、图标、`/models` 回执或一次运行结果升级成模型永久能力事实。
- 明确“交互不等于判断”：组件可以有足够信息完成接收、翻译、发送或展示，却仍没有足够信息或权限做全局能力裁决；新增 `docs/KNOWLEDGE_BOUNDARY.md` 与 `docs/AI_RULES.md` 固化该认识论边界。
- 新增 `docs/TEST_HISTORY.md` 与 `docs/REGRESSION_SCOPE.md`：历史 QQ 音频/视频验证不会因为本版没有重复跑同一条高成本链路而被遗忘；只有媒体 adapter、AstrBot MediaResolver/媒体契约、Ark 音视频 payload 或 QQ/NapCat 输入语义发生相关变化时，才要求完整 QQ 等价链重验。
- 明确裸供应商测试的权限边界：raw Ark 请求用于下游协议归因，不能替代 `QQ -> NapCat/OneBot -> AstrBot -> MediaResolver -> plugin adapter -> Ark/model` 的产品链；禁止为了让不等价的 WAV/MP4 fixture 变绿而放宽生产代码，避免出现“CI 可用但 QQ 不可用”。
- 普通 Ark 真实运行证据升级为 raw-vs-plugin 对照：当前账户的 `/models`（一次观测返回 129 项）、文本和同字节 PNG 图片路径均完成对照；这些结果作为当前 L5 运行证据保存，不写成永久模型能力表。
- 当前普通 Ark 凭据调用 Agent Plan 时，raw 与插件路径同时落在同一认证/账户边界，因此只记录为凭据/账户前提，不据此修改 Provider 生产逻辑，也不把失败归因为模型能力。
- Dashboard 精细 Playwright 卡片矩阵不再作为发布硬门槛：保留真实 AstrBot 生产 Dashboard 构建、登录、Provider 页面可达的粗粒度 L4 证据，以及截图/DOM/可见文本证据采集；避免把欢迎弹窗、显示标签、固定 Source ID 或 Vuetify selector 等测试夹具假设误报成插件故障。
- 完善 AI/项目可解释性入口：`AGENTS.md`、`docs/AI_ONBOARDING.md`、`docs/PROJECT_STATE.json`、`docs/DECISION_INDEX.json`、ADR、证据等级与测试边界共同暴露“客观条件 -> 目标 -> 当前策略 -> 历史证据 -> 重新验证条件”，但这些文件仍是解释钩子，不是运行时控制面。
- 本版本没有重新定义已实现的 QQ 音频/视频产品接口；媒体路径按影响分析继承既有验证资产。若未来修改 `adapters/audio.py`、`adapters/video.py`、相关宿主 hook 或媒体依赖，则必须按 `REGRESSION_SCOPE.md` 重新跑对应 QQ 等价链。

## 0.1.15

- `/models` 模态反馈不再过滤到当前插件认识的 `text/image/audio/video` 枚举：上游未来新增的非空模态 token 会作为本轮信息原样保留，由当前 AstrBot 自然忽略或由未来宿主解释；今天的适配器不替未来删除信息。
- 修复共享模型卡 schema 的 UI 外溢风险：不再把 `volcengine_video_input_enabled` 作为无条件公共 schema 项暴露；改为按火山 Source 的 `provider_source_id` 生成临时条件字段，使用 Source ID 的 UTF-8→hex 可逆无碰撞编码，保存边界转换回正式字段并删除，外国 Provider 无可见字段也不能用伪造临时键生成火山状态。
- 普通 Ark 动态反馈改为单次实时回执：请求前清理旧值，使用 `ContextVar` 隔离并发模型列表请求，Dashboard 读取一次即消费；当前回执明确字段只覆盖本次 Source 响应中的同名旧展示值，不写入全局 `LLM_METADATAS`，历史回执不能压过新回执。
- 新增 `AdapterInputTransportError` 区分本地媒体传递/归一化/Ark payload 组装失败与上游模型回执；前者明确 `reached_model=false`、`capability_observed=null`，只说明输入链路没送达，不作为模型不支持模态的证据，也不由插件自行决定 fallback。
- 新增 `capabilities/SEMANTICS.json` 机器可读语义契约：允许未来新增能力发现与反馈来源，但必须声明来源、时效和权限，禁止把当前无反馈、历史回执或裸 model ID 升格成永久模型事实。
- 修正供应商适配能力与模型能力反馈的边界：视频设置改为逐模型卡 `volcengine_video_input_enabled` 请求传输开关，不再存放在 Provider Source，也不读写 AstrBot `modalities`；开关只决定是否尝试发送 `video_url`，不是模型支持/不支持视频的结论。
- 兼容迁移旧 `volcengine_ark_video_input`、`volcengine_agent_plan_video_input`、`volcengine_model_video_input` 以及旧插件曾写入的 `modalities: video`，但迁移只生成新的插件传输字段，绝不删除或改写宿主 `modalities`。
- 普通 Ark `/models` 改为 Source-scoped 实时稀疏反馈：缺失字段保持“未反馈”，显式 `False`、显式空列表与显式整数 `0` 都作为本轮信息保留；当前回执只在本次 Source 响应中替换同名旧展示值，未回执字段保持宿主管理，并且绝不写入全局 `LLM_METADATAS[model_id]`。
- Agent Plan 保留控制台可见 model-name 候选与 `agentplan/` 本地命名空间，但删除按豆包、DeepSeek、GLM、Kimi、MiniMax 等 model ID 预填能力的静态表；模型能力变化无需等待本插件升级。
- 保留 0.1.14 已完成的 `adapters/audio.py`、`adapters/video.py`、结构化日志脱敏和 side-effect-free package import；本版只纠正能力/反馈策略，不把媒体生命周期重新塞回 Provider。
- 主模型、fallback、重试、图片/音频/工具能力反馈仍完全归 AstrBot；火山上游对某模态的接受或拒绝属于有效运行反馈，插件不自行换模型。

## 0.1.14

- 在 0.1.13“宿主负责生命周期、插件负责火山协议差异”的职责审计基础上继续做纯结构整理，不新增 retry、Key 轮换、媒体下载器、第二模型或独立 Provider 生命周期。
- 把普通 Ark `/models` 事实翻译、Agent Plan 官方事实快照与 AstrBot `LLM_METADATAS` 写入句柄拆到 `metadata/`；Agent Plan 快照显式记录 `2026-08-09` 核对时间及“火山公开套餐/模型表 + 当时 Agent Plan 控制台”的来源类型，使外部事实与程序控制流分离。
- 把 OpenAI SDK 音视频请求日志脱敏拆到 `adapters/logging.py`，把 AstrBot 429 Key 前缀日志兼容 shim 拆到 `compatibility/astrbot.py`；观察层与临时宿主兼容层不再混在 Provider 主文件。
- 把 Ark 音频最后一公里拆到 `adapters/audio.py`：AstrBot `MediaResolver` 继续拥有下载、格式识别与 Tencent Silk 解码，适配器只拥有 16 kHz / 单声道 / PCM16 WAV / 25 MiB 约束与 `input_audio` 序列化。
- 把视频可信附件边界与 `video_url` 转换拆到 `adapters/video.py`：仅当前请求 `extra_user_content_parts` 中的 AstrBot 可信 `TextPart` 可触发媒体读取，用户自己输入的同形字符串保持普通文本；显式 Provider Source 视频开关继续优先于旧 `modalities: video` 兼容值。
- `providers.py` 从约 35.6 KB（0.1.13 发布前）降到约 10 KB，并在此停止拆分：剩余固定端点、Provider 配置、Agent Plan 命名空间、模型发现和两张 Provider 类属于同一个 Provider 身份/调度内聚域，避免为了文件数量继续过度碎片化。
- 根 `__init__.py` 改为无副作用的惰性兼容导出：导入 `metadata/`、`adapters/` 或 `compatibility/` 不再顺带注册 Provider；Provider 注册副作用只由 AstrBot 插件入口 `main.py` 显式触发，旧的根包 Provider 导入方式仍兼容。
- 新增架构边界回归：验证 knowledge ownership、dependency direction、外部事实 provenance、utility import 无注册副作用、Provider 入口注册、音视频 adapter 不拥有 retry/model/key-pool 生命周期。
- 最终源码在 AstrBot `4.26.1` 与 `4.27.2` 双版本矩阵全部通过：两版均完成 Provider 注册、标准 WAV 快路径、真实合成 Tencent Silk、视频可信附件桥、普通 Ark `/models` 与 metadata 发布，并使用 `doubao-seed-2-0-pro-260215` 完成真实 Chat Completions；因此继续声明 `astrbot_version: ">=4.26.1"`。
- 同步修正文档中过时的“音频短哈希”描述：0.1.13 已移除该无协议用途的 SHA-256 计算，当前日志只保留安全引用描述、格式与字节数。

## 0.1.13

- 完成一次以“插件能力 = 目标能力 − AstrBot 已有能力”为标准的职责边界审计：删除插件自有的 429 Key 池删除、随机轮换与等待逻辑，所有恢复行为重新委托 `ProviderOpenAIOfficial._handle_api_error()`；插件只保留 API Key 日志脱敏。
- 删除插件重复实现的 Tencent Silk 魔数检测与直接解码流程，统一把格式识别、下载、Silk 解码和通用音频转换交给 AstrBot `MediaResolver`；插件只验证火山方舟要求的 16 kHz、单声道、16-bit PCM WAV 与 25 MB 上限。
- 新增已合规 WAV 快路径：标准 Ark WAV 不再无条件启动 ffmpeg，也移除了每次请求都计算但没有协议用途的 SHA-256 调试摘要。
- OpenAI SDK 的音视频 DEBUG 脱敏改为结构化 copy-on-write，不再先 `record.getMessage()` 生成巨型字符串。GitHub Actions 的 8 MiB 合成音频基准由约 299 ms / 64 MB 峰值额外内存降至约 0.124 ms / 0.001 MB。
- 撤销对 AstrBot 全局 `modalities` 的 `video` 枚举污染；普通 Ark 与 Agent Plan 改用只属于各自 Provider Source 的“视频输入”布尔字段，旧版已保存的 `modalities: video` 仍作为兼容回退。
- 接近 25 MiB 上限的 `input_audio` Base64 编码移出 asyncio 主协程的直接 Python 路径；最终 24 MiB 合成数据基准总编码约 24.8 ms，事件循环最大间隔约 20.1 ms。
- 保留普通 Ark `/models` → AstrBot `LLM_METADATAS` 的元数据映射、Agent Plan 本地候选表，以及插件自有 Provider 注册替换保护：这些分别补足上游能力信息、Agent Plan 无 `/models` 与 AstrBot 当前无 Provider unregister 的宿主缺口，并未另建独立模型/注册生命周期。
- 最终在 AstrBot `4.27.2` 完成汇总回归：两个 Provider 类型仍由宿主 registry 注册，真实 `/models` 返回 129 个模型，`doubao-seed-2-0-pro-260215` 真实 Chat Completions 返回 `FINAL_THIN_OK`；标准 WAV、真实 Tencent Silk、旧视频配置迁移、日志脱敏与静态职责检查全部通过。
- 审计同时确认图片二次 materialize，以及 AstrBot 5 次 provider retry 与 OpenAI SDK 内层 retry 的 429 放大属于宿主/SDK 热路径；本插件刻意不为它们建立第二套重试或媒体旁路。

## 0.1.12

- 解除 AstrBot 兼容版本的人工上限：`astrbot_version` 从 `>=4.26.1,<4.27` 调整为 `>=4.26.1`，只保留经过验证的最低版本，不再因为未来 AstrBot 小版本发布而被元数据直接判定为不兼容。
- README 的 AstrBot 兼容徽章同步改为 `>=4.26.1`，并明确后续版本只要相关 Provider API 保持兼容即可继续使用。
- 本版本不改变火山方舟普通 API、Agent Plan、QQ 音频归一化、视频输入或计费隔离逻辑。

## 0.1.11

- 重写插件卡、短简介与 README 首屏的价值主叙事：不再把已经真实打通的 QQ 音频与视频理解缩成末尾能力枚举，而是明确告诉你，QQ Silk/AMR 语音会经过可靠归一化并随完整上下文进入同一个主模型，本轮或引用的视频会进入火山官方视频理解协议。
- 把“无需另接 STT、转录模型或第二条聊天旁路”提前到首屏，并将“听、看、回答仍是一条主对话”列为核心能力；普通 API 与 Agent Plan 双通道退回支撑层，继续保证密钥、端点与计费互不混线。
- 本版本只修正价值表达和说明顺序，不改变已经通过真实 QQ 音频、合成视频和双端点请求验证的 Provider 协议、能力开关或运行状态机。

## 0.1.10

- 新增原创 `logo.png`：沿用现有插件家族的复古机器人视觉，用两条互不交叉的橙色/蓝色数据通道表达普通 API 与 Agent Plan 的固定隔离，并用图像、音频、视频三个简洁信号符号表达多模态输入。
- 把统一广告词同步到插件详细简介、短简介与 README 首屏：**让你的 AI 接通火山方舟双通道：能力不缺席，计费不混线。**
- 把 README 从第三人称技术报告重写成面向你的第二人称说明书：先告诉你能得到什么，再给出安装、两条通道配置、多模态开关、排错与计费边界；协议与真实验收证据下沉到后半部分供你审计。
- 补齐正式仓库地址，便于 AstrBot 插件页、市场记录与项目主页保持同一来源。本版本不改变 Provider 请求、计费隔离、音视频协议或运行状态机。

## 0.1.9

- 修复 QQ 音频下载地址没有扩展名时，AstrBot 4.26.x 可能把真实 AMR 字节写入 `.wav` 临时文件，并因后缀捷径把它误标为 WAV 发送，最终触发火山方舟 `InvalidParameter: input_audio is not of valid wav format` 的问题。
- 火山双通道现在拥有可移除、可审计的音频发送句柄：继续使用 AstrBot `MediaResolver` 解析本地路径、URL 与 Base64 引用，但以内容魔数而非后缀/MIME 为真值；Tencent Silk 先解码，再由 ffmpeg 统一归一化为 16 kHz、单声道、16-bit PCM WAV。
- 发送前校验 RIFF/WAVE 结构、声道、采样率、位深、PCM 编码、非空帧与 25 MB 上限；失败时显式停止，不再把错误格式静默交给模型，也不降级成纯文本请求。
- 火山 Chat Completions 请求继续使用官方 `input_audio: {data: <裸 Base64>, format: "wav"}`；音频开关仍是逐模型卡能力，未增加全局 STT、第二模型或聊天旁路。
- 原有可卸载的 OpenAI SDK 请求日志过滤器同时保护 `input_audio.data`，将音频 Base64 替换为 `[REDACTED_AUDIO_BASE64]`，避免修复协议后引入新的日志内容泄漏。
- 使用此前报错的真实 QQ Silk 语音完成本地归一化验收，得到 RIFF/WAVE、16 kHz、单声道、16-bit PCM；同一真实语音的标准 WAV 请求已在普通方舟端点返回 HTTP 200。

## 0.1.8

- 普通方舟 `/models` 返回的每个模型现在都会生成一份谨慎的 AstrBot 模型元数据：文本始终可选，图片、音频、视频与工具能力仅在本次上游回执明确声明时作为新模型卡默认值。
- 上游未给出能力字段时不再缺失元数据并触发 AstrBot 的旧版“默认全能力”回退，也不再继承同名模型残留的可选能力；用户之后仍可在模型卡中手动勾选，插件不会在运行时替用户撤销选择。
- 确认 QQ `Record` 继续完全复用 AstrBot 原生链路：规范化音频进入 `audio_urls`，火山双通道继承的 OpenAI Chat 适配器将其序列化为标准 `input_audio`，不增加 STT 或音频旁路。

## 0.1.7

- 修复 0.1.6 在 AstrBot 4.26 新“供应商源 / 模型配置”结构中无法显示独立视频开关的问题。
- 按 AstrBot 原生图片开关的同一数据模型，把 `video` 补入逐模型 `modalities` 能力集合，并同时补齐第五个可见标签“视频”，不再出现空白复选框。
- 删除“通道专属布尔值 + 原生模型能力”双状态；从此 `modalities` 是图片、音频、工具与视频的唯一能力真值。仅在读取没有 `modalities` 的 0.1.6 旧数据时兼容旧布尔值。
- Schema 响应只复制后扩展选项，不再借由 AstrBot i18n 的浅拷贝引用污染全局配置；视频日志脱敏过滤器增加跨插件重载实例的租约计数，旧实例终止不会提前撤掉新实例仍需要的保护。

## 0.1.6

- 修正 AstrBot 4.26.x 通用 `modalities` 翻译只有四项造成的空白第五复选框，并撤回对所有供应商模型卡的全局视频枚举扩展。
- 普通方舟与 Agent Plan 现在各自获得一个条件显示的模型级“视频输入”开关：两者语义相同、配置键隔离，只在匹配的火山 Provider 类型上出现，不污染其他供应商。
- Provider 配置响应扩展与日志脱敏一样由插件生命周期持有并可精确移除，不修改 AstrBot/Dashboard 文件；0.1.5 已存在的 `modalities.video` 会被读取为迁移初值。

## 0.1.5

- 按 AstrBot 原生图片/音频开关的结构，在每个已配置模型的“模型能力”中补充“视频”选项；开关写入同一个 `modalities` 列表，不另造供应商总开关。
- `modalities` 包含 `video` 时才读取当前视频并转换为火山 `video_url`；明确关闭时不读取、不发送视频，以 `[Video]` 占位继续原生对话，行为与关闭图片后的 `[Image]` 占位同构。
- 未配置能力或空列表继续遵守 AstrBot 的向后兼容语义，视为支持全部能力；视频选项和日志过滤器均由插件生命周期持有并精确移除，不使用裸脚本修改 AstrBot。

## 0.1.4

- 补齐 AstrBot 4.26.x 到火山方舟 Chat Completions 的视频输入链路：只识别 AstrBot 为本次请求组装的受信视频附件标记，并转换为火山官方 `video_url` 内容块。
- HTTP(S) 视频引用保持远程引用；本地、文件引用与 base64 引用统一复用 AstrBot `MediaResolver`，不建立第二套下载、缓存或临时文件基础设施。
- 受信附件标记进入插件后，视频读取失败、MIME 不正确或标记与请求体失配时显式停止，不再静默退化成“模型只看见路径文字”的请求；AstrBot 在生成标记之前的上游媒体转换失败仍以框架日志为准。
- 增加插件生命周期内可安装、可卸载的 OpenAI SDK 视频 URL 日志脱敏；本地视频 data URL 与远程签名 URL 在 DEBUG 日志中统一显示为 `[REDACTED_VIDEO_URL]`。
- 普通 API 与 Agent Plan 均通过同一个 4 秒红蓝合成视频完成真实请求验收：两个固定端点均返回 HTTP 200，模型均正确识别前后半段主色。
- 回归测试扩展为 27 项，其中 25 项默认通过、2 项真实额度测试默认跳过并仅在显式注入临时环境变量时运行。

## 0.1.3

- 普通方舟 `/models` 的完整枚举结果不再只是名称列表：同步把上游返回的输入/输出模态、上下文、最大输出、思考与函数工具能力写入 AstrBot 原生模型元数据。
- Agent Plan 候选与 2026-08-09 控制台“配置 model-name”及套餐模型表对齐；保留 10 个活跃直接模型、`glm-latest` 别名和 `ark-code-latest` 控制台路由，并补齐前缀模型卡能力。
- 说明并区分 Agent Plan 的推理平面与 `ListArkAgentPlanModel` 控制平面；不要求用户提供权限更广、却只能返回 ModelID 的云 AK/SK。
- Provider 来源模板对齐 AstrBot 原生 OpenAI Compatible 卡，不再预填统一模型、128K 上下文、统一模态或 `custom_extra_body`。
- 移除插件自行增加的认证头/请求体字段禁令、Azure 报错门、SDK 重试所有权和流式重放分支；这些行为回归 AstrBot 原生适配器，仅保留固定计费端点、Agent Plan 本地前缀及 429 日志脱敏。
- 明确 Responses 内置工具、Agent Plan Harness 与 Chat Function Calling 是三套不同能力；记录豆包搜索每月 500 次免费、之后套餐内 5 AFP/次及两个独立控制台开关的边界。

## 0.1.2

- 普通方舟通道恢复 AstrBot 原生 OpenAI Compatible 在线 `/models` 枚举，不再用 7 项离线列表截断当前 API Key 实际可见的模型。
- Agent Plan 仍保留独立的 `agentplan/` 命名空间与离线候选列表，避免把两个计费通道重新混合。

## 0.1.1

- 将两个语言模型通道的 `provider` 统一归一化为 AstrBot 内置的火山引擎品牌键 `volcengine`，使普通 API 与 Agent Plan 在供应商页面显示官方公司商标。
- 通道身份仍由各自独立的 Provider 类型、固定端点、默认 ID 与 Agent Plan 模型前缀承载，不改变请求和计费隔离逻辑。

## 0.1.0

- 新增火山方舟普通 API Provider。
- 新增火山方舟 Agent Plan Provider。
- Agent Plan 使用本地 `agentplan/` 模型命名空间，上游请求自动剥离前缀。
- 两个计费端点固定隔离，禁止自动跨通道回退。
- 复用 AstrBot 原生流式、多模态和函数工具调用链路。
- 增加 Provider 注册所有权检查，避免热重载覆盖外部同名类型。
- 覆写 429 重试日志，避免继承的原生适配器记录 API Key 前缀。
- 明确 AstrBot 全局 `fallback_chat_models` 仍需由用户按计费通道隔离配置。
- 拒绝通过自定义认证头或协议保留 extra-body 字段绕过端点、密钥和模型边界。
- 默认上下文窗口改为保守的 128K，不再对全部模型静态宣称 262K。
- 默认能力改为文本与工具；视觉能力需按所选模型显式开启。
- 禁用 OpenAI SDK 内层重试，并禁止已产出分片的流式请求从头重放。
- 拒绝 Azure 专用配置触发错误的客户端与鉴权路径。