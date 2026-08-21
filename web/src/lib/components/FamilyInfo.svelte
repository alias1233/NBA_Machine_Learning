<!-- The one place to see every model in a family and the figures it has earned. -->
<script lang="ts">
	import ModelIndex from '$lib/components/ModelIndex.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import { familyPath } from '$lib/models';
	import { pageTitle } from '$lib/site';

	import type { ListedFamily } from '$lib/models';
	import type { FamilyInfoModel } from '$lib/types';

	type Props = {
		/** Every family the service names, which is what says whether this one can be predicted with. */
		families: ListedFamily[];
		/** False where the service did not answer at all, which is not the same as nothing being listed. */
		answering: boolean;
		/** The model names and descriptions this page asks the service for, without any figures. */
		models: FamilyInfoModel[];
		/** This family's `name`, as the service gives it. */
		family: string;
		/** The family name used in the document and band titles. */
		title: string;
		description: string;
	};

	let {
		families,
		answering,
		models,
		family,
		title,
		description
	}: Props = $props();

	const listed = $derived(families.find(({ name }) => name === family) ?? null);
</script>

<svelte:head>
	<title>{pageTitle(`${title} info`)}</title>
	<meta name="description" content={description} />
</svelte:head>

<PlateBand title={`${title} info`}>
	{#snippet action()}
		<!-- Back to the thing the reader came to decide about. -->
		{#if listed?.published}
			<a class="small text-link" href={familyPath(listed)}>Run a prediction</a>
		{/if}
	{/snippet}
</PlateBand>

<div class="page reading">
	<!-- A service that never answered is not an empty family, and only one of the two is worth
	     waiting for. -->
	{#if !listed}
		{#if answering}
			<Notice>No model is listed here yet.</Notice>
		{:else}
			<Notice>
				The prediction service is not answering, so there is nothing to describe here yet. Try again
				in a few minutes.
			</Notice>
		{/if}
	{:else}
		<section id="models">
			<h2 class="section-rule">All models</h2>
			<p class="small muted">Select a model to view its evaluation metrics.</p>

			{#if models.length === 0}
				<Notice>Model details could not be read right now. Try again in a few minutes.</Notice>
			{:else}
				<ModelIndex {models} {family} />
			{/if}
		</section>
	{/if}
</div>

<style>
	.reading {
		padding-block-start: var(--space-7);
	}

	section {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
</style>
