# 0.1.15 架构目录与职责边界

> AstrBot 管生命周期、模型卡反馈、路由、fallback 与重试；插件只补火山协议差异、自己的传输设置和非破坏性 Source 回执展示。

```text
astrbot_plugin_volcengine_provider/
├── main.py                 # 插件生命周期 + 旧插件字段一次性迁移
├── registry.py             # Provider 注册 + 可撤销 Dashboard 窄桥
├── providers.py            # 两条固定端点的薄 Provider 编排
├── adapters/
│   ├── audio.py            # Ark WAV / input_audio 最后一公里
│   ├── video.py            # 受信视频附件 → Ark video_url
│   └── logging.py          # SDK 音视频结构化脱敏
├── capabilities/
│   ├── model_scope.py      # 逐模型卡视频传输设置 + 旧配置迁移
│   ├── source_hints.py     # (source_id, model_id) 稀疏反馈
│   └── source_migration.py # 换 Source 时只清理插件字段
├── metadata/
│   ├── ark.py              # /models → 稀疏反馈，不写全局缓存
│   └── agent_plan.py       # model-name 候选，不保存能力先验
└── compatibility/
    └── astrbot.py          # AstrBot Key 前缀日志脱敏 shim
```

## 不变量

1. `volcengine_video_input_enabled` 是请求传输设置，不是模型能力事实。
2. 插件不读写 AstrBot `modalities` 来管理视频；仅在 0.1.15 迁移时读取历史 `video` 作为旧插件状态线索，并保持原字段不变。
3. `/models` 缺失字段保持 unknown；Source feedback 只 additive merge，不覆盖 AstrBot 反馈，不写 `LLM_METADATAS[model_id]`。
4. Agent Plan 不按 model ID 维护豆包/DeepSeek/GLM/Kimi/MiniMax 能力表。
5. Provider 不选择其他模型，不维护 Key/fallback/retry 池，不复制 AstrBot MediaResolver 生命周期。
6. `adapters/audio.py` / `video.py` 是协议最后一公里；拆分不意味着能力失踪，根目录由本文件提供导航。
7. 所有兼容桥必须可卸载；AstrBot 原生提供对应 hook/视频反馈后应删除兼容层，而不是继续叠加。
