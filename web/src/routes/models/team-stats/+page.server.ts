/**
 * The team statistics page.
 *
 * The whole request lives in the URL, so a prediction renders on the server and a link to one is
 * shareable. A half-filled URL is a valid page: it renders the parameters and no result.
 *
 * A request names one of the games on the board and one of its two sides, because the answer belongs
 * to that side and would be a different number for the other one. The game is named by its id alone,
 * because the schedule is the only source of a game.
 *
 * A model is offered only if it has a trained file and answers in a shape this page has a reading
 * for. A reader is never shown a stat that cannot answer.
 */

import { isHttpError } from '@sveltejs/kit';

import { DRAWN_KINDS } from '$lib/odds';
import { gameRequest, readGameId, readLine, reasonFor } from '$lib/predictions';
import { getModels, getUpcomingGames, predictTeamStat } from '$lib/server/api';

import type { Model, Prediction, ScheduledGame } from '$lib/types';
import type { PageServerLoad } from './$types';

const FAMILY = 'team_stats';

export const load: PageServerLoad = async ({ url }) => {
	const parameters = url.searchParams;

	let models: Model[] = [];
	let games: ScheduledGame[] = [];

	try {
		const [allModels, upcoming] = await Promise.all([getModels(), getUpcomingGames()]);

		models = allModels.filter(
			(model) =>
				model.family === FAMILY && model.published && DRAWN_KINDS.includes(model.output.kind)
		);
		games = upcoming;
	} catch {
		// Nothing on this page works without the service. With no published model the page is its
		// own empty state, which is what the reader sees.
	}

	const asked = models.find(({ name }) => name === parameters.get('model'));
	const model = asked ?? models[0] ?? null;

	const gameId = readGameId(parameters);
	const selectedGame = games.find((game) => game.id === gameId) ?? null;

	// Only one of the game's two sides is an answer to which team, so a side left over from another
	// game is dropped rather than sent.
	const named = parameters.get('team') ?? '';
	const sides = selectedGame
		? [selectedGame.away_team.abbreviation, selectedGame.home_team.abbreviation]
		: [];
	const team = sides.includes(named) ? named : '';

	let prediction: Prediction | null = null;
	let error: string | null = null;

	if (selectedGame !== null && team !== '' && model !== null) {
		try {
			prediction = await predictTeamStat(model.name, {
				team,
				game: gameRequest(selectedGame)
			});
		} catch (thrown) {
			if (!isHttpError(thrown)) throw thrown;

			error = reasonFor(thrown);
		}
	}

	return {
		models,
		model: model?.name ?? '',
		games,
		selectedGame,
		team,
		prediction,
		line: readLine(parameters),
		error
	};
};
