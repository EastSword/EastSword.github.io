#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb_distill.py — 工作站知识库 → 官网 周度知识提炼

每周日由 launchd（com.qianli.kb-distill）触发：
  1. 扫描 Neo4j 知识图谱（概念/域/实践），解析官网 _topics 与 _articles 的 frontmatter；
  2. 生成 assets/graph/graph-data.json（官网 /graph/ 页面的精选锚点图谱数据）；
  3. 生成候选清单（待挂课题文章 / 课题交叉点 / 课题概念缺口 / 新入库概念 / 实践关联），
     写入 8971 工作台 STATE 目录 distill/，供 admin「知识提炼」分组查看。

用法:
  python3 kb_distill.py                # 完整提炼（图谱数据 + 候选报告）
  python3 kb_distill.py --push-graph   # 提炼后自动 commit+push 图谱数据到 GitHub Pages
  python3 kb_distill.py --graph-only   # 只生成 graph-data.json，不写报告
  python3 kb_distill.py --dry-run      # 只打印，不写任何文件
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

SITE = Path(__file__).resolve().parent.parent
STATE = Path.home() / '.local/share/eastsword-admin' / hashlib.sha256(str(SITE).encode()).hexdigest()[:12]
DISTILL_DIR = STATE / 'distill'
GRAPH_OUT = SITE / 'assets' / 'graph' / 'graph-data.json'

NEO4J_URL = 'http://192.168.1.7:7475/db/neo4j/tx/commit'
NEO4J_AUTH = base64.b64encode(b'neo4j:kuzuv2pass').decode()
TIMEOUT = 30

CORE_PER_DOMAIN = 12      # 每个域取核心概念数
CORE_LINK_PER_TOPIC = 8   # 每个课题最多挂的核心概念连接（相关性排序后截断）
SUMMARY_LIMIT = 50        # 概念摘要公网截断长度（保守公开边界）
RECENT_DAYS = 7           # “新入库概念”回看窗口
OVERLAP_MIN = 3           # 课题交叉判定：共享概念数下限
KEEP_REPORTS = 12         # 报告保留期数

REL_TYPES = ('RELATES_TO', 'CAUSES', 'COUNTERS', 'IMPLEMENTS', 'USES', 'CONTRASTS_WITH', 'ANALOGOUS_TO')


# ---------------------------------------------------------------- 基础设施

def log(msg):
    stamp = dt.datetime.now().strftime('%H:%M:%S')
    print(f'[{stamp}] {msg}', flush=True)


def cypher(statements):
    """执行 Neo4j HTTP Cypher 事务，返回 results 列表。"""
    payload = json.dumps({'statements': statements}).encode()
    req = urllib.request.Request(NEO4J_URL, data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    req.add_header('Authorization', 'Basic ' + NEO4J_AUTH)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read())
    if data.get('errors'):
        raise RuntimeError('Cypher 错误: ' + json.dumps(data['errors'], ensure_ascii=False))
    return data['results']


def rows(result, *cols):
    """把 Neo4j result（或 results 列表首项）转成 dict 列表。"""
    if isinstance(result, list):
        result = result[0] if result else {}
    out = []
    for entry in result.get('data', []):
        row = dict(zip(result['columns'], entry['row']))
        out.append({c: row.get(c) for c in cols} if cols else row)
    return out


def frontmatter_of(path):
    """解析 markdown frontmatter（与 site_admin.py 相同约定）。"""
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---'):
        return {}, text
    end = text.find('\n---', 3)
    if end == -1:
        return {}, text
    meta = yaml.safe_load(text[3:end]) or {}
    return meta, text


def norm_name(name):
    """归一化名称：去掉空格，用于课题 tags → Domain/Concept 匹配。"""
    return (name or '').replace(' ', '').replace('　', '').strip().lower()


def clip(text, limit=SUMMARY_LIMIT):
    text = (text or '').strip().replace('\n', ' ')
    return text if len(text) <= limit else text[:limit] + '…'


