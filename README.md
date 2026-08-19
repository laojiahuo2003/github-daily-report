# GitHub 每日报告 📊

> **📦 另有博客版（2026-08-20 起）**：博客仓库 [laojiahuo2003.github.io](https://github.com/laojiahuo2003/laojiahuo2003.github.io) 的 [`daily/`](https://github.com/laojiahuo2003/laojiahuo2003.github.io/tree/main/daily) 目录也有一份生成器，在[博客日报页](https://laojiahuo2003.github.io/daily/)每日自动更新。本仓库继续独立运行，两边互不影响。

> 自动发现 GitHub 每日趋势、飙升项目与新兴开源项目，每天 09:00 / 18:00（北京时间）生成中文报告

[![Daily Report](https://github.com/laojiahuo2003/github-daily-report/actions/workflows/daily.yml/badge.svg)](https://github.com/laojiahuo2003/github-daily-report/actions/workflows/daily.yml)
[![RSS](https://img.shields.io/badge/RSS-订阅-orange)](./feed.xml)
[![最新报告](https://img.shields.io/badge/最新报告-查看-blue)](./reports/index.md)

## ✨ 报告内容

| 板块 | 说明 |
| --- | --- |
| 🏆 今日最佳项目 | 当日 star 增长量最高的项目，附完整信息卡 |
| 📊 今日飙升榜 | 排名表格：项目 / 今日增长🔺 / 总⭐ / 语言 / 分类 |
| 🚀 快速增长项目 | 基于历史追踪的周增长 50+ 项目（含趋势榜之外的黑马） |
| 🔥 热门项目 · 按分类 | 日/周/月趋势榜合并去重，按分类组织 |
| 🌱 新项目速递 · 按分类 | 近 7 天创建的高星新项目 |
| 🔍 探索发现 | 按语言（Python/TS/Rust/Go）和主题探索的新项目 |
| ✨ 新发现项目 | 最近 3 天首次进入追踪视野的项目 |

**分类体系**（关键词自动分类，见 `categorizer.py`）：🤖 AI / LLM · 🔒 网络安全 · ⚡ 自动化 / 效率 · 🛠️ 开发工具 · 🎨 前端 / UI · 📊 数据 / 可视化 · ⚙️ 系统 / 网络 · 📚 学习资源 · 📦 其他

## 📬 订阅方式

- **RSS**：订阅 [`feed.xml`](./feed.xml)（RSS 阅读器直接添加本仓库地址即可）
- **微信推送**：PushPlus 推送（见下方配置）
- **Watch 本仓库**：或直接查看 [历史报告索引](./reports/index.md)

## 🏗️ 工作原理

```
GitHub Trending 页面 ─┐
                      ├─→ 去重合并 ─→ 历史追踪(star增长) ─→ 分类 ─→ Markdown 报告 ─→ commit 到仓库
GitHub Search API  ───┘                                              ├─→ RSS (feed.xml)
（新项目/语言/主题探索）                                              └─→ 微信推送 (PushPlus)
```

- **数据源**：GitHub Trending 页面（含每日/周/月 star 增长量）+ GitHub Search API（新创建项目、按语言/主题探索）
- **历史追踪**：`history/stars_history.json` 记录每个项目每日 star 数，计算日/周增长，发现趋势榜之外的增长黑马
- **定时任务**：GitHub Actions 每天 09:00 / 18:00（北京时间）运行，报告自动提交，60 天前的旧报告自动清理

## 🔧 本地运行

```bash
pip install -r requirements.txt

# 可选：配置 token（提升 API 限额）
cp local_config_example.py local_config.py  # 填入 MY_GITHUB_TOKEN / PUSHPLUS_TOKEN

python main.py       # 生成完整报告到 reports/，同时更新索引和 RSS
python feed.py       # 仅重建 reports/index.md 和 feed.xml
```

环境变量优先级高于 `local_config.py`：`MY_GITHUB_TOKEN`、`PUSHPLUS_TOKEN`。

## 📁 目录结构

```
├── main.py               # 入口：抓取 → 分析 → 生成报告/索引/RSS → 推送
├── categorizer.py        # 关键词分类器（AI/安全/工具/前端/数据/系统/资源）
├── feed.py               # 历史索引 reports/index.md + RSS feed.xml
├── config.py             # 搜索策略、语言/主题配置
├── fetchers/
│   ├── trending.py       # Trending 页面抓取（解析 stars today 增长量）
│   └── search.py         # Search API：新项目发现 + 打分排序
├── history_tracker.py    # star 历史追踪，计算日/周增长
├── notifiers/wechat.py   # PushPlus 微信推送
├── reports/              # 每日报告（index.md 为索引）
└── history/              # star 历史数据
```

## 📝 说明

- 灵感来自 [OpenGithubs/github-daily-rank](https://github.com/OpenGithubs/github-daily-rank) 的榜单形式
- 所有数据来自公开页面与 API，不使用任何大模型生成内容
