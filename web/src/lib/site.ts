/**
 * What the site calls itself, held in one place so that naming it is one edit.
 *
 * SITE_ORIGIN is baked in at build time, because canonical links, the sitemap and the structured
 * data are the site's identity rather than a setting of the machine it runs on. It has to agree
 * with DOMAIN in deploy/.env, and with the sitemap line at the end of static/robots.txt. Serving
 * this build from another name comes up healthy and advertises the wrong one.
 */

export const SITE_NAME = 'Bazaar Ball';
export const DOMAIN_NAME = `BazaarBall.com`;
export const SITE_ORIGIN = 'https://bazaarball.com';
export const SITE_UPDATED_AT = '2026-08-22';

/** The site metadata description, for searching and indexing. */
export const PRIVATE_SITE_DESCRIPTION = 'Predict player, team, and game statistics of upcoming NBA games with AI through machine learning models, completely for free.';
/** The user facing description, shown on the Hero. */
export const PUBLIC_SITE_DESCRIPTION = `Predict statistics of upcoming NBA games.`;

/**
 * The section of the About page that teaches reading an answer. Every answer block leads here, so
 * the anchor is fixed and the About page holds it.
 */
export const READING_PATH = '/about#reading';

/** The document title. The home page is the site name on its own. */
export const pageTitle = (name?: string) => (name ? `${name} | ${SITE_NAME}` : SITE_NAME + ' | NBA Predictions With AI');

/** A public path, written once so canonical links and structured data cannot disagree. */
export const absoluteUrl = (path: string) => new URL(path, SITE_ORIGIN).toString();

export const longDate = (date: string) =>
	new Intl.DateTimeFormat('en-US', { dateStyle: 'long', timeZone: 'UTC' }).format(
		new Date(`${date}T00:00:00Z`)
	);
