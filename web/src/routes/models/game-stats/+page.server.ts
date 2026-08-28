/**
 * The game statistics page.
 *
 * The whole request lives in the URL, so a prediction renders on the server and a link to one is
 * shareable. A half-filled URL is a valid page: it renders the parameters and no result.
 *
 * A request names one of the games on the board, by its id, because the schedule is the only source
 * of a game. Anything with a direction is read from the home side, so a positive point differential
 * is the home team's margin.
 *
 * Both sides' rosters are read as well. A game statistic is decided by both teams, so who is missing
 * from either of them changes the answer. Each side opens on the lineup the collected injury report
 * and roster snapshot expects of it, which the reader is free to change.
 *
 * A model is offered only if it has a trained file and answers in a shape this page has a reading
 * for. A reader is never shown a stat that cannot answer.
 */

import { isHttpError } from '@sveltejs/kit';

import { DRAWN_KINDS } from '$lib/odds';
import { gameRequest, readGameId, readLine, reasonFor } from '$lib/predictions';
import {
	getModels,
	getRosters,
	getScoredModels,
	getUpcomingGames,
	predictGameStat
} from '$lib/server/api';
import {
	expectedScenarios,
	isGameChanged,
	readGameScenarios,
	scenarioRequest
} from '$lib/server/rosters';

import type { Model, Prediction, ScheduledGame } from '$lib/types';
import type { PageServerLoad } from './$types';

const FAMILY = 'game_stats';

export const load: PageServerLoad = async ({ url }) => {
	const parameters = url.searchParams;

	let models: Model[] = [];
	let games: ScheduledGame[] = [];

	// The family's standing listing, asked for alongside everything else. It is not the same set as
	// the models a prediction can be run with: one that is not trained yet is still worth reading
	// about, and losing the figures must not take the form down with them.
	const listing = getScoredModels(FAMILY).catch(() => []);

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

	// The rosters are read first because they carry the lineup each side is expected to field, which
	// is what the page opens on where the reader has not named one of their own.
	const rosters = selectedGame === null ? [] : await getRosters(selectedGame.id).catch(() => []);
	const expected = expectedScenarios(rosters, selectedGame);
	const scenarios = await readGameScenarios(parameters, expected);

	let prediction: Prediction | null = null;
	let error: string | null = null;

	if (selectedGame !== null && model !== null) {
		try {
			prediction = await predictGameStat(model.name, {
				game: gameRequest(selectedGame),
				rosters: {
					home: scenarioRequest(scenarios.home),
					away: scenarioRequest(scenarios.away)
				}
			});
		} catch (thrown) {
			if (!isHttpError(thrown)) throw thrown;

			error = reasonFor(thrown);
		}
	}

	return {
		models,
		scored: await listing,
		model: model?.name ?? '',
		games,
		selectedGame,
		rosters,
		scenarios,
		customRoster: isGameChanged(scenarios, expected),
		prediction,
		line: readLine(parameters),
		error
	};
};
