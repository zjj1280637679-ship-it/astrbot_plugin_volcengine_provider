# 火山方舟双通道模型供应商

让 AstrBot 的同一个主模型直接处理 QQ 语音与视频，并把火山方舟普通 API 与 Agent Plan 两条计费通道分开管理。

**当前版本：0.1.33**  
**最低 AstrBot：4.26.1**

## 安装与更新

本仓库从 0.1.33 起恢复 AstrBot 标准插件模式：**默认分支 `main` 就是插件安装源**，不再使用额外 `runtime` 发布分支、候选发布分支或自定义白名单运行包。

仓库地址：

`https://github.com/zjj1280637679-ship-it/astrbot_plugin_volcengine_provider`

AstrBot 插件市场、手动 Git 安装和更新都应指向上面的仓库根地址。仓库根目录直接提供 `metadata.yaml`、`main.py`、`_conf_schema.json`、插件源码和资源文件；`.github/`、`docs/`、`tests/` 等开发文件可以与标准 AstrBot 插件一样保留在仓库中，不参与插件入口解析。

> 旧的 `runtime` 分支只作为历史发布痕迹保留，不再是版本真值或安装入口。

## 两张供应商卡

| 类型 | 固定端点 | 密钥 |
| --- | --- | --- |
| `volcengine_ark_chat_completion` | `https://ark.cn-beijing.volces.com/api/v3` | 普通方舟推理 API Key |
| `volcengine_agent_plan_chat_completion` | `https://ark.cn-beijing.volces.com/api/plan/v3` | Agent Plan 专属 API Key |

两条通道使用独立 Provider 类型、端点和密钥。插件内部不会把一条失败请求自动改发到另一条；AstrBot 自己配置的全局 fallback 仍按宿主规则执行。

## 多模态能力

- **图片**：继续走 AstrBot 原生图片能力。
- **QQ 语音**：媒体经 AstrBot resolver 解析后，插件做火山 Chat 所需的 WAV 规范化，再交给当前火山主模型。
- **视频**：在具体火山模型卡的原生 `modalities` 中勾选 `Video` 后，本轮或本轮引用中的可信视频附件会转换为火山 `video_url` 内容块。
- **对象级隔离**：插件 Video 与 `volcengine_*` 设置只属于火山 Ark / Agent Plan 模型卡，不应污染 OpenAI、Gemini、DeepSeek 等其他 Provider 模型卡。

## 媒体护栏

插件配置页提供音频/视频大小和转码超时、超限图片压缩等选项；这些是传输护栏，不是模型能力数据库。

## 缓存命中观测

0.1.30+ 提供 `[VolcengineCache]` 与 `[VolcengineCache:SUM]` 日志，帮助观察上游 `cached_tokens` 命中情况，并对已知模型系列使用更合理的上下文上限。

## 0.1.33：发布架构归位

0.1.33 不改变 Provider 路由、音视频协议或模型卡语义，主要修复发布结构：

- `metadata.yaml` 的 `repo` 恢复为标准 GitHub 仓库根 URL；
- `main` 恢复为唯一市场/安装版本真值；
- 退役自定义 `runtime` 分支发布器、候选分支发布器和运行包白名单门禁；
- 保留功能回归测试，但不再让自定义分发系统覆盖 AstrBot 官方市场与安装器的默认仓库模型。

完整历史变更见 `CHANGELOG.md`。

## 反馈

QQ 群：916646029
