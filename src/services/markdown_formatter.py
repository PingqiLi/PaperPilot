from typing import Any


def _render_list(items: list, ordered: bool = False) -> str:
    lines = []
    for i, item in enumerate(items):
        prefix = f"{i + 1}." if ordered else "-"
        if isinstance(item, str):
            lines.append(f"{prefix} {item}")
        elif isinstance(item, dict):
            title = item.get("title") or item.get("name") or ""
            body = (
                item.get("why")
                or item.get("reason")
                or item.get("one_liner")
                or item.get("significance")
                or item.get("description")
                or item.get("summary")
                or item.get("insight")
                or ""
            )
            if title and body:
                lines.append(f"{prefix} **{title}** — {body}")
            elif title:
                lines.append(f"{prefix} **{title}**")
            elif body:
                lines.append(f"{prefix} {body}")
        else:
            lines.append(f"{prefix} {item}")
    return "\n".join(lines)


def format_field_overview(content: dict[str, Any], topic_name: str) -> str:
    parts = [f"# 领域概览: {topic_name}\n"]

    if content.get("summary"):
        parts.append(f"## 总结\n\n{content['summary']}\n")

    if content.get("pillars"):
        parts.append("## 研究支柱\n")
        for pillar in content["pillars"]:
            name = pillar.get("name", "")
            maturity = pillar.get("maturity", "")
            desc = pillar.get("description", "")
            header = f"### {name}"
            if maturity:
                header += f" ({maturity})"
            parts.append(f"{header}\n\n{desc}\n")

    rp = content.get("reading_path")
    if rp:
        parts.append("## 阅读路径\n")
        for stage, label in [("start_with", "入门"), ("then_read", "进阶"), ("deep_dive", "深入")]:
            reason = rp.get(f"{stage.split('_')[0]}_reason") or rp.get(f"{stage}_reason", "")
            if not reason and stage == "start_with":
                reason = rp.get("start_reason", "")
            elif not reason and stage == "then_read":
                reason = rp.get("then_reason", "")
            elif not reason and stage == "deep_dive":
                reason = rp.get("deep_reason", "")
            if reason:
                parts.append(f"### {label}\n\n{reason}\n")

    if content.get("open_problems"):
        parts.append("## 未解决问题\n")
        parts.append(_render_list(content["open_problems"]) + "\n")

    return "\n".join(parts)


def format_weekly_digest(content: dict[str, Any], topic_name: str) -> str:
    parts = [f"# 周报: {topic_name}\n"]

    if content.get("week_summary"):
        parts.append(f"## 本周总结\n\n{content['week_summary']}\n")

    if content.get("must_read"):
        parts.append("## 必读\n")
        parts.append(_render_list(content["must_read"]) + "\n")

    if content.get("worth_noting"):
        parts.append("## 值得关注\n")
        parts.append(_render_list(content["worth_noting"]) + "\n")

    if content.get("trend_signal"):
        parts.append(f"## 趋势信号\n\n{content['trend_signal']}\n")

    if content.get("skip_reason"):
        parts.append(f"## 可跳过\n\n{content['skip_reason']}\n")

    return "\n".join(parts)


def format_monthly_report(content: dict[str, Any], topic_name: str) -> str:
    parts = [f"# 月报: {topic_name}\n"]

    if content.get("month_summary"):
        parts.append(f"## 月度总结\n\n{content['month_summary']}\n")

    if content.get("highlights"):
        parts.append("## 亮点论文\n")
        parts.append(_render_list(content["highlights"]) + "\n")

    if content.get("clusters"):
        parts.append("## 主题聚类\n")
        for cluster in content["clusters"]:
            theme = cluster.get("theme") or cluster.get("name", "")
            insight = cluster.get("insight", "")
            parts.append(f"### {theme}\n\n{insight}\n")

    momentum = content.get("momentum")
    if momentum and isinstance(momentum, dict):
        parts.append("## 研究动量\n")
        for key, label in [("accelerating", "加速"), ("emerging", "新兴"), ("declining", "减速")]:
            items = momentum.get(key, [])
            if items:
                if isinstance(items, list):
                    parts.append(f"**{label}**\n")
                    parts.append(_render_list(items) + "\n")
                else:
                    parts.append(f"**{label}**: {items}\n")

    if content.get("next_month_watch"):
        watch = content["next_month_watch"]
        if isinstance(watch, list):
            parts.append("## 下月关注\n")
            parts.append(_render_list(watch) + "\n")
        else:
            parts.append(f"## 下月关注\n\n{watch}\n")

    return "\n".join(parts)


FORMATTERS = {
    "field_overview": format_field_overview,
    "weekly": format_weekly_digest,
    "monthly": format_monthly_report,
}


def format_digest_markdown(digest_type: str, content: dict[str, Any], topic_name: str) -> str:
    formatter = FORMATTERS.get(digest_type)
    if not formatter:
        return f"# {topic_name}\n\n```json\n{content}\n```\n"
    return formatter(content, topic_name)
