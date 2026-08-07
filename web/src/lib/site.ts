/**
 * What the site calls itself, held in one place so that naming it is one edit.
 *
 * Both values below are open decisions in section 16 of `docs/WEBSITE_DESIGN_DOCUMENT.md`. A page
 * that still shows `SITE_NAME` is not finished.
 */

export const SITE_NAME = 'SITE_NAME';

/** The landing screen's one description line. 12 words at most, one sentence. */
export const SITE_DESCRIPTION = 'Points, rebounds and assists for upcoming NBA games.';

/** The document title. The landing screen is the site name on its own. */
export const pageTitle = (name?: string) => (name ? `${name} | ${SITE_NAME}` : SITE_NAME);
