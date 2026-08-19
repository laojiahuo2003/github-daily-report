import re
from typing import Dict, List

# 分类规则：按顺序匹配（先匹配到的优先），关键词命中 full_name/description/topics
# 英文关键词按单词边界匹配（避免 "ai" 命中 "email"），中文关键词按子串匹配
CATEGORY_RULES = [
    ("🤖 AI / LLM", [
        "llm", "gpt", "agent", "ai", "agi", "mcp", "rag",
        "machine learning", "deep learning", "artificial intelligence",
        "transformer", "diffusion", "inference", "embedding", "fine-tuning", "finetuning",
        "chatbot", "copilot", "neural", "llama", "qwen", "deepseek", "openai", "claude", "gemini",
        "人工智能", "大模型", "机器学习", "深度学习", "大语言模型", "智能体", "推理", "知识库",
    ]),
    ("🔒 网络安全", [
        "security", "ctf", "vulnerab", "exploit", "pentest", "red team", "osint",
        "malware", "ransomware", "encrypt", "cryptography", "firewall", "zero-day",
        "安全", "漏洞", "渗透", "密码学", "加密",
    ]),
    ("⚡ 自动化 / 效率", [
        "automation", "automate", "workflow", "productivity", "bot", "scraping", "scraper",
        "crawler", "spider", "pipeline", "scheduler", "rpa", "batch",
        "自动化", "爬虫", "效率", "批处理", "工作流",
    ]),
    ("🛠️ 开发工具", [
        "cli", "tool", "toolkit", "sdk", "framework", "library", "developer", "devtool",
        "ide", "editor", "debug", "compiler", "linter", "devops", "ci/cd", "terminal",
        "git", "testing", "lint", "build", "package", "api",
        "开发", "编译", "调试", "终端",
    ]),
    ("🎨 前端 / UI", [
        "ui", "frontend", "css", "react", "vue", "svelte", "angular", "component",
        "dashboard", "website", "web app", "desktop app", "design system", "theme",
        "template", "game", "gui",
        "界面", "前端", "可视化界面",
    ]),
    ("📊 数据 / 可视化", [
        "data", "visualization", "analytics", "database", "sql", "etl", "chart",
        "bi", "metrics", "monitoring", "observability",
        "数据", "可视化", "图表", "监控",
    ]),
    ("⚙️ 系统 / 网络", [
        "os", "kernel", "network", "server", "proxy", "docker", "kubernetes", "k8s",
        "linux", "distributed", "rpc", "filesystem", "embedded", "iot", "raspberry",
        "操作系统", "内核", "网络", "分布式", "嵌入式",
    ]),
    ("📚 学习资源", [
        "tutorial", "course", "learn", "interview", "awesome", "book", "guide",
        "roadmap", "resource", "cheatsheet", "cheat sheet", "example", "doc",
        "教程", "面试", "指南", "学习", "资源", "入门",
    ]),
]

DEFAULT_CATEGORY = "📦 其他"

CATEGORY_ORDER = [name for name, _ in CATEGORY_RULES] + [DEFAULT_CATEGORY]


def _compile_keywords(keywords: List[str]):
    compiled = []
    for kw in keywords:
        if kw.isascii():
            compiled.append((re.compile(r"(?<![a-z0-9])" + re.escape(kw.lower()) + r"(?![a-z0-9])"), kw))
        else:
            compiled.append((None, kw))
    return compiled


_COMPILED_RULES = [(name, _compile_keywords(kws)) for name, kws in CATEGORY_RULES]


def categorize_repo(repo: Dict) -> str:
    """根据仓库名、描述、topics 判断项目分类"""
    parts = [
        repo.get("full_name", "") or "",
        repo.get("description", "") or "",
        " ".join(repo.get("topics", []) or []),
    ]
    text = " ".join(parts).lower()

    for category, patterns in _COMPILED_RULES:
        for pattern, kw in patterns:
            if pattern is None:
                if kw in text:
                    return category
            elif pattern.search(text):
                return category

    return DEFAULT_CATEGORY


def group_by_category(repos: List[Dict], max_per_category: int = 0) -> Dict[str, List[Dict]]:
    """把仓库列表按分类分组，保持 CATEGORY_ORDER 的顺序"""
    groups: Dict[str, List[Dict]] = {}
    for repo in repos:
        category = repo.get("_category") or categorize_repo(repo)
        repo["_category"] = category
        groups.setdefault(category, []).append(repo)

    ordered = {}
    for category in CATEGORY_ORDER:
        if category in groups:
            items = groups[category]
            if max_per_category > 0:
                items = items[:max_per_category]
            ordered[category] = items
    return ordered


if __name__ == "__main__":
    test_repos = [
        {"full_name": "a/b", "description": "A local LLM inference server", "topics": []},
        {"full_name": "c/d", "description": "Beautiful CLI tool for git", "topics": []},
        {"full_name": "e/f", "description": "Awesome list of machine learning resources", "topics": []},
        {"full_name": "g/h", "description": "Email template engine", "topics": []},
    ]
    for repo in test_repos:
        print(f"{repo['full_name']}: {categorize_repo(repo)}")
