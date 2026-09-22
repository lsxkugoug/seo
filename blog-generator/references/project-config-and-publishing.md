# 多项目配置与受控发布

仅在把 Blog Generator 接入具体站点、查询历史文章或发布文章时读取。每个项目一份 JSON 配置，配置存放在 `config/projects/`。可提交的 `*.example.json` 不含凭据；真实项目配置使用 `*.local.json`，已被 Git 忽略。密钥由环境变量保存，配置只记录变量名。

## 配置与密钥

从 `project_id` 选择配置：优先 `config/projects/<project_id>.local.json`，其次同名 `.json` 或 `.example.json`。示例文件是接口设计，不可用于实际发布：其中的 `<site-host>`、关键词、范围和 URL 必须被项目真实值替换。

`auth.secret_env` 是唯一允许记录密钥的字段，例如 `HUMANIZER_BLOG_API_KEY`。运行时读取它并放入指定请求头；不得把密钥写入 Git、文章、日志、错误报告或发布 JSON。环境变量缺失时停止发布，不猜测或请求回显密钥。

运行：

```bash
python3 scripts/validate_project_config.py config/projects/humanizer.example.json --allow-template-urls
python3 scripts/validate_project_config.py config/projects/humanizer.local.json
```

## 历史文章查询 API：`inventory-v1`

配置中的 `apis.history` 指向后端只读接口。请求必须使用配置的 `method`、`query` 和认证头；每次写作或发布前获取完整分页结果。响应至少如下：

```json
{
  "snapshot_id": "content-2026-09-20T10:00:00Z",
  "coverage": {
    "status": "complete",
    "live": 120,
    "archived": 14,
    "merged": 9,
    "redirected": 11,
    "known_gaps": []
  },
  "items": [{
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
    "body": "full body or retrievable body reference",
    "internal_links": []
  }],
  "next_cursor": null
}
```

只有所有分页和四种状态均已对账，`coverage.status` 才能是 `complete`。查重候选必须读取相关正文；同时从 `live` 内容中挑选符合当前读者任务的历史链接，满足 `internal_link_policy.min_contextual_historical_links`。链接要真实、相关、已发布且使用描述性锚文本；不能承诺它必然提升排名。

## 自动发布 API：`publish-blog-v1`

后端可新增 `POST /internal/publish_blogs`。接口必须验证配置指定请求头中的密钥，并把 `Idempotency-Key` 作为同一篇提交的去重键。建议后端返回：

```json
{
  "publication_id": "pub_123",
  "status": "published",
  "url": "https://example.com/blog/article-slug",
  "content_id": "article_456",
  "idempotency_key": "request UUID"
}
```

Agent 发送的 JSON 必须符合以下结构。双花括号是生成时替换的值，不是字面内容：

```json
{
  "schema_version": "publish-blog-v1",
  "idempotency_key": "{{uuid}}",
  "project_id": "{{project_id}}",
  "inventory_snapshot_id": "{{inventory.snapshot_id}}",
  "article": {
    "title": "{{draft.title}}",
    "slug": "{{draft.slug}}",
    "excerpt": "{{draft.excerpt}}",
    "content_markdown": "{{reviewed_draft.markdown}}",
    "author": "{{config.presentation_defaults.author}}",
    "author_bio": "{{config.presentation_defaults.author_bio}}",
    "avatar_seed": "{{config.presentation_defaults.avatar_seed}}",
    "tag": "{{config.presentation_defaults.tag}}",
    "read_time": "{{config.presentation_defaults.read_time}}",
    "image": "{{config.presentation_defaults.image}}",
    "canonical_url": null,
    "seo": {
      "primary_keyword": "{{primary_keyword}}",
      "meta_title": "{{meta_title}}",
      "meta_description": "{{meta_description}}"
    },
    "internal_links": [{
      "target_content_id": "{{history.content_id}}",
      "target_url": "{{history.url}}",
      "anchor_text": "{{descriptive_anchor}}",
      "relation": "prerequisite|deeper_explanation|evidence_or_example|next_action",
      "placement": "{{section and sentence context}}"
    }]
  },
  "review": {
    "status": "approved",
    "reviewed_at": "{{ISO-8601}}",
    "checks_passed": ["dedupe", "facts", "scope", "structure", "internal_links"]
  },
  "dedupe": {
    "content_disposition": "new",
    "closest_candidates": [],
    "body_reviewed": true
  }
}
```

只有 `publish.mode` 为 `auto_after_review` 才执行 POST；必须同时满足：库存完整、正文级查重通过、所有事实与范围检查通过、审查状态为 `approved`、历史链接达到配置要求、库存快照仍有效、payload 完整、生成新的 UUID。调用后保存返回的 `publication_id`、URL、内容 ID 和幂等键。超时、5xx 或无响应时不换键重发；保留原始 payload 和幂等键，等待人工核对发布结果，避免重复文章。当前 CLI 会在库存变化后阻断 POST，包括首次提交已成功但响应丢失的情况；不要换新键绕过这个阻断。后端自身支持相同 payload 和键的幂等重放。

`manual_review` 模式只生成 payload 和审查结果，不调用发布 URL。Humanizer 后端的接口路径为 `/internal/blogs` 和 `/internal/publish_blogs`。新版默认关闭发布，且不支持自动覆盖旧文章。上线前须设置 `BLOG_AUTOMATION_API_KEY`、与客户端一致的 `BLOG_AUTOMATION_PROJECT_ID`，验收后才开启 `BLOG_AUTOMATION_PUBLISH_ENABLED=true`；执行版本库中的数据库迁移脚本，并通过健康检查后才可使用真实配置。

## 执行脚本

`scripts/blog_api.py` 使用标准库调用已配置的 API，不把密钥打印到输出。查询库存：

```bash
# 由团队的密钥管理方式注入 HUMANIZER_BLOG_API_KEY，避免把值写进命令历史。
python3 scripts/blog_api.py inventory --config config/projects/humanizer.local.json \
  --output /absolute/path/inventory.json
```

先对审查通过的 payload 做本地预检：

```bash
python3 scripts/blog_api.py publish \
  --config config/projects/humanizer.local.json \
  --payload /absolute/path/reviewed-article.json \
  --inventory /absolute/path/inventory.json
```

只有通过预检后才用 `--execute` 调用 API。脚本再次检查配置模式、审查状态、去重、历史链接、快照和幂等键；网络失败时不会自动以新键重发。


## 完整性与安全边界

客户端必须完成全部分页并校验各状态数量、完整正文、无重复 ID、游标推进和一致的快照，才保存 inventory.json。任何一页异常都停止，不能把部分库存作为成功结果。库存 API 的 `coverage` 描述服务端数据覆盖范围，不代表调用方已经读完所有分页。公开页面或归档系统中不在该 API 覆盖范围内的历史仍需另行核对。

本地预检读取 `--inventory` 的已完整对账内容；`--execute` 发送前还会重新读取全部历史并与审查时内容比较。审核声明不等于程序完成了语义查重、事实核查；正文审查仍需由 Agent/编辑实际执行。需要更新旧文时走编辑流程，不要把 update 换成不同 slug 的 new 来规避重复保护。

请求拒绝所有 HTTP 重定向，防止密钥被转发到另一个地址；配置必须填写最终 HTTPS API 地址。客户端配置校验只验证结构，服务器仍独立核对项目和密钥。

验证命令（使用临时目录和模拟响应，不联系正式 API）：

```bash
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```