# 抽取噪音特征：知识库自动抽取产生的一批“伪概念”，summary 是元描述模板句而非定义
NOISE_MARKERS = ('本情报中出现的', '知识图谱中的技术概念节点')
NOISE_META_RE = re.compile(r'^.{1,24}，(属于|作为(实体|技术概念|标签|攻击手法|防护手段))')
NOISE_REL_RE = re.compile(r'，与.+存在关联')


def is_noise_concept(name, summary):
    """判定抽取噪音概念：summary 为模板句（“X，属于YY领域，与ZZ存在关联”“本情报中出现的标签”等）。"""
    s = (summary or '').strip()
    if not s:
        return True
    head = s[:64]
    if any(m in head for m in NOISE_MARKERS):
        return True
    if NOISE_META_RE.match(head) and (NOISE_REL_RE.search(head) or '，属于' in head):
        return True
    return False


# ---------------------------------------------------------------- 数据采集

def load_site_content():
    topics, articles = [], []
    for p in sorted((SITE / '_topics').glob('*.md')):
        meta, _ = frontmatter_of(p)
        if meta.get('published', True):
            slug = p.stem
            topics.append({
                'slug': slug, 'title': meta.get('title', slug),
                'subtitle': meta.get('subtitle', ''), 'status': meta.get('status', '待开始'),
                'categories': meta.get('categories') or [], 'tags': meta.get('tags') or [],
                'keyword': meta.get('keyword', ''), 'updated': str(meta.get('updated', '')),
            })
    for p in sorted((SITE / '_articles').glob('*.md')):
        meta, _ = frontmatter_of(p)
        if not meta.get('published', True):
            continue
        slug = p.stem
        articles.append({
            'slug': slug, 'title': meta.get('title', slug),
            'topic': meta.get('topic', ''), 'category': meta.get('category', ''),
            'tags': meta.get('tags') or [], 'date': str(meta.get('date', '')),
        })
    log(f'官网内容：课题 {len(topics)} 个，文章 {len(articles)} 篇')
    return topics, articles


def fetch_domain_map(domains):
    """每个 Domain 的核心概念（按度数，level L0-L2，滤掉泛化 hub 与跨域词）。"""
    result = cypher([{
        'statement': (
            'MATCH (c:Concept)-[:BELONGS_TO]->(d:Domain) WHERE d.name IN $names AND coalesce(c.level,"L2") IN ["L0","L1","L2"] '
            'AND size([(c)-[:BELONGS_TO]->() | 1]) <= 6 '
            'OPTIONAL MATCH (c)--() WITH c, d, count(*) AS degree '
            'RETURN d.name AS domain, c.name AS name, c.summary AS summary, c.level AS level, degree ORDER BY degree DESC'
        ),
        'parameters': {'names': domains},
    }])
    by_domain = {}
    for r in rows(result):
        d, name = r['domain'], r['name']
        # 过滤泛化 hub：与 Domain 同名、长度<=2 的短名（"AI"“云”类）、度数畸高的超级节点
        if not name or name == d or len(name) <= 2 or (r['degree'] or 0) > 2000:
            continue
        # 过滤抽取噪音概念（模板句 summary：媒体名、"个组织"、"创纪录"类伪概念）
        if is_noise_concept(name, r['summary']):
            continue
        if len(by_domain.setdefault(d, [])) < CORE_PER_DOMAIN:
            by_domain[d].append(r)
    for d, items in by_domain.items():
        log(f'域 [{d}] 核心概念 {len(items)} 个（首名: {items[0]["name"] if items else "-"}）')
    return by_domain


def match_concepts(names):
    """按名称精确匹配 Concept（同样滤掉抽取噪音）。"""
    if not names:
        return []
    uniq = sorted(set(names))
    result = cypher([{
        'statement': 'MATCH (c:Concept) WHERE c.name IN $names '
                     'OPTIONAL MATCH (c)--() WITH c, count(*) AS degree '
                     'RETURN c.name AS name, c.summary AS summary, c.level AS level, degree',
        'parameters': {'names': uniq},
    }])
    return [r for r in rows(result) if not is_noise_concept(r['name'], r['summary'])]


