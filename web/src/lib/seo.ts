import { AUTHOR } from './owner.ts';
import { absoluteUrl, PRIVATE_SITE_DESCRIPTION, SITE_NAME, SITE_ORIGIN, SITE_UPDATED_AT } from './site.ts';

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

export const authorSchema = (): JsonLd => ({
	'@type': 'Person',
	'@id': absoluteUrl('/about#author'),
	name: AUTHOR.name,
	jobTitle: AUTHOR.jobTitle,
	description: AUTHOR.bio,
	url: absoluteUrl('/about#author')
});

export const webSiteSchema = (): JsonLd => ({
	'@type': 'WebSite',
	'@id': absoluteUrl('/#website'),
	url: SITE_ORIGIN,
	name: SITE_NAME,
	description: PRIVATE_SITE_DESCRIPTION,
	publisher: authorSchema()
});

export const webApplicationSchema = (): JsonLd => ({
	'@type': 'WebApplication',
	'@id': absoluteUrl('/#application'),
	name: SITE_NAME,
	url: SITE_ORIGIN,
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

export const articleSchema = ({ name, description, path }: Page): JsonLd => ({
	'@type': 'Article',
	headline: name,
	description,
	url: absoluteUrl(path),
	datePublished: SITE_UPDATED_AT,
	dateModified: SITE_UPDATED_AT,
	author: authorSchema(),
	publisher: authorSchema(),
	isPartOf: { '@id': absoluteUrl('/#website') }
});

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
