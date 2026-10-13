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

const VALIDATED = ['text/html', 'application/xml'];

async function weakTag(body: ArrayBuffer): Promise<string> {
	const digest = await crypto.subtle.digest('SHA-256', body);
	const hex = Array.from(new Uint8Array(digest, 0, 8), (byte) =>
		byte.toString(16).padStart(2, '0')
	).join('');

	return `W/"${hex}"`;
}

function alreadyHeld(header: string | null, etag: string): boolean {
	if (!header) return false;
	if (header.trim() === '*') return true;

	const held = etag.replace(/^W\//, '');

	return header.split(',').some((candidate) => candidate.trim().replace(/^W\//, '') === held);
}

/** Adds an ETag to every rendered page and returns 304 when the page has not changed. */
export const handle: Handle = async ({ event, resolve }) => {
	const response = await resolve(event);
	const type = response.headers.get('content-type') ?? '';

	if (event.request.method !== 'GET' || response.status !== 200) return response;
	if (!VALIDATED.some((validated) => type.startsWith(validated))) return response;

	const body = await response.arrayBuffer();
	const etag = await weakTag(body);
	const headers = new Headers(response.headers);

	headers.set('etag', etag);

	if (!headers.has('cache-control')) headers.set('cache-control', 'no-cache');

	if (alreadyHeld(event.request.headers.get('if-none-match'), etag)) {
		headers.delete('content-length');

		return new Response(null, { status: 304, headers });
	}

	return new Response(body, { status: 200, headers });
};
