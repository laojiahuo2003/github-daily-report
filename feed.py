import os
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape

REPO_URL = "https://github.com/laojiahuo2003/github-daily-report"
RSS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feed.xml")
INDEX_HEADER = "# 📜 历史报告索引\n\n> 每日 09:00 / 18:00（北京时间）自动更新 · [RSS 订阅](../feed.xml)\n\n"


def list_report_files(reports_dir: str) -> list:
    """列出报告文件，按文件名（即时间）倒序"""
    if not os.path.isdir(reports_dir):
        return []
    files = [f for f in os.listdir(reports_dir) if re.match(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.md$", f)]
    return sorted(files, reverse=True)


def latest_report_per_day(files: list) -> list:
    """同一天多次运行只保留最新一份"""
    seen_days = set()
    result = []
    for f in files:
        day = f[:10]
        if day not in seen_days:
            seen_days.add(day)
            result.append(f)
    return result


def report_summary(filepath: str, max_items: int = 15) -> str:
    """提取报告开头的飙升榜表格行作为摘要（纯文本）"""
    lines = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 表格数据行：以 | 开头且含 markdown 链接（表头和分隔行没有链接）
                # 保留 [name](url) 链接格式，订阅端可解析为可点击的项目名
                if line.startswith("|") and "](" in line:
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    if len(cells) >= 4:
                        # 排名 | 项目 | 增长 | 总⭐ |（有则带上语言、分类）
                        lines.append(" | ".join(cells[:6]))
                if len(lines) >= max_items:
                    break
    except OSError:
        pass
    return "\n".join(lines)


def generate_index(reports_dir: str, max_days: int = 60):
    """生成 reports/index.md：按天倒序的历史报告索引"""
    files = latest_report_per_day(list_report_files(reports_dir))[:max_days]

    content = [INDEX_HEADER, "| 日期 | 报告 |", "| --- | --- |"]
    for f in files:
        day = f[:10]
        content.append(f"| {day} | [{f}]({f}) |")

    index_path = os.path.join(reports_dir, "index.md")
    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(content) + "\n")
    print(f"Index saved to: {index_path}")


def generate_rss(reports_dir: str, max_items: int = 15):
    """生成仓库根目录 feed.xml，供 RSS 阅读器订阅"""
    files = latest_report_per_day(list_report_files(reports_dir))[:max_items]

    items = []
    for f in files:
        day = f[:10]
        link = f"{REPO_URL}/blob/main/reports/{f}"
        summary = report_summary(os.path.join(reports_dir, f))
        items.append(
            "    <item>\n"
            f"      <title>GitHub 每日报告 - {day}</title>\n"
            f"      <link>{escape(link)}</link>\n"
            f"      <guid>{escape(link)}</guid>\n"
            "      <description><![CDATA[\n"
            f"{summary}\n"
            "      ]]></description>\n"
            "    </item>"
        )

    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        "    <title>GitHub 每日报告</title>\n"
        f"    <link>{REPO_URL}</link>\n"
        "    <description>每日 GitHub 趋势、飙升榜与新项目发现（09:00 / 18:00 更新）</description>\n"
        "    <language>zh-cn</language>\n"
        f"    <lastBuildDate>{now}</lastBuildDate>\n"
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )

    with open(RSS_FILE, "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"RSS feed saved to: {RSS_FILE}")


if __name__ == "__main__":
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    generate_index(reports_dir)
    generate_rss(reports_dir)
