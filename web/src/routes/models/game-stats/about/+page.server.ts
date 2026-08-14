import { getFamilyAboutModels } from '$lib/server/api';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => ({
	models: await getFamilyAboutModels('game_stats').catch(() => [])
});
