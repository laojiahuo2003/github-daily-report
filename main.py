import json
import os
from datetime import datetime
from typing import List, Dict, Tuple

from config import MAX_TOTAL_RESULTS, REPORTS_DIR
from fetchers.search import fetch_created_repos, explore_all
from fetchers.trending import fetch_all_trending
from notifiers.wechat import send_daily_report
from history_tracker import record_repos, get_fast_growing_repos, get_newly_discovered_repos
from categorizer import categorize_repo, group_by_category
from feed import generate_index, generate_rss, generate_json_index


def format_created_date(repo: Dict) -> str:
    created_at = repo.get("created_at")
    if not created_at:
        return ""
    try:
        created_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        return created_date.strftime("%Y-%m-%d")
    except:
        return ""


def format_stars(n: int) -> str:
    """108691 -> 108.7k, 945 -> 945"""
    if not n:
        return "0"
    if n >= 1000:
        s = f"{n / 1000:.1f}".rstrip("0").rstrip(".")
        return f"{s}k"
    return str(n)


def repo_growth(repo: Dict) -> int:
    """优先用 trending 页面的 stars today，回退到历史追踪的日增长"""
    return repo.get("_stars_gained", 0) or repo.get("_daily_growth", 0)


def build_leaderboard(trending_repos: Dict[str, List[Dict]], limit: int = 15) -> List[Dict]:
    """今日飙升榜：日趋势榜按当日 star 增长量排序"""
    repos = list(trending_repos.get("daily", []))
    repos.sort(key=repo_growth, reverse=True)
    return repos[:limit]


def format_repo_line(repo: Dict, shown_tags: List[str] = None) -> str:
    """单条项目的列表项渲染"""
    name = repo.get("full_name", "")
    url = repo.get("html_url", f"https://github.com/{name}")
    stars = repo.get("stargazers_count", 0)
    language = repo.get("language", "")
    desc = (repo.get("description") or "无描述").strip()
    created = format_created_date(repo)
    daily_growth = repo.get("_daily_growth", 0)
    weekly_growth = repo.get("_weekly_growth", 0)

    tags = list(shown_tags or [])
    if daily_growth > 0:
        tags.append(f"+{daily_growth}/日")
    elif weekly_growth > 0:
        tags.append(f"+{weekly_growth}/周")
    if language:
        tags.append(language)

    line = f"- **[{name}]({url})** ⭐{format_stars(stars)}"
    if created:
        line += f" 📅{created}"
    if tags:
        line += " " + " ".join(f"`{t}`" for t in tags)
    line += "\n"
    if desc and desc != ".":  # genlayerlabs 那种占位描述跳过
        line += f"  > {desc[:120]}\n"
    return line


def render_category_section(title: str, repos: List[Dict], max_total: int = 20,
                            max_per_category: int = 8) -> str:
    """把仓库列表按分类渲染成一个章节"""
    if not repos:
        return ""

    md = f"## {title}\n\n"
    groups = group_by_category(repos[:max_total * 2], max_per_category=max_per_category)

    shown = 0
    for category, items in groups.items():
        if shown >= max_total:
            break
        md += f"### {category}\n\n"
        for repo in items:
            if shown >= max_total:
                break
            source_tags = []
            source = repo.get("_source_label")
            if source:
                source_tags.append(source)
            md += format_repo_line(repo, source_tags)
            shown += 1
        md += "\n"
    return md


def collect_trending_for_categories(trending_repos: Dict[str, List[Dict]]) -> Tuple[List[Dict], set]:
    """合并日/周/月趋势榜（日榜优先），标注来源标签，返回 (列表, 已出现的项目名)"""
    period_labels = {"daily": "今日", "weekly": "本周", "monthly": "本月"}
    merged, shown = [], set()

    for period in ["daily", "weekly", "monthly"]:
        for repo in trending_repos.get(period, []):
            name = repo.get("full_name", "")
            if not name or name in shown:
                continue
            shown.add(name)
            repo["_source_label"] = period_labels[period]
            merged.append(repo)

    return merged, shown


