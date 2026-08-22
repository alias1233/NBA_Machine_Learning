/**
 * What the site calls itself, held in one place so that naming it is one edit.
 */

export const SITE_NAME = 'Bazaar Ball';
export const DOMAIN_NAME = `BazaarBall.com`;

/** The hero's one description line. 12 words at most, one sentence. */
export const SITE_DESCRIPTION = 'Predict player, team, and game statistics of upcoming NBA games using machine learning models for free.';

/**
 * The section of the About page that teaches reading an answer. Every answer block leads here, so
 * the anchor is fixed and the About page holds it.
 */
export const READING_PATH = '/about#reading';

/** The document title. The home page is the site name on its own. */
export const pageTitle = (name?: string) => (name ? `${name} | ${SITE_NAME}` : SITE_NAME);
