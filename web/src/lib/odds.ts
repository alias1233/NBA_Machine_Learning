/**
 * Reading a predicted answer: the value it expects, the odds it gives a line, and the share each
 * named category holds.
 *
 * The only place this arithmetic lives. Every question about a line is a sum over an array the page
 * already holds, so no request is needed to answer a new line.
 */

import type { ModelOutput, Prediction } from '$lib/types';

/**
 * One thing the model can answer, and the chance it gives it.
 *
 * An outcome covers a run of whole numbers. Usually that run is one number, and where a model
 * answers in buckets it is as many as the bucket holds.
 */
export type Outcome = {
	/** The middle of the run, which is where it sits on the value axis and what it averages as. */
	value: number;
	lowest: number;
	highest: number;
	probability: number;
	/** What a reader sees: "21", or "88 to 90" where the run holds more than one number. */
	label: string;
};

/**
 * A probability per bucket of whole numbers, counting up from `minimumValue`.
 *
 * `bucketWidth` is how many whole numbers one probability covers. At one this is a chance per whole
 * number, which is what every player model answers with. Above one the model is saying it cannot
 * tell those numbers apart, so anything asked inside a bucket reads it as spread evenly across it.
 */
export type Distribution = {
	minimumValue: number;
	bucketWidth: number;
	probabilities: number[];
};

/** A probability per named category, most notable first, with no order and no line to read against. */
export type CategoryAnswer = {
	names: string[];
	probabilities: number[];
};

/**
 * An answer in a shape the site can draw. Adding a shape is a member here and a reading beside the
 * two already built.
 */
export type Answer =
	| { kind: 'integer_distribution'; distribution: Distribution }
	| { kind: 'category_distribution'; categories: CategoryAnswer };

export type AnswerKind = Answer['kind'];

export const DRAWN_KINDS: ModelOutput['kind'][] = ['integer_distribution', 'category_distribution'];
/** The shapes a reading exists for. A model answering any other way is never offered. */

/** What an answer holds, or null when the model does not answer in a shape the site draws. */
export function readAnswer(prediction: Prediction): Answer | null {
	const { output, values } = prediction;

	if (output.kind === 'integer_distribution') {
		return {
			kind: output.kind,
			distribution: {
				minimumValue: output.minimum_value,
				bucketWidth: output.bucket_width,
				probabilities: values
			}
		};
	}

	if (output.kind === 'category_distribution') {
		return { kind: output.kind, categories: { names: output.categories, probabilities: values } };
	}

	return null;
}

/** The three ways a line can settle. They add up to one. */
export type LineOdds = {
	over: number;
	under: number;
	/** The chance of landing exactly on the line, which only a whole number line can do. */
	push: number;
};

/** The lowest and highest whole numbers the model can answer with. */
export const lowestValue = (distribution: Distribution) => distribution.minimumValue;

export const highestValue = ({ minimumValue, bucketWidth, probabilities }: Distribution) =>
	minimumValue + probabilities.length * bucketWidth - 1;

/** Which outcome a value falls in. Anything past either end is that end, which is how it was fit. */
export function outcomeOf(distribution: Distribution, value: number): number {
	const offset = Math.floor((value - distribution.minimumValue) / distribution.bucketWidth);

	return Math.min(Math.max(offset, 0), distribution.probabilities.length - 1);
}

/** Each probability paired with the outcome it stands for. */
export function outcomes({
	minimumValue,
	bucketWidth,
	probabilities
}: Distribution): Outcome[] {
	return probabilities.map((probability, offset) => {
		const lowest = minimumValue + offset * bucketWidth;
		const highest = lowest + bucketWidth - 1;

		return {
			value: (lowest + highest) / 2,
			lowest,
			highest,
			probability,
			label: lowest === highest ? String(lowest) : `${lowest} to ${highest}`
		};
	});
}

/** The average outcome the distribution implies. */
export function expectedValue(distribution: Distribution): number {
	return outcomes(distribution).reduce(
		(total, { value, probability }) => total + value * probability,
		0
	);
}

/**
 * The three ways a line settles.
 *
 * A line falling inside an outcome splits it. The model said nothing about where inside that run the
 * answer sits, so the run is read as spread evenly over the whole numbers it holds. Where an outcome
 * is one whole number, which is every player model, that is the plain sum either side of the line.
 */
export function calculateOdds(distribution: Distribution, line: number): LineOdds {
	const odds: LineOdds = { over: 0, under: 0, push: 0 };

	for (const { lowest, highest, probability } of outcomes(distribution)) {
		if (lowest > line) {
			odds.over += probability;
			continue;
		}

		if (highest < line) {
			odds.under += probability;
			continue;
		}

		const share = probability / (highest - lowest + 1);

		for (let value = lowest; value <= highest; value++) {
			if (value > line) odds.over += share;
			else if (value < line) odds.under += share;
			else odds.push += share;
		}
	}

	return odds;
}

/** The outcomes the model gives the most weight to, likeliest first. */
export function mostLikelyOutcomes(distribution: Distribution, count: number): Outcome[] {
	return outcomes(distribution)
		.sort((a, b) => b.probability - a.probability)
		.slice(0, count);
}

