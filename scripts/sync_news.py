#!/usr/bin/env python3
"""安全资讯同步：内网 EchoMind 情报聚合服务 -> news-archive 数据仓库 -> git push

数据流：GET /api/channels（渠道分类映射）+ GET /api/articles（文章）
  日常模式（默认）      ：拉近 2 天增量，合并去重，按月写入 months/YYYY-MM.json
  回填模式（--backfill）：拉服务端全量历史（2021-03 起），一次性建立完整归档

富化加工（合并后统一执行）：
  tags       内容标签：21 组关键词规则引擎（标题+摘要联合匹配，每条最多 4 个标签），
             每次运行全量重算（幂等），规则更新后无需特殊操作即可全量刷新
  title_zh   英文标题中文翻译：本机 ollama qwen2.5:7b 翻译（只翻无 CJK 字符的标题），
             增量执行——已带 title_zh 的条目直接复用（归档本身就是翻译缓存），
             ollama 不可达时跳过翻译不影响同步，下次运行自动补翻

产物（全部写入独立数据仓库 ../news-archive，官网仓库不再存任何资讯数据）：
  months/YYYY-MM.json   按月分片全量归档（官网资讯页按月懒加载）
  feed.json             最近 24 条（首页/资讯页首屏快照）
  index.json            月度索引 + facets（分类/级别/标签/来源全量计数）

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

# ---------- 内容标签规则引擎 ----------
# 顺序即优先级：条目标签数达到上限时，排在前面的标签优先保留。
# 匹配对象：标题 + 摘要 联合小写化文本（中文不受影响）。
TAGS_MAX = 4
TAG_RULES = [
    ("勒索软件", r"ransomware|勒索软件|勒索攻击|勒索病毒|lockbit|black ?cat|alphv|akira|\bhive\b"),
    ("APT组织", r"\bapt ?-?\d+\b|lazarus|kimsuky|sandworm|volt ?typhoon|mustang ?panda|黑客组织|威胁组织|apt 攻击|apt攻击|国家级攻击|政府支持|间谍软件|spyware"),
    ("漏洞预警", r"cve-\d|ghsa-|零日|0day|0-day|zero ?day|在野利用|actively exploit|远程代码执行|\brce\b|漏洞利用|高危漏洞|安全漏洞|漏洞预警|漏洞披露|未修复"),
    ("供应链攻击", r"supply ?chain|供应链|dependency confusion|typosquat|包投毒|\bnpm\b|\bpypi\b|开源组件|第三方库"),
    ("数据泄露", r"data ?breach|数据泄露|数据泄漏|信息泄露|数据库泄|exposed data|数据窃取|撞库|credential stuffing"),
    ("钓鱼攻击", r"phishing|钓鱼|鱼叉|smishing|vishing|社会工程|社工攻击|仿冒网站"),
    ("网络诈骗", r"\bscam|诈骗|fraud|杀猪盘|洗钱|money laundering|博彩|赌场|虚假投资"),
    ("加密货币犯罪", r"cryptocurrenc|加密货币|比特币|bitcoin|以太坊|ethereum|挖矿木马|挖矿病毒|混币"),
    ("僵尸网络", r"botnet|僵尸网络|\bddos\b|分布式拒绝服务"),
    ("大模型安全", r"\bllm\b|large language|大模型|\bgpt\b|gpt-\d|chatgpt|claude|gemini|prompt injection|提示注入|越狱|jailbreak|ai agent|智能体"),
    ("AI攻防", r"adversarial|对抗样本|对抗攻击|deepfake|深度伪造|model poisoning|数据投毒|机器学习|machine learning|model extraction|membership inference|成员推理"),
    ("云安全", r"\bcloud\b|\baws\b|azure|\bgcp\b|kubernetes|\bk8s\b|docker|容器安全|云安全|云服务|serverless|s3 bucket|存储桶|云主机"),
    ("移动安全", r"\bandroid\b|\bios\b|iphone|安卓|移动恶意|mobile malware|恶意 app|手机病毒|短信拦截"),
    ("物联网安全", r"\biot\b|物联网|\brouter\b|路由器|摄像头|智能设备|车联网|车载"),
    ("工控安全", r"\bics\b|scada|工控|\bplc\b|operational technology|工业控制"),
    ("Web安全", r"\bxss\b|跨站|sql 注入|sql injection|\bssrf\b|\bcsrf\b|webshell|网页后门|wordpress|插件漏洞|web 应用|\bwaf\b"),
    ("密码学", r"post ?quantum|后量子|密码学|cryptanalysis|密码分析|加密算法|椭圆曲线|zero ?knowledge|零知识|哈希碰撞|量子计算|同态加密"),
    ("身份认证", r"\bmfa\b|\b2fa\b|多因素|身份认证|identity|\boauth\b|\bsso\b|passkey|凭据|credential|会话劫持|身份盗窃"),
    ("监管合规", r"\bcisa\b|\bfbi\b|执法|起诉|制裁|sanction|indict|监管|合规|compliance|\bnis2\b|\bgdpr\b|个人信息保护|网络安全审查|数据安全法"),
    ("安全运营", r"应急响应|事件响应|incident response|取证|forensic|溯源|归因|威胁狩猎|threat hunting|威胁情报|态势感知|安全监控|\bedr\b|\bxdr\b|\bsiem\b"),
    ("学术研究", r"we propose|we present|arxiv|论文|benchmark|dataset"),
]

# ---------- 本机 ollama 翻译 ----------
OLLAMA_CHAT = "http://127.0.0.1:11434/api/chat"
TRANSLATE_MODEL = "qwen2.5:7b"
TRANSLATE_SYSTEM = (
    "你是网络安全资讯的专业翻译。将用户给出的英文标题译为简洁专业的简体中文。"
    "规则：恶意软件家族名、黑客组织名(APT)、产品名、公司名、CVE/GHSA 编号一律保留英文原文不翻译；"
    "专业术语用业界通用中文译法；只输出译文本身，不要任何解释或引号。"
)


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


# ---------- 富化：内容标签 + 英文标题翻译 ----------

def is_english(text):
    """标题里没有任何 CJK 字符即视为英文（需要翻译）。"""
    return not re.search(r"[\u4e00-\u9fff]", text or "")


def build_tags(item):
    """标题 + 摘要联合匹配关键词规则，按优先级取前 TAGS_MAX 个标签。
    arXiv 一类学术源强制补「学术研究」，论文类条目不靠标题碰运气。"""
    text = (item.get("title", "") + "\n" + item.get("digest", "")).lower()
    tags = []
    for tag, pat in TAG_RULES:
        if len(tags) >= TAGS_MAX:
            break
        if re.search(pat, text):
            tags.append(tag)
    src = (item.get("source") or "").lower()
    if "arxiv" in src and len(tags) < TAGS_MAX and "学术研究" not in tags:
        tags.append("学术研究")
    return tags


def ollama_online():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as r:
            json.load(r)
        return True
    except Exception:
        return False


def translate_title(title):
    """ollama 翻译单个英文标题；失败重试一次，仍失败返回 None（下次同步补翻）。"""
    payload = {
        "model": TRANSLATE_MODEL,
        "messages": [
            {"role": "system", "content": TRANSLATE_SYSTEM},
            {"role": "user", "content": title},
        ],
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 150},
    }
    req = urllib.request.Request(
        OLLAMA_CHAT, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                content = json.load(r)["message"]["content"]
            zh = re.sub(r"\s+", " ", content).strip().strip('"“”\'「」')
            zh = re.sub(r"^(译文|翻译)[:：]\s*", "", zh)
            # 质量护栏：译文反而没有中文 = 模型没干正事，视为失败
            if zh and re.search(r"[\u4e00-\u9fff]", zh):
                return zh[:120]
            return None
        except Exception:
            continue
    return None


def enrich(items, verbose=False):
    """对全量归档做富化：标签每次全量重算（规则可迭代），翻译只补缺失的。"""
    tagged = sum(1 for it in items if build_tags(it))
    for it in items:
        it["tags"] = build_tags(it)
    print(f"  · 内容标签: {tagged}/{len(items)} 条命中（{len(TAG_RULES)} 组规则，每条最多 {TAGS_MAX} 个）")

    pending = [it for it in items if is_english(it.get("title")) and not it.get("title_zh")]
    if not pending:
        print(f"  · 英文标题翻译: 无待翻条目（已译 {sum(1 for i in items if i.get('title_zh'))} 条）")
        return
    if not ollama_online():
        print(f"  ! 本机 ollama 不可达，{len(pending)} 条英文标题本次跳过，下次同步自动补翻")
        return
    print(f"  · 英文标题翻译: {len(pending)} 条待翻（模型 {TRANSLATE_MODEL}）…")
    ok = fail = 0
    for i, it in enumerate(pending, 1):
        zh = translate_title(it["title"])
        if zh:
            it["title_zh"] = zh
            ok += 1
        else:
            fail += 1
        if verbose and i % 20 == 0:
            print(f"      进度 {i}/{len(pending)}（成功 {ok}，失败 {fail}）")
    print(f"  · 翻译完成: 成功 {ok}，失败 {fail}")


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
    enrich(all_items(archive), verbose=backfill)
    write_archive(archive)

    # feed：全量按时间倒序取头部（首页预览 / 资讯页首屏快照）
    flat = sorted(all_items(archive), key=sort_key, reverse=True)
    feed = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total": total,
            "items": flat[:FEED_SIZE]}
    (DATA_REPO / "feed.json").write_text(
        json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")

    # index：月度索引 + facets（官网筛选器全量选项与计数）
    facets = {"categories": {}, "sources": {}, "priorities": {}, "tags": {}}
    for i in flat:
        facets["categories"][i["category"]] = facets["categories"].get(i["category"], 0) + 1
        facets["sources"][i["source"]] = facets["sources"].get(i["source"], 0) + 1
        facets["priorities"][i["priority"]] = facets["priorities"].get(i["priority"], 0) + 1
        for t in i.get("tags", []):
            facets["tags"][t] = facets["tags"].get(t, 0) + 1
    facets["sources"] = dict(sorted(facets["sources"].items(), key=lambda kv: -kv[1]))
    facets["tags"] = dict(sorted(facets["tags"].items(), key=lambda kv: -kv[1]))
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
