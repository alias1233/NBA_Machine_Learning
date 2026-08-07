import { publishedFamilies } from '$lib/models';
import { getHealth, getModels } from '$lib/server/api';

import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async () => {
	// A dead service must not blank the whole site. Every page below still renders, the footer says
	// the service is not answering, and no family is offered rather than one that cannot answer.
	const [health, models] = await Promise.all([
		getHealth().catch(() => null),
		getModels().catch(() => [])
	]);

	return { health, families: publishedFamilies(models) };
};
