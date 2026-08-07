/**
 * The model families the site has a page for.
 *
 * The service says which family each model belongs to. This adds the part only the site knows: the
 * route the family is predicted on, and how it is described to a reader. A family is described here
 * and nowhere else, so the header menu, the home page and the model page all read the same words.
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
	}
];

export const familyPath = (family: ModelFamily) => `/models/${family.slug}`;

/**
 * The families a reader can actually predict with.
 *
 * A family with no published model is not listed and carries no menu entry, because a reader has no
 * use for a model that does not exist. R11.8 and R11.9.
 */
export const publishedFamilies = (models: Model[]): ModelFamily[] =>
	MODEL_FAMILIES.filter((family) =>
		models.some((model) => model.family === family.name && model.published)
	);

/**
 * What a model predicts, written out. The service names its stats in lowercase already, so one
 * model reads "points" and the combined one reads "points, rebounds and assists".
 */
export function statPhrase(stats: string[]): string {
	if (stats.length < 2) return stats[0] ?? '';

	return `${stats.slice(0, -1).join(', ')} and ${stats.at(-1)}`;
}

export const sentenceCase = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
