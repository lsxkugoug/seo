# Blog Generator 验证协议

本协议用于回归测试 Skill 的编辑决策质量。测试通过表示规则能约束输出，不代表文章会获得排名或流量。

## Hard failures

出现任一项即不允许接入自动发布：

- 把只换年份、受众、数字标题或 slug 的明显变体判为 `new`。
- 忽略 archived、merged 或 redirected 内容历史。
- 库存不完整或相近正文未读，却设置 `publish_allowed: true`。
- 虚构产品能力、实测、排名、数据、来源、URL 或第一手经历。
- 用关键词不同代替正文级任务比较。

## 回归案例

至少覆盖：

1. 年份变体应 `update/merge`。
2. 只有受众标签、没有专属材料时应 `update/merge/defer`。
3. 标题不同但正文步骤相同时不得建立新 URL。
4. 有真实场景约束、原始材料和独有阅读产物时可以有条件 `new`。
5. “我们测试了 N 款工具”但没有原始输入输出时应 `needs_evidence`。
6. 开头承诺必须映射到正文段落。
7. 内链应有方向、位置、读者需要和描述性锚文本。
8. 缺少库存时只能输出 provisional 候选，`publish_allowed: false`。
9. 批量更换年份和受众时应返回去重矩阵，不生成平行正文。
10. 与合并或重定向历史碰撞时，应更新 canonical 目标或继续合并。
11. 内容需要合并但页面冻结时，应同时输出 `content_disposition: merge` 和 `execution_status: frozen`。

## 真实库存验收

接入 Generator 前，在完整站点库存上测：

- 已知重复文章的 Top-3 候选召回率；
- 已知重复被误判为 `new` 的比例，目标为 0；
- 同一输入重复运行三次的 disposition 与 gate 一致率；
- `closest_candidates` 是否包含正文审查证据；
- live、archived、merged、redirected 数量能否对账；
- 三篇完整文章的匿名 A/B 审查，包括任务清晰度、独有材料、开头承诺、事实风险和可操作性。

小规模上线后再按预先定义的业务指标、搜索指标和保护指标评估效果。文章数量不作为成功指标。
