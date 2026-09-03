#!/usr/bin/env python3
"""安全资讯同步：内网 EchoMind 情报聚合服务 -> news-archive 数据仓库 -> git push

数据流：GET /api/channels（渠道分类映射）+ GET /api/articles（文章）
  日常模式（默认）      ：拉近 2 天增量，合并去重，按月写入 months/YYYY-MM.json
  回填模式（--backfill）：拉服务端全量历史（2021-03 起），一次性建立完整归档

产物（全部写入独立数据仓库 ../news-archive，官网仓库不再存任何资讯数据）：
  months/YYYY-MM.json   按月分片全量归档（官网资讯页按月懒加载）
  feed.json             最近 24 条（首页/资讯页首屏快照）
  index.json            月度索引 + facets（分类/级别/来源全量计数）

用法：python3 scripts/sync_news.py [--no-push] [--backfill]
"""
import html
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HOSTS = ["192.168.1.7", "192.168.1.11", "192.168.1.12", "192.168.1.10", "192.168.1.6"]
PORT = 10010
CATEGORIES = ["security", "ai-security"]  # ai（AI 行业资讯）默认不收
CATEGORY_LABELS = {"security": "网络安全", "ai-security": "AI安全", "ai": "AI动态"}
LOOKBACK_DAYS = 2     # 日常模式拉取范围：昨天全量 + 今天已出的（10 点跑）
FETCH_LIMIT = 1000    # 日常模式单次拉取上限
BACKFILL_LIMIT = 30000  # 回填模式：服务端全量
FEED_SIZE = 24        # feed.json 保留条数
DIGEST_MAX = 160      # 摘要清洗后最大字符数
SITE = Path(__file__).resolve().parent.parent
# 数据仓库：默认与 blog-site 平级，可用环境变量 NEWS_ARCHIVE_DIR 覆盖
DATA_REPO = Path(os.environ.get("NEWS_ARCHIVE_DIR", SITE.parent / "news-archive"))
MONTHS_DIR = DATA_REPO / "months"


def find_service():
    for host in HOSTS:
        base = f"http://{host}:{PORT}"
        try:
            with urllib.request.urlopen(f"{base}/api/stats", timeout=4) as r:
                json.load(r)
            return base
        except Exception:
            continue
    raise SystemExit("内网 10010 服务不可达，逐个尝试过: " + ", ".join(HOSTS))


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=60) as r:
        return json.load(r)


def parse_published(s):
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def clean_desc(s):
    """摘要清洗：去 HTML 标签 -> 解码实体 -> 压空白 -> 截断。悬停预览用，不需要全文。"""
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:DIGEST_MAX] + ("…" if len(s) > DIGEST_MAX else "")


def sort_key(item):
    """按真实时间戳倒序：published_at 混着 +0800 / +0000 / GMT 时区，
    直接字符串排序会把 27 号的条目排到 31 号前面，必须解析后统一换算。
    旧条目从磁盘读回没有内存态，统一从 published_at 解析。"""
    ts = parse_published(item.get("published_at", ""))
    return ts.timestamp() if ts else 0.0


