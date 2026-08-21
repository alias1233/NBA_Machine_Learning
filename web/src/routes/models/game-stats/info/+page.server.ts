import { getFamilyInfoModels } from '$lib/server/api';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => ({
	models: await getFamilyInfoModels('game_stats').catch(() => [])
});
