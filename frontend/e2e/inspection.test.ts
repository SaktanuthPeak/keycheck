// End-to-end flow against the MOCK API build (PUBLIC_USE_MOCK=1, see .env.test).
import { expect, test, type Page } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const FIXTURE = fileURLToPath(new URL('./fixtures/keyboard.jpg', import.meta.url));
// Slot centres in the 1200x700 fixture (Q centre 150,200; pitch 90; stagger 0 / .25 / .75).
const REF = {
	Q: [150 / 1200, 200 / 700],
	P: [960 / 1200, 200 / 700],
	M: [757.5 / 1200, 380 / 700],
	Z: [217.5 / 1200, 380 / 700]
} as const;
type Norm = readonly [number, number];

async function chooseFixture(page: Page) {
	await page.goto('/');
	await expect(page.getByTestId('layout-name')).toContainText('QWERTY');
	await page.locator('input[type=file]:not([capture])').setInputFiles(FIXTURE);
	await expect(page.getByTestId('local-preview')).toBeVisible();
}

async function uploadFixture(page: Page) {
	await chooseFixture(page);
	await page.getByRole('button', { name: 'ใช้ภาพนี้' }).click();
	await expect(page).toHaveURL(/\/inspect\?image=img_/);
	const img = page.getByTestId('corner-surface').locator('img');
	await expect(img).toBeVisible();
	await expect
		.poll(() => img.evaluate((el: HTMLImageElement) => el.complete && el.naturalWidth))
		.toBe(1200);
}

async function tap(page: Page, [x, y]: Norm, isMobile: boolean) {
	const surface = page.getByTestId('corner-surface');
	await surface.scrollIntoViewIfNeeded();
	const box = (await surface.locator('img').boundingBox())!;
	const px = box.x + x * box.width;
	const py = box.y + y * box.height;
	if (isMobile) await page.touchscreen.tap(px, py);
	else await page.mouse.click(px, py);
}

async function tapAll(page: Page, order: Norm[], isMobile: boolean, total = order.length) {
	for (const p of order) await tap(page, p, isMobile);
	await expect(page.getByTestId('corner-surface').locator('[data-handle]')).toHaveCount(total);
}

async function runToResult(page: Page, isMobile: boolean) {
	await uploadFixture(page);
	await tapAll(page, [REF.Q, REF.P, REF.M, REF.Z], isMobile);
	await expect(page.getByTestId('picker-instruction')).toContainText('ครบ 4 จุดแล้ว');
	await page.getByRole('button', { name: 'ส่งตรวจ' }).click();
	await expect(page).toHaveURL(/\/inspections\/ins_/);
}

async function noHorizontalScroll(page: Page) {
	const overflow = await page.evaluate(
		() => document.documentElement.scrollWidth - document.documentElement.clientWidth
	);
	expect(overflow).toBeLessThanOrEqual(1);
}

