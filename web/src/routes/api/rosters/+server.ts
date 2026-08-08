/**
 * Both sides of an upcoming game, for the browser.
 *
 * Choosing a game card changes parameters without navigating, so the player list it switches to has
 * to be fetched rather than loaded.
 */

import { json } from '@sveltejs/kit';

import { getRosters, getUpcomingGames } from '$lib/server/api';

import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url }) => {
	const id = Number(url.searchParams.get('game'));
	const game = (await getUpcomingGames()).find((candidate) => candidate.id === id);

	return json(game ? await getRosters(game) : []);
};
