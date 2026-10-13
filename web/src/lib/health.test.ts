// @ts-expect-error Node types are not installed. This test only runs in Node.
import { readFileSync } from 'node:fs';

function check(what: string, actual: unknown, expected: unknown) {
	if (JSON.stringify(actual) !== JSON.stringify(expected)) {
		throw new Error(`${what}\n  expected ${JSON.stringify(expected)}\n  got      ${JSON.stringify(actual)}`);
	}

	console.log(`ok   ${what}`);
}

const caddyfile: string = readFileSync(
	new URL('../../../deploy/Caddyfile', import.meta.url),
	'utf8'
).replace(/\r\n/g, '\n');
const health = caddyfile.search(/handle \/health\s*\{\s*reverse_proxy api:8000\s*\}/);
const site = caddyfile.search(/handle\s*\{\s*reverse_proxy web:3000\s*\}/);

check('health is routed to the uncapped API endpoint', health >= 0, true);
check('the site catch-all still routes to SvelteKit', site >= 0, true);
check('the health route is declared before the catch-all', health < site, true);

console.log('\nAll health route checks passed.');
