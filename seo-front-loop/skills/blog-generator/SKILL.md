---
name: blog-generator
description: "规划、撰写或审查网站 Blog；先对完整内容库存和相近正文执行防重复门禁，再决定 new、update、merge 或 defer，并设计文章结构、开头和自然内链。适用于单篇文章、选题组、内容集群和旧文更新决策；不用于库存不全时批准新 URL、未经核实声称实测，或自动发布。"
---

# Blog Generator

让每篇文章有独立存在的理由，同时让多篇文章组成读者能够自然探索的内容体系。可以生成选题、brief、提纲、开头、完整草稿或审查报告。生成草稿不等于批准发布。

## 开始前

1. 确认目标读者、语言、网站或产品、业务目的，以及用户本轮要选题、写作还是审查。信息不足但不影响研究时，明确假设后继续。
2. 读取文章库存中的 live、archived、merged、redirected URL，以及可用正文、canonical 目标、产品事实和搜索证据。最终查重必须阅读最相近候选的正文，不能只比较标题或关键词。
3. 记录 `inventory_coverage`。如果无法证明库存完整，或者没有读取相近正文，`publish_allowed` 必须为 `false`，不能批准 `new`；可继续输出 provisional 候选、补查计划或 `update / merge / defer` 建议。
4. 对每个候选分别判断 `content_disposition: new / update / merge / defer` 和 `execution_status: ready / blocked / frozen / needs_evidence`。例如内容最终应合并但页面仍在观察期时，前者为 `merge`，后者为 `frozen`。
5. 搜索量、竞品流量和工具分数只用于发现或排序候选。不要把估算数据、一次收录或少量点击写成某种结构已被证明有效。

## 防重复门禁

先从完整库存召回最相近的候选，再做正文级判断。候选检索至少覆盖标题、slug、目标查询、受众情境、读者任务、核心答案、主要步骤、独有材料、canonical、合并和重定向历史。库存较大时先返回 Top 3–5 个候选，但不能把 Top-K 之外的内容假设为不存在。

对每个候选比较：

- `audience_situation`：谁在什么具体情境下遇到问题。
- `reader_job`：读者要理解、诊断、执行、比较还是核查什么。
- `core_answer`：本文给出的主要判断或方法。
- `reader_takeaway`：读完能完成什么或做出什么决定。
- `unique_contribution`：旧文没有的案例、证据、分析、方法或约束。
- `proof_material`：支持文章的来源、原始示例、测试或产品事实。

标题、年份、人群标签、关键词、语气、数字清单长度、段落顺序或新 slug 不构成独立价值。去掉这些表面差异后，如果正文仍服务同一任务、给出同一答案并使用同类材料，必须 `update` 或 `merge`，不能 `new`。已合并和重定向页面仍属于内容历史，不能通过换 URL 重建旧意图。

只有以下条件全部成立时才可批准 `new`：

1. 内容库存与重定向历史覆盖完整；
2. 已读取最相近候选正文；
3. reader job、核心答案或必要阅读产物存在实质差异；
4. 独有材料已经存在或有可执行、可核验的获取方案；
5. 与旧文的边界能够用一句话说明；
6. 没有通过改年份、受众或标题格式制造差异。

详细差异判断见 [编辑框架](references/editorial-framework.md)。需要为 Humanizer、AI 写作、学术写作等主题提供选题或开头时，再读 [案例与选题库](references/case-library.md)。示例展示方法，不代表已验证的搜索表现。

## 文章定位卡

在写提纲或正文前，明确：

- `audience_situation`
- `reader_job`
- `core_answer`
- `reader_takeaway`
- `unique_contribution`
- `proof_material` 与材料缺口
- `closest_candidates`：Top 3–5 相近内容及正文级差异
- `collision_reason`：为何重复或为何可独立存在
- `boundary`：本篇不展开、交给其他文章回答的问题

## 规划文章关系

按照读者下一步需要建立关系：`prerequisite`、`deeper_explanation`、`evidence_or_example`、`next_action`。每条链接记录来源文章、出现位置、目标文章、读者为何需要它和描述性锚文本。

本篇必须独立兑现核心承诺。不要规定固定内链数量，不要求文章两两互链，不为尚未发布的文章生成可点击 URL。若计划修改旧文添加回链，将旧文列入实际影响范围；已冻结或正在观察的页面只保留建议，交由站点的 SEO 发布流程处理。

## 选择结构与开头

先选读者任务，再选文章结构。教程、诊断、比较、案例、核查与观点文章使用不同的推进顺序。统一要求是：让读者认出问题，尽早获得有用信息，看见依据，理解如何行动，并知道合理的下一步。

开头优先使用真实且与正文有关的材料：具体症状、微型对照、关键问题、选择情境、结果或矛盾。开头提出的承诺必须映射到正文中的实际段落。不得虚构第一手经历、实验、用户故事、数据或引语，也不要靠夸张、空泛趋势、模板化提问和大段背景制造吸引力。

## 输出契约

每个候选先输出以下结构，再按用户需要补充 brief、提纲或正文：

```yaml
candidate_title: ""
content_disposition: new | update | merge | defer
execution_status: ready | blocked | frozen | needs_evidence
publish_allowed: false
inventory_coverage:
  status: complete | partial | unknown
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
```

当 `inventory_coverage.status != complete`、任何关键相近正文尚未读取或必要证据缺失时，不得把 `publish_allowed` 改为 `true`。

- **选题规划**：输出少量、分工清楚的候选及完整门禁结果。
- **提纲或写作**：补充结构选择、正文或提纲、来源与事实缺口、内链图和发布前待处理项。
- **内容审查**：补充重复与蚕食风险、承诺兑现情况、证据缺口、结构问题、链接建议和逐篇处理决定。

用户要求大量候选时也要先聚类和查重，不能用换词、换年份或换受众凑数量。若大部分候选重复，交付去重矩阵和少量证据充分的 brief，而不是强行补足数量。

## 发布前质量门槛

检查以下问题：

1. 文章为什么值得单独存在，能否用一句话说清？
2. 与最近似旧文相比，新增价值是否体现在正文材料中？
3. 标题和开头的承诺是否由正文兑现？
4. 每一节是否推进新的问题、证据或动作？
5. 抽象判断后是否有足够具体的例子、依据或步骤？
6. 产品能力、数据、引用和第一手经验是否真实可核查？
7. 文章关系是否帮助读者继续完成任务，且没有依赖未发布链接？
8. 结尾是否给出与当前任务匹配的下一步？

任一关键项不满足时，先修正 brief、补材料或建议更新旧文，不要用更长的文字掩盖问题。该 Skill 只产生内容决策和草稿；实际发布、冻结与效果评估由 `$seo-front-loop` 管理。
