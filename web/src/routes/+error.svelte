<!--
	Covers 404 and everything else. A heading, one line, and a link home. See section 11.7.

	The reader is never shown a status code or the name of a service that failed. R11.25.
-->
<script lang="ts">
	import { page } from '$app/state';

	const missing = $derived(page.status === 404);
</script>

<svelte:head>
	<title>{missing ? 'Page not found' : 'Something went wrong'}</title>
</svelte:head>

<div class="page">
	<h1 class="page-title">{missing ? 'Page not found' : 'Something went wrong'}</h1>
	<p>{missing ? 'That page does not exist.' : 'The page could not be loaded. Try again shortly.'}</p>
	<a href="/">Go home</a>
</div>

<style>
	.page {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-4);
	}

	a {
		display: inline-flex;
		align-items: center;
		min-height: var(--tap-target);
	}
</style>
