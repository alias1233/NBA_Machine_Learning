/**
 * The model families the site knows about.
 *
 * The service says which family each model belongs to and whether it is published. This adds the
 * part only the site knows: the route the family is predicted on, and how it is described to a
 * reader. A family is described here and nowhere else, so the header menu, the home page and the
 * model page all read the same words.
 *
 * Adding a family is one entry here and one folder under `src/routes/models/`.
 */

import type { Model } from '$lib/types';

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
		title: 'Player game statistics',
		description: 'Points, rebounds and assists for one player in one game.'
	},
	{
		name: 'team_game_stats',
		slug: 'team-game-stats',
		title: 'Team game statistics',
		description: 'How much a team wins by, how much it scores, and the game total.'
	}
];

export type ListedFamily = ModelFamily & {
	/** Whether the service holds a trained model in it, which is what makes it predictable. */
	published: boolean;
};

/** Where every family is listed. The Models tab, the hero's button and /models all lead here. */
export const MODELS_SECTION = 'models';
export const MODELS_PATH = `/#${MODELS_SECTION}`;

export const familyPath = (family: ModelFamily) => `/models/${family.slug}`;

/** How that family predicts, and how well. Every figure about a family lives there. */
export const familyAboutPath = (family: ModelFamily) => `${familyPath(family)}/about`;

/**
 * The families to list, and whether each can be predicted with yet.
 *
 * A family the service does not name at all is left out, so a service that is not answering shows
 * the empty state rather than a page of families nothing stands behind. One it names but has not
 * trained is listed and marked, because a family on the way is worth knowing about.
 */
export const listedFamilies = (models: Model[]): ListedFamily[] =>
	MODEL_FAMILIES.filter((family) => models.some((model) => model.family === family.name)).map(
		(family) => ({
			...family,
			published: models.some((model) => model.family === family.name && model.published)
		})
	);

/**
 * What a model predicts, written out. The service names it in lowercase already, so one model reads
 * "points" and the combined one reads "points, rebounds and assists".
 */
export function predictsPhrase(predicts: string[]): string {
	if (predicts.length < 2) return predicts[0] ?? '';

	return `${predicts.slice(0, -1).join(', ')} and ${predicts.at(-1)}`;
}

export const sentenceCase = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
