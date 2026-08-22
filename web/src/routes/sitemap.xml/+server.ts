import { SITE_ORIGIN, SITE_UPDATED_AT } from '$lib/site';

const paths = [
	'/',
	'/about',
	'/models/player-stats',
	'/models/player-stats/info',
	'/models/team-stats',
	'/models/team-stats/info',
	'/models/game-stats',
	'/models/game-stats/info',
	'/privacy',
	'/terms-and-conditions'
];

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
