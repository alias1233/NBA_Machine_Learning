// @ts-expect-error The site intentionally carries no Node type package for this Node-only test.
import { readdirSync } from 'node:fs';

import { familyPath, MODEL_FAMILIES } from './models.ts';
import { INDEXED_PAGES, NEWEST_UPDATE, PAGES, datesOf, isIndexed } from './pages.ts';
import { robotsDirective } from './seo.ts';

function check(what: string, actual: unknown, expected: unknown) {
	if (JSON.stringify(actual) !== JSON.stringify(expected)) {
		throw new Error(`${what}\n  expected ${JSON.stringify(expected)}\n  got      ${JSON.stringify(actual)}`);
	}

	console.log(`ok   ${what}`);
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

check(
	'every indexed page is named by an absolute path',
	INDEXED_PAGES.filter(({ path }) => !path.startsWith('/')),
	[]
);

check(
	'no page is offered twice',
	INDEXED_PAGES.length - new Set(INDEXED_PAGES.map(({ path }) => path)).size,
	0
);

check(
	'every page carries two dates a sitemap can print',
	INDEXED_PAGES.filter(
		({ published, updated }) => !ISO_DATE.test(published) || !ISO_DATE.test(updated)
	),
	[]
);

check(
	'nothing claims to have changed before it existed',
	INDEXED_PAGES.filter(({ published, updated }) => updated < published).map(({ path }) => path),
	[]
);

// A family added without dating its page is a family missing from the sitemap, which is the one
// failure here that nothing else on the site would report.
check(
	'every model family is offered',
	MODEL_FAMILIES.map(familyPath).filter((path) => datesOf(path) === undefined),
	[]
);

check(
	'the newest date is the newest a page carries',
	INDEXED_PAGES.filter(({ updated }) => updated > NEWEST_UPDATE),
	[]
);

// ----------------------------------------------------------------------------
// WHAT IS INDEXED AND WHAT IS NOT
// ----------------------------------------------------------------------------

/**
 * The pages the site keeps out of the index. Today there are none.
 *
 * Written here rather than read off the entries, so that an entry flipped to `indexed: false` by
 * accident fails here rather than going unnoticed until a search result quietly disappears months
 * later. A page that genuinely should be held out is added to this list in the same change that
 * sets its flag.
 */
const NOT_INDEXED: string[] = [];

check(
	'exactly the declared pages are held out of the index',
	Object.keys(PAGES).filter((path) => !isIndexed(path)),
	NOT_INDEXED
);

check(
	'the sitemap offers every page that asks to be indexed, and nothing else',
	INDEXED_PAGES.map(({ path }) => path),
	Object.keys(PAGES).filter((path) => !NOT_INDEXED.includes(path))
);

// A sitemap only advertises. A page left out of one is still crawled, and still indexed if anything
// links to it, so the directive printed on the page is the half that decides. This holds it to the
// same entry the sitemap was built from, in both directions.
check(
	'every page tells a crawler what its entry says',
	Object.keys(PAGES).map((path) => robotsDirective(path).startsWith('index, follow')),
	Object.keys(PAGES).map((path) => isIndexed(path))
);

// ----------------------------------------------------------------------------
// EVERY RENDERED PAGE IS ACCOUNTED FOR
// ----------------------------------------------------------------------------

/**
 * The path of every route that renders a page, read off the routes themselves.
 *
 * A directory holding a `+page.svelte` is a page a reader can open. A directory holding only a
 * `+page.server.ts` is a redirect or an endpoint and is not one. Reading the tree rather than
 * listing the routes here is what makes a page added without an entry in pages.ts a failure: that
 * entry is the only place saying whether the page belongs in the sitemap and what it tells a
 * crawler.
 */
const renderedPaths = (dir: URL, path: string): string[] => {
	const entries: { name: string; isDirectory: () => boolean }[] = readdirSync(dir, {
		withFileTypes: true
	});
	const here = entries.some(({ name }) => name === '+page.svelte') ? [path || '/'] : [];

	return entries
		.filter((entry) => entry.isDirectory())
		.reduce(
			(paths: string[], { name }) =>
				paths.concat(renderedPaths(new URL(`${name}/`, dir), `${path}/${name}`)),
			here
		);
};

const RENDERED = renderedPaths(new URL('../routes/', import.meta.url), '');

check(
	'every page the site renders has an entry',
	RENDERED.filter((path) => datesOf(path) === undefined),
	[]
);

check(
	'every entry names a page the site renders',
	Object.keys(PAGES).filter((path) => !RENDERED.includes(path)),
	[]
);

console.log('\nAll indexed page checks passed.');
