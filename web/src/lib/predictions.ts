/**
 * What every prediction page reads out of its address bar, and the words it answers a refusal with.
 *
 * Every family asks about one of the games on the board, so the whole of the game a request names is
 * that game's own id. Nothing describes a game by hand any more: the schedule is the only source of
 * one, so a game the schedule does not hold is a game no model can be asked about. A family adds
 * only the parameters it alone needs, so this is the part that never differs.
 */

import { goto } from '$app/navigation';

import type { HttpError } from '@sveltejs/kit';
import type { GameRequest, ScheduledGame } from '$lib/types';

export const UNREACHABLE = 'The prediction service is not answering. Try again in a few minutes.';
const REFUSED = 'This prediction could not be made. Try again in a moment.';

/** The game a request names, or null where it names none. */
export function readGameId(parameters: URLSearchParams): number | null {
	const id = Number(parameters.get('game'));

	return Number.isInteger(id) && id > 0 ? id : null;
}

/** A scheduled game written the way the prediction service asks for one. */
export const gameRequest = (game: ScheduledGame): GameRequest => ({
	date: game.date,
	home_team: game.home_team.abbreviation,
	away_team: game.away_team.abbreviation,
	season_type: game.season_type
});

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
	too_few_games: 'This player has no earlier game to build a prediction from.',
	missing_player_information: 'Too little is known about this player to make a prediction.',
	unknown_player_team: 'Say which team this player is on.',
	no_team_history: 'This team has no earlier game to build a prediction from.',
	game_already_played: 'This game has already been played, so there is nothing to predict.',
	service_busy: 'The service is answering as many predictions as it can. Try again in a moment.'
};

/**
 * A named reason wins over the status, because a busy service and an unreachable one both answer
 * 503 and only one of them is worth telling a reader to wait for.
 */
export function reasonFor(thrown: HttpError): string {
	const named = REASONS[thrown.body.reason ?? ''];

	if (named !== undefined) return named;

	return thrown.status === 503 ? UNREACHABLE : REFUSED;
}

/**
 * Copies a prediction form into the address bar, which is what runs a prediction.
 *
 * Every family asks with the same form and answers into the same block, so the asking is here. The
 * fields name themselves, so the query is read off the form rather than restated per family, and an
 * empty one is left out so the address bar names only what the reader actually asked for.
 *
 * The page is told first, because the reader is walked to the answer on the reader's own press
 * rather than when the service comes back.
 */
export function askPrediction(
	event: SubmitEvent & { currentTarget: HTMLFormElement },
	shell?: { reveal: () => void }
) {
	event.preventDefault();

	const query = new URLSearchParams();

	for (const [key, value] of new FormData(event.currentTarget)) {
		if (value !== '') query.append(key, String(value));
	}

	shell?.reveal();

	goto(`?${query}`, { noScroll: true, keepFocus: true, invalidateAll: true });
}

/**
 * What a game card falls back to where scripting is off: the same request with its game named.
 *
 * The rest of the form is whatever the page wants carried over, which differs by family.
 */
export function gameHref(game: ScheduledGame, carried: Record<string, string> = {}): string {
	const query = new URLSearchParams({ game: String(game.id) });

	for (const [key, value] of Object.entries(carried)) {
		if (value !== '') query.set(key, value);
	}

	return `?${query}`;
}
