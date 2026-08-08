<script lang="ts">
	import Notice from '$lib/components/Notice.svelte';
	import { pageTitle } from '$lib/site';
</script>

<svelte:head>
	<title>{pageTitle('Privacy')}</title>
	<meta name="description" content="What this site collects and what it sets on your device." />
</svelte:head>

<div class="page">
	<h1 class="page-title">Privacy</h1>

	<!-- The wording is the user's to write or source. Ads stay off until it is real. -->
	<Notice tone="warning">
		This page is not written yet. No ads and no analytics run on this site.
	</Notice>
</div>

<style>
	.page {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}
</style>
