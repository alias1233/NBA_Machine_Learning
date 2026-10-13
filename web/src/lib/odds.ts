import type { ModelOutput, Prediction } from '$lib/types';

/** One possible outcome, covering a range of whole numbers, with its probability. */
export type Outcome = {
	/** Midpoint of the range. */
	value: number;
	lowest: number;
	highest: number;
	probability: number;
	/** Display text, such as "21" or "88 to 90". */
	label: string;
};

/** One probability per bucket of whole numbers, starting at `minimumValue`. */
export type Distribution = {
	minimumValue: number;
	/** Number of whole numbers each probability covers. */
	bucketWidth: number;
	/** A whole number the stat can never be, such as a point differential of zero. */
	impossibleValue: number | null;
	probabilities: number[];
};

/** One probability per named category, most notable first. */
export type CategoryAnswer = {
	names: string[];
	probabilities: number[];
};

export type Answer =
	| { kind: 'integer_distribution'; distribution: Distribution }
	| { kind: 'category_distribution'; categories: CategoryAnswer };

export type AnswerKind = Answer['kind'];

export const DRAWN_KINDS: ModelOutput['kind'][] = ['integer_distribution', 'category_distribution'];

/** Converts a prediction into an Answer, or returns null if the site cannot show that output type. */
export function readAnswer(prediction: Prediction): Answer | null {
	const { output, values } = prediction;

	if (output.kind === 'integer_distribution') {
		return {
			kind: output.kind,
			distribution: {
				minimumValue: output.minimum_value,
				bucketWidth: output.bucket_width,
				impossibleValue: output.impossible_value,
				probabilities: values
			}
		};
	}

	if (output.kind === 'category_distribution') {
		return { kind: output.kind, categories: { names: output.categories, probabilities: values } };
	}

	return null;
}

/** Probabilities of going over, under or exactly on a line. They add up to one. */
export type LineOdds = {
	over: number;
	under: number;
	/** Probability of landing exactly on the line. Only possible for a whole number line. */
	push: number;
};

/** Returns a value's position on the chart axis, counted from the lowest outcome. */
export function axisAt(distribution: Distribution, value: number): number {
	const { minimumValue, impossibleValue } = distribution;

	if (impossibleValue === null) return value - minimumValue;

	return value - minimumValue - Math.min(Math.max(value - impossibleValue + 0.5, 0), 1);
}

/** Returns the value at a position on the chart axis. The inverse of axisAt. */
export function valueAt(distribution: Distribution, axis: number): number {
	const { minimumValue, impossibleValue } = distribution;

	if (impossibleValue === null) return minimumValue + axis;

	const gap = impossibleValue - minimumValue - 0.5;

	if (axis < gap) return minimumValue + axis;

	return axis > gap ? minimumValue + axis + 1 : impossibleValue;
}

export const lowestValue = (distribution: Distribution) => distribution.minimumValue;

export const highestValue = (distribution: Distribution) =>
	valueAt(distribution, distribution.probabilities.length * distribution.bucketWidth - 1);

const outcomeAt = (distribution: Distribution, axis: number) =>
	Math.min(
		Math.max(Math.floor(axis / distribution.bucketWidth), 0),
		distribution.probabilities.length - 1
	);

/** Returns the index of the outcome a value falls in, clamped to the first and last outcome. */
export const outcomeOf = (distribution: Distribution, value: number) =>
	outcomeAt(distribution, axisAt(distribution, value));

export function outcomes(distribution: Distribution): Outcome[] {
	const { bucketWidth, probabilities } = distribution;

	return probabilities.map((probability, offset) => {
		const lowest = valueAt(distribution, offset * bucketWidth);
		const highest = valueAt(distribution, offset * bucketWidth + bucketWidth - 1);

		return {
			value: (lowest + highest) / 2,
			lowest,
			highest,
			probability,
			label: lowest === highest ? String(lowest) : `${lowest} to ${highest}`
		};
	});
}

export function expectedValue(distribution: Distribution): number {
	return outcomes(distribution).reduce(
		(total, { value, probability }) => total + value * probability,
		0
	);
}

/** Formats a value for display. Adds a plus sign only if the stat can be negative. */
export function figureText(distribution: Distribution, value: number, decimals = 1): string {
	const rounded = Number(value.toFixed(decimals));
	const signed = lowestValue(distribution) < 0 && rounded > 0;

	return `${signed ? '+' : ''}${rounded.toFixed(decimals)}`;
}

/** Calculates the over, under and push probabilities for a line. A bucket the line falls inside is treated as evenly spread. */
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

export function mostLikelyOutcomes(distribution: Distribution, count: number): Outcome[] {
	return outcomes(distribution)
		.sort((a, b) => b.probability - a.probability)
		.slice(0, count);
}

export const defaultLine = (expected: number) => Math.floor(expected) + 0.5;

/** Range of outcomes to show, as indexes and not values. */
export type ChartRange = { first: number; last: number };

/** Part of the axis a range of outcomes covers, measured from the outer edges. */
export type AxisSpan = { from: number; to: number };

/** Returns the smallest range that covers `coverage` of the probability, widened to contain `include`. */
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
		const at = axisAt(distribution, include);

		first = Math.min(first, outcomeAt(distribution, Math.floor(at)));
		last = Math.max(last, outcomeAt(distribution, Math.ceil(at)));
	}

	return { first, last };
}

export function axisSpan(distribution: Distribution, range: ChartRange): AxisSpan {
	const { bucketWidth } = distribution;

	return {
		from: range.first * bucketWidth - 0.5,
		to: (range.last + 1) * bucketWidth - 0.5
	};
}

/** Fraction of the chart height used by the tallest bar. */
const AXIS_HEADROOM = 0.85;

export function axisTicks(
	tallest: number,
	marks = 4
): { top: number; step: number; values: number[] } {
	const reach = tallest / AXIS_HEADROOM;
	const rough = reach / marks;
	const magnitude = 10 ** Math.floor(Math.log10(rough || 1));
	const step = ([1, 2, 2.5, 5].find((size) => size * magnitude >= rough) ?? 10) * magnitude;

	const steps = Math.max(Math.ceil(reach / step), 1);

	return {
		top: steps * step,
		step,
		values: Array.from({ length: steps + 1 }, (_, mark) => mark * step)
	};
}

export type OddsText = Record<keyof LineOdds, string>;

export const CATEGORY_DECIMALS = 2;

/** Converts parts of a whole to percentages, rounded so they still add up to 100. */
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

/** Returns the three odds as percentages with one decimal, adding up to 100. */
export function oddsPercentages(odds: LineOdds): OddsText {
	const [over, under, push] = sharePercentages([odds.over, odds.under, odds.push]);

	return { over, under, push };
}
