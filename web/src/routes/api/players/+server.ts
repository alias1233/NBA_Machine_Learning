/** Player search for the browser. The prediction service itself is not reachable from one. */

import { json } from '@sveltejs/kit';

import { searchPlayers } from '$lib/server/api';

import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url }) => {
	const search = url.searchParams.get('search')?.trim() ?? '';

	if (search.length < 2) return json([]);

	return json(await searchPlayers(search));
};
