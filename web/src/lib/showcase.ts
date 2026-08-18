/**
 * What a published sample set is worth drawing.
 *
 * The home page is the one page that has to render whatever the service hands it, so nothing here
 * throws and nothing here takes a field on trust. A job that was interrupted half way through
 * writing, a set drawn against an older version of a model than the one answering now, and a set
 * nobody has rebuilt since the games in it were played are all ordinary rather than exceptional.
 * Each of them reads here as a sample the page leaves out, and a set that loses every one of its
 * samples is the same empty plate as a day with nothing to draw.
 *
 * It is all arithmetic and checking, so `npm test` reads it directly rather than the page having to
 * be loaded to find out. See `python/src/nba_ml/showcase.py` for what writes the set.
 */

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

/** Whether the numbers read as chances: present, real, none of them negative, and not all zero. */
function areChances(values: unknown): values is number[] {
	if (!Array.isArray(values) || values.length === 0) return false;
	if (!values.every((value) => isNumber(value) && value >= 0)) return false;

	return values.reduce((total: number, value: number) => total + value, 0) > 0;
}

/**
 * Whether a sample carries everything the plate reads off it.
 *
 * Only what is actually drawn is checked. The count of outcomes a model declares is not, because
 * the numbers themselves are the run of outcomes and a drawing takes its bars from them, so a
 * disagreement there costs the reader nothing. A set of category names that has moved on from the
 * numbers beside it is checked, because that one prints a chance against nothing.
 */
export function isDrawable(sample: ShowcaseSample): boolean {
	if (!sample || typeof sample !== 'object') return false;

	const { game, output, player, team, values } = sample;

	if (!isText(sample.family) || !isText(sample.model) || !isText(sample.title)) return false;
	if (!Array.isArray(sample.predicts) || sample.predicts.length === 0) return false;
	if (!sample.predicts.every(isText)) return false;
	if (!isNumber(sample.past_games) || sample.past_games < 0) return false;

	if (!game || !isText(game.date)) return false;
	if (!isTeam(game.home_team) || !isTeam(game.away_team)) return false;

	// Whose number it is. Absent is a whole meaning of its own, which is a statistic belonging to the
	// game rather than to anybody, so only a subject that is there has to be named.
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

/**
 * Whether a game has yet to start, which is what makes a sample of it still worth showing.
 *
 * The hero is tonight's slate. A set nobody rebuilt would otherwise go on offering last week's
 * games as though they were ahead, which is the one thing on this page that would be untrue rather
 * than merely stale.
 */
export function isUpcoming(game: ShowcaseSample['game'], now: number): boolean {
	if (isText(game.tipoff)) {
		const at = utcMoment(game.tipoff);

		if (!Number.isNaN(at)) return at > now;
	}

	// No tip-off to read, so the calendar day is all there is. That day is a United States eastern
	// one, which runs up to five hours behind UTC, so it is only certainly over once the next one is.
	const midnight = Date.parse(`${game.date}T00:00:00Z`);

	return !Number.isNaN(midnight) && midnight + DAY_MS > now;
}

/** The samples of a published set still worth drawing, in the order the job wrote them. */
export function drawableSamples(published: Showcase | null, now: number): ShowcaseSample[] {
	if (!published || !Array.isArray(published.samples)) return [];

	return published.samples.filter((sample) => isDrawable(sample) && isUpcoming(sample.game, now));
}
