import requests
from datetime import datetime
from typing import List, Dict
from config import (
    CREATED_REPOS_STRATEGIES,
    LANGUAGE_EXPLORATION,
    TOPIC_EXPLORATION,
    MAX_RESULTS_PER_STRATEGY,
    MAX_LANGUAGE_RESULTS,
    MAX_TOPIC_RESULTS,
    get_date_days_ago,
    MY_GITHUB_TOKEN
)

HEADERS = {
    "Accept": "application/vnd.github.v3+json"
}
if MY_GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {MY_GITHUB_TOKEN}"

def search_repositories(query: str, per_page: int = 30, sort: str = "stars") -> List[Dict]:
    url = "https://api.github.com/search/repositories"
    params = {
        "q": query,
        "per_page": per_page,
        "sort": sort,
        "order": "desc"
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])
    except requests.exceptions.RequestException as e:
        print(f"Search error: {e}")
        return []

def calculate_repo_score(repo: Dict) -> float:
    score = 0.0
    
    stars = repo.get("stargazers_count", 0)
    score += min(stars / 50, 30)
    
    forks = repo.get("forks_count", 0)
    score += min(forks / 10, 15)
    
    watchers = repo.get("watchers_count", 0)
    score += min(watchers / 10, 10)
    
    if repo.get("has_wiki"):
        score += 2
    if repo.get("has_issues"):
        score += 2
    
    topics = repo.get("topics", [])
    if topics:
        score += len(topics) * 2
    
    created_at = repo.get("created_at")
    if created_at:
        try:
            created_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
            days_since_created = (datetime.now() - created_date).days
            if days_since_created <= 1:
                score += 50
            elif days_since_created <= 3:
                score += 30
            elif days_since_created <= 7:
                score += 20
            elif days_since_created <= 14:
                score += 10
        except:
            pass
    
    pushed_at = repo.get("pushed_at")
    if pushed_at:
        try:
            pushed_date = datetime.strptime(pushed_at, "%Y-%m-%dT%H:%M:%SZ")
            days_since_update = (datetime.now() - pushed_date).days
            score += max(15 - days_since_update, 0)
        except:
            pass
    
    return score

def fetch_created_repos() -> Dict[str, List[Dict]]:
    result = {}
    
    for strategy_name, strategy_config in CREATED_REPOS_STRATEGIES.items():
        date_str = get_date_days_ago(strategy_config["date_delta"])
        sort_by = strategy_config.get("sort", "stars")
        
        query = strategy_config["query_template"].format(date=date_str)
        repos = search_repositories(query, MAX_RESULTS_PER_STRATEGY, sort_by)
        
        for repo in repos:
            repo["_strategy"] = strategy_config["desc"]
            repo["_score"] = calculate_repo_score(repo)
        
        result[strategy_name] = repos
        print(f"    - {strategy_config['desc']}: {len(repos)} repos")
    
    return result

def explore_by_language() -> List[Dict]:
    all_results = []
    seen_names = set()
    
    for lang_name, lang_config in LANGUAGE_EXPLORATION.items():
        date_str = get_date_days_ago(lang_config["date_delta"])
        
        query = lang_config["query_template"].format(date=date_str)
        results = search_repositories(query, MAX_LANGUAGE_RESULTS, "stars")
        
        for repo in results:
            if repo["full_name"] not in seen_names:
                seen_names.add(repo["full_name"])
                repo["_strategy"] = lang_config["desc"]
                repo["_score"] = calculate_repo_score(repo)
                all_results.append(repo)
    
    return all_results

def explore_by_topics() -> List[Dict]:
    all_results = []
    seen_names = set()
    
    for topic in TOPIC_EXPLORATION[:5]:
        date_str = get_date_days_ago(7)
        query = f"topic:{topic} created:>{date_str} stars:>3 fork:false archived:false"
        results = search_repositories(query, MAX_TOPIC_RESULTS, "stars")
        
        for repo in results:
            if repo["full_name"] not in seen_names:
                seen_names.add(repo["full_name"])
                repo["_strategy"] = f"Topic: {topic}"
                repo["_score"] = calculate_repo_score(repo)
                all_results.append(repo)
    
    return all_results

def explore_all() -> List[Dict]:
    all_results = []
    seen_names = set()
    
    print("  - Exploring by languages...")
    lang_results = explore_by_language()
    for repo in lang_results:
        if repo["full_name"] not in seen_names:
            seen_names.add(repo["full_name"])
            all_results.append(repo)
    
    print("  - Exploring by topics...")
    topic_results = explore_by_topics()
    for repo in topic_results:
        if repo["full_name"] not in seen_names:
            seen_names.add(repo["full_name"])
            all_results.append(repo)
    
    all_results.sort(key=lambda x: x["_score"], reverse=True)
    return all_results

def format_repo_info(repo: Dict) -> str:
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    desc = repo.get("description") or "无描述"
    language = repo.get("language") or ""
    strategy = repo.get("_strategy", "")
    
    info = f"**{repo['full_name']}** ⭐{stars} 🍴{forks}"
    if language:
        info += f" `{language}`"
    info += f" [{strategy}]\n"
    info += f"> {desc[:100]}..."
    
    return info

if __name__ == "__main__":
    created = fetch_created_repos()
    for period, repos in created.items():
        print(f"\n{period}: {len(repos)} repos")
        for repo in repos[:3]:
            print(format_repo_info(repo))
