---
name: blog-generator
description: "研究、规划、撰写或审查任何网站的 Blog；从产品、受众、搜索需求和竞品中提出选题，再以内容库存、内链关系、事实和效果数据决定 new、update、merge 或 defer。适用于内容集群、工具型网站、SaaS、服务型网站和知识站；不用于未经核实的批量发文、自动发布或虚构搜索数据。"
---

# Blog Generator

为任何网站寻找值得写、能服务读者且不与现有内容冲突的主题。它先研究可能性，再用内容库存决定是否应建立新 URL；库存是发布门禁，不是选题的唯一来源。可以生成主题地图、brief、提纲、开头、完整草稿、内链计划或内容审查报告。生成草稿、推送到后台和上线是三个不同的动作。

## 先判断本轮模式

- **选题研究**：先读本节和 [选题研究与系统集成](references/topic-research-and-integration.md) 的“发现主题”部分。
- **查重、内链或内容规划**：读 [编辑框架](references/editorial-framework.md)。
- **需要 Semrush、GSC、历史文章 API 或草稿推送 API**：读 [选题研究与系统集成](references/topic-research-and-integration.md) 的对应接口契约。
- **需要 Humanizer、AI 写作或学生写作示例**：再读 [案例与选题库](references/case-library.md)。案例只说明一种垂直场景，不定义本 Skill 的适用范围。
- **验证本 Skill 或接入新站点**：读 [验证协议](references/validation-protocol.md)。

## 开始前

1. 确认网站或产品、目标语言和地区、目标读者、真实能力、业务目标及用户希望得到选题、brief、写作、审查还是系统集成建议。信息不足时列出假设，继续做可验证的研究；不要虚构功能、客户、搜索量、排名或竞品私有数据。
2. 先建立一个简短的 **主题地图**：网站帮助谁，在什么情境下完成什么任务，产品或服务实际能帮助到哪一步，哪些相邻问题需要内容解释而不是产品页面。主题可来自产品事实、客户语言、公开竞品、SERP、站内搜索、支持问题、GSC 查询或关键词工具。
3. 对每个主题写出 `audience_situation`、`reader_job`、`core_answer`、`reader_takeaway`、`proof_material` 和 `boundary`。题材、产品类型和关键词工具会变，但这六项是通用的选题判断单位。
4. 主题通过业务相关性、读者需求、搜索意图、可提供的独有材料、可执行性和重复风险排序。搜索量、Keyword Difficulty、竞品流量和模型评分只能作为证据的一部分，不能代替读者任务或产品事实；不要把某个站点曾用的流量或 KD 区间当作通用阈值。
5. 再读取文章库存中的 live、archived、merged、redirected URL，以及可用正文、canonical 目标和历史内链。最终查重必须阅读最相近候选的正文，不能只比较标题或关键词。
6. 记录 `inventory_coverage`。无法证明库存完整、没有读取关键相近正文或产品/来源证据不足时，可以交付研究和 provisional brief，但 `publish_allowed` 必须为 `false`。

## 从主题到文章，不从关键词直接跳到 URL

优先从以下来源提出假设，再把它们归并为少量主题：

- **产品与业务**：功能如何使用、前后步骤、常见错误、适用边界、实施或购买决策。
- **用户任务**：理解、诊断、执行、比较、核查、恢复或向他人解释一件事。
- **需求证据**：GSC 的真实查询和落地页、Semrush 或其他关键词工具、公开 SERP 的结果类型和问题、站内搜索或支持记录。
- **同行研究**：竞争者已覆盖但本站可用不同任务、材料或产品事实服务的需求；不要改写同行标题或复制其结构作为独立价值。
- **内容维护**：已有页面的过期事实、未兑现承诺、意图变化、查询增长、内容缺口或相互蚕食。

每个候选先判断 `opportunity_type`：`new_demand`、`underserved_job`、`competitor_gap`、`refresh`、`consolidation`、`conversion_support` 或 `support_deflection`。这使“为什么写它”可被审查，也避免把所有研究结果变成新文章。

对候选分别判断：

- `content_disposition: new | update | merge | defer`
- `execution_status: ready | blocked | frozen | needs_evidence`

例如某主题确有需求但与旧文重叠，应为 `update` 或 `merge`；内容决策是 `merge`、而页面处于观察期时，执行状态为 `frozen`。关键词不同、年份不同、换人群标签、换清单数字、换语气或新 slug 都不构成独立价值。

## 防重复与发布门禁

候选检索至少覆盖标题、slug、目标查询、受众情境、读者任务、核心答案、主要步骤、独有材料、canonical、合并和重定向历史。库存较大时先返回 Top 3–5 个候选，但不能把 Top-K 之外的内容假设为不存在。

只有以下条件全部成立时才可批准 `new`：

1. 内容库存与重定向历史覆盖完整；
2. 已读取最相近候选正文；
3. `reader_job`、核心答案或必要阅读产物存在实质差异；
4. 独有材料已经存在，或有可执行、可核验的获取方案；
5. 与旧文的边界能够用一句话说明；
6. 没有通过改年份、受众或标题格式制造差异。

