export type PageDates = {
	/** Date the page was first published, as YYYY-MM-DD. */
	published: string;
	/** Date the page's text last changed, as YYYY-MM-DD. */
	updated: string;
};

export type PageEntry = PageDates & {
	/** True if search engines should index the page. */
	indexed: boolean;
};

export const PAGES = {
	'/': { published: '2026-08-06', updated: '2026-09-01', indexed: true },
	'/about': { published: '2026-08-06', updated: '2026-09-01', indexed: true },
	'/models/player-stats': { published: '2026-08-06', updated: '2026-09-01', indexed: true },
	'/models/team-stats': { published: '2026-08-11', updated: '2026-09-01', indexed: true },
	'/models/game-stats': { published: '2026-08-11', updated: '2026-09-01', indexed: true },
	'/privacy': { published: '2026-08-06', updated: '2026-08-22', indexed: true },
	'/terms-and-conditions': { published: '2026-08-21', updated: '2026-08-21', indexed: true }
} as const satisfies Record<string, PageEntry>;

/** Path of a page on the site. */
export type PagePath = keyof typeof PAGES;

const entryOf = (path: string): PageEntry | undefined => PAGES[path as PagePath];

/** Pages listed in the sitemap, in order. */
export const INDEXED_PAGES = Object.entries(PAGES)
	.filter(([, { indexed }]) => indexed)
	.map(([path, { published, updated }]) => ({ path, published, updated }));

/** Returns the dates for a path, or undefined if there is no page there. */
export const datesOf = (path: string): PageDates | undefined => entryOf(path);

/** Returns true if the page at a path should be indexed. Unlisted paths default to true. */
export const isIndexed = (path: string): boolean => entryOf(path)?.indexed ?? true;

/** Most recent update date across all indexed pages. */
export const NEWEST_UPDATE = INDEXED_PAGES.reduce<string>(
	(newest, { updated }) => (updated > newest ? updated : newest),
	PAGES['/'].updated
);
