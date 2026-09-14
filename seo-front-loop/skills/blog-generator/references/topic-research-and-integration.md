# 选题研究、数据与 API 集成

在需要从零提出主题、使用 Semrush 或 GSC、接入历史文章和推送接口时读取。本文件定义通用数据契约，不假设任意网站已经有这些接口。

## 1. 发现主题

先画出网站的任务地图，而不是先收集关键词：

```text
目标读者 + 情境
  → 想完成的任务
  → 会遇到的判断、障碍或下一步
  → 网站可验证地帮助的环节
  → 值得解释、比较、演示或核查的主题
```

从产品文档、页面、公开评论、支持问题、销售/客服记录、站内搜索、GSC、关键词工具、SERP 和同行内容收集候选。每条来源记录 `source_type`、URL 或快照、时间、地区/语言和已知局限。同行页面只能作为市场和任务证据：先问读者任务是否尚未被本站服务，再决定是否有独有材料，禁止按标题、段落顺序或 FAQ 改写。

将相近词、问题和页面先聚为一个 `intent_cluster`。一篇文章可覆盖同一任务的多个自然变体；不同页面必须能解释为什么读者需要单独访问它。主题研究阶段可以没有库存或关键词工具，但必须显式标为 `partial` 或 `unknown`。

## 2. Semrush 与关键词工具

Semrush 是可选的需求和竞争信号，不是内容审批器。若用户提供访问权限或导出的数据，优先记录：

- 关键词和目标国家/语言/设备；
- 搜索意图、月搜索量、趋势、KD、CPC、SERP features；
- 相关问题、变体和集群；
- 排名页面、可见的竞争者和内容格式；
- 数据取得时间、报告类型和数据限制。

Semrush 的 Keyword Overview 可提供 intent、volume、trend、KD、CPC、SERP features 和排名页面；Keyword Gap 可以发现竞争者词差，Strategy Builder 可以把相关词聚为页面级集群。[Keyword Overview](https://www.semrush.com/kb/257-keyword-overview) [Keyword Research](https://www.semrush.com/kb/1187-keyword-research)

处理方法：

1. 先按意图和读者任务聚类，再看单词的流量与难度。
2. 用 SERP 实际结果核验工具给出的意图和内容形式；工具数据是估算，会随地区、时间和数据库更新变化。
3. 用产品相关性、独有材料、已有内容覆盖和可测量性筛选，不能只按高 volume 或低 KD 排序。
4. 无 Semrush 时使用可用 GSC、公开 SERP、站内数据和用户语言继续研究，并在 `keyword_research.status` 记录缺口。

## 3. 历史文章库存 API

当网站提供内容服务时，优先让后端返回一个版本化库存快照，而不是让 Agent 从零猜测全部 URL。实现可用任意路径或协议，但读接口至少应等价于：

```json
{
  "snapshot_id": "content-2026-09-14T10:00:00Z",
  "coverage": {
    "status": "complete",
    "live": 120,
    "archived": 14,
    "merged": 9,
    "redirected": 11,
    "known_gaps": []
  },
  "items": [
    {
      "content_id": "article_123",
      "url": "https://example.com/blog/example",
      "status": "live",
      "title": "",
      "slug": "",
      "canonical_url": "",
      "redirect_target": null,
      "intent_cluster": null,
      "published_at": null,
      "updated_at": null,
      "body": "or a retrievable body reference",
      "content_hash": ""
    }
  ],
  "next_cursor": null
}
```

库存可以分页，但 `coverage.status` 只能在所有状态和分页已对账后标为 `complete`。正文可以受权限保护；若 Agent 无法读取相近正文，必须把 `body_reviewed: false` 和 `publish_allowed: false` 写入结论。`merged` 与 `redirected` 不能从库存中省略。

## 4. 草稿推送 API 与发布边界

推送 API 的默认对象是可审查的主题卡、brief 或草稿，不是自动上线内容。建议接口接受幂等键，并返回不可变的提案 ID：

```json
{
  "idempotency_key": "uuid",
  "site_id": "",
  "inventory_snapshot_id": "",
  "proposal": {
    "content_disposition": "new",
    "publish_allowed": false,
    "title": "",
    "intent_cluster": "",
    "closest_candidates": [],
    "brief": {},
    "draft": null,
    "relations": [],
    "evidence": []
  }
}
```

返回值至少包含 `proposal_id`、`status: drafted | pending_review | rejected`、保存版本和可供人工查看的地址。实际发布应是另一个受权限保护的动作，并要求已批准的提案 ID、当前库存快照、内容版本、发布者身份和线上回执。推送失败时报告失败，不静默重试或创建重复文章。

## 5. GSC 搜索表现与内容评估

只有在用户授权的 Search Console property 上读取。Google Search Analytics API 可按 page、query、date、country 和 device 查询 clicks、impressions、CTR 和 average position；结果有行数与数据完整性限制，因此保存请求参数、快照时间、数据截止日和 `first_incomplete_date`。[Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)

对新文章或更新文章分别记录：

- `live_verified_at`：页面实际可访问且内容版本正确的时间；
- 固定的页面、查询组或 `intent_cluster`，以及国家、设备、搜索类型；
- 基线与观察窗口、点击和曝光主指标、CTR 或现有同意图页面等保护指标；
- 其他同期改动、季节性、索引/抓取状态和数据不完整情况。

曝光增长是有价值的观察信号，但不是单独的成功结论：它可能来自更多查询覆盖、排名变化、需求变化或展示方式变化。新文章尤其要评估意图组净变化，避免把旧页面被分流的曝光误记为增长。按 `$seo-front-loop` 已冻结的 20/40/60 天检查点评估；没有足够暴露或最终数据时结论为 `insufficient` 或 `inconclusive`。

## 6. 内链实现与验证

Google 建议每个重要页面至少从站内另一页获得链接，并使用可脱离上下文理解的描述性锚文本；内部链接帮助读者和 Google 理解和发现站内页面。[Google link best practices](https://developers.google.com/search/docs/crawling-indexing/links-crawlable)

每个计划链接保存：

```yaml
source_content_id: ""
placement: "section and sentence context"
target_content_id: ""
relation: prerequisite | deeper_explanation | evidence_or_example | next_action
reader_need: ""
anchor_text: ""
target_status: live | planned
```

验证链接的可访问性、目标 canonical、锚文本、来源/目标页面的主题关系以及对观察中页面的影响。不要批量堆砌锚文本、链接未发布 URL，或声称链接数量必然增加“权重”。
