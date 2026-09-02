<h1 align="center">火山方舟双通道模型供应商</h1>
<p align="center"><strong>普通 Ark API 与 Agent Plan 两条计费通道完全隔离；火山模型卡拥有真正可点击、可保存、可重启恢复的原生 Video 对号与请求参数。</strong></p>

[![Version](https://img.shields.io/badge/version-0.1.35-orange)](CHANGELOG.md)
[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.26.1-6b63ff)](https://github.com/AstrBotDevs/AstrBot)
[![Platform](https://img.shields.io/badge/platform-aiocqhttp-2f855a)](https://docs.astrbot.app/dev/star/plugin-new.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 当前发布状态

| 对象 | 状态 |
| --- | --- |
| 活跃候选 | **0.1.35**：单一发布真值清理版；只有真实 AstrBot Dashboard 与重启验收全部通过后才能晋升稳定 |
| 当前稳定 | **0.1.34**：在 0.1.35 通过并合并前继续作为公开稳定版本 |
| 唯一安装源 | GitHub 默认分支 `main` 的仓库根地址；任何其他分支都不是安装、版本或市场真值 |

机器可读状态仅看 [`docs/PROJECT_STATE.json`](docs/PROJECT_STATE.json)。历史失败方案不得从分支名、旧测试名或旧文档反推成当前发布目标。

## 0.1.35 的硬成功标准

这次发布不接受“能 import / 能编译 / 没冲突 / 单元测试绿”作为成功。候选必须在**真实构建并启动的 AstrBot Dashboard**中完成下面的用户可见闭环：

1. 普通 Ark 与 Agent Plan 的新增模型卡，各自的原生 `modalities` 行必须**恰好出现一个 `视频 / Video` 复选项**。
2. 测试必须通过这个可见标签真实点击 Video，并观察 checkbox 进入 checked 状态；保存后重新打开，Video 仍必须是勾选状态。
3. 模型卡必须同时真实显示并可保存：`自定义请求体参数 / custom_extra_body`、`视频质量 / Video Quality`、`思考模式 / Thinking Mode`、`思考强度 / Reasoning Effort`、`Temperature`、`Top P`、`Max Output Tokens`、`Stop Sequences`、`Frequency Penalty`、`Presence Penalty`。
4. 修改上述字段后保存、关闭、重开，值必须保持；AstrBot 进程真实重启后 Video 对号仍必须保持。
5. OpenAI、xAI、Gemini 等 foreign Provider 卡不得得到火山专属 Video 或 `volcengine_*` 行。
6. 插件卸载并重启 AstrBot 后，插件注入的 UI/运行时桥必须消失，不留下第五个全局 modality。
7. 发布门禁覆盖 AstrBot `4.27.3`、`4.27.4` 与当前 Provider WebUI 已重构的 `4.28.0-beta.1`。任一宿主失败，0.1.35 都不得成为稳定版。

这套标准由真实浏览器 Playwright 操作完成，不调用付费火山模型；它证明的是用户实际看到和保存的模型卡行为，而不是“程序没有报错”。

## 模型卡能力

火山 Ark / Agent Plan 模型卡使用 AstrBot 原生配置界面：

- **模型能力 / Modalities**：Text、Image、Audio、Tool use，以及本插件只对火山模型卡加入的 **Video**。
- **自定义请求体参数 / custom_extra_body**：保留 AstrBot 原生高级请求体入口。
- **视频质量 / Video Quality**：`Original Quality` 或 `Compressed`。
- **思考模式 / Thinking Mode**：默认、Disabled、Enabled、Auto。
- **思考强度 / Reasoning Effort**：默认、Low、Medium、High。
- **Temperature / Top P / Max Output Tokens / Stop Sequences / Frequency Penalty / Presence Penalty**：均为逐模型卡设置；留空时不强行覆盖平台默认或已有 `custom_extra_body`。

Video 是当前模型卡自己的请求传输开关，不是对模型永久能力的全局判断。只有该卡保存的 `modalities` 包含 `video` 时，可信视频附件才会转换为火山 `video_url`。

## 两张供应商卡

| 类型 | 固定端点 | 使用的凭据 |
| --- | --- | --- |
| `volcengine_ark_chat_completion` | `https://ark.cn-beijing.volces.com/api/v3` | 普通方舟推理 API Key |
| `volcengine_agent_plan_chat_completion` | `https://ark.cn-beijing.volces.com/api/plan/v3` | Agent Plan 专属 API Key |

两条通道不自动跨通道回退。Agent Plan 模型在 AstrBot 内可显示为 `agentplan/...`，发送到火山前再移除本地命名空间前缀。

## 安装与更新

唯一标准地址：

`https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider`

只使用默认分支 `main`。版本、运行代码、README 与配置 schema 必须在同一个默认分支根目录闭合；不再维护第二套运行分支、生成分支或回滚发布树。

最低声明兼容版本为 AstrBot `>=4.26.1`。发布测试矩阵是“已验证宿主范围”，不是对未来版本的硬拒载上限。

## QQ 多模态路径

### 语音

```text
QQ Record
  → AstrBot MediaResolver
  → 插件归一化为 Ark 要求的 WAV
  → input_audio
  → 当前火山主模型
```

### 视频

```text
当前火山模型卡 Video 已勾选
  → 本轮可信 Video Attachment
  → Original / Compressed
  → video_url
  → 当前火山主模型
```

普通文本伪造的附件标记不会触发本地文件读取。

## 插件配置

| 配置项 | 默认值 | 说明 |
| --- | ---: | --- |
| `audio_max_mb` | 25 | 归一化后音频上限 |
| `audio_transcode_timeout_seconds` | 120 | 音频转码墙钟上限 |
| `video_max_mb` | 200 | 视频输入/压缩结果上限 |
| `video_transcode_timeout_seconds` | 300 | Compressed 视频转码墙钟上限 |
| `image_compress_enabled` | true | 是否压缩超限图片 |
| `image_max_mb` | 5 | 单图压缩触发/目标上限 |
| `image_compress_max_size` | 1280 | 压缩后最长边像素 |
| `image_compress_quality` | 85 | 首轮 JPEG 质量 |
| `cache_log_enabled` | true | 是否记录缓存命中明细 |
| `cache_log_every` | 10 | 每 N 次请求记录汇总 |

## 发布纪律

`main` 是唯一长期版本真值。临时 PR 分支只用于审查和验收，永远不是安装源；失败候选直接停止，不建立永久失败分支、运行分支或回滚树。历史只保留在 Git 提交历史与当前 `CHANGELOG.md` 的必要摘要中，不保留会被 AI 误认为当前指令的失效发布基础设施。

完整模型卡合同见 [`docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md`](docs/contracts/MODEL_CARD_VIDEO_CONTRACT.md)，发布规则见 [`docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md`](docs/ASTRBOT_PLUGIN_RELEASE_SPEC.md)。
