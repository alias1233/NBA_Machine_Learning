export type SeasonType = 'PRESEASON' | 'REGULAR_SEASON' | 'PLAYOFFS' | 'PLAY_IN';

export type GameSide = 'home' | 'away';

export type Team = {
	abbreviation: string;
	name: string;
};

export type Player = {
	id: number;
	name: string;
};

/** A team and its players for one game. */
export type Roster = {
	team: Team;
	players: Player[];
	/** Players who played the team's last game and are not expected to play this one. */
	without: Player[];
	/** Players expected to play this game who did not play the last one. */
	returning: Player[];
};

/** Format of a model's output. The output is a list of numbers, and this describes what each position means. */
export type ModelOutput =
	| {
			kind: 'integer_distribution';
			minimum_value: number;
			outcomes: number;
			bucket_width: number;
			impossible_value: number | null;
	  }
	| { kind: 'category_distribution'; categories: string[] }
	| { kind: 'values'; quantities: string[] };

export type Model = {
	name: string;
	/** Display name of the model. */
	title: string;
	/** One sentence describing what the model predicts. */
	description: string;
	/** Model family this model belongs to. */
	family: string;
	/** Names of the predicted stats, as shown to users. */
	predicts: string[];
	output: ModelOutput;
	/** Side of the game a positive value is for. Null if the output is not tied to a side. */
	read_from: GameSide | null;
	/** Side of the game each category is for, in output order. */
	category_sides: GameSide[] | null;
	/** True if a trained model file exists. */
	published: boolean;
};

/** How a metric is displayed. In the stat's own units, as a probability or as a plain score. */
export type MetricUnit = 'value' | 'probability' | 'score';

/** One evaluation metric. */
export type Metric = {
	/** Stable identifier of the metric. */
	key: string;
	label: string;
	value: number;
	/** Score of a baseline that predicts the season's outcome distribution, on the same games. Null if it cannot be scored. */
	floor: number | null;
	unit: MetricUnit;
	higher_is_better: boolean;
	/** Target value for metrics where closer to the target is better. Null otherwise. */
	ideal: number | null;
};

/** Definition of an evaluation metric, shown in the About page glossary. */
export type MetricDefinition = {
	key: string;
	label: string;
	description: string;
};

/** Evaluation results for one model on games it was not trained on. */
export type ModelEvaluation = {
	/** Data split the metrics were calculated on. */
	scored_on: string;
	samples: number;
	/** Dates of the first and last evaluated games, as YYYY-MM-DD. */
	first_game: string;
	last_game: string;
	/** When the evaluation ran, in UTC. */
	evaluated: string;
	/** Metrics this model publishes, main one first. */
	metrics: Metric[];
};

/** A model as listed on a family page, with its description and evaluation results. */
export type ScoredModel = {
	name: string;
	title: string;
	description: string;
	published: boolean;
	evaluation: ModelEvaluation | null;
};

/** An upcoming game that has all the data needed to predict it. */
export type ScheduledGame = {
	id: number;
	date: string;
	/** Start time of the game in UTC. Null if the schedule has no time. */
	tipoff: string | null;
	home_team: Team;
	away_team: Team;
	season_type: SeasonType;
	/** True for a test game added by hand, not collected from the schedule. */
	is_mock: boolean;
};

/** One of the day's sample predictions, picked at random by a scheduled job. */
export type ShowcaseSample = {
	family: string;
	model: string;
	/** Short display name of the model. */
	title: string;
	predicts: string[];
	output: ModelOutput;
	values: number[];
	past_games: number;
	game: {
		date: string;
		home_team: Team;
		away_team: Team;
		season_type: SeasonType;
		/** Start time of the game in UTC. Null if the schedule has no time. */
		tipoff: string | null;
	};
	/** Player the stat belongs to, for a player model. Null for other families. */
	player: Player | null;
	/** Team the stat is for. Null for a game stat, which is not tied to a team. */
	team: Team | null;
	read_from: GameSide | null;
};

/** The day's sample predictions, shown in the home page hero. */
export type Showcase = {
	format_version: number;
	/** Date the samples were built for, as YYYY-MM-DD. */
	built_for: string;
	built_at: string;
	samples: ShowcaseSample[];
};

export type Health = {
	models: string[];
	/** Date of the newest stored game. Predictions measure rest days from this date. */
	newest_stored_game: string | null;
	/** When the roster and injury snapshot was collected, in UTC. Null if there is none yet. */
	roster_snapshot: string | null;
};

/** One prediction. `values` has one number for each position in `output`. */
export type Prediction = {
	model: string;
	output: ModelOutput;
	values: number[];
	/** Number of past games the prediction used. */
	past_games: number;
};

export type GameRequest = {
	date: string;
	home_team: string;
	away_team: string;
	season_type: SeasonType;
};

/** Lineup changes for one team compared to its last game, as player ids. */
export type Scenario = {
	without: number[];
	returning: number[];
};

/** Lineup changes for both teams in a game. */
export type GameRosters = {
	home: Scenario;
	away: Scenario;
};

export type PlayerPredictionRequest = {
	player_id: number;
	game: GameRequest;
	/** The player's team. Only needed if they just changed teams and have not played for the new one yet. */
	player_team?: string;
	scenario?: Scenario;
};

export type TeamPredictionRequest = {
	/** Abbreviation such as LAL, or a full team name. */
	team: string;
	game: GameRequest;
	rosters?: GameRosters;
};

/** A game stat request has no team. Signed values such as point differential are from the home team's side. */
export type GamePredictionRequest = {
	game: GameRequest;
	rosters?: GameRosters;
};
