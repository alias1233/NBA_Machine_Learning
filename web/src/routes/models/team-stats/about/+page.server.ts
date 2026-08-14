import { getFamilyAboutModels } from '$lib/server/api';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => ({
	models: await getFamilyAboutModels('team_stats').catch(() => [])
});
