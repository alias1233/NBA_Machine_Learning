/**
 * Checks `odds.ts` against answers small enough to work out by hand.
 *
 * Nothing else checks this arithmetic. The service sends a distribution and every figure a reader
 * reads off it is worked out here, so this is the only thing standing behind those numbers.
 *
 * Run with `npm test`. Node reads the TypeScript directly, so there is nothing to install.
 */

import {
	calculateOdds,
	chartRange,
	defaultLine,
	expectedValue,
	mostLikelyOutcomes,
	oddsPercentages
} from './odds.ts';

import type { LineOdds } from './odds.ts';

function check(what: string, actual: unknown, expected: unknown) {
	const [got, wanted] = [JSON.stringify(actual), JSON.stringify(expected)];

	if (got !== wanted) throw new Error(`${what}\n  expected ${wanted}\n  got      ${got}`);

	console.log(`ok   ${what}`);
}

/** Sums of floats do not land on round numbers, so every comparison is made at six places. */
const round = (value: number) => Math.round(value * 1e6) / 1e6;

const rounded = (odds: LineOdds) => ({
	over: round(odds.over),
	under: round(odds.under),
	push: round(odds.push)
});

// A distribution over 0 to 4, small enough that every answer below can be checked by hand.
const probabilities = [0.1, 0.15, 0.4, 0.25, 0.1];

check('expected value', round(expectedValue(probabilities)), 2.1);
check('expected value counts from the minimum', round(expectedValue(probabilities, 10)), 12.1);

check('a half point line leaves nothing on it', rounded(calculateOdds(probabilities, 2.5)), {
	over: 0.35,
	under: 0.65,
	push: 0
});

check('a whole number line can be landed on', rounded(calculateOdds(probabilities, 2)), {
	over: 0.35,
	under: 0.25,
	push: 0.4
});

check('the minimum shifts which outcome a line cuts', rounded(calculateOdds(probabilities, 12, 10)), {
	over: 0.35,
	under: 0.25,
	push: 0.4
});

for (const line of [-1, 0, 2, 2.5, 4, 99]) {
	const odds = calculateOdds(probabilities, line);

	check(`the three ways line ${line} settles add up to one`, round(odds.over + odds.under + odds.push), 1);
}

check('the likeliest outcomes come back in order', mostLikelyOutcomes(probabilities, 3), [
	{ value: 2, probability: 0.4 },
	{ value: 3, probability: 0.25 },
	{ value: 1, probability: 0.15 }
]);

check('ranking leaves the given array alone', probabilities, [0.1, 0.15, 0.4, 0.25, 0.1]);

check('a result opens on the half number below what is expected', defaultLine(23.1), 23.5);
check('and on the same one from above it', defaultLine(23.7), 23.5);

// A hundred outcomes where a run of five holds 99.6% of them, so that run is the only answer.
const spread = Array.from({ length: 100 }, (_, value) =>
	value >= 40 && value < 45 ? 0.1992 : 0.004 / 95
);

check('the chart draws the run holding the mass', chartRange(spread), { first: 40, last: 44 });
check('and widens to hold a line outside it', chartRange(spread, 0, 60.5), { first: 40, last: 61 });
check('and counts from the minimum', chartRange(spread, 10), { first: 50, last: 54 });

check('a line at the edge cannot widen past the outcomes', chartRange(spread, 0, 500), {
	first: 40,
	last: 99
});

check('the three shown odds are rounded to a hundred', oddsPercentages(calculateOdds(probabilities, 2), 2), {
	over: '35.0',
	under: '25.0',
	push: '40.0'
});

check('a half line pushes at nothing and the pair still reads as a hundred', oddsPercentages(calculateOdds(probabilities, 2.5), 2.5), {
	over: '35.0',
	under: '65.0',
	push: '0.0'
});

// Thirds round down to 33.3 each and leave a tenth over, which has to land somewhere.
const thirds = oddsPercentages({ over: 1 / 3, under: 1 / 3, push: 1 / 3 }, 2);
const summed = Number(thirds.over) + Number(thirds.under) + Number(thirds.push);

check('a figure that does not divide still sums to a hundred', round(summed), 100);

console.log('\nAll odds checks passed.');
