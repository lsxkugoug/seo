# seo-front-loop：Codex 执行手册与实施验收

版本：v1.3，2026-09-09。默认由单 Codex 串行工作，是否委派子 Agent 由主任务按总体方案第 5 节决定。已提供可复用 Skill、只读配置/日期脚本及离线单元测试；下述 Harness 接口仍待实施。未创建调度、数据库、账户连接或发布权限。

## 1. 新任务启动说明

现在可先使用 `$seo-front-loop` 加管理项目绝对路径进行只读研究/复查；配置方法见 [README](../README.md)。每轮读取 `config` 和 `seo-keywords.json`，检查点默认第 20/40/60 天，真实记录使用冻结配置。安装 Skill 不代表已经实现下述 P0/P1 服务或接管某个站点。

后续用户决定实施时，可把下面这段交给 Codex。第一步只建立方案里的基础设施，不直接做 SEO 改动：

> 工作目录是 /Users/shixianglong/Desktop/seo/seo-front-loop，旧代码参考目录是 /Users/shixianglong/Desktop/seo-agent。父目录 seo 是多项目集合，不是本子项目的工作目录。
> 先阅读 README.md、docs/PLAN.md、docs/MEMORY_SPEC.md 和本执行手册。
> 本轮实施 P0/P1：站点配置契约、实验账本、完整版本历史、防重复门禁、资源预约、上下文生成和恢复测试。
> 复用旧项目经过核实的采集逻辑，不运行旧的自治增长循环。
> 未有真实网站与部署配置时使用明确标识的测试站点和测试数据，不能猜测生产账户或把示例视为线上事实。
> 默认由一个 Codex Agent 串行完成本轮；只有遇到独立研究或第二视角审查、且交接和成本值得时，请按需委派子 Agent，由主 Codex 决定是否触发。不开子 Agent 也应能完成普通流程；不要固定分派 Builder、Reviewer、Evaluator。账本和生产部署只走统一服务，独立复核条件按 PLAN.md 第 5 节执行。
> 第一阶段不启用自动发布。完成后报告实现内容、通过和未通过的验收场景，以及下一步真实配置要求。

