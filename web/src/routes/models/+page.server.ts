/** Every family is listed on the home page, so the path they sit under leads to that section. */

import { redirect } from '@sveltejs/kit';

import { MODELS_PATH } from '$lib/models';

export const load = () => redirect(308, MODELS_PATH);
