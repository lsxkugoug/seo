# seo-front-loop

由 Codex 执行的网站 SEO 优化闭环，是 `seo` 项目集合中的一个独立子项目。

顶层设计：默认由一个 Codex Agent 串行完成观察、决策、执行、自检和评估，使用同一份共享 SEO 档案及数据、代码、验证工具。是否调用子 Agent 由主 Codex 根据任务独立性、复核价值和成本决定；不开子 Agent 也能完成普通实验，不设置固定的多 Agent 流水线。

状态：已有可复用 Skill、配置/关键词读取与复查日期计算脚本；记忆已改为纯 Markdown；指标账户连接和生产发布尚未实现。设计日期：2026-09-07，当前版本 v1.4（2026-09-12）。

设计更新：2026-09-08，统一为“单 Agent 串行优先，Codex 按需委派”。高风险或历史重复例外所需的独立复核，按明确规则由子 Agent 或人工完成；普通改动不强制另开 Reviewer。

范围设计：按摘要、内容、结构、内链、结构化数据、抓取索引、性能、页面生命周期分八类；先区分修复、优化实验和结构性项目。一次完成一个最小完整干预，分别约定可编辑范围、实际影响范围和评估/冻结范围；组合改动保存整体与成员历史，不把整体效果误记为每个成员的独立效果。详见总体方案第 3 节。

## 多项目使用

每个站点使用独立的 `projects/<项目名>/config`、`seo-keywords.json` 和 `.seo-memory/`，共享 Skill 工具。完整规则见 [项目隔离说明](skills/seo-front-loop/references/projects.md)。用户未说明项目时，Agent 先询问；不会自动选最近使用项目。

运行 `python3 skills/seo-front-loop/tools/list_projects.py --root .` 列出候选，然后工具 `--project` 指向选定的具体目录。新项目可使用 Skill 的空白配置/词表模板；当前尚未创建真实站点子目录，也未搬动现有配置或历史。

各项目通过 SEO_GSC_TOKEN_ENV、SEO_POSTHOG_KEY_ENV、SEO_GSC_CREDENTIALS_ENV 指定专属秘密环境变量名称，不能把密钥写入 config，也不自动借用全局凭据。关键词、记忆和证据路径不得越出所属管理项目目录。

## 现在怎么用

调用 `$seo-front-loop`，同时说明管理项目路径、要处理的站点和本轮目的。例如：

```text
使用 $seo-front-loop，管理项目是 /Users/shixianglong/Desktop/seo/seo-front-loop。
先读取我的关键词、周期配置和历史，告诉我本轮哪些可研究、哪些应继续观察；先不发布。
```

Skill 源文件为 [SKILL.md](skills/seo-front-loop/SKILL.md)，本机个人 Skill 目录使用指向它的链接，修改源文件即可更新，不维护两份副本。未出现时可重启 Codex 后检查；宿主可能采用不同的本地发现路径，不能把文件存在当作 UI 已验证加载。[官方 Skill 发现说明](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)

### 修改时间

编辑管理项目的 [config](config)（明文配置，可提交 Git；不要保存凭据）：

```ini
SEO_REPOSITORY_URL=
SEO_REVIEW_INTERVAL_DAYS=20
SEO_REVIEW_MAX_CHECKS=3
SEO_KEYWORDS_FILE=seo-keywords.json
SEO_MEMORY_DIR=.seo-memory
```

默认部署确认后第 20/40/60 天复查；例如将间隔改为 10，则新实验第 10/20/30 天复查。到期不是必须判胜、更不是必须改站；最后仍无结论则保留正确版本并关闭常规等待，部署未知或事故未恢复先对账。

仅周期优先级是当前进程环境变量 > 项目 `config` > 默认值；账户、仓库、关键词/记忆路径与凭据变量名称以选定项目 config 为准，Agent 能从脚本输出看到来源。无需 `source config`；脚本主动读文件且不执行其中内容，避免依赖桌面应用是否继承终端环境。支持整数天 1–365、检查点数 1–12；这些是输入边界，不是建议把所有实验设到极端值。

已部署实验继续用自己的冻结周期，调全局变量不会偷偷改旧约定；若希望同时调整旧任务，请明确告诉 Agent，并保存计划修订。其他项目复制 [config.example](config.example) 为自己的 `config`，不要覆盖已有文件。脚本不再读取旧 `.env`；私有凭据仍应使用独立的秘密配置或连接器。

### 配置网站源码仓库

在 config 的 SEO_REPOSITORY_URL 填无凭据的 HTTPS 地址，例如 `https://github.com/OWNER/REPO`。目前尚未确认实际网站源码仓库，留空，不拿本流程仓库冒充目标。脚本校验并返回地址，不连接 GitHub，也不证明权限。

Agent 使用已授权 GitHub 连接或本机登录检查目标仓库读取权限，推送前再确认写权限。令牌和 SSH 私钥不写入 config。每次改动记录完整 commit ID、仓库链接和改前基线；未提交就保留 Diff 并明确说明，不擅自提交。合并、部署和线上生效分别核实。

### 填写你认为正确的关键词

编辑 [seo-keywords.json](seo-keywords.json)：

