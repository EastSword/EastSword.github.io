const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const calls = [];
    let failCheck = false;
    // Intercept all release mutations: verification never commits or pushes.
    await page.route('**/api/admin/check', async route => {
      calls.push('check');
      await route.fulfill({ json: { job: 'test-check' } });
    });
    await page.route('**/api/admin/publish', async route => {
      calls.push('publish');
      assert.equal(route.request().postDataJSON().proof, 'test-proof');
      await route.fulfill({ json: { job: 'test-publish' } });
    });
    await page.route('**/api/admin/job/test-*', async route => {
      const check = route.request().url().endsWith('test-check');
      await route.fulfill({ json: check && failCheck
        ? { status: 'failed', error: '测试构建失败' }
        : { status: 'complete', result: check
          ? { ok: true, proof: 'test-proof' }
          : { ok: true, commit: 'testcommit123' } } });
    });
    await page.goto('http://127.0.0.1:8971/#release');
    const publish = page.getByRole('button', { name: '发布到官网', exact: true });
    await publish.waitFor();
    assert.equal(await publish.isEnabled(), true);
    await page.getByLabel('全选待发布文件').uncheck();
    assert.equal(await publish.isEnabled(), false);
    await page.getByLabel('全选待发布文件').check();
    await publish.click();
    await page.getByRole('button', { name: '确认发布', exact: true }).click();
    await page.waitForFunction(() => document.getElementById('toast').textContent.includes('testcom'));
    assert.deepEqual(calls, ['check', 'publish']);
    failCheck = true;
    calls.length = 0;
    await publish.click();
    await page.getByRole('button', { name: '确认发布', exact: true }).click();
    await page.locator('#modal-body').getByText('测试构建失败', { exact: true }).waitFor();
    assert.deepEqual(calls, ['check']);
    await page.getByRole('button', { name: '取消', exact: true }).click();
    await page.screenshot({ path: '/tmp/admin-release-desktop.png' });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: '/tmp/admin-release-mobile.png' });
    console.log('PASS: default selection, automatic check before push, failed check blocks push, mobile layout');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
