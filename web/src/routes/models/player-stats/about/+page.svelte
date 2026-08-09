<!--
	How the player game statistics family predicts, and how well.

	It exists so a reader can decide whether to trust this family's numbers, and it is where every
	figure about the family lives. Nothing here moves to /about, whatever the family is.

	The bodies are placeholders. Writing them is the user's to settle, and the accuracy table waits
	on the three untrained models and on a held-out score.
-->
<script lang="ts">
	import Notice from '$lib/components/Notice.svelte';
	import { familyPath } from '$lib/models';
	import { pageTitle } from '$lib/site';

	let { data } = $props();

	const FAMILY = 'player_stats';

	const family = $derived(data.families.find(({ name }) => name === FAMILY) ?? null);

	// Each carries a stable anchor, so a section can be linked to on its own.
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
	<div class="title">
		<h1 class="page-title">How this model works</h1>

		<!-- Back to the thing the reader came to decide about. -->
		{#if family?.published}
			<a class="small" href={familyPath(family)}>Run a prediction</a>
		{/if}
	</div>

	{#if !family?.published}
		<!-- A family with no published model carries no page of its own either. -->
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

	.title {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
	}

	.title a {
		display: inline-flex;
		align-items: center;
		min-height: var(--tap-target);
	}

	section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
</style>