如果站点没有历史文章、历史 API 尚未开放或库存只能部分读取，仍可做通用选题研究和草稿，但不能把某个新 URL 标为已批准发布。

## 规划文章关系与内部链接

按读者下一步需要建立 `prerequisite`、`deeper_explanation`、`evidence_or_example`、`next_action` 四种关系。每条链接记录来源文章、出现位置、目标文章、读者为何需要它和描述性锚文本。

内部链接的目标是让读者和搜索引擎发现相关页面、理解页面关系；不承诺“加链接数量就会增加权重或排名”。核心答案必须留在当前页，不要求文章两两互链，也不为尚未发布的文章生成可点击 URL。需要修改旧文添加回链时，将两端都列入影响范围；冻结或观察中的页面只输出建议，交给 `$seo-front-loop` 判断是否可执行。

## 选择结构、开头与产品入口

先选读者任务，再选文章结构。写作前完成一次 **SERP 结构审计**：在目标地区、语言和设备下查看自然结果前 10 个页面，忽略广告，记录结果共同回答的任务、页面类型、反复出现且服务该任务的内容块、证据形式、媒体/工具形式，以及读者仍未被充分服务的问题。将共同需求吸收进提纲，但不能逐篇复制标题、段落或 FAQ；若 SERP 与关键词工具的意图标签冲突，以实际结果和读者任务为准，并记录冲突。

教程、诊断、比较、案例、核查与观点文章使用不同推进顺序。统一要求是：读者快速认出问题，尽早得到有用信息，看见依据，理解如何行动，并知道合理的下一步。

开头优先使用真实且与正文有关的材料：具体症状、微型对照、关键问题、选择情境、结果或矛盾。开头承诺必须映射到正文中的实际段落；不得虚构第一手经历、实验、用户故事、数据或引语。

提纲中的每个主要段落都应标明它解决的子问题、所需证据或例子、以及适合读者理解的呈现形式。插图、截图、GIF、表格和视频用于展示步骤、状态或差异时才加入；它们不能替代答案，也不能只为凑数量。发布前同时检查标题、URL、首段、标题层级、描述性内外链、图片替代文本、页面加载与移动端可读性；具体技术字段应由站点的发布系统或 SEO 规范提供，不能凭空声称已优化。

产品或工具 CTA 只在产品确实帮助读者完成当前步骤时出现。内容页可以链接工具，工具页也应链接解释其任务、边界与下一步的指南；不因增加转化入口而打断文章主任务。

## 输出契约

每个候选先输出以下结构，再按用户需要补充 brief、提纲或正文：

```yaml
topic_source: product | user_language | gsc | keyword_tool | serp | competitor | existing_content
opportunity_type: new_demand | underserved_job | competitor_gap | refresh | consolidation | conversion_support | support_deflection
candidate_title: ""
content_disposition: new | update | merge | defer
execution_status: ready | blocked | frozen | needs_evidence
publish_allowed: false
evidence_summary: []
keyword_research:
  status: unavailable | partial | complete
  target_location: ""
  intent: ""
  metrics_observed_at: null
intent_cluster: ""
inventory_coverage:
  status: complete | partial | unknown
  snapshot_id: null
  live: null
  archived: null
  merged: null
  redirected: null
closest_candidates:
  - url: ""
    status: live | archived | merged | redirected
    body_reviewed: false
    overlap: ""
collision_reason: ""
audience_situation: ""
reader_job: ""
core_answer: ""
reader_takeaway: ""
unique_contribution: ""
proof_material: []
missing_evidence: []
boundary: ""
opening_direction: ""
structure: []
relations: []
measurement_plan:
  gsc_status: unavailable | proposed | configured
  primary_metric: ""
  protection_metrics: []
serp_audit:
  status: unavailable | partial | complete
  observed_at: null
  market: ""
  organic_results_reviewed: 0
  dominant_intent: ""
  recurring_content_blocks: []
  underserved_reader_need: ""
integration:
  inventory_api_status: unavailable | partial | complete
  proposal_push_status: not_requested | ready | pushed | failed
```

当 `inventory_coverage.status != complete`、关键相近正文尚未读取或必要证据缺失时，不得把 `publish_allowed` 改为 `true`。推送草稿到后台只表示交接成功，不表示已经发布。

- **选题研究**：输出主题地图、需求证据、少量分工清楚的候选和待补材料。
- **提纲或写作**：补充结构、正文或提纲、来源与事实缺口、内链计划和发布前待处理项。
- **内容审查**：补充重复与蚕食风险、承诺兑现情况、证据缺口、结构问题、链接建议及逐篇处理决定。
- **系统集成**：输出需要的读取、推送和评估字段、权限边界与缺口；不假装接口已存在或已调用。

用户要求大量候选时先聚类和查重，不能用换词、换年份或换受众凑数量。任一发布前质量门槛不满足时，先修正 brief、补材料或建议更新旧文，不要用更长的文字掩盖问题。实际发布、冻结和效果评估由 `$seo-front-loop` 管理。
