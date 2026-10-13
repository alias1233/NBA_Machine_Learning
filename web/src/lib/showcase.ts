import { utcMoment } from './games.ts';
import { DRAWN_KINDS } from './odds.ts';

import type { Showcase, ShowcaseSample } from '$lib/types';

const DAY_MS = 24 * 60 * 60 * 1000;

const isText = (value: unknown): value is string =>
	typeof value === 'string' && value.trim() !== '';

const isNumber = (value: unknown): value is number =>
	typeof value === 'number' && Number.isFinite(value);

const isTeam = (team: unknown) => {
	const named = team as { abbreviation?: unknown; name?: unknown } | null;

	return !!named && isText(named.abbreviation) && isText(named.name);
};

/** Returns true if the values are valid probabilities. Not empty, all numbers, none negative and not all zero. */
function areChances(values: unknown): values is number[] {
	if (!Array.isArray(values) || values.length === 0) return false;
	if (!values.every((value) => isNumber(value) && value >= 0)) return false;

	return values.reduce((total: number, value: number) => total + value, 0) > 0;
}

/** Returns true if a sample has everything the home page needs to show it. */
export function isDrawable(sample: ShowcaseSample): boolean {
	if (!sample || typeof sample !== 'object') return false;

	const { game, output, player, team, values } = sample;

	if (!isText(sample.family) || !isText(sample.model) || !isText(sample.title)) return false;
	if (!Array.isArray(sample.predicts) || sample.predicts.length === 0) return false;
	if (!sample.predicts.every(isText)) return false;
	if (!isNumber(sample.past_games) || sample.past_games < 0) return false;

	if (!game || !isText(game.date)) return false;
	if (!isTeam(game.home_team) || !isTeam(game.away_team)) return false;

	if (player && !isText(player.name)) return false;
	if (team && !isText(team.name)) return false;

	if (!output || !DRAWN_KINDS.includes(output.kind)) return false;
	if (!areChances(values)) return false;

	if (output.kind === 'category_distribution') {
		return (
			Array.isArray(output.categories) &&
			output.categories.length === values.length &&
			output.categories.every(isText)
		);
	}

	if (output.kind !== 'integer_distribution') return false;

	return (
		Number.isInteger(output.minimum_value) &&
		Number.isInteger(output.bucket_width) &&
		output.bucket_width >= 1
	);
}

/** Returns true if a game has not started yet. */
export function isUpcoming(game: ShowcaseSample['game'], now: number): boolean {
	if (isText(game.tipoff)) {
		const at = utcMoment(game.tipoff);

		if (!Number.isNaN(at)) return at > now;
	}

	// Without a tipoff time, the game counts as upcoming until its date ends in UTC.
	const midnight = Date.parse(`${game.date}T00:00:00Z`);

	return !Number.isNaN(midnight) && midnight + DAY_MS > now;
}

/** Returns the published samples that are valid and still upcoming, in their original order. */
export function drawableSamples(published: Showcase | null, now: number): ShowcaseSample[] {
	if (!published || !Array.isArray(published.samples)) return [];

	return published.samples.filter((sample) => isDrawable(sample) && isUpcoming(sample.game, now));
}
