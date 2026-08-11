/**
 * What every prediction page reads out of its address bar, and the words it answers a refusal with.
 *
 * Every family describes the game the same way, with the same four parameters, whether the reader
 * typed them or chose a card. A family adds only the parameters it alone needs, so this is the part
 * that never differs.
 */

import type { HttpError } from '@sveltejs/kit';
import type { ScheduledGame, SeasonType } from '$lib/types';

export const SEASON_TYPES: SeasonType[] = ['REGULAR_SEASON', 'PLAYOFFS', 'PLAY_IN', 'PRESEASON'];

/** The phase field's options, in the order a reader is most likely to want them. */
export const PHASES = [
	['REGULAR_SEASON', 'Regular season'],
	['PLAYOFFS', 'Playoffs'],
	['PLAY_IN', 'Play-in'],
	['PRESEASON', 'Preseason']
] as const;

export const UNREACHABLE = 'The prediction service is not reachable. Try again shortly.';
export const SAME_TEAM = 'A game needs two different teams.';
const REFUSED = 'The prediction could not be made. Try again shortly.';

/** The game being asked about, however the reader described it. */
export type GameChoice = {
	date: string;
	homeTeam: string;
	awayTeam: string;
	seasonType: SeasonType;
};

const today = () => new Date().toISOString().slice(0, 10);

export function readGameChoice(parameters: URLSearchParams): GameChoice {
	const seasonType = parameters.get('type') as SeasonType;

	return {
		date: parameters.get('date') || today(),
		homeTeam: parameters.get('home') || '',
		awayTeam: parameters.get('away') || '',
		seasonType: SEASON_TYPES.includes(seasonType) ? seasonType : SEASON_TYPES[0]
	};
}

/** Whether the described game is one of the upcoming ones, which is what a chosen card names. */
export const isGame = (game: ScheduledGame, choice: GameChoice) =>
	game.date === choice.date &&
	game.home_team.abbreviation === choice.homeTeam &&
	game.away_team.abbreviation === choice.awayTeam &&
	game.season_type === choice.seasonType;

/** Both sides named, which is what every prediction needs before it can be asked for. */
export const namesBothTeams = (choice: GameChoice) =>
	choice.homeTeam !== '' && choice.awayTeam !== '';

/** A line the reader shared. Anything that is not a number is dropped rather than argued with. */
export function readLine(parameters: URLSearchParams): number | null {
	const line = Number(parameters.get('line'));

	return parameters.has('line') && Number.isFinite(line) ? line : null;
}

/**
 * What each refusal the service names means to a reader.
 *
 * The service's own message states ids and is for a log. Only the reason crosses over, and the words
 * a reader sees are written here.
 */
const REASONS: Record<string, string> = {
	too_few_games: 'This player has no earlier game to read.',
	missing_player_information: 'Too little is known about this player to predict.',
	unknown_player_team: 'Say which of the two teams this player is on.',
	no_team_history: 'This team has no earlier game to read.'
};

export function reasonFor(thrown: HttpError): string {
	if (thrown.status === 503) return UNREACHABLE;

	return REASONS[thrown.body.reason ?? ''] ?? REFUSED;
}

/**
 * What a game card falls back to where scripting is off: the same request with its game filled in.
 *
 * The rest of the form is whatever the page wants carried over, which differs by family.
 */
export function gameHref(game: ScheduledGame, carried: Record<string, string> = {}): string {
	const query = new URLSearchParams({
		date: game.date,
		away: game.away_team.abbreviation,
		home: game.home_team.abbreviation,
		type: game.season_type
	});

	for (const [key, value] of Object.entries(carried)) {
		if (value !== '') query.set(key, value);
	}

	return `?${query}`;
}