test('full flow: file -> preview -> upload -> 4 points -> stages -> result', async ({
	page,
	isMobile
}) => {
	await chooseFixture(page);
	await expect(page.getByTestId('mock-banner')).toBeVisible();
	await noHorizontalScroll(page);
	await runToResult(page, isMobile);

	// Stage names (no percentages) while polling.
	await expect(page.getByTestId('stage-text')).toBeVisible();
	await expect(page.getByTestId('stage-text')).toHaveText(/รอคิว|กำลังประมวลผล/);
	await expect(page.getByText('%')).toHaveCount(0);

	await expect(page.getByTestId('processing-done')).toBeVisible({ timeout: 15_000 });
	await expect(page.getByTestId('count-correct')).toHaveText('22');
	await expect(page.getByTestId('count-incorrect')).toHaveText('2');
	await expect(page.getByTestId('count-uncertain')).toHaveText('2');
	await expect(page.getByTestId('verdict')).toContainText('พบปุ่มที่อยู่ผิดตำแหน่ง 2 ช่อง');
	await expect(page.getByText('ทุกปุ่มถูกต้อง')).toHaveCount(0);
	await expect(page.getByText('ผลจำลอง')).toBeVisible();
	await expect(page.getByTestId('suggestions')).toContainText('สลับปุ่มในช่อง A กับช่อง S');
	await expect(page.getByTestId('warnings')).toContainText('โมเดลทดลอง');

	const overlay = page.getByTestId('result-overlay');
	await expect(overlay.locator('g[data-slot-id]')).toHaveCount(26);
	await expect(overlay.locator('g[data-status=incorrect]')).toHaveCount(2);
	await expect(overlay.locator('g[data-source=layout]')).toHaveCount(1);
	const list = page.getByTestId('slot-list');
	await expect(list).toContainText('ช่อง A: ควรเป็น A / พบ S');
	await expect(list).toContainText('ช่อง S: ควรเป็น S / พบ A');

	// Polygons stay aligned with the image: the Q polygon centre sits on the Q key centre.
	const ob = (await overlay.boundingBox())!;
	const qb = (await overlay.locator('g[data-slot-id=r0c0] polygon').first().boundingBox())!;
	expect(Math.abs(qb.x + qb.width / 2 - (ob.x + REF.Q[0] * ob.width))).toBeLessThan(
		ob.width * 0.02
	);
	expect(Math.abs(qb.y + qb.height / 2 - (ob.y + REF.Q[1] * ob.height))).toBeLessThan(
		ob.height * 0.03
	);
	await noHorizontalScroll(page);

	// Tapping a polygon selects its list row.
	await overlay.locator('g[data-slot-id=r1c1]').dispatchEvent('click');
	await expect(list.locator('button[data-slot-id=r1c1]')).toHaveAttribute('aria-pressed', 'true');
});

test('crossing reference points are blocked before submit', async ({ page, isMobile }) => {
	await uploadFixture(page);
	await tapAll(page, [REF.Q, REF.P, REF.Z, REF.M], isMobile);
	await expect(page.getByTestId('quad-error')).toContainText('ไขว้');
	await expect(page.getByRole('button', { name: 'ส่งตรวจ' })).toBeDisabled();

	// Undo the last point, tap the correct one -> valid.
	await page.getByRole('button', { name: 'ย้อนกลับหนึ่งขั้น' }).click();
	await page.getByRole('button', { name: 'ย้อนกลับหนึ่งขั้น' }).click();
	await expect(page.getByTestId('corner-surface').locator('[data-handle]')).toHaveCount(2);
	await tapAll(page, [REF.M, REF.Z], isMobile, 4);
	await expect(page.getByTestId('quad-error')).toHaveCount(0);
	await expect(page.getByRole('button', { name: 'ส่งตรวจ' })).toBeEnabled();

	await page.getByRole('button', { name: 'ล้างจุดทั้งหมด' }).click();
	await expect(page.getByTestId('corner-surface').locator('[data-handle]')).toHaveCount(0);
	await expect(page.getByTestId('picker-instruction')).toContainText('จุดที่ 1/4');
});

test('keyboard: place and nudge points, select slots', async ({ page, isMobile }) => {
	test.skip(isMobile, 'keyboard flow is desktop only');
	await uploadFixture(page);
	const surface = page.getByTestId('corner-surface');
	await surface.focus();
	await page.keyboard.press('Enter');
	const h0 = surface.locator('[data-handle="0"]');
	await expect(h0).toBeFocused();
	const before = await h0.getAttribute('style');
	await page.keyboard.press('Shift+ArrowRight');
	await expect.poll(() => h0.getAttribute('style')).not.toBe(before);

	await page.getByRole('button', { name: 'ล้างจุดทั้งหมด' }).click();
	await tapAll(page, [REF.Q, REF.P, REF.M, REF.Z], false);
	await page.getByRole('button', { name: 'ส่งตรวจ' }).click();
	await expect(page.getByTestId('processing-done')).toBeVisible({ timeout: 15_000 });

	const list = page.getByTestId('slot-list');
	const first = list.locator('button[data-slot-id]').first();
	await first.focus();
	await page.keyboard.press('Enter');
	await expect(first).toHaveAttribute('aria-pressed', 'true');
	const firstId = await first.getAttribute('data-slot-id');
	await expect(
		page.getByTestId('result-overlay').locator(`g[data-slot-id=${firstId}]`)
	).toHaveAttribute('data-selected', 'true');

	await page.keyboard.press('ArrowDown');
	const second = list.locator('button[data-slot-id]').nth(1);
	await expect(second).toBeFocused();
	await page.keyboard.press(' ');
	await expect(second).toHaveAttribute('aria-pressed', 'true');
	await expect(first).toHaveAttribute('aria-pressed', 'false');
});

