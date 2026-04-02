import os
from datetime import datetime
from typing import List, Dict

from config import MAX_TOTAL_RESULTS, REPORTS_DIR
from fetchers.search import fetch_created_repos, explore_all
from fetchers.trending import fetch_all_trending
from notifiers.wechat import send_daily_report
from history_tracker import record_repos, get_fast_growing_repos, get_newly_discovered_repos

def format_created_date(repo: Dict) -> str:
    created_at = repo.get("created_at")
    if not created_at:
        return ""
    try:
        created_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        return created_date.strftime("%Y-%m-%d")
    except:
        return ""

def generate_markdown_report(trending_repos: Dict[str, List[Dict]], created_repos: Dict[str, List[Dict]],
                             explored_repos: List[Dict], fast_growing: List[Dict], newly_discovered: List[Dict], date_str: str) -> str:
    md = f"# GitHub 每日报告 - {date_str}\n\n"
    md += "---\n\n"
    
    if fast_growing:
        md += "## 🚀 快速增长项目\n\n"
        md += "*本周星标增长 50+ 的项目*\n\n"
        for i, repo in enumerate(fast_growing[:15], 1):
            name = repo.get("full_name", "")
            url = repo.get("html_url", f"https://github.com/{name}")
            stars = repo.get("stargazers_count", 0)
            weekly_growth = repo.get("_weekly_growth", 0)
            daily_growth = repo.get("_daily_growth", 0)
            language = repo.get("language", "")
            desc = repo.get("description", "无描述")
            created = format_created_date(repo)
            
            md += f"{i}. **[{name}]({url})** ⭐{stars}"
            if created:
                md += f" 📅{created}"
            if weekly_growth > 0:
                md += f" `+{weekly_growth}/周`"
            if daily_growth > 0:
                md += f" `+{daily_growth}/日`"
            if language:
                md += f" `{language}`"
            md += "\n"
            md += f"   > {desc[:100]}...\n\n"
        md += "\n"
    
    if newly_discovered:
        md += "## ✨ 新发现项目\n\n"
        md += "*最近 3 天首次发现的项目*\n\n"
        for repo in newly_discovered[:10]:
            name = repo.get("full_name", "")
            url = repo.get("html_url", f"https://github.com/{name}")
            stars = repo.get("stargazers_count", 0)
            first_seen = repo.get("_first_seen", "")
            language = repo.get("language", "")
            desc = repo.get("description", "无描述")
            created = format_created_date(repo)
            
            md += f"- **[{name}]({url})** ⭐{stars}"
            if created:
                md += f" 📅{created}"
            if language:
                md += f" `{language}`"
            md += f" `{first_seen}发现`\n"
            md += f"  > {desc[:100]}...\n\n"
        md += "\n"
    
    trending_labels = {
        "daily": "今天获得最多新 star 的项目",
        "weekly": "本周获得最多新 star 的项目",
        "monthly": "本月获得最多新 star 的项目"
    }
    
    shown_repos = set()
    
    for period in ["daily", "weekly", "monthly"]:
        repos = trending_repos.get(period, [])
        if repos:
            md += f"## {trending_labels[period]}\n\n"
            count = 0
            for repo in repos:
                name = repo.get("full_name", "")
                if name in shown_repos:
                    continue
                
                shown_repos.add(name)
                count += 1
                if count > 10:
                    break
                
                url = repo.get("html_url", f"https://github.com/{name}")
                stars = repo.get("stargazers_count", 0)
                forks = repo.get("forks_count", 0)
                language = repo.get("language", "")
                desc = repo.get("description", "无描述")
                created = format_created_date(repo)
                
                md += f"{count}. **[{name}]({url})** ⭐{stars} 🍴{forks}"
                if created:
                    md += f" 📅{created}"
                if language:
                    md += f" `{language}`"
                md += "\n"
                md += f"   > {(desc or '无描述')[:100]}...\n\n"
            md += "\n"
    
    created_labels = {
        "today": "今天最新创建的项目最多 star",
        "this_week": "本周最新创建的项目最多 star",
        "this_month": "本月最新创建的项目最多 star"
    }
    
    for period in ["today", "this_week", "this_month"]:
        repos = created_repos.get(period, [])
        if repos:
            md += f"## {created_labels[period]}\n\n"
            count = 0
            for repo in repos:
                name = repo.get("full_name", "")
                if name in shown_repos:
                    continue
                
                shown_repos.add(name)
                count += 1
                if count > 10:
                    break
                
                url = repo.get("html_url", f"https://github.com/{name}")
                stars = repo.get("stargazers_count", 0)
                forks = repo.get("forks_count", 0)
                language = repo.get("language", "")
                desc = repo.get("description", "无描述")
                created = format_created_date(repo)
                
                md += f"{count}. **[{name}]({url})** ⭐{stars} 🍴{forks}"
                if created:
                    md += f" 📅{created}"
                if language:
                    md += f" `{language}`"
                md += "\n"
                md += f"   > {(desc or '无描述')[:100]}...\n\n"
            md += "\n"
    
    if explored_repos:
        md += "---\n\n"
        md += "## 🔍 探索发现\n\n"
        md += "*按语言和主题探索的新项目*\n\n"
        
        strategy_groups = {}
        for repo in explored_repos:
            strategy = repo.get("_strategy", "其他")
            if strategy not in strategy_groups:
                strategy_groups[strategy] = []
            strategy_groups[strategy].append(repo)
        
        for strategy, repos in strategy_groups.items():
            md += f"### {strategy}\n\n"
            count = 0
            for repo in repos:
                name = repo.get("full_name", "")
                if name in shown_repos:
                    continue
                
                shown_repos.add(name)
                count += 1
                if count > 10:
                    break
                
                url = repo.get("html_url", f"https://github.com/{name}")
                stars = repo.get("stargazers_count", 0)
                forks = repo.get("forks_count", 0)
                language = repo.get("language", "")
                desc = repo.get("description", "无描述")
                created = format_created_date(repo)
                
                md += f"- **[{name}]({url})** ⭐{stars} 🍴{forks}"
                if created:
                    md += f" 📅{created}"
                if language:
                    md += f" `{language}`"
                md += "\n"
                md += f"  > {(desc or '无描述')[:100]}...\n\n"
    
    md += "---\n\n"
    md += f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    
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
    
    print("\nSending WeChat notification...")
    send_daily_report(trending_repos, created_repos, explored_repos, fast_growing, newly_discovered, date_str)
    
    print("\nDone!")
    return report_path

if __name__ == "__main__":
    main()
