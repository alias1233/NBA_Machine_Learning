<!--
	One model family, printed as a sheet on the home page's index.

	The sheet is the family's own stock, the same ground its prediction page and its About page are
	printed on, so a reader has seen where they are going before they arrive. It reads down in three
	registers: what the family is, the models it holds, and the two ways into it.

	The middle register is the point of it. A family is not a picture, it is the models in it, so the
	sheet prints them by name with what each one answers. Only a batch stands at once, because a model
	a reader cannot read is a model the sheet did not show them, and the rest come round on a turn.
	A family small enough to print whole never turns and never offers the control.

	The turn follows the same rules as the hero's, and for the same reasons. Reduced motion never
	starts it, a reader resting on the sheet holds it where it is, and turning it by hand settles it
	there for the visit, which is the standing way to stop it. A thin run of spot ink along the top
	edge of the index says how much of the turn is left, drawn only while the turn is really running,
	so nothing on the sheet changes without the reader having seen it coming.
-->
<script lang="ts">
	import { prefersReducedMotion } from 'svelte/motion';

	import { familyAboutPath, familyPath } from '$lib/models';
	import { roomForBatch } from '$lib/screen';

	import type { ListedFamily } from '$lib/models';

	type Props = {
		family: ListedFamily;
	};

	let { family }: Props = $props();

	/**
	 * How many models stand at once.
	 *
	 * Every one of them prints its name and what it answers, so this is a count of what a reader can
	 * read at a glance rather than of what would fit. It is also about what a family is expected to
	 * hold at the least, so most families will print whole and never turn at all.
	 *
	 * One fewer on a short screen, because the index has to be readable against both its own edges
	 * without a scroll, and on a screen that cannot hold four entries and stay inside them the entry
	 * that would be cut is worth less than the scroll it costs.
	 */
	const shown = $derived(roomForBatch.current ? 4 : 3);

	/** How long a batch stays up. Longer than the hero's, because this is prose rather than a shape. */
	const TURN = 9000;

	/** Where the batch starts in the family's own order. Wrapped, so a batch is never short. */
	let start = $state(0);

	/** True once the reader has turned the sheet themselves, which ends the turn for the visit. */
	let settled = $state(false);

	/** True while the reader is resting on this sheet, by pointer or by focus, which holds the turn. */
	let held = $state(false);

	/** What a reader who cannot see the sheet is told, and only for a turn they asked for. */
	let announced = $state('');

	const models = $derived(family.models);

	/** A family that prints whole has nothing to turn to, so it is never given the control. */
	const rotates = $derived(models.length > shown);

	const batch = $derived(
		rotates
			? Array.from({ length: shown }, (_, place) => models[(start + place) % models.length])
			: models
	);

	/**
	 * Whether the batches are actually coming round, which is the one thing the run of ink may say.
	 *
	 * The same conditions the timer below runs under, read rather than restated, so the run can never
	 * promise a change that is not on its way.
	 */
	const turning = $derived(rotates && !settled && !held && !prefersReducedMotion.current);

	// `start` is written rather than read here, so the turn it sets off does not restart the timer
	// that set it.
	$effect(() => {
		if (!turning) return;

		const coming = setInterval(() => {
			start = (start + shown) % models.length;
		}, TURN);

		return () => clearInterval(coming);
	});

	function turnOver() {
		start = (start + shown) % models.length;
		settled = true;
		announced = `${family.title}. ${batch.map((model) => model.title).join('. ')}.`;
	}

	/** Focus moving from one control on the sheet to another is still focus on the sheet. */
	function releaseTurn(event: FocusEvent & { currentTarget: HTMLElement }) {
		held = event.currentTarget.contains(event.relatedTarget as Node | null);
	}
</script>

<!-- The family's own stock. One attribute is the whole of what a family colours. -->
<li
	class="family plate"
	data-plate={family.slug}
	style:--turn-duration="{TURN}ms"
	onpointerenter={() => (held = true)}
	onpointerleave={() => (held = false)}
	onfocusin={() => (held = true)}
	onfocusout={releaseTurn}
