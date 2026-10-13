import { json } from '@sveltejs/kit';

import { getRosters } from '$lib/server/api';

import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url }) => {
	const id = Number(url.searchParams.get('game'));

	if (!Number.isInteger(id) || id <= 0) return json([]);

	return json(await getRosters(id).catch(() => []));
};
