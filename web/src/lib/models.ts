/**
 * The model families the site knows about.
 *
 * A family is named after what a reader has to choose before it can answer: a player, a team, or a
 * game. That is what makes each family a page of its own, because it is what the page asks for.
 *
 * The service says which family each model belongs to and whether it is published. This adds the
 * part only the site knows: the route the family is predicted on, and how it is described to a
 * reader. A family is described here and nowhere else, so the header menu, the home page and the
 * model page all read the same words.
 *
 * Adding a family is one entry here and one folder under `src/routes/models/`.
 *
 * It also holds the words read off a model rather than off an answer: what it predicts, whose number
 * an answer is when it belongs to one side of a game, and the sentence an answer is announced with.
 */

// Relative and extended, so `npm test` can read this file with Node exactly as it stands.
import { CATEGORY_DECIMALS, expectedValue, figureText, sharePercentages } from './odds.ts';

import type { Answer } from './odds.ts';
import type { GameSide, Model } from '$lib/types';

export type ModelFamily = {
	/** Matches the `family` field on a model from the service. */
	name: string;
	/** The path segment under /models. */
	slug: string;
	title: string;
	/** One line, 14 words at most. */
	description: string;
};

export const MODEL_FAMILIES: ModelFamily[] = [
	// Each description covers everything its family holds. Naming two or three of fourteen models
	// reads as the whole list to somebody who has not opened the family yet.
	{
		name: 'player_stats',
		slug: 'player-stats',
		title: 'Player stat models',
		description: 'Points, rebounds, assists and other box score numbers for one player.'
	},
	{
		name: 'team_stats',
		slug: 'team-stats',
		title: 'Team stat models',
		description: 'Points, rebounds, assists and three-pointers for one team.'
	},
	{
		name: 'game_stats',
		slug: 'game-stats',
		title: 'Game stat models',
		description: 'How much one team wins by, the game totals, and who wins.'
	}
];

/**
 * What a model is printed as wherever it is listed rather than run.
 *
 * The words are the model's own, authored beside it in the service, so the home page's index and a
 * family's About page name it identically without either writing the words down again.
 */
export type ListedModel = Pick<Model, 'name' | 'title' | 'description' | 'published'>;

export type ListedFamily = ModelFamily & {
	/** Whether the service holds a trained model in it, which is what makes it predictable. */
	published: boolean;
	/** Everything in the family, in the order the service names it. */
	models: ListedModel[];
};

/** Where every family is listed. The Models tab, the hero's button and /models all lead here. */
export const MODELS_SECTION = 'models';
export const MODELS_PATH = `/#${MODELS_SECTION}`;

export const familyPath = (family: ModelFamily) => `/models/${family.slug}`;

/**
 * The section of a family's own page that lists every model it holds and the figures each has
 * earned, and the link that lands a reader on it.
 */
export const FAMILY_MODELS_SECTION = 'models';

export const familyModelsPath = (family: ModelFamily) =>
	`${familyPath(family)}#${FAMILY_MODELS_SECTION}`;

/**
 * Which stock a page is printed on: the family whose pages it is one of, or null for the site's own.
 *
 * Every plate on the site prints in the same two inks and only the ground changes, so this is the
 * whole of what a family colors. The value is the family's slug, which `app.css` names the grounds
 * by.
 */
export const plateOf = (pathname: string): string | null =>
	MODEL_FAMILIES.find((family) => {
		const path = familyPath(family);

		return pathname === path || pathname.startsWith(`${path}/`);
	})?.slug ?? null;

/**
 * The families to list, and whether each can be predicted with yet.
 *
 * A family the service does not name at all is left out, so a service that is not answering shows
 * the empty state rather than a page of families nothing stands behind. One it names but has not
 * trained is listed and marked, because a family on the way is worth knowing about.
 */
export const listedFamilies = (models: Model[]): ListedFamily[] =>
	MODEL_FAMILIES.map((family) => {
		// Only the four words a listing prints. The rest of a model is what a prediction page needs,
		// and carrying it into every page's data is weight nothing on them reads.
		const held: ListedModel[] = models
			.filter((model) => model.family === family.name)
			.map(({ name, title, description, published }) => ({
				name,
				title,
				description,
				published
			}));

		return {
			...family,
			models: held,
			published: held.some((model) => model.published)
		};
	}).filter((family) => family.models.length > 0);

/**
 * What a model predicts, written out. The service names it in lowercase already, so one model reads
 * "points" and the combined one reads "points, rebounds and assists".
 */
export function predictsPhrase(predicts: string[]): string {
	if (predicts.length < 2) return predicts[0] ?? '';

	return `${predicts.slice(0, -1).join(', ')} and ${predicts.at(-1)}`;
}

export const sentenceCase = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

/** The two sides of the game being asked about, named in full. */
export type GameSides = Record<GameSide, string>;

/**
 * What the lead figure counts and whose it is, for a model read from one side of the game.
 *
 * A game statistic names no team, so nothing but this says which of the two a margin belongs to.
 * Every other family names its subject in the heading already, so it gets nothing here.
 */
export function figureNote(model: Model | null, sides: GameSides | null): string {
	if (!model?.read_from || !sides) return '';

	return `${predictsPhrase(model.predicts)} for ${sides[model.read_from]}`;
}

/**
 * The categories as a reader sees them once a game is chosen.
 *
 * A category naming a side of the game leads with that side's word, so the team playing it goes in
 * place of the word and "home win" is read as "Toronto Raptors win". Null leaves the model's own
 * words, which is every answer naming no side.
 */
export function namedCategories(model: Model | null, sides: GameSides | null): string[] | null {
	const named = model?.category_sides;

	if (!named || !sides || model.output.kind !== 'category_distribution') return null;

	return model.output.categories.map((category, index) => {
		const side = named[index];

		if (!side) return category;

		const rest = category.startsWith(side) ? category.slice(side.length).trim() : category;

		return rest === '' ? sides[side] : `${sides[side]} ${rest}`;
	});
}

/**
 * The one sentence an answer is announced with, which is whatever its block leads with.
 *
 * `names` is what the categories are called for the chosen game, where they name one of its sides.
 */
export function answerSentence(answer: Answer, stat: string, names: string[] | null = null): string {
	if (answer.kind === 'integer_distribution') {
		const { distribution } = answer;

		return `Expected ${figureText(distribution, expectedValue(distribution))} ${stat}.`;
	}

	const { probabilities } = answer.categories;
	const shown = names ?? answer.categories.names;

	return `${sentenceCase(stat)}, ${shown[0]} ${sharePercentages(probabilities, CATEGORY_DECIMALS)[0]} percent.`;
}
