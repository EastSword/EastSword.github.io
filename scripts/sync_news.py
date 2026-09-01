#!/usr/bin/env python3
"""安全资讯同步：内网 EchoMind 情报聚合服务 -> _data/news.json -> git push

数据流：GET /api/channels（渠道分类映射）+ GET /api/articles（最新文章）
       -> 过滤 security / ai-security 分类 -> 按天合并去重 -> GitHub Pages 自动重建

用法：python3 scripts/sync_news.py [--no-push]
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HOSTS = ["192.168.1.7", "192.168.1.11", "192.168.1.12", "192.168.1.10", "192.168.1.6"]
PORT = 10010
CATEGORIES = ["security", "ai-security"]  # ai（AI 行业资讯）默认不收
CATEGORY_LABELS = {"security": "网络安全", "ai-security": "AI安全", "ai": "AI动态"}
LOOKBACK_DAYS = 2   # 拉取范围：昨天全量 + 今天已出的（10 点跑，覆盖“前一天出现的情报”）
FETCH_LIMIT = 1000
KEEP_MAX = 300
SITE = Path(__file__).resolve().parent.parent
OUT = SITE / "_data" / "news.json"


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
    with urllib.request.urlopen(base + path, timeout=20) as r:
        return json.load(r)


def parse_published(s):
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def sort_key(item):
    """按真实时间戳倒序：published_at 混着 +0800 / +0000 时区，
    直接字符串排序会把 27 号的条目排到 31 号前面，必须解析后统一换算。"""
    ts = parse_published(item.get("published_at", ""))
    return ts.timestamp() if ts else 0.0


def main():
    push = "--no-push" not in sys.argv
    base = find_service()
    print(f"[1/4] 服务在线: {base}")

    channels = {c["id"]: c for c in get(base, "/api/channels")}
    wanted = {cid for cid, c in channels.items() if c.get("category") in CATEGORIES and c.get("is_enabled")}
    print(f"[2/4] 收录源: {len(wanted)} 个（分类 {CATEGORIES}）")

    articles = get(base, f"/api/articles?limit={FETCH_LIMIT}")
    cutoff = datetime.now().astimezone() - timedelta(days=LOOKBACK_DAYS)
    fresh = {}
    for a in articles:
        if a.get("channel_id") not in wanted:
            continue
        ts = parse_published(a.get("published_at", ""))
        if ts is None or ts < cutoff:
            continue
        fresh[a["id"]] = {
            "id": a["id"],
            "title": a.get("title_cn") or a.get("title", ""),
            "url": a.get("url", ""),
            "source": a.get("source_name") or a.get("channel_id", ""),
            "category": CATEGORY_LABELS.get(channels.get(a.get("channel_id"), {}).get("category"), "网络安全"),
            "priority": a.get("priority", ""),
            "published_at": a.get("published_at", ""),
            "published_date": ts.strftime("%Y-%m-%d") if ts else "",
            "description": a.get("description_cn") or a.get("description", ""),
        }
    print(f"[3/4] 新增情报: {len(fresh)} 条（近 {LOOKBACK_DAYS} 天）")

    merged = {}
    if OUT.exists():
        try:
            merged = {i["id"]: i for i in json.loads(OUT.read_text(encoding="utf-8")).get("items", [])}
        except Exception:
            pass
    merged.update(fresh)
    items = sorted(merged.values(), key=sort_key, reverse=True)[:KEEP_MAX]
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_count": len(wanted),
        "items": items,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[4/4] 写入 {OUT.name}: 共 {len(items)} 条（保留上限 {KEEP_MAX}）")

    if not push:
        return
    diff = subprocess.run(
        ["git", "diff", "--stat", "--", OUT.relative_to(SITE).as_posix()],
        cwd=SITE, capture_output=True, text=True,
    )
    if not diff.stdout.strip():
        print("无变化，跳过提交")
        return
    today = datetime.now().strftime("%Y-%m-%d")
    subprocess.run(["git", "add", OUT.relative_to(SITE).as_posix()], cwd=SITE, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"安全资讯自动同步 {today}：新增 {len(fresh)} 条"],
        cwd=SITE, check=True,
    )
    env = dict(os.environ)
    push = subprocess.run(["git", "push", "origin", "main"], cwd=SITE, capture_output=True, text=True)
    if push.returncode != 0:
        # 直连失败时走本地 Clash 代理兜底
        env["HTTPS_PROXY"] = "http://127.0.0.1:7890"
        env["HTTP_PROXY"] = "http://127.0.0.1:7890"
        push = subprocess.run(["git", "push", "origin", "main"], cwd=SITE, env=env, check=True)
    print("已提交并推送，GitHub Pages 约 1 分钟后重建")


if __name__ == "__main__":
    main()
