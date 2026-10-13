import { gamesMatching } from './games.ts';

import type { ScheduledGame } from './types.ts';

const game = (id: number, away: [string, string], home: [string, string]): ScheduledGame => ({
	id,
	date: '2026-01-14',
	tipoff: null,
	away_team: { abbreviation: away[0], name: away[1] },
	home_team: { abbreviation: home[0], name: home[1] },
	season_type: 'REGULAR_SEASON',
	is_mock: false
});

const board = [
	game(1, ['LAL', 'Los Angeles Lakers'], ['DEN', 'Denver Nuggets']),
	game(2, ['MIL', 'Milwaukee Bucks'], ['BOS', 'Boston Celtics']),
	game(3, ['DEN', 'Denver Nuggets'], ['LAC', 'Los Angeles Clippers'])
];

function check(what: string, search: string, expected: number[]) {
	const got = gamesMatching(board, search).map((match) => match.id);

	if (got.join() !== expected.join()) {
		throw new Error(`${what}\n  expected ${expected.join() || '(none)'}\n  got      ${got.join() || '(none)'}`);
	}

	console.log(`ok   ${what}`);
}

check('an empty search is not a filter', '', [1, 2, 3]);
check('whitespace alone is not a filter', '   ', [1, 2, 3]);
check('a name finds every game the team plays', 'nuggets', [1, 3]);
check('a tricode reads the same as a name', 'lac', [3]);
check('case is not asked about', 'BUCKS', [2]);
check('both sides named is the one game between them', 'lakers nuggets', [1]);
check('a city names both of its teams', 'los angeles', [1, 3]);
check('a matchup that is not on the board finds nothing', 'bucks nuggets', []);

if (gamesMatching(board, '') !== board) throw new Error('an empty search should hand the board back');

console.log('\nAll game board checks passed.');
