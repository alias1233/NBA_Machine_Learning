/**
 * What the site checks about itself before it serves anything, and what it puts on what it serves.
 *
 * The domain is written in three places. `SITE_ORIGIN` in `lib/site.ts` is baked into every
 * canonical link and every piece of structured data at build time. `DOMAIN` in the deployment's own
 * environment names the certificate and reaches this process as `ORIGIN`. The sitemap line at the
 * end of `static/robots.txt` names it a third time, and `lib/robots.test.ts` holds those two
 * together.
 *
 * This holds the remaining pair. A build served under a name it does not claim comes up healthy and
 * advertises the wrong one to search engines, which is the kind of fault that is found weeks later
 * in a search console rather than in a log, so it stops the server instead.
 *
 * `ORIGIN` is unset when the site runs locally, and that is not a disagreement.
 */

import { env } from '$env/dynamic/private';

import { SITE_ORIGIN } from '$lib/site';

import type { Handle } from '@sveltejs/kit';

const servedAs = env.ORIGIN?.replace(/\/+$/, '');

if (servedAs && servedAs !== SITE_ORIGIN) {
	throw new Error(
		`This build is for ${SITE_ORIGIN} and is being served as ${servedAs}. ` +
			'SITE_ORIGIN in web/src/lib/site.ts, the Sitemap line in web/static/robots.txt and DOMAIN ' +
			'in deploy/.env all name the same site. Match them, then rebuild.'
	);
}

/** What is worth a validator: the pages, and the sitemap. Everything else is a file with its own. */
const VALIDATED = ['text/html', 'application/xml'];

/**
 * A tag naming exactly what was sent, so asking again is a header rather than a page.
 *
 * Weak, because the proxy in front of this compresses what it forwards and a compressed page is not
 * the same bytes. Weak is also the only comparison `If-None-Match` is defined to make, so nothing
 * is lost by saying so. Half a SHA-256 is far more than enough to tell two versions of one page
 * apart.
 */
async function weakTag(body: ArrayBuffer): Promise<string> {
	const digest = await crypto.subtle.digest('SHA-256', body);
	const hex = Array.from(new Uint8Array(digest, 0, 8), (byte) =>
		byte.toString(16).padStart(2, '0')
	).join('');

	return `W/"${hex}"`;
}

/** Whether what the caller already holds is what it would be sent. `*` means anything at all. */
function alreadyHeld(header: string | null, etag: string): boolean {
	if (!header) return false;
	if (header.trim() === '*') return true;

	const held = etag.replace(/^W\//, '');

	return header.split(',').some((candidate) => candidate.trim().replace(/^W\//, '') === held);
}

/**
 * Gives every rendered page a validator, and answers with it where nothing has changed.
 *
 * A page here is built fresh on every request, so there is no honest moment to call its last
 * modification and nothing but the page itself can say whether it moved. The tag is the page, so a
 * crawler asking whether anything changed is answered by a header rather than by the whole document,
 * and a reader returning to a page they already hold is answered the same way. Bing and Google both
 * ask for this, and both read a site that cannot answer it as one they have to fetch in full every
 * time.
 *
 * The tag is taken over the finished bytes, which means the response is held rather than streamed.
 * Nothing here streams: every page waits for its loaders and renders in one pass.
 */
export const handle: Handle = async ({ event, resolve }) => {
	const response = await resolve(event);
	const type = response.headers.get('content-type') ?? '';

	if (event.request.method !== 'GET' || response.status !== 200) return response;
	if (!VALIDATED.some((validated) => type.startsWith(validated))) return response;

	const body = await response.arrayBuffer();
	const etag = await weakTag(body);
	const headers = new Headers(response.headers);

	headers.set('etag', etag);

	// Without this a browser is free to decide for itself how long a page stays fresh, and the tag
	// above is never asked about. A page holds live data, so it is checked every time and sent again
	// only when it differs.
	if (!headers.has('cache-control')) headers.set('cache-control', 'no-cache');

	if (alreadyHeld(event.request.headers.get('if-none-match'), etag)) {
		headers.delete('content-length');

		return new Response(null, { status: 304, headers });
	}

	return new Response(body, { status: 200, headers });
};
