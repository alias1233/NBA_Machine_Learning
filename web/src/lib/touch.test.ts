import { isTap } from './touch.ts';

function check(what: string, actual: unknown, expected: unknown) {
	if (actual !== expected) throw new Error(`${what}\n  expected ${expected}\n  got      ${actual}`);

	console.log(`ok   ${what}`);
}

check('a finger lifted near where it landed is a tap', isTap({ x: 2, y: 3 }, { clientX: 8, clientY: 8 }), true);
check('a finger that travels farther is a scroll', isTap({ x: 0, y: 0 }, { clientX: 11, clientY: 0 }), false);

console.log('\nAll touch checks passed.');
