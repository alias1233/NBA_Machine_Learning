import { SITE_ORIGIN, SITE_UPDATED_AT } from '$lib/site';

/**
 * Every page the site asks to be indexed.
 *
 * The prediction pages and their Info pages are not here. Google has crawled them and declined
 * them, and a sitemap that keeps offering pages a crawler keeps refusing is a weaker signal for
 * every URL beside them, the home page included. They carry a matching `noindex` so the two say the
 * same thing. See PageMetadata.svelte.
 */
const paths = ['/', '/about', '/privacy', '/terms-and-conditions'];

export const GET = () => {
	const urls = paths
		.map(
			(path) =>
				`  <url><loc>${new URL(path, SITE_ORIGIN).toString()}</loc><lastmod>${SITE_UPDATED_AT}</lastmod></url>`
		)
		.join('\n');

	return new Response(
		`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>`,
		{ headers: { 'content-type': 'application/xml; charset=utf-8' } }
	);
};