def generate_markdown_report(trending_repos: Dict[str, List[Dict]], created_repos: Dict[str, List[Dict]],
                             explored_repos: List[Dict], fast_growing: List[Dict], newly_discovered: List[Dict], date_str: str) -> str:
    leaderboard = build_leaderboard(trending_repos)

    md = f"# GitHub 每日报告 - {date_str}\n\n"
    md += "---\n\n"

    # 🏆 今日最佳项目
    if leaderboard:
        top = leaderboard[0]
        name = top.get("full_name", "")
        url = top.get("html_url", f"https://github.com/{name}")
        desc = (top.get("description") or "").strip()
        created = format_created_date(top)

        md += "## 🏆 今日最佳项目\n\n"
        md += f"**[{name}]({url})**\n\n"
        md += f"- ⭐ 总星标：{format_stars(top.get('stargazers_count', 0))}\n"
        md += f"- 🔺 今日增长：+{repo_growth(top)}\n"
        if top.get("language"):
            md += f"- 💻 语言：{top['language']}\n"
        if created:
            md += f"- 📅 创建时间：{created}\n"
        md += f"- 🗂️ 分类：{categorize_repo(top)}\n"
        if desc:
            md += f"- 📝 简介：{desc[:150]}\n"
        md += "\n"

    # 📊 今日飙升榜
    if leaderboard:
        md += "## 📊 今日飙升榜\n\n"
        md += "| 排名 | 项目 | 今日增长 | 总⭐ | 语言 | 分类 | 简介 |\n"
        md += "| --- | --- | --- | --- | --- | --- | --- |\n"
        for i, repo in enumerate(leaderboard, 1):
            name = repo.get("full_name", "")
            url = repo.get("html_url", f"https://github.com/{name}")
            language = repo.get("language") or "-"
            desc = (repo.get("description") or "").strip()
            desc_cell = desc.replace("|", "/")[:80] if desc and desc != "." else "-"
            md += (f"| {i} | [{name}]({url}) | 🔺{repo_growth(repo)} "
                   f"| {format_stars(repo.get('stargazers_count', 0))} "
                   f"| {language} | {categorize_repo(repo)} | {desc_cell} |\n")
        md += "\n"

    # 🚀 快速增长项目（周增长 50+，历史追踪发现，可能不在趋势榜上）
    if fast_growing:
        md += "## 🚀 快速增长项目\n\n"
        md += "*本周星标增长 50+ 的项目（基于历史追踪，含趋势榜之外的项目）*\n\n"
        md += "| 排名 | 项目 | 周增长 | 总⭐ | 语言 |\n"
        md += "| --- | --- | --- | --- | --- |\n"
        for i, repo in enumerate(fast_growing[:15], 1):
            name = repo.get("full_name", "")
            url = repo.get("html_url", f"https://github.com/{name}")
            language = repo.get("language") or "-"
            md += (f"| {i} | [{name}]({url}) | 🔺+{repo.get('_weekly_growth', 0)}/周 "
                   f"| {format_stars(repo.get('stargazers_count', 0))} | {language} |\n")
        md += "\n"

    # 🔥 热门项目 · 按分类（日/周/月趋势榜合并去重）
    trending_merged, shown_repos = collect_trending_for_categories(trending_repos)
    if trending_merged:
        md += render_category_section("🔥 热门项目 · 按分类", trending_merged, max_total=25, max_per_category=8)

    # 🌱 新项目速递 · 按分类（今天/本周创建）
    new_repos = []
    for period in ["today", "this_week"]:
        for repo in created_repos.get(period, []):
            name = repo.get("full_name", "")
            if not name or name in shown_repos:
                continue
            shown_repos.add(name)
            new_repos.append(repo)
    if new_repos:
        # 按 star 数取头部，避免长尾填充报告
        new_repos.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
        md += render_category_section("🌱 新项目速递 · 按分类（近 7 天创建）", new_repos, max_total=15, max_per_category=6)

    # 🔍 探索发现（按语言/主题策略）
    if explored_repos:
        md += "---\n\n"
        md += "## 🔍 探索发现\n\n"
        md += "*按语言和主题探索的新项目*\n\n"

        strategy_groups = {}
        for repo in explored_repos:
            strategy = repo.get("_strategy", "其他")
            strategy_groups.setdefault(strategy, []).append(repo)

        for strategy, repos in strategy_groups.items():
            md += f"### {strategy}\n\n"
            count = 0
            for repo in repos:
                name = repo.get("full_name", "")
                if name in shown_repos:
                    continue
                shown_repos.add(name)
                count += 1
                if count > 8:
                    break
                md += format_repo_line(repo)
            if count:
                md += "\n"

    # ✨ 新发现（首次进入追踪视野，且未在上方出现）
    if newly_discovered:
        fresh = [r for r in newly_discovered if r.get("full_name") not in shown_repos][:10]
        if fresh:
            md += "## ✨ 新发现项目\n\n"
            md += "*最近 3 天首次发现的项目*\n\n"
            for repo in fresh:
                first_seen = repo.get("_first_seen", "")
                tags = [f"{first_seen}发现"] if first_seen else []
                md += format_repo_line(repo, tags)
            md += "\n"

    md += "---\n\n"
    md += f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · [历史报告](index.md) · [RSS 订阅](../feed.xml) *\n"

    return md


def save_report(content: str, date_str: str) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"{timestamp}.md"
    filepath = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Report saved to: {filepath}")
    return filepath


def _repo_to_dict(repo: Dict) -> Dict:
    """把单个仓库序列化为 JSON 友好结构（与 markdown 渲染同源）"""
    name = repo.get("full_name", "")
    return {
        "name": name,
        "url": repo.get("html_url", f"https://github.com/{name}"),
        "stars": repo.get("stargazers_count", 0),
        "stars_fmt": format_stars(repo.get("stargazers_count", 0)),
        "growth": repo_growth(repo),
        "weekly_growth": repo.get("_weekly_growth", 0),
        "language": repo.get("language") or "",
        "category": categorize_repo(repo),
        "description": (repo.get("description") or "").strip(),
        "created": format_created_date(repo),
        "source": repo.get("_source_label", ""),
        "first_seen": repo.get("_first_seen", ""),
    }


