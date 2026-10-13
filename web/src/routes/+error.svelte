<script lang="ts">
	import { page } from '$app/state';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import { pageTitle } from '$lib/site';

	const missing = $derived(page.status === 404);
	const heading = $derived(missing ? 'Page not found' : 'Something went wrong');
	const line = $derived(
		missing
			? 'That page does not exist. It may have moved, or the address may have a typo in it.'
			: 'This page could not be loaded. Try again in a moment.'
	);
</script>

<svelte:head>
	<title>{pageTitle(heading)}</title>
	<meta name="robots" content="noindex, nofollow" />
</svelte:head>

<PlateBand title={heading} lede={line}>
	{#snippet action()}
		<a class="text-link" href="/">Go to the home page</a>
	{/snippet}
</PlateBand>
