<!--
	How one model family predicts, and how well.

	It exists so a reader can decide whether to trust that family's numbers, and it is where every
	figure about the family lives. Nothing here moves to /about, whatever the family is.

	The sections and their order are the same for every family, so they are here and a family brings
	only its own name and its own words. The bodies are placeholders. Writing them is the user's to
	settle, and an accuracy table waits on a trained model and a held-out score.
-->
<script lang="ts">
	import ModelGrid from '$lib/components/ModelGrid.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import { familyPath } from '$lib/models';
	import { pageTitle } from '$lib/site';

	import type { ListedFamily } from '$lib/models';
	import type { FamilyAboutModel } from '$lib/types';

	type Props = {
		/** Every family the service names, which is what says whether this one can be predicted with. */
		families: ListedFamily[];
		/** The explanatory card copy this page alone asks the service for, without any figures. */
		models: FamilyAboutModel[];
		/** This family's `name`, as the service gives it. */
		family: string;
		/** The document title, which names the family rather than repeating the page heading. */
		title: string;
		description: string;
	};

	let { families, models, family, title, description }: Props = $props();

	const listed = $derived(families.find(({ name }) => name === family) ?? null);

	// Each carries a stable anchor, so a section can be linked to on its own.
	const SECTIONS = [
		['how', 'How a prediction is made'],
		['which-games', 'Which games can be predicted'],
		['models', 'Models in this family'],
		['inputs', 'What the model reads'],
		['accuracy', 'How accurate it is'],
		['limits', 'What it does not do']
	];
</script>

<svelte:head>
	<title>{pageTitle(title)}</title>
	<meta name="description" content={description} />
</svelte:head>

<div class="page">
	<div class="title">
		<h1 class="page-title">How this model works</h1>

		<!-- Back to the thing the reader came to decide about. -->
		{#if listed?.published}
			<a class="small" href={familyPath(listed)}>Run a prediction</a>
		{/if}
	</div>

	{#if !listed}
		<Notice>No model is listed right now.</Notice>
	{:else}
		{#each SECTIONS as [anchor, heading] (anchor)}
			<section id={anchor}>
				<h2>{heading}</h2>

				{#if anchor === 'models'}
					{#if models.length === 0}
						<Notice>Model details are not available right now.</Notice>
					{:else}
						<ModelGrid {models} {family} />
					{/if}
				{:else if anchor === 'accuracy'}
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
