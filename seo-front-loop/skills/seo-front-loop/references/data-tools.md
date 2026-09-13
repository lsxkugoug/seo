# 数据配置、权限检查与采集

工具位于 tools/collect_metrics.py。外部查询只读，可能消耗 API 配额；本地仅在 --output 时新建证据文件。不更改站点、埋点、账户权限或实验 Markdown。不启动定时任务。

## 首次使用与缺项询问

先运行 python3 <Skill绝对路径>/tools/collect_metrics.py --project <管理项目绝对路径>。默认只检查本地配置，不请求网络，也不加载 ADC。退出码 2 且 status 为 needs_user_input 时，Agent 将 missing 转成简短问题：请用户提供 GSC 资源标识、PostHog 服务地址/项目 ID，并确认是否启用相应数据源。不要要求无 PostHog 的用户为了 GSC 任务开通它；用 --provider gsc 或 posthog 单独检查。

先按 [项目选择协议](projects.md) 确认具体项目。管理项目 config 不存在时同样询问，不创建虚构配置。用户提供非敏感值并授权后才保存，保留已有配置；凭据要求用户在安全环境或秘密管理工具设置，不让用户粘贴到聊天，不读取或打印其内容。不搜索磁盘上的未知凭据。确认 PostHog host 是用户认可的服务地址再向它发送密钥。

仓库地址缺失仍按主 Skill 的 GitHub 规则询问；数据工具不替代仓库检查。仅周期环境变量允许覆盖 config；账户目标、路径和凭据变量名称来自选定项目 config。冲突环境值会报错，不能沿用另一个站点的数据。

## 配置项与安全授权

- SEO_GSC_PROPERTY：GSC 的完整资源标识，域名资源为 sc-domain:example.com，URL 前缀资源保留完整 URL，包括必要尾斜杠。
- SEO_GSC_AUTH_MODE：access_token 或 adc。前者读取 SEO_GSC_TOKEN_ENV 指定的项目专属环境变量，令牌过期需用户授权工具刷新。后者读取 SEO_GSC_CREDENTIALS_ENV 指定环境变量内的凭据文件路径，并由 google-auth 加载刷新，适合后续重复运行；首次 OAuth/服务账号设置不由脚本自动完成。
- ADC 依赖见 tools/requirements-adc.txt，仅在用户允许后于独立虚拟环境安装。SEO_GSC_CREDENTIALS_ENV 只保存环境变量名称，例如 PRODUCT_A_GOOGLE_CREDENTIALS_FILE；变量值为用户可信的安全凭据文件路径，文件不入 Git。不自动发现全局 ADC。无论 OAuth 用户还是服务账号，其身份都需对应 GSC 资源读取权限，并启用 Search Console API；使用 webmasters.readonly 范围。
- SEO_POSTHOG_HOST：实际 HTTPS 服务根地址，不是前端事件采集代理；SEO_POSTHOG_PROJECT_ID：目标项目数字 ID。
- SEO_POSTHOG_KEY_ENV：本项目密钥环境变量名称，例如 PRODUCT_A_POSTHOG_KEY；实际值在安全环境设置，需目标项目 query:read 权限，不是公开前端采集 key。缺名称/凭据时询问，不回退通用变量。
- SEO_POSTHOG_CONVERSION_EVENTS：用户确认的业务事件，逗号分隔。空值允许仅采集 pageview，但要询问需要评估的是注册、付费还是其他行为；不猜事件名、不自动增加埋点。

## 三种运行方式

以下以当前目录为管理项目为例；跨目录执行时用实际绝对路径代替。

```bash
# 1. 本地缺项检查，不联网
python3 skills/seo-front-loop/tools/collect_metrics.py --project projects/product-a
# 2. 用户允许后检查真实读取权限（需已配置凭据）
python3 skills/seo-front-loop/tools/collect_metrics.py --project projects/product-a --provider gsc --check-access
python3 skills/seo-front-loop/tools/collect_metrics.py --project projects/product-a --provider posthog --check-access
# 3. 明确采集窗口；示例日期不是实际站点基线
python3 skills/seo-front-loop/tools/collect_metrics.py --project projects/product-a --provider gsc --collect --start 2026-08-01 --end 2026-08-28 --output .seo-memory/证据/gsc-baseline-唯一名称.json
python3 skills/seo-front-loop/tools/collect_metrics.py --project projects/product-a --provider posthog --collect --start 2026-08-01 --end 2026-08-28 --output .seo-memory/证据/posthog-baseline-唯一名称.json
```

证据路径相对选定项目目录解析，不允许越到其他项目；父目录必须已存在，文件独占新建且权限为 0600，拒绝覆盖。不用 --output 时只输出结果，不保存记忆。准备私有目录和保存快照也需要在用户授权任务范围内；只问状态时不要写文件。HTTP 错误不输出响应正文和令牌，不自动无限重试。401 提示更新登录，403 核对权限/API，404 核对资源，429 稍后重试。任何失败都不能记为零或覆盖旧基线。

## 何时采集及数据边界

首次接管检查资源与历史范围；每项新实验在改动前保存自己的基线，部署后保留实际 commit/线上确认，按原第 20/40/60 天等约定复查并另存快照。缺配置时先询问或请求手动导出；无可比数据时不开展盲目文案实验，必要正确性修复仍按授权处理。采集不是自动评估或发布授权。

GSC 采集 web 类型、final 数据，分别保存日总量与 date/page/query 日明细及完整请求口径。--page 为完整 URL 精确过滤。每类默认最多四页、每页 25000 行，--max-pages 可设 1–40；碰到上限就报错并缩小范围，不输出伪完整基线。分页结束仍不保证全部长尾，缺行不当零，不从 query 明细求站点总量。请求窗口是 PT 日期且包含首尾日；Agent 核对返回日期覆盖、最新最终数据延迟和样本，不因 HTTP 成功就宣称完整。

PostHog 第一版固定查询 UTC 日级 pageview 和已配置事件的次数，只输出聚合值，不采集用户身份/录屏。不提供自由 SQL 执行入口。结果不是独立用户、会话、漏斗转化率或自然搜索归因。--page 匹配每个事件的当前 URL，不是最初落地页；支付等服务端事件没有该属性时可能被排除。未确认埋点和归因前，只作业务背景，不能作为 SEO 收益证明。GSC PT 与 PostHog UTC 日界不同，不机械逐日相减；如需可靠 SEO 漏斗，先与用户确认归因和事件属性，再另行扩展查询。

工具输出为原始证据 JSON，不是新增机器状态账本。Agent 在自然语言改动记录中链接快照，说明窗口、来源、缺口和判断，保留旧记录。API 访问成功不证明埋点存在/正确、数据充足或已上线。

接口依据：[GSC Search Analytics](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)、[GSC Sites get](https://developers.google.com/webmaster-tools/v1/sites/get)、[PostHog Query API](https://posthog.com/docs/api/query)。
