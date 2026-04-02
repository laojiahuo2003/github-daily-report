import os
from datetime import datetime, timedelta

try:
    from local_config import MY_GITHUB_TOKEN as LOCAL_GITHUB_TOKEN
    from local_config import PUSHPLUS_TOKEN as LOCAL_PUSHPLUS_TOKEN
except ImportError:
    LOCAL_GITHUB_TOKEN = None
    LOCAL_PUSHPLUS_TOKEN = None

CREATED_REPOS_STRATEGIES = {
    "today": {
        "query_template": "created:>{date} fork:false archived:false",
        "date_delta": 1,
        "desc": "今天最新创建的项目最多 star",
        "sort": "stars"
    },
    "this_week": {
        "query_template": "created:>{date} stars:>3 fork:false archived:false",
        "date_delta": 7,
        "desc": "本周最新创建的项目最多 star",
        "sort": "stars"
    },
    "this_month": {
        "query_template": "created:>{date} stars:>5 fork:false archived:false",
        "date_delta": 30,
        "desc": "本月最新创建的项目最多 star",
        "sort": "stars"
    }
}

LANGUAGE_EXPLORATION = {
    "python": {
        "query_template": "language:Python created:>{date} stars:>3 fork:false archived:false",
        "date_delta": 7,
        "desc": "Python 新项目"
    },
    "typescript": {
        "query_template": "language:TypeScript created:>{date} stars:>3 fork:false archived:false",
        "date_delta": 7,
        "desc": "TypeScript 新项目"
    },
    "rust": {
        "query_template": "language:Rust created:>{date} stars:>3 fork:false archived:false",
        "date_delta": 7,
        "desc": "Rust 新项目"
    },
    "go": {
        "query_template": "language:Go created:>{date} stars:>3 fork:false archived:false",
        "date_delta": 7,
        "desc": "Go 新项目"
    }
}

TOPIC_EXPLORATION = [
    "artificial-intelligence",
    "machine-learning",
    "developer-tools",
    "productivity",
    "automation",
    "cli",
    "api",
    "framework",
    "library",
    "tool"
]

TRENDING_LANGUAGES = ["python", "typescript", "rust", "go"]

MAX_RESULTS_PER_STRATEGY = 50
MAX_LANGUAGE_RESULTS = 30
MAX_TOPIC_RESULTS = 20
MAX_TOTAL_RESULTS = 150

MY_GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN") or LOCAL_GITHUB_TOKEN or ""

PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN") or LOCAL_PUSHPLUS_TOKEN or ""

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")

def get_date_days_ago(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
