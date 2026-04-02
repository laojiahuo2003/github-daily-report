import requests
from typing import List, Dict
from datetime import datetime
from config import PUSHPLUS_TOKEN

def format_created_date(repo: Dict) -> str:
    created_at = repo.get("created_at")
    if not created_at:
        return ""
    try:
        created_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        return created_date.strftime("%Y-%m-%d")
    except:
        return ""

def send_pushplus_message(title: str, content: str, template: str = "html") -> bool:
    if not PUSHPLUS_TOKEN:
        print("PUSHPLUS_TOKEN not configured, skip push notification")
        return False
    
    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": template
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        if result.get("code") == 200:
            print("Push notification sent successfully")
            return True
        else:
            print(f"Push notification failed: {result.get('msg')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Push notification error: {e}")
        return False

def format_repos_for_wechat(trending_repos: Dict[str, List[Dict]], created_repos: Dict[str, List[Dict]],
                            explored_repos: List[Dict], fast_growing: List[Dict], newly_discovered: List[Dict]) -> str:
    html = """
    <html>
    <head>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
            .section { margin-bottom: 20px; }
            .section-title { font-size: 18px; font-weight: bold; color: #24292e; 
                           border-bottom: 2px solid #0366d6; padding-bottom: 5px; margin-bottom: 10px; }
            .repo { margin-bottom: 15px; padding: 10px; background: #f6f8fa; border-radius: 6px; }
            .repo-name { font-weight: bold; color: #0366d6; text-decoration: none; }
            .repo-name:hover { text-decoration: underline; }
            .repo-meta { font-size: 12px; color: #586069; margin-top: 5px; }
            .repo-desc { color: #24292e; margin-top: 5px; font-size: 14px; }
            .tag { display: inline-block; padding: 2px 6px; background: #e1e4e8; 
                  border-radius: 3px; font-size: 11px; margin-right: 5px; }
            .growth-tag { background: #d4edda; color: #155724; }
            .strategy-tag { background: #fff5b1; }
        </style>
    </head>
    <body>
    """
    
    if fast_growing:
        html += '<div class="section">'
        html += '<div class="section-title">🚀 快速增长项目</div>'
        for repo in fast_growing[:12]:
            html += format_growth_repo_html(repo)
        html += '</div>'
    
    if newly_discovered:
        html += '<div class="section">'
        html += '<div class="section-title">✨ 新发现项目</div>'
        for repo in newly_discovered[:10]:
            html += format_single_repo_html(repo)
        html += '</div>'
    
    trending_labels = {
        "daily": "今天获得最多新 star 的项目",
        "weekly": "本周获得最多新 star 的项目",
        "monthly": "本月获得最多新 star 的项目"
    }
    
    shown_repos = set()
    
    for period in ["daily", "weekly", "monthly"]:
        repos = trending_repos.get(period, [])
        if repos:
            html += '<div class="section">'
            html += f'<div class="section-title">{trending_labels[period]}</div>'
            count = 0
            for repo in repos:
                name = repo.get("full_name", "")
                if name in shown_repos:
                    continue
                shown_repos.add(name)
                count += 1
                if count > 5:
                    break
                html += format_single_repo_html(repo)
            html += '</div>'
    
    created_labels = {
        "today": "今天最新创建的项目最多 star",
        "this_week": "本周最新创建的项目最多 star",
        "this_month": "本月最新创建的项目最多 star"
    }
    
    for period in ["today", "this_week", "this_month"]:
        repos = created_repos.get(period, [])
        if repos:
            html += '<div class="section">'
            html += f'<div class="section-title">{created_labels[period]}</div>'
            count = 0
            for repo in repos:
                name = repo.get("full_name", "")
                if name in shown_repos:
                    continue
                shown_repos.add(name)
                count += 1
                if count > 5:
                    break
                html += format_single_repo_html(repo)
            html += '</div>'
    
    if explored_repos:
        html += '<div class="section">'
        html += '<div class="section-title">🔍 探索发现</div>'
        count = 0
        for repo in explored_repos:
            name = repo.get("full_name", "")
            if name in shown_repos:
                continue
            shown_repos.add(name)
            count += 1
            if count > 10:
                break
            html += format_single_repo_html(repo)
        html += '</div>'
    
    html += "</body></html>"
    return html

