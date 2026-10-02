const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

async function main() {
    const origin = process.env.TURNI_PREVIEW_URL || 'http://127.0.0.1:8783';
    assert.ok(['127.0.0.1', 'localhost'].includes(new URL(origin).hostname));
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    try {
        const page = await browser.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.addInitScript(() => {
            window.exportWrites = [];
            window.pickerCalls = 0;
            window.failFile = '';
            window.cancelPicker = false;
            window.showDirectoryPicker = async () => {
                window.pickerCalls += 1;
                if (window.cancelPicker) throw new DOMException('Cancelled', 'AbortError');
                return { getFileHandle: async name => ({ createWritable: async () => ({
                    write: async () => {},
                    close: async () => {
                        if (window.failFile === name) throw new Error('Simulated write failure');
                        window.exportWrites.push(name);
                    },
                }) }) };
            };
        });
        const requests = [];
        let failResponse = false;
        await page.route('**/portal/turni-planner/**', async route => {
            const request = route.request();
            if (request.method() !== 'POST') return route.continue();
            const form = await new Request(request.url(), {
                method: 'POST', headers: request.headers(), body: request.postDataBuffer(),
            }).formData();
            const action = form.get('action');
            if (!action?.startsWith('export_')) return route.continue();
            requests.push(action);
            if (failResponse) return route.fulfill({ status: 200, contentType: 'text/html', body: 'Login required' });
            await route.fulfill({ status: 200, contentType: action.startsWith('export_pdf_') ? 'application/pdf' : 'image/jpeg',
                headers: { 'Content-Disposition': `attachment; filename="${action}"` }, body: 'export fixture' });
        });
        await page.goto(`${origin}/__preview__/admin/`);
        await page.goto(`${origin}/portal/turni-planner/`);
        const label = `Export test ${Date.now()}`;
        await page.locator('#week_label').fill(label);
        await Promise.all([page.waitForURL(url => url.searchParams.get('week') === label), page.locator('#week_label').press('Enter')]);

        async function exportChanged(format, expected, failed = false) {
            requests.length = 0;
            await page.locator('[data-turni-panel="dashboard"]').click();
            const button = page.locator(`[data-bulk-export-format="${format}"]`);
            await button.click();
            await page.waitForFunction(() => [...document.querySelectorAll('[data-bulk-export-format]')].every(element => !element.disabled));
            assert.deepEqual(requests, expected);
            if (!failed) assert.equal(await page.locator('[data-bulk-export-status]').evaluate(element => element.classList.contains('text-danger')), false);
        }

        const sections = ['weekly', 'portineria_weekly', 'saturday', 'sunday', 'jolly_weekend', 'scorrimento', 'portineria_weekend'];
        await exportChanged('pdf', sections.map(section => `export_pdf_${section}`));
        await exportChanged('pdf', []);
        assert.equal(await page.evaluate(() => window.pickerCalls), 1);
        await exportChanged('jpg', sections.map(section => `export_jpg_${section}`));
        await page.locator('[data-turni-panel="weekly"]').click();
        const name = page.locator('[name="weekly_row_0_0"]').first();
        const original = await name.inputValue();
        const modifiedName = `Nome ${Date.now()}`;
        await name.fill(modifiedName);
        await exportChanged('all', ['export_pdf_weekly', 'export_jpg_weekly']);
        await exportChanged('all', []);
        await page.locator('[data-turni-panel="weekly"]').click();
        await name.fill(original);
        await name.fill(modifiedName);
        await exportChanged('all', []);

        await page.locator('#weekly_export_week_label').fill(`Titolo ${label}`);
        await page.evaluate(() => { window.failFile = 'export_jpg_weekly'; });
        await exportChanged('all', ['export_pdf_weekly', 'export_jpg_weekly'], true);
        await page.evaluate(() => { window.failFile = ''; });
        await exportChanged('all', ['export_jpg_weekly']);
        await page.locator('[data-turni-panel="saturday"]').click();
        const saturdayDate = page.locator('[name="saturday_base_date"]');
        await saturdayDate.fill(await saturdayDate.inputValue() === '10/10/2026' ? '17/10/2026' : '10/10/2026');
        await page.evaluate(() => { window.cancelPicker = true; });
        await exportChanged('all', []);
        await page.evaluate(() => { window.cancelPicker = false; });
        await exportChanged('all', ['export_pdf_saturday', 'export_jpg_saturday']);

        for (const [section, field] of [
            ['portineria_weekly', 'portineria_weekly_row_0_0'],
            ['sunday', 'sunday_base_date'],
            ['jolly_weekend', 'jolly_weekend_title'],
            ['scorrimento', 'scorrimento_title'],
            ['portineria_weekend', 'portineria_weekend_base_date'],
        ]) {
            await page.locator(`[data-turni-panel="${section.replaceAll('_', '-')}"]`).click();
            const input = page.locator(`[name="${field}"]`).first();
            await input.fill((await input.inputValue()) + ' aggiornato');
            await exportChanged('all', [`export_pdf_${section}`, `export_jpg_${section}`]);
        }
        await page.locator('[data-turni-panel="saturday"]').click();
        await page.locator('[data-weekend-row-prefix="saturday"] [data-weekend-row-action="remove"]').click();
        failResponse = true;
        await exportChanged('pdf', ['export_pdf_saturday'], true);
        failResponse = false;
        await exportChanged('all', ['export_pdf_saturday', 'export_jpg_saturday']);

        await Promise.all([page.waitForNavigation(), page.locator('[name="action"][value="save_planner"]').click()]);
        await exportChanged('all', []);
        assert.deepEqual(errors, []);
        console.log('OK: all sections/formats, no-op, reverted changes, titles, row removal, failed responses/writes, cancellation and persistence after saving');
    } finally {
        await browser.close();
    }
}

main().catch(error => { console.error(error); process.exitCode = 1; });