/** What this page held is on the family's own page now. Kept so an older link still lands. */

import { redirect } from '@sveltejs/kit';

export const load = () => redirect(308, '/models/game-stats');
