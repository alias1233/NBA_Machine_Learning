<!--
	How the player game statistics family predicts, and how well. See section 11.4.

	It exists so a reader can decide whether to trust this family's numbers, and it is where every
	figure about the family lives. Nothing here moves to /about, whatever the family is. R11.22.

	The bodies are placeholders. Writing them is an open decision in section 16, and the accuracy
	table waits on the three untrained models and on a held-out score. R11.18 to R11.20.
-->
<script lang="ts">
	import Notice from '$lib/components/Notice.svelte';
	import { pageTitle } from '$lib/site';

	let { data } = $props();

	const FAMILY = 'player_stats';

	const published = $derived(data.families.some(({ name }) => name === FAMILY));

	// Each carries a stable anchor, because the Why? link on the prediction page points at one.
	const sections = [
		['how', 'How a prediction is made'],
		['which-games', 'Which games can be predicted'],
		['inputs', 'What the model reads'],
		['accuracy', 'How accurate it is'],
		['limits', 'What it does not do']
	];
</script>

<svelte:head>
	<title>{pageTitle('Player game statistics, how it works')}</title>
	<meta
		name="description"
		content="How points, rebounds and assists are predicted for one NBA player, and how accurate it is."
	/>
</svelte:head>

<div class="page">
	<h1 class="page-title">How this model works</h1>

	{#if !published}
		<!-- A family with no published model carries no page of its own either. R11.10. -->
		<Notice>No model is published right now.</Notice>
	{:else}
		{#each sections as [anchor, heading] (anchor)}
			<section id={anchor}>
				<h2>{heading}</h2>

				{#if anchor === 'accuracy'}
					<Notice>Accuracy is not published yet. The models are still being trained.</Notice>
				{:else}
					<Notice>This section is not written yet.</Notice>
				{/if}
			</section>
		{/each}
	{/if}
</div>

<style>
	.page {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		scroll-margin-top: var(--space-8);
	}
</style>
