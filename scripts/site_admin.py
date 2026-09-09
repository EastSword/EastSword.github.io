"""Local content drafts, isolated Jekyll previews and reviewed Git releases."""

import datetime
import hashlib
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

SITE = Path(__file__).resolve().parent.parent
STATE = Path.home() / '.local/share/eastsword-admin' / hashlib.sha256(str(SITE).encode()).hexdigest()[:12]
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.RLock()
JOBS = {}
PREVIEW_URL = None
SINGLE = {'home': '_data/editorial.yml', 'global': '_data/site_ui.yml',
          'tools': '_data/tools.yml', 'about': '_data/about.yml'}
PAGES = ['topics', 'articles', 'resources', 'news', 'tools', 'wall', 'about']


def digest(value):
    return hashlib.sha256(value).hexdigest()


def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.admin-tmp')
    temp.write_text(text, encoding='utf-8')
    os.replace(temp, path)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n'


def frontmatter(text):
    if text.startswith('---\n'):
        parts = text.split('\n---', 1)
        if len(parts) == 2:
            return yaml.safe_load(parts[0][4:]) or {}, parts[1].lstrip('\n')
    return {}, text


def serialize(meta, body=None):
    text = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=120)
    return text if body is None else '---\n' + text + '---\n\n' + body.rstrip() + '\n'


def registry(root=None):
    root = root or SITE
    return json.loads((root / 'scripts/articles.json').read_text())['articles']


def records():
    result = []
    labels = {'home': '首页编排', 'global': '导航与页脚', 'tools': '兵器谱', 'about': '关于我们'}
    for key, path in SINGLE.items():
        result.append({'id': key, 'group': key, 'title': labels[key], 'path': path, 'url': '/' if key in ('home', 'global') else '/' + key + '/'})
    registered = {a['slug']: a for a in registry()}
    for group in ('articles', 'topics', 'resources'):
        names = {p.stem for p in (SITE / ('_' + group)).glob('*.md')}
        if group == 'articles':
            names.update(registered)
        for slug in sorted(names):
            path = '_' + group + '/' + slug + '.md'
            file = SITE / path
            meta = frontmatter(file.read_text())[0] if file.exists() else {}
            cfg = registered.get(slug) if group == 'articles' else None
            result.append({'id': group + '/' + slug, 'group': group, 'title': (cfg or meta).get('title', slug),
                           'path': path, 'url': '/resources/' if group == 'resources' else '/' + group + '/' + slug + '/',
                           'registered': bool(cfg)})
    for slug in PAGES:
        result.append({'id': 'pages/' + slug, 'group': 'pages', 'title': slug, 'path': slug + '.md', 'url': '/' + slug + '/'})
    known = {r['id'] for r in result}
    for file in (STATE / 'drafts').glob('*.json'):
        draft = json.loads(file.read_text())
        if draft['id'] not in known:
            result.append(draft['record'])
    return result


def record(key):
    for item in records():
        if item['id'] == key:
            return item
    raise ValueError('内容不存在')


def draft_path(key):
    return STATE / 'drafts' / (digest(key.encode()) + '.json')


def source(item):
    if item.get('registered'):
        cfg = next(a for a in registry() if a['slug'] == item['id'].split('/')[1])
        path = Path(cfg['source'])
        path = path if path.is_absolute() else SITE / path
        return path.resolve(), cfg
    return SITE / item['path'], None


def base_document(item):
    path, cfg = source(item)
    text = path.read_text(encoding='utf-8') if path.exists() else ''
    if cfg:
        meta = {k: v for k, v in cfg.items() if k not in ('slug', 'source', 'img_dir')}
        body = text
        version = digest((text + json_text(cfg)).encode())
    else:
        meta, body = (yaml.safe_load(text) or {}, None) if item['path'].endswith('.yml') else frontmatter(text)
        version = digest(text.encode())
    # JSON normalizes YAML dates for form editing.
    return json.loads(json_text({'id': item['id'], 'record': item, 'meta': meta, 'body': body, 'version': version}))


