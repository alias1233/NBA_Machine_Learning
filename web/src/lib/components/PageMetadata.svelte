<script lang="ts">
	import { AUTHOR } from '$lib/owner';
	import { datesOf } from '$lib/pages';
	import { jsonLd, robotsDirective } from '$lib/seo';
	import { absoluteUrl, pageTitle, SITE_NAME } from '$lib/site';

	import type { JsonLd } from '$lib/seo';

	type Props = {
		title?: string;
		description: string;
		/** Path of the page, used for its canonical URL. */
		path: string;
		schema?: JsonLd | JsonLd[];
		article?: boolean;
	};

	let { title, description, path, schema, article = false }: Props = $props();

	const canonical = $derived(absoluteUrl(path));
	const documentTitle = $derived(pageTitle(title));
	const structuredData = $derived(schema ? jsonLd(schema) : null);
	const dates = $derived(datesOf(path));
	const robots = $derived(robotsDirective(path));
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
