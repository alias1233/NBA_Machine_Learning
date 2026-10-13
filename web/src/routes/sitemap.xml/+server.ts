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
