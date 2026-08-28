<!--
	The shape every prediction page takes, whichever family it is for.

	The page opens on the printed band, stamped on the family's own stock, and the work sits under it
	in three regions: the night's board, the parameters, and the answer. That is the order a reader
	works in, and each is a different register, which is what tells them apart without a box around
	any of them. The board is printed, because the slate is the site talking. The parameters are
	paper, because that is the reader working. The answer is a block, because it is an object set into
	the page.

	Wide, the asking and the answering are two rows rather than three columns. The board and the
	parameters stand side by side, because the reader moves between them until the request is
	complete, and the answer takes the whole page under them, because a distribution is a drawing and
	a drawing wants width. The board is given the larger share of that first row: it holds a whole
	night of cards, and the parameters hold at most a handful of fields.

	The answer region stands from the first frame, because a reader should be able to see what the
	page is for before working out how to ask for it. Until one has been asked for it holds nothing
	but the words saying what to do, standing on the page rather than on paper of their own, because
	there is no answer yet for a block to be the container of. The press is what grows the region into
	the block the answer lands in, and the words sit where that block's own heading will, so it opens
	around them rather than replacing them. From then on it stays open, because a region that closed
	again under a reader reading it would be worse than one that never opened.

	Under all of it the family lists every model it holds and what each one scored on games it never
	saw. It is the page's standing content: a reader deciding which stat to ask about reads it before
	asking, and a reader holding an answer reads it to know what that answer is worth.

	Narrow, the regions lie on top of each other in the same order, so the page is read down rather
	than across and nothing is dropped.

	Above all of it the page says, in its own standing words, what this family answers. It is one
	sentence, because the reader came here to ask something, and it is above the form rather than
	under it, because it is what the page is about and a search engine reads a page from the top down.

	What differs between families is those words, the night's board, the game the parameters are
	about, what the reader has to choose, and how the answer names itself, so those arrive as the
	snippets and the one sentence. Everything here is the shared layout.
-->
<script lang="ts">
	import { tick } from 'svelte';

	import AdSlot from '$lib/components/AdSlot.svelte';
	import ModelIndex from '$lib/components/ModelIndex.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PageMetadata from '$lib/components/PageMetadata.svelte';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import { FAMILY_MODELS_SECTION } from '$lib/models';
	import { flowingHeight, MOTION, MOTION_IMPACT, MOTION_SLOW, settled } from '$lib/motion';
	import { phone } from '$lib/screen';
	import { stopWalking, walkTo } from '$lib/scroll';
	import { webPageSchema } from '$lib/seo';

	import type { ScoredModel } from '$lib/types';
	import type { Snippet } from 'svelte';

	type Props = {
		title: string;
		/** The family's own path, which is this page. Every request on it names this one address. */
		path: string;
		/** One sentence, for a search result and a shared link. */
		privateDescription: string;
		/** One sentence, shown as the page lede.*/
		publicDescription: string;
		/**
		 * The page's own standing sentence, printed above the form.
		 *
		 * It says what the family answers, in words that are the same on every visit. Nothing else on
		 * the page is: the board is tonight's games and the answer is whatever was asked for.
		 */
		standing: string;
		/** Every model in the family, each carrying what it measured, drawn on the server. */
		scored: ScoredModel[];
		/** False when the service offers nothing this page can draw, which is its empty state. */
		hasModels: boolean;
		/** False where the service did not answer at all, which is not the same as nothing published. */
		answering: boolean;
		/** A successful response. Its identity distinguishes each completed prediction. */
		prediction: unknown | null;
		/** The completed prediction's model, recorded without any player or game data. */
		model: string;
		/**
		 * True where the address bar already names a request that was answered or refused, which
		 * stands the answer open on arrival rather than growing it. A shared link and a reload both
		 * land that way, and neither is a reveal the reader watched.
		 */
		hasAnswer: boolean;
		/** The night's games, the first region. Omitted by a family that predicts on something else. */
		board?: Snippet;
		/** The head naming the game the parameters are about. Omitted where there is no board. */
		matchup?: Snippet;
		controls: Snippet;
		/** One element. It holds the answer, the skeleton and a failure alike. */
		result: Snippet<[opening: boolean]>;
	};

	let {
		title,
		path,
		privateDescription,
		publicDescription,
		standing,
		scored,
		hasModels,
		answering,
		prediction,
		model,
		hasAnswer,
		board,
		matchup,
		controls,
		result
	}: Props = $props();

	let answerColumn = $state<HTMLElement>();
	let controlsColumn = $state<HTMLElement>();
	let trackedPrediction = $state.raw<unknown>(null);

	/** Whether the block has grown into the one an answer lands in, which the first press does. */
	// svelte-ignore state_referenced_locally
	let opened = $state(hasAnswer);
	let opening = $state(false);

	$effect(() => {
		if (prediction === null || prediction === trackedPrediction) return;

		window.dataLayer?.push({
			event: 'prediction_made',
			prediction_family: path.slice('/models/'.length),
			prediction_model: model
		});
		trackedPrediction = prediction;
	});

	/**
	 * Walks to the answer region, then grows it out of the block standing in its place.
	 *
	 * The request is already running while the page travels. On the first request the walk starts
	 * against the small block, which is already on the page, and the skeleton is fed in once the walk
	 * is under way, then held until its entrance finishes so a fast response cannot replace it
	 * mid-motion. The walk follows the region for the whole of that entrance, because the block grows
	 * under it.
	 *
	 * Beside the parameters the answer almost always ends up in front of the reader anyway, so the
	 * walk does nothing there. Under them, which is every narrow screen, it is a page away from the
	 * button that asked for it.
	 *
	 * Later requests keep the existing block in place and follow it while its answer changes size.
	 */
	export async function reveal(asking?: Promise<unknown>): Promise<void> {
		stopWalking();

		if (!opened) {
			const walking = walkTo(answerColumn, {
				block: 'start',
				flowing: MOTION_IMPACT,
				always: true
			});

			// Let the page cover most of the distance first, so the sheet starts just before it arrives.
			await Promise.race([walking, settled(MOTION)]);

			opening = true;
			opened = true;
			await tick();
			await Promise.all([walking, settled(MOTION_IMPACT)]);
			opening = false;
			return;
		}

		walkTo(answerColumn, { block: 'start', flowing: phone.current ? MOTION_SLOW : asking });

		// The first mobile answer opens a new region. Once it has arrived, the reader owns the page.
		if (phone.current && asking) asking.then(stopWalking, stopWalking);
	}

	/**
	 * Puts the parameters at the top of the screen, under the header.
	 *
	 * A game is what the whole request is about, so choosing one changes every question under it. The
	 * page is walked whether or not the parameters were already showing, because leaving the board
	 * they were picked from filling the screen above them is what made the choice read as though
	 * nothing had happened.
	 */
	export function revealControls(): void {
		walkTo(controlsColumn, { block: 'start', always: true });
	}
