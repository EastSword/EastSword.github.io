#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地文章编辑器：浏览器改主稿 + 实时预览（与线上同引擎）+ 一键保存/发布

用法:
  python3 scripts/edit_article.py             # 打开 http://127.0.0.1:8917
  python3 scripts/edit_article.py --port 8918
  python3 scripts/edit_article.py --no-open   # 不自动开浏览器

仅绑定 127.0.0.1，不对外网开放。保存 = 写回主稿 .md 与登记表；
发布 = 保存后调用 publish_article.py（可仅生成不推送）。
预览依赖本地 ruby + kramdown（gem install kramdown kramdown-parser-gfm）。
"""

import argparse
import json
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

SCRIPTS = Path(__file__).resolve().parent
SITE = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
import publish_article as pub

UI_FILE = SCRIPTS / "editor_ui.html"
RUBY_RENDER = SCRIPTS / "_preview_render.rb"
IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
CONTENT_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
}


def find_cfg(slug):
    for c in pub.load_registry():
        if c["slug"] == slug:
            return c
    return None


def render_preview(content: str, cfg: dict):
    text = pub.strip_leading_h1(content)
    text, toc = pub.inject_ids_and_toc(text)
    text = pub.autolink_urls(text)
    img_dir = cfg.get("img_dir", "文章配图")
    slug = cfg["slug"]
    text = re.sub(
        r"\]\((?:\./)?" + re.escape(img_dir) + r"/([^)\s]+)\)",
        lambda m: f"](/preview-img/{slug}/{m.group(1)})",
        text,
    )
    try:
        r = subprocess.run(["ruby", str(RUBY_RENDER)], input=text,
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return r.stdout, None, toc
        return None, r.stderr.strip()[:500], toc
    except FileNotFoundError:
        return None, "本地未安装 ruby，预览不可用（brew install ruby 后 gem install kramdown kramdown-parser-gfm）", toc
    except subprocess.TimeoutExpired:
        return None, "渲染超时", toc


def persist(slug, content, meta):
    cfg = find_cfg(slug)
    if not cfg:
        return None, "文章不存在"
    if not content.strip():
        return None, "内容为空，拒绝保存"
    cfg["source"].parent.mkdir(parents=True, exist_ok=True)
    cfg["source"].write_text(content, encoding="utf-8")
    if meta:
        arts = pub.load_registry()
        for a in arts:
            if a["slug"] == slug:
                for k in ("title", "subtitle", "abstract", "category", "keyword", "topic"):
                    if meta.get(k) is not None:
                        a[k] = str(meta[k]).strip()
                if isinstance(meta.get("tags"), list):
                    a["tags"] = [str(t).strip() for t in meta["tags"] if str(t).strip()]
        pub.save_registry(arts)
    return True, None


class Handler(BaseHTTPRequestHandler):
    server_version = "ArticleEditor/1.0"

    def log_message(self, fmt, *args):
        pass

    # ---------- 响应工具 ----------
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        return json.loads(raw.decode("utf-8")) if raw else {}

    # ---------- GET ----------
    def do_GET(self):
        try:
            path = unquote(urlparse(self.path).path)
            if path == "/":
                return self._bytes(UI_FILE.read_bytes(), "text/html; charset=utf-8")
            if path == "/api/articles":
                return self._json(self.articles_list())
            m = re.fullmatch(r"/api/article/([a-z0-9-]+)", path)
            if m:
                return self._json(self.article_detail(m.group(1)))
            m = re.fullmatch(r"/api/images/([a-z0-9-]+)", path)
            if m:
                return self._json(self.images_list(m.group(1)))
            m = re.fullmatch(r"/preview-img/([a-z0-9-]+)/(.+)", path)
            if m:
                return self.serve_img(m.group(1), Path(m.group(2)))
            if path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            self._json({"error": "not found"}, 404)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    # ---------- POST ----------
    def do_POST(self):
        try:
            path = unquote(urlparse(self.path).path)
            m = re.fullmatch(r"/api/article/([a-z0-9-]+)/(save|preview|publish)", path)
            if m:
                slug, action = m.group(1), m.group(2)
                if action == "preview":
                    cfg = find_cfg(slug)
                    if not cfg:
                        return self._json({"error": "文章不存在"}, 404)
                    html, err, toc = render_preview(self._body().get("content", ""), cfg)
                    return self._json({
                        "html": html, "error": err,
                        "toc": [{"title": c["title"]} for c in toc],
                    })
                data = self._body()
                ok, err = persist(slug, data.get("content", ""), data.get("meta") or {})
                if not ok:
                    return self._json({"error": err}, 400)
                if action == "save":
                    return self._json({"ok": True})
                cmd = [sys.executable, str(SCRIPTS / "publish_article.py")]
                if data.get("no_push"):
                    cmd.append("--no-push")
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   cwd=str(SITE), timeout=600)
                log = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
                return self._json({"ok": r.returncode == 0, "log": log[-6000:]})
            if path == "/api/articles/new":
                return self._json(self.create_article(self._body()))
            self._json({"error": "not found"}, 404)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    # ---------- 业务 ----------
    def articles_list(self):
        out = []
        for c in pub.load_registry():
            out.append({
                "slug": c["slug"],
                "title": c.get("title", c["slug"]),
                "category": c.get("category", ""),
                "published": (SITE / "_articles" / f"{c['slug']}.md").exists(),
                "source_exists": Path(c["source"]).exists(),
            })
        return {"articles": out}

    def article_detail(self, slug):
        cfg = find_cfg(slug)
        if not cfg:
            return {"error": "文章不存在"}
        src = Path(cfg["source"])
        content = src.read_text(encoding="utf-8") if src.exists() else ""
        meta = {k: cfg.get(k, "") for k in ("title", "subtitle", "abstract", "category", "keyword", "topic")}
        meta["tags"] = cfg.get("tags", [])
        return {"meta": meta, "content": content, "source": str(src)}

    def images_list(self, slug):
        cfg = find_cfg(slug)
        if not cfg:
            return {"error": "文章不存在"}
        d = Path(cfg["source"]).parent / cfg.get("img_dir", "文章配图")
        imgs = []
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.suffix.lower() in IMG_EXTS:
                    imgs.append({"name": f.name, "url": f"/preview-img/{slug}/{quote(f.name)}"})
        return {"images": imgs, "img_dir": cfg.get("img_dir", "文章配图")}

    def serve_img(self, slug, name):
        cfg = find_cfg(slug)
        if not cfg:
            return self._json({"error": "文章不存在"}, 404)
        f = Path(cfg["source"]).parent / cfg.get("img_dir", "文章配图") / name
        if not f.is_file():
            return self._json({"error": "图片不存在"}, 404)
        self._bytes(f.read_bytes(), CONTENT_TYPES.get(f.suffix.lower(), "application/octet-stream"))

    def create_article(self, d):
        slug = (d.get("slug") or "").strip()
        title = (d.get("title") or "").strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,60}", slug):
            return {"error": "slug 只允许小写字母/数字/连字符"}
        if not title:
            return {"error": "标题不能为空"}
        arts = pub.load_registry()
        if any(a["slug"] == slug for a in arts):
            return {"error": f"slug 已存在: {slug}"}
        source_name = (d.get("source") or f"../{title}.md").strip()
        src = (SITE / source_name).resolve()
        if not src.exists():
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_text(f"# {title}\n\n", encoding="utf-8")
        entry = {
            "slug": slug,
            "source": str(src),
            "title": title,
            "subtitle": (d.get("subtitle") or "").strip(),
            "topic": (d.get("topic") or "").strip(),
            "category": (d.get("category") or "").strip(),
            "tags": [t.strip() for t in re.split(r"[,，\s]+", d.get("tags") or "") if t.strip()],
            "keyword": (d.get("keyword") or "").strip(),
            "img_dir": (d.get("img_dir") or "文章配图").strip(),
            "abstract": (d.get("abstract") or "").strip(),
        }
        arts.append(entry)
        pub.save_registry(arts)
        return {"ok": True, "slug": slug}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8917)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"[编辑器] {url}  （Ctrl+C 退出）")
    if not args.no_open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[退出]")


if __name__ == "__main__":
    main()
