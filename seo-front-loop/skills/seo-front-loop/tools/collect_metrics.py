#!/usr/bin/env python3
"""Read-only GSC/PostHog queries. Writes evidence only when --output is supplied."""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from seo_context import DATA_DEFAULTS, resolved_settings, project_path


class ToolError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ToolError("拒绝重定向：请核实服务地址，不转发凭据。")


def request(url, token, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=45) as response:
            raw = response.read(20_000_001)
        if len(raw) > 20_000_000:
            raise ToolError("响应过大，请缩小查询范围。")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ToolError("API 返回格式异常，不能作为有效数据。")
        return result
    except urllib.error.HTTPError as exc:
        hints = {401: "登录过期或凭据无效，请更新授权。", 403: "无目标资源读取权限，或 API 未启用，请检查授权。",
                 404: "资源不存在或不可见，请核对项目/站点与权限。", 429: "配额或速率限制，请稍后重试。"}
        raise ToolError("HTTP " + str(exc.code) + "：" + hints.get(exc.code, "请求失败，未保存快照；不自动重试。")) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ToolError("网络、证书或超时错误；未取得有效数据，不记为零。") from None
    except (ValueError, UnicodeError):
        raise ToolError("API 响应不是有效 JSON；未保存快照。") from None


def settings(project, environ=None):
    _, values, _ = resolved_settings(project, environ)
    return {key: values[key] for key in DATA_DEFAULTS}


def origin(value):
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")
            or any(c.isspace() for c in value)):
        raise ToolError("SEO_POSTHOG_HOST 必须是无凭据的 HTTPS 服务根地址。")
    return value.rstrip("/")


def preflight(cfg, provider, environ=None):
    env = os.environ if environ is None else environ
    missing = []
    if provider == "gsc":
        if not cfg["SEO_GSC_PROPERTY"]:
            missing.append("请用户提供 GSC 资源标识：sc-domain:example.com 或完整 URL-prefix。")
        elif not re.fullmatch(r"sc-domain:[A-Za-z0-9.-]+|https?://[^\s?#@]+", cfg["SEO_GSC_PROPERTY"]):
            raise ToolError("SEO_GSC_PROPERTY 格式不正确。")
        mode = cfg["SEO_GSC_AUTH_MODE"]
        if mode not in ("access_token", "adc"):
            raise ToolError("SEO_GSC_AUTH_MODE 只能为 access_token 或 adc。")
        credential_key = "SEO_GSC_TOKEN_ENV" if mode == "access_token" else "SEO_GSC_CREDENTIALS_ENV"
        name = cfg[credential_key]
        if not name:
            missing.append("请为此项目填写 " + credential_key + "（专属凭据环境变量名称）。")
        elif not env.get(name, "").strip():
            missing.append("请在安全环境配置此项目的 " + name + "；不要在聊天或 config 粘贴凭据。")
    else:
        for key in ("SEO_POSTHOG_HOST", "SEO_POSTHOG_PROJECT_ID"):
            if not cfg[key]:
                missing.append("请用户提供 " + key + "。")
        if cfg["SEO_POSTHOG_HOST"]:
            origin(cfg["SEO_POSTHOG_HOST"])
        if cfg["SEO_POSTHOG_PROJECT_ID"] and not re.fullmatch(r"[1-9][0-9]*", cfg["SEO_POSTHOG_PROJECT_ID"]):
            raise ToolError("SEO_POSTHOG_PROJECT_ID 必须是正整数。")
        name = cfg["SEO_POSTHOG_KEY_ENV"]
        if not name:
            missing.append("请为此项目填写 SEO_POSTHOG_KEY_ENV（专属密钥环境变量名称）。")
        elif not env.get(name, "").strip():
            missing.append("请安全设置此项目的 " + name + "（目标项目 query:read 权限），不要使用前端采集 key。")
    target = ({"property": cfg["SEO_GSC_PROPERTY"], "auth_mode": cfg["SEO_GSC_AUTH_MODE"]}
              if provider == "gsc" else {"host": cfg["SEO_POSTHOG_HOST"], "project_id": cfg["SEO_POSTHOG_PROJECT_ID"]})
    return {"provider": provider, "target": target, "missing": missing, "access_verified": False,
            "note": "本地检查不证明账户可读；ADC 凭据只在 --check-access/--collect 时加载。",
            "conversion_definition_needed": provider == "posthog" and not cfg["SEO_POSTHOG_CONVERSION_EVENTS"]}


