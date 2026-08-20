/**
 * Both sides of an upcoming game, for the browser.
 *
 * Choosing a game card changes parameters without navigating, so the player lists it switches to,
 * and the lineup change each side expects, have to be fetched rather than loaded.
 */

import { json } from '@sveltejs/kit';

import { getRosters } from '$lib/server/api';

import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url }) => {
	const id = Number(url.searchParams.get('game'));

	if (!Number.isInteger(id) || id <= 0) return json([]);

	return json(await getRosters(id).catch(() => []));
};
