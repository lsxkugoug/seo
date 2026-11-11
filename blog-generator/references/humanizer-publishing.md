# Humanizer 分类与上线契约

仅在 Humanizer 选题、生成 publish-blog-v1 payload 或静态发布时读取。分类是发布端持久化的编辑判断，不是前端根据卡片标签临时筛选。2026-11-11 已核对分类分支与生产代码；分支、release 和计数都是核对线索，运行时重新确认，不当永久部署目标。

## 归类与 payload

每篇选择一个主分类，以文章主要读者任务判断，不按正文偶然出现的例子、引文或内链归类：

| primary_category | 名称 | 主要任务 | 分类页面 |
| --- | --- | --- | --- |
| ai-writing | AI Writing | 通用AI写作、保真编辑、检测边界、写作工具选择 | /blog/category/ai-writing |
| education | Education | 学生、教师和研究人员的学习、教学、学术写作任务 | /blog/category/education |
| business | Business | 工作场景的邮件、报告和商业沟通任务 | /blog/category/business |

读者任务重叠时，按文章真正承诺交付的产物及主要情境选一个分类。通用编辑指南里的商务邮件示例不使整篇自动变成 business；标题不能只换“学生/职场”来制造新的独立文章。不得以均衡三类数量为由发布重复内容。

在既有 `article` 中加入下列元数据（示例需用真实 brief 替换）：

```json
{
  "editorial": {
    "primary_category": "ai-writing",
    "audience_situation": "An author is reviewing an AI-assisted draft after checking its sources.",
    "reader_job": "Match each statement's certainty to its evidence and function.",
    "core_answer": "Keep verified observations direct and qualify only the uncertain proposition.",
    "reader_takeaway": "A reviewed paragraph and a claim-by-claim certainty map.",
    "unique_contribution": "A mixed-certainty fixture that also exposes unnecessary hedging.",
    "boundary": "Hedging does not supply evidence or numerical probabilities.",
    "source_type": "evergreen",
    "content_type": "guide",
    "tags": ["editing", "evidence"]
  }
}
```

`primary_category` 必须是上表 slug，不是显示名。当前本机和示例配置的 editorial_policy 要求主分类以及非空 reader_job、audience_situation；其余六要素依主技能 brief 填写。后端接受 source_type：evergreen/trend/product/competitor/user/search/existing_content，content_type：guide/diagnosis/comparison/case_study/template/explainer/checklist/opinion；可选字段不确定时不杜撰。六要素文本后端上限4000字符；tags最多12个，每个非空且最多80字符。

保留原 `tag`（展示标签）、SEO关键词、review、dedupe及上下文内链；它们与主分类不同。若同时提交 editorial.content_disposition，必须与 dedupe.content_disposition 一致。review.status=approved、库存快照、正文去重和幂等约束仍全部适用。

发布端将结果存入 `document.editorial.primary_category`，库存及公开API返回 `primary_category`/`editorial`。旧调用未传分类时有 task-rules-v1 推断兜底，新任务必须显式传入；不要在前端另建一套关键词归类逻辑。

## 源码和静态发布

- 当前本地旧工作树不包含分类实现。2026-11-11 核对的分类实现位于前端 `origin/codex/blog-editorial-categories`，当时提交 ce27b05，生产 release 为 front-blog-hero-trim-ce27b05。每次运行先核对现网 dist、release 对应源码与当前分支进展，采用已核实含分类功能的源码隔离构建；不能把“本地主目录”或“origin/main”直接等同生产最新版，也不固定回退到上述历史提交。
- 分类相关入口为 `src/lib/blogCategories.ts`、`src/lib/blogFeed.ts`、`src/pages/Blog.tsx` 和 `src/components/blog/BlogCard.tsx`。列表使用服务端 category/q/page/limit，默认12条分页；分类页路由为 `/blog/category/:category`，未知分类及搜索态 noindex。分类名称/路径由统一 registry 管理。
- 使用生产数据构建时显式指定 `PRERENDER_API_BASE_URL=https://www.humanizer.help/api` 以及 `PRERENDER_BLOG_API_BASE_URL=https://www.humanizer.help/api`，保留任务要求的 SEO_BLOG_LIMIT=300、SEO_REQUIRE_COMPLETE_BLOG_SET=1，避免新脚本默认指向本机18081。按 total/has_more核对全部分页，不能因首页只显示少量卡片误判库存少了。
- 跑当前源码要求的测试/build/prerender/sitemap。更新静态首页和三个分类页的必要快照及 sitemap/资产；旧“只覆盖 /blog、两新文、sitemap”的清单不再足够。依当前输出和生产基底决定最小发布清单，保留其他服务、普通页面和已有运行行为，核对共享文件/资产兼容性后只激活一个新release，保留上一版。不自动合并分支、提交或推送Git。
- 继续遵守 workspace AGENTS：普通发布不覆盖共享gateway、不编辑AI Manager配置，INSTALL_NGINX_CONF=0，nginx -t/reload后验证Feishu实际代理边界。

## 上线验收和图片冲突

除主技能与每日任务的文章、主图、SEO和共享路由验收外，增加：

1. API中每篇主分类与批准brief一致、分类计数合计等于完整live数量、uncategorized_count=0；按当前数据核对，不写死旧计数。
2. 新文章可从其分类列表找到；分类筛选无跨类泄漏，分页/搜索按实际API工作，未知分类/搜索态的索引策略符合当前实现。
3. `/blog` 和三个分类页实际HTTP响应与浏览器可读，正常分类页canonical为自身且可索引，首页/页脚分类链接正确。核对静态快照、当前sitemap分类URL策略、结构化列表与页面实际内容一致；不能只验证新文章而漏掉分类入口。
4. 公开API和页面实际hero/alt与批准图片一致。现网曾无条件异步覆盖payload主图为生成图或占位图，返回published不证明图片验收通过。若覆盖仍发生，保留原键/回执，不另发文章顶替；在当前授权内修复这两篇的进度或报告阻断，不能默认改全局生图策略或照搬历史数据库修复脚本。主图选择遵从本次用户和项目要求，不能因后端有生图功能而自行改用生成图。

把类别、归类依据、API分类结果、分类入口验证、实际release/源码和失败恢复写入该站点 .seo-memory；下一次运行继续重新读取完整库存。
