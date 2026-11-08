# 从需求到发布的同一条链路

用于连接选题来源、Blog Generator、现有配图流程和网站分类。先读取项目的 `editorial_policy`；分类名和业务人群属于项目配置，不是本 Skill 的通用分类。

## 两种来源，同一个候选池

常青来源包括用户任务、产品用途、搜索查询、支持问题、旧文维护和同行覆盖；Buzzword/Radar 提供词语、事件与变化信号。后者保存实际来源、观察时间、比较窗口和证据范围。`source_type=trend` 表示线索来源，不代表证实了升温。无热点时继续研究常青需求，无独立价值时允许暂不产稿。

候选先进入同一个 Blog Generator 编辑判断，再进入写作。明确读者情境、任务、核心答案、读完带走的东西、实际可提供的独有材料和内容边界；读取最相近旧文的完整正文后决定 `new/update/merge/defer`。相同任务优先更新/合并；自动更新尚未开放的站点，保留实际决定和理由，不能为迁就发布接口改成 new。

## 在 brief 阶段确定分类与文章形式

一篇文章保存一个 `primary_category`；另用 tags 记录交叉主题。按主要读者与任务归类，不按 AI、工具名等高频词机械归类。Humanizer 的三个项目类别是：

- `ai-writing`：一般写作者的 AI 使用、润色、检测解释和工具判断；
- `education`：学习、教学、研究中的具体任务；
- `business`：客户、团队、职场与业务沟通任务。

“AI 客户邮件”属于 business；学生准备作业的 AI 使用说明属于 education。分类入口只读取已保存字段，文章发布时自动加入列表。旧文一次性归类时保留正文、图片、发布与更新时间、已有人工分类和配图来源记录。

`content_type` 与分类、来源分开记录：guide、diagnosis、comparison、case_study、template、explainer、checklist、opinion。文章形式由阅读产物决定；不要把所有来源都写成 Review/Check/Edit 清单。案例必须有真实来源，教学虚构示例要明确标注。

## 传递同一份编辑记录

项目开启 `require_editorial_plan` 时，提交文章的 `article.editorial` 至少包含：

```json
{
  "schema_version": "editorial-plan-v1",
  "source_type": "evergreen",
  "primary_category": "business",
  "content_type": "template",
  "audience_situation": "谁在何种情境下需要这篇文章",
  "reader_job": "主要任务",
  "core_answer": "核心答案",
  "reader_takeaway": "读完可完成的动作",
  "unique_contribution": "实际可交付的新材料",
  "boundary": "本文不展开什么",
  "content_disposition": "new",
  "reason": "为何值得独立成篇",
  "closest_candidates": []
}
```

`closest_candidates` 使用实际读取的 content_id、URL、body_reviewed、正文 SHA-256、任务/答案重叠判断与理由。超出执行端上下文能力时记录 defer，不截断正文后声称完整审查。发布阶段核对相近正文是否发生变化，并保留原有库存、事实、内链、范围与幂等检查。发布检查始终是独立动作，生成正文或图片不能代替它。

配图复用同一份 audience_situation、reader_job、core_answer、unique_contribution、content_type 以及正文核心例子。正文是解释、对照或模板时，画面中的情境与动作也随之变化。使用已有生图与托管服务，不新设图像项目或付费服务。

## 网站与表现反馈

发布接口将编辑记录写入现有文章文档，并向公开列表、详情和内容库存返回 primary_category。分类列表在数据库端筛选并分页，不能只筛最近 300 篇。分类页、Blog 首页、页脚入口共用相同项目分类。

保留候选来源 → 编辑决定 → 文章 → 发布/图片回执的对应关系。报告区分候选数、生成数、更新/暂缓决定、发布成功与失败。搜索展示、点击、工具使用等指标只有接入实际数据源后才报告；不要用发布成功替代内容效果。
