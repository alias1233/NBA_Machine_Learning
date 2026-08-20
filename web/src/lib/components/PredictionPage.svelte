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

	All three stand from the first frame, the answer included. Nothing opens, and nothing about the
	empty answer pulses, because a reader who has not pressed the button is not waiting on anything.

	Narrow, the three lie on top of each other in the same order, so the page is read down rather than
	across and nothing is dropped.

	What differs between families is the night's board, the game the parameters are about, what the
	reader has to choose, and how the answer names itself, so those arrive as the four snippets.
	Everything here is the shared layout.
-->
<script lang="ts">
	import AdSlot from '$lib/components/AdSlot.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import { walkTo } from '$lib/scroll';
	import { pageTitle } from '$lib/site';

	import type { Snippet } from 'svelte';

	type Props = {
		title: string;
		/** One sentence, for a search result, a shared link, and the band's own lede. */
		description: string;
		/** The family's own page, linked under the title before a reader asks for a number. */
		aboutHref: string;
		/** False when the service offers nothing this page can draw, which is its empty state. */
		hasModels: boolean;
		/** False where the service did not answer at all, which is not the same as nothing published. */
		answering: boolean;
		/** The night's games, the first region. Omitted by a family that predicts on something else. */
		board?: Snippet;
		/** The head naming the game the parameters are about. Omitted where there is no board. */
		matchup?: Snippet;
		controls: Snippet;
		/** One element. It holds the answer, the skeleton and a failure alike. */
		result: Snippet;
	};

	let {
		title,
		description,
		aboutHref,
		hasModels,
		answering,
		board,
		matchup,
		controls,
		result
	}: Props = $props();

	let answerColumn = $state<HTMLElement>();
	let controlsColumn = $state<HTMLElement>();

	/**
	 * Walks the reader to the answer when it is not already in front of them.
	 *
	 * Beside the parameters it almost always is, so this does nothing there. Under them, which is
	 * every narrow screen, the answer is a page away from the button that asked for it. Nothing is
	 * awaited by the caller, because the request it is answering goes out in the same breath.
	 *
	 * The request is the flow, so it is handed over and the page holds the answer at the top of the
	 * screen until it lands. An answer changes the height of everything it touches, and a page that
	 * stopped travelling when the button was pressed is left wherever that leaves it.
	 */
	export function reveal(asking?: Promise<unknown>): void {
		walkTo(answerColumn, { block: 'start', flowing: asking });
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

<svelte:head>
	<title>{pageTitle(title)}</title>
	<meta name="description" content={description} />
</svelte:head>

<PlateBand {title} lede={description}>
	{#snippet action()}
		<!-- How the number is reached, before a reader asks for one. -->
		<a class="small text-link" href={aboutHref}>How these models work</a>
	{/snippet}
</PlateBand>

<div class="page work">
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
		<div class="columns" class:boardless={!board}>
			{#if board}
				<div class="board-column">{@render board()}</div>
			{/if}

			<!--
				The head, the game it is about, then the fields. This region is what the form's groups are
				measured against, so how many columns they set as follows the width it has rather than
				the width of the screen.
			-->
			<section class="controls" aria-labelledby="controls-column" bind:this={controlsColumn}>
				<h2 class="column-label micro" id="controls-column">What to predict</h2>
				{@render matchup?.()}
				{@render controls()}
			</section>

			<section class="answer" aria-labelledby="answer-column" bind:this={answerColumn}>
				<h2 class="column-label micro" id="answer-column">Answer</h2>
				{@render result()}
			</section>
		</div>
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

	/* Narrow: board, then parameters, then answer, which is the order the work is done in. */
	.columns {
		display: grid;
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

		.answer {
			grid-column: 1 / -1;
		}
	}
</style>