实施阶段再把“先读规则→查账本→检查允许动作”的简短入口写入项目 `AGENTS.md`。不要只把整份设计贴进去，导致每次任务上下文被长文档挤满。`AGENTS.md` 用于启动指导，完整约束仍由工具/CI 执行。[Codex AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

## 2. 一期需要实现的最小工具

以下名称是建议接口，不是当前可运行命令。可以用一个 Python CLI 或小型本地服务承载，不要求立即建 MCP 服务。

| 接口 | 输入 | 返回与副作用 |
| --- | --- | --- |
| `site.inspect` | site_id、产品路径 | 配置完整性、只读运行状态；不吐出密钥 |
| `evidence.collect` | 站点、来源、明确窗口/维度 | 不可变 snapshot、质量与完整性、工件校验 |
| `memory.context` | site_id、目标资源、任务类型 | 权威 revision、活动限制、相关历史引用、允许动作 |
| `experiment.propose` | 版本化实验规范 | 保存候选及去重键；不发布、不占长期观察锁 |
| `experiment.reserve` | 候选、expected_revision | 原子完整历史检查与资源预约；返回许可或明确阻断原因 |
| `experiment.record-checks` | 许可、commit/diff hash、检查回执 | 记录验证结果；不能由 Builder 自报通过代替实际检查 |
| `release.preflight` | 许可、当前基线、Diff、审查/授权引用 | 重新检查影响范围和历史，产生绑定准确版本的部署意图 |
| `release.reconcile` | deploy_intent、部署回执、线上证据 | 确认部署与线上暴露，或等待/失败；崩溃恢复也走此入口 |
| `experiment.evaluate` | 实验、最终数据快照 | 由固定计算程序生成评估材料；无改站副作用 |
| `experiment.decide` | 评估、retain/rollback 等决定与依据 | 原子写结果、保护规则、下一步；回滚另建动作 |
| `run.finish` | run_id、当前游标、下次条件 | 保存 no_change/完成/等待/阻断以及精简报告 |

一期优先实现 memory.context、reserve、版本/策略查询、状态转换和 reconcile 的可测试行为。所有写接口必须支持幂等键与 revision 检查，返回结构化错误码而非让 Codex 从异常文字猜测。

## 3. 实验规范样例

虚构测试样例，目标 URL、ID、日期、数值均不能直接用于真实生产。`null` 代表待填项，门禁必须拒绝带必填空值的发布申请。

```json
{
  "schema_version": 3,
  "experiment_id": "demo-title-001",
  "site_id": "demo-site",
  "page_id": "demo-page",
  "status": "proposed",
  "action_kind": "experiment",
  "work_kind": "experiment",
  "primary_category": "metadata",
  "intervention_unit": "demo 页的 title 使用场景表达",
  "attribution_unit": "single_intervention",
  "hypothesis": "现有 title 没有清楚表达页面已经支持的使用场景，可能影响相关查询的点击选择",
  "primary_edits": [{"resource_id": "page:demo-page", "field": "metadata.title"}],
  "required_supporting_edits": [],
  "change_scope": ["metadata.title"],
  "forbidden_changes": ["正文", "description", "内链", "价格", "canonical"],
  "impact_resources": ["page:demo-page"],
  "impact_evidence": null,
  "frozen_resources": ["page:demo-page"],
  "measurement_scope": {
    "treated_pages": ["demo-page"],
    "query_cohort_version": "demo-cohort-v1",
    "guardrail_pages": ["demo-page"]
  },
  "engineering_acceptance": ["仅目标页实际 title 按批准值变化", "构建、渲染及事实检查通过"],
  "query_cohort_version": "demo-cohort-v1",
  "evidence_snapshot_id": "demo-snapshot-v1",
  "before_variant_id": "demo-A",
  "after_variant_id": "demo-B",
  "strategy_key": "existing-use-case-clarity",
  "keyword_config_snapshot": null,
  "keywords_hash": null,
  "review_policy": {"interval_days": 20, "max_checks": 3},
  "live_verified_at": null,
  "reviews": [],
  "memory_revision": null,
  "source_base_commit": null,
  "primary_metric": "gsc_ctr_fixed_cohort",
  "guardrail_metrics": ["page_total_clicks", "qualified_organic_conversions"],
  "conversion_measurement_available": false,
  "country_device_filters": null,
  "baseline_window": null,
  "measurement_start_rule": null,
  "control_cohort": null,
  "estimator_version": null,
  "minimum_meaningful_effect": null,
  "planned_evaluation_dates": null,
  "sample_feasibility_result": null,
  "max_days_from_live_verification": 60,
  "reopen_of": null,
  "authorization_ref": null,
  "rollback_target_variant_id": "demo-A"
}
```

如果转化数据不可用，必须明确批准仅做流量实验、移除不能执行的转化硬保护或补齐测量；不能在结果中假装验证过该指标。对照为空时也必须填明采用描述性分析及其限制，不能靠 null 绕过方法选择。

冻结后的规范修改必须创建新 revision：改主要指标、查询集合、对照、时间窗或干预范围都要留痕；上线后不得用改规范来美化原结果。

本样例中的 SEO 指标、窗口等字段共同组成范围卡的 `seo_evaluation`，不再维护第二份重复的评估计划；查询组引用必须一致。补入对照后，保护资源也要相应补齐。`impact_evidence=null` 表示尚未证明实际影响范围，不能发布。

成员前后值与策略在 variants/changes 中保存，组合方案另保存 bundle_id 和整体快照。修复与结构项目使用各自工程验收与权限契约，不把本 title 实验样例的 CTR、样本量或等到复查日的要求强塞给必要修复；参考 MEMORY_SPEC 第 3、4 节。planned_evaluation_dates 在 live_verified_at 确认后按冻结 review_policy 派生；最大天数必须等于 interval_days×max_checks。关键词快照需保存真实用户词表（可明确为空），不能用空引用冒充已核对方向。

## 4. 每轮操作协议

### Observe

- 读取站点配置和账本 revision；对账线上版本与未完成发布。
- 拉取需要刷新的数据，不因某个可选来源缺失而重跑全部步骤。
- 发现未知改动、采集异常或技术故障，建立关联记录。
- 输出到期实验、新数据摘要、阻断项和 next_check_at；不生成“必须修改”的任务。

### Decide

- 优先处理到期评估和事故，不先给所有页面重新写文案。
- 对可修改候选调用历史检测，保留被拒绝原因和重开条件。
- 主 Codex 默认自行研究；发现可独立完成且有收益的子任务时，才按需委派最多两个只读子 Agent，交付同一证据快照和相关历史。
- 合并事实与反证，择一可测量干预，或明确 no_change。
- 按八类修改方向选择主类别，先判 repair/experiment/structural_project；列明干预、编辑、影响、评估与保护四个边界。配套改动逐项说明必要性，多个独立优化不得以共同“提升 SEO”为由打包。
- 提案需列出“和历史方案相比的新证据”，仅换措辞不得过关。

### Execute

- 原子预约资源；主 Codex 在编码阶段获取批准规范、记忆上下文和隔离代码基线，不另开固定 Builder。
- 编码完成后检查实际 Diff 是否越界；需要变更范围时返回 Decide。
- 检查实际渲染/依赖影响，而非仅核对文件白名单；公共组件的一行变更也可能扩大到整组页面。修复中断观察时走关联 Incident 记录，不静默解除锁。
- 主 Codex 编码后自检来源、当前规则、代码与页面效果，记录 review_mode=self。触发独立复核条件时，由未参与起草的子 Agent 或人工复核并记录相应模式；不能把自检写成独立审查。
- 测试通过后重查历史、资源、源码和生产版本。没有发布权限则交付可审查结果与单个明确待授权动作。
- 有权限时通过独立发布入口完成部署，保存线上指纹并开始预约中的观察状态。

### Evaluate

- 检查是否真正部署、搜索侧暴露是否充分、数据是否完整、有无干扰。
- 程序按冻结规范计算；同一个主 Codex 在评估阶段描述证据和限制，不凭 confidence 判胜，也不必另开 Evaluator。
- 保存 observed_result、causal_strength、操作决定及下一步条件。
- 工程修复成功和 SEO 结果分开；组合结果只记在组合层，成员独立效果标未知。新页/迁移看相关意图组与新旧 URL 的总变化，不能把旧页流量搬到新页当作净增长。
- 保留当前版本时写 stable 或 observe-no-change 限制；要回滚时引用具体实验和当前基线。
- 无新条件时，本轮可以完全不修改网站。

## 5. 每次交付给用户的简报

```text
本轮结论：不修改 / 提交实验 / 等待观察 / 需要处理异常
已确认线上版本：...
上次修改：哪个页面、哪个字段、A→B、为何修改、何时上线
本轮修改：没有，或具体改动及实验 ID
修改性质与边界：哪一类、修复/实验/结构项目；主改动、必要配套、影响及冻结谁
本轮没做的建议：哪些因观察锁、历史重复、无新证据而被拒绝
当前证据：数据窗口、完整性、结果与归因限制
下一次允许做什么：评估 E1 / 补数据 / 在某条件成立时重开
下次检查：日期或外部事件条件
关联记录：实验、Diff、部署、评估
```

示例：`首页 title 仍为 B。E1 正在观察，本轮拒绝 B→C；它没有新证据且会污染 E1。正式评估在约定数据完整后进行。` 这比输出一页新建议更能表达系统正在有效工作。

## 6. 实施任务与验收门槛

### P0：建立站点基线

产物：无秘密的站点配置、产品路径/部署映射、线上快照、历史导入报告、缺失信息表。

验收：明确 `seo` 是多项目集合、`seo/seo-front-loop` 是本 Harness 子项目、`seo-agent` 是参考代码、真实产品仓库另行识别；能说明哪个程序有生产写权限。未接数据和部署时只允许离线测试。

### P1：记忆与状态服务

产物：版本化 SQLite schema、追加事件、资源关系、Context Packet、准入检查、恢复流程、可重放的测试夹具。

验收：下面表中的 T01–T17 及 T29–T36 的离线范围/记忆夹具均通过；后者不意味着一期开放结构项目发布。Builder 不可直接修改权威状态，门禁不可仅依赖提示词。若一期环境无法隔离发布凭据，明确保持人工发布，不称已实现自主发布安全。

### P2：只读研究试跑

产物：同一份脱敏证据上，旧方案参考产出与单 Codex 串行产出的比较；仅在出现具体委派需求时补充子 Agent 协作结果。

验收：单 Agent 可完成普通流程；比较可核验事实错误、重复建议、遗漏历史、范围膨胀、耗时与成本。自检或复核必须识别同源证据重复计数；若使用了子 Agent，记录它解决的具体问题，不以篇幅或 Agent 数量衡量质量。

### P3：一次完整真实实验

产物：可测量性评估、冻结规范、检查记录及 review_mode、代码 Diff、部署回执、线上快照、观察和最终评估；只有触发条件时要求独立复核。

验收：一个完整观察周期；中途换任务能继续、锁有效、没有额外 SEO 改动。工程正确不等于效果 positive，允许最后是 inconclusive。

### P4：有限扩大

产物：最多 3 个不共享影响范围的活动实验，定期复核因果限制和业务结果。

验收：持续无重复/越界发布，记忆与线上对账一致；多数实验不可测或成本高于价值时收缩，不能持续增加 Agent 或改动数量掩盖问题。

## 7. 必须用测试证明的场景

| 编号 | 场景 | 正确行为 |
| --- | --- | --- |
| T01 | A→B 已上线，下一轮建议 B→C，E1 未结束 | 拒绝写入，保持 B 和观察预约 |
| T02 | A→B→C 发生在历史中，新候选回 A | 检出完整祖先，要求 rollback/retest 记录；不自动当新实验 |
| T03 | A 已在很久以前，超过模型摘要或旧查询 limit | 完整索引仍能检出，摘要截断不影响拒绝 |
| T04 | 候选 A' 与 A 同策略但只是近义文本 | 标记疑似重复并要求复核；不能 hash 不同就通过 |
| T05 | 完全相同 evidence 换 ID 再交同一个提案 | 内容与意图去重，不算新证据、不重复创建实验 |
| T06 | 两个任务同时预约同一页/共享组件 | 事务只允许一个成功，另一个拿到冲突记录 |
| T07 | 审批后 Diff 或基线变了 | 旧许可失效，重新检查与审查 |
| T08 | 数据源失败、最新日未最终确定、目标行缺失 | 质量标记并暂停结论；不填零、不覆盖良好快照 |
| T09 | Build 成功但实际没有部署 | 不开始观察、不记录已暴露、不评估 SEO 效果 |
| T10 | 部署完成后进程在落账前崩溃 | 重启先对账同一 commit/幂等键，恢复事件，不重复发布 |
| T11 | 租约过期，但线上实验仍在观察 | 可接管工作租约，观察预约不释放；旧 token 写入被拒绝 |
| T12 | 人工发布改了实验页，或改共享模板污染对照 | 写 external_change，标污染；不静默覆盖人类修改 |
| T13 | C 出现确定错误，需要恢复 B，但历史规则阻断旧版本 | 通过显式 rollback/correction 流程；保留错误历史，禁止下一轮无证据重试 C |
| T14 | URL 或组件移动，页面身份不变 | 继承历史和活动限制；不能当新页面绕过 |
| T15 | 关闭聊天、换任务、重启服务或恢复备份 | 仍能恢复当前线上版本、完整相关历史、锁和下一步 |
| T16 | 评估期结束但样本不足，模型却报告高 confidence | 记录 insufficient/inconclusive，不升为成功策略；达到上限结束等待但不自动重改 |
| T17 | 计划修改标题，实际 Diff 还包含正文/公共 SEO 模板 | 阻断范围越界，重新确认影响资源，不能只看文件数 |
| T18 | 品牌营销上涨，页面点击与对照都涨 | 降低因果解释，不把全站增长都归功于页面实验 |
| T19 | Google 仍显示旧/重写标题 | 记录暴露不确定，按计划等待或关闭，不能连续改标题催收录 |
| T20 | 两个评估任务对同一实验写入不同结论 | revision/幂等控制；后续更正以 supersedes 留痕 |
| T21 | 旧 FAQ rich result 规则再次被提议 | 当前规则检查识别来源失效，不能生成虚假收益假设 |
| T22 | 回滚时当前版本包含其他人的后续代码 | 检查逆向 Diff 和冲突；保留后续代码或交人工处理，禁止整个文件覆盖 |
| T23 | 缺少历史档案或工件校验失败 | 标 memory_incomplete，研究可以继续，相关写入暂停 |
| T24 | 稳定版保护时间已过，但没有新证据 | 仍保持不修改；时间本身不算重开依据 |
| T25 | 首次接管缺乏旧历史，或接管后丢了账本 | 首次可显式建立有边界的基线；后者必须恢复，不能重置基线清空限制 |
| T26 | 普通低风险实验，未启动任何子 Agent | 单 Codex 串行完成全部阶段，检查记录为 self，不因缺少独立 Reviewer 阻断 |
| T27 | 有独立资料研究且委派收益明确 | 主 Codex 自行决定委派并记录范围与理由，汇总核验后继续，不建立固定 Agent 队伍 |
| T28 | 独立复核条件已触发，但主任务只完成自检 | 保留未满足的复核条件；需子 Agent 或人工复核，不能伪报 independent_agent |
| T29 | 仅改一个公共模板文件，但实际改变 100 个页面 | 按真实消费者扩大影响/保护范围；不能按单页小实验批准，适用高影响独立复核 |
| T30 | 一套导出说明需要小标题、步骤、配图与模块样式，涉及四个文件 | 必要依赖明确且批准范围一致时可作为一个完整内容干预；不能因文件多而拆成无意义实验 |
| T31 | title 实验顺带优化图片加载或 CTA 文案 | 识别独立干预，阻断越界；拆开或重新批准为有明确理由的组合，不能偷偷纳入配套 |
| T32 | 已核实的错误 noindex 需要修复，但无 GSC 数据且原页正在观察 | 既有事故权限下允许必要恢复并记录中断；工程成功与 SEO unknown 分开，未授权不能仅改 work_kind 绕过 |
| T33 | 内链目标页未改文件，或来源页原本是对照 | 两端仍纳入实际影响；受影响对照不得作为未处理组，必要时换对照/降级归因 |
| T34 | 组合上线后增长，或下一轮改名/拆成多轮重放旧组合 | 不生成各成员独立成功规则；通过整体与成员历史检出重复，按新证据重开而非按名称放行 |
| T35 | 新页获得 100 点击，同意图旧页减少 100 点击 | 结合预定义群组、背景和口径评估净变化，不能仅报告新增 100；迁移继承新旧 URL 历史 |
| T36 | 内部重构没有搜索或用户暴露变化，或 shared 文件只影响一个明确消费者 | 用依赖/渲染检查证明范围；前者不记 SEO 干预，后者不无依据锁全站；未知影响不得按无影响通过 |

测试可以证明流程约束有效，不能证明未来排名会提高。真实收益需要 P3/P4 的完整数据和独立结果审查。

## 8. 当前交付边界

本次完成了方案、记忆设计、任务协议、验收标准及可复用 Skill（含配置读取、关键词校验、冻结日期计算与离线测试）。新增本地 Skill 发现入口不等于修改全局记忆设置。未创建真实实验或记忆账本、未连接账户、未调用付费 SEO API、未改变产品代码或线上内容、未启动自治循环。

Skill 脚本单元测试与第 7 节 T01–T36 的未来 Harness 验收是不同层级；脚本测试通过不代表这 36 项已实现，也不证明 SEO 收益。

下一项有价值的工程工作是 P0/P1：先实现可靠的“知道过去发生了什么，以及现在不能做什么”，再让 Codex 拿到改站权限。