def document(key):
    item = record(key)
    path = draft_path(key)
    result = json.loads(path.read_text()) if path.exists() else base_document(item)
    result['draft'] = path.exists()
    result['conflict'] = result['version'] != base_document(item)['version']
    result['revision'] = digest(path.read_bytes()) if path.exists() else ''
    return result


def validate(doc):
    if not isinstance(doc.get('meta'), dict):
        raise ValueError('元信息需要是字段对象')
    if doc.get('body') is not None and not isinstance(doc['body'], str):
        raise ValueError('正文格式错误')
    if doc['id'].startswith(('topics/', 'articles/', 'resources/')) and not doc['meta'].get('title', '').strip():
        raise ValueError('标题不能为空')
    def walk(value):
        if isinstance(value, dict):
            for key, val in value.items():
                if key in ('url', 'external_url', 'image', 'cover', 'logo', 'art') and val:
                    if not isinstance(val, str) or not (val.startswith(('https://', 'http://', '/')) and not val.startswith('//')):
                        raise ValueError('链接和图片需要使用站内绝对路径或 HTTP(S) 地址')
                walk(val)
        elif isinstance(value, list):
            for val in value:
                walk(val)
    walk(doc['meta'])
    if doc['id'] == 'global':
        nav = doc['meta'].get('navigation', [])
        keys = [n.get('key') for n in nav]
        if sorted(keys) != sorted(PAGES):
            raise ValueError('导航必须保留七个栏目的唯一标识；可调整顺序和显示状态')
    if doc['id'] == 'home':
        for key, low, high in [('feather', 0, 100), ('height', 280, 500)]:
            value = doc['meta'].get('hero', {}).get(key, 35 if key == 'feather' else 350)
            if not isinstance(value, (int, float)) or not low <= value <= high:
                raise ValueError('首页图片数值超出范围')


def save_draft(data):
    key = data['id']
    with LOCK:
        current = document(key)
        if data.get('revision', '') != current['revision'] or data.get('version') != current['version']:
            raise ValueError('此内容已在其他窗口修改，请重新加载后再保存')
        doc = {k: current[k] for k in ('id', 'record', 'version')}
        doc.update(meta=data['meta'], body=data.get('body'), saved_at=datetime.datetime.now().isoformat(timespec='seconds'))
        validate(doc)
        atomic(draft_path(key), json_text(doc))
        return document(key)


def create(data):
    group, slug = data.get('group'), data.get('slug', '')
    if group not in ('articles', 'topics', 'resources') or not re.fullmatch('[a-z0-9][a-z0-9-]{0,60}', slug):
        raise ValueError('请选择内容类型，并填写小写字母、数字或连字符组成的路径')
    key = group + '/' + slug
    if any(r['id'] == key for r in records()):
        raise ValueError('这个路径已存在')
    title = data.get('title', '').strip()
    if not title:
        raise ValueError('请填写标题')
    day = datetime.date.today().isoformat()
    meta = {'title': title, 'date': day}
    if group == 'topics':
        meta.update(layout='topic', published=True, status='研讨中', subtitle='', updated=day, categories=[], tags=[], links=[], changelog=[])
        for layer in ('dao', 'fa', 'shu', 'qi'):
            meta[layer + '_summary'] = ''
            meta[layer] = []
    elif group == 'resources':
        meta.update(source='', author='', type='官方规范', external_url='', topics=[], reason='')
    else:
        meta.update(layout='article', author='千里', subtitle='', abstract='', category='', tags=[], cover='')
    item = {'id': key, 'group': group, 'title': title, 'path': '_' + group + '/' + slug + '.md',
            'url': '/resources/' if group == 'resources' else '/' + key + '/', 'registered': False}
    doc = {'id': key, 'record': item, 'meta': meta, 'body': '', 'version': digest(b''), 'saved_at': day}
    atomic(draft_path(key), json_text(doc))
    return document(key)


def run(args, cwd=None, timeout=90, env=None):
    cwd = cwd or SITE
    proc = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    if proc.returncode:
        raise ValueError((proc.stderr or proc.stdout)[-5000:])
    return proc.stdout


