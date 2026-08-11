/**
 * The team statistics page.
 *
 * The whole request lives in the URL, so a prediction renders on the server and a link to one is
 * shareable. A half-filled URL is a valid page: it renders the parameters and no result.
 *
 * A request names a game and one of its two sides, because the answer belongs to that side and would
 * be a different number for the other one.
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
import { getModels, getTeams, getUpcomingGames, predictTeamStat } from '$lib/server/api';

import type { Model, Prediction, ScheduledGame, Team } from '$lib/types';
import type { PageServerLoad } from './$types';

const FAMILY = 'team_stats';

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

	// Only one of the game's two sides is an answer to which team, so a side left over from another
	// game is dropped rather than sent.
	const named = parameters.get('team') ?? '';
	const team = [choice.awayTeam, choice.homeTeam].includes(named) ? named : '';

	let prediction: Prediction | null = null;
	let error: string | null = null;

	const bothTeams = namesBothTeams(choice);

	if (models.length === 0) {
		// The empty state says this, so there is nothing to add.
	} else if (bothTeams && choice.homeTeam === choice.awayTeam) {
		error = SAME_TEAM;
	} else if (bothTeams && team !== '' && model !== null) {
		try {
			prediction = await predictTeamStat(model.name, {
				team,
				game: {
					date: choice.date,
					home_team: choice.homeTeam,
					away_team: choice.awayTeam,
					season_type: choice.seasonType
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
		teams,
		choice,
		team,
		prediction,
		line: readLine(parameters),
		error
	};
};
