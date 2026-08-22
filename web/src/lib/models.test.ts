/**
 * Checks the words `models.ts` reads off a model.
 *
 * A game statistic names no team, so what the site writes beside a figure is the only thing saying
 * which of the two sides an answer is about. Getting it wrong reads as a working answer about the
 * other team.
 *
 * Run with `npm test`. Node reads the TypeScript directly, so there is nothing to install.
 */

import {
	answerSentence,
	familyInfoPath,
	figureNote,
	MODEL_FAMILIES,
	namedCategories
} from './models.ts';

import type { GameSides } from './models.ts';
import type { Answer } from './odds.ts';
import type { Model } from './types.ts';

function check(what: string, actual: unknown, expected: unknown) {
	const [got, wanted] = [JSON.stringify(actual), JSON.stringify(expected)];

	if (got !== wanted) throw new Error(`${what}\n  expected ${wanted}\n  got      ${got}`);

	console.log(`ok   ${what}`);
}

const sides: GameSides = { home: 'Toronto Raptors', away: 'Boston Celtics' };

check(
	'a family Info link uses the info route',
	familyInfoPath(MODEL_FAMILIES[0]),
	'/models/player-stats/info'
);

const model = (fields: Partial<Model>): Model => ({
	name: 'test',
	title: 'Test',
	description: 'A model that exists only in this file.',
	family: 'game_stats',
	predicts: ['point differential'],
	output: {
		kind: 'integer_distribution',
		minimum_value: -6,
		outcomes: 5,
		bucket_width: 3,
		impossible_value: 0
	},
	read_from: null,
	category_sides: null,
	published: true,
	...fields
});

const margin = model({ read_from: 'home' });

const wins = model({
	predicts: ['win chances'],
	output: { kind: 'category_distribution', categories: ['home win', 'away win'] },
	category_sides: ['home', 'away']
});

check(
	'a figure read from one side names what it counts and whose it is',
	figureNote(margin, sides),
	'point differential for Toronto Raptors'
);

check('a figure naming no side says nothing', figureNote(model({}), sides), '');
check('and neither does one before both teams are named', figureNote(margin, null), '');

check(
	'a category naming a side is named by the team playing it',
	namedCategories(wins, sides),
	['Toronto Raptors win', 'Boston Celtics win']
);

check('categories naming no side keep the model\'s own words', namedCategories(model({}), sides), null);
check('and so do they before both teams are named', namedCategories(wins, null), null);

// What each page announces to a screen reader, which is whatever its block leads with.
const distribution: Answer = {
	kind: 'integer_distribution',
	distribution: {
		minimumValue: -6,
		bucketWidth: 3,
		impossibleValue: 0,
		probabilities: [0.1, 0.15, 0.4, 0.25, 0.1]
	}
};

check(
	'an announced figure carries its sign and what it counts',
	answerSentence(distribution, 'point differential for Toronto Raptors'),
	'Expected +2.0 point differential for Toronto Raptors.'
);

const categories: Answer = {
	kind: 'category_distribution',
	categories: { names: ['home win', 'away win'], probabilities: [0.6324, 0.3676] }
};

check(
	'and an announced category is spoken as it is drawn',
	answerSentence(categories, 'win chances', ['Toronto Raptors win', 'Boston Celtics win']),
	'Win chances, Toronto Raptors win 63.24 percent.'
);

console.log('\nAll model wording checks passed.');