def jekyll(root, output):
    binary = shutil.which('jekyll')
    if not binary:
        candidates = sorted((Path.home() / '.gem/ruby').glob('*/bin/jekyll'))
        binary = str(candidates[-1]) if candidates else 'jekyll'
    return run([binary, 'build', '--source', str(root), '--destination', str(output)], root, 180)


def apply_document(doc, root, real=False):
    item = doc['record']
    if item.get('registered'):
        entries = registry(root)
        cfg = next(a for a in entries if a['slug'] == item['id'].split('/')[1])
        original, _ = source(item)
        cfg.update(doc['meta'])
        if real:
            atomic(original, doc['body'])
        else:
            temp_source = root / '.admin-sources' / cfg['slug'] / original.name
            atomic(temp_source, doc['body'])
            cfg['source'] = str(temp_source)
            image_dir = Path(cfg.get('img_dir', '文章配图'))
            if not image_dir.is_absolute() and '..' not in image_dir.parts:
                images = original.parent / image_dir
                if images.exists():
                    shutil.copytree(images, temp_source.parent / image_dir, dirs_exist_ok=True)
        atomic(root / 'scripts/articles.json', json_text({'articles': entries}))
        # Generation is explicit and restricted to the selected article.
        run([os.sys.executable, str(root / 'scripts/publish_article.py'), '--slug', cfg['slug'], '--no-push'], root)
    else:
        atomic(root / item['path'], serialize(doc['meta'], doc['body']))


def preview(keys, live=None):
    with LOCK:
        STATE.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix='preview-', dir=STATE))
        try:
            shutil.copytree(SITE, root, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git', '_site', '__pycache__', '.DS_Store'))
            for key in keys:
                apply_document(document(key), root)
            if live is not None:
                item = record(live['id'])
                doc = base_document(item)
                doc.update(meta=live['meta'], body=live.get('body'))
                validate(doc)
                apply_document(doc, root)
            output = root / '_site'
            log = jekyll(root, output)
            target = STATE / 'preview'
            backup = STATE / 'previous-preview'
            if backup.exists():
                shutil.rmtree(backup)
            if target.exists():
                target.rename(backup)
            output.rename(target)
            return {'ok': True, 'url': start_preview(), 'log': log}
        finally:
            shutil.rmtree(root, ignore_errors=True)


def start_preview():
    global PREVIEW_URL
    if PREVIEW_URL is None:
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(STATE / 'preview')))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        PREVIEW_URL = 'http://127.0.0.1:' + str(server.server_port)
    return PREVIEW_URL


def materialize(keys):
    with LOCK:
        docs = [document(key) for key in keys]
        for doc in docs:
            if doc['conflict']:
                raise ValueError('磁盘文件已更新，草稿存在冲突：' + doc['record']['title'])
            validate(doc)
        preview(keys)
        def site_files():
            return {p for p in SITE.rglob('*') if p.is_file() and not any(
                part in ('.git', '_site', '__pycache__') for part in p.relative_to(SITE).parts)}
        originals = {source(doc['record'])[0] for doc in docs}
        before_paths = site_files() | originals
        before = {p: p.read_bytes() if p.exists() else None for p in before_paths}
        try:
            for doc in docs:
                original, _ = source(doc['record'])
                stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                if original.exists():
                    atomic(STATE / 'history' / (stamp + '-' + digest(doc['id'].encode())[:8] + '.json'),
                           json_text({'id': doc['id'], 'path': str(original), 'content': original.read_text(), 'meta': base_document(doc['record'])['meta']}))
                apply_document(doc, SITE, real=True)
        except Exception:
            for path in site_files() | originals | before_paths:
                old = before.get(path)
                if old is None:
                    path.unlink(missing_ok=True)
                elif not path.exists() or path.read_bytes() != old:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(old)
            raise
        for doc in docs:
            draft_path(doc['id']).unlink(missing_ok=True)
        return {'ok': True, 'changes': changes()}


