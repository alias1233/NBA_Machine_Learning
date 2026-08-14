<!--
	How one model family predicts, and how well.

	It exists so a reader can decide whether to trust that family's numbers, and it is where every
	figure about the family lives. Nothing here moves to /about, whatever the family is.

	The five sections and their order are the same for every family, so they are here and a family
	brings only its own name and its own words. The bodies are placeholders. Writing them is the
	user's to settle, and an accuracy table waits on a trained model and a held-out score.
-->
<script lang="ts">
	import Notice from '$lib/components/Notice.svelte';
	import { familyPath } from '$lib/models';
	import { pageTitle } from '$lib/site';
	import { prefersReducedMotion } from 'svelte/motion';

	import type { ListedFamily } from '$lib/models';
	import type { FamilyAboutModel } from '$lib/types';

	type Props = {
		/** Every family the service names, which is what says whether this one can be predicted with. */
		families: ListedFamily[];
		/** The explanatory card copy this page alone asks the service for. */
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

	const railId = $derived(`family-models-${family}`);

	let rail = $state<HTMLUListElement>();
	let atStart = $state(true);
	let atEnd = $state(false);

	function updateRailPosition() {
		if (!rail) return;

		atStart = rail.scrollLeft <= 1;
		atEnd = rail.scrollLeft + rail.clientWidth >= rail.scrollWidth - 1;
	}

	function moveRail(direction: -1 | 1) {
		rail?.scrollBy({
			left: rail.clientWidth * direction,
			behavior: prefersReducedMotion.current ? 'auto' : 'smooth'
		});
	}

	$effect(() => {
		if (!rail) return;

		const observer = new ResizeObserver(updateRailPosition);
		observer.observe(rail);
		updateRailPosition();

		return () => observer.disconnect();
	});
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
						<div class="rail">
							<div class="rail-controls">
								<button
									type="button"
									class="button button--quiet"
									aria-controls={railId}
									disabled={atStart}
									onclick={() => moveRail(-1)}
								>
									Previous
								</button>
								<button
									type="button"
									class="button button--quiet"
									aria-controls={railId}
									disabled={atEnd}
									onclick={() => moveRail(1)}
								>
									Next
								</button>
							</div>

							<ul
								id={railId}
								class="model-cards"
								aria-label="Models in this family"
								bind:this={rail}
								onscroll={updateRailPosition}
							>
								{#each models as model (model.name)}
									<li>
										<article class="block model-card">
											<h3>{model.title}</h3>
											<p class="small muted">{model.description}</p>

											{#if !model.published}
												<span class="tag micro">Not published yet</span>
											{/if}
										</article>
									</li>
								{/each}
							</ul>
						</div>
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

	.rail {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		min-width: 0;
	}

	.rail-controls {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3);
	}

	.model-cards {
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: min(100%, var(--model-rail-card));
		gap: var(--space-4);
		margin: 0;
		padding: 0;
		overflow-x: auto;
		scroll-behavior: smooth;
		scroll-snap-type: x mandatory;
		overscroll-behavior-x: contain;
		list-style: none;
	}

	.model-cards > li {
		scroll-snap-align: start;
	}

	.model-card {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-4);
		min-height: calc(var(--space-8) * 2);
	}

	@media (prefers-reduced-motion: reduce) {
		.model-cards {
			scroll-behavior: auto;
		}
	}
</style>
