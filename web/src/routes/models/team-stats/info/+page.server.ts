/** The family's models are listed on its own page now. Kept so an indexed link still lands. */

import { redirect } from '@sveltejs/kit';

export const load = () => redirect(308, '/models/team-stats');
