<!--
	One model family, printed as a sheet on the home page's index.

	The sheet is the family's own stock, the same ground its prediction page and its About page are
	printed on, so a reader has seen where they are going before they arrive. It reads down in three
	registers: what the family is, the models it holds, and the two ways into it.

	The middle register is the point of it. A family is not a picture, it is the models in it, so the
	sheet prints them by name, at a size that makes the names the texture of the sheet, with the
	sentence that says what each one answers stepped back under it.

	They stand in a slot cut through the stock: one ink on every sheet, whatever the family is printed
	on, so the index reads as a cut down through the board rather than as a second colour the family
	chose. The whole family is in there and the roll feeds it past on its own. See ModelRoll.svelte.
-->
<script lang="ts">
	import ModelRoll from '$lib/components/ModelRoll.svelte';
	import { familyInfoPath, familyPath } from '$lib/models';

	import type { ListedFamily } from '$lib/models';

	type Props = {
		family: ListedFamily;
		/** The first family is the anchor of the home page's press composition. */
		position: number;
	};

	let { family, position }: Props = $props();

	const models = $derived(family.models);
</script>

<!-- The family's own stock. One attribute is the whole of what a family colours. -->
<li class:lead={position === 0} class="family plate" data-plate={family.slug}>
	<span class="registration top-start" aria-hidden="true"></span>
	<span class="registration top-end" aria-hidden="true"></span>
	<span class="registration bottom-start" aria-hidden="true"></span>
	<span class="registration bottom-end" aria-hidden="true"></span>

	<div class="said">
		<h3 class="type-h2">{family.title}</h3>
		<p class="words">{family.description}</p>
	</div>

	<div class="index">
		<p class="count micro">{models.length} {models.length === 1 ? 'model' : 'models'}</p>

		<ModelRoll {models} label={family.title}>
			{#snippet entry(model)}
				<p class="name">{model.title}</p>
				<p class="what">{model.description}</p>
				{#if !model.published}
					<p class="tag micro">Not trained yet</p>
				{/if}
			{/snippet}
		</ModelRoll>
	</div>

	<!-- A family with nothing trained behind it has nowhere to lead, so it says so instead of offering
	     a page that cannot answer. -->
	<div class="ways">
		{#if family.published}
			<a class="button" href={familyPath(family)}>Run a prediction</a>
			<a class="small text-link" href={familyInfoPath(family)}>More info about these models</a>
		{:else}
			<span class="tag micro">Not published yet</span>
		{/if}
	</div>
</li>

<style>
	/*
	 * Portrait, a family is a brick: what it is, the models it holds, and the ways into it, stacked.
	 * Landscape, the page subgrids it into a column a screen tall. Either way the three registers are
	 * in the same order and the ways in are at the foot.
	 */
	.family {
		position: relative;
		display: grid;
		grid-template-rows: min-content minmax(0, 1fr) min-content;
		gap: var(--space-4);
		padding: var(--space-5);
		min-height: var(--models-sheet-min-height);
		/* A sheet lies on the board rather than being printed into it, so it is lit along its top edge
		   and casts onto the board under it. The one place on paper that carries the plate's own
		   shadow, because the ground it falls on is printed stock. */
		box-shadow: inset 0 var(--models-sheet-rule) 0 var(--acetate-sheen), var(--sheet-shadow);
		transition:
			transform var(--motion) var(--ease-in),
			box-shadow var(--motion) var(--ease-in);
	}

	.family::after {
		position: absolute;
		inset: var(--models-sheet-cue-inset);
		content: '';
		border: var(--rule-plate);
		border-left: 0;
		pointer-events: none;
	}

	.family:hover,
	.family:focus-within {
		transform: translateY(var(--models-sheet-lift));
		box-shadow: inset 0 var(--models-sheet-rule) 0 var(--acetate-sheen), var(--models-sheet-hover-shadow);
	}

	.said {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.words {
		color: var(--plate-ink-muted);
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
	}

	.count {
		color: var(--plate-ink-muted);
	}

	.index :global(.stage) {
		flex: 1;
	}

	/* The slot itself: one ink on every family's sheet, cut into the stock and shadowed by its own
	   edge, so an entry is never the tone of the sheet it is printed on. */
	.index :global(.ground) {
		background: var(--plate-slot);
		box-shadow: var(--plate-slot-cut);
	}

	.index :global(.roll) {
		padding-inline: var(--space-4);
	}

	/* A rule between entries, drawn in the slot's own neutral rather than the family's, for the same
	   reason the slot is. */
	.index :global(.roll li) {
		padding-block: var(--space-3);
		border-top: var(--rule-slot);
	}

	/* The model's own word, which is what a reader is choosing between. */
	.name {
		font-size: var(--type-plate-index);
		font-weight: 800;
		letter-spacing: -0.025em;
		line-height: 1.05;
		text-transform: uppercase;
	}

	.what {
		margin-block-start: var(--space-2);
		color: var(--plate-ink-muted);
		font-size: var(--type-small);
	}

	/* A model nothing stands behind yet is named in the muted ink and says so in words, so the state
	   is never carried by the tone alone. */
	.name:has(~ .tag) {
		color: var(--plate-ink-muted);
	}

	.tag {
		margin-block-start: var(--space-2);
		color: var(--plate-ink-muted);
	}

	/* The two ways into a family, side by side while there is room for both and stacked where there
	   is not. */
	.ways {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-3) var(--space-4);
	}

	/* A way to read about a family is printed in the one ink rather than in the spot colour, which
	   belongs to the action rather than to a link beside it. It also clears 4.5:1 on every stock,
	   which the spot ink does not. */
	.ways .text-link {
		--plane-accent: var(--plate-ink);
	}

	/*
	 * Landscape, the lead family takes the full press height and the two supporting sheets share the
	 * other edge. Each index still takes exactly the room between its own heading and ways in.
	 */
	@media (orientation: landscape) {
		.family {
			min-height: 0;
		}

		.family.lead {
			grid-row: 1 / -1;
			grid-template-rows: min-content minmax(0, 1fr) min-content;
			padding: var(--models-lead-inset);
		}

		.family:not(.lead) {
			padding: var(--models-support-inset);
		}

		.family.lead .said {
			gap: var(--space-3);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.family {
			transition: none;
		}
	}
</style>
