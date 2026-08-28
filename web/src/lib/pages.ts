/**
 * Every page the site has, the dates each one carries, and whether it asks to be indexed.
 *
 * One entry per page: when it first went up, when its own words last changed, and whether a search
 * engine is asked to hold it. The sitemap is built from this list, every page's robots directive is
 * read off it, the structured data and the article timestamps read their dates off it, and the two
 * policy pages print their own date from it. A page's date is written once here, so nothing that
 * states it can disagree with anything else that states it.
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

export type PageEntry = PageDates & {
	/**
	 * Whether a search engine is asked to hold the page.
	 *
	 * Both halves of the answer come from here. An indexed page is offered in the sitemap and tells
	 * a crawler `index`; a page that is not indexed is left out of the sitemap and tells the crawler
	 * `noindex` on the page itself. The second half is the one that decides it: a sitemap only
	 * advertises, and a page linked from every footer is found and indexed on the strength of that
	 * link whether or not anything advertised it.
	 *
	 * The policy pages are the pages that say no. They exist for a reader who goes looking for them
	 * and for the ad and analytics services that require them, not for anyone arriving from a
	 * search, and neither of them says anything a search engine has a use for. They are still
	 * followed, so the links they carry back into the site still count.
	 */
	indexed: boolean;
};

export const PAGES = {
	'/': { published: '2026-08-06', updated: '2026-08-27', indexed: true },
	'/about': { published: '2026-08-06', updated: '2026-08-27', indexed: true },
	'/models/player-stats': { published: '2026-08-06', updated: '2026-08-27', indexed: true },
	'/models/team-stats': { published: '2026-08-11', updated: '2026-08-27', indexed: true },
	'/models/game-stats': { published: '2026-08-11', updated: '2026-08-27', indexed: true },
	'/privacy': { published: '2026-08-06', updated: '2026-08-22', indexed: false },
	'/terms-and-conditions': { published: '2026-08-21', updated: '2026-08-21', indexed: false }
} as const satisfies Record<string, PageEntry>;

/** A path the site has a page at. */
export type PagePath = keyof typeof PAGES;

const entryOf = (path: string): PageEntry | undefined => PAGES[path as PagePath];

/** The pages the sitemap offers, in the order it offers them. */
export const INDEXED_PAGES = Object.entries(PAGES)
	.filter(([, { indexed }]) => indexed)
	.map(([path, { published, updated }]) => ({ path, published, updated }));

/** The dates a path carries, or nothing where the site has no page at that path. */
export const datesOf = (path: string): PageDates | undefined => entryOf(path);

/**
 * Whether the page at a path asks to be indexed.
 *
 * A path this file does not list is taken to be a page that does, which is what a page added
 * without an entry here would want. Keeping it out of the index is the answer that has to be
 * written down, and lib/pages.test.ts holds every rendered page to having an entry either way.
 */
export const isIndexed = (path: string): boolean => entryOf(path)?.indexed ?? true;

/**
 * The newest date any indexed page carries, which is when the site itself last changed.
 *
 * These are ISO dates, so the newest of two is the later of them in plain alphabetical order.
 */
export const NEWEST_UPDATE = INDEXED_PAGES.reduce<string>(
	(newest, { updated }) => (updated > newest ? updated : newest),
	PAGES['/'].updated
);
