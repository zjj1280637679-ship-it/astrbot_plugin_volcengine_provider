# 更新记录

## 0.1.35

- **单一发布真值**：默认分支 `main` 是唯一安装、版本和市场发布真值。删除旧双分支/诊断/失败候选基础设施；任何临时 PR 分支都不得成为安装源或长期版本线。
- **把“真 UI 成功”升级成发布硬门**：发布不是以 import、语法、单元测试或“无冲突”判定成功，而是在真实启动的 AstrBot Dashboard 中创建火山 Ark / Agent Plan 模型卡，看到恰好一个原生 `视频 / Video` 复选项，通过可见标签点击并确认 checkbox 真实 checked，保存后重开仍 checked。
- **模型卡高级参数必须实际可用**：真实浏览器同时要求 `custom_extra_body`、Video Quality、Thinking Mode、Reasoning Effort、Temperature、Top P、Max Output Tokens、Stop Sequences、Frequency Penalty、Presence Penalty 可见；插件字段完成保存/重开持久化验证。
- **生命周期验收**：Video 对号必须跨页面重开、AstrBot 进程重启和同版本插件替换保持；卸载并重启后插件 UI 注入必须完全消失。
- **对象级隔离**：OpenAI、xAI、Gemini 等 foreign Provider 不能获得火山专属 Video 或 `volcengine_*` 模型卡字段。
- **当前宿主验证范围**：发布矩阵覆盖 AstrBot 4.27.3、4.27.4，以及 2026-09-02 Provider WebUI 已重构的 4.28.0-beta.1。任一真实浏览器/生命周期格失败，0.1.35 不得晋升稳定。
- **清理失效数据**：从当前仓库树移除已退役的 runtime 发布基础设施、旧分支专用诊断工作流、已废弃 Video fallback 模块/合同和失效 archive 快照；不再让旧失败状态充当 AI 的当前指令来源。
- **运行语义保持**：继续保留 0.1.34 已验证的双固定端点、音频规范化、视频传输、图片压缩、缓存观测与模型卡对象级隔离；本版本不引入跨通道回退。

### 历史处理说明

0.1.34 及更早的细节仍可从 Git 提交历史审计，但不再在当前工作树中保留会被误认为“现行发布路径”的失败分支说明、archive 状态或退役发布器。当前行为只由 `metadata.yaml`、`docs/PROJECT_STATE.json`、README、模型卡合同和当前发布门禁共同定义。
