import { goto } from '$app/navigation';

import type { HttpError } from '@sveltejs/kit';
import type { GameRequest, ScheduledGame } from '$lib/types';

export const UNREACHABLE = 'The prediction service is not answering. Try again in a few minutes.';
const REFUSED = 'This prediction could not be made. Try again in a moment.';

/** Returns the game id from the query parameters, or null if there is none. */
export function readGameId(parameters: URLSearchParams): number | null {
	const id = Number(parameters.get('game'));

	return Number.isInteger(id) && id > 0 ? id : null;
}

/** Converts a scheduled game into the format the prediction service expects. */
export const gameRequest = (game: ScheduledGame): GameRequest => ({
	date: game.date,
	home_team: game.home_team.abbreviation,
	away_team: game.away_team.abbreviation,
	season_type: game.season_type
});

/** Returns the line from the query parameters, or null if it is missing or not a number. */
export function readLine(parameters: URLSearchParams): number | null {
	const line = Number(parameters.get('line'));

	return parameters.has('line') && Number.isFinite(line) ? line : null;
}

/** User-facing message for each reason code from the service. */
const REASONS: Record<string, string> = {
	too_few_games: 'This player has no earlier game to build a prediction from.',
	missing_player_information: 'Too little is known about this player to make a prediction.',
	unknown_player_team: 'Say which team this player is on.',
	no_team_history: 'This team has no earlier game to build a prediction from.',
	game_already_played: 'This game has already been played, so there is nothing to predict.',
	service_busy: 'The service is answering as many predictions as it can. Try again in a moment.'
};

/** Returns the message for an error. The reason code is checked first, because two different failures return 503. */
export function reasonFor(thrown: HttpError): string {
	const named = REASONS[thrown.body.reason ?? ''];

	if (named !== undefined) return named;

	return thrown.status === 503 ? UNREACHABLE : REFUSED;
}

/** Puts the form values into the URL, which triggers the prediction. */
export function askPrediction(
	event: SubmitEvent & { currentTarget: HTMLFormElement },
	shell?: { reveal: (asking?: Promise<unknown>) => void }
) {
	event.preventDefault();

	const query = new URLSearchParams();

	for (const [key, value] of new FormData(event.currentTarget)) {
		if (value !== '') query.append(key, String(value));
	}

	const asking = goto(`?${query}`, {
		noScroll: true,
		invalidateAll: true
	});

	shell?.reveal(asking);
}

/** Returns the link for a game card, used when JavaScript is off. */
export function gameHref(game: ScheduledGame, carried: Record<string, string> = {}): string {
	const query = new URLSearchParams({ game: String(game.id) });

	for (const [key, value] of Object.entries(carried)) {
		if (value !== '') query.set(key, value);
	}

	return `?${query}`;
}