def format_growth_repo_html(repo: Dict) -> str:
    name = repo.get("full_name", "")
    url = repo.get("html_url", f"https://github.com/{name}")
    stars = repo.get("stargazers_count", 0)
    weekly_growth = repo.get("_weekly_growth", 0)
    daily_growth = repo.get("_daily_growth", 0)
    language = repo.get("language", "")
    desc = (repo.get("description") or "无描述")[:150]
    created = format_created_date(repo)
    
    html = f'<div class="repo">'
    html += f'<a href="{url}" class="repo-name">{name}</a>'
    html += '<div class="repo-meta">'
    html += f'⭐ {stars}'
    if created:
        html += f'  📅 {created}'
    if weekly_growth > 0:
        html += f'  <span class="tag growth-tag">+{weekly_growth}/周</span>'
    if daily_growth > 0:
        html += f'  <span class="tag growth-tag">+{daily_growth}/日</span>'
    if language:
        html += f'  <span class="tag">{language}</span>'
    html += '</div>'
    html += f'<div class="repo-desc">{desc}</div>'
    html += '</div>'
    
    return html

def format_single_repo_html(repo: Dict) -> str:
    name = repo.get("full_name", "")
    url = repo.get("html_url", f"https://github.com/{name}")
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    language = repo.get("language", "")
    desc = (repo.get("description") or "无描述")[:150]
    strategy = repo.get("_strategy", "")
    created = format_created_date(repo)
    
    html = f'<div class="repo">'
    html += f'<a href="{url}" class="repo-name">{name}</a>'
    html += '<div class="repo-meta">'
    html += f'⭐ {stars}  🍴 {forks}'
    if created:
        html += f'  📅 {created}'
    if language:
        html += f'  <span class="tag">{language}</span>'
    if strategy:
        html += f'  <span class="tag strategy-tag">{strategy}</span>'
    html += '</div>'
    html += f'<div class="repo-desc">{desc}</div>'
    html += '</div>'
    
    return html

def send_daily_report(trending_repos: Dict[str, List[Dict]], created_repos: Dict[str, List[Dict]],
                      explored_repos: List[Dict], fast_growing: List[Dict], newly_discovered: List[Dict], date_str: str) -> bool:
    title = f"GitHub 每日报告 - {date_str}"
    content = format_repos_for_wechat(trending_repos, created_repos, explored_repos, fast_growing, newly_discovered)
    return send_pushplus_message(title, content, template="html")

if __name__ == "__main__":
    test_trending = {
        "daily": [
            {
                "full_name": "test/daily-repo",
                "html_url": "https://github.com/test/daily-repo",
                "stargazers_count": 1000,
                "forks_count": 100,
                "language": "Python",
                "description": "A daily trending repository",
                "created_at": "2026-04-01T00:00:00Z"
            }
        ],
        "weekly": [],
        "monthly": []
    }
    test_created = {
        "today": [
            {
                "full_name": "test/new-repo",
                "html_url": "https://github.com/test/new-repo",
                "stargazers_count": 100,
                "forks_count": 10,
                "language": "TypeScript",
                "description": "A newly created repository",
                "created_at": "2026-04-02T00:00:00Z"
            }
        ],
        "this_week": [],
        "this_month": []
    }
    test_fast_growing = [
        {
            "full_name": "test/growing-repo",
            "html_url": "https://github.com/test/growing-repo",
            "stargazers_count": 500,
            "_weekly_growth": 150,
            "_daily_growth": 30,
            "language": "Go",
            "description": "A fast growing repository",
            "created_at": "2026-03-15T00:00:00Z"
        }
    ]
    test_newly_discovered = [
        {
            "full_name": "test/newly-repo",
            "html_url": "https://github.com/test/newly-repo",
            "stargazers_count": 100,
            "_first_seen": "2026-04-01",
            "language": "Rust",
            "description": "A newly discovered repository",
            "created_at": "2026-03-30T00:00:00Z"
        }
    ]
    
    content = format_repos_for_wechat(test_trending, test_created, test_fast_growing, test_newly_discovered)
    print(content)