def fetch_inner_relations(names, limit=300):
    """选中概念集合内部的关系（按 source+target 去重，平行关系只保留一条）。"""
    if len(names) < 2:
        return []
    result = cypher([{
        'statement': (
            'MATCH (a:Concept)-[r]->(b:Concept) '
            'WHERE a.name IN $names AND b.name IN $names AND type(r) IN $rels '
            'RETURN a.name AS source, type(r) AS rel, b.name AS target LIMIT $limit'
        ),
        'parameters': {'names': sorted(set(names)), 'rels': list(REL_TYPES), 'limit': limit},
    }])
    seen, out = set(), []
    for r in rows(result):
        key = (r['source'], r['target'])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def fetch_recent_concepts():
    """近 N 天入库的概念（ingested_at），按度数排序。"""
    result = cypher([{
        'statement': (
            'MATCH (c:Concept) WHERE c.ingested_at IS NOT NULL AND '
            'datetime(c.ingested_at) > datetime() - duration({days: $days}) '
            'OPTIONAL MATCH (c)--() WITH c, count(*) AS degree '
            'RETURN c.name AS name, c.summary AS summary, c.level AS level, c.ingested_at AS ingested_at, degree '
            'ORDER BY degree DESC LIMIT 15'
        ),
        'parameters': {'days': RECENT_DAYS},
    }])
    return rows(result)


def fetch_practices():
    """全部 Practice 节点（实践层，经 APPLIES 关联概念）。"""
    result = cypher([{
        'statement': 'MATCH (p:Practice) OPTIONAL MATCH (p)-[:APPLIES]->(c:Concept) '
                     'RETURN p.title AS name, p.summary AS summary, collect(c.name) AS related',
    }])
    return rows(result)


def fetch_stats():
    result = cypher([{
        'statement': 'MATCH (c:Concept) WITH count(c) AS concepts '
                     'OPTIONAL MATCH (:Source) WITH concepts, count(*) AS sources '
                     'OPTIONAL MATCH (:Practice) WITH concepts, sources, count(*) AS practices '
                     'OPTIONAL MATCH (:Domain) RETURN concepts, sources, practices, count(*) AS domains',
    }])
    r = rows(result)
    return r[0] if r else {}


# ---------------------------------------------------------------- 图谱数据

def relevance(topic, cname, csummary):
    """课题 × 概念粗相关性：概念名出现在课题文本中 > 课题关键词出现在概念摘要中 > 仅凭度数。"""
    text = ' '.join([topic['title'], topic.get('keyword') or '',
                     topic.get('subtitle') or '', ' '.join(topic.get('tags') or [])])
    score = 0
    if len(cname) >= 2 and cname in text:
        score += 2
    kw = topic.get('keyword') or ''
    if len(kw) >= 2 and kw in (csummary or ''):
        score += 1
    return score


