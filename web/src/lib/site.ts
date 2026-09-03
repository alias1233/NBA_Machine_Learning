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

/**
 * The other names the site answers to, in the order a search engine should prefer them.
 *
 * Google picks the name it prints beside a result from several places, and where it is not
 * confident enough it prints the bare host instead. A site with no outside references to
 * corroborate its name has to state every form of it itself, and Google's own troubleshooting for
 * exactly that case asks for these two: the name written the way a domain writes it, and the host.
 * Derived rather than typed, so neither can drift from the origin above.
 */
export const SITE_ALTERNATE_NAMES = [SITE_NAME.replace(/\s+/g, ''), new URL(SITE_ORIGIN).host];

/** The site metadata description, for searching and indexing. */
export const PRIVATE_SITE_DESCRIPTION = 'Predict player, team, and game statistics of upcoming NBA games with AI through machine learning models, completely for free.';
/**
 * The user facing description, shown on the Hero and on every page band's lede.
 *
 * On the home page it is also the only `h1`, so it is the one heading a search engine reads as the
 * subject of the site. It says what the site does rather than naming it, because the wordmark
 * printed directly above it has already done that.
 *
 * It says what it costs because that is the thing a reader is looking for a reason to doubt, and
 * because the site's own metadata leads with it. A page whose description promises free and whose
 * words never say it is a page a search engine marks the term missing from.
 */
export const PUBLIC_SITE_DESCRIPTION = `Predict statistics of upcoming NBA games, for free.`;

/**
 * The section of the About page that teaches reading an answer. Every answer block leads here, so
 * the anchor is fixed and the About page holds it.
 */
export const READING_PATH = '/about#reading';

/**
 * The document title: the page's own name and the site's, in that order, and on the home page the
 * site's name and one phrase saying what it does.
 *
 * The home page's is the shape Google's own guidance asks for and the shape every comparable site
 * uses: the name, one delimiter, one descriptive phrase, and no term said twice. Repeating a term
 * or listing variants of it is what its spam policy calls keyword stuffing, and a title doing that
 * is one Google rewrites.
 */
export const pageTitle = (name?: string) =>
	name ? `${name} | ${SITE_NAME}` : `${SITE_NAME} | NBA Predictions with AI`;

/** A public path, written once so canonical links and structured data cannot disagree. */
export const absoluteUrl = (path: string) => new URL(path, SITE_ORIGIN).toString();

export const longDate = (date: string) =>
	new Intl.DateTimeFormat('en-US', { dateStyle: 'long', timeZone: 'UTC' }).format(
		new Date(`${date}T00:00:00Z`)
	);
