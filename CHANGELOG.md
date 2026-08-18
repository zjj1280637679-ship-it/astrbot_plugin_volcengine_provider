# 更新记录

## 0.1.31（发布候选）

- **恢复 main → Gate → runtime 单向发布拓扑**：把 0.1.28–0.1.30 曾直接落在 `runtime` 的媒体限制、图片压缩、插件配置与缓存观测代码完整收编回 `main`；`runtime` 重新只由受控发布器生成，不再作为平行开发分支。
- **上下文治理改为“前反馈 → 后反馈”证据闭环**：撤回早期候选按 `deepseek* / glm* / doubao*` 等模型名写静态上下文上限的方案。模型名、接入点 ID、`ark-code-latest` 等别名只作为对象标签，不再拥有能力裁决权。请求前只采用当前 Ark `/models` 回执、具体模型卡、AstrBot 元数据/fallback 等明确前反馈；请求真的到达上游后再记录后反馈。
- **成功后反馈只证明下界**：一次请求成功只记录本次实际输入/输出规模被接受，不反推出最大窗口，也不会因为同一模型名曾成功过就永久扩大上下文 guard。
- **明确拒绝反馈可纠正下一轮 guard**：只有上游明确报告 context ceiling 时，才允许把当前 Provider 实例里的旧 guard 向上或向下纠正；`requested_tokens`、HTTP 状态码、其它数字和模型名均不足以改写。若本轮显式设置了 `max_tokens`、`max_completion_tokens`、`custom_extra_body` 中的等价字段或模型卡 `Max Output Tokens`，换算输入历史 guard 时会为输出预留相应空间。
- **反馈有生命周期**：后反馈只属于当前 Provider 实例；插件热重载、Provider 重建、同版本替换或 AstrBot restart 后重新从当时的前反馈开始，不把旧观察提升成永久全局模型事实。当前失败请求的历史缩减/retry 仍由 AstrBot 原生策略负责，后反馈主要约束下一次请求。
- **修复插件配置热重载的真实 Provider 漂移**：消极生命周期测试真实抓到“新插件实例已加载新策略，但旧 Ark Provider 仍存活”的 `provider_reloads=0`。修复后按 live Provider 实例自身的 plugin-owned marker 识别重绑对象，从 AstrBot 取得当前配置并 `ProviderManager.reload()`；foreign Provider 不被选择。真实 AstrBot 4.27.3 已通过 refresh → plugin-config hot reload → `provider_reloads=1` → restart → 同版本替换 → uninstall 的全链重新确认。
- **修复缓存耗时语义**：`ms` 的计时从 completion 解析器移到 `_query` / `_query_stream` 外围，覆盖真实请求生命周期与内部重试；缓存命中仍直接读取上游 `prompt_tokens_details.cached_tokens`。
- **修复缓存汇总串桶**：滚动汇总改为按 `channel + model` 独立计数，并把“计数 → 阈值判断 → 快照 → 清零”放在同一锁内；插件观测配置发生变化时清空旧汇总桶，避免跨策略/跨生命周期混样本。
- **图片护栏前移到 Base64 之前**：超限本地/远端图片在 materialize 阶段先 stat，并直接从物化文件压缩；透明图转 JPEG 时铺白底。压缩链先执行 `image_compress_max_size` 最长边，再逐级降质/降分辨率；无法同时满足字节上限与最长边目标时 fail closed。关闭自动压缩只关闭“自动修复”，不会关闭 `image_max_mb` 上限。
- **音频输出读前限流**：ffmpeg 归一化输出先 stat 检查字节上限，再读文件/Base64；取消与超时继续清理子进程。
- **保留旧证据而不是覆盖旧测试**：0.1.25 的 data URL、大文件、空文件、ffmpeg timeout/cancel 等负路径合同独立保存在 `tests/test_transport_legacy_guards.py`；0.1.31 新增 `tests/test_context_feedback_loop.py` 专门验证模型名无裁决权、前反馈/后反馈、成功下界、明确拒绝 ceiling、输出 reserve、Provider hook 接入与 Provider 重建后旧反馈失效。两类合同同时进入 Runtime Distribution Gate，不互相替代。
- **修复运行包白名单**：`_conf_schema.json` 与 `README.md` 进入 `build_runtime_package.py`、publisher `allowed_root` 与默认分支归档等价合同；`.gitattributes` 不再把 README 排除，避免正规发布再次丢掉 WebUI 配置或用户说明。
- **发布状态不再自锁**：README 预先同时描述“0.1.30 稳定 + 0.1.31 候选”和“0.1.31 晋升后的稳定状态”；候选继续保持 `validating / releaseable=false`，只有同一个最终 head 的 Runtime、Lifecycle、Video 与 0.1.19 四套阻断 workflow 全绿后才允许进入 ready。

