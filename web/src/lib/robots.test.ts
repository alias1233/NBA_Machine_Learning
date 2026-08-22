// @ts-expect-error The site intentionally carries no Node type package for this Node-only test.
import { readFileSync } from 'node:fs';

function check(what: string, actual: unknown, expected: unknown) {
	if (JSON.stringify(actual) !== JSON.stringify(expected)) {
		throw new Error(`${what}\n  expected ${JSON.stringify(expected)}\n  got      ${JSON.stringify(actual)}`);
	}

	console.log(`ok   ${what}`);
}

const policy: string = readFileSync(new URL('../../static/robots.txt', import.meta.url), 'utf8');
const lines = policy.split(/\r?\n/);
const allowLines = lines.flatMap((line: string, index: number) =>
	line === 'Allow: /' ? [index] : []
);

check('the public policy has allowed crawler groups', allowLines.length > 0, true);

for (const line of allowLines) {
	const nextDirective = lines
		.slice(line + 1)
		.find((value: string) => value && !value.startsWith('#'));
	check(
		`allowed crawler group at line ${line + 1} blocks model query strings`,
		nextDirective,
		'Disallow: /models/*?'
	);
}

check(
	'ordinary model pages are not covered by a broader model rule',
	[...new Set(lines.filter((line: string) => line.startsWith('Disallow: /models/')))],
	['Disallow: /models/*?']
);

console.log('\nAll robots policy checks passed.');
