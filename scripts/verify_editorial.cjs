const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

const base = process.env.SITE_URL || 'http://127.0.0.1:4018';
const output = process.env.QA_OUTPUT || '/tmp/eastsword-ui-qa';
const routes = ['/', '/topics/', '/resources/', '/articles/', '/about/', '/topics/ai-agent-governance/', '/topics/mcp-supply-chain/', '/articles/ai-agent-governance/', '/news/', '/tools/', '/wall/'];

(async () => {
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome' });
  const errors = [];
  const broken = [];
  const localLinks = new Set();
  const layoutIssues = [];
  try {
    const context = await browser.newContext();
    // Isolate local UI checks from analytics, comments and remote font availability.
    await context.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.origin === new URL(base).origin) return route.continue();
      if (url.pathname === '/news-archive/feed.json') return route.fulfill({ json: { items: [{ title: 'Agent 安全研究动态', source: '测试来源', published_date: '2026-09-08', url: 'https://example.org/research' }] } });
      return route.abort();
    });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => { if (response.url().startsWith(base) && response.status() >= 400) broken.push(response.url()); });
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: width === 1440 ? 1000 : 844 });
      for (const route of routes) {
        await page.goto(base + route, { waitUntil: 'networkidle' });
        await page.evaluate(() => Promise.all(Array.from(document.querySelectorAll('main img')).map(img => { img.loading = 'eager'; return img.decode().catch(() => {}); })));
        const audit = await page.evaluate(() => {
          const visible = el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
          const overflow = Array.from(document.querySelectorAll('main *, .nav *')).filter(el => {
            if (!visible(el) || el.closest('pre, .table-shell, table, .df-tip')) return false;
            const r = el.getBoundingClientRect();
            return r.width > 0 && (r.right > innerWidth + 2 || r.left < -2);
          }).map(el => el.tagName + '.' + el.className).slice(0, 10);
          return { overflow, images: Array.from(document.querySelectorAll('main img')).filter(el => !el.complete || !el.naturalWidth).map(el => el.src), links: Array.from(document.querySelectorAll('a[href]')).map(el => el.getAttribute('href')).filter(href => href.startsWith('/')) };
        });
        if (audit.overflow.length) layoutIssues.push({ width, route, elements: audit.overflow });
        assert.deepEqual(audit.images, [], `Missing image ${width} ${route}`);
        audit.links.forEach(link => localLinks.add(link));
        if (['/', '/resources/', '/topics/', '/about/'].includes(route) && width !== 320) {
          await page.screenshot({ path: path.join(output, `${width}-${route.replaceAll('/', '') || 'home'}.png`), fullPage: true });
          if (route === '/') await page.screenshot({ path: path.join(output, `${width}-home-viewport.png`) });
        }
        if (route === '/') {
          assert.equal(await page.locator('.focus-story').count(), 1);
          assert.equal(await page.locator('.source-preview .source-entry').count(), 3);
          const bounds = await page.locator('#focus-heading').boundingBox();
          assert(bounds.y < (width === 1440 ? 1000 : 844), 'Research heading must appear in first viewport');
        }
      }
    }
    assert.deepEqual(layoutIssues, [], 'Responsive layout issues');
    await page.goto(base + '/resources/', { waitUntil: 'networkidle' });
    assert.equal(await page.locator('[data-resource]:visible').count(), 8);
    const external = await page.locator('.source-entry h3 a').evaluateAll(links => links.every(a => /^https?:/.test(a.getAttribute('href'))));
    assert(external, 'Resource URLs must point to their original source');
    await page.locator('#resource-search').fill('MCP');
    assert((await page.locator('[data-resource]:visible').count()) > 0);
    await page.locator('#resource-type').selectOption('官方规范');
    assert.equal(await page.locator('[data-resource]:visible').count(), 2);
    await page.locator('#resource-search').fill('zz-no-match');
    assert(await page.locator('#resource-empty').isVisible());
    await page.getByRole('button', { name: '重置筛选' }).click();
    await page.waitForFunction(() => document.querySelector('#resource-count').textContent === '8 条资料');
    await page.goto(base + '/resources/?topic=mcp-supply-chain', { waitUntil: 'networkidle' });
    assert((await page.locator('[data-resource]:visible').count()) > 0);
    await page.goto(base + '/topics/?category=AI安全', { waitUntil: 'networkidle' });
    assert.equal(await page.locator('#topic-list .tile:visible').count(), 3);
    await page.getByRole('button', { name: /^待开始/ }).click();
    assert.equal(await page.locator('#topic-list .tile:visible').count(), 1);
    await page.locator('#topic-search').fill('no-topic-found');
    assert(await page.locator('#empty-result').isVisible());
    await page.goto(base + '/about/', { waitUntil: 'networkidle' });
    await page.locator('.contact-card[data-modal="modal-wechat"]').click();
    assert(await page.locator('#modal-wechat').isVisible());
    await page.keyboard.press('Escape');
    assert(await page.locator('#modal-wechat').isHidden());
    for (const link of localLinks) {
      const response = await context.request.get(base + link);
      assert(response.ok(), `Broken internal link ${link}: ${response.status()}`);
      const hash = new URL(base + link).hash;
      if (hash) {
        const html = await response.text();
        assert(html.includes(`id="${decodeURIComponent(hash.slice(1))}"`), `Missing anchor ${link}`);
      }
    }
    await context.route('**/news-archive/feed.json', route => route.fulfill({ status: 503, body: 'Unavailable' }));
    await page.goto(base, { waitUntil: 'networkidle' });
    assert.match(await page.locator('#home-news-list').innerText(), /暂时无法加载/);
    await context.route('**/news-archive/feed.json', route => route.fulfill({ json: { items: [] } }));
    await page.reload({ waitUntil: 'networkidle' });
    assert.match(await page.locator('#home-news-list').innerText(), /暂无资讯/);
    assert.deepEqual(errors, [], 'Browser exceptions');
    assert.deepEqual(broken, [], 'Local HTTP errors');
    console.log(JSON.stringify({ pages: routes.length, widths: [1440, 390, 320], internalLinks: localLinks.size, checks: 'layout, images, filtering, query links, anchors, contact modal, news success/error/empty', screenshots: output }, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
