/**
 * The player game statistics page.
 *
 * The whole request lives in the URL, so a prediction renders on the server and a link to one is
 * shareable. A half-filled URL is a valid page: it renders the parameters and no result.
 *
 * A game is described by its date, its two teams and the part of the season, whether the reader
 * typed it or chose a card. A card writes those four parameters, so there is one way to name a game
 * and no precedence to keep straight.
 *
 * Only published models are returned. A model that has no trained file is not offered at all, so a
 * reader is never shown a stat that cannot answer.
 */

import { isHttpError } from '@sveltejs/kit';

import {
	getModels,
	getPlayer,
	getRosters,
	getTeams,
	getUpcomingGames,
	predictPlayerStat
} from '$lib/server/api';

import type { HttpError } from '@sveltejs/kit';
import type { Model, Player, Prediction, ScheduledGame, SeasonType, Team } from '$lib/types';
import type { PageServerLoad } from './$types';

const FAMILY = 'player_stats';

const SEASON_TYPES: SeasonType[] = ['REGULAR_SEASON', 'PLAYOFFS', 'PLAY_IN', 'PRESEASON'];

const UNREACHABLE = 'The prediction service is not reachable. Try again shortly.';
const SAME_TEAM = 'A game needs two different teams.';
const REFUSED = 'The prediction could not be made. Try again shortly.';

const today = () => new Date().toISOString().slice(0, 10);

/** The game being asked about, however the reader described it. */
export type GameChoice = {
	date: string;
	homeTeam: string;
	awayTeam: string;
	seasonType: SeasonType;
};

const EMPTY: GameChoice = {
	date: today(),
	homeTeam: '',
	awayTeam: '',
	seasonType: SEASON_TYPES[0]
};

function readChoice(parameters: URLSearchParams): GameChoice {
	const seasonType = parameters.get('type') as SeasonType;

	return {
		date: parameters.get('date') || EMPTY.date,
		homeTeam: parameters.get('home') || EMPTY.homeTeam,
		awayTeam: parameters.get('away') || EMPTY.awayTeam,
		seasonType: SEASON_TYPES.includes(seasonType) ? seasonType : EMPTY.seasonType
	};
}

/** Whether the described game is one of the upcoming ones, which is what confines the player list. */
const isGame = (game: ScheduledGame, choice: GameChoice) =>
	game.date === choice.date &&
	game.home_team.abbreviation === choice.homeTeam &&
	game.away_team.abbreviation === choice.awayTeam &&
	game.season_type === choice.seasonType;

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

/**
 * What each refusal the service names means to a reader.
 *
 * The service's own message states ids and is for a log. Only the reason crosses over, and the
 * words a reader sees are written here.
 */
const REASONS: Record<string, string> = {
	too_few_games: 'This player has too few recorded games to predict.',
	missing_player_information: 'Too little is known about this player to predict.',
	unknown_player_team: 'Say which of the two teams this player is on.',
	no_team_history: 'This team has no earlier game to read.'
};

function reasonFor(thrown: HttpError): string {
	if (thrown.status === 503) return UNREACHABLE;

	return REASONS[thrown.body.reason ?? ''] ?? REFUSED;
}

/** A line the reader shared. Anything that is not a number is dropped rather than argued with. */
function readLine(parameters: URLSearchParams): number | null {
	const line = Number(parameters.get('line'));

	return parameters.has('line') && Number.isFinite(line) ? line : null;
}

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

		models = allModels.filter((model) => model.family === FAMILY && model.published);
		games = upcoming;
		teams = allTeams;
	} catch {
		// Nothing on this page works without the service. With no published model the page is its
		// own empty state, which is what the reader sees.
	}

	const asked = models.find(({ name }) => name === parameters.get('model'));
	const model = asked ?? models[0] ?? null;

	const choice = readChoice(parameters);
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

	const bothTeams = choice.homeTeam !== '' && choice.awayTeam !== '';

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
