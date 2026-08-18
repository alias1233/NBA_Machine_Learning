<script lang="ts">
	import Notice from '$lib/components/Notice.svelte';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import { pageTitle } from '$lib/site';
</script>

<svelte:head>
	<title>{pageTitle('Privacy')}</title>
	<meta name="description" content="What this site collects and what it sets on your device." />
</svelte:head>

<PlateBand title="Privacy" />

<div class="page">
	<!-- The wording is the user's to write or source. Ads stay off until it is real. -->
	<div class="measure">
		<Notice tone="warning">
			This page is not written yet. No ads and no analytics run on this site.
		</Notice>
	</div>
</div>

<style>
	.page {
		padding-block-start: var(--space-7);
	}
</style>