## 0.1.30

- **缓存命中强化收编进插件**（`capabilities/cache_insight.py`）：把此前散落在独立脚本里的缓存命中观测与上下文治理正式纳入插件管理，不再依赖难以维护的无头脚本。
- **缓存命中日志**：每次对话完成后打印 `[VolcengineCache]` 行，含 `channel`、`model`、输入/缓存命中/未缓存/输出 token 与命中率，以及 reasoning token 和耗时；每 N 次（默认 10）追加 `[VolcengineCache:SUM]` 汇总。仿照 DeepSeek Harness 的缓存命中诊断，用于验证稳定前缀（同模型、同渠道、对话头稳定）确实按缓存命中计费。
- **上下文治理**：上下文长度错误不再盲目弹记录，而是先按模型解析已知上下文上限（deepseek-v4 系/glm 系 → 1M，doubao/kimi/minimax → 256K）并记入缓存日志；未知模型按保守上限降级。保持长对话前缀稳定，正是缓存高命中的关键前提。
- **WebUI 可管理**：`_conf_schema.json` 新增 `cache_log_enabled`（默认开）与 `cache_log_every`（默认 10）两个配置项。
- 实验数据见 README「缓存命中强化」一节：真实运行 24 条 Agent Plan 记录平均命中 83.1%（加权 85.9%），最近 6 条稳定 97.1–97.9%。

## 0.1.29

- **README 归位到运行时包**：`runtime` 分支此前缺少 `README.md`，GitHub 仓库的 `tree/runtime` 页面与 AstrBot 插件信息展示无文档可读。本版本把面向用户的 README 加入运行包，并在其中补齐 0.1.28 的媒体护栏配置说明。
- 新增的 README 为自包含用户文档：安装、两张供应商卡配置、媒体输入上限与超限图片压缩（0.1.28+）、多模态路径、常见问题与隐私/费用边界；不再依赖 `docs/` 内部资料。
- 本版本不改任何插件行为、UI、模型卡、Provider 路由、音视频协议或请求语义；只补文档并随严格更新的版本号 0.1.29 走完整门禁与发布器。

## 0.1.28（已发布到 runtime）

- **可配置媒体输入上限**：音频/视频输入上限与转码超时从写死的常量改为 `_conf_schema.json` 可调项（`audio_max_mb`、`audio_transcode_timeout_seconds`、`video_max_mb`、`video_transcode_timeout_seconds`），WebUI 插件配置页可直接修改。
- **超限图片自动压缩**：新增 `adapters/image.py`，超过 `image_max_mb`（默认 5MB）的本地/`data` 图片在发送前自动降分辨率压缩到上限以内，压缩目标长边与 JPEG 质量可配；仍超限时逐级降质重试，避免请求被火山方舟拒绝。
- 本版本不改 Provider 路由、模型卡 Video 合同或请求语义。

## 0.1.27

- **发布状态归位**：0.1.26 已通过主分支 Runtime Distribution Gate 并由受控发布器晋升到 `runtime`；本版本把上一条更新记录从“发布候选”改为“已发布到 runtime”，避免 AstrBot 更新弹窗把已安装版本误标为候选。
- 0.1.27 只修正版本元数据、更新记录与发布账本，不改插件行为、UI、模型卡、Provider 路由、音视频协议或请求语义。
- `CHANGELOG.md` 已属于运行包；即使只修改更新文字，也必须随严格更新的版本号走完整门禁与发布器，不能在 0.1.26 运行包上原地改写。

