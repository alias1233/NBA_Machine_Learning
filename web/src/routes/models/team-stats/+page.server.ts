import { isHttpError } from '@sveltejs/kit';

import { DRAWN_KINDS } from '$lib/odds';
import { gameRequest, readGameId, readLine, reasonFor } from '$lib/predictions';
import {
	getModels,
	getRosters,
	getScoredModels,
	getUpcomingGames,
	predictTeamStat
} from '$lib/server/api';
import {
	expectedScenarios,
	isGameChanged,
	readGameScenarios,
	scenarioRequest
} from '$lib/server/rosters';

import type { Model, Prediction, ScheduledGame } from '$lib/types';
import type { PageServerLoad } from './$types';

const FAMILY = 'team_stats';

export const load: PageServerLoad = async ({ url }) => {
	const parameters = url.searchParams;

	let models: Model[] = [];
	let games: ScheduledGame[] = [];

	const listing = getScoredModels(FAMILY).catch(() => []);

	try {
		const [allModels, upcoming] = await Promise.all([getModels(), getUpcomingGames()]);

		models = allModels.filter(
			(model) =>
				model.family === FAMILY && model.published && DRAWN_KINDS.includes(model.output.kind)
		);
		games = upcoming;
	} catch {
		// If the service is down, the page shows its empty state.
	}

	const asked = models.find(({ name }) => name === parameters.get('model'));
	const model = asked ?? models[0] ?? null;

	const gameId = readGameId(parameters);
	const selectedGame = games.find((game) => game.id === gameId) ?? null;

	const named = parameters.get('team') ?? '';
	const sides = selectedGame
		? [selectedGame.away_team.abbreviation, selectedGame.home_team.abbreviation]
		: [];
	const team = sides.includes(named) ? named : '';

	const rosters = selectedGame === null ? [] : await getRosters(selectedGame.id).catch(() => []);
	const expected = expectedScenarios(rosters, selectedGame);
	const scenarios = await readGameScenarios(parameters, expected);

	let prediction: Prediction | null = null;
	let error: string | null = null;

	if (selectedGame !== null && team !== '' && model !== null) {
		try {
			prediction = await predictTeamStat(model.name, {
				team,
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
		team,
		rosters,
		scenarios,
		customRoster: isGameChanged(scenarios, expected),
		prediction,
		line: readLine(parameters),
		error
	};
};
