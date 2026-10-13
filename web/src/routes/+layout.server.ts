import { listedFamilies } from '$lib/models';
import { getHealth, getModels } from '$lib/server/api';

import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async () => {
	// The site still renders if the service is down.
	const [health, models] = await Promise.all([
		getHealth().catch(() => null),
		getModels().catch(() => [])
	]);

	return { health, families: listedFamilies(models) };
};
