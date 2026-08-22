import { articleSchema, faqSchema, jsonLd } from './seo.ts';

function check(what: string, actual: unknown, expected: unknown) {
	if (JSON.stringify(actual) !== JSON.stringify(expected)) {
		throw new Error(`${what}\n  expected ${JSON.stringify(expected)}\n  got      ${JSON.stringify(actual)}`);
	}

	console.log(`ok   ${what}`);
}

const article = articleSchema({
	name: 'About Bazaar Ball',
	description: 'How Bazaar Ball makes NBA predictions.',
	path: '/about'
});

check('article schema uses the canonical URL', article.url, 'https://bazaarball.com/about');
check('article schema names the supplied author', (article.author as { name: string }).name, 'Fatrick Dang');

const document = JSON.parse(
	jsonLd([
		article,
		faqSchema([{ question: 'Is this safe?', answer: ['Yes.', 'Read the terms.'] }])
	])
);

check('multiple schemas share one schema.org graph', document['@graph'].length, 2);
check('FAQ answers remain complete text', document['@graph'][1].mainEntity[0].acceptedAnswer.text, 'Yes. Read the terms.');

console.log('\nAll SEO checks passed.');