## 0.1.26（已发布到 runtime）
- **更新日志随包分发**：AstrBot 插件更新后的"更新日志"弹窗读取插件安装目录里的 `CHANGELOG.md`（`PluginService.get_plugin_changelog`），此前运行时白名单没有打包该文件导致弹窗为空。本版本把 `CHANGELOG.md` 加入运行时包，与开发仓库保持同一个文件、同一份内容。
- 同步四处分发定义：`tools/release/build_runtime_package.py` 的 `ROOT_FILES`、`.gitattributes` 的 export-ignore（默认分支归档与运行时包逐字节等价校验）、发布器 `allowed_root`、`docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md` 的运行时清单。
- 本版本不改任何插件行为、UI、模型卡、路由或请求语义；运行时树变化按仓库规则随严格更新的版本号 0.1.26 走正常门禁与发布器。

## 0.1.25（已发布到 runtime）

- **视频压缩墙钟超时**：`Compressed` 转码由 `asyncio.wait_for` 绑定 300 秒上限；超时终止 ffmpeg 并以明确错误 fail closed，不再可能无限挂起整个聊天请求。音频归一化的 120 秒上限保持不变。
- **火山方舟视频输入上限前置检查**：所有本地视频物化路径在 Base64 膨胀前强制 200 MB 上限（Original 与 Compressed 两条路径、输入与转码输出双向检查）；空文件同样被拒绝。Base64 data URL 用「ceil(bytes/3)×4」长度天花板做免解码检查；HTTP(S) 远端 URL 保持 0.1.18 直通形状（尺寸本地未知，由 Ark 服务端拉取）。
- **取消/异常不再遗留 ffmpeg**：视频压缩与音频 WAV 归一化两条路径在请求取消时同步 `kill()` 转码子进程（音频路径原只在超时时清理）；`-nostdin` 一并补上，避免继承标准输入造成的意外交互。
- Original 模式本地物化改为 `MediaResolver.as_path()` + stat + 读字节 + MIME 校验，语义与旧 `to_base64_data` 路径一致（mime 非 `video/*` 仍拒绝），但在读取前就能拒绝超大/空输入。
- 新增 `tests/test_video_transport_guards.py` 并进入 Runtime Distribution Gate：data URL 天花板、超大/空本地输入拒绝、压缩超时杀进程、视频/音频取消杀进程，全部以 fake subprocess 确定性执行，不依赖付费 API；十四个打包单元/合同脚本全部通过。
- 本版本不改任何 UI、模型卡、Provider 路由、请求覆盖或音频协议常量。
- `runtime` 已由受控发布器（run 31914641554，main gate 31914581993）晋升至 `2cce38ffc389930854e5d7752cac67a441741318`（metadata 0.1.25），主仓 `main` 合并提交为 `5ea2d3d91a4c51ddce606f6832fa25b457b8e5c4`。

## 0.1.24（已发布到 runtime）

