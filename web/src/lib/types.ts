/**
 * The shapes the prediction service sends and receives.
 *
 * Field names are left exactly as they cross the wire, so this file can be read side by side with
 * `python/src/nba_ml/api/app.py` and checked against it.
 */

export type SeasonType = 'PRESEASON' | 'REGULAR_SEASON' | 'PLAYOFFS' | 'PLAY_IN';

/** One side of a game, which is what an answer belonging to a game names. */
export type GameSide = 'home' | 'away';

export type Team = {
	abbreviation: string;
	name: string;
};

export type Player = {
	id: number;
	name: string;
};

/**
 * One team and who plays for it, for one game. Both sides of a chosen game, away first.
 *
 * `players` is the roster the team is projected to field, so somebody traded away since their last
 * game for it is not in it. It is what the player pickers open on.
 *
 * `without` and `returning` are the lineup change the collected roster and injury snapshot expects
 * of this side, already worked out. The site opens its roster controls on them, so a reader who
 * changes nothing is still answered for the players who will actually take the floor. Both are
 * empty where nothing collected says who will play.
 */
export type Roster = {
	team: Team;
	players: Player[];
	/** Who played the team's last game and is not expected to play this one. */
	without: Player[];
	/** Who is expected to play this one and did not play the last. */
	returning: Player[];
};

/**
 * What a model answers with: an ordered list of numbers, and what each position means.
 *
 * A model does not have to answer with a distribution, so `kind` is what says how to read the
 * values. A shape the site cannot draw is a shape it does not offer.
 *
 * An integer distribution counts up from `minimum_value` in steps of `bucket_width`. At a width of
 * one each value gets its own chance. Above one a position covers that many whole numbers, which is
 * what a model with too few games to fill a class per outcome answers with. `impossible_value` is a
 * whole number the statistic cannot take, such as a point differential of zero, and it is off the
 * number line rather than inside a position, so every position still covers `bucket_width` outcomes.
 *
 * A category distribution lists its categories most notable first, so a reading leads with the
 * first one. For a yes or no answer that is the chance of yes.
 */
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
	/** What the model is called where it is listed rather than run. */
	title: string;
	/** One sentence saying what it answers, for a reader who has not opened the family yet. */
	description: string;
	/** The group of models this belongs to, which is the page it is predicted on. */
	family: string;
	/** What the model answers about, in the words a reader sees. */
	predicts: string[];
	output: ModelOutput;
	/**
	 * Which side of the game a value above zero belongs to, for an answer with a direction.
	 *
	 * Null where the answer names no side. A point differential is read from the home team, so the
	 * answer says whose margin it is drawing rather than leaving a signed number to say it.
	 */
	read_from: GameSide | null;
	/**
	 * Which side of the game each category names, in the order the output lists them.
	 *
	 * A name leads with its side's word, so the team playing that side goes in place of the word and
	 * "home win" is read as the team's own name. Null where no category names a side.
	 */
	category_sides: GameSide[] | null;
	/** Whether a trained file exists for it. A model without one is listed but cannot be asked. */
	published: boolean;
};

/** How a figure is written down: in the statistic's own units, as a probability, or as a bare score. */
export type MetricUnit = 'amount' | 'probability' | 'score';

/** One measured figure, with everything needed to write it down and read it. */
export type Metric = {
	/** The stable name of the figure, so one can be singled out without matching on wording. */
	key: string;
	label: string;
	description: string;
	value: number;
	/** What answering with the season's own spread of outcomes scores on the same games, if scorable. */
	floor: number | null;
	unit: MetricUnit;
	higher_is_better: boolean;
	/** The value this figure should reach, where closer is better than higher or lower. */
	ideal: number | null;
};

/** How one model scored on games it never saw while it was being fitted. */
export type ModelEvaluation = {
	/** Which split produced these figures. Only a held-out one is published. */
	scored_on: string;
	samples: number;
	/** The stretch of calendar the scored games cover, as YYYY-MM-DD. */
	first_game: string;
	last_game: string;
	/** When the scoring ran, in UTC. */
	evaluated: string;
	/** The figures this model chose to publish, headline first. */
	metrics: Metric[];
};

/**
 * One model card on a family Info page: the words it prints and the figures under them.
 *
 * The evaluation travels with the card because the page is rendered on the server and read by
 * search engines, and a figure fetched after the page has been sent reaches neither. Null where the
 * model has never been scored.
 */
export type FamilyInfoModel = {
	name: string;
	title: string;
	description: string;
	published: boolean;
	evaluation: ModelEvaluation | null;
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

/**
 * One of the day's sample predictions, drawn at random by a job rather than asked for by a reader.
 *
 * It is the same answer a prediction endpoint returns, plus the subject it was asked about, because
 * nobody requested it and so nothing else says what it is of. Everything read off the numbers is
 * still worked out in `src/lib/odds.ts`, exactly as it is for an answer somebody did ask for.
 */
export type ShowcaseSample = {
	family: string;
	model: string;
	/** The model's short reader-facing name. */
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
		/** When the game starts, in UTC. Null when the schedule names no time. */
		tipoff: string | null;
	};
	/** Whose statistic it is, for a player model. Null for every other family. */
	player: Player | null;
	/** Which side of the game it is about. Null for a game statistic, which names no side. */
	team: Team | null;
	read_from: GameSide | null;
};

/**
 * The day's sample predictions, built once by a job and read by everyone who visits that day.
 *
 * Nothing on this site predicts on its own, so the home page shows these rather than starting a
 * forward pass for whoever arrived. The set is drawn at random, seeded from the day, so it changes
 * every morning and is the same for every reader of that morning.
 */
export type Showcase = {
	format_version: number;
	/** The day the set was drawn for, as YYYY-MM-DD. */
	built_for: string;
	built_at: string;
	samples: ShowcaseSample[];
};

export type Health = {
	models: string[];
	/** Predictions read rest off the gap to this date, so a stale database reads as a layoff. */
	newest_stored_game: string | null;
	/** When the roster and injury snapshot was collected, in UTC. Null while none has been. */
	roster_snapshot: string | null;
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
 * Which core players are on the floor for one team, when that differs from its last game.
 *
 * `without` is the site's Out control and `returning` is New teammates. The reader never sees
 * either service name.
 */
export type Scenario = {
	without: number[];
	returning: number[];
};

/**
 * The same, for both sides of a game.
 *
 * A team or game model reads one row that carries what each side has available, so a request names
 * both. A defense missing its best player changes what the team it faces is expected to score.
 */
export type GameRosters = {
	home: Scenario;
	away: Scenario;
};

export type PlayerPredictionRequest = {
	player_id: number;
	game: GameRequest;
	/** The player's team. Only needed when they have just moved and no game records it yet. */
	player_team?: string;
	scenario?: Scenario;
};

/** A team statistic belongs to one side of the game, so a request names which side. */
export type TeamPredictionRequest = {
	/** A tricode such as LAL, or a full team name. */
	team: string;
	game: GameRequest;
	rosters?: GameRosters;
};

/**
 * A game statistic names no team. Anything with a direction is the home team's, so a positive point
 * differential is the home team's margin.
 */
export type GamePredictionRequest = {
	game: GameRequest;
	rosters?: GameRosters;
};
