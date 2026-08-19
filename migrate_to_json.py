#!/usr/bin/env python3
"""一次性迁移：把历史 reports/*.md 解析成 reports/*.json，并重建 feed.json。

报告由 main.py 的 generate_markdown_report 确定性生成，格式稳定，可按结构解析。
运行一次即可；之后由 main.py 的 build_report_data 直接产出 JSON，无需再解析 markdown。
"""
import json
import os
import re

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")

LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
BULLET = re.compile(r'^(?:[-*]|\d+\.)\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*\s+⭐([\w.]+)(.*)$')
BEST_NAME = re.compile(r'^\*\*\[([^\]]+)\]\(([^)]+)\)\*\*$')
DESC = re.compile(r'^\s*>\s*(.*)$')


def parse_stars(s):
    s = (s or "").strip()
    m = re.match(r'^([\d.]+)([kK])?$', s)
    if not m:
        return 0
    v = float(m.group(1))
    if m.group(2):
        v *= 1000
    return int(v)


def new_repo(name, url, stars_fmt, category=""):
    return {
        "name": name, "url": url,
        "stars": parse_stars(stars_fmt), "stars_fmt": stars_fmt,
        "growth": 0, "weekly_growth": 0, "language": "", "category": category,
        "description": "", "created": "", "source": "", "first_seen": "",
    }


def parse_bullet(line, category=""):
    m = BULLET.match(line)
    if not m:
        return None
    repo = new_repo(m.group(1), m.group(2), m.group(3), category)
    rest = m.group(4)
    cm = re.search(r'📅(\d{4}-\d{2}-\d{2})', rest)
    if cm:
        repo["created"] = cm.group(1)
    for t in re.findall(r'`([^`]+)`', rest):
        if t in ("今日", "本周", "本月"):
            repo["source"] = t
        elif t.endswith("发现"):
            repo["first_seen"] = t[:-2]
        elif re.match(r'^\+?\d+[kK]?/(日|周)$', t):
            n = re.match(r'^\+?(\d+)[kK]?', t)
            if "/周" in t:
                repo["weekly_growth"] = int(n.group(1))
            else:
                repo["growth"] = int(n.group(1))
        else:
            repo["language"] = t
    return repo


def parse_leaderboard_row(cells):
    # 排名 | 项目 | 今日增长 | 总⭐ | 语言 | 分类 | 简介
    if len(cells) < 6:
        return None
    m = LINK.match(cells[1])
    if not m:
        return None
    repo = new_repo(m.group(1), m.group(2), cells[3], cells[5])
    repo["language"] = cells[4]
    g = re.search(r'(\d+)', cells[2])
    if g:
        repo["growth"] = int(g.group(1))
    repo["description"] = cells[6] if len(cells) > 6 else ""
    return repo


def parse_fast_row(cells):
    # 排名 | 项目 | 周增长 | 总⭐ | 语言
    if len(cells) < 5:
        return None
    m = LINK.match(cells[1])
    if not m:
        return None
    repo = new_repo(m.group(1), m.group(2), cells[3])
    repo["language"] = cells[4]
    g = re.search(r'(\d+)', cells[2])
    if g:
        repo["weekly_growth"] = int(g.group(1))
    return repo


