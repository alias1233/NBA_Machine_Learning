/*
 * Contrast check for the palette in docs/WEBSITE_DESIGN_DOCUMENT.md section 3.
 *
 * Run with `node web/scripts/contrast.mjs`. It reads the two theme tables below, not app.css, so
 * update both together. Text pairs must clear 4.5 to 1 and control edges 3 to 1. Anything that
 * fails prints FAIL and the script exits non-zero.
 *
 * See rule R0.7. Re-run this and paste the figures into section 3 whenever a colour changes.
 */

const LIGHT = {
	page: '#F8F5EE',
	panel: '#EAE2D2',
	block: '#22201C',
	'block-ink': '#F5F1E8',
	'block-muted': '#B0A896',
	surface: '#FFFDF9',
	'surface-sunken': '#D9CFBA',
	ink: '#1C1A16',
	'ink-muted': '#5C574B',
	hairline: '#E3DCCC',
	'hairline-panel': '#D6CDB9',
	'hairline-block': '#3A362E',
	'control-border': '#6B6559',
	accent: '#A83C1E',
	'accent-on': '#FFFFFF',
	'accent-block': '#E9A177',
	over: '#0B6845',
	under: '#B01D57',
	'warn-wash': '#F8EDD6',
	'warn-border': '#DFC79B',
	'chart-neutral': '#8A8375'
};

const DARK = {
	page: '#141311',
	panel: '#26231C',
	block: '#EDE7D9',
	'block-ink': '#1C1A16',
	'block-muted': '#5C574B',
	surface: '#1A1815',
	'surface-sunken': '#312D25',
	ink: '#F0EBDF',
	'ink-muted': '#A69E8C',
	hairline: '#2E2B24',
	'hairline-panel': '#3D392F',
	'hairline-block': '#CFC7B4',
	'control-border': '#807969',
	accent: '#E28B5C',
	'accent-on': '#141311',
	'accent-block': '#A83C1E',
	over: '#4BCF9A',
	under: '#F072B0',
	'warn-wash': '#2A2211',
	'warn-border': '#5C4A1D',
	'chart-neutral': '#807969'
};

// Text must clear 4.5 to 1. Every foreground paired with every plane it is allowed to sit on.
const TEXT = [
	['ink', 'page'],
	['ink', 'panel'],
	['ink', 'surface'],
	['ink', 'surface-sunken'],
	['ink', 'warn-wash'],
	['ink-muted', 'page'],
	['ink-muted', 'panel'],
	['ink-muted', 'surface'],
	['ink-muted', 'surface-sunken'],
	['accent', 'page'],
	['accent', 'panel'],
	['accent', 'surface'],
	['accent-on', 'accent'],
	['block-ink', 'block'],
	['block-muted', 'block'],
	['accent-block', 'block'],
	['over', 'surface'],
	['over', 'panel'],
	['under', 'surface'],
	['under', 'panel']
];

// A control edge or a chart shape must clear 3 to 1.
const SHAPE = [
	['control-border', 'surface'],
	['control-border', 'panel'],
	['control-border', 'page'],
	['control-border', 'surface-sunken'],
	['chart-neutral', 'surface']
];

// Reported for judgement, no minimum. Plane separation and the hairlines against their own plane.
const INFO = [
	['panel', 'page'],
	['block', 'page'],
	['surface', 'block'],
	['surface', 'panel'],
	['surface-sunken', 'panel'],
	['hairline', 'page'],
	['hairline-panel', 'panel'],
	['hairline-block', 'block'],
	['warn-border', 'warn-wash'],
	['over', 'under']
];

function luminance(hex) {
	const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
	const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a, b) {
	const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m);
	return (x + 0.05) / (y + 0.05);
}

let failed = 0;

function report(title, pairs, floor) {
	console.log(`\n=== ${title}${floor ? ` (floor ${floor})` : ''} ===`);

	for (const [fg, bg] of pairs) {
		const light = ratio(LIGHT[fg], LIGHT[bg]);
		const dark = ratio(DARK[fg], DARK[bg]);

		const bad = floor
			? [
					['light', light],
					['dark', dark]
				]
					.filter(([, r]) => r < floor)
					.map(([n]) => n)
			: [];

		failed += bad.length;

		const row = `${fg} on ${bg}`.padEnd(38);
		const flag = bad.length ? `   <-- FAIL ${bad.join(', ')}` : '';

		console.log(`${row} light ${light.toFixed(2).padStart(6)}   dark ${dark.toFixed(2).padStart(6)}${flag}`);
	}
}

report('Text', TEXT, 4.5);
report('Shapes and control edges', SHAPE, 3);
report('Separation, no floor', INFO, null);

console.log(failed ? `\n${failed} pair(s) below the floor.` : '\nAll pairs clear their floor.');

process.exit(failed ? 1 : 0);
