/**
 * Checks `odds.ts` against answers small enough to work out by hand.
 *
 * Nothing else checks this arithmetic. The service sends a distribution and every figure a reader
 * reads off it is worked out here, so this is the only thing standing behind those numbers.
 *
 * Run with `npm test`. Node reads the TypeScript directly, so there is nothing to install.
 */

import {
	axisTicks,
	calculateOdds,
	chartRange,
	defaultLine,
	expectedValue,
	highestValue,
	mostLikelyOutcomes,
	oddsPercentages,
	outcomeOf,
	outcomes,
	readAnswer,
	sharePercentages,
	valueSpan
} from './odds.ts';

import type { Distribution, LineOdds } from './odds.ts';
import type { Prediction } from './types.ts';

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

/** A chance per whole number, over 0 to 4, small enough to check every answer below by hand. */
const probabilities = [0.1, 0.15, 0.4, 0.25, 0.1];

const over = (minimumValue: number, bucketWidth = 1): Distribution => ({
	minimumValue,
	bucketWidth,
	probabilities
});

check('expected value', round(expectedValue(over(0))), 2.1);
check('expected value counts from the minimum', round(expectedValue(over(10))), 12.1);

check('a half point line leaves nothing on it', rounded(calculateOdds(over(0), 2.5)), {
	over: 0.35,
	under: 0.65,
	push: 0
});

check('a whole number line can be landed on', rounded(calculateOdds(over(0), 2)), {
	over: 0.35,
	under: 0.25,
	push: 0.4
});

check('the minimum shifts which outcome a line cuts', rounded(calculateOdds(over(10), 12)), {
	over: 0.35,
	under: 0.25,
	push: 0.4
});

for (const line of [-1, 0, 2, 2.5, 4, 99]) {
	const odds = calculateOdds(over(0), line);

	check(`the three ways line ${line} settles add up to one`, round(odds.over + odds.under + odds.push), 1);
}

check('the likeliest outcomes come back in order', mostLikelyOutcomes(over(0), 3).map(({ value, probability }) => ({ value, probability })), [
	{ value: 2, probability: 0.4 },
	{ value: 3, probability: 0.25 },
	{ value: 1, probability: 0.15 }
]);

check('ranking leaves the given array alone', probabilities, [0.1, 0.15, 0.4, 0.25, 0.1]);

// The same five chances, each now covering three whole numbers: 10 to 12, 13 to 15, and so on.
// Everything a reader reads off one of these has to stay true when a bucket holds more than one.
const buckets = over(10, 3);

check('a bucket is named by the run it covers', outcomes(buckets).map(({ label }) => label), [
	'10 to 12',
	'13 to 15',
	'16 to 18',
	'19 to 21',
	'22 to 24'
]);

// The middles are 11, 14, 17, 20 and 23.
check('a bucket averages as its middle', round(expectedValue(buckets)), 17.3);
check('and reaches as far as its last whole number', highestValue(buckets), 24);

check('a line between two buckets is a plain sum', rounded(calculateOdds(buckets, 15.5)), {
	over: 0.75,
	under: 0.25,
	push: 0
});

// The bucket holding 16 to 18 is worth 0.4, so each of those three numbers is worth a third of it.
check('a line inside one splits it evenly across the numbers it holds', rounded(calculateOdds(buckets, 16.5)), {
	over: round(0.35 + (0.4 / 3) * 2),
	under: round(0.25 + 0.4 / 3),
	push: 0
});

check('a whole number line inside a bucket pushes at its share of it', rounded(calculateOdds(buckets, 17)), {
	over: round(0.35 + 0.4 / 3),
	under: round(0.25 + 0.4 / 3),
	push: round(0.4 / 3)
});

for (const line of [-5, 10, 16.5, 17, 24, 99]) {
	const odds = calculateOdds(buckets, line);

	check(`the three ways bucketed line ${line} settles add up to one`, round(odds.over + odds.under + odds.push), 1);
}

check('a value names the bucket holding it', [9, 10, 12, 13, 24, 40].map((value) => outcomeOf(buckets, value)), [0, 0, 0, 1, 4, 4]);

// Each bucket owns three whole numbers of the axis, so the drawn run reaches half a number past the
// first and last it holds. This is what places a line by its value alone at any width.
check('a drawn run of buckets spans every number it covers', valueSpan(buckets, { first: 1, last: 3 }), {
	from: 12.5,
	to: 21.5
});

check('and a run of single values spans one each', valueSpan(over(10), { first: 1, last: 3 }), {
	from: 10.5,
	to: 13.5
});

check('a result opens on the half number below what is expected', defaultLine(23.1), 23.5);
check('and on the same one from above it', defaultLine(23.7), 23.5);

