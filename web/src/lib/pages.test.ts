import { familyInfoPath, familyPath, MODEL_FAMILIES } from './models.ts';
import { INDEXED_PAGES, NEWEST_UPDATE, datesOf } from './pages.ts';

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

// A family added without dating its two pages is a family missing from the sitemap, which is the
// one failure here that nothing else on the site would report.
check(
	'both pages of every model family are offered',
	MODEL_FAMILIES.flatMap((family) =>
		[familyPath(family), familyInfoPath(family)].filter((path) => datesOf(path) === undefined)
	),
	[]
);

check(
	'the newest date is the newest a page carries',
	INDEXED_PAGES.filter(({ updated }) => updated > NEWEST_UPDATE),
	[]
);

console.log('\nAll indexed page checks passed.');
