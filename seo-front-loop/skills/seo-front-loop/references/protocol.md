# 持久记忆、周期与执行边界

## 配置

显式传 `--project`，不从 Skill 安装位置猜管理项目。配置优先级：当前进程环境变量 > 管理项目 `config` > 默认值。config 是可提交 Git 的 KEY=VALUE 明文配置，不用于保存密钥。脚本只读取四个 SEO 设置，不执行 shell、不展开变量、不输出其他环境变量或密钥。

| 变量 | 默认值 | 含义 |
| --- | --- | --- |
| SEO_REVIEW_INTERVAL_DAYS | 20 | 复查间隔，整数天，支持 1–365 |
| SEO_REVIEW_MAX_CHECKS | 3 | 最多检查点数，支持 1–12；默认最晚第 60 天结案 |
| SEO_KEYWORDS_FILE | seo-keywords.json | 用户词表，相对路径按管理项目解析，也可显式绝对路径 |
| SEO_MEMORY_DIR | .seo-memory | 持久记忆目录，同一站点所有任务/worktree 共用；不是临时目录 |

上述范围是输入保护，不是 SEO 推荐值。真实日历日按 UTC 24 小时计算，可本地时区展示。测试时间 `--now` 仅用于离线夹具，不能用于提前释放真实实验。管理项目 `config` 是脚本自己的输入，不声称 Codex 自动加载它；当前进程环境覆盖必须在报告中说明来源。脚本不读取旧 `.env`，也不执行 `source config`。

当前配置用于新提案。立项保存冻结 `review_policy`、关键词完整快照/hash 和查询集合版本；发布前若配置改变，解释差异并重新确认方案，不能自动替换已批准计划。部署后改变 `config` 只影响新实验；对旧实验的显式计划修订要保留前后值、原因、用户要求及批准，禁止追溯挑选更好看的窗口。

## 账本选择

已有受控账本服务时使用它作为唯一权威来源，不另写一份独立文件账本。尚无服务时，可在明确单写入者、人工控制发布的试点中使用下列文件协议。它是合作约束，不提供原子跨进程预约、强制防篡改或完整自动化安全保证。并发写入/无人自主发布需求出现时先升级受控服务。

```text
<SEO_MEMORY_DIR>/
  site.json                    # 站点、产品仓库、已知历史边界、接管证据、唯一 writer 约定
  experiments/<id>.json         # 当前方案、状态、期限、冻结范围、稳定/重开条件
  history/<id>/<revision>.json  # 每次状态/计划修订的完整快照，不覆盖旧文件
  evidence/<id>/                # 脱敏数据、Diff、线上回执、事实来源
  runs/<run-id>.json            # 本轮 no_change/提案/评估、拒绝理由与下次条件
```

只有用户要求初始化/实施时才创建真实状态，Skill 安装不等于接管某站点。首次接管先核对真实站点、线上快照、代码/部署历史与已知活动工作，记录 `history_known_since`、缺口、`baseline_adopted` 及依据。不知道旧历史就如实说明，不能伪造过去；接管后的文件缺失/损坏必须恢复，不得重新初始化以清空限制。

实际状态放在私有持久目录，禁止把密钥或原始用户查询/支付数据提交公共 Git。自定义目录时也要配置忽略/访问控制和私有备份；`.gitignore` 不是备份。备份需同时覆盖历史和引用证据，并核实可恢复。

## 修改前必须知道

用稳定 site/page/resource ID 和 URL 别名关联历史，不因重命名、迁移、换文件路径重置身份。查目标、内链两端、共享影响、相关意图及对照的所有历史；模型摘要可以精简，完整查重不能只取最近几条。

记录并核对：

- 当前真实线上版本、未完成部署、人工/其他系统变动。
- 每个字段/模块和组合的前后原值、内容 hash、语义策略、父版本、实际是否上线。
- 拒绝、失败、回滚、无结论的证据与重开条件。
- 活动冻结、对照保护、stable、未来检查点；默认关闭后 14 天保护，同页滚动 90 天第 3 次常规实验需独立复核。到期只是允许重新检查，不等于授权修改。

