<!--
	How one model family predicts, and how well.

	It exists so a reader can decide whether to trust that family's numbers, and it is where every
	figure about the family lives. Nothing here moves to /about, whatever the family is.

	The sections and their order are the same for every family, so they are here and a family brings
	only its own name and its own words. They are listed down the side of the page, so a reader who
	came for one of them can go straight to it and can see what else the page holds. The bodies are
	placeholders. Writing them is the user's to settle, and an accuracy table waits on a trained model
	and a held-out score.
-->
<script lang="ts">
	import ModelIndex from '$lib/components/ModelIndex.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import SectionIndex from '$lib/components/SectionIndex.svelte';
	import { familyPath } from '$lib/models';
	import { pageTitle } from '$lib/site';

	import type { ListedFamily } from '$lib/models';
	import type { FamilyAboutModel } from '$lib/types';

	type Props = {
		/** Every family the service names, which is what says whether this one can be predicted with. */
		families: ListedFamily[];
		/** False where the service did not answer at all, which is not the same as nothing being listed. */
		answering: boolean;
		/** The explanatory card copy this page alone asks the service for, without any figures. */
		models: FamilyAboutModel[];
		/** This family's `name`, as the service gives it. */
		family: string;
		/** The document title, which names the family rather than repeating the page heading. */
		title: string;
		description: string;
	};

	let { families, answering, models, family, title, description }: Props = $props();

	const listed = $derived(families.find(({ name }) => name === family) ?? null);

	// Each carries a stable anchor, so a section can be linked to on its own. The anchors never
	// change, whatever the heading over them says.
	//
	// Plural throughout, because a family page covers every model in the family and lists all of
	// them under Models in this family.
	const SECTIONS = [
		['how', 'How a prediction is made'],
		['which-games', 'Which games can be predicted'],
		['models', 'Models in this family'],
		['inputs', 'What the models read'],
		['accuracy', 'How accurate they are'],
		['limits', 'What they do not do']
	];
</script>

<svelte:head>
	<title>{pageTitle(title)}</title>
	<meta name="description" content={description} />
</svelte:head>

<!-- These models, plural. The page covers a whole family and lists every model in it. -->
<PlateBand title="How these models work" lede={listed?.description ?? description}>
	{#snippet action()}
		<!-- Back to the thing the reader came to decide about. -->
		{#if listed?.published}
			<a class="small text-link" href={familyPath(listed)}>Run a prediction</a>
		{/if}
	{/snippet}
</PlateBand>

<div class="page reading" class:indexed={listed}>
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
		<SectionIndex sections={SECTIONS} label="Sections of this page" />

		<div class="sections">
			{#each SECTIONS as [anchor, heading] (anchor)}
				<section id={anchor}>
					<h2 class="section-rule">{heading}</h2>

					{#if anchor === 'models'}
						{#if models.length === 0}
							<Notice>Model details could not be read right now. Try again in a few minutes.</Notice>
						{:else}
							<ModelIndex {models} {family} />
						{/if}
					{:else if anchor === 'accuracy'}
						<Notice>Accuracy is not published yet. The models are still being trained.</Notice>
					{:else}
						<Notice>This section is not written yet.</Notice>
					{/if}
				</section>
			{/each}
		</div>
	{/if}
</div>

<style>
	.reading {
		padding-block-start: var(--space-7);
	}

	.sections {
		gap: var(--space-7);
		min-width: 0;
	}

	section {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
</style>
