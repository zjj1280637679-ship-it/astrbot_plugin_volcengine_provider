# 当前架构目录与职责边界

> AstrBot 管生命周期、模型卡、路由、fallback 与重试；插件只补火山协议差异、自己的传输设置，并把**当前回执**作为当前回执展示，不把反馈升级成模型真理。

```text
astrbot_plugin_volcengine_provider/
├── main.py                 # 插件生命周期 + 旧插件字段一次性迁移
├── registry.py             # Provider 注册 + 可撤销的 Source 页面 Dashboard 窄桥
├── providers.py            # 两条固定端点的薄 Provider 编排
├── adapters/
│   ├── audio.py            # Ark WAV / input_audio 最后一公里
│   ├── video.py            # 受信视频附件 → Ark video_url
│   ├── errors.py           # 本地媒体传递失败的结构化来源信息
│   └── logging.py          # SDK 音视频结构化脱敏
├── capabilities/
│   ├── SEMANTICS.json      # 机器可读：信息来源、时效、权限、不成立推论
│   ├── model_scope.py      # 逐模型卡视频传输设置 + 旧配置迁移
│   ├── source_hints.py     # 当前 /models 回执的一次性 ContextVar 邮箱
│   └── source_migration.py # 换 Source 时只清理插件字段
├── metadata/
│   ├── ark.py              # /models → 当前稀疏反馈，不写全局缓存
│   └── agent_plan.py       # model-name 候选，不保存能力先验
└── compatibility/
    └── astrbot.py          # AstrBot Key 前缀日志脱敏 shim
```

## 不变量

1. `volcengine_video_input_enabled` 是请求传输设置，不是模型能力事实；`False` 只表示“不发送视频 payload”。
2. 插件不读写 AstrBot `modalities` 来管理视频；升级迁移只把历史 `video` 当作最低优先级的旧插件状态线索，并保持原字段不变。
3. `/models` 缺失字段保持“未反馈”；插件动态反馈在请求前清旧值、按 async context 隔离、Dashboard 读取一次即消费，**不形成历史数据库**。
4. 当前 `/models` 回执明确给出的字段（包括 `False`、显式空模态列表）可在**本次 Source Dashboard 响应**中替换同名旧展示值；没有给出的字段不由插件补。整个过程 copy-on-write，不写 `LLM_METADATAS[model_id]`。
5. Agent Plan 不按 model ID 维护豆包/DeepSeek/GLM/Kimi/MiniMax 能力表；候选名称只是发现入口。
6. Provider 不选择其他模型，不维护 Key/fallback/retry 池，不复制 AstrBot MediaResolver 生命周期。
7. `AdapterInputTransportError` 只说明本次媒体在到达有效 Ark 模型请求前失败：`reached_model=false`、`capability_observed=null`。上游 API 回执则继续由 AstrBot/OpenAI SDK 原生错误链处理。
8. 插件负责**区分错误来源**，不替用户把一次错误写成永久能力结论，也不复制 AstrBot runner 来决定 fallback。当前 AstrBot 4.26/4.27 对 Provider exception 的 fallback 行为仍属于宿主策略。
9. `adapters/audio.py` / `video.py` 是协议最后一公里；拆分不意味着能力失踪，根目录由本文件提供导航。
10. AstrBot 4.26/4.27 的模型卡 schema 是共享的；插件**禁止**把 canonical 火山字段无条件塞进共享 schema，也不在通用模型卡投影中显示视频控件。配置入口放在拥有真实 `type` / Source 身份的火山供应商 Source 页面，外国 Source 不获得字段。
11. `volcengine_video_controls_visible` 是 Source 级持久**展示偏好**，只控制逐模型复选列表显示/隐藏；`False` 不清除任何选择，也不停止已启用模型的视频转发。运行时唯一真值仍是各模型卡的 `volcengine_video_input_enabled`。
12. Source 页面模型选择器使用 `Source ID UTF-8 bytes → hex` 可逆无碰撞编码和当前 Source 的模型卡 ID 列表。选择器只存在于 Dashboard 投影；当展示开关开启并保存时，选择写回每卡 canonical 字段后立即删除，绝不作为第二份持久运行状态或进入请求 payload。
13. Source 页面控制面只在 `get_provider_schema + upsert_provider_source` 两个宿主接口都存在时开放；缺少任一接口时只降级 UI，不让半功能控制面影响 Provider 本体或实时模型反馈。旧模型卡临时键的 create/update 翻译仅保留为已经打开的旧 0.1.17 页面兼容路径，不再作为可见入口。
14. Source 页面保存语义已经在 AstrBot `4.26.1` 与 `4.27.2` 服务矩阵完成 L3 验证；2026-08-12 的真实 AstrBot `4.27.2` Dashboard DOM 又完成 L4：Ark / Agent Plan 的 master 各 1 个，展开选择器各 1 个且仅包含本 Source 的 2 / 1 张卡；关闭隐藏、再开选择保留且 0 API 请求；外国 Source 为 0 / 0；Ark / Plan / foreign 通用模型弹窗都不含 canonical、旧临时或新临时字段，`pageErrors=[]`。该结论只覆盖观察到的界面布局与客户端状态行为。
15. 升级迁移优先级固定为 canonical 逐卡值 > 与卡 `provider_source_id` 精确匹配且为 bool 的 0.1.17 旧模型 UI 键 > 更早逐卡字段 > 旧 Source 显式 bool（含 `False`）> `modalities: video`。AstrBot 4.26.1 的 live-schema 残留只在 exact Source 条件成立时保留用户意图；wrong-source / foreign 值不得晋升。
16. 迁移解析后清除模型卡和 Source 上所有错层、旧 UI 与临时选择器字段；owned Source 只有 `volcengine_video_controls_visible` 可以继续持久，宿主 `modalities` 不变。Source 选择器在内存中写回逐卡值后若宿主 upsert 失败，必须恢复调用前的完整模型卡列表并原样抛错。
17. 所有兼容桥必须可卸载；AstrBot 原生提供对应 hook/视频反馈后应优先退出兼容层，而不是叠加第二套生命周期。

## 未来扩展

当前实现不预言未来 Provider/AstrBot 能知道什么。未来可以新增自动能力发现、官方反馈源或用户验证机制，但新增信息必须声明来源、时效与权限；不能用“当前没反馈”推出“不支持”，也不能让过去一次回执压过未来新的条件与回执。详见 `capabilities/SEMANTICS.json`。