当前值相同记 no_op；历史祖先、近义重写或旧失败策略需要显式重开。新增证据应是事实/意图/可测量条件发生实质变化，换模型、换措辞、换关键词文件或时间过去不自动成立。明确业务方向调整可作为重新研究依据，但仍需处理旧实验和影响冲突。

文件模式更新前重读当前 revision 和线上基线，写新 history 快照后更新当前记录；任一步中断先对账，不覆盖冲突。snapshot 路径必须唯一。没有硬锁，不能宣称“检查了 revision 所以绝对没有竞争”。summary/聊天只用于导航，不反向覆盖历史。

## 实验记录的最小字段

下列是字段契约，非已批准实验。缺少真实站点/授权/基线时只保存 proposed；不要把示例 ID 当成网站。

| 分组 | 必须保存 |
| --- | --- |
| 身份/版本 | experiment_id、site_id、page_ids/aliases、revision、parent_revision、status |
| 原因与范围 | work_kind、action_kind、primary_category、hypothesis、主改动与配套成员、forbidden_changes、impact_resources、frozen_resources、attribution_unit |
| 关键词 | keyword_config_snapshot/hash、用户优先级、实际采用/待验证/不采用理由、固定 query_cohort 与国家/设备口径 |
| 历史与证据 | before/after 原值与 hash、strategy_key、祖先关联、bundle/member IDs、证据引用、重复检查理由、reopen_of |
| 执行 | source_base_commit、diff/commit、工程检查、review_mode、授权引用、deployment_id、live_verified_at、线上证据 |
| 评估 | review_policy、基线/后续窗口、measurement_start_rule、指标/保护指标、方法、样本可行性、干扰记录、reviews |
| 决策 | observed_result、causal_strength、retain/rollback/extend/close_inconclusive、stable/reopen 条件、next_review_at |

日期脚本只读取该记录的少数字段，不是全记录校验器。最小可计算日期的示例（虚构，只用于测试）如下；真实发布不能仅靠这几个字段：

```json
{
  "experiment_id": "demo-only",
  "status": "observing",
  "review_policy": {"interval_days": 20, "max_checks": 3},
  "live_verified_at": "2026-09-09T10:00:00+08:00",
  "reviews": []
}
```

## 复查如何记录

从 `live_verified_at` 固定计算 D×1、D×2、…、D×N。搜索处理慢、流量少不重置起点；第 20 天允许结果“不足以判断”。分析窗口与复查日分开：只使用已完整的数据，保存实际数据截止、处理缓冲和未知暴露。不要因截至第 20 天而把尚未最终确定的日数据算入结论，也不要把 20 天前后直接总量相比而忽略星期组成、季节性和查询变化。

每次 reviews 成员保存 `checkpoint`（从 1 开始）、带时区 `reviewed_at`、数据快照、实际窗口、暴露/质量/污染、结果、操作决定、下次条件。不要每天判胜，亦不要把第 20/40/60 天的累计重叠数据当成三个独立实验；若作正式统计检验，需预先处理重复检验，否则只作有局限的描述性判断。

错过多个检查点时只做一次当前复查，用最新已到期 checkpoint；较早点标 `missed` 并记录当前补记时间，不能编造当时的评估。脚本不会自动补记、关闭或解锁。达到最后检查点仍无结论且没有待恢复事故/未知部署时，记 close_inconclusive 和保留当前正确版本；停止常规循环，但保留 stable/reopen 约束。

修复先验收错误消失，SEO 效果可以 unknown；事故不等复查日。回滚必须对照当前生产基线生成受控逆向改动，不能拿旧文件覆盖后续工作。若部署状态未知或故障未恢复，保持冻结、转 reconcile，不以“到 60 天了”为由释放资源。

## 调度边界

脚本算出日期不等于创建定时器。没有用户调度请求时，记录 next_review_at 并说明需下次调用。用户明确要求自动复查时用宿主原生调度，读取账本到期项，状态无变化保持安静；只报告重要变化、故障或需要用户决策。调度触发也不新增产品部署权限。
