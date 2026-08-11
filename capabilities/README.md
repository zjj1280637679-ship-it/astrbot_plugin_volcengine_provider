# 模型卡设置与能力反馈边界

这里不保存“模型能做什么”的真值表，只管理：

- `volcengine_video_input_enabled`：逐模型卡的视频**请求传输开关**；
- 普通 Ark `/models` 本次明确返回的 Source-scoped 稀疏反馈；
- 旧插件视频字段的一次性迁移。

关键语义：

- 传输开关关闭 = 插件不发送视频；**不等于模型不支持视频**。
- 反馈字段缺失 = 未反馈；**不等于 False**。
- AstrBot 自己已有的图片/音频/工具等反馈优先，插件只补缺口。
- 插件不根据 model ID 推断能力，不选择主模型或 fallback，不建立 CapabilityStore。
