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

export type Model = {
	name: string;
	/** The group of models this belongs to, which is the page it is predicted on. */
	family: string;
	stats: string[];
	/** The outcome the first probability stands for. */
	minimum_value: number;
	outcomes: number;
	/** Whether a trained file exists for it. A model without one is offered but cannot be asked. */
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

export type Prediction = {
	model: string;
	minimum_value: number;
	probabilities: number[];
	expected_value: number;
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
	scenario?: Scenario;
};
