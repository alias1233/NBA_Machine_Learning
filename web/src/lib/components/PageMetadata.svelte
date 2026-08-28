<script lang="ts">
	import { AUTHOR } from '$lib/owner';
	import { datesOf } from '$lib/pages';
	import { jsonLd } from '$lib/seo';
	import { absoluteUrl, pageTitle, SITE_NAME } from '$lib/site';

	import type { JsonLd } from '$lib/seo';

	type Props = {
		title?: string;
		description: string;
		/**
		 * The page's own path, which is its canonical URL.
		 *
		 * A prediction page passes the bare path rather than the request it is answering, so every
		 * combination of parameters names one page instead of asking to be indexed as a page of its
		 * own. See lib/pages.ts.
		 */
		path: string;
		schema?: JsonLd | JsonLd[];
		article?: boolean;
	};

	let { title, description, path, schema, article = false }: Props = $props();

	const canonical = $derived(absoluteUrl(path));
	const documentTitle = $derived(pageTitle(title));
	const structuredData = $derived(schema ? jsonLd(schema) : null);
	// The page's own dates, which an article states as its timestamps. See lib/pages.ts.
	const dates = $derived(datesOf(path));
</script>

<svelte:head>
	<title>{documentTitle}</title>
	<meta name="description" content={description} />
	<meta name="author" content={AUTHOR.name} />
	<meta
		name="robots"
		content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
	/>
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
		{#if dates}
			<meta property="article:published_time" content={dates.published} />
			<meta property="article:modified_time" content={dates.updated} />
		{/if}
		<meta property="article:author" content={AUTHOR.name} />
	{/if}

	{#if structuredData}
		{@html `<script type="application/ld+json">${structuredData}</script>`}
	{/if}
</svelte:head>
