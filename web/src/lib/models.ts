// Relative path with the .ts extension, so Node can run this file in `npm test`.
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

/** Fields shown for a model in a list. */
export type ListedModel = Pick<Model, 'name' | 'title' | 'description' | 'published'>;

export type ListedFamily = ModelFamily & {
	/** True if the family has at least one trained model. */
	published: boolean;
	/** All models in the family, in the order the service returns them. */
	models: ListedModel[];
};

export const MODELS_SECTION = 'models';
export const MODELS_PATH = `/#${MODELS_SECTION}`;

export const familyPath = (family: ModelFamily) => `/models/${family.slug}`;

export const FAMILY_MODELS_SECTION = 'models';

export const familyModelsPath = (family: ModelFamily) =>
	`${familyPath(family)}#${FAMILY_MODELS_SECTION}`;

/** Returns the slug of the family a path belongs to, or null if it is not a family page. */
export const plateOf = (pathname: string): string | null =>
	MODEL_FAMILIES.find((family) => {
		const path = familyPath(family);

		return pathname === path || pathname.startsWith(`${path}/`);
	})?.slug ?? null;

export const listedFamilies = (models: Model[]): ListedFamily[] =>
	MODEL_FAMILIES.map((family) => {
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

/** Joins the predicted stats into a phrase, such as "points" or "points, rebounds and assists". */
export function predictsPhrase(predicts: string[]): string {
	if (predicts.length < 2) return predicts[0] ?? '';

	return `${predicts.slice(0, -1).join(', ')} and ${predicts.at(-1)}`;
}

export const sentenceCase = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

/** Full team names for the home and away sides of a game. */
export type GameSides = Record<GameSide, string>;

/** Returns the stat and the team it is counted for, for a model tied to one side of the game. */
export function figureNote(model: Model | null, sides: GameSides | null): string {
	if (!model?.read_from || !sides) return '';

	return `${predictsPhrase(model.predicts)} for ${sides[model.read_from]}`;
}

/** Returns the category names with team names filled in, or null to keep the model's own names. */
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

export function answerSentence(answer: Answer, stat: string, names: string[] | null = null): string {
	if (answer.kind === 'integer_distribution') {
		const { distribution } = answer;

		return `Expected ${figureText(distribution, expectedValue(distribution))} ${stat}.`;
	}

	const { probabilities } = answer.categories;
	const shown = names ?? answer.categories.names;

	return `${sentenceCase(stat)}, ${shown[0]} ${sharePercentages(probabilities, CATEGORY_DECIMALS)[0]} percent.`;
}
