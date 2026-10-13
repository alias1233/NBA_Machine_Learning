/** The model list moved to the family page. The redirect keeps indexed links working. */

import { redirect } from '@sveltejs/kit';

export const load = () => redirect(308, '/models/team-stats');