def load_archive():
    """读现有月度分片 -> {month: {id: item}}。日常增量据此全局去重。"""
    archive = {}
    if not MONTHS_DIR.exists():
        return archive
    for f in sorted(MONTHS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            archive[data["month"]] = {i["id"]: i for i in data.get("items", [])}
        except Exception as e:
            print(f"  ! 跳过损坏分片 {f.name}: {e}")
    return archive


def write_archive(archive):
    """分片排序落盘：月内按真实时间戳倒序。"""
    MONTHS_DIR.mkdir(parents=True, exist_ok=True)
    for month, items in archive.items():
        ordered = sorted(items.values(), key=sort_key, reverse=True)
        payload = {"month": month, "items": ordered}
        (MONTHS_DIR / f"{month}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
        )


def all_items(archive):
    return [i for items in archive.values() for i in items.values()]


def main():
    push = "--no-push" not in sys.argv
    backfill = "--backfill" in sys.argv
    limit = BACKFILL_LIMIT if backfill else FETCH_LIMIT
    base = find_service()
    print(f"[1/5] 服务在线: {base}{'（全量回填模式）' if backfill else ''}")

    channels = {c["id"]: c for c in get(base, "/api/channels")}
    wanted = {cid for cid, c in channels.items() if c.get("category") in CATEGORIES and c.get("is_enabled")}
    print(f"[2/5] 收录源: {len(wanted)} 个（分类 {CATEGORIES}）")

    articles = get(base, f"/api/articles?limit={limit}")
    cutoff = datetime(2000, 1, 1).astimezone() if backfill else datetime.now().astimezone() - timedelta(days=LOOKBACK_DAYS)
    fresh = {}
    for a in articles:
        if a.get("channel_id") not in wanted:
            continue
        ts = parse_published(a.get("published_at", ""))
        if ts is None or ts < cutoff:
            continue
        ch = channels.get(a.get("channel_id"), {})
        fresh[a["id"]] = {
            "id": a["id"],
            "title": a.get("title_cn") or a.get("title", ""),
            "url": a.get("url", ""),
            "source": a.get("source_name") or a.get("channel_id", ""),
            "category": CATEGORY_LABELS.get(ch.get("category"), "网络安全"),
            "priority": a.get("priority", ""),
            "published_at": a.get("published_at", ""),
            "published_date": ts.strftime("%Y-%m-%d"),
            "digest": clean_desc(a.get("description_cn") or a.get("description", "")),
        }
    print(f"[3/5] 本次拉取: {len(fresh)} 条{'（不限时间范围）' if backfill else f'（近 {LOOKBACK_DAYS} 天）'}")

    # 合并进归档：新数据覆盖同 id 旧数据，按 published_date 月份归位
    archive = load_archive()
    for item in fresh.values():
        month = item["published_date"][:7]
        if month < "2000-01":
            continue  # 防御：无有效日期的条目不归档
        archive.setdefault(month, {})[item["id"]] = item

    total = sum(len(v) for v in archive.values())
    print(f"[4/5] 归档合并: 共 {total} 条，覆盖 {min(archive)} ~ {max(archive)}（{len(archive)} 个月）")
    write_archive(archive)

    # feed：全量按时间倒序取头部（首页预览 / 资讯页首屏快照）
    flat = sorted(all_items(archive), key=sort_key, reverse=True)
    feed = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total": total,
            "items": flat[:FEED_SIZE]}
    (DATA_REPO / "feed.json").write_text(
        json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")

    # index：月度索引 + facets（官网筛选器全量选项与计数）
    facets = {"categories": {}, "sources": {}, "priorities": {}}
    for i in flat:
        facets["categories"][i["category"]] = facets["categories"].get(i["category"], 0) + 1
        facets["sources"][i["source"]] = facets["sources"].get(i["source"], 0) + 1
        facets["priorities"][i["priority"]] = facets["priorities"].get(i["priority"], 0) + 1
    facets["sources"] = dict(sorted(facets["sources"].items(), key=lambda kv: -kv[1]))
    index = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_count": len(wanted),
        "total": total,
        "months": [{"month": m, "count": len(v)} for m, v in sorted(archive.items(), reverse=True)],
        "facets": facets,
    }
    (DATA_REPO / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[5/5] 生成 feed.json（{min(FEED_SIZE, len(flat))} 条）+ index.json（{len(archive)} 个月索引）")

    if not push:
        return
    if not (DATA_REPO / ".git").exists():
        raise SystemExit("数据仓库尚未 git init，先初始化后再推送")
    status = subprocess.run(["git", "status", "--porcelain", "months", "index.json", "feed.json"],
                            cwd=DATA_REPO, capture_output=True, text=True)
    if not status.stdout.strip():
        print("无变化，跳过提交")
        return
    today = datetime.now().strftime("%Y-%m-%d")
    msg = (f"全量回档：{total} 条，覆盖 {min(archive)} ~ {max(archive)}" if backfill
           else f"安全资讯同步 {today}：新增 {len(fresh)} 条（总 {total} 条）")
    subprocess.run(["git", "add", "months", "index.json", "feed.json", "README.md"], cwd=DATA_REPO, check=True)
    subprocess.run(["git", "commit", "-m", msg], cwd=DATA_REPO, check=True)
    env = dict(os.environ)
    push_r = subprocess.run(["git", "push", "origin", "main"], cwd=DATA_REPO, capture_output=True, text=True)
    if push_r.returncode != 0:
        env["HTTPS_PROXY"] = "http://127.0.0.1:7890"  # 直连失败时走本地 Clash 代理兜底
        env["HTTP_PROXY"] = "http://127.0.0.1:7890"
        subprocess.run(["git", "push", "origin", "main"], cwd=DATA_REPO, env=env, check=True)
    print("已提交并推送数据仓库，GitHub Pages 约 1 分钟后重建")


if __name__ == "__main__":
    main()
