# 模型卡设置与反馈边界

这里不保存“模型能做什么”的真值表，只管理：

- `volcengine_video_input_enabled`：逐模型卡的视频**请求传输开关**；
- 普通 Ark `/models` **当前这一轮回执**明确返回的 Source-scoped 稀疏反馈；
- 旧插件视频字段的一次性**用户意图迁移**。

机器可读定义见 [`SEMANTICS.json`](./SEMANTICS.json)。

关键语义：

- 传输开关关闭 = 插件不发送视频；**不等于模型不支持视频**。
- 反馈字段缺失 = 未反馈；**不等于 False**，插件也不补负面图标。
- `/models` 动态反馈不持久化：请求前清旧值、异步上下文隔离、Dashboard 读取一次即消费。
- 当前回执若明确给出某字段（包括 `False`、显式空列表），只在**本次 Source 的 Dashboard 响应**里覆盖同名旧展示信息；不会写回 AstrBot 全局 `LLM_METADATAS`，不会成为路由事实。
- 当前插件不认识的未来模态 token 仍作为回执信息原样保留；今天的枚举不能替未来宿主删信息。
- Agent Plan 候选只传递 model-name，不传递模型能力事实。
- 旧字段迁移只传递过去的用户传输意图，不把旧配置升级成模型事实。
- 插件不根据 model ID 推断能力，不选择主模型或 fallback，不建立 CapabilityStore。

## 失败信息不是能力事实

本地媒体链路失败使用 `AdapterInputTransportError`：

```json
{
  "failure_domain": "input_transport",
  "reached_model": false,
  "capability_observed": null,
  "evidence_lifetime": "current_request"
}
```

它表示 QQ/NapCat/AstrBot/媒体解析/Ark payload 这条输入链路没有成功把有效请求送到模型，**不能推出模型不支持该模态**。

如果请求已经到达火山并由上游返回错误，则继续走 AstrBot/OpenAI SDK 原生错误与 fallback 机制。插件只区分信息来源，不给出 fallback 建议，不替用户把某次上游反馈写成永恒模型能力，也不复制 AstrBot 的路由器。
