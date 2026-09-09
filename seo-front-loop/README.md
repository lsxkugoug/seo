# seo-front-loop

由 Codex 执行的网站 SEO 优化闭环，是 `seo` 项目集合中的一个独立子项目。

顶层设计：默认由一个 Codex Agent 串行完成观察、决策、执行、自检和评估，使用同一份共享 SEO 档案及数据、代码、验证工具。是否调用子 Agent 由主 Codex 根据任务独立性、复核价值和成本决定；不开子 Agent 也能完成普通实验，不设置固定的多 Agent 流水线。

状态：已有可复用 Skill、配置/关键词读取与复查日期计算脚本；完整 Harness、指标账户连接和生产发布尚未实现。设计日期：2026-09-07，当前版本 v1.3（2026-09-09）。

设计更新：2026-09-08，统一为“单 Agent 串行优先，Codex 按需委派”。高风险或历史重复例外所需的独立复核，按明确规则由子 Agent 或人工完成；普通改动不强制另开 Reviewer。

范围设计：按摘要、内容、结构、内链、结构化数据、抓取索引、性能、页面生命周期分八类；先区分修复、优化实验和结构性项目。一次完成一个最小完整干预，分别约定可编辑范围、实际影响范围和评估/冻结范围；组合改动保存整体与成员历史，不把整体效果误记为每个成员的独立效果。详见总体方案第 3 节。

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
SEO_REVIEW_INTERVAL_DAYS=20
SEO_REVIEW_MAX_CHECKS=3
SEO_KEYWORDS_FILE=seo-keywords.json
SEO_MEMORY_DIR=.seo-memory
```

默认部署确认后第 20/40/60 天复查；例如将间隔改为 10，则新实验第 10/20/30 天复查。到期不是必须判胜、更不是必须改站；最后仍无结论则保留正确版本并关闭常规等待，部署未知或事故未恢复先对账。

优先级是当前进程环境变量 > 项目 `config` > 默认值，Agent 能从脚本输出看到来源。无需 `source config`；脚本主动读文件且不执行其中内容，避免依赖桌面应用是否继承终端环境。支持整数天 1–365、检查点数 1–12；这些是输入边界，不是建议把所有实验设到极端值。

已部署实验继续用自己的冻结周期，调全局变量不会偷偷改旧约定；若希望同时调整旧任务，请明确告诉 Agent，并保存计划修订。其他项目复制 [config.example](config.example) 为自己的 `config`，不要覆盖已有文件。脚本不再读取旧 `.env`；私有凭据仍应使用独立的秘密配置或连接器。

### 填写你认为正确的关键词

编辑 [seo-keywords.json](seo-keywords.json)：

- `primary`：你希望优先优化的词，如 `["你的主关键词", "另一个主关键词"]`。
- `secondary`：辅助词/长尾词。
- `excluded`：不想主动优化的方向。
- `page_targets`：可选页面映射，如 `{"/目标页面": ["对应关键词"]}`。
- `notes`：语言、目标用户和业务侧重点。

当前实际词表为空，没有替你猜关键词。Agent 保留你的方向和原词，核实产品事实、搜索意图及现有页面，再说明采用/待验证/不适合的原因；不是把所有词塞进 title，也不自动为每个近义词建页。改词表不替换旧实验已冻结的查询组。

### 记忆与执行边界

接管实际站点后，按 [文件记忆协议](skills/seo-front-loop/references/protocol.md) 保存当前实验、完整修订历史、证据和每轮决策；默认目录 `.seo-memory`，所有相关任务共用且需要私有备份。现在尚未创建真实站点记忆，缺少目录不代表从未修改过网站。

文件模式适合单写入者、人工控制发布；需要并发或自主发布时再实现受控账本。这个 Skill 不会自动定时醒来，配置日期也不会创建自动化。未授权时不连接账户、不部署、不启动旧自治循环。

### 验证工具

在本项目目录运行（Python 3.9+，标准库，无第三方运行依赖）：

```bash
python3 skills/seo-front-loop/scripts/seo_context.py --project /Users/shixianglong/Desktop/seo/seo-front-loop
python3 -B -m unittest discover -s skills/seo-front-loop/scripts -p 'test_*.py' -v
```

检查某个已保存实验的日期时，为第一条命令添加 `--record /绝对路径/实验.json`。日期根据实验冻结值计算，脚本只读，不写状态、不查重、不计算 SEO 收益、不自动解锁。它的测试不是下方执行手册中完整 Harness 的验收。

目标：把旧 `seo-agent` 的 SEO 工作拆成可由 Codex 执行、可复盘、可恢复的任务；保证下一轮知道以前改过什么、哪些正在观察、哪些方案失败过，避免无证据地 A→B→C→A。

| 文档 | 内容 |
| --- | --- |
| [总体方案](docs/PLAN.md) | SEO 范围、工作流拆分、Codex 分工、实验设计、旧项目迁移及潜在问题 |
| [记忆与防反复修改协议](docs/MEMORY_SPEC.md) | 持久化结构、完整版本历史、锁、重复检测、重新立项、断点恢复 |
| [执行手册与验收](docs/RUNBOOK.md) | 可交给下一次 Codex 的启动说明、逐步实施任务、样例、验收场景 |

核心约束：每次写代码前、发布前都查询历史；观察期冻结实验影响范围；成功改动默认保留；无新证据不重做；允许有记录的必要回滚；没有合适实验时可以整轮不修改。

本项目目录是 `/Users/shixianglong/Desktop/seo/seo-front-loop`。父目录 `seo` 用于容纳多个项目；本项目的说明、方案和后续实现放在本目录内。代码审计来源是另一个项目 `/Users/shixianglong/Desktop/seo-agent`；它不是本项目，也不是已确认的产品源码目录。新方案尚未确定实际产品源码路径与生产部署方式，不沿用旧配置作为默认授权。

返回 [SEO 项目集合](../README.md)。
