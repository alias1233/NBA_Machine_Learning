import { isHttpError } from '@sveltejs/kit';

import { gameDayNow } from '$lib/games';
import { getShowcase } from '$lib/server/api';
import { drawableSamples } from '$lib/showcase';

import type { Showcase } from '$lib/types';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	let published: Showcase | null = null;
	let answering = true;

	try {
		published = await getShowcase();
	} catch (thrown) {
		// The service counts as reachable unless the error is a 503.
		answering = !isHttpError(thrown) || thrown.status !== 503;
	}

	// Read once, so the server and the browser use the same date.
	const now = Date.now();

	return {
		samples: drawableSamples(published, now),
		answering,
		heldOver: published && published.built_for !== gameDayNow(now) ? published.built_for : null
	};
};