def _build_category_groups(repos: List[Dict], max_total: int, max_per_category: int) -> List[Dict]:
    """与 render_category_section 同源的分类分组（含同样的截断规则）"""
    groups = group_by_category(repos[:max_total * 2], max_per_category=max_per_category)
    out, shown = [], 0
    for category, items in groups.items():
        if shown >= max_total:
            break
        projects = []
        for repo in items:
            if shown >= max_total:
                break
            projects.append(_repo_to_dict(repo))
            shown += 1
        if projects:
            out.append({"category": category, "projects": projects})
    return out


def build_report_data(trending_repos, created_repos, explored_repos,
                      fast_growing, newly_discovered, date_str) -> Dict:
    """生成与 markdown 报告同源的 JSON 结构，供博客日报页渲染卡片"""
    leaderboard = build_leaderboard(trending_repos)

    data = {
        "date": date_str,
        "best": _repo_to_dict(leaderboard[0]) if leaderboard else None,
        "leaderboard": [_repo_to_dict(r) for r in leaderboard],
        "fast_growing": [_repo_to_dict(r) for r in fast_growing[:15]],
        "monthly": [],
        "by_category": [],
        "new_projects": [],
        "explored": [],
        "newly_discovered": [],
    }

    # 🔥 热门项目 · 按分类（日/周/月合并去重）
    trending_merged, shown_repos = collect_trending_for_categories(trending_repos)
    data["by_category"] = _build_category_groups(trending_merged, max_total=25, max_per_category=8)

    # 🌱 新项目（今天/本周创建）
    new_repos = []
    for period in ["today", "this_week"]:
        for repo in created_repos.get(period, []):
            name = repo.get("full_name", "")
            if not name or name in shown_repos:
                continue
            shown_repos.add(name)
            new_repos.append(repo)
    new_repos.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
    data["new_projects"] = _build_category_groups(new_repos, max_total=15, max_per_category=6)

    # 🔍 探索发现（按策略分组）
    strategy_groups = {}
    for repo in explored_repos:
        strategy = repo.get("_strategy", "其他")
        strategy_groups.setdefault(strategy, []).append(repo)
    for strategy, repos in strategy_groups.items():
        projects = []
        for repo in repos:
            name = repo.get("full_name", "")
            if name in shown_repos:
                continue
            shown_repos.add(name)
            if len(projects) < 8:
                projects.append(_repo_to_dict(repo))
        if projects:
            data["explored"].append({"strategy": strategy, "projects": projects})

    # ✨ 新发现
    fresh = [r for r in newly_discovered if r.get("full_name") not in shown_repos][:10]
    data["newly_discovered"] = [_repo_to_dict(r) for r in fresh]

    return data


def save_report_json(data: Dict) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"{timestamp}.json"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Report JSON saved to: {filepath}")
    return filepath


def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"Starting GitHub daily report for {date_str}")

    print("\nFetching trending repositories...")
    trending_repos = fetch_all_trending()
    total_trending = sum(len(repos) for repos in trending_repos.values())
    print(f"Found {total_trending} trending repos")

    print("\nFetching created repositories...")
    created_repos = fetch_created_repos()
    total_created = sum(len(repos) for repos in created_repos.values())
    print(f"Found {total_created} created repos")

    print("\nExploring repositories...")
    explored_repos = explore_all()
    print(f"Found {len(explored_repos)} explored repos")

    all_repos = []
    for repos in trending_repos.values():
        all_repos.extend(repos)
    for repos in created_repos.values():
        all_repos.extend(repos)
    all_repos.extend(explored_repos)

    print("\nRecording repos to history...")
    record_repos(all_repos)

    print("\nAnalyzing growth trends...")
    fast_growing = get_fast_growing_repos(all_repos, min_weekly_growth=50)
    newly_discovered = get_newly_discovered_repos(all_repos, days=3)
    print(f"Found {len(fast_growing)} fast growing repos")
    print(f"Found {len(newly_discovered)} newly discovered repos")

    print("\nGenerating markdown report...")
    md_content = generate_markdown_report(trending_repos, created_repos, explored_repos, fast_growing, newly_discovered, date_str)
    report_path = save_report(md_content, date_str)

    print("\nGenerating structured JSON report...")
    report_data = build_report_data(trending_repos, created_repos, explored_repos, fast_growing, newly_discovered, date_str)
    save_report_json(report_data)

    print("\nGenerating report index, RSS and JSON feeds...")
    generate_index(REPORTS_DIR)
    generate_rss(REPORTS_DIR)
    generate_json_index(REPORTS_DIR)

    print("\nSending WeChat notification...")
    leaderboard = build_leaderboard(trending_repos)
    send_daily_report(trending_repos, created_repos, explored_repos, fast_growing, newly_discovered, date_str, leaderboard)

    print("\nDone!")
    return report_path


if __name__ == "__main__":
    main()
