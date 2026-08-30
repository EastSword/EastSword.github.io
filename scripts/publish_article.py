#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本地主稿发布为官网文章（一键：主稿 → _articles/ → git push）

用法:
  python3 scripts/publish_article.py            # 同步全部已登记文章并推送
  python3 scripts/publish_article.py --no-push  # 只生成文件，不提交不推送
  python3 scripts/publish_article.py --slug llm-api-key-leak   # 只处理这一篇

流程:
  1. 读主稿（ARTICLES 里登记的 source 路径）
  2. 剥离文件首行 H1 标题
  3. 给 ## / ### 标题注入稳定锚点 id（ch01 / ch01-2 形式，跳过代码块内部）
  4. 由标题生成 front-matter 里的 toc（章 + 节两级）
  5. 重写图片路径 文章配图/xxx → /assets/images/<slug>/xxx，并拷贝图片
  6. 计算阅读时长；首次发布写 date，再发布只更新 updated（读取已有文章的 date 保持稳定）
  7. 写 _articles/<slug>.md；git 有变更则 add/commit/push

登记新文章: 往 ARTICLES 列表加一条字典即可。
"""

import argparse
import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
ARTICLES_DIR = SITE / "_articles"
IMG_ROOT = SITE / "assets" / "images"
MASTER_ROOT = SITE.parent  # 安全架构/

ARTICLES = [
    {
        "slug": "llm-api-key-leak",
        "source": MASTER_ROOT / "公网大模型的密钥泄露：攻击面、提取手法与防御.md",
        "title": "公网大模型的密钥泄露：攻击面、提取手法与防御",
        "subtitle": "口令不是关键，公网暴露才是。五家机构数据交叉验证 + FOFA 独立测量 + 422 台实例实测 + 四起国内暴露实证",
        "topic": "llm-api-key-security",
        "category": "AI安全",
        "tags": ["AI 安全", "云安全", "API Key", "检测工程"],
        "keyword": "APIKEY",
        "img_dir": "文章配图",
        "abstract": "LiteLLM 的 SQL 注入漏洞进 CISA KEV 后 36 小时内被在野利用，攻击者直奔存上游 Key 的三张表。这篇文章用 FOFA 测量、两个审计脚本和 47 条一手来源，把公网大模型系统的 Key 是怎么被拿的讲透：八条提取路径、四起国内暴露实证、三条产业链、九层防御。",
    },
]

FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})")
H2_RE = re.compile(r"^##\s+(?!#)(.*)$")
H3_RE = re.compile(r"^###\s+(?!#)(.*)$")
ATTR_RE = re.compile(r"\s*\{:[^}]*\}\s*$")


def strip_leading_h1(text: str) -> str:
    lines = text.split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].startswith("# "):
        lines = lines[i + 1:]
    return "\n".join(lines).lstrip("\n")


def inject_ids_and_toc(text: str):
    """给 h2/h3 注入锚点（ALD 写在标题下一行，kramdown 2.x 不认同行尾部语法）并生成 toc"""
    lines = text.split("\n")
    out = []
    toc = []
    ch = 0
    sub = 0
    in_fence = False
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence:
            if re.match(r"^\{:\s*#ch[\d-]+\}\s*$", line):
                continue
            m2 = H2_RE.match(line)
            m3 = H3_RE.match(line)
            if m2:
                ch += 1
                sub = 0
                title = ATTR_RE.sub("", m2.group(1)).strip()
                hid = f"ch{ch:02d}"
                out.append(f"## {title}")
                out.append(f"{{: #{hid}}}")
                toc.append({"id": hid, "title": title, "children": []})
                continue
            if m3:
                sub += 1
                title = ATTR_RE.sub("", m3.group(1)).strip()
                hid = f"ch{ch:02d}-{sub}"
                out.append(f"### {title}")
                out.append(f"{{: #{hid}}}")
                if toc:
                    toc[-1]["children"].append({"id": hid, "title": title})
                continue
        out.append(line)
    return "\n".join(out), toc


def autolink_urls(text: str) -> str:
    """把裸 URL 转成 markdown 链接（附录来源可直接点击）。跳过代码块，不动已有 [x](url) 链接"""
    url_re = re.compile(r"(?<![\(\[/\w])(https?://[^\s\)\]\<\u3000，。；、\"']+)")

    def repl(m):
        url = m.group(1)
        return f"[{url}]({url})"

    out = []
    in_fence = False
    for line in text.split("\n"):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        out.append(url_re.sub(repl, line) if not in_fence else line)
    return "\n".join(out)


def rewrite_images(text: str, img_dir: str, slug: str):
    """文章配图/xxx.png → /assets/images/<slug>/xxx.png，返回新文本和用到的图片名"""
    pattern = re.compile(r"\]\((?:\./)?" + re.escape(img_dir) + r"/([^)\s]+)\)")
    used = []

    def repl(m):
        used.append(m.group(1))
        return f"]( /assets/images/{slug}/{m.group(1)})".replace("( ", "(")

    return pattern.sub(repl, text), used


def copy_images(used, img_dir: Path, slug: str):
    dest_dir = IMG_ROOT / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in used:
        src = img_dir / name
        if not src.exists():
            print(f"  [警告] 图片不存在: {src}")
            continue
        dest = dest_dir / name
        if not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime:
            shutil.copy2(src, dest)
            copied.append(name)
    return copied


def reading_minutes(text: str) -> int:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    words = len(re.findall(r"[A-Za-z0-9_\-]+", text))
    return max(1, round((cjk + words * 0.6) / 500))


def yaml_str(v: str) -> str:
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_front_matter(cfg, toc, minutes, date, updated):
    fm = ["---", "layout: article", f"title: {yaml_str(cfg['title'])}"]
    if cfg.get("subtitle"):
        fm.append(f"subtitle: {yaml_str(cfg['subtitle'])}")
    if cfg.get("abstract"):
        fm.append(f"abstract: {yaml_str(cfg['abstract'])}")
    fm.append(f"date: {date}")
    fm.append(f"updated: {updated}")
    fm.append(f"reading_time: {minutes}")
    if cfg.get("topic"):
        fm.append(f"topic: {cfg['topic']}")
    fm.append(f"category: {yaml_str(cfg['category'])}")
    tags = ", ".join(yaml_str(t) for t in cfg.get("tags", []))
    fm.append(f"tags: [{tags}]")
    if cfg.get("keyword"):
        fm.append(f"keyword: {cfg['keyword']}")
    fm.append("toc:")
    for ch in toc:
        fm.append(f"  - id: {ch['id']}")
        fm.append(f"    title: {yaml_str(ch['title'])}")
        if ch["children"]:
            fm.append("    children:")
            for c in ch["children"]:
                fm.append(f"      - id: {c['id']}")
                fm.append(f"        title: {yaml_str(c['title'])}")
        else:
            fm.append("    children: []")
    fm.append("---")
    return "\n".join(fm)


def existing_date(slug: str):
    p = ARTICLES_DIR / f"{slug}.md"
    if not p.exists():
        return None
    m = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", p.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def git(*args, check=True):
    return subprocess.run(["git", "-C", str(SITE), *args],
                          capture_output=True, text=True, check=check)


def publish(cfg, push=True):
    slug = cfg["slug"]
    src = cfg["source"]
    if not src.exists():
        print(f"[跳过] 主稿不存在: {src}")
        return False
    print(f"[同步] {src.name} → _articles/{slug}.md")

    text = src.read_text(encoding="utf-8")
    text = strip_leading_h1(text)
    text, toc = inject_ids_and_toc(text)
    text = autolink_urls(text)
    text, used = rewrite_images(text, cfg["img_dir"], slug)
    copied = copy_images(used, src.parent / cfg["img_dir"], slug)

    minutes = reading_minutes(text)
    date = existing_date(slug) or datetime.date.today().isoformat()
    updated = datetime.date.today().isoformat()

    ARTICLES_DIR.mkdir(exist_ok=True)
    out = ARTICLES_DIR / f"{slug}.md"
    content = build_front_matter(cfg, toc, minutes, date, updated) + "\n\n" + text.rstrip() + "\n"

    changed = (not out.exists()) or (out.read_text(encoding="utf-8") != content)
    out.write_text(content, encoding="utf-8")

    n_ch = len(toc)
    print(f"  章节 {n_ch} 个，图片 {len(used)} 张（更新 {len(copied)} 张），阅读约 {minutes} 分钟")
    if not changed and not copied:
        print("  无变化")
    return changed or bool(copied)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-push", action="store_true", help="只生成文件，不 git 提交推送")
    ap.add_argument("--slug", help="只处理指定 slug 的文章")
    args = ap.parse_args()

    targets = [a for a in ARTICLES if not args.slug or a["slug"] == args.slug]
    if not targets:
        print(f"未找到 slug={args.slug} 的登记文章")
        sys.exit(1)

    any_change = False
    for cfg in targets:
        if publish(cfg, push=not args.no_push):
            any_change = True

    if args.no_push:
        print("\n[完成] 已生成文件（--no-push，未提交）")
        return

    status = git("status", "--porcelain").stdout.strip()
    if not any_change and not status:
        print("\n[完成] 无变更，无需推送")
        return

    git("add", "-A")
    git("commit", "-m", "发布/更新技术文章", check=False)
    try:
        r = git("push")
        print(r.stderr.strip() or r.stdout.strip())
        print("\n[上线] 已推送，GitHub Pages 约 1 分钟后生效")
    except subprocess.CalledProcessError as e:
        print("直连失败，改走本地代理 127.0.0.1:7890 重试…")
        r = subprocess.run(["git", "-C", str(SITE), "-c", "http.proxy=http://127.0.0.1:7890", "push"],
                           capture_output=True, text=True, check=True)
        print(r.stderr.strip() or r.stdout.strip())
        print("\n[上线] 已推送（经代理），GitHub Pages 约 1 分钟后生效")


if __name__ == "__main__":
    main()