- **退役 0.1.23 的有标记共享 schema Video 兜底**：`video_modality_fallback` 桥不再被插件入口安装。该兜底在精确前端桥未执行时会让 OpenAI、xAI、Gemini 等 foreign 模型卡短暂多出一个 Video，本版本移除这条降级路径，恢复严格对象级隔离。
- 共享 schema 中插件模型字段（视频质量、思考模式等）默认以 `invisible: true` 贡献；编译产物桥只对已知 Source 类型的**单模型卡私有 metadata clone** 解除隐藏，并只为 owned 新建卡数据对象注入默认字段值。
- 编译产物桥升级为**三结构边界严格单匹配**：模型卡私有 clone、新建卡数据构造器与宿主复选框标签渲染器必须在同一个 served bundle 中各出现恰好一次才接受补丁；部分匹配一律不修改资产。视频标签只在宿主翻译数组缺少第五项且带插件 marker 时由插件本地化提供，宿主的四个原生标签不再被整体替换。
- 新增**运行时组件桥** `capabilities/dashboard_runtime_bridge.py`：通过宿主 index resolver 向页面注入幂等脚本，等待具体 AstrBotConfig 模型卡组件出现，仅凭 `iterable.provider_source_id → Provider Source type`（来自带鉴权的 `/api/v1/providers/schema`）判定所有权，只改写 owned 卡的普通响应式数据与私有 metadata。foreign 对话框从不被选中或改写；两个桥都不生效时 fail closed（火山卡没有 Video），绝不污染 foreign 卡。
- `main.py` 生命周期改为安装/释放四条桥：registry Dashboard 桥、model-fields 桥、编译产物桥与运行时索引桥；卸载顺序与安装顺序相反，临时资产随释放删除。
- 真实 DeepSeek foreign 差分修复并转绿：AstrBot 4.27.3 的 Source 页模型列表预览用持久化源配置直接构造临时 Provider、不解析 `$VAR` 密钥引用（只有 `load_provider` 走 `_resolve_env_key_list`），原测试因此必 401。工作流预检改为直连 `/models` 只输出模型 ID 清单，浏览器测试经 AstrBot 自定义模型对话框加卡；并修复 source key 落盘形状断言（AstrBot 持久化为列表），同时新增"真实密钥永不落盘"硬断言。
- 真实验证：AstrBot 4.27.3 上 Real Source-Type Video Differential（31852045657）、Real Cross-Provider Plugin Effect Matrix（31852045661）、Model-card Video Contract（31852048201）、Model-card Lifecycle Contract（31852048202）全部通过；DeepSeek 差分（31912600006）未保存/保存重开 foreign 卡均零插件痕迹、落盘无真实密钥、经 AstrBot 供应商测试端点真实请求通过；Runtime Distribution Gate（31852048206）与 0.1.19 Compatibility Baseline（31852048207）在候选树通过；十三个打包单元/合同脚本对真实 AstrBot 运行时全部通过。
- `runtime` 已由受控发布器（run 31913489827，main gate 31913416300）晋升至 `c32214ee2af106b324b06595b978f3910ffddac0`（metadata 0.1.24），主仓 `main` 合并提交为 `8dfb158db1c31872e78e436d0e993d94392462ca`。

## 0.1.23（已发布到 runtime）

- 在 0.1.22 精确 Source-scoped 模型卡 Video 路径之外，加入有标记、可逆、foreign 保存剥离的共享 schema Video 兜底，并给兼容 Dashboard bundle 加内容哈希查询参数，避免已缓存旧 JS 导致火山卡完全没有 Video。
- 已知边界：精确前端桥未执行时，foreign 模型卡可能短暂显示一枚 Video，但保存边界会在持久化前剥离，不会形成 foreign 配置或请求行为。该兜底由 0.1.24 退役。
- `runtime` 已由受控发布器晋升至 `b8d15630f0b97d2c4374d5f232fce4a9833e2925`（metadata 0.1.23），主仓 `main` 为 `699a52f36d140d2acecb79801c0071ce50ae8c4e`。

## 0.1.22（发布候选）

- 恢复只作用于火山方舟普通 API 与 Agent Plan 模型卡私有 schema 的原生 `modalities` Video 能力选择项；外国 Provider 模型卡保持不变。
- 保存时以 `modalities` 是否包含 `video` 同步当前模型卡自己的 `volcengine_video_input_enabled`，重新打开模型卡时按已保存状态投影；旧 Source 页面选择器与旧三态视频行不再充当替代入口。
- 运行代码来自从未合并、从未发布的正确候选提交 `ac8cdb0`；发布身份提升为 0.1.22，并换用新版插件图标。

## 0.1.21（发布候选）

- 不改 Provider、音频、视频、模型路由或 Dashboard 行为；本版本只修复“商场版本标签与实际冻结包不是同一个稳定运行包”的分发身份问题。
- 商场 `0.1.19` 的冻结 ZIP 已被逐文件证明来自默认分支旧提交 `a43b678`，而不是当前 `runtime` 提交 `d7dc0f1`：它多带了开发语义文件，并缺少后续加入的非有限浮点拒绝。版本标签、文档页面和 CI 通过都不再被当成下载件身份的替代证明。
- 将开发语义契约移到 `docs/contracts/SEMANTICS.json`。生产代码从不读取它；默认分支归档与白名单运行包都不再携带该文件。
- 增加默认分支归档与白名单运行包的逐路径、逐字节一致性门禁。AstrBot Cloud 当前冻结默认分支归档，而直接安装使用 `runtime` 分支；两条入口必须携带相同运行内容。
- 知识状态机现在能分别表达“稳定版”“活动实验”“验证中的候选”“已可发布候选”，不再逼迫尚未通过阻断项的版本提前自称稳定或可发布；只有发布器要求候选达到 `ready + releaseable=true`。
- 已退役外部效果工作流按精确身份禁止复活，不再把厂商名、端点或密钥变量名当作永久禁词；历史决策只有被 HOT 状态明确引用时才可表现为活动对象。

