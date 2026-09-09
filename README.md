# SEO 项目集合

本仓库用于存放多个 SEO 相关项目。每个项目使用独立子目录，分别维护 README、设计文档和后续实现。

## 项目

| 项目 | 用途 | 当前状态 |
| --- | --- | --- |
| [seo-front-loop](seo-front-loop/README.md) | Codex SEO Skill、用户关键词、可配置部署后复查周期及跨轮记忆协议 | Skill 与只读配置/日期工具已提供；完整账本服务和自动发布未实现 |

## 目录结构

```text
seo/
  README.md
  seo-front-loop/
    README.md
    config
    config.example
    seo-keywords.json
    skills/seo-front-loop/
      SKILL.md
      scripts/
      references/
    docs/
      PLAN.md
      MEMORY_SPEC.md
      RUNBOOK.md
```

后续项目与 `seo-front-loop` 并列放置，并在上方项目表中增加入口。项目专属代码、配置和文档放在对应子目录，避免混入仓库根目录。

仓库路径：`/Users/shixianglong/Desktop/seo`。此前审计的旧项目 `/Users/shixianglong/Desktop/seo-agent` 位于仓库之外，仅作为 `seo-front-loop` 的参考来源。