def parse_report(text, date):
    data = {
        "date": date, "best": None, "leaderboard": [], "fast_growing": [], "monthly": [],
        "by_category": [], "new_projects": [], "explored": [], "newly_discovered": [],
    }
    section, cur, last = None, None, None

    for line in text.split("\n"):
        s = line.strip()

        if s.startswith("## "):
            h = s[3:]
            if h.startswith("🏆"):
                section, cur = "best", None
            elif h.startswith("📊"):
                section, cur = "leaderboard", None
            elif h.startswith("🚀"):
                section, cur = "fast", None
            elif h.startswith("🔥"):
                section, cur = "bycat", None
            elif h.startswith("🌱"):
                section, cur = "new", None
            elif h.startswith("🔍"):
                section, cur = "explored", None
            elif h.startswith("✨"):
                section, cur = "newdisc", None
            elif "获得最多新 star" in h:  # 旧格式：今天/本周/本月 star 榜
                if h.startswith("今天"):
                    section = "leaderboard"
                elif h.startswith("本周"):
                    section = "fast"
                else:
                    section = "monthly"
                cur = None
            elif "最新创建的项目" in h:  # 旧格式：今天/本周/本月 新创建
                label = "今天新创建" if h.startswith("今天") else "本周新创建" if h.startswith("本周") else "本月新创建"
                cur = {"category": label, "projects": []}
                data["new_projects"].append(cur)
                section = "old_created"
            else:
                section, cur = None, None
            last = None
            continue

        if s.startswith("### "):
            h = s[4:]
            if section in ("bycat", "new"):
                cur = {"category": h, "projects": []}
                (data["by_category"] if section == "bycat" else data["new_projects"]).append(cur)
            elif section == "explored":
                cur = {"strategy": h, "projects": []}
                data["explored"].append(cur)
            last = None
            continue

        # 表格数据行（表头/分隔行无 markdown 链接，自动跳过）
        if s.startswith("|") and "](" in s:
            cells = [c.strip() for c in s.strip().strip("|").split("|")]
            if section == "leaderboard":
                r = parse_leaderboard_row(cells)
                if r:
                    data["leaderboard"].append(r)
            elif section == "fast":
                r = parse_fast_row(cells)
                if r:
                    data["fast_growing"].append(r)
            last = None
            continue

        if section == "best":
            bm = BEST_NAME.match(s)
            if bm and data["best"] is None:
                data["best"] = new_repo(bm.group(1), bm.group(2), "")
                last = data["best"]
                continue
            if s.startswith("- ") and data["best"] is not None:
                kv = re.match(r'^-\s*([^：:]+)[：:]\s*(.*)$', s)
                if kv:
                    key, val = kv.group(1), kv.group(2).strip()
                    if "星标" in key:
                        data["best"]["stars_fmt"] = val
                        data["best"]["stars"] = parse_stars(val)
                    elif "增长" in key:
                        g = re.search(r'\d+', val)
                        data["best"]["growth"] = int(g.group()) if g else 0
                    elif "语言" in key:
                        data["best"]["language"] = val
                    elif "分类" in key:
                        data["best"]["category"] = val
                    elif "简介" in key:
                        data["best"]["description"] = val
                    elif "创建" in key:
                        data["best"]["created"] = val
                last = None
                continue

        dm = DESC.match(s)
        if dm and last is not None and not last.get("description"):
            last["description"] = dm.group(1).strip()
            continue

        bp = parse_bullet(line, cur["category"] if cur and "category" in cur else "")
        if bp:
            if section == "newdisc":
                data["newly_discovered"].append(bp)
            elif section == "leaderboard":
                data["leaderboard"].append(bp)
            elif section == "fast":
                data["fast_growing"].append(bp)
            elif section == "monthly":
                data["monthly"].append(bp)
            elif cur is not None:
                cur["projects"].append(bp)
            last = bp
            continue

        last = None

    return data


def main():
    files = sorted(
        [f for f in os.listdir(REPORTS_DIR) if re.match(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.md$", f)],
        reverse=True,
    )
    written = 0
    for f in files:
        with open(os.path.join(REPORTS_DIR, f), "r", encoding="utf-8") as fh:
            text = fh.read()
        data = parse_report(text, f[:10])
        json_path = os.path.join(REPORTS_DIR, f[:-3] + ".json")
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        written += 1
    print(f"迁移完成：{written} 份 .md → .json")

    # 重建 feed.json
    import feed
    feed.generate_json_index(REPORTS_DIR)


if __name__ == "__main__":
    main()