## 0.1.19

- **冻结 0.1.18 Provider Source 面板。** 本版本不改变“显示逐模型视频选项”、当前 Source 的模型选择器、保存/回滚语义或 `volcengine_video_input_enabled` 的运行权威；0.1.19 只增强火山 Ark / Agent Plan 已配置模型的编辑弹窗。
- 新增中英双语的逐模型横向设置：`视频输入模式 / Video Input Mode`、`思考模式 / Thinking Mode`、`思考强度 / Reasoning Effort`、`温度 / Temperature`、`核采样 / Top P`、`最大输出 Token / Max Output Tokens`、`停止序列 / Stop Sequences`、`频率惩罚 / Frequency Penalty` 与 `存在惩罚 / Presence Penalty`。外国 Provider 的模型弹窗不投影、也不持久化这些火山字段。
- 视频设置从单一布尔展示升级为 `关闭 / Off`、`压缩 / Compressed`、`原画 / Original Quality` 三态 UI，但保留 0.1.18 数据兼容：旧 `volcengine_video_input_enabled=true` 等价于 `Original`；关闭视频只切换旧 Boolean，不删除上次 `compressed/original` profile，重新启用可恢复上次模式。
- `Original` 严格保留 0.1.18 视频解析与调用形状；`Compressed` 才显式使用系统 `ffmpeg` 将受信视频规范化为较紧凑的 H.264 MP4 后再形成 `video_url`。缺少 ffmpeg 或转码失败时 fail closed，不会静默退回原画。官方 AstrBot Docker 镜像包含 ffmpeg；原生/自定义部署需要保证 `ffmpeg` 在 PATH 中。
- 横向模型字段的优先级明确为“显式横向设置 > 同名 `custom_extra_body` > AstrBot/Ark/模型默认”。数字项在 Dashboard 中以可空字符串承载，空值表示**不注入**而不是数值 0；保存时空字段会清理，真实 `0` 仍可作为合法值持久化。
- 思考参数只提升已经有明确通用语义的 `thinking.type` 与 `reasoning_effort`；本版本没有伪造统一 `Thinking Budget` 字段。厂商/模型专属预算参数继续由 `custom_extra_body` 承载，直到存在可验证的 Ark 映射。
- 同时兼容 AstrBot `4.26.1` 的 `_apply_provider_specific_extra_body_overrides` 与 `4.27.2+` 的 `_apply_provider_specific_request_overrides`，使横向字段在两条受支持宿主路径都于 `custom_extra_body` 合并后覆盖同名请求值。
- 新增独立、可撤销的 0.1.19 model-fields Dashboard bridge，并叠在 0.1.18 Source bridge外层；安装顺序为 Source bridge → model-fields bridge，卸载顺序反向。`registry.py` 与 0.1.18 Source UI 逻辑保持不变，AstrBot `modalities` 仍不改写。
- AstrBot 的首次“新增模型”弹窗由前端本地构造，插件无法在不修改共享 Dashboard 的前提下把服务端投影字段塞进该未保存对象；因此新横向字段在模型**保存后重新打开编辑弹窗**时出现。这是宿主 UI 生命周期边界，不是保存失败。
- 发布实现已经通过 AstrBot `4.26.1` / `4.27.2` 双版本最小运行包合同与真实启动；真实 `4.27.2` Dashboard 浏览器矩阵确认 Ark / Agent Plan 模型显示并持久化双语横向字段，foreign 模型保持干净，0.1.18 Source master/selector 不受影响且 `pageErrors=[]`。压缩正向合同会现场生成测试视频、走 `Compressed` 转码、再由 ffmpeg 完整解码生成结果，不依赖付费火山 API。
- 修复首次合并后的发行阻断：活动发布链不再分别硬编码插件版本，而是由 `metadata.yaml` 生成 runtime manifest，再验证候选包和原生安装后的 metadata 与该 manifest 完全一致；知识状态门禁会拒绝重新引入固定发行版本比较，避免下次迭代再次因遗漏旧版本字面量而失败。
- 原生安装矩阵只对 GitHub archive 的 HTTP `408` / `429` / `5xx` 与传输中断做最多三次的有限重试，并在重试前清理半下载 ZIP/目录；清单、字节或插件启动等确定性失败仍立即阻断发布。
- `Temperature`、`Top P`、`Frequency Penalty` 与 `Presence Penalty` 保存边界现在显式拒绝 `NaN`、正无穷和负无穷，避免非有限浮点绕过上下界比较后进入 Ark 请求；空值、合法零值与原有范围保持不变。
- 仓库内所有第三方 GitHub Actions 均固定到完整 40 位提交 SHA（注释保留可读版本），包括真实 Dashboard、真实火山矩阵与六个 Seedance 手动工作流，避免浮动标签在未审查时改变 CI 或接触密钥的执行代码。
- PR #8 合并后的主门禁 `31630774583` 与发布器 `31630921686`（第 4 次尝试）全部成功；发布前、发布后原生安装矩阵各 4 格通过，`runtime` 已晋升到提交 `d7dc0f171cca237304b24604137659bc98a3d962`（树 `d394a878ee250c6d6d116b9a954589ab0df59ae2`，metadata `0.1.19`），候选分支清理完成。AstrBot Store 刷新与真实 Windows 商店安装仍是尚未观察的外部状态。

