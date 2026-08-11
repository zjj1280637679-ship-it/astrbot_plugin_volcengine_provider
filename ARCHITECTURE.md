# 0.1.15 架构目录与职责边界

> AstrBot 管生命周期、模型卡、路由、fallback 与重试；插件只补火山协议差异、自己的传输设置，并把**当前回执**作为当前回执展示，不把反馈升级成模型真理。

```text
astrbot_plugin_volcengine_provider/
├── main.py                 # 插件生命周期 + 旧插件字段一次性迁移
├── registry.py             # Provider 注册 + 可撤销 Dashboard 窄桥
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
2. 插件不读写 AstrBot `modalities` 来管理视频；仅在 0.1.15 迁移时读取历史 `video` 作为旧插件状态线索，并保持原字段不变。
3. `/models` 缺失字段保持“未反馈”；插件动态反馈在请求前清旧值、按 async context 隔离、Dashboard 读取一次即消费，**不形成历史数据库**。
4. 当前 `/models` 回执明确给出的字段（包括 `False`）可在**本次 Source Dashboard 响应**中替换同名旧展示值；没有给出的字段不由插件补。整个过程 copy-on-write，不写 `LLM_METADATAS[model_id]`。
5. Agent Plan 不按 model ID 维护豆包/DeepSeek/GLM/Kimi/MiniMax 能力表；候选名称只是发现入口。
6. Provider 不选择其他模型，不维护 Key/fallback/retry 池，不复制 AstrBot MediaResolver 生命周期。
7. `AdapterInputTransportError` 只说明本次媒体在到达有效 Ark 模型请求前失败：`reached_model=false`、`capability_observed=null`。上游 API 回执则继续由 AstrBot/OpenAI SDK 原生错误链处理。
8. 插件负责**区分错误来源**，不替用户把一次错误写成永久能力结论，也不复制 AstrBot runner 来决定 fallback。当前 AstrBot 4.26/4.27 对 Provider exception 的 fallback 行为仍属于宿主策略。
9. `adapters/audio.py` / `video.py` 是协议最后一公里；拆分不意味着能力失踪，根目录由本文件提供导航。
10. 所有兼容桥必须可卸载；AstrBot 原生提供对应 hook/视频反馈后应优先退出兼容层，而不是叠加第二套生命周期。

## 未来扩展

当前实现不预言未来 Provider/AstrBot 能知道什么。未来可以新增自动能力发现、官方反馈源或用户验证机制，但新增信息必须声明来源、时效与权限；不能用“当前没反馈”推出“不支持”，也不能让过去一次回执压过未来新的条件与回执。详见 `capabilities/SEMANTICS.json`。
