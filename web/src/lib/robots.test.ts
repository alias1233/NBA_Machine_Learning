// @ts-expect-error Node types are not installed. This test only runs in Node.
import { readFileSync } from 'node:fs';

import { SITE_ORIGIN } from './site.ts';

function check(what: string, actual: unknown, expected: unknown) {
	if (JSON.stringify(actual) !== JSON.stringify(expected)) {
		throw new Error(`${what}\n  expected ${JSON.stringify(expected)}\n  got      ${JSON.stringify(actual)}`);
	}

	console.log(`ok   ${what}`);
}

/** Disallow rules every allowed crawler group must have, in file order. */
const BLOCKED = [
	'Disallow: /models/*?',
	'Disallow: /api/',
	'Disallow: /health',
	'Disallow: /healthz'
];

/** Pattern for a valid crawler name. */
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

const userAgents = lines.flatMap((line: string) =>
	line.startsWith('User-agent:') ? [line.slice('User-agent:'.length).trim()] : []
);

check('the policy names crawlers', userAgents.length > 0, true);

check(
	'every crawler is named by a product token and nothing else',
	userAgents.filter((value: string) => !PRODUCT_TOKEN.test(value)),
	[]
);

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

check(
	'the sitemap line names the origin the pages are built with',
	lines.filter((line: string) => line.startsWith('Sitemap:')),
	[`Sitemap: ${SITE_ORIGIN}/sitemap.xml`]
);

console.log('\nAll robots policy checks passed.');