- `primary`：你希望优先优化的词，如 `["你的主关键词", "另一个主关键词"]`。
- `secondary`：辅助词/长尾词。
- `excluded`：不想主动优化的方向。
- `page_targets`：可选页面映射，如 `{"/目标页面": ["对应关键词"]}`。
- `notes`：语言、目标用户和业务侧重点。

当前实际词表为空，没有替你猜关键词。Agent 保留你的方向和原词，核实产品事实、搜索意图及现有页面，再说明采用/待验证/不适合的原因；不是把所有词塞进 title，也不自动为每个近义词建页。改词表不替换旧实验已冻结的查询组。

### 记忆与执行边界

所有决策记忆均为 Markdown，不使用数据库、实验 JSON 或 YAML 状态表。可参考 [改动记录模板](skills/seo-front-loop/assets/改动记录模板.md)。接管实际站点后，按 [文件记忆协议](skills/seo-front-loop/references/protocol.md) 保存当前实验、完整修订历史、证据和每轮决策；默认目录 `.seo-memory`，所有相关任务共用且需要私有备份。现在尚未创建真实站点记忆，缺少目录不代表从未修改过网站。

文件模式适合单写入者、人工控制发布；不提供并发硬锁，需要并发或自主发布时另行设计。这个 Skill 不会自动定时醒来，配置日期也不会创建自动化。未授权时不连接账户、不部署、不启动旧自治循环。

### GSC / PostHog 数据工具

已提供 [tools/collect_metrics.py](skills/seo-front-loop/tools/collect_metrics.py)，用法和授权见 [数据工具说明](skills/seo-front-loop/references/data-tools.md)。config / config.example 已列出资源地址、项目 ID、授权方式及凭据环境变量说明；当前真实账户值留空。

运行 `python3 skills/seo-front-loop/tools/collect_metrics.py --project .` 只检查缺项，不联网。Skill 会向用户收集缺失的非敏感信息，提醒在安全环境完成授权；用户可仅启用 GSC 或 PostHog。经授权使用 `--check-access` 检查真实读取权限，再用 `--collect --start 日期 --end 日期` 采集。

GSC 保存日总量和页面/查询日明细；PostHog 当前只提供日级事件次数，不是自然搜索归因漏斗。`--output` 独占新建私有证据快照，不覆盖旧基线；解释和决定仍写 Markdown。工具已做离线测试，尚未完成真实账户联调，不会自动安装依赖、登录或创建定时任务。

### 本地验证

在本项目目录运行（Python 3.9+，标准库，无第三方运行依赖）：

```bash
python3 skills/seo-front-loop/scripts/seo_context.py --project /Users/shixianglong/Desktop/seo/seo-front-loop
python3 -B -m unittest discover -s skills/seo-front-loop/scripts -p 'test_*.py' -v
python3 -B -m unittest discover -s skills/seo-front-loop/tools -p 'test_*.py' -v
```

Agent 先读 Markdown 原记录，再添加 `--live-verified-at 2026-09-09T10:00:00+08:00 --interval-days 20 --max-checks 3` 计算日期（仅为示例）。三个参数必须同时明确提供，不以当前配置替代旧约定。脚本不解析记忆、不判断可否修改，不计算 SEO 收益；输出 JSON 只是临时工具结果。测试不等于真实站点行为验收。

目标：把旧 `seo-agent` 的 SEO 工作拆成可由 Codex 执行、可复盘、可恢复的任务；保证下一轮知道以前改过什么、哪些正在观察、哪些方案失败过，避免无证据地 A→B→C→A。

| 文档 | 内容 |
| --- | --- |
| [总体方案](docs/PLAN.md) | SEO 范围、工作流拆分、Codex 分工、实验设计、旧项目迁移及潜在问题 |
| [记忆与防反复修改协议](docs/MEMORY_SPEC.md) | 自然语言历史、提交追溯、观察限制、防重复、重新立项、恢复 |
| [执行手册与验收](docs/RUNBOOK.md) | 可交给下一次 Codex 的启动说明、逐步实施任务、样例、验收场景 |

核心约束：每次写代码前、发布前都查询历史；观察期冻结实验影响范围；成功改动默认保留；无新证据不重做；允许有记录的必要回滚；没有合适实验时可以整轮不修改。

本项目目录是 `/Users/shixianglong/Desktop/seo/seo-front-loop`。父目录 `seo` 用于容纳多个项目；本项目的说明、方案和后续实现放在本目录内。代码审计来源是另一个项目 `/Users/shixianglong/Desktop/seo-agent`；它不是本项目，也不是已确认的产品源码目录。新方案尚未确定实际产品源码路径与生产部署方式，不沿用旧配置作为默认授权。

返回 [SEO 项目集合](../README.md)。


Blog 选题、查重、结构与写作使用 [`$blog-generator`](skills/blog-generator/SKILL.md)。它在批准新 URL 前检查 live、archived、merged、redirected 库存和相近正文；库存不完整时只允许研究、更新/合并建议或延期，不允许把候选标为可发布。该 Skill 负责内容决策和草稿，发布、冻结与效果评估继续由 `$seo-front-loop` 管理。