test('mobile: dragging a point does not scroll the page', async ({ page, isMobile }) => {
	test.skip(!isMobile, 'touch only');
	await uploadFixture(page);
	await tapAll(page, [REF.Q, REF.P, REF.M, REF.Z], true);
	const surface = page.getByTestId('corner-surface');
	expect(await surface.evaluate((el) => getComputedStyle(el).touchAction)).toBe('none');
	expect(
		await page.evaluate(() => document.documentElement.scrollHeight > window.innerHeight)
	).toBe(true);

	await surface.scrollIntoViewIfNeeded();
	const handle = surface.locator('[data-handle="2"]');
	const hb = (await handle.boundingBox())!;
	const styleBefore = await handle.getAttribute('style');
	const scrollBefore = await page.evaluate(() => window.scrollY);

	const cdp = await page.context().newCDPSession(page);
	const x = hb.x + hb.width / 2;
	const y = hb.y + hb.height / 2;
	await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
	for (let i = 1; i <= 8; i++) {
		await cdp.send('Input.dispatchTouchEvent', {
			type: 'touchMove',
			touchPoints: [{ x: x - i * 4, y: y + i * 8 }]
		});
	}
	await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });

	await expect.poll(() => handle.getAttribute('style')).not.toBe(styleBefore);
	expect(await page.evaluate(() => window.scrollY)).toBe(scrollBefore);
});

test('camera permission denied falls back to file input', async ({ page }) => {
	await page.addInitScript(() => {
		navigator.mediaDevices.getUserMedia = () =>
			Promise.reject(new DOMException('denied', 'NotAllowedError'));
	});
	await page.goto('/');
	await page.getByRole('button', { name: 'เปิดกล้องถ่ายภาพ' }).click();
	await expect(page.getByRole('alert')).toContainText('ไม่ได้รับสิทธิ์ใช้กล้อง');
	await expect(page.getByRole('button', { name: 'เปิดกล้องถ่ายภาพ' })).toHaveCount(0);
	const capture = page.locator('input[type=file][capture=environment]');
	await expect(capture).toHaveCount(1);
	await capture.setInputFiles(FIXTURE);
	await expect(page.getByTestId('local-preview')).toBeVisible();
});

test('no MediaDevices: no camera button, file input still works', async ({ page }) => {
	await page.addInitScript(() => {
		Object.defineProperty(navigator, 'mediaDevices', { get: () => undefined });
	});
	await page.goto('/');
	await expect(page.getByText('เปิดกล้องในหน้าเว็บไม่ได้')).toBeVisible();
	await expect(page.getByRole('button', { name: 'เปิดกล้องถ่ายภาพ' })).toHaveCount(0);
	await page.locator('input[type=file]:not([capture])').setInputFiles(FIXTURE);
	await expect(page.getByTestId('local-preview')).toBeVisible();
});

