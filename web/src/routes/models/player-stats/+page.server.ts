/**
 * The player game statistics page.
 *
 * The whole request lives in the URL, so a prediction renders on the server and a link to one is
 * shareable. A half-filled URL is a valid page: it renders the parameters and no result.
 *
 * A request names a game and the player it is about, plus the roster changes the reader made and,
 * where no roster names that player, which of the two sides they are on.
 *
 * A model is offered only if it has a trained file and answers in a shape this page has a reading
 * for. A reader is never shown a stat that cannot answer.
 */

import { isHttpError } from '@sveltejs/kit';

import { DRAWN_KINDS } from '$lib/odds';
import {
	SAME_TEAM,
	isGame,
	namesBothTeams,
	readGameChoice,
	readLine,
	reasonFor
} from '$lib/predictions';
import {
	getModels,
	getPlayer,
	getRosters,
	getTeams,
	getUpcomingGames,
	predictPlayerStat
} from '$lib/server/api';

import type { Model, Player, Prediction, ScheduledGame, Team } from '$lib/types';
import type { PageServerLoad } from './$types';

const FAMILY = 'player_stats';

/** Names the players a roster parameter holds ids for, so a shared link opens with its pills. */
async function namePlayers(ids: number[]): Promise<Player[]> {
	const found = await Promise.all(ids.map((id) => getPlayer(id).catch(() => null)));

	return found.filter((player): player is Player => player !== null);
}

const readIds = (parameters: URLSearchParams, name: string) =>
	parameters
		.getAll(name)
		.map(Number)
		.filter((id) => Number.isInteger(id) && id > 0);

export const load: PageServerLoad = async ({ url }) => {
	const parameters = url.searchParams;

	let models: Model[] = [];
	let games: ScheduledGame[] = [];
	let teams: Team[] = [];

	try {
		const [allModels, upcoming, allTeams] = await Promise.all([
			getModels(),
			getUpcomingGames(),
			getTeams()
		]);

		models = allModels.filter(
			(model) =>
				model.family === FAMILY && model.published && DRAWN_KINDS.includes(model.output.kind)
		);
		games = upcoming;
		teams = allTeams;
	} catch {
		// Nothing on this page works without the service. With no published model the page is its
		// own empty state, which is what the reader sees.
	}

	const asked = models.find(({ name }) => name === parameters.get('model'));
	const model = asked ?? models[0] ?? null;

	const choice = readGameChoice(parameters);
	const selectedGame = games.find((game) => isGame(game, choice)) ?? null;

	// Which side a player who has just moved is on. Nothing stored says it, so the reader names it,
	// and only one of the game's two teams is an answer to the question.
	const namedTeam = parameters.get('team') ?? '';
	const playerTeam = [choice.awayTeam, choice.homeTeam].includes(namedTeam) ? namedTeam : '';

	const playerId = Number(parameters.get('player')) || null;

	// A chosen player is never dropped for being off both rosters. Somebody who has just joined a
	// team has no game on it yet and so appears on neither, and predicting exactly them is one of
	// the things this site is for.
	const [rosters, player] = await Promise.all([
		selectedGame === null ? [] : getRosters(selectedGame).catch(() => []),
		playerId === null ? null : getPlayer(playerId).catch(() => null)
	]);

	const [out, joined] = await Promise.all([
		namePlayers(readIds(parameters, 'out')),
		namePlayers(readIds(parameters, 'joined'))
	]);

	let prediction: Prediction | null = null;
	let error: string | null = null;

	const bothTeams = namesBothTeams(choice);

	if (models.length === 0) {
		// The empty state says this, so there is nothing to add.
	} else if (bothTeams && choice.homeTeam === choice.awayTeam) {
		error = SAME_TEAM;
	} else if (bothTeams && player !== null && model !== null) {
		try {
			prediction = await predictPlayerStat(model.name, {
				player_id: player.id,
				game: {
					date: choice.date,
					home_team: choice.homeTeam,
					away_team: choice.awayTeam,
					season_type: choice.seasonType
				},
				player_team: playerTeam || undefined,
				scenario: {
					without: out.map(({ id }) => id),
					returning: joined.map(({ id }) => id)
				}
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
		rosters,
		teams,
		choice,
		player,
		playerTeam,
		out,
		joined,
		prediction,
		line: readLine(parameters),
		error
	};
};
