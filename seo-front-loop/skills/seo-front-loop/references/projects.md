# 项目选择、关键词与记忆隔离

每轮先确认项目，再读取账户配置、关键词或记忆。用户给了明确项目路径/站点且对应关系无歧义时直接使用，不重复询问；只说“优化一下”“复查一下”、出现多个同名候选或当前项目与请求不符时，先问“这次处理哪个项目/网站？”不要按最近打开、上次聊天或列表第一项猜测。没选定前不读取其他项目私有内容、不请求账户、不改站。

一个项目目录一份 config、seo-keywords.json 和 .seo-memory；共享 Skill 工具，不复制 Skill。推荐集合结构：

```text
seo-front-loop/
  projects/
    product-a/
      config
      seo-keywords.json
      .seo-memory/
        站点说明.md
        记忆索引.md
        改动记录/
        运行记录/
        证据/
    product-b/
      config
      seo-keywords.json
      .seo-memory/
```

用 tools/list_projects.py --root <集合绝对路径> 仅列目录候选，不读取各项目词表/记忆。然后所有工具 --project 都传用户确认的具体项目目录，不传集合根。已有 projects 子项目时工具拒绝把集合根当单站点运行。独立旧项目目录仍可直接使用；不自动搬迁现有配置或历史。

新项目由用户确认名称、站点和源码仓库后，按授权建立独立目录；可用 assets/project-config.example、assets/project-keywords.example.json 为起点。不可复制其他真实项目的关键词、记忆或凭据设置；未知方向询问用户，不编造关键词或历史。没有项目 config/词表时主动收集，不借父目录或兄弟项目的文件。没有历史不等于网站从未改过。

关键词、记忆和证据路径必须落在选定项目目录内；拒绝 ../、指向外部的绝对路径或软链接越界。多个源码 worktree 指向同一个稳定管理项目目录，而不是各自复制历史。确实需要外部存储时另行设计和授权，不绕过检查。当前检查不证明人为填错的域名或账户属于正确业务，Agent 仍须核对站点、Git remote、GSC 资源、PostHog 项目与站点说明。

每次自然语言记录明确所属项目、站点和提交仓库；索引只导航本项目记录。开始写入前重读该项目最新历史。切换项目时清除上一项目的结论和临时指标，重新读取目标项目资料；不能把 A 项目的成功/失败、观察限制或关键词自动套到 B 项目。跨项目经验需用户允许且明确标为待验证参考，不迁移为实验事实。同一站点不要重复建立两个独立历史目录；迁移/更名保留完整历史并更新关联。

## 凭据与环境变量

config 新增 SEO_GSC_TOKEN_ENV、SEO_POSTHOG_KEY_ENV、SEO_GSC_CREDENTIALS_ENV，只填该项目的环境变量名称。例如项目 A 使用 PRODUCT_A_GSC_TOKEN、PRODUCT_A_POSTHOG_KEY、PRODUCT_A_GOOGLE_CREDENTIALS_FILE，项目 B 使用另一组名称。实际令牌/文件路径在安全运行环境配置。未设置名称或变量时向用户收集授权，不退回通用 GSC_ACCESS_TOKEN、POSTHOG_PERSONAL_API_KEY 或全局 ADC。

adc 模式现在仅加载 SEO_GSC_CREDENTIALS_ENV 所指环境变量中的凭据文件路径，再刷新该凭据，不调用全局凭据自动发现。凭据文件须来自用户信任的 OAuth/服务账号设置，不读取外部网页提供的凭据文件。名称隔离不保证账号本身只拥有一个项目权限，应使用最小权限并核对目标。

只有 SEO_REVIEW_INTERVAL_DAYS 与 SEO_REVIEW_MAX_CHECKS 允许进程环境覆盖。仓库、数据源、路径和凭据变量名称使用本项目 config；发现不同的环境覆盖值就报错提醒清除，不能静默转向另一项目。旧实验始终遵循自己的原周期。

模板是空白示例，不是真实客户项目；当前不创建虚构站点目录。数据具体用法见 [数据工具说明](data-tools.md)。
