// @ts-expect-error The site intentionally carries no Node type package for this Node-only test.
import { readFileSync } from 'node:fs';

import { SITE_ORIGIN } from './site.ts';

function check(what: string, actual: unknown, expected: unknown) {
	if (JSON.stringify(actual) !== JSON.stringify(expected)) {
		throw new Error(`${what}\n  expected ${JSON.stringify(expected)}\n  got      ${JSON.stringify(actual)}`);
	}

	console.log(`ok   ${what}`);
}

/**
 * What every allowed crawler group is refused, in the order the file writes it.
 *
 * A model page's query string is a prediction, which is a page per combination and none of them
 * worth indexing. The proxy routes under `/api/` are the browser's way to the service and nothing
 * links to them, so a crawler reaching one only costs the service a call. The two health routes
 * answer anyone, have no title between them, and are read by the container and the proxy rather
 * than by a reader.
 */
const BLOCKED = [
	'Disallow: /models/*?',
	'Disallow: /api/',
	'Disallow: /health',
	'Disallow: /healthz'
];

/**
 * What a parser reads as a crawler's name: letters, digits, underscore and hyphen, or the
 * catch-all. A space, a dot or a slash ends the name there, so a value carrying one is a group
 * named something other than what the file appears to say.
 */
const PRODUCT_TOKEN = /^(\*|[A-Za-z0-9_-]+)$/;

const policy: string = readFileSync(new URL('../../static/robots.txt', import.meta.url), 'utf8');
const rawLines = policy.split(/\r?\n/);
const lines = rawLines.map((line: string) => line.trim());
const directives = (from: number) =>
	lines.slice(from).filter((value: string) => value !== '' && !value.startsWith('#'));

const allowLines = lines.flatMap((line: string, index: number) =>
	line === 'Allow: /' ? [index] : []
);

check('the public policy has allowed crawler groups', allowLines.length > 0, true);

for (const line of allowLines) {
	check(
		`allowed crawler group at line ${line + 1} blocks what nothing links to`,
		directives(line + 1).slice(0, BLOCKED.length),
		BLOCKED
	);
}

// A value with a space, a slash or a version in it is read as far as its first odd character and
// no further, so a group named that way is one whose name the file and the crawler disagree on.
const userAgents = lines.flatMap((line: string) =>
	line.startsWith('User-agent:') ? [line.slice('User-agent:'.length).trim()] : []
);

check('the policy names crawlers', userAgents.length > 0, true);

check(
	'every crawler is named by a product token and nothing else',
	userAgents.filter((value: string) => !PRODUCT_TOKEN.test(value)),
	[]
);

// A group is separated from the next by an empty line. A line holding one space is not one, and a
// parser is free to read the two groups it separates as one.
check(
	'nothing in the policy is a line of whitespace',
	rawLines.flatMap((line: string, index: number) =>
		line !== '' && line.trim() === '' ? [index + 1] : []
	),
	[]
);

check(
	'ordinary model pages are not covered by a broader model rule',
	[...new Set(lines.filter((line: string) => line.startsWith('Disallow: /models/')))],
	['Disallow: /models/*?']
);

check(
	'the site pages are not covered by a broader api rule',
	[...new Set(lines.filter((line: string) => line.startsWith('Disallow: /api')))],
	['Disallow: /api/']
);

// The domain is written here and in site.ts, and a sitemap advertising a name the pages do not
// claim as their canonical one is a name search engines are asked to index and never shown.
check(
	'the sitemap line names the origin the pages are built with',
	lines.filter((line: string) => line.startsWith('Sitemap:')),
	[`Sitemap: ${SITE_ORIGIN}/sitemap.xml`]
);

console.log('\nAll robots policy checks passed.');
