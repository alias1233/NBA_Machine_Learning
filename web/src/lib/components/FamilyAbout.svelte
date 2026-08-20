<!--
	What one model family predicts, and how well.

	It exists so a reader can decide whether to trust that family's numbers, and it is where every
	figure about the family lives.

	The page is two sections. The first is the family's own words, which no two families share, so it
	is a snippet the family page writes rather than copy kept here. The second is every model in the
	family and what each one measured, which is the same shape for all of them and so is built here.
	Anything true of every family belongs on /about instead, because a family page would otherwise
	restate it once per family.

	A family with more of its own to say passes `extra`: further whole sections, each with its own
	anchor and heading, listed down the side with the rest. They follow the family's words and come
	before the models, because the models are what a reader scrolls to the end for.
-->
<script lang="ts">
	import ModelIndex from '$lib/components/ModelIndex.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import SectionIndex from '$lib/components/SectionIndex.svelte';
	import { familyPath } from '$lib/models';
	import { pageTitle } from '$lib/site';

	import type { Snippet } from 'svelte';
	import type { ListedFamily } from '$lib/models';
	import type { FamilyAboutModel } from '$lib/types';

	/** A section a family adds to the two every family has. */
	type ExtraSection = {
		/** Its place on the page, which is what the index and any link to it use. */
		anchor: string;
		heading: string;
		body: Snippet;
	};

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
		/** This family's own account of itself, written by the family's page. */
		overview: Snippet;
		/** Whole sections this family alone holds, between its overview and its models. */
		extra?: ExtraSection[];
	};

	let {
		families,
		answering,
		models,
		family,
		title,
		description,
		overview,
		extra = []
	}: Props = $props();

	const listed = $derived(families.find(({ name }) => name === family) ?? null);

	// Each carries a stable anchor, so a section can be linked to on its own. The anchors never
	// change, whatever the heading over them says.
	//
	// Plural throughout, because a family page covers every model in the family and lists all of
	// them under Models in this family.
	const sections = $derived([
		{ anchor: 'overview', heading: 'What these models predict', body: overview },
		...extra,
		{ anchor: 'models', heading: 'Models in this family', body: undefined }
	]);

	const index = $derived(sections.map(({ anchor, heading }) => [anchor, heading]));
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
		<SectionIndex sections={index} label="Sections of this page" />

		<div class="sections">
			{#each sections as { anchor, heading, body } (anchor)}
				<section id={anchor}>
					<h2 class="section-rule">{heading}</h2>

					{#if body}
						{@render body()}
					{:else if models.length === 0}
						<Notice>Model details could not be read right now. Try again in a few minutes.</Notice>
					{:else}
						<ModelIndex {models} {family} />
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

	/* A 76rem page would set a line nobody can track back, so running text is capped by measure. */
	section :global(p),
	section :global(h3) {
		max-width: var(--measure);
	}
</style>