def changes():
    # NUL-separated paths preserve spaces, Unicode and rename destinations.
    out = subprocess.check_output(['git', 'status', '--porcelain=v1', '-z', '--untracked-files=all'], cwd=SITE)
    parts = out.decode().split('\0')
    rows = []
    i = 0
    while i < len(parts) and parts[i]:
        status, path = parts[i][:2], parts[i][3:]
        i += 1
        if 'R' in status or 'C' in status:
            old = parts[i]
            i += 1
            rows.append({'path': old, 'status': 'D', 'hash': ''})
        file = SITE / path
        rows.append({'path': path, 'status': status.strip(), 'hash': digest(file.read_bytes()) if file.is_file() else ''})
    return rows


def reviewed_paths(data):
    selected = data.get('files', [])
    current = {r['path']: r for r in changes()}
    if not selected:
        raise ValueError('请先选择待发布文件')
    for item in selected:
        if item['path'] not in current or item != current[item['path']]:
            raise ValueError('文件已变化，请刷新待发布列表并重新检查')
        path = (SITE / item['path']).resolve()
        if not path.is_relative_to(SITE) or '.git' in path.relative_to(SITE).parts:
            raise ValueError('文件路径不允许发布')
    return [item['path'] for item in selected]


def release_check(data):
    with LOCK:
        STATE.mkdir(parents=True, exist_ok=True)
        paths = reviewed_paths(data)
        head = run(['git', 'rev-parse', 'HEAD']).strip()
        with tempfile.TemporaryDirectory(prefix='release-', dir=STATE) as work:
            root = Path(work)
            index = root / 'index'
            env = dict(os.environ, GIT_INDEX_FILE=str(index))
            run(['git', 'read-tree', 'HEAD'], env=env)
            run(['git', 'add', '-A', '--'] + paths, env=env)
            tree = run(['git', 'write-tree'], env=env).strip()
            checkout = root / 'site'
            checkout.mkdir()
            run(['git', 'checkout-index', '--all', '--prefix=' + str(checkout) + '/'], env=env)
            log = jekyll(checkout, root / 'output')
        proof = digest(json_text({'files': data['files'], 'head': head, 'tree': tree}).encode())
        atomic(STATE / 'release.json', json_text({'proof': proof, 'files': data['files'], 'head': head}))
        return {'ok': True, 'proof': proof, 'log': log}


def publish(data):
    with LOCK:
        paths = reviewed_paths(data)
        proof = json.loads((STATE / 'release.json').read_text())
        if proof['proof'] != data.get('proof') or proof['files'] != data['files'] or proof['head'] != run(['git', 'rev-parse', 'HEAD']).strip():
            raise ValueError('发布检查已过期，请重新检查')
        if run(['git', 'diff', '--cached', '--name-only']).strip():
            raise ValueError('Git 暂存区已有其他修改，请先处理后再从后台发布')
        message = str(data.get('message', '')).strip() or '更新官网内容'
        run(['git', 'add', '-A', '--'] + paths)
        run(['git', 'commit', '-m', message])
        commit = run(['git', 'rev-parse', 'HEAD']).strip()
        try:
            log = run(['git', 'push', 'origin', 'HEAD'], timeout=120)
        except Exception as error:
            return {'ok': False, 'commit': commit, 'error': '已提交到本地，推送失败。可在发布中心重试推送。' + str(error)}
        return {'ok': True, 'commit': commit, 'log': log, 'actions_url': 'https://github.com/EastSword/EastSword.github.io/actions'}


def task(fn, *args):
    key = secrets.token_hex(8)
    JOBS[key] = {'status': 'running'}
    def work():
        try:
            JOBS[key] = {'status': 'complete', 'result': fn(*args)}
        except Exception as error:
            JOBS[key] = {'status': 'failed', 'error': str(error)}
    threading.Thread(target=work, daemon=True).start()
    return {'job': key}


def media():
    files = []
    for file in sorted((SITE / 'assets').rglob('*')):
        if file.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.gif'):
            relative = '/' + str(file.relative_to(SITE))
            files.append({'url': relative, 'name': file.name, 'size': file.stat().st_size})
    return files


