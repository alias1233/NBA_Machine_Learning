/**
 * Reading a predicted distribution: the value it expects, and the odds it gives a line.
 *
 * The only place this arithmetic lives. A prediction is a probability for every whole number
 * outcome, so every question about a line is a sum over an array the page already holds. The service
 * sends the distribution and nothing else, and no request is needed to answer a new line.
 */

export type Outcome = {
	value: number;
	probability: number;
};

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
 * The three odds as percentages to one decimal, rounded so that the ones shown still read as a
 * hundred.
 *
 * Rounding each on its own leaves 99.9 or 100.1 on the page. Whatever the rounding down left over is
 * handed to the figures it cut by the most.
 */
export function oddsPercentages(odds: LineOdds, line: number): OddsText {
	const push = hasPush(line) ? odds.push : 0;
	const total = odds.over + odds.under + push;
	const exact = [odds.over, odds.under, push].map((part) => (total > 0 ? part / total : 0) * 1000);
	const tenths = exact.map(Math.floor);

	const byRemainder = [0, 1, 2].sort((a, b) => exact[b] - tenths[b] - (exact[a] - tenths[a]));
	let spare = 1000 - tenths.reduce((running, part) => running + part, 0);

	for (const index of byRemainder) {
		if (spare <= 0) break;

		tenths[index] += 1;
		spare -= 1;
	}

	const written = (value: number) => (value / 10).toFixed(1);

	return { over: written(tenths[0]), under: written(tenths[1]), push: written(tenths[2]) };
}