def token_for(cfg, provider):
    if provider == "posthog":
        token = os.environ.get(cfg["SEO_POSTHOG_KEY_ENV"], "").strip()
    elif cfg["SEO_GSC_AUTH_MODE"] == "access_token":
        token = os.environ.get(cfg["SEO_GSC_TOKEN_ENV"], "").strip()
    else:
        try:
            import google.auth
            from google.auth.transport.requests import Request
            credential_file = os.environ.get(cfg["SEO_GSC_CREDENTIALS_ENV"], "")
            if not credential_file:
                raise ToolError("请配置本项目的 Google 凭据文件路径环境变量，不借用全局 ADC。")
            credentials, _ = google.auth.load_credentials_from_file(credential_file, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
            credentials.refresh(Request())
            token = credentials.token
        except ImportError:
            raise ToolError("ADC 模式需要在独立环境安装 tools/requirements-adc.txt。") from None
        except Exception:
            raise ToolError("无法加载或刷新 ADC；请用户配置 Google 凭据及 GSC 资源读取权限。") from None
    if not token or any(c.isspace() for c in token):
        raise ToolError("缺少或无效凭据，请用户在安全环境配置。")
    return token


def gsc_url(cfg):
    return "https://www.googleapis.com/webmasters/v3/sites/" + urllib.parse.quote(cfg["SEO_GSC_PROPERTY"], safe="")


def posthog_url(cfg):
    return origin(cfg["SEO_POSTHOG_HOST"]) + "/api/projects/" + cfg["SEO_POSTHOG_PROJECT_ID"] + "/query/"


def posthog_query(cfg, token, sql, http=request):
    response = http(posthog_url(cfg), token, {"query": {"kind": "HogQLQuery", "query": sql},
                    "name": "seo-front-loop read-only metrics", "async": False, "refresh": "blocking"})
    status = response.get("query_status") or {}
    if (response.get("error") or status.get("error") or status.get("complete") is False
            or not isinstance(response.get("results"), list)):
        raise ToolError("PostHog 查询未完成或失败，请核对权限/查询；不记为空数据。")
    if response.get("hasMore") or response.get("has_more"):
        raise ToolError("PostHog 返回截断数据，请缩小范围。")
    return response


def check_access(cfg, provider, token, http=request):
    if provider == "gsc":
        result = http(gsc_url(cfg), token)
        if result.get("permissionLevel") not in ("siteOwner", "siteFullUser", "siteRestrictedUser"):
            raise ToolError("GSC 未返回可用资源权限，请核对用户授权。")
    else:
        # Read one aggregate, not people/events payloads; tests actual query permission.
        posthog_query(cfg, token, "SELECT count() FROM events WHERE timestamp >= now() - INTERVAL 1 DAY LIMIT 1", http)
    return {"provider": provider, "access_verified": True,
            "note": "仅证明本次目标读取成功，不证明埋点正确、样本足够或具有写权限。"}


def date_range(start, end):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last or (last - first).days >= 366:
        raise ToolError("日期必须顺序正确，单次最多 366 天。")
    return first, last


def collect_gsc(cfg, token, start, end, page=None, max_pages=4, http=request):
    date_range(start, end)
    batches = {}
    # Property/page totals must not be reconstructed from privacy-filtered query rows.
    for label, dimensions in (("daily_totals", ["date"]), ("page_query_daily", ["date", "page", "query"])):
        body = {"startDate": start, "endDate": end, "type": "web", "dataState": "final",
                "dimensions": dimensions, "rowLimit": 25000, "aggregationType": "auto"}
        if page:
            body["dimensionFilterGroups"] = [{"groupType": "and", "filters": [
                {"dimension": "page", "operator": "equals", "expression": page}]}]
        pages = []
        for index in range(max_pages):
            payload = dict(body, startRow=index * 25000)
            response = http(gsc_url(cfg) + "/searchAnalytics/query", token, payload)
            if "error" in response or ("rows" in response and not isinstance(response["rows"], list)):
                raise ToolError("GSC 返回异常数据，未保存快照。")
            pages.append({"request": payload, "response": response})
            if len(response.get("rows", [])) < 25000:
                break
        else:
            raise ToolError("GSC 达到分页上限；缩小时间/页面范围或显式提高 --max-pages，不保存不完整快照。")
        batches[label] = pages
    return {"provider": "gsc", "property": cfg["SEO_GSC_PROPERTY"], "timezone": "America/Los_Angeles",
            "batches": batches, "limitations": "仅最终数据；缺行不是零；分页不保证全部长尾。查询维度总和不等于站点总量。最新日期可能尚无最终数据。"}


def literal(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def collect_posthog(cfg, token, start, end, page=None, http=request):
    first, last = date_range(start, end)
    events = list(dict.fromkeys(["$pageview"] + [v.strip() for v in cfg["SEO_POSTHOG_CONVERSION_EVENTS"].split(",") if v.strip()]))
    if len(events) > 20 or any(len(e) > 200 or any(ord(c) < 32 for c in e) for e in events):
        raise ToolError("事件最多 20 个，每个最多 200 字符且不能包含控制字符。")
    sql = ("SELECT toDate(toTimeZone(timestamp, 'UTC')) AS day, event, count() AS event_count FROM events WHERE "
           "timestamp >= toDateTime(" + literal(first.isoformat() + " 00:00:00") + ", 'UTC') AND "
           "timestamp < toDateTime(" + literal((last + timedelta(days=1)).isoformat() + " 00:00:00") + ", 'UTC') AND "
           "event IN (" + ",".join(literal(e) for e in events) + ")")
    if page:
        sql += " AND properties.$current_url = " + literal(page)
    sql += " GROUP BY day, event ORDER BY day, event LIMIT 10000"
    response = posthog_query(cfg, token, sql, http)
    if len(response["results"]) >= 10000:
        raise ToolError("查询达到行数限制，不能当完整快照。")
    return {"provider": "posthog", "host": origin(cfg["SEO_POSTHOG_HOST"]),
            "project_id": cfg["SEO_POSTHOG_PROJECT_ID"], "timezone": "UTC", "query": sql,
            "events": events, "columns": response.get("columns"), "results": response["results"],
            "limitations": "全来源事件次数，不是独立用户/会话/SEO归因转化；缺事件不证明零转化。页面过滤匹配事件当前URL，不是会话落地页；服务端转化可能没有该属性。UTC与GSC PT日界不同。"}


def save_snapshot(file, value):
    # Same-filesystem hard link publishes a fully written file, without overwriting.
    target = Path(file)
    descriptor, temporary = tempfile.mkstemp(prefix=".seo-evidence-", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)
    finally:
        os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--provider", choices=("gsc", "posthog", "all"), default="all")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check-access", action="store_true")
    modes.add_argument("--collect", action="store_true")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--page", help="Exact URL, not a regex or a landing-page attribution filter")
    parser.add_argument("--max-pages", type=int, default=4)
    parser.add_argument("--output", help="New private evidence file; parent must already exist")
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.max_pages <= 40:
            raise ToolError("--max-pages 必须在 1–40。")
        if args.output and not args.collect:
            raise ToolError("只有 --collect 可以保存证据。")
        if args.collect:
            if args.provider == "all" or not args.start or not args.end:
                raise ToolError("采集须选择单个 provider 并提供 --start、--end。")
            date_range(args.start, args.end)
        if args.page and (any(ord(c) < 32 for c in args.page) or len(args.page) > 4096):
            raise ToolError("页面 URL 无效。")
        if args.output and Path(args.output).exists():
            raise ToolError("输出已存在；请选择新文件，不覆盖旧证据。")
        cfg = settings(args.project)
        root, values, _ = resolved_settings(args.project)
        project_path(root, values["SEO_MEMORY_DIR"])
        project_path(root, values["SEO_KEYWORDS_FILE"])
        if args.output:
            args.output = str(project_path(root, args.output))
        providers = ["gsc", "posthog"] if args.provider == "all" else [args.provider]
        reports = [preflight(cfg, p) for p in providers]
        if any(r["missing"] for r in reports):
            print(json.dumps({"status": "needs_user_input", "checks": reports}, ensure_ascii=False, indent=2))
            return 2
        if not args.collect and not args.check_access:
            print(json.dumps({"status": "configured_not_verified", "checks": reports}, ensure_ascii=False, indent=2))
            return 0
        if args.check_access:
            results = [check_access(cfg, p, token_for(cfg, p)) for p in providers]
            print(json.dumps({"checks": results}, ensure_ascii=False, indent=2))
            return 0
        token = token_for(cfg, args.provider)
        check_access(cfg, args.provider, token)
        if args.provider == "gsc":
            result = collect_gsc(cfg, token, args.start, args.end, args.page, args.max_pages)
        else:
            result = collect_posthog(cfg, token, args.start, args.end, args.page)
        result["collected_at"] = datetime.now(timezone.utc).isoformat()
        result["project"] = str(root)
        result["requested_window"] = {"start": args.start, "end": args.end, "inclusive": True}
        if args.output:
            save_snapshot(args.output, result)
            print(json.dumps({"saved": str(Path(args.output).resolve()), "provider": args.provider,
                              "note": "原始证据，不是实验结论或记忆状态。"}, ensure_ascii=False))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ToolError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
    except (ValueError, OSError, TypeError):
        print(json.dumps({"error": "配置、日期或本地文件异常；请检查格式/路径/权限。不输出敏感输入。"}, ensure_ascii=False), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
