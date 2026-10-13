/** This page's content moved to the family page. The redirect keeps old links working. */

import { redirect } from '@sveltejs/kit';

export const load = () => redirect(308, '/models/player-stats');
