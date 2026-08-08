/**
 * What the site calls itself, held in one place so that naming it is one edit.
 *
 * Both values below are the user's to settle. A page still showing `SITE_NAME` is not finished.
 */

export const SITE_NAME = 'SITE_NAME';

/** The hero's one description line. 12 words at most, one sentence. */
export const SITE_DESCRIPTION = 'Points, rebounds and assists for upcoming NBA games.';

/** The document title. The home page is the site name on its own. */
export const pageTitle = (name?: string) => (name ? `${name} | ${SITE_NAME}` : SITE_NAME);
