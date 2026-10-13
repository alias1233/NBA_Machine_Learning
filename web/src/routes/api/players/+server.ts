import { json } from '@sveltejs/kit';

import { searchPlayers } from '$lib/server/api';

import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url }) => {
	const search = url.searchParams.get('search')?.trim() ?? '';

	if (search.length < 2) return json([]);

	return json(await searchPlayers(search));
};
