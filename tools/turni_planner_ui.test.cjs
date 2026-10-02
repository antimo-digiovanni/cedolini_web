const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

async function main() {
    const origin = process.env.TURNI_PREVIEW_URL || 'http://127.0.0.1:8783';
    assert.ok(['127.0.0.1', 'localhost'].includes(new URL(origin).hostname), 'Use a local disposable preview only');
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    try {
        const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.goto(`${origin}/__preview__/admin/`);
        await page.goto(`${origin}/portal/turni-planner/`);
        const run = Date.now();
        for (const label of [`Prova precedente ${run}`, `Prova corrente ${run}`]) {
            await page.locator('#week_label').fill(label);
            await Promise.all([
                page.waitForURL(url => url.searchParams.get('week') === label),
                page.locator('#week_label').press('Enter'),
            ]);
        }
        const history = page.locator('.turni-week-history');
        const historyToggle = history.locator(':scope > summary');
        assert.equal(await history.getAttribute('open'), null);
        assert.equal(await page.locator('.turni-recent-week-item:visible').count(), 1);
        await historyToggle.click();
        assert.ok(await page.locator('.turni-recent-week-item:visible').count() >= 2);
        assert.ok(await page.locator('.turni-week-history-list').evaluate(element => element.clientHeight <= 320));
        const currentWeekUrl = page.url();
        await history.locator('.turni-recent-week-main a').first().click();
        assert.equal(await history.getAttribute('open'), null);
        assert.equal(await page.locator('.turni-recent-week-item:visible').count(), 1);
        await historyToggle.click();
        assert.equal(await page.locator('[data-turni-mail-recipients]').isVisible(), false);
        await page.locator('.turni-week-mail-details summary').click();
        assert.equal(await page.locator('[data-turni-mail-recipients]').isVisible(), true);
        await page.goto(currentWeekUrl);
        assert.equal(await page.locator('.turni-week-mail-details').first().getAttribute('open'), null);
        assert.equal(await page.locator('.turni-opening-row .turni-planner-card').count(), 0);
        assert.equal(await page.locator('.turni-sidebar-card').evaluate(element => getComputedStyle(element).backgroundColor), 'rgb(224, 242, 254)');

        await page.locator('[data-turni-panel="weekly"]').click();
        const first = page.locator('[name="weekly_row_0_0"]').nth(0);
        const second = page.locator('[name="weekly_row_0_0"]').nth(1);
        const nextRow = page.locator('[name="weekly_row_0_1"]').nth(0);
        await first.fill('Mario Rossi');
        await second.click();
        await first.click();
        assert.deepEqual(await first.evaluate(element => [element.selectionStart, element.selectionEnd]), [0, 11]);
        await first.press('F2');
        await first.press('ArrowLeft');
        assert.equal(await first.evaluate(element => document.activeElement === element), true);
        assert.equal(await first.evaluate(element => element.selectionStart), 10);
        await first.press('Escape');
        await first.press('Tab');
        assert.equal(await second.evaluate(element => document.activeElement === element), true);
        await second.press('Shift+Tab');
        await first.press('Enter');
        assert.equal(await nextRow.evaluate(element => document.activeElement === element), true);

        await first.click();
        const editor = page.locator('[data-turni-name-editor]');
        assert.equal(await editor.inputValue(), 'Mario Rossi');
        await editor.fill('Nome provvisorio');
        await editor.press('Control+z');
        assert.equal(await first.inputValue(), 'Mario Rossi');
        await editor.press('Control+y');
        assert.equal(await first.inputValue(), 'Nome provvisorio');
        await editor.fill('Alessandro Di Giovanni');
        await editor.press('Enter');
        assert.equal(await first.inputValue(), 'Alessandro Di Giovanni');
        await page.locator('[data-turni-undo]').click();
        assert.equal(await first.inputValue(), 'Nome provvisorio');
        await page.locator('[data-turni-redo]').click();
        assert.equal(await first.inputValue(), 'Alessandro Di Giovanni');

        const scrollbar = page.locator('[data-sheet-scrollbar="weekly-sheet"]');
        assert.ok(await scrollbar.evaluate(element => element.scrollWidth > element.clientWidth));

        await first.click();
        await first.evaluate(element => {
            const clipboardData = new DataTransfer();
            clipboardData.setData('text/plain', 'Mario Rossi\tLaura Bianchi\nLuca Verdi\tAnna Neri');
            element.dispatchEvent(new ClipboardEvent('paste', { clipboardData, bubbles: true, cancelable: true }));
        });
        assert.equal(await first.inputValue(), 'Mario Rossi');
        assert.equal(await second.inputValue(), 'Laura Bianchi');
        assert.equal(await nextRow.inputValue(), 'Luca Verdi');
        await page.locator('[data-turni-undo]').click();
        assert.equal(await first.inputValue(), 'Alessandro Di Giovanni');
        await page.locator('[data-turni-redo]').click();
        assert.equal(await first.inputValue(), 'Mario Rossi');

        for (const width of [1440, 390]) {
            await page.setViewportSize({ width, height: 1000 });
            await page.locator('[data-turni-panel="weekly"]').click();
            await first.scrollIntoViewIfNeeded();
            const sizing = await first.evaluate(element => ({
                width: element.getBoundingClientRect().width,
                height: element.getBoundingClientRect().height,
                overflow: document.documentElement.scrollWidth > innerWidth,
            }));
            assert.ok(sizing.width >= 160, JSON.stringify(sizing));
            assert.ok(sizing.height >= 44, JSON.stringify(sizing));
            assert.equal(sizing.overflow, false, JSON.stringify(sizing));
            assert.ok(await page.locator('.turni-weekly-app-table tr:first-child th').evaluate(element => element.getBoundingClientRect().width <= 81));
            await page.screenshot({ path: `tmp/turni-planner-${width}.png`, fullPage: true });
        }

        await Promise.all([
            page.waitForNavigation(),
            page.locator('button[name="action"][value="save_planner"]').click(),
        ]);
        await page.locator('[data-turni-panel="weekly"]').click();
        assert.equal(await first.inputValue(), 'Mario Rossi');
        assert.equal(await second.inputValue(), 'Laura Bianchi');
        assert.equal(await nextRow.inputValue(), 'Luca Verdi');
        assert.deepEqual(errors, []);
        console.log('OK: history, sky-blue panels, editing, Tab/Enter, clipboard, undo/redo, responsive sizing and saved names');
    } finally {
        await browser.close();
    }
}

main().catch(error => { console.error(error); process.exitCode = 1; });