def build_graph_data(topics, articles, domain_cores, tag_concepts, inner_rels, practices):
    """构建官网 /graph/ 页面的精选锚点图谱 JSON。"""
    # 概念池：Domain core + tag 匹配，dict 去重
    concept_pool = {}

    def add_concept(name, summary, level, degree, source, domain=''):
        if not name or name in concept_pool:
            return
        concept_pool[name] = {
            'id': 'concept:' + name, 'type': 'concept', 'name': name,
            'level': level or 'L2', 'domain': domain,
            'summary': clip(summary), 'degree': int(degree or 0),
            '_sources': {source},
        }

    # Domain 名归一化映射（课题 categories → 知识库 Domain）
    all_domains = set()
    for t in topics:
        all_domains.update(t['categories'])
    domain_lookup = {}
    for d in domain_cores:
        domain_lookup[norm_name(d)] = d
        domain_lookup[d] = d

    topic_domains = {}
    for t in topics:
        matched = []
        for c in t['categories']:
            d = domain_lookup.get(norm_name(c))
            if d:
                matched.append(d)
        topic_domains[t['slug']] = matched

    # 课题 → Domain core 概念（相关性排序后截断，避免课题挂满无关的域重心词）
    topic_core_links = []
    for t in topics:
        pool = [(d, c) for d in topic_domains[t['slug']] for c in domain_cores.get(d, [])]
        pool.sort(key=lambda dc: (-relevance(t, dc[1]['name'], dc[1]['summary']),
                                  -(dc[1]['degree'] or 0)))
        seen = set()
        for d, c in pool:
            if len(seen) >= CORE_LINK_PER_TOPIC:
                break
            if c['name'] in seen:
                continue
            seen.add(c['name'])
            add_concept(c['name'], c['summary'], c['level'], c['degree'], 'core', d)
            topic_core_links.append({'source': 'topic:' + t['slug'], 'target': 'concept:' + c['name'],
                                     'type': 'core', 'domain': d})

    # 课题 tags/keyword → 概念（tag 匹配）
    tag_names = set()
    for t in topics:
        tag_names.update(t['tags'])
        if t['keyword']:
            tag_names.add(t['keyword'])
    for a in articles:
        tag_names.update(a['tags'])
        if a['category']:
            tag_names.add(a['category'])
    tag_matched = {c['name']: c for c in tag_concepts
                   if norm_name(c['name']) not in {norm_name(d) for d in domain_cores}
                   and len(c['name']) > 2}

    topic_tag_links = []
    for t in topics:
        names = set(t['tags']) | ({t['keyword']} if t['keyword'] else set())
        for n in names:
            c = tag_matched.get(n)
            if c:
                add_concept(c['name'], c['summary'], c['level'], c['degree'], 'tag', '')
                topic_tag_links.append({'source': 'topic:' + t['slug'], 'target': 'concept:' + c['name'], 'type': 'tag'})

    article_tag_links = []
    for a in articles:
        for n in set(a['tags']) | ({a['category']} if a['category'] else set()):
            c = tag_matched.get(n)
            if c:
                add_concept(c['name'], c['summary'], c['level'], c['degree'], 'tag', '')
                article_tag_links.append({'source': 'article:' + a['slug'], 'target': 'concept:' + c['name'], 'type': 'tag'})

    # 概念内部关系（限定在池内）
    pool_names = set(concept_pool)
    concept_links = []
    for r in inner_rels:
        if r['source'] in pool_names and r['target'] in pool_names:
            concept_links.append({'source': 'concept:' + r['source'], 'target': 'concept:' + r['target'],
                                  'type': 'rel', 'rel': r['rel']})

    # Practice 节点：仅收录与池内概念有关联的
    practice_nodes, practice_links = [], []
    for p in practices:
        related = p.get('related') or []
        hit = [c for c in related if c in pool_names]
        if hit:
            pid = 'practice:' + p['name']
            practice_nodes.append({'id': pid, 'type': 'practice', 'name': p['name'], 'summary': clip(p['summary'])})
            for c in hit[:4]:
                practice_links.append({'source': pid, 'target': 'concept:' + c, 'type': 'applies'})

    # 课题与文章节点
    topic_nodes = [{
        'id': 'topic:' + t['slug'], 'type': 'topic', 'name': t['title'],
        'url': '/topics/' + t['slug'] + '/', 'status': t['status'],
        'categories': t['categories'], 'summary': clip(t['subtitle'], 60), 'updated': t['updated'],
    } for t in topics]
    article_nodes = [{
        'id': 'article:' + a['slug'], 'type': 'article', 'name': a['title'],
        'url': '/articles/' + a['slug'] + '/', 'topic': a['topic'],
        'summary': clip(a['title'], 60), 'date': a['date'],
    } for a in articles]

    belongs = [{'source': 'article:' + a['slug'], 'target': 'topic:' + a['topic'], 'type': 'belongs'}
               for a in articles if a['topic']]

    # 只保留有连接的概念节点（被截断的 core 概念可能成为孤立点）
    all_links = topic_core_links + topic_tag_links + article_tag_links + belongs + concept_links + practice_links
    linked_ids = {l['source'] for l in all_links} | {l['target'] for l in all_links}
    concepts = [dict(v) for v in concept_pool.values() if v['id'] in linked_ids]
    for c in concepts:
        c.pop('_sources', None)

    data = {
        'meta': {
            'generated_at': dt.datetime.now().isoformat(timespec='seconds'),
            'source': '工作站知识库 · 东方隐侠安全团队',
            'disclosure': '概念摘要经截断展示，完整知识图谱存于工作站内网',
            'counts': {'topics': len(topic_nodes), 'articles': len(article_nodes),
                       'concepts': len(concepts), 'practices': len(practice_nodes),
                       'links': len(topic_core_links) + len(topic_tag_links) + len(article_tag_links)
                                + len(belongs) + len(concept_links) + len(practice_links)},
        },
        'nodes': topic_nodes + article_nodes + concepts + practice_nodes,
        'links': topic_core_links + topic_tag_links + article_tag_links + belongs + concept_links + practice_links,
    }
    log(f'图谱数据：{len(data["nodes"])} 节点 / {len(data["links"])} 连接')
    return data, {
        'topic_domains': topic_domains, 'concept_pool': concept_pool,
        'tag_matched': tag_matched, 'domain_cores': domain_cores,
    }


