import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from config import TRENDING_LANGUAGES

def fetch_trending_by_period(since: str = "daily") -> List[Dict]:
    url = "https://github.com/trending"
    params = {"since": since}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        repos = []
        articles = soup.select("article.Box-row")
        
        for article in articles:
            try:
                repo_link = article.select_one("h2 a")
                if not repo_link:
                    continue

                full_name = repo_link.get("href", "").strip("/")

                desc_elem = article.select_one("p")
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                stars_elem = article.select_one('[href$="/stargazers"]')
                stars = stars_elem.get_text(strip=True).replace(",", "") if stars_elem else "0"
                stars = parse_number(stars)

                forks_elem = article.select_one('[href$="/network/members"]')
                forks = forks_elem.get_text(strip=True).replace(",", "") if forks_elem else "0"
                forks = parse_number(forks)

                language_elem = article.select_one('[itemprop="programmingLanguage"]')
                language = language_elem.get_text(strip=True) if language_elem else ""

                # 页面上的 "1,234 stars today/this week/this month" 增长数据
                stars_gained = 0
                gained_elem = article.select_one("span.d-inline-block.float-sm-right")
                if gained_elem:
                    gained_text = gained_elem.get_text(strip=True)
                    for token in gained_text.replace(",", "").split():
                        if token.isdigit():
                            stars_gained = int(token)
                            break

                repos.append({
                    "full_name": full_name,
                    "description": description,
                    "stargazers_count": stars,
                    "forks_count": forks,
                    "language": language,
                    "html_url": f"https://github.com/{full_name}",
                    "_period": since,
                    "_stars_gained": stars_gained
                })
            except Exception as e:
                continue
                
        return repos
    except requests.exceptions.RequestException as e:
        print(f"Trending fetch error: {e}")
        return []

def fetch_trending_repos(language: str = "", since: str = "daily") -> List[Dict]:
    return fetch_trending_by_period(since)

def parse_number(s: str) -> int:
    s = s.strip().lower()
    if "k" in s:
        return int(float(s.replace("k", "")) * 1000)
    try:
        return int(s)
    except:
        return 0

def fetch_all_trending() -> Dict[str, List[Dict]]:
    periods = {
        "daily": "今日热门",
        "weekly": "本周热门",
        "monthly": "本月热门"
    }

    result = {}

    for period, label in periods.items():
        repos = fetch_trending_by_period(since=period)
        # 每个周期保留完整榜单（跨周期去重在报告生成时统一做，
        # 之前在这里去重会导致周榜/月榜缺项，不是真实排名）
        for repo in repos:
            repo["_period_label"] = label
        result[period] = repos

    return result

def format_trending_repo(repo: Dict) -> str:
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    desc = repo.get("description") or "无描述"
    language = repo.get("language") or ""
    
    info = f"**{repo['full_name']}** ⭐{stars} 🍴{forks}"
    if language:
        info += f" `{language}`"
    info += f"\n> {desc[:100]}..."
    
    return info

if __name__ == "__main__":
    repos = fetch_all_trending()
    print(f"Found {len(repos)} trending repos")
    for repo in repos[:10]:
        print(format_trending_repo(repo))
