<script lang="ts">
	import AdSlot from '$lib/components/AdSlot.svelte';
	import FamilySheet from '$lib/components/FamilySheet.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PageMetadata from '$lib/components/PageMetadata.svelte';
	import ShowcasePlate from '$lib/components/ShowcasePlate.svelte';
	import SiteBrief from '$lib/components/SiteBrief.svelte';
	import { listedFamilies, MODELS_PATH, MODELS_SECTION } from '$lib/models';
	import { webApplicationSchema, webSiteSchema } from '$lib/seo';
	import { PRIVATE_SITE_DESCRIPTION } from '$lib/site';
	import { isTap } from '$lib/touch';

	let { data } = $props();

	let activeTouchFamily = $state<string | null>(null);
	let touchStartedOutside: { id: number; x: number; y: number } | null = null;

	function touchFamily(event: PointerEvent) {
		if (event.pointerType !== 'touch') return;

		const section = document.getElementById(MODELS_SECTION);
		const family =
			section?.contains(event.target as Node) && event.target instanceof Element
				? event.target.closest<HTMLElement>('[data-family]')
				: null;

		if (family?.dataset.family) {
			activeTouchFamily = family.dataset.family;
			touchStartedOutside = null;
			return;
		}

		touchStartedOutside = { id: event.pointerId, x: event.clientX, y: event.clientY };
	}

	function releaseTouchFamily(event: PointerEvent) {
		if (event.pointerType !== 'touch' || touchStartedOutside?.id !== event.pointerId) return;

		if (isTap(touchStartedOutside, event)) activeTouchFamily = null;

		touchStartedOutside = null;
	}
</script>

<PageMetadata
	description={PRIVATE_SITE_DESCRIPTION}
	path="/"
	schema={[webSiteSchema(), webApplicationSchema()]}
/>

<ShowcasePlate samples={data.samples} heldOver={data.heldOver} answering={data.answering} />

<svelte:window
	onpointerdown={touchFamily}
	onpointerup={releaseTouchFamily}
	onpointercancel={() => (touchStartedOutside = null)}
/>

<div class="over-plate">
	<section class="models lands-flush" id={MODELS_SECTION}>
		<a class="models-tab" href={MODELS_PATH}>Models</a>

		<div class="page inside">
			<div class="head">
				<h2 class="page-title type-h1">Models</h2>
			</div>

			{#if data.families.length === 0}
				{#if data.health}
					<Notice>No model is published yet.</Notice>
				{:else}
					<Notice>No model can be listed while the prediction service is not answering.</Notice>
				{/if}
			{:else}
				<ul class="families">
					{#each data.families as family (family.name)}
						<FamilySheet {family} touchActive={activeTouchFamily === family.name} />
					{/each}
				</ul>
			{/if}

			<p class="more muted">More models <span class="tag micro">Coming soon</span></p>

			<AdSlot place="homeModels" />
		</div>
	</section>

	<SiteBrief />
</div>

<style>
	/* Positioned so this section paints over the sticky hero and not under it. */
	.over-plate {
		position: relative;
		display: flex;
		flex-direction: column;
		background: var(--page);
	}

	.models {
		position: relative;
		display: flex;
		flex-direction: column;
		padding-block: var(--space-6) var(--space-5);
	}

	.models-tab {
		position: absolute;
		inset-block-end: 100%;
		inset-inline-start: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		min-block-size: var(--tap-target);
		inline-size: max(calc(var(--tap-target) * 4), 20vw);
		padding-inline: var(--space-5);
		background: var(--page);
		border: var(--rule);
		border-block-end: 0;
		clip-path: polygon(0 0, calc(100% - var(--space-3)) 0, 100% 100%, 0 100%);
		color: var(--ink);
		font-size: var(--type-small);
		font-weight: 700;
		text-decoration: none;
		white-space: nowrap;
		transition: color var(--motion-fast) var(--ease-in);
	}

	.models-tab:hover {
		color: var(--plane-accent);
	}

	.inside {
		display: flex;
		flex: 1;
		flex-direction: column;
		gap: var(--space-5);
	}

	.families {
		display: grid;
		flex: 1;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
		grid-auto-rows: minmax(var(--models-frame-min-height), auto);
		gap: var(--space-5);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.more {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-3);
	}

	@media (min-width: 64rem) and (orientation: landscape) {
		.models {
			padding-block: var(--space-5);
			min-height: 100svh;
		}

		.families {
			grid-template-columns: repeat(3, minmax(0, 1fr));
			grid-template-rows: minmax(0, 1fr);
			grid-auto-rows: minmax(0, 1fr);
			min-height: 0;
			padding-block-end: calc(var(--models-frame-stagger) * 2);
		}

		:global(.families > .family:nth-child(2)) {
			translate: 0 var(--models-frame-stagger);
		}

		:global(.families > .family:nth-child(3)) {
			translate: 0 calc(var(--models-frame-stagger) * 2);
		}
	}
</style>