# ---------------------------------------------------------------- 候选清单

def load_status():
    f = DISTILL_DIR / 'status.json'
    if f.exists():
        try:
            return json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}


def build_candidates(topics, articles, ctx, recent, practices, stats):
    """生成周度提炼候选清单。"""
    pool = ctx['concept_pool']
    tag_matched = ctx['tag_matched']
    domain_cores = ctx['domain_cores']
    topic_domains = ctx['topic_domains']
    status = load_status()
    cands = []

    def add(cid, ctype, title, detail, action, priority, ref=''):
        cands.append({'id': cid, 'type': ctype, 'title': title, 'detail': detail,
                      'action': action, 'priority': priority, 'ref': ref,
                      'status': status.get(cid, {}).get('status', 'open')})

    # A. 未挂课题的文章
    topic_by_norm = {norm_name(t['title']): t for t in topics}
    for t in topics:
        topic_by_norm.setdefault(norm_name(t['slug']), t)
    for a in articles:
        if a['topic']:
            continue
        suggest = [t for t in topics if norm_name(a['category']) in
                   {norm_name(c) for c in t['categories']}]
        suggest_names = '、'.join(t['title'] for t in suggest[:3]) or '按内容人工判断'
        add(f'article-orphan:{a["slug"]}', 'article-orphan',
            f'文章未挂课题：{a["title"]}',
            f'文章 frontmatter 缺 topic 字段，所属分类「{a["category"] or "未填"}」。按分类匹配建议课题：{suggest_names}。',
            f'编辑 _articles/{a["slug"]}.md，补 topic: 建议slug；再到课题「术」层加入口（publication: true, type: 原创）。',
            'high', 'article:' + a['slug'])

    # B. 课题交叉点：仅用课题显式声明（tags/keyword）命中的概念，避免同分类课题因共享 Domain 核心概念而假阳性
    topic_tag_concepts, topic_all_concepts = {}, {}
    for t in topics:
        tag_hits = {n for n in set(t['tags']) | ({t['keyword']} if t['keyword'] else set()) if n in tag_matched}
        core_hits = set()
        for d in topic_domains.get(t['slug'], []):
            core_hits.update(c['name'] for c in domain_cores.get(d, []))
        topic_tag_concepts[t['slug']] = tag_hits
        topic_all_concepts[t['slug']] = tag_hits | core_hits
    for i, t1 in enumerate(topics):
        for t2 in topics[i + 1:]:
            shared = topic_tag_concepts[t1['slug']] & topic_tag_concepts[t2['slug']]
            if len(shared) >= 2:
                shared_txt = '、'.join(sorted(shared)[:6])
                add(f'topic-overlap:{t1["slug"]}:{t2["slug"]}', 'topic-overlap',
                    f'课题交叉点：{t1["title"]} × {t2["title"]}',
                    f'两课题显式关注的概念重叠 {len(shared)} 个：{shared_txt}。存在交叉研究空间，可互链或合并视角。',
                    '在两个课题页 links/互推入口中互相引用，或评估是否合并为同一研究纲领。',
                    'medium', f'topic:{t1["slug"]}|topic:{t2["slug"]}')

    # C. 课题概念缺口（Domain 核心概念未入课题 tags）
    for t in topics:
        own = {norm_name(n) for n in t['tags']} | ({norm_name(t['keyword'])} if t['keyword'] else set())
        gaps = []
        for d in topic_domains.get(t['slug'], []):
            for c in domain_cores.get(d, [])[:6]:
                if norm_name(c['name']) not in own:
                    gaps.append(c)
        if gaps:
            gap_txt = '；'.join(f'{c["name"]}（{c["level"]}）' for c in gaps[:4])
            add(f'topic-gap:{t["slug"]}', 'topic-gap',
                f'课题概念缺口：{t["title"]}',
                f'所属域的核心概念中 {len(gaps)} 个尚未纳入课题视角：{gap_txt}。可作为研究议程扩展方向。',
                '评估这些概念是否值得加入课题「道法术器」任一层，或在 tags 中显式覆盖。',
                'medium', 'topic:' + t['slug'])

    # D. 新入库概念
    for c in recent:
        add(f'new-concept:{c["name"]}', 'new-concept',
            f'新入库概念：{c["name"]}',
            f'近 {RECENT_DAYS} 天入库（{c["level"]}，连接度 {int(c["degree"] or 0)}）。{clip(c["summary"], 80)}',
            '评估是否与现有课题相关：相关则补入课题，重要且独立可考虑立项。',
            'low', 'concept:' + c['name'])

    # E. 实践关联（Practice ↔ 官网课题）
    for p in practices:
        related = p.get('related') or []
        hits = []
        for t in topics:
            inter = set(related) & topic_all_concepts.get(t['slug'], set())
            if inter:
                hits.append((t, inter))
        if hits:
            t0, inter = hits[0]
            add(f'practice-link:{p["name"]}', 'practice-link',
                f'实践笔记可反哺官网：{p["name"]}',
                f'知识库实践层笔记，关联概念与课题「{t0["title"]}」重叠（{ "、".join(sorted(inter)[:4]) }）。实践中的踩坑与方案可提炼为官网文章。',
                f'阅读实践笔记（GET /api/obsidian/concept/{related[0] if related else ""}/practices），评估提炼为原创文章或课题「术」层案例。',
                'low', 'practice:' + p['name'])

    open_cands = [c for c in cands if c['status'] == 'open']
    by_type = {}
    for c in cands:
        by_type[c['type']] = by_type.get(c['type'], 0) + 1
    report = {
        'date': dt.date.today().isoformat(),
        'generated_at': dt.datetime.now().isoformat(timespec='seconds'),
        'summary': {
            'total': len(cands), 'open': len(open_cands),
            'processed': len(cands) - len(open_cands), 'by_type': by_type,
        },
        'stats': {
            'concepts': int(stats.get('concepts') or 0), 'sources': int(stats.get('sources') or 0),
            'practices': int(stats.get('practices') or 0), 'domains': int(stats.get('domains') or 0),
            'topics': len(topics), 'articles': len(articles),
        },
        'candidates': cands,
    }
    log(f'候选清单：{len(cands)} 条（open {len(open_cands)} / 已处理 {len(cands) - len(open_cands)}）')
    return report


