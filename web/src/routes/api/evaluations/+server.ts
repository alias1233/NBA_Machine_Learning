/**
 * What one model measured, for the browser. The prediction service itself is not reachable from one.
 *
 * A family About page draws its cards without figures, so opening a card is what asks for them, and
 * a reader who opens none costs the service nothing.
 */

import { json } from '@sveltejs/kit';

import { getModelEvaluation } from '$lib/server/api';

import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url }) => {
	const family = url.searchParams.get('family') ?? '';
	const model = url.searchParams.get('model') ?? '';

	if (!family || !model) return json(null);

	return json(await getModelEvaluation(family, model));
};
