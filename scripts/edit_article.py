#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地文章编辑器：浏览器改主稿 + 实时预览（与线上同引擎）+ 一键保存/发布

用法:
  python3 scripts/edit_article.py              # 后台启动并打开 http://127.0.0.1:8917（默认）
  python3 scripts/edit_article.py --port 8918  # 换端口
  python3 scripts/edit_article.py --no-open    # 后台启动但不自动开浏览器
  python3 scripts/edit_article.py --stop       # 停止后台编辑器
  python3 scripts/edit_article.py --status     # 查看运行状态
  python3 scripts/edit_article.py --foreground # 前台运行（调试用，Ctrl+C 退出）

后台模式：服务进程独立会话运行，关闭终端不受影响；重复执行命令时检测到
已在运行则直接开浏览器。日志写在系统临时目录（不入仓库，publish 是 git add -A）。
仅绑定 127.0.0.1，不对外网开放。保存 = 写回主稿 .md 与登记表；
发布 = 保存后调用 publish_article.py（可仅生成不推送）。
预览依赖本地 ruby + kramdown（gem install kramdown kramdown-parser-gfm）。
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from urllib.request import urlopen
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


def safe_filename(name):
    """只留字母数字/中文/点横线，其余替换成 -：文件名里的空格和括号会破坏发布脚本的图片路径改写"""
    name = Path((name or "").replace("\\", "/")).name.strip()
    name = "".join(
        c if (c.isalnum() or c in "._-" or "\u4e00" <= c <= "\u9fff") else "-"
        for c in name
    )
    return name.lstrip(".")[:80]


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
                for k in ("title", "subtitle", "abstract", "category", "keyword", "topic", "author"):
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
            if path == "/api/ping":
                return self._json({"app": "article-editor", "pid": os.getpid()})
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
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, cwd=str(SITE), start_new_session=True)
                try:
                    out, err = proc.communicate(timeout=300)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    out, err = proc.communicate()
                    return self._json({
                        "ok": False,
                        "log": ("发布超时（300 秒），已强制终止（git push 可能被网络挂起）\n"
                                + (out or "") + "\n" + (err or "")).strip()[-6000:],
                    })
                log = ((out or "") + "\n" + (err or "")).strip()
                return self._json({"ok": proc.returncode == 0, "log": log[-6000:]})
            m = re.fullmatch(r"/api/article/([a-z0-9-]+)/image", path)
            if m:
                return self.upload_image(m.group(1))
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
        meta = {k: cfg.get(k, "") for k in ("title", "subtitle", "abstract", "category", "keyword", "topic", "author")}
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

    def upload_image(self, slug):
        cfg = find_cfg(slug)
        if not cfg:
            return self._json({"error": "文章不存在"}, 404)
        name = safe_filename(unquote(self.headers.get("X-Filename", "")))
        ext = Path(name).suffix.lower() if name else ""
        if not name or ext not in IMG_EXTS:
            return self._json({"error": "仅支持 " + "/".join(sorted(IMG_EXTS)) + " 格式"}, 400)
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return self._json({"error": "上传内容为空"}, 400)
        if n > 30 * 1024 * 1024:
            return self._json({"error": "图片超过 30MB，拒绝上传"}, 400)
        raw = self.rfile.read(n)
        img_dir = Path(cfg["source"]).parent / cfg.get("img_dir", "文章配图")
        img_dir.mkdir(parents=True, exist_ok=True)
        stem = name[: -len(ext)]
        dest = img_dir / name
        i = 2
        while dest.exists():
            dest = img_dir / f"{stem}-{i}{ext}"
            i += 1
        dest.write_bytes(raw)
        return self._json({
            "ok": True,
            "name": dest.name,
            "img_dir": cfg.get("img_dir", "文章配图"),
            "url": f"/preview-img/{slug}/{quote(dest.name)}",
        })

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


def ping(port, timeout=0.5):
    """探测端口上是否跑着本编辑器，是则返回其 pid，否则 None"""
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        if data.get("app") == "article-editor":
            return data.get("pid")
    except Exception:
        pass
    return None


def serve(port, open_browser):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"[编辑器] {url}  （Ctrl+C 退出）", flush=True)
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[退出]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8917)
    ap.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    ap.add_argument("--foreground", action="store_true", help="前台运行（调试用，Ctrl+C 退出）")
    ap.add_argument("--stop", action="store_true", help="停止后台运行的编辑器")
    ap.add_argument("--status", action="store_true", help="查看运行状态")
    args = ap.parse_args()

    url = f"http://127.0.0.1:{args.port}"
    pid = ping(args.port)

    if args.stop:
        if pid:
            os.kill(pid, signal.SIGTERM)
            print(f"[编辑器] 已停止（pid {pid}）")
        else:
            print(f"[编辑器] 未在运行（端口 {args.port}）")
        return

    if args.status:
        print(f"[编辑器] 运行中 pid={pid}  {url}" if pid else "[编辑器] 未运行")
        return

    if pid:
        print(f"[编辑器] 已在运行 pid={pid}  {url}")
        if not args.no_open:
            webbrowser.open(url)
        return

    if args.foreground:
        serve(args.port, not args.no_open)
        return

    log = Path(tempfile.gettempdir()) / f"article-editor-{args.port}.log"
    with open(log, "ab") as lf:
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()),
             "--foreground", "--no-open", "--port", str(args.port)],
            stdout=lf, stderr=lf, stdin=subprocess.DEVNULL,
            cwd=str(SITE), start_new_session=True,
        )
    for _ in range(60):
        new_pid = ping(args.port)
        if new_pid:
            print(f"[编辑器] 后台已启动 pid={new_pid}  {url}")
            print(f"  日志: {log}")
            print("  停止: python3 scripts/edit_article.py --stop")
            if not args.no_open:
                webbrowser.open(url)
            return
        if proc.poll() is not None:
            print(f"[编辑器] 启动失败，查看日志: {log}")
            sys.exit(1)
        time.sleep(0.1)
    print(f"[编辑器] 启动超时，查看日志: {log}")
    sys.exit(1)


if __name__ == "__main__":
    main()