# ---------------------------------------------------------------- 写出与发布

def write_outputs(graph_data, report, dry):
    if not dry:
        GRAPH_OUT.parent.mkdir(parents=True, exist_ok=True)
        GRAPH_OUT.write_text(json.dumps(graph_data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        log(f'已写出 {GRAPH_OUT.relative_to(SITE)}')
        if report is None:
            return graph_data, report
        DISTILL_DIR.mkdir(parents=True, exist_ok=True)
        report_file = DISTILL_DIR / f'candidates-{report["date"].replace("-", "")}.json'
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
        # 更新报告索引（保留最近 KEEP_REPORTS 期）
        index_file = DISTILL_DIR / 'index.json'
        index = {'reports': []}
        if index_file.exists():
            try:
                index = json.loads(index_file.read_text(encoding='utf-8'))
            except Exception:
                pass
        index['reports'] = [r for r in index.get('reports', []) if r.get('date') != report['date']]
        index['reports'].append({'date': report['date'], 'file': report_file.name,
                                 'generated_at': report['generated_at'],
                                 'total': report['summary']['total'], 'open': report['summary']['open'],
                                 'by_type': report['summary']['by_type']})
        index['reports'] = index['reports'][-KEEP_REPORTS:]
        index['updated'] = dt.datetime.now().isoformat(timespec='seconds')
        index_file.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding='utf-8')
        log(f'已写出报告 {report_file.name} 与 index.json')
    return graph_data, report


def push_graph(dry):
    """单独提交并推送图谱数据（仅 assets/graph/，一条干净提交）。"""
    if dry:
        log('dry-run：跳过 git 提交')
        return
    rel = str(GRAPH_OUT.relative_to(SITE))
    stamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    cmds = [
        ['git', 'add', rel],
        ['git', 'diff', '--cached', '--quiet'],  # 无变化则退出码 1
    ]
    subprocess.run(cmds[0], cwd=SITE, check=True)
    if subprocess.run(cmds[1], cwd=SITE).returncode == 0:
        log('图谱数据无变化，跳过提交')
        return
    subprocess.run(['git', 'commit', '-m', f'知识图谱数据周度更新 {stamp}'], cwd=SITE, check=True)
    r = subprocess.run(['git', 'push'], cwd=SITE, capture_output=True, text=True)
    if r.returncode == 0:
        log('已推送图谱数据到 GitHub Pages')
    else:
        log('git push 失败（不影响候选清单）：' + (r.stderr or r.stdout).strip()[:200])


# ---------------------------------------------------------------- 主流程

def main():
    parser = argparse.ArgumentParser(description='工作站知识库 → 官网 周度知识提炼')
    parser.add_argument('--push-graph', action='store_true', help='提炼后自动 commit+push 图谱数据')
    parser.add_argument('--graph-only', action='store_true', help='只生成图谱数据，不写候选报告')
    parser.add_argument('--dry-run', action='store_true', help='只打印，不写文件')
    args = parser.parse_args()

    log('=== 知识库周度提炼 开始 ===')
    topics, articles = load_site_content()

    # 图谱查询
    domain_names = sorted({c for t in topics for c in t['categories']})
    domain_cores = fetch_domain_map(domain_names)
    tag_names = set()
    for t in topics:
        tag_names.update(t['tags'])
        if t['keyword']:
            tag_names.add(t['keyword'])
    for a in articles:
        tag_names.update(a['tags'])
        if a['category']:
            tag_names.add(a['category'])
    log(f'待匹配名称 {len(tag_names)} 个（课题/文章 tags+keyword+category）')
    tag_concepts = match_concepts(sorted(tag_names))
    log(f'标签命中概念 {len(tag_concepts)} 个')
    # 概念间关系查询集合：tag 命中 + 各域核心概念（池内过滤在 build_graph_data 做）
    rel_names = [c['name'] for c in tag_concepts]
    for items in domain_cores.values():
        rel_names.extend(c['name'] for c in items)
    inner = fetch_inner_relations(rel_names)
    log(f'概念内部关系 {len(inner)} 条')

    graph_data, ctx = build_graph_data(topics, articles, domain_cores, tag_concepts, inner, [])

    report = None
    if not args.graph_only:
        recent = fetch_recent_concepts()
        log(f'近 {RECENT_DAYS} 天新概念 {len(recent)} 个')
        practices = fetch_practices()
        log(f'实践笔记 {len(practices)} 篇')
        stats = fetch_stats()
        report = build_candidates(topics, articles, ctx, recent, practices, stats)

    write_outputs(graph_data, report, args.dry_run)
    if args.push_graph:
        push_graph(args.dry_run)
    log('=== 知识库周度提炼 完成 ===')


if __name__ == '__main__':
    main()