// A hundred outcomes where a run of five holds 99.6% of them, so that run is the only answer. The
// range comes back as positions in the answer, not as values, because that is what the chart slices.
const spread: Distribution = {
	minimumValue: 0,
	bucketWidth: 1,
	probabilities: Array.from({ length: 100 }, (_, value) =>
		value >= 40 && value < 45 ? 0.1992 : 0.004 / 95
	)
};

check('the chart draws the run holding the mass', chartRange(spread), { first: 40, last: 44 });
check('and widens to hold a line outside it', chartRange(spread, 60.5), { first: 40, last: 61 });

check('a line at the edge cannot widen past the outcomes', chartRange(spread, 500), {
	first: 40,
	last: 99
});

check('counting from a minimum does not move the positions', chartRange({ ...spread, minimumValue: 10 }), {
	first: 40,
	last: 44
});

// 200.5 falls between the bucket holding 198 to 200 and the one holding 201 to 203, so both are
// drawn and the line lands on the edge between them.
check('and a bucketed run widens to the buckets a line sits between', chartRange({ ...spread, bucketWidth: 3 }, 200.5), {
	first: 40,
	last: 67
});

check('the three shown odds are rounded to a hundred', oddsPercentages(calculateOdds(over(0), 2)), {
	over: '35.0',
	under: '25.0',
	push: '40.0'
});

check('a half line pushes at nothing and the pair still reads as a hundred', oddsPercentages(calculateOdds(over(0), 2.5)), {
	over: '35.0',
	under: '65.0',
	push: '0.0'
});

// A figure part way through rolling towards its new value. All three are read together, so a
// reading taken mid-roll still adds up to a hundred rather than rescaling the two beside it.
check('a rolling push reads as itself rather than as nothing', oddsPercentages({ over: 0.5, under: 0.3, push: 0.2 }), {
	over: '50.0',
	under: '30.0',
	push: '20.0'
});

// Thirds round down to 33.3 each and leave a tenth over, which has to land somewhere.
const thirds = oddsPercentages({ over: 1 / 3, under: 1 / 3, push: 1 / 3 });
const summed = Number(thirds.over) + Number(thirds.under) + Number(thirds.push);

check('a figure that does not divide still sums to a hundred', round(summed), 100);

check('two shares are rounded to a hundred', sharePercentages([0.158, 0.842]), ['15.8', '84.2']);

const sevenths = sharePercentages(Array.from({ length: 7 }, () => 1 / 7));
const sevenSummed = sevenths.reduce((running, share) => running + Number(share), 0);

check('and so is any other count of them', round(sevenSummed), 100);

check('a share can be read to a further place', sharePercentages([0.0026, 0.9974], 2), [
	'0.26',
	'99.74'
]);

const finerThirds = sharePercentages(Array.from({ length: 3 }, () => 1 / 3), 2);
const finerSummed = finerThirds.reduce((running, share) => running + Number(share), 0);

check('and still reads as a hundred at that place', round(finerSummed), 100);

// The axis a larger chart is drawn against. The top clears the tallest bar so its figure fits over
// it, and every mark is a round step.
const axis = axisTicks(0.062);

check('the axis tops out above the tallest bar', axis.top > 0.062, true);
check('and marks it in round steps', { step: axis.step, marks: axis.values.length }, {
	step: 0.02,
	marks: 5
});

check('the tallest bar keeps room for a figure over it', 0.062 / axis.top < 0.9, true);

const wideAxis = axisTicks(0.25);

check('a taller answer takes a larger step', round(wideAxis.step), 0.1);
check('and the last mark is the top', round(wideAxis.values.at(-1)!), round(wideAxis.top));

// The two shapes the site draws, and one it does not.
const answered = (output: Prediction['output'], values: number[]): Prediction => ({
	model: 'test',
	output,
	values,
	past_games: 30
});

check(
	'a whole number answer is read as a distribution',
	readAnswer(answered({ kind: 'integer_distribution', minimum_value: 10, outcomes: 2, bucket_width: 1 }, [0.4, 0.6])),
	{
		kind: 'integer_distribution',
		distribution: { minimumValue: 10, bucketWidth: 1, probabilities: [0.4, 0.6] }
	}
);

check(
	'and carries how wide a bucket is',
	readAnswer(answered({ kind: 'integer_distribution', minimum_value: 10, outcomes: 2, bucket_width: 3 }, [0.4, 0.6])),
	{
		kind: 'integer_distribution',
		distribution: { minimumValue: 10, bucketWidth: 3, probabilities: [0.4, 0.6] }
	}
);

check(
	'a named answer keeps the order the model listed',
	readAnswer(answered({ kind: 'category_distribution', categories: ['yes', 'no'] }, [0.2, 0.8])),
	{ kind: 'category_distribution', categories: { names: ['yes', 'no'], probabilities: [0.2, 0.8] } }
);

check(
	'a shape with no reading is turned away rather than half drawn',
	readAnswer(answered({ kind: 'values', quantities: ['minutes'] }, [31.4])),
	null
);

console.log('\nAll odds checks passed.');
