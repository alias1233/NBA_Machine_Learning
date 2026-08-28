/**
 * Every page the site asks to be indexed, and the dates each one carries.
 *
 * One entry per page: when it first went up, and when its own words last changed. The sitemap is
 * built from this list, the structured data and the article timestamps read their dates off it, and
 * the two policy pages print their own date from it. A page's date is written once here, so nothing
 * that states it can disagree with anything else that states it.
 *
 * `updated` is edited in the same change as the page it belongs to. It says when the words changed,
 * not when the site was last built, so a deployment that touched nothing on a page leaves its date
 * where it is. A search engine that is told four pages changed on one day, every day, learns to
 * ignore the claim.
 *
 * What is missing from this list is deliberate. A prediction page carrying a query string is one
 * page per combination of parameters: each of them names the bare page as its canonical URL and
 * static/robots.txt refuses the query string to every crawler, so the page is offered once and the
 * combinations are never offered at all.
 */

export type PageDates = {
	/** When the page first went up, as YYYY-MM-DD. */
	published: string;
	/** When its own words last changed, as YYYY-MM-DD. */
	updated: string;
};

export const PAGE_DATES = {
	'/': { published: '2026-08-06', updated: '2026-08-27' },
	'/about': { published: '2026-08-06', updated: '2026-08-27' },
	'/models/player-stats': { published: '2026-08-06', updated: '2026-08-27' },
	'/models/player-stats/info': { published: '2026-08-21', updated: '2026-08-27' },
	'/models/team-stats': { published: '2026-08-11', updated: '2026-08-27' },
	'/models/team-stats/info': { published: '2026-08-21', updated: '2026-08-27' },
	'/models/game-stats': { published: '2026-08-11', updated: '2026-08-27' },
	'/models/game-stats/info': { published: '2026-08-21', updated: '2026-08-27' },
	'/privacy': { published: '2026-08-06', updated: '2026-08-22' },
	'/terms-and-conditions': { published: '2026-08-21', updated: '2026-08-21' }
} as const satisfies Record<string, PageDates>;

/** The same pages as a list, in the order the sitemap offers them. */
export const INDEXED_PAGES = Object.entries(PAGE_DATES).map(([path, dates]) => ({
	path,
	...dates
}));

/** The dates a path carries, or nothing where the site does not offer that path for indexing. */
export const datesOf = (path: string): PageDates | undefined =>
	PAGE_DATES[path as keyof typeof PAGE_DATES];

/**
 * The newest date any indexed page carries, which is when the site itself last changed.
 *
 * These are ISO dates, so the newest of two is the later of them in plain alphabetical order.
 */
export const NEWEST_UPDATE = INDEXED_PAGES.reduce<string>(
	(newest, { updated }) => (updated > newest ? updated : newest),
	PAGE_DATES['/'].updated
);