/** The line a result opens on, which is the half number nearest what the model expects. */
export const defaultLine = (expected: number) => Math.floor(expected) + 0.5;

/** A run of outcomes to draw, as positions in the answer rather than as values. */
export type ChartRange = { first: number; last: number };

/** The stretch of the number line a run of outcomes covers, from the outer edge of each end. */
export type ValueSpan = { from: number; to: number };

/**
 * The smallest continuous run of outcomes holding `coverage` of the probability, widened to hold
 * `include`.
 *
 * A points model has 60 outcomes and most of them are empty tail. Drawing all of them on a phone
 * gives four pixel bars of nothing, so the chart draws this run instead.
 *
 * `include` is a value, usually the chosen line, and the run is widened to the outcomes it falls
 * between so the line is always drawn over the bars it splits.
 */
export function chartRange(
	distribution: Distribution,
	include: number | null = null,
	coverage = 0.995
): ChartRange {
	const { probabilities } = distribution;
	let best: [number, number] = [0, Math.max(0, probabilities.length - 1)];
	let start = 0;
	let held = 0;

	for (let end = 0; end < probabilities.length; end++) {
		held += probabilities[end];

		while (held - probabilities[start] >= coverage) held -= probabilities[start++];

		if (held >= coverage && end - start < best[1] - best[0]) best = [start, end];
	}

	let [first, last] = best;

	if (include !== null) {
		first = Math.min(first, outcomeOf(distribution, Math.floor(include)));
		last = Math.max(last, outcomeOf(distribution, Math.ceil(include)));
	}

	return { first, last };
}

/**
 * Where a drawn run starts and ends on the number line.
 *
 * Each outcome owns its own share of the axis, so the edges sit half a whole number outside the
 * first and last numbers drawn. That is what lets a line be placed by its value alone, at any
 * bucket width.
 */
export function valueSpan(distribution: Distribution, range: ChartRange): ValueSpan {
	const { minimumValue, bucketWidth } = distribution;

	return {
		from: minimumValue + range.first * bucketWidth - 0.5,
		to: minimumValue + (range.last + 1) * bucketWidth - 0.5
	};
}

/** How much of the chart's height the tallest bar takes, which leaves its figure room above it. */
const AXIS_HEADROOM = 0.85;

/**
 * A rounded top for a chart's probability axis, the step between its marks, and the values marked
 * on the way up to it.
 *
 * The top is a round step above the tallest bar rather than the bar itself, so the marks read as
 * whole figures and the tallest bar has room to carry one over it.
 */
export function axisTicks(
	tallest: number,
	marks = 4
): { top: number; step: number; values: number[] } {
	const reach = tallest / AXIS_HEADROOM;
	const rough = reach / marks;
	const magnitude = 10 ** Math.floor(Math.log10(rough || 1));
	const step = ([1, 2, 2.5, 5].find((size) => size * magnitude >= rough) ?? 10) * magnitude;

	// Counted rather than stepped, because adding a fraction repeatedly drifts off the top it is
	// meant to land on.
	const steps = Math.max(Math.ceil(reach / step), 1);

	return {
		top: steps * step,
		step,
		values: Array.from({ length: steps + 1 }, (_, mark) => mark * step)
	};
}

/** The three odds written as percentages to one decimal. */
export type OddsText = Record<keyof LineOdds, string>;

/**
 * A named category is read to one place further than a line's odds. A yes or no answer usually sits
 * close to a hundred or to nothing, so the digit that carries the answer is the one after the point.
 */
export const CATEGORY_DECIMALS = 2;

/**
 * Parts of one whole as percentages, rounded so that the figures shown still read as a hundred.
 *
 * Rounding each on its own leaves 99.9 or 100.1 on the page. Whatever the rounding down left over is
 * handed to the figures it cut by the most.
 */
export function sharePercentages(parts: number[], decimals = 1): string[] {
	const units = 100 * 10 ** decimals;
	const total = parts.reduce((running, part) => running + part, 0);
	const exact = parts.map((part) => (total > 0 ? part / total : 0) * units);
	const whole = exact.map(Math.floor);

	const byRemainder = parts
		.map((_, index) => index)
		.sort((a, b) => exact[b] - whole[b] - (exact[a] - whole[a]));
	let spare = units - whole.reduce((running, part) => running + part, 0);

	for (const index of byRemainder) {
		if (spare <= 0) break;

		whole[index] += 1;
		spare -= 1;
	}

	return whole.map((value) => (value / 10 ** decimals).toFixed(decimals));
}

/**
 * The three odds as percentages to one decimal, summing to a hundred as shown.
 *
 * Only the three numbers, because a half number line already pushes at nothing. Reading the line
 * here as well and zeroing push on it would take a rolling figure straight to zero while the other
 * two rolled, which is the one place these three can disagree with the chart beside them.
 */
export function oddsPercentages(odds: LineOdds): OddsText {
	const [over, under, push] = sharePercentages([odds.over, odds.under, odds.push]);

	return { over, under, push };
}