>
	<span class="registration top-start" aria-hidden="true"></span>
	<span class="registration top-end" aria-hidden="true"></span>
	<span class="registration bottom-start" aria-hidden="true"></span>
	<span class="registration bottom-end" aria-hidden="true"></span>

	<div class="said">
		<h3 class="type-h2">{family.title}</h3>
		<p class="words">{family.description}</p>
	</div>

	<div class="index">
		<!-- What is standing out of what the family holds, which is what says there is more to come.
		     A family printing whole says only how many it has. -->
		<div class="head">
			<p class="count micro">
			{#if rotates}{batch.length} of {models.length} models{:else}{models.length}
				{models.length === 1 ? 'model' : 'models'}{/if}
			</p>

			{#if rotates}
				<button class="button button--quiet" type="button" onclick={turnOver}>
					Show the next {shown}<span class="visually-hidden"> {family.title.toLowerCase()}</span>
				</button>
			{/if}
		</div>

		<!-- Keyed on the batch, so each one is laid down in its own right rather than having its words
		     swapped underneath the last one's. -->
		{#key start}
			<div class="run">
				<!-- How much of the turn is left, emptying from the right along the top edge of the
				     models, which is the part of the sheet that changes. -->
				{#if turning}
					<span class="turn" aria-hidden="true"><span class="turn-left"></span></span>
				{/if}

				<ol class="held" style:--slots={shown}>
					{#each batch as model, place (model.name)}
						<li style:--laid-after="{place * 60}ms">
							<p class="name">{model.title}</p>
							<p class="what">{model.description}</p>
							{#if !model.published}
								<p class="tag micro">Not trained yet</p>
							{/if}
						</li>
					{/each}
				</ol>
			</div>
		{/key}
	</div>

	<!-- A family with nothing trained behind it has nowhere to lead, so it says so instead of offering
	     a page that cannot answer. -->
	<div class="ways">
		{#if family.published}
			<a class="button" href={familyPath(family)}>Run a prediction</a>
			<a class="small text-link" href={familyAboutPath(family)}>How these models work</a>
		{:else}
			<span class="tag micro">Not published yet</span>
		{/if}
	</div>

	<p class="visually-hidden" role="status">{announced}</p>
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
	 * The models the family holds. The count and the control share a line above them, because the
	 * control acts on what is under it rather than on the sheet as a whole. That line is one control
	 * tall on every sheet whether or not it carries one, so the index below it starts in the same
	 * place straight across the board.
	 */
	.index {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-2) var(--space-3);
		min-height: var(--tap-target);
	}

	.count {
		color: var(--plate-ink-muted);
	}

	/* Printed at label size, because it names what the count beside it is a part of rather than
	   leading the sheet. It keeps the site's tap target, which is a floor and not a suggestion. */
	.index .button--quiet {
		padding-inline: var(--space-3);
		font-family: var(--font-mono);
		font-size: var(--type-micro);
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	/* Stretched rather than centred in the room the sheet has, so the first rule of the index is in
	   the same place on all three sheets however many models each one prints. */
	.run {
		position: relative;
		flex: 1;
		min-height: 0;
	}

	/*
	 * A set index, read from the top. It is ruled for a full batch whether or not the family fills
	 * one, so an entry is the same height on every sheet and the rules line up straight across the
	 * board. A family holding less than a batch leaves the rest of its stock as margin, which the
	 * registration crosses are what make read as printed rather than as a hole.
	 */
	.held {
		display: grid;
		grid-template-rows: repeat(var(--slots), minmax(min-content, 1fr));
		height: 100%;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	/* The floor an entry is set at. Where the sheet has room the rows share it and open up past this,
	   so tightening the floor buys a screen without costing a wide one anything. */
	.held li {
		padding-block: var(--space-2);
		border-top: var(--rule-plate);
	}

	.name {
		font-weight: 600;
		letter-spacing: -0.01em;
	}

	.what {
		color: var(--plate-ink-muted);
		font-size: var(--type-small);
	}

	/* A model nothing stands behind yet is named in the muted ink and says so in words, so the state
	   is never carried by the tone alone. */
	.held li:has(.tag) .name {
		color: var(--plate-ink-muted);
	}

	.held .tag {
		margin-block-start: var(--space-2);
		color: var(--plate-ink-muted);
	}

	/*
	 * How much of the turn is left, printed along the top edge of the models. The track is the whole
	 * turn and the run inside it is what is left of it, emptying from the right, which is the
	 * direction the next batch comes from.
	 *
	 * Spot ink, because the turn is the site's own doing rather than the reader's, and a bar rather
	 * than a figure, because a countdown in numbers on a page nobody asked to wait on is pressure.
	 */
	.turn {
		position: absolute;
		inset: 0 0 auto;
		z-index: 1;
		height: 2px;
		background: color-mix(in oklab, var(--plate-spot) 28%, transparent);
		overflow: clip;
	}

	.turn-left {
		display: block;
		height: 100%;
		background: var(--plate-spot);
		transform-origin: left center;
		animation: empty var(--turn-duration) linear;
	}

	@keyframes empty {
		to {
			scale: 0 1;
		}
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

	/* A batch is laid down a row at a time, in the order a press would lay it, which is what makes a
	   turn read as the sheet being reprinted rather than as its words being swapped. */
	.held li {
		animation: lay var(--motion) var(--ease-in) var(--laid-after) backwards;
	}

	@keyframes lay {
		from {
			opacity: 0;
			translate: 0 var(--space-2);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.held li {
			animation: none;
		}
	}

	/*
	 * Landscape, the page stands the families as columns of one grid, so the three registers line up
	 * across the row however long a family's own words run. The index takes the room between them.
	 */
	@media (orientation: landscape) {
		.family {
			grid-row: span 3;
			grid-template-rows: subgrid;
		}

		.said {
			grid-row: 1;
			gap: var(--space-3);
		}

		/* The models take the room between what the family is and the ways into it, so the sheets are
		   the same height whatever each one holds. */
		.index {
			grid-row: 2;
		}

		.ways {
			grid-row: 3;
		}
	}
</style>
