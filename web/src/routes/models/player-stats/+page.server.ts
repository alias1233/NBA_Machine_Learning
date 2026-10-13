import { isHttpError } from '@sveltejs/kit';

import { DRAWN_KINDS } from '$lib/odds';
import { gameRequest, readGameId, readLine, reasonFor } from '$lib/predictions';
import {
	getModels,
	getPlayer,
	getRosters,
	getScoredModels,
	getUpcomingGames,
	predictPlayerStat
} from '$lib/server/api';
import { expectedAround, rosterOf } from '$lib/rosters';
import { isChanged, readScenario, scenarioRequest } from '$lib/server/rosters';

import type { Model, Prediction, ScheduledGame } from '$lib/types';
import type { PageServerLoad } from './$types';

const FAMILY = 'player_stats';

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

	const namedTeam = parameters.get('team') ?? '';
	const sides = selectedGame
		? [selectedGame.away_team.abbreviation, selectedGame.home_team.abbreviation]
		: [];
	const namedSide = sides.includes(namedTeam) ? namedTeam : '';

	const playerId = Number(parameters.get('player')) || null;

	// A player who just joined a team is on neither roster, so a missing roster entry does not drop the player.
	const [rosters, player] = await Promise.all([
		selectedGame === null ? [] : getRosters(selectedGame.id).catch(() => []),
		playerId === null ? null : getPlayer(playerId).catch(() => null)
	]);

	// If a roster includes the player, that team is used instead of the one in the request.
	const playerTeam =
		rosters.find((roster) => roster.players.some(({ id }) => id === playerId))?.team.abbreviation ??
		namedSide;

	const expected = expectedAround(rosterOf(rosters, playerTeam), playerId);
	const scenario = await readScenario(parameters, expected);

	let prediction: Prediction | null = null;
	let error: string | null = null;

	if (selectedGame !== null && player !== null && model !== null) {
		try {
			prediction = await predictPlayerStat(model.name, {
				player_id: player.id,
				game: gameRequest(selectedGame),
				player_team: playerTeam || undefined,
				scenario: scenarioRequest(scenario)
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
		player,
		playerTeam,
		scenario,
		customRoster: isChanged(scenario, expected),
		prediction,
		line: readLine(parameters),
		error
	};
};
