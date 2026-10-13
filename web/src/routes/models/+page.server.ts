/** Redirects /models to the Models section of the home page. */

import { redirect } from '@sveltejs/kit';

import { MODELS_PATH } from '$lib/models';

export const load = () => redirect(308, MODELS_PATH);
