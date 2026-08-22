<!-- One model family in a shaped home-page frame. It starts hollow and fills with the block plane on
     hover or keyboard focus. -->
<script lang="ts">
	import ModelRoll from '$lib/components/ModelRoll.svelte';
	import { familyInfoPath, familyPath } from '$lib/models';

	import type { ListedFamily, ListedModel } from '$lib/models';

	type Props = {
		family: ListedFamily;
		/** A touch keeps its frame filled until the reader taps somewhere else. */
		touchActive?: boolean;
	};

	let { family, touchActive = false }: Props = $props();

	const models = $derived(family.models);
	let rollPosition = $state(0);
</script>

{#snippet modelEntry(model: ListedModel)}
	<p class="name">{model.title}</p>
	<p class="what">{model.description}</p>
	{#if !model.published}
		<p class="tag micro">Not trained yet</p>
	{/if}
{/snippet}

{#snippet familyContent(masked: boolean)}
	<div class:masked-content={masked} class="family-content">
		<div class="said">
			<h3 class="type-h2">{family.title}</h3>
			<p class="words">{family.description}</p>
		</div>

		<div class="index">
			<p class="count micro">{models.length} {models.length === 1 ? 'model' : 'models'}</p>

			{#if masked}
				<ModelRoll {models} label={family.title} position={rollPosition} passive>
					{#snippet entry(model)}
						{@render modelEntry(model)}
					{/snippet}
				</ModelRoll>
			{:else}
				<ModelRoll {models} label={family.title} bind:position={rollPosition}>
					{#snippet entry(model)}
						{@render modelEntry(model)}
					{/snippet}
				</ModelRoll>
			{/if}
		</div>

		<div class="ways">
			{#if family.published}
				{#if masked}
					<span class="button">Run a prediction</span>
					<span class="small text-link">More info about these models</span>
				{:else}
					<a class="button" href={familyPath(family)}>Run a prediction</a>
					<a class="small text-link" href={familyInfoPath(family)}>More info about these models</a>
				{/if}
			{:else}
				<span class="tag micro">Not published yet</span>
			{/if}
		</div>
	</div>
{/snippet}

<li
	class="family"
	class:touch-active={touchActive}
	data-family={family.name}
	data-plate={family.slug}
	style:--frame-clip={`url(#family-frame-${family.slug})`}
>
	<!-- The normalized path lets the HTML fill retain the SVG frame's exact shape at every size. -->
	<svg class="frame-clip" aria-hidden="true">
		<defs>
			<clipPath id={`family-frame-${family.slug}`} clipPathUnits="objectBoundingBox">
				<path
					d="M.0173077.0081818h.4923077c.0211538 0 .0403846.0045455.0538462.0127273l.0423077.0263636c.0115385.0072727.0307692.0109091.05.0109091h.3269231c.0096154 0 .0173077.0036364.0173077.0081818v.9254545c0 .0045455-.0076923.0081818-.0173077.0081818H.0173077c-.0096154 0-.0173077-.0036364-.0173077-.0081818V.0163636c0-.0045455.0076923-.0081818.0173077-.0081818Z"
				/>
			</clipPath>
		</defs>
	</svg>

	<!-- A flipped press cut. The step at the upper-right leaves the page showing through the frame. -->
	<svg class="frame" viewBox="0 0 520 1100" preserveAspectRatio="none" aria-hidden="true">
		<path
			d="M9 9h256c11 0 21 5 28 14l22 29c6 8 16 12 26 12h170c5 0 9 4 9 9v1018c0 5-4 9-9 9H9c-5 0-9-4-9-9V18c0-5 4-9 9-9Z"
			vector-effect="non-scaling-stroke"
		/>
	</svg>

	{@render familyContent(false)}

	<!-- The visual copy is clipped by the same moving fill as its block ground, so its ink changes
	     exactly where the contrast changes. -->
	<div class="masked-fill" aria-hidden="true">
		{@render familyContent(true)}
	</div>
</li>

<style>
	.family {
		position: relative;
		min-height: var(--models-frame-min-height);
		color: var(--ink);
		isolation: isolate;
		--plane-accent: light-dark(var(--plate), var(--models-frame-highlight));
		--plane-accent-on: light-dark(var(--plate-ink), var(--block-ink));
		--plane-accent-hover: light-dark(
			var(--plate-deep),
			color-mix(in oklab, var(--models-frame-highlight) 85%, white)
		);
		--plane-pencil: light-dark(var(--pencil-deep), var(--pencil));
		--rule-accent: 2px solid var(--accent);
		--waiting: var(--surface-sunken);
	}

	.frame-clip {
		position: absolute;
		inline-size: 0;
		block-size: 0;
	}

	.frame {
		position: absolute;
		z-index: 3;
		inset: 0;
		width: 100%;
		height: 100%;
		overflow: visible;
		pointer-events: none;
	}

	.family-content {
		position: relative;
		z-index: 1;
		display: grid;
		grid-template-rows: min-content minmax(0, 1fr) min-content;
		gap: var(--space-4);
		height: 100%;
		padding: var(--space-7) var(--space-5) var(--space-5);
	}

	.masked-fill {
		position: absolute;
		z-index: 2;
		inset: 0;
		clip-path: var(--frame-clip);
		pointer-events: none;
	}

	.masked-content {
		position: absolute;
		inset: 0;
		background: var(--block);
		color: var(--block-ink);
		clip-path: ellipse(100% 0% at 50% 100%);
		transition: clip-path var(--motion-slow) var(--ease-in);
		--plane-accent: var(--accent-block);
		--plane-accent-on: var(--block);
		--plane-accent-hover: var(--accent-block-hover);
		--plane-pencil: light-dark(var(--pencil), var(--pencil-deep));
		--hairline: var(--hairline-block);
		--hairline-panel: var(--hairline-block);
		--rule-accent: 2px solid var(--accent-block);
		--waiting: var(--hairline-block);
	}

	.frame path {
		fill: transparent;
		stroke: var(--block);
		stroke-width: 1;
		transition:
			color var(--motion-fast) var(--ease-in),
			filter var(--motion) var(--ease-in),
			stroke var(--motion-fast) var(--ease-in),
			stroke-width var(--motion-fast) var(--ease-in);
	}

	@media (hover: hover) {
		.family:hover .frame path {
			color: var(--block);
			stroke: currentColor;
			stroke-width: 3;
			filter: var(--models-frame-hover-glow);
		}

		.family:hover .masked-content {
			clip-path: ellipse(100% 110% at 50% 50%);
		}
	}

	.family.touch-active .frame path {
		color: var(--block);
		stroke: currentColor;
		stroke-width: 3;
		filter: var(--models-frame-hover-glow);
	}

	.family.touch-active .masked-content {
		clip-path: ellipse(100% 110% at 50% 50%);
	}

	.family:has(:global(:focus-visible)) .frame path {
		color: var(--block);
		stroke: currentColor;
		stroke-width: 3;
		filter: var(--models-frame-hover-glow);
	}

	.family:has(:global(:focus-visible)) .masked-content {
		clip-path: ellipse(100% 110% at 50% 50%);
	}

	.said {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.words {
		color: var(--ink-muted);
		font-size: var(--type-small);
	}

	/*
	 * The models the family holds. The count is a printed label above the slot rather than a label on
	 * a rule, because the slot's own top edge is the rule, and it is one line tall on every sheet, so
	 * the slots are cut on one line straight across the board.
	 */
	.index {
		display: flex;
		container-type: inline-size;
		flex-direction: column;
		gap: var(--space-3);
		min-height: 0;
		padding: var(--space-4);
	}

	.count {
		color: var(--ink-muted);
	}

	.index :global(.stage) {
		flex: 1;
	}

	.index :global(.ground) {
		background: transparent;
		box-shadow: none;
	}

	.index :global(.roll) {
		padding-inline: var(--space-4);
	}

	.index :global(.roll li) {
		padding-block: var(--space-3);
		border-top: var(--rule);
	}

	.name {
		font-size: var(--type-plate-index);
		font-weight: 800;
		letter-spacing: -0.025em;
		line-height: 1.05;
		text-transform: uppercase;
	}

	.what {
		margin-block-start: var(--space-2);
		color: var(--ink-muted);
		font-size: var(--type-small);
	}

	.name:has(~ .tag) {
		color: var(--ink-muted);
	}

	.tag {
		margin-block-start: var(--space-2);
		color: var(--ink-muted);
	}

	.masked-content .words,
	.masked-content .count,
	.masked-content .what,
	.masked-content .name:has(~ .tag),
	.masked-content .tag {
		color: var(--block-muted);
	}

	.masked-content .text-link {
		color: var(--plane-accent);
		text-decoration: underline;
		text-decoration-thickness: 1px;
		text-underline-offset: 2px;
	}

	/* The visible layer carries the focus ring too, because it sits over the real control while filled. */
	.family:has(.family-content:not(.masked-content) .button:focus-visible) .masked-content .button,
	.family:has(.family-content:not(.masked-content) .text-link:focus-visible) .masked-content .text-link,
	.family:has(.family-content:not(.masked-content) :global(.roll:focus-visible))
		.masked-content :global(.roll) {
		outline: var(--rule-accent);
		outline-offset: 2px;
	}

	/* The two ways into a family, side by side while there is room for both and stacked where there
	   is not. */
	.ways {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-3) var(--space-4);
	}

	@media (min-width: 64rem) and (orientation: landscape) {
		.family {
			min-height: 0;
		}
	}

	/* Every family remains one tab. Its models roll within the available middle register on phones
	   and smaller screens instead of making a longer tab for a larger family. */
	@media (width < 64rem), (orientation: portrait) {
		.family {
			height: var(--models-frame-min-height);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.family {
			transition: none;
		}
	}
</style>
