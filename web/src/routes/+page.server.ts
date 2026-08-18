import { isHttpError } from '@sveltejs/kit';

import { gameDayNow } from '$lib/games';
import { getShowcase } from '$lib/server/api';
import { drawableSamples } from '$lib/showcase';

import type { Showcase } from '$lib/types';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	// The hero is the only thing on the site that shows an answer nobody asked for, and it must never
	// be the reason the home page fails to render. A service that is not answering, one that has never
	// had the job run against it, and a set whose games have all been played all read as no samples,
	// and the hero draws its plate without them. See python/src/nba_ml/showcase.py.
	let published: Showcase | null = null;
	let answering = true;

	try {
		published = await getShowcase();
	} catch (thrown) {
		// A refusal the service worded is still the service answering, and only this one page is short
		// of something. No reply at all is different: every prediction page is down with it, so the
		// plate says so rather than offering an action that cannot work either.
		answering = !isHttpError(thrown) || thrown.status !== 503;
	}

	// Read once here rather than in the browser. The two clocks can sit on opposite sides of midnight,
	// and a page that renders one set of words on the server and another on arrival is a page that
	// flickers its own caveat.
	const now = Date.now();

	return {
		samples: drawableSamples(published, now),
		answering,
		// A set nobody has rebuilt is still worth drawing while its games are ahead, so long as the
		// page names the morning it was actually drawn on rather than claiming this one.
		heldOver: published && published.built_for !== gameDayNow(now) ? published.built_for : null
	};
};
