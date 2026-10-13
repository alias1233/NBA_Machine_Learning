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

/** Returns the robots meta directive for a page. */
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

/** Returns the WebSite schema. Other schemas reference it as the site they are part of. */
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

/** Serializes JSON-LD. Escapes `<` so a string cannot close the script tag. */
export const jsonLd = (schema: JsonLd | JsonLd[]) =>
	JSON.stringify(
		Array.isArray(schema)
			? { '@context': 'https://schema.org', '@graph': schema }
			: { '@context': 'https://schema.org', ...schema }
	).replace(/</g, '\\u003c');