def handle(handler, path, method):
    if method == 'GET' and path in ('/', '/admin.css', '/admin.js', '/admin_format.js'):
        name = {'/': 'admin_ui.html', '/admin.css': 'admin.css', '/admin.js': 'admin.js', '/admin_format.js': 'admin_format.js'}[path]
        return handler._bytes((SITE / 'scripts' / name).read_bytes(), mimetypes.guess_type(name)[0] or 'text/plain') or True
    if path.startswith('/assets/') and method == 'GET':
        file = (SITE / path.lstrip('/')).resolve()
        if not file.is_relative_to(SITE / 'assets') or not file.is_file():
            handler._json({'error': '图片不存在'}, 404)
        else:
            handler._bytes(file.read_bytes(), mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
        return True
    if not path.startswith('/api/admin/'):
        return False
    try:
        if method == 'POST':
            if handler.headers.get('X-Admin-Token') != TOKEN:
                raise ValueError('操作凭证失效，请刷新后台')
            if int(handler.headers.get('Content-Length', '0')) > 35 * 1024 * 1024:
                raise ValueError('请求超过大小限制')
        if method == 'GET':
            if path == '/api/admin/bootstrap':
                result = {'token': TOKEN, 'records': records(), 'drafts': [json.loads(p.read_text())['id'] for p in (STATE / 'drafts').glob('*.json')], 'preview_url': start_preview()}
            elif path.startswith('/api/admin/document/'):
                result = document(path.removeprefix('/api/admin/document/'))
            elif path == '/api/admin/changes':
                result = {'files': changes(), 'ahead': run(['git', 'log', '@{upstream}..HEAD', '--oneline']).strip(), 'branch': run(['git', 'branch', '--show-current']).strip()}
            elif path == '/api/admin/media':
                result = media()
            elif path.startswith('/api/admin/job/'):
                result = JOBS.get(path.split('/')[-1], {'status': 'failed', 'error': '任务不存在，请重试'})
            elif path == '/api/admin/deployments':
                result = json.loads(run(['gh', 'run', 'list', '--limit', '5', '--json', 'status,conclusion,displayTitle,url,headSha']))
            else:
                raise ValueError('接口不存在')
        elif path == '/api/admin/upload':
            from PIL import Image
            import io
            raw = handler.rfile.read(int(handler.headers.get('Content-Length', '0')))
            img = Image.open(io.BytesIO(raw))
            img.verify()
            img = Image.open(io.BytesIO(raw)).convert('RGBA')
            if img.width * img.height > 40000000:
                raise ValueError('图片尺寸过大')
            name = datetime.datetime.now().strftime('%Y%m%d-') + secrets.token_hex(5) + '.webp'
            dest = SITE / 'assets/uploads' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            img.save(dest, 'WEBP', quality=92)
            result = {'url': '/assets/uploads/' + name}
        else:
            data = handler._body()
            if path == '/api/admin/save':
                result = save_draft(data)
            elif path == '/api/admin/new':
                result = create(data)
            elif path == '/api/admin/discard':
                record(data['id'])
                draft_path(data['id']).unlink(missing_ok=True)
                result = {'ok': True}
            elif path == '/api/admin/preview':
                result = task(preview, data.get('ids', []))
            elif path == '/api/admin/live-preview':
                result = task(preview, [], data)
            elif path == '/api/admin/apply':
                result = task(materialize, data.get('ids', []))
            elif path == '/api/admin/check':
                result = task(release_check, data)
            elif path == '/api/admin/publish':
                result = task(publish, data)
            elif path == '/api/admin/retry-push':
                result = task(lambda: {'ok': True, 'log': run(['git', 'push', 'origin', 'HEAD'], timeout=120)})
            elif path == '/api/admin/diff':
                paths = reviewed_paths({'files': [data['file']]})
                file = SITE / paths[0]
                if file.suffix.lower() in ('.png', '.jpg', '.webp', '.gif', '.ico', '.jpeg'):
                    result = {'diff': '图片文件：' + paths[0]}
                elif data['file']['status'] == '??':
                    result = {'diff': file.read_text()[:60000]}
                else:
                    result = {'diff': run(['git', 'diff', 'HEAD', '--'] + paths)[:60000]}
            else:
                raise ValueError('接口不存在')
        handler._json(result)
    except Exception as error:
        handler._json({'error': str(error)}, 400)
    return True