## 0.1.18

- 把火山视频传输的可见配置入口从通用模型卡移到对应 Provider Source 页面，避免共享模型卡组件因缺少可靠的当前 Provider 身份而出现“所有供应商都显示”或“所有供应商都不显示”。
- 新增持久 `volcengine_video_controls_visible` 展示开关；它只控制当前火山 Source 的逐模型复选列表显示/隐藏。关闭不会清除已有选择，也不会停用已勾选模型的视频转发，运行时真值仍是每张模型卡的 `volcengine_video_input_enabled`。
- Source 页面临时选择器按当前 Source 的准确模型卡 ID 投影；打开并保存时写回每卡 canonical 字段，随后删除临时键。外国 Source 没有展示字段或选择器，通用模型卡不再显示视频控件，AstrBot `modalities` 保持不变。
- Source 保存合同已在 AstrBot `4.26.1` 与 `4.27.2` 真实服务矩阵完成 L3 验证；2026-08-12 的真实 AstrBot `4.27.2` Dashboard DOM 另行完成 L4：Ark / Plan master 各 1、选择器各 1 且仅列本 Source 的 2 / 1 张卡，关闭隐藏、再开选择保留且 0 API 请求，foreign 为 0 / 0，三类通用模型弹窗均无 canonical / 旧临时 / 新临时字段，`pageErrors=[]`。
- 修复 AstrBot `4.26.1` 升级兼容：0.1.17 schema 投影曾可能把 `_volcengine_video_transport_ui_<source-hex>` 留在真实模型卡。迁移现在只接受与该卡 `provider_source_id` 精确匹配的布尔值，优先级为 canonical > 精确匹配的 0.1.17 旧 UI > 更早逐卡字段 > 旧 Source 显式布尔（含 `false`）> `modalities: video`；随后清除所有错层和临时字段，wrong-source / foreign 值绝不晋升为火山状态，宿主 `modalities` 仍不改写。
- Source 选择器保存增加补偿式回滚：若 AstrBot 的 `upsert_provider_source` 抛错，恢复调用前的 Source/模型卡及 manager 镜像，通过宿主 `save_config()` 补偿持久化，并尽力按旧快照 reload 该 Source 的 Provider 实例；始终继续抛出原宿主错误。4.26.1/4.27.2 回归覆盖“配置已保存、随后 Provider reload 失败”和 Source rename 失败，确认内存、落盘、manager 恢复及旧实例 reload 调用；补偿写或旧实例 reload 再失败时只给原错误附注，不作虚假恢复保证。

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
- 新增机器可读语义契约（当前路径为 `docs/contracts/SEMANTICS.json`）：允许未来新增能力发现与反馈来源，但必须声明来源、时效和权限，禁止把当前无反馈、历史回执或裸 model ID 升格成永久模型事实。
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