</script>

<!-- The bare path, never the request in the address bar, so every combination of parameters names
     this one page. See lib/pages.ts. -->
<PageMetadata
	{title}
	description={privateDescription}
	{path}
	schema={webPageSchema({ name: title, description: privateDescription, path })}
/>

<PlateBand {title} lede={publicDescription}>
	{#snippet action()}
		<!-- Every model this page can ask, and what each one scored, further down the page itself. -->
		{#if scored.length > 0}
			<a class="small text-link" href={`#${FAMILY_MODELS_SECTION}`}>
				See every model and how it scores
			</a>
		{/if}
	{/snippet}
</PlateBand>

<div class="page work">
	<!-- Stands whether or not the service is answering, because it is the page's own words rather
	     than anything read off a model. -->
	<section class="standing">
		<p>{standing}</p>
	</section>

	{#if !hasModels}
		<!-- With nothing to ask there is nothing to offer, so the page is this and no more. A service
		     that never answered is not an empty family, and only one of the two is worth waiting for. -->
		{#if answering}
			<Notice>No model here can answer yet.</Notice>
		{:else}
			<Notice>
				The prediction service is not answering, so nothing can be predicted right now. Try again in a
				few minutes.
			</Notice>
		{/if}
	{:else}
		<div class="request">
			<div class="columns" class:boardless={!board}>
				{#if board}
					<div class="board-column">{@render board()}</div>
				{/if}

				<!--
					The head, the game it is about, then the fields. This region is what the form's groups
					are measured against, so how many columns they set as follows the width it has rather
					than the width of the screen.
				-->
				<section class="controls" aria-labelledby="controls-column" bind:this={controlsColumn}>
					<h2 class="column-label micro" id="controls-column">What to predict</h2>
					{@render matchup?.()}
					<div class="panel">
						{@render controls()}
					</div>
				</section>
			</div>

			<section class="answer" aria-labelledby="answer-column" bind:this={answerColumn}>
				<h2 class="column-label micro" id="answer-column">Answer</h2>

				<!--
					The region holds the height of whatever is in it, so the standing words grow into the
					block an answer lands in rather than being swapped for it in a frame, and it is
					clipped only while it grows, because the drawing inside an answer is free to hang over
					its own edges once it is there.

					A page that arrived already carrying an answer renders it open, because a transition
					does not run on the first frame and nothing about a shared link was revealed to anyone.
				-->
				<div class="answer-result" class:opening use:flowingHeight>
					<div class="swap">
						{#if opened}
							<div>{@render result(opening)}</div>
						{:else}
							<p class="prompt type-h2">Make a prediction first.</p>
						{/if}
					</div>
				</div>
			</section>
		</div>
	{/if}

	<!-- The family's standing content: what it holds, and what each of them is worth. Absent only
	     where the service could not name them, which the region above has already said. -->
	{#if scored.length > 0}
		<section
			class="listing"
			class:unanswered={!opened}
			id={FAMILY_MODELS_SECTION}
			aria-labelledby="models-section"
		>
			<h2 class="column-label micro" id="models-section">All models</h2>

			<p class="small muted">
				Every model in this category, and what it measured on games it never saw while it was being
				fitted. Open one to read its figures in full.
			</p>

			<ModelIndex models={scored} />

			<p>
				<a class="small text-link" href="/about#evaluation-metrics">
					Learn what each evaluation metric means
				</a>
			</p>
		</section>
	{/if}

	<AdSlot place="modelBelowResult" />
</div>

<style>
	.work {
		display: flex;
		flex-direction: column;
		gap: var(--space-7);
		padding-block-start: var(--space-7);
	}

	/*
	 * The page's own opening statement, under the accent rule that marks anything the site says in
	 * its own words. Set a step above body text and run it across the page, so it names the work below
	 * rather than only the board beside it.
	 */
	.standing::before {
		content: '';
		display: block;
		width: var(--space-6);
		margin-block-end: var(--space-4);
		border-top: var(--rule-accent);
	}

	.standing p {
		font-size: var(--type-note);
		text-wrap: pretty;
	}

	/* Narrow: board, then parameters, then answer, which is the order the work is done in. */
	.columns {
		display: grid;
		gap: var(--space-6);
	}

	.request {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.board-column,
	.controls,
	.answer {
		min-width: 0;
	}

	.controls {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		container-type: inline-size;
		container-name: controls;
	}

	/* The block inside sets itself against this rather than against the screen, because it is also
	   drawn in a narrow column on the About page and has to fold there without a breakpoint. */
	.answer {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		container-type: inline-size;
		container-name: answer-column;
	}

	.answer-result {
		min-width: 0;
	}

	/* One cell, so the small block and the answer trade in the same place rather than one under the
	   other while the height flows between them. */
	.swap {
		display: grid;
	}

	.swap > * {
		grid-area: 1 / 1;
		min-width: 0;
	}

	/* No paper of its own: the block arrives with the answer, so until then the words stand on the
	   page in muted ink. They sit where the answer's own heading will, so the block grows around them
	   rather than replacing them. */
	.prompt {
		padding-block-end: var(--space-3);
		color: var(--ink-muted);
	}

	/* The skeleton is fed into view like a fresh sheet, just before the page reaches its mark. */
	.answer-result.opening {
		position: relative;
		isolation: isolate;
		overflow: clip;
		animation: open-answer var(--motion-impact) var(--ease-in);
	}

	.answer-result.opening::after {
		content: '';
		position: absolute;
		z-index: 1;
		inset: 0;
		background: linear-gradient(
			to right,
			transparent calc(100% - 2px),
			var(--accent-block) calc(100% - 2px)
		);
		opacity: 0;
		pointer-events: none;
		animation: open-edge var(--motion-impact) var(--ease-in);
	}

	@keyframes open-answer {
		from {
			clip-path: inset(0 100% 0 0);
		}

		to {
			clip-path: inset(0);
		}
	}

	@keyframes open-edge {
		from {
			opacity: 0;
			transform: translateX(-100%);
		}

		8%,
		82% {
			opacity: 1;
		}

		to {
			opacity: 0;
			transform: translateX(0);
		}
	}

	/* Every model the family holds, printed under the work rather than beside it. */
	.listing {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		margin-block-start: var(--space-6);
	}

	/* Before a reader asks for an answer, the supporting evidence stands a further step away from
	   the task. Once the answer opens, it returns to the page's ordinary section spacing. */
	.listing.unanswered {
		margin-block-start: var(--space-7);
	}

	@media (width < 40rem) {
		/* The response replaces a reserved drawing. It must not become the browser's scroll anchor. */
		.answer {
			overflow-anchor: none;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.answer-result.opening {
			animation: none;
		}

		.answer-result.opening::after {
			display: none;
		}
	}

	/*
	 * Wide enough for two rows: the board and the parameters side by side, and the answer across the
	 * whole page under them. The two above are the request and they are worked on together, so they
	 * share a line of sight. The answer is what the page was for, and given the page it draws its
	 * distribution at a width a column could never give it.
	 *
	 * With no board there is nothing to stand beside, so the parameters take the row on their own and
	 * their groups set as two columns in it.
	 */
	@media (min-width: 64rem) {
		.columns {
			grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
			align-items: start;
			column-gap: var(--space-6);
		}

		.columns.boardless {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
