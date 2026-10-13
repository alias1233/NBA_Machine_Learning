export const SITE_NAME = 'Bazaar Ball';
export const DOMAIN_NAME = `BazaarBall.com`;
export const SITE_ORIGIN = 'https://bazaarball.com';

/** Alternate names for the site, in the order search engines should prefer them. */
export const SITE_ALTERNATE_NAMES = [SITE_NAME.replace(/\s+/g, ''), new URL(SITE_ORIGIN).host];

/** The site metadata description, for searching and indexing. */
export const PRIVATE_SITE_DESCRIPTION = 'Predict player, team, and game statistics of upcoming NBA games with AI through machine learning models, completely for free.';
/** The user facing description, shown on the Hero and on every page band's lede. */
export const PUBLIC_SITE_DESCRIPTION = `Predict statistics of upcoming NBA games, for free.`;

/** About page section that explains how to read a prediction. */
export const READING_PATH = '/about#reading';

/** Returns the document title. The page name comes first, then the site name. */
export const pageTitle = (name?: string) =>
	name ? `${name} | ${SITE_NAME}` : `${SITE_NAME} | NBA Predictions with AI`;

export const absoluteUrl = (path: string) => new URL(path, SITE_ORIGIN).toString();

export const longDate = (date: string) =>
	new Intl.DateTimeFormat('en-US', { dateStyle: 'long', timeZone: 'UTC' }).format(
		new Date(`${date}T00:00:00Z`)
	);
