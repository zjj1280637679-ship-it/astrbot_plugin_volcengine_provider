# 当前架构与职责边界

当前发布状态只看 `docs/PROJECT_STATE.json`。本文件描述仍然生效的运行结构，不保留已经退役的 Source 页视频控制或第二发布树。

```text
astrbot_plugin_volcengine_provider/
├── main.py
│   └── 插件生命周期：迁移旧配置、安装/释放可逆桥
├── registry.py
│   ├── Provider 注册所有权
│   ├── 共享 schema 的旧字段清理
│   ├── 当前 Source 模型反馈的单次覆盖
│   └── owned/foreign 模型卡 create/update 保存边界
├── providers.py
│   └── 普通 Ark / Agent Plan 两个固定端点的薄 Provider
├── adapters/
│   ├── audio.py        # QQ/AstrBot 媒体 → Ark WAV/input_audio
│   ├── video.py        # 可信 Video attachment → Ark video_url
│   ├── image.py        # 超限图片压缩
│   ├── limits.py       # 可配置媒体边界
│   └── logging.py      # 音视频敏感 payload 日志脱敏
├── capabilities/
│   ├── model_scope.py
│   │   └── owned 卡身份、native modalities Video 状态、旧配置一次性迁移
│   ├── model_fields.py
│   │   └── Video Quality / Thinking / sampling/output/penalty 等逐卡请求字段
│   ├── model_fields_bridge.py
│   │   └── owned 卡字段投影与保存，foreign 清理
│   ├── dashboard_asset_bridge.py
│   │   └── 仅在编译产物结构唯一匹配时修改 concrete card 私有 metadata
│   ├── dashboard_runtime_bridge.py
│   │   └── 运行时等待 concrete AstrBotConfig，再按 provider_source_id → Source type 作用于 owned 卡
│   ├── source_hints.py
│   │   └── 当前 /models 回执的单次 ContextVar 交接
│   └── cache_insight.py
│       └── 缓存命中观测
├── metadata/
│   ├── ark.py
│   └── agent_plan.py
└── compatibility/
    └── astrbot.py
```

## 当前不变量

1. **main 是唯一长期安装/版本/发布真值。** 不存在第二 runtime、generated、rollback 或版本分支发布树。
2. **Video 属于一个具体 owned 模型卡的原生 `modalities`。** 新卡默认未勾选；用户点击 `视频 / Video` 后，保存的 `modalities` 包含 `video`。
3. `volcengine_video_input_enabled` 只是兼容/请求时镜像，不是第二个用户可见真值，也不是模型永久能力事实。
4. Source 页面没有视频 master、逐模型选择器或“显示视频控制”开关。旧 Source/临时键只允许在迁移和保存边界被识别后删除。
5. 共享 Provider schema 不得无条件增加第五个全局 modality。只有 concrete card 已解析到本插件的 Ark/Agent Plan Source 类型后，私有/当前卡才可看到 Video。
6. owned 卡必须保留 AstrBot 原生 `custom_extra_body`，并显示插件的 Video Quality、Thinking Mode、Reasoning Effort、Temperature、Top P、Max Output Tokens、Stop Sequences、Frequency Penalty、Presence Penalty。
7. foreign Provider 卡不得出现插件 Video、`volcengine_*` 请求行或持久字段。
8. `dashboard_asset_bridge` 与 `dashboard_runtime_bridge` 只是同一 concrete-object 边界的两种可逆交付方式；前者结构不唯一就 fail closed，后者必须先解析当前卡真实 Source 身份。
9. `registry.py` 不再包含已退役的 Source 视频保存器或 Source UI 控制状态机；它只处理当前 schema/feedback/create/update 边界和旧 debris 清理。
10. `/models` 缺失字段仍是“未反馈”，不是 `False`；一次当前回执不会写成全局永久能力数据库。
11. Provider 不维护第二套 fallback、重试、Key 池或路由器；这些继续由 AstrBot 管理。
12. 媒体 adapter 只负责火山协议最后一公里。本地传输失败与上游模型拒绝必须分开归因。
13. 所有 Dashboard/字段桥都必须可释放；卸载并重启后不得留下插件公共 UI。

## 发布成功标准

对模型卡/UI 相关版本，import、compile、单测或“补丁成功安装”只能证明低层结构，不足以发布。

阻断标准由以下两个当前入口给出：

- `tests/e2e/provider_card_matrix/current_release_ui_contract.py`
- `tests/e2e/provider_card_matrix/current_lifecycle_contract.py`

它们必须在 `PROJECT_STATE` 指定的 AstrBot 宿主矩阵中真实构建 Dashboard、启动 AstrBot，并完成：看见 Video → 点击可见标签 → checkbox 真 checked → 保存/重开 → 请求字段可见并持久 → 进程重启保持 → foreign 无污染 → 卸载无残留。

更详细合同见 `docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`。
