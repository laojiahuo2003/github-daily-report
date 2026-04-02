import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history")
HISTORY_FILE = os.path.join(HISTORY_DIR, "stars_history.json")

def ensure_history_dir():
    os.makedirs(HISTORY_DIR, exist_ok=True)

def load_history() -> Dict:
    ensure_history_dir()
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_history(history: Dict):
    ensure_history_dir()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def record_repos(repos: List[Dict]):
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    
    for repo in repos:
        full_name = repo.get("full_name")
        if not full_name:
            continue
            
        stars = repo.get("stargazers_count", 0)
        
        if full_name not in history:
            history[full_name] = {
                "first_seen": today,
                "stars_history": {}
            }
        
        history[full_name]["stars_history"][today] = stars
        history[full_name]["last_seen"] = today
        history[full_name]["current_stars"] = stars
    
    clean_old_history(history)
    save_history(history)

def clean_old_history(history: Dict, keep_days: int = 30):
    cutoff_date = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    
    for repo_name, repo_data in history.items():
        stars_history = repo_data.get("stars_history", {})
        repo_data["stars_history"] = {
            date: stars for date, stars in stars_history.items()
            if date >= cutoff_date
        }

def calculate_growth(repo_name: str, history: Dict) -> Dict:
    if repo_name not in history:
        return {"daily_growth": 0, "weekly_growth": 0, "growth_rate": 0}
    
    repo_history = history[repo_name]
    stars_history = repo_history.get("stars_history", {})
    current_stars = repo_history.get("current_stars", 0)
    
    today = datetime.now()
    
    daily_growth = 0
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    if yesterday in stars_history:
        daily_growth = current_stars - stars_history[yesterday]
    
    weekly_growth = 0
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    if week_ago in stars_history:
        weekly_growth = current_stars - stars_history[week_ago]
    
    growth_rate = 0
    if current_stars > 0 and weekly_growth > 0:
        growth_rate = round((weekly_growth / current_stars) * 100, 1)
    
    return {
        "daily_growth": daily_growth,
        "weekly_growth": weekly_growth,
        "growth_rate": growth_rate,
        "first_seen": repo_history.get("first_seen", "")
    }

def get_fast_growing_repos(repos: List[Dict], min_weekly_growth: int = 50) -> List[Dict]:
    history = load_history()
    
    for repo in repos:
        full_name = repo.get("full_name", "")
        growth = calculate_growth(full_name, history)
        repo["_daily_growth"] = growth["daily_growth"]
        repo["_weekly_growth"] = growth["weekly_growth"]
        repo["_growth_rate"] = growth["growth_rate"]
        repo["_first_seen"] = growth["first_seen"]
    
    growing_repos = [r for r in repos if r.get("_weekly_growth", 0) >= min_weekly_growth]
    growing_repos.sort(key=lambda x: x.get("_weekly_growth", 0), reverse=True)
    
    return growing_repos

def get_newly_discovered_repos(repos: List[Dict], days: int = 3) -> List[Dict]:
    history = load_history()
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    new_repos = []
    for repo in repos:
        full_name = repo.get("full_name", "")
        if full_name in history:
            first_seen = history[full_name].get("first_seen", "")
            if first_seen >= cutoff_date:
                repo["_first_seen"] = first_seen
                new_repos.append(repo)
    
    return new_repos