test('camera allowed: capture a frame, tracks are stopped', async ({ page, context }) => {
	await context.grantPermissions(['camera']);
	await page.addInitScript(() => {
		const orig = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
		const w = window as unknown as { __streams: MediaStream[] };
		w.__streams = [];
		navigator.mediaDevices.getUserMedia = async (c) => {
			const s = await orig(c);
			w.__streams.push(s);
			return s;
		};
	});
	await page.goto('/');
	await page.getByRole('button', { name: 'เปิดกล้องถ่ายภาพ' }).click();
	const shoot = page.getByRole('button', { name: 'ถ่ายภาพ', exact: true });
	await expect(shoot).toBeEnabled();
	await expect
		.poll(() => page.locator('video').evaluate((v: HTMLVideoElement) => v.videoWidth))
		.toBeGreaterThan(0);
	await shoot.click();
	await expect(page.getByTestId('local-preview')).toBeVisible();
	const live = await page.evaluate(() =>
		(window as unknown as { __streams: MediaStream[] }).__streams
			.flatMap((s) => s.getTracks())
			.filter((t) => t.readyState === 'live')
			.length.valueOf()
	);
	expect(live).toBe(0);
});

test('HEIC is rejected with a clear message', async ({ page }) => {
	await page.goto('/');
	await page.locator('input[type=file]:not([capture])').setInputFiles({
		name: 'IMG_0001.HEIC',
		mimeType: 'image/heic',
		buffer: Buffer.from('not really heic')
	});
	await expect(page.getByTestId('file-error')).toContainText('HEIC');
	await expect(page.getByTestId('local-preview')).toHaveCount(0);
});

test('retake clears the preview before upload', async ({ page }) => {
	await chooseFixture(page);
	await page.getByRole('button', { name: /ถ่ายใหม่/ }).click();
	await expect(page.getByTestId('local-preview')).toHaveCount(0);
	await expect(page.locator('input[type=file]:not([capture])')).toHaveCount(1);
});

test('LAYOUT_MISMATCH: advises re-tapping, re-calibration starts with no points', async ({
	page,
	isMobile
}) => {
	await page.addInitScript(() =>
		sessionStorage.setItem('keycheck.mockScenario', 'layout_mismatch')
	);
	await runToResult(page, isMobile);
	const rejected = page.getByTestId('rejected');
	await expect(rejected).toBeVisible({ timeout: 15_000 });
	await expect(rejected).toContainText('แตะจุดอ้างอิงผิดช่อง');
	await expect(rejected).toContainText('อาจไม่ใช่แถวเยื้องมาตรฐาน');
	await expect(page.getByTestId('count-correct')).toHaveCount(0);
	await rejected.getByRole('link', { name: 'แตะจุดอ้างอิงใหม่' }).click();
	await expect(page).toHaveURL(/\/inspect\?image=img_/);
	await expect(page.getByTestId('corner-surface').locator('[data-handle]')).toHaveCount(0);
	await expect(page.getByTestId('picker-instruction')).toContainText('จุดที่ 1/4');
});

test('all correct: says so, with the layout-fit warning', async ({ page, isMobile }) => {
	await page.addInitScript(() => sessionStorage.setItem('keycheck.mockScenario', 'all_correct'));
	await runToResult(page, isMobile);
	await expect(page.getByTestId('verdict')).toContainText('ทุกปุ่มถูกต้อง', { timeout: 15_000 });
	await expect(page.getByTestId('count-correct')).toHaveText('26');
	await expect(page.getByTestId('warnings')).toContainText('ระบบตรวจไม่ได้ว่าแตะจุดอ้างอิงถูกช่อง');
});

test('network drop during polling recovers and shows the result', async ({ page, isMobile }) => {
	await page.addInitScript(() => sessionStorage.setItem('keycheck.mockScenario', 'flaky_poll'));
	await runToResult(page, isMobile);
	await expect(page.getByTestId('processing-done')).toBeVisible({ timeout: 25_000 });
});

test('double submit creates one job; history lists it', async ({ page, isMobile }) => {
	await uploadFixture(page);
	await tapAll(page, [REF.Q, REF.P, REF.M, REF.Z], isMobile);
	const submit = page.getByRole('button', { name: 'ส่งตรวจ' });
	await submit.dblclick();
	await expect(page).toHaveURL(/\/inspections\/ins_/);
	await page.getByRole('link', { name: 'ประวัติ' }).click();
	await expect(page.getByTestId('history-list').locator('li')).toHaveCount(1);
});
