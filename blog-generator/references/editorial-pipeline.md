# 从需求到发布的同一条链路

用于连接选题来源、Blog Generator、现有配图流程和网站分类。先读取项目的 `editorial_policy`；分类名和业务人群属于项目配置，不是本 Skill 的通用分类。

## 两种来源，同一个候选池

常青来源包括用户任务、产品用途、搜索查询、支持问题、旧文维护和同行覆盖；Buzzword/Radar 提供词语、事件与变化信号。后者保存实际来源、观察时间、比较窗口和证据范围。`source_type=trend` 表示线索来源，不代表证实了升温。无热点时继续研究常青需求，无独立价值时允许暂不产稿。

候选先进入同一个 Blog Generator 编辑判断，再进入写作。明确读者情境、任务、核心答案、读完带走的东西、实际可提供的独有材料和内容边界；读取最相近旧文的完整正文后决定 `new/update/merge/defer`。相同任务优先更新/合并；自动更新尚未开放的站点，保留实际决定和理由，不能为迁就发布接口改成 new。

Humanizer 的执行端先独立检查已有标题/摘要的任务重叠，以及同一原始来源的复用。明显或潜在重复进入 update 提案，不能用小模型的一次“新文”判断绕过；这类前置匹配不冒充完整正文审核。分类还需与实际来源任务相符，模型提出的人群标签不直接成为事实。新文仍执行完整正文比较和原有发布检查。

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

Humanizer 生产部署的公开 Blog 读接口与发布接口共用现有独立博客服务（环回 18081），经 Nginx 对外提供 `/api/blog`。内部预渲染可设置 `PRERENDER_BLOG_API_BASE_URL=http://127.0.0.1:18081/api`；其他站点 API 沿用原配置。

## Humanizer 执行与来源回执（2026-11-13）

调度器领取候选后，将 brief、完整正文库存、写作规范和不含凭据的项目范围配置复制到原 Agent 已有权限的任务资料目录。不要让 Agent 读取调度器私有目录，也不要复制 claims、lease token、环境文件或 API 密钥。原 Agent 只产出草稿与正文审查记录；发布由受控执行端完成。

写作前的 `required_body_reviews` 是发布阶段使用的同一组正文；可以额外审查相近文章。`overlap=true` 仅指旧文已能服务同一读者任务并给出相同核心答案，不指共享“AI 写作”大主题。新文须为所有必读项记录实际完整正文 SHA-256 与 `overlap=false`；同任务仍进入 update/merge。正文中的历史内链可使用已核实的 live canonical URL 和自然锚文本，发布前再次核对每个来源 ID、URL 和正文哈希。

Humanizer 新发布要求 `article.editorial.lineage`，由可信调度器根据已领取的真实候选填写：`candidate_id`、`task_id`、`source_type`、`source_record_ids`、`source_urls`、`selection_method=shared_candidate_pool`。模型不得编造这些值。库存快照和相近旧文清单都不能充当候选来源。缺少该回执的新请求会被拒绝；历史已成功请求的相同 payload 和幂等键仍能安全重放。

配图属于发布服务维护的结果。客户端提交后不要用原始图库回退值覆盖文章图片和 `image_generation`。正文哈希未变且图片被旧客户端换回已知图库时，服务复用已经视觉验收的图片恢复结果；真实正文变更或另行上传的自定义图片仍会停止自动覆盖。不能把“服务在线”当作图片已显示，须核对最终 URL、文章页、列表/分类入口与封面回执。

候选回执不只是格式正确的编号。Humanizer 调度器会在模型资料目录之外保存只含公开来源信息、任务编号、原 Agent 作业编号和正文哈希的只读回执；发布服务核对它与实际正文是否一致。模型或旧客户端随意填入一个 candidate_id 不能通过。定时服务先验证资料交接和回执目录的实际可写性，再领取任务，避免手工执行可用而沙盒中的定时任务失败。
