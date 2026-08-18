/**
 * Checks what `showcase.ts` will and will not let the home page draw.
 *
 * The hero is the one surface that has to render whatever the service hands it, and everything it
 * refuses is refused here rather than by failing on the page. Two of these matter more than the
 * rest: a sample carrying no numbers must never reach the drawing, and a set nobody rebuilt must
 * stop offering games that have already been played.
 *
 * Run with `npm test`. Node reads the TypeScript directly, so there is nothing to install.
 */

import { drawableSamples, isDrawable, isUpcoming } from './showcase.ts';

import type { Showcase, ShowcaseSample } from './types.ts';

function check(what: string, actual: unknown, expected: unknown) {
	const [got, wanted] = [JSON.stringify(actual), JSON.stringify(expected)];

	if (got !== wanted) throw new Error(`${what}\n  expected ${wanted}\n  got      ${got}`);

	console.log(`ok   ${what}`);
}

const NOON = Date.parse('2026-08-17T12:00:00Z');

const sample = (fields: Partial<ShowcaseSample> = {}): ShowcaseSample =>
	({
		family: 'player_stats',
		model: 'points',
		title: 'Points',
		predicts: ['points'],
		output: {
			kind: 'integer_distribution',
			minimum_value: 0,
			outcomes: 4,
			bucket_width: 1,
			impossible_value: null
		},
		values: [0.1, 0.4, 0.3, 0.2],
		past_games: 240,
		game: {
			date: '2026-08-18',
			home_team: { abbreviation: 'LAL', name: 'Los Angeles Lakers' },
			away_team: { abbreviation: 'DEN', name: 'Denver Nuggets' },
			season_type: 'REGULAR_SEASON',
			tipoff: '2026-08-19T02:00:00Z'
		},
		player: { id: 1, name: 'Nikola Jokic' },
		team: { abbreviation: 'DEN', name: 'Denver Nuggets' },
		read_from: null,
		...fields
	}) as ShowcaseSample;

const categories = (fields: Partial<ShowcaseSample> = {}) =>
	sample({
		output: {
			kind: 'category_distribution',
			categories: ['home win', 'away win']
		},
		values: [0.6, 0.4],
		...fields
	});

// What a whole sample looks like when nothing is wrong with it.

check('a whole sample is drawn', isDrawable(sample()), true);
check('and so is one answering in named categories', isDrawable(categories()), true);
check(
	'a statistic belonging to the game names nobody',
	isDrawable(sample({ player: null, team: null })),
	true
);

// A job that stopped half way through, and a file written by something that has moved on.

check('a sample with no numbers is not drawn', isDrawable(sample({ values: [] })), false);
check(
	'and neither is one whose numbers are all nothing',
	isDrawable(sample({ values: [0, 0, 0, 0] })),
	false
);
check('a chance below zero is not a chance', isDrawable(sample({ values: [0.5, -0.5] })), false);
check(
	'and neither is one that is not a number',
	isDrawable(sample({ values: [0.5, null] as never })),
	false
);
check(
	'more categories than chances would print one against nothing',
	isDrawable(categories({ values: [1] })),
	false
);
check(
	'a shape the site has no reading for is not offered',
	isDrawable(sample({ output: { kind: 'values', quantities: ['points'] } })),
	false
);
check('a sample with no model behind it is not drawn', isDrawable(sample({ model: '' })), false);
check('nor one with nothing to say it predicts', isDrawable(sample({ predicts: [] })), false);
check(
	'nor one that cannot say how many games it rests on',
	isDrawable(sample({ past_games: Number.NaN })),
	false
);
check(
	'nor one whose game names no side',
	isDrawable(
		sample({
			game: { ...sample().game, away_team: { abbreviation: '', name: '' } }
		})
	),
	false
);
check(
	'a bucket has to be a whole number of outcomes wide',
	isDrawable(
		sample({
			output: {
				kind: 'integer_distribution',
				minimum_value: 0,
				outcomes: 4,
				bucket_width: 0,
				impossible_value: null
			}
		})
	),
	false
);

// A set nobody rebuilt. The plate is tonight's slate, so a game already played is the one thing on
// it that would be untrue rather than merely stale.

const gameOn = (date: string, tipoff: string | null) => ({
	...sample().game,
	date,
	tipoff
});

check(
	'a game still to tip off is upcoming',
	isUpcoming(gameOn('2026-08-17', '2026-08-18T00:00:00Z'), NOON),
	true
);
check(
	'one that has tipped off is not',
	isUpcoming(gameOn('2026-08-17', '2026-08-17T11:00:00Z'), NOON),
	false
);
check(
	'a tip-off with no zone written on it is read as UTC',
	isUpcoming(gameOn('2026-08-17', '2026-08-17T11:00:00'), NOON),
	false
);
check(
	'with no tip-off, a game keeps its day out to the end of it everywhere',
	isUpcoming(gameOn('2026-08-17', null), NOON),
	true
);
check(
	'and is over once the next day has started in UTC',
	isUpcoming(gameOn('2026-08-16', null), NOON),
	false
);
check(
	'a date nothing can be read from is not upcoming',
	isUpcoming(gameOn('soon', null), NOON),
	false
);

// The whole set, which is what the loader asks for.

const published = (samples: ShowcaseSample[]): Showcase => ({
	format_version: 1,
	built_for: '2026-08-17',
	built_at: '2026-08-17T09:00:00Z',
	samples
});

check('nothing published draws nothing', drawableSamples(null, NOON), []);
check(
	'a set keeps only what is whole and still ahead',
	drawableSamples(
		published([
			sample({ model: 'kept' }),
			sample({ model: 'empty', values: [] }),
			sample({
				model: 'played',
				game: gameOn('2026-08-16', '2026-08-16T23:00:00Z')
			})
		]),
		NOON
	).map(({ model }) => model),
	['kept']
);
check(
	'a set that loses every sample is the same as no set at all',
	drawableSamples(published([sample({ values: [] })]), NOON),
	[]
);

console.log('\nAll showcase checks passed.');
