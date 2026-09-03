import { AUTHOR } from './owner.ts';
import { datesOf, isIndexed } from './pages.ts';
import { absoluteUrl, PRIVATE_SITE_DESCRIPTION, SITE_ALTERNATE_NAMES, SITE_NAME } from './site.ts';

export type JsonLd = Record<string, unknown>;

type Page = {
	name: string;
	description: string;
	path: string;
};

type FaqQuestion = {
	question: string;
	answer: string[];
};

/**
 * What a page tells a crawler to do with it, read off its entry in pages.ts.
 *
 * An indexed page asks for the whole preview: a full-size image, an untrimmed snippet, and an
 * untrimmed video preview, which is what a search result for a page of writing should be allowed to
 * show. A page that is not indexed says so here rather than only by being left out of the sitemap,
 * because a sitemap advertises and this directive decides. `follow` on that page keeps the links it
 * carries back into the site worth as much as any other link on the site.
 */
export const robotsDirective = (path: string): string =>
	isIndexed(path)
		? 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
		: 'noindex, follow';

export const authorSchema = (): JsonLd => ({
	'@type': 'Person',
	'@id': absoluteUrl('/about#author'),
	name: AUTHOR.name,
	jobTitle: AUTHOR.jobTitle,
	description: AUTHOR.bio,
	url: absoluteUrl('/about#author')
});

/**
 * The site itself, which is the entity every page names as the thing it is part of.
 *
 * This is where the name printed beside a search result comes from, and Google reads it from the
 * home page alone, so the home page is the only page that states it. `url` is the home page's own
 * canonical link rather than the bare origin, so the two agree character for character.
 */
export const webSiteSchema = (): JsonLd => ({
	'@type': 'WebSite',
	'@id': absoluteUrl('/#website'),
	url: absoluteUrl('/'),
	name: SITE_NAME,
	alternateName: SITE_ALTERNATE_NAMES,
	description: PRIVATE_SITE_DESCRIPTION,
	publisher: authorSchema()
});

export const webApplicationSchema = (): JsonLd => ({
	'@type': 'WebApplication',
	'@id': absoluteUrl('/#application'),
	name: SITE_NAME,
	url: absoluteUrl('/'),
	description: PRIVATE_SITE_DESCRIPTION,
	applicationCategory: 'SportsApplication',
	isAccessibleForFree: true,
	author: authorSchema()
});

export const webPageSchema = ({ name, description, path }: Page): JsonLd => ({
	'@type': 'WebPage',
	name,
	description,
	url: absoluteUrl(path),
	isPartOf: { '@id': absoluteUrl('/#website') }
});

/** Dated from the page's own entry in pages.ts, so the schema cannot outlive what it describes. */
export const articleSchema = ({ name, description, path }: Page): JsonLd => {
	const dates = datesOf(path);

	return {
		'@type': 'Article',
		headline: name,
		description,
		url: absoluteUrl(path),
		...(dates && { datePublished: dates.published, dateModified: dates.updated }),
		author: authorSchema(),
		publisher: authorSchema(),
		isPartOf: { '@id': absoluteUrl('/#website') }
	};
};

export const faqSchema = (questions: FaqQuestion[]): JsonLd => ({
	'@type': 'FAQPage',
	mainEntity: questions.map(({ question, answer }) => ({
		'@type': 'Question',
		name: question,
		acceptedAnswer: { '@type': 'Answer', text: answer.join(' ') }
	}))
});

/** JSON-LD is data, not HTML. Escaping `<` keeps an untrusted string from closing its script tag. */
export const jsonLd = (schema: JsonLd | JsonLd[]) =>
	JSON.stringify(
		Array.isArray(schema)
			? { '@context': 'https://schema.org', '@graph': schema }
			: { '@context': 'https://schema.org', ...schema }
	).replace(/</g, '\\u003c');
