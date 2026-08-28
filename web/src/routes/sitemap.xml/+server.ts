/**
 * Every page the site asks to be indexed, each dated with the day its own words last changed.
 *
 * The set and the dates are in `lib/pages.ts`, so adding a page is one entry there rather than a
 * list here that has to be remembered separately. The file itself carries the newest of those dates
 * as its own `Last-Modified`, which is true of it: nothing in it is newer than that.
 */

import { INDEXED_PAGES, NEWEST_UPDATE } from '$lib/pages';
import { SITE_ORIGIN } from '$lib/site';

export const GET = () => {
	const urls = INDEXED_PAGES.map(
		({ path, updated }) =>
			`  <url><loc>${new URL(path, SITE_ORIGIN).toString()}</loc><lastmod>${updated}</lastmod></url>`
	).join('\n');

	return new Response(
		`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>`,
		{
			headers: {
				'content-type': 'application/xml; charset=utf-8',
				'last-modified': new Date(`${NEWEST_UPDATE}T00:00:00Z`).toUTCString()
			}
		}
	);
};
