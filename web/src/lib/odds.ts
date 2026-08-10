/**
 * Reading a predicted answer: the value it expects, the odds it gives a line, and the share each
 * named category holds.
 *
 * The only place this arithmetic lives. Every question about a line is a sum over an array the page
 * already holds, so no request is needed to answer a new line.
 */

import type { ModelOutput, Prediction } from '$lib/types';

export type Outcome = {
	value: number;
	probability: number;
};

/** A probability per whole number outcome, counting up from `minimumValue`. */
export type Distribution = {
	minimumValue: number;
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
			distribution: { minimumValue: output.minimum_value, probabilities: values }
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

/** Each probability paired with the outcome it stands for. */
export function outcomes(probabilities: number[], minimumValue = 0): Outcome[] {
	return probabilities.map((probability, offset) => ({ value: minimumValue + offset, probability }));
}

/** The average outcome the distribution implies. */
export function expectedValue(probabilities: number[], minimumValue = 0): number {
	return probabilities.reduce(
		(total, probability, offset) => total + (minimumValue + offset) * probability,
		0
	);
}

export function calculateOdds(
	probabilities: number[],
	line: number,
	minimumValue = 0
): LineOdds {
	const odds: LineOdds = { over: 0, under: 0, push: 0 };

	for (const { value, probability } of outcomes(probabilities, minimumValue)) {
		if (value > line) odds.over += probability;
		else if (value < line) odds.under += probability;
		else odds.push += probability;
	}

	return odds;
}

/** The count outcomes the model gives the most weight to, likeliest first. */
export function mostLikelyOutcomes(
	probabilities: number[],
	count: number,
	minimumValue = 0
): Outcome[] {
	return outcomes(probabilities, minimumValue)
		.sort((a, b) => b.probability - a.probability)
		.slice(0, count);
}

/** The line a result opens on, which is the half number nearest what the model expects. */
export const defaultLine = (expected: number) => Math.floor(expected) + 0.5;

/**
 * The smallest continuous run of outcomes holding `coverage` of the probability, widened to hold
 * `include`.
 *
 * A points model has 60 outcomes and most of them are empty tail. Drawing all of them on a phone
 * gives four pixel bars of nothing, so the chart draws this run instead.
 */
export function chartRange(
	probabilities: number[],
	minimumValue = 0,
	include: number | null = null,
	coverage = 0.995
): { first: number; last: number } {
	let best: [number, number] = [0, Math.max(0, probabilities.length - 1)];
	let start = 0;
	let held = 0;

	for (let end = 0; end < probabilities.length; end++) {
		held += probabilities[end];

		while (held - probabilities[start] >= coverage) held -= probabilities[start++];

		if (held >= coverage && end - start < best[1] - best[0]) best = [start, end];
	}

	const highest = minimumValue + probabilities.length - 1;
	let [first, last] = [minimumValue + best[0], minimumValue + best[1]];

	if (include !== null) {
		first = Math.min(first, Math.max(minimumValue, Math.floor(include)));
		last = Math.max(last, Math.min(highest, Math.ceil(include)));
	}

	return { first, last };
}

/** Only a whole number line can be landed on exactly, so a half number pushes with 0.0 percent. */
const hasPush = (line: number) => Number.isInteger(line);

/** The three odds written as percentages to one decimal. */
export type OddsText = Record<keyof LineOdds, string>;

/**
 * Parts of one whole as percentages to one decimal, rounded so that the figures shown still read as
 * a hundred.
 *
 * Rounding each on its own leaves 99.9 or 100.1 on the page. Whatever the rounding down left over is
 * handed to the figures it cut by the most.
 */
export function sharePercentages(parts: number[]): string[] {
	const total = parts.reduce((running, part) => running + part, 0);
	const exact = parts.map((part) => (total > 0 ? part / total : 0) * 1000);
	const tenths = exact.map(Math.floor);

	const byRemainder = parts
		.map((_, index) => index)
		.sort((a, b) => exact[b] - tenths[b] - (exact[a] - tenths[a]));
	let spare = 1000 - tenths.reduce((running, part) => running + part, 0);

	for (const index of byRemainder) {
		if (spare <= 0) break;

		tenths[index] += 1;
		spare -= 1;
	}

	return tenths.map((value) => (value / 10).toFixed(1));
}

/** The three odds as percentages to one decimal, summing to a hundred as shown. */
export function oddsPercentages(odds: LineOdds, line: number): OddsText {
	const [over, under, push] = sharePercentages([
		odds.over,
		odds.under,
		hasPush(line) ? odds.push : 0
	]);

	return { over, under, push };
}
