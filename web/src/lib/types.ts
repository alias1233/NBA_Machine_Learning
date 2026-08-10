/**
 * The shapes the prediction service sends and receives.
 *
 * Field names are left exactly as they cross the wire, so this file can be read side by side with
 * `python/src/nba_ml/api/app.py` and checked against it.
 */

export type SeasonType = 'PRESEASON' | 'REGULAR_SEASON' | 'PLAYOFFS' | 'PLAY_IN';

export type Team = {
	abbreviation: string;
	name: string;
};

export type Player = {
	id: number;
	name: string;
};

/** One team and who plays for it. Both sides of a chosen game, away first. */
export type Roster = {
	team: Team;
	players: Player[];
};

/**
 * What a model answers with: an ordered list of numbers, and what each position means.
 *
 * A model does not have to answer with a distribution, so `kind` is what says how to read the
 * values. A shape the site cannot draw is a shape it does not offer.
 *
 * A category distribution lists its categories most notable first, so a reading leads with the
 * first one. For a yes or no answer that is the chance of yes.
 */
export type ModelOutput =
	| { kind: 'integer_distribution'; minimum_value: number; outcomes: number }
	| { kind: 'category_distribution'; categories: string[] }
	| { kind: 'values'; quantities: string[] };

export type Model = {
	name: string;
	/** The group of models this belongs to, which is the page it is predicted on. */
	family: string;
	/** What the model answers about, in the words a reader sees. */
	predicts: string[];
	output: ModelOutput;
	/** Whether a trained file exists for it. A model without one is listed but cannot be asked. */
	published: boolean;
};

/** A game that has not been played and that every model input for it is already held for. */
export type ScheduledGame = {
	id: number;
	date: string;
	/** When the game starts, in UTC. Null when the schedule names no time. */
	tipoff: string | null;
	home_team: Team;
	away_team: Team;
	season_type: SeasonType;
	/** Added by hand for testing rather than collected. */
	is_mock: boolean;
};

export type Health = {
	models: string[];
	/** Predictions read rest off the gap to this date, so a stale database reads as a layoff. */
	newest_stored_game: string | null;
};

/**
 * One answer: a number per position of its `output`.
 *
 * Everything a reader reads off it is worked out in `src/lib/odds.ts` rather than asked for again.
 */
export type Prediction = {
	model: string;
	output: ModelOutput;
	values: number[];
	/** How many earlier games the answer was built from. A few of them means it rests on very little. */
	past_games: number;
};

export type GameRequest = {
	date: string;
	home_team: string;
	away_team: string;
	season_type: SeasonType;
};

/**
 * Which core players are on the floor, when that differs from the team's last game.
 *
 * `without` is the site's Out control and `returning` is New teammates. The reader never sees
 * either service name.
 */
export type Scenario = {
	without: number[];
	returning: number[];
};

export type PredictionRequest = {
	player_id: number;
	game: GameRequest;
	/** The player's team. Only needed when they have just moved and no game records it yet. */
	player_team?: string;
	scenario?: Scenario;
};
