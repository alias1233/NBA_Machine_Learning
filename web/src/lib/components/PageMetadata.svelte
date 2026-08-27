<script lang="ts">
	import { AUTHOR } from '$lib/owner';
	import { jsonLd } from '$lib/seo';
	import { absoluteUrl, pageTitle, SITE_NAME, SITE_UPDATED_AT } from '$lib/site';

	import type { JsonLd } from '$lib/seo';

	type Props = {
		title?: string;
		description: string;
		path: string;
		schema?: JsonLd | JsonLd[];
		article?: boolean;
		/**
		 * Kept out of a search index, while its links are still followed.
		 *
		 * The prediction pages and their Info pages take it. They are a form a reader works in rather
		 * than something to read, Google has crawled them and declined to index them, and a set of
		 * URLs a crawler keeps being offered and keeps refusing weakens every other URL offered with
		 * them. They are left out of the sitemap for the same reason. See sitemap.xml/+server.ts.
		 */
		noindex?: boolean;
	};

	let { title, description, path, schema, article = false, noindex = false }: Props = $props();

	const canonical = $derived(absoluteUrl(path));
	const documentTitle = $derived(pageTitle(title));
	const structuredData = $derived(schema ? jsonLd(schema) : null);
	const robots = $derived(
		noindex
			? 'noindex, follow'
			: 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
	);
</script>

<svelte:head>
	<title>{documentTitle}</title>
	<meta name="description" content={description} />
	<meta name="author" content={AUTHOR.name} />
	<meta name="robots" content={robots} />
	<link rel="canonical" href={canonical} />
	<meta property="og:site_name" content={SITE_NAME} />
	<meta property="og:type" content={article ? 'article' : 'website'} />
	<meta property="og:title" content={documentTitle} />
	<meta property="og:description" content={description} />
	<meta property="og:url" content={canonical} />
	<meta name="twitter:card" content="summary" />
	<meta name="twitter:title" content={documentTitle} />
	<meta name="twitter:description" content={description} />

	{#if article}
		<meta property="article:published_time" content={SITE_UPDATED_AT} />
		<meta property="article:modified_time" content={SITE_UPDATED_AT} />
		<meta property="article:author" content={AUTHOR.name} />
	{/if}

	{#if structuredData}
		{@html `<script type="application/ld+json">${structuredData}</script>`}
	{/if}
</svelte:head>
