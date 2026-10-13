import {
	axisAt,
	axisSpan,
	axisTicks,
	calculateOdds,
	chartRange,
	defaultLine,
	expectedValue,
	figureText,
	highestValue,
	mostLikelyOutcomes,
	oddsPercentages,
	outcomeOf,
	outcomes,
	readAnswer,
	sharePercentages,
	valueAt
} from './odds.ts';

import type { Distribution, LineOdds } from './odds.ts';
import type { Prediction } from './types.ts';

function check(what: string, actual: unknown, expected: unknown) {
	const [got, wanted] = [JSON.stringify(actual), JSON.stringify(expected)];

	if (got !== wanted) throw new Error(`${what}\n  expected ${wanted}\n  got      ${got}`);

	console.log(`ok   ${what}`);
}

const round = (value: number) => Math.round(value * 1e6) / 1e6;

const rounded = (odds: LineOdds) => ({
	over: round(odds.over),
	under: round(odds.under),
	push: round(odds.push)
});

const probabilities = [0.1, 0.15, 0.4, 0.25, 0.1];

const over = (minimumValue: number, bucketWidth = 1): Distribution => ({
	minimumValue,
	bucketWidth,
	impossibleValue: null,
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

const buckets = over(10, 3);

check('a bucket is named by the run it covers', outcomes(buckets).map(({ label }) => label), [
	'10 to 12',
	'13 to 15',
	'16 to 18',
	'19 to 21',
	'22 to 24'
]);

check('a bucket averages as its middle', round(expectedValue(buckets)), 17.3);
check('and reaches as far as its last whole number', highestValue(buckets), 24);

check('a line between two buckets is a plain sum', rounded(calculateOdds(buckets, 15.5)), {
	over: 0.75,
	under: 0.25,
	push: 0
});

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

check('a drawn run of buckets spans every step it covers', axisSpan(buckets, { first: 1, last: 3 }), {
	from: 2.5,
	to: 11.5
});

check('and a run of single values spans one each', axisSpan(over(10), { first: 1, last: 3 }), {
	from: 0.5,
	to: 3.5
});

const margin: Distribution = {
	minimumValue: -6,
	bucketWidth: 3,
	impossibleValue: 0,
	probabilities: [0.1, 0.15, 0.4, 0.25, 0.1]
};

check('an impossible value is left out of the buckets either side of it', outcomes(margin).map(({ label }) => label), [
	'-6 to -4',
	'-3 to -1',
	'1 to 3',
	'4 to 6',
	'7 to 9'
]);

check('and the range reaches one further to hold the same count', highestValue(margin), 9);

check('a bucket either side of it averages as its own middle', round(expectedValue(margin)), 2.05);

check('the value itself is never landed on', rounded(calculateOdds(margin, 0)), {
	over: 0.75,
	under: 0.25,
	push: 0
});

check('and neither half number beside it settles differently', [-0.5, 0.5].map((line) => rounded(calculateOdds(margin, line))), [
	{ over: 0.75, under: 0.25, push: 0 },
	{ over: 0.75, under: 0.25, push: 0 }
]);

check('a whole number line above it still pushes at its share of a bucket', rounded(calculateOdds(margin, 2)), {
	over: round(0.35 + 0.4 / 3),
	under: round(0.25 + 0.4 / 3),
	push: round(0.4 / 3)
});

check('the axis skips the value the model cannot answer with', [-6, -1, 0, 1, 9].map((value) => axisAt(margin, value)), [0, 5, 5.5, 6, 14]);

check('and half a step either side of the gap lands on the gap', [-0.5, 0.5].map((value) => axisAt(margin, value)), [5.5, 5.5]);

check('reading the axis back gives the value, and the gap gives the value it stands for', [0, 5, 5.5, 6, 14].map((axis) => valueAt(margin, axis)), [-6, -1, 0, 1, 9]);

check('a line in the gap names both buckets it sits between', chartRange(margin, 0, 0.15), {
	first: 1,
	last: 2
});

check('a figure on a statistic that can run below zero carries its sign', [5.64, -5.64, 0.04, -0.04, 0].map((value) => figureText(margin, value)), ['+5.6', '-5.6', '0.0', '0.0', '0.0']);

check('and one that cannot is written plain', [5.64, 0].map((value) => figureText(over(0), value)), ['5.6', '0.0']);

check('a result opens on the half number below what is expected', defaultLine(23.1), 23.5);
check('and on the same one from above it', defaultLine(23.7), 23.5);

const spread: Distribution = {
	minimumValue: 0,
	bucketWidth: 1,
	impossibleValue: null,
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

check('a rolling push reads as itself rather than as nothing', oddsPercentages({ over: 0.5, under: 0.3, push: 0.2 }), {
	over: '50.0',
	under: '30.0',
	push: '20.0'
});

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

const answered = (output: Prediction['output'], values: number[]): Prediction => ({
	model: 'test',
	output,
	values,
	past_games: 30
});

check(
	'a whole number answer is read as a distribution',
	readAnswer(answered({ kind: 'integer_distribution', minimum_value: 10, outcomes: 2, bucket_width: 1, impossible_value: null }, [0.4, 0.6])),
	{
		kind: 'integer_distribution',
		distribution: { minimumValue: 10, bucketWidth: 1, impossibleValue: null, probabilities: [0.4, 0.6] }
	}
);

check(
	'and carries how wide a bucket is',
	readAnswer(answered({ kind: 'integer_distribution', minimum_value: 10, outcomes: 2, bucket_width: 3, impossible_value: null }, [0.4, 0.6])),
	{
		kind: 'integer_distribution',
		distribution: { minimumValue: 10, bucketWidth: 3, impossibleValue: null, probabilities: [0.4, 0.6] }
	}
);

check(
	'and which value the model can never answer with',
	readAnswer(answered({ kind: 'integer_distribution', minimum_value: -6, outcomes: 2, bucket_width: 3, impossible_value: 0 }, [0.4, 0.6])),
	{
		kind: 'integer_distribution',
		distribution: { minimumValue: -6, bucketWidth: 3, impossibleValue: 0, probabilities: [0.4, 0.6] }
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
