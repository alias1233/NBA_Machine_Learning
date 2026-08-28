import { getMetricDefinitions } from '$lib/server/api';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => ({
	metrics: await getMetricDefinitions().catch(() => [])
});
