/**
 * The player game statistics page.
 *
 * The whole request lives in the URL, so a prediction renders on the server and a link to one is
 * shareable. A half-filled URL is a valid page: it renders the parameters and no result.
 *
 * A request names one of the games on the board, which of its two teams the player is on, and the
 * player, plus the roster changes the reader made. The game is named by its id alone, because the
 * schedule is the only source of a game and a game it does not hold is one no model can answer
 * about.
 *
 * A model is offered only if it has a trained file and answers in a shape this page has a reading
 * for. A reader is never shown a stat that cannot answer.
 */

import { isHttpError } from '@sveltejs/kit';

import { DRAWN_KINDS } from '$lib/odds';
import { gameRequest, readGameId, readLine, reasonFor } from '$lib/predictions';
import {
	getModels,
	getPlayer,
	getRosters,
	getUpcomingGames,
	predictPlayerStat
} from '$lib/server/api';

import type { Model, Player, Prediction, ScheduledGame } from '$lib/types';
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

	// Which side of the game the player is on. The reader names it, and only one of the game's two
	// teams is an answer to the question.
	const namedTeam = parameters.get('team') ?? '';
	const sides = selectedGame
		? [selectedGame.away_team.abbreviation, selectedGame.home_team.abbreviation]
		: [];
	const namedSide = sides.includes(namedTeam) ? namedTeam : '';

	const playerId = Number(parameters.get('player')) || null;

	// A chosen player is never dropped for being off both rosters. Somebody who has just joined a
	// team has no game on it yet and so appears on neither, and predicting exactly them is one of
	// the things this site is for.
	const [rosters, player] = await Promise.all([
		selectedGame === null ? [] : getRosters(selectedGame).catch(() => []),
		playerId === null ? null : getPlayer(playerId).catch(() => null)
	]);

	// A roster naming the player is the last word on which side they are on, whatever the request
	// said, so somebody picked out of a league search is answered for the team they actually play
	// for. Nobody names a player who has just joined, which is the case the reader's answer is for.
	const playerTeam =
		rosters.find((roster) => roster.players.some(({ id }) => id === playerId))?.team.abbreviation ??
		namedSide;

	const [out, joined] = await Promise.all([
		namePlayers(readIds(parameters, 'out')),
		namePlayers(readIds(parameters, 'joined'))
	]);

	let prediction: Prediction | null = null;
	let error: string | null = null;

	if (selectedGame !== null && player !== null && model !== null) {
		try {
			prediction = await predictPlayerStat(model.name, {
				player_id: player.id,
				game: gameRequest(selectedGame),
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
		player,
		playerTeam,
		out,
		joined,
		prediction,
		line: readLine(parameters),
		error
	};
};
