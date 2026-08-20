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

	The answer is not on the page until one has been asked for. A reader who has not pressed the
	button is not waiting on anything, and an empty block standing in the room the answer will take is
	a page of held breath before there is anything to hold it for. The press is what opens the region,
	so it opens on the reader's own action rather than when the service comes back, and it opens onto
	the skeleton at the size the answer will land in. From then on it stands, because a region that
	closed again under a reader reading it would be worse than one that never opened.

	Narrow, the three lie on top of each other in the same order, so the page is read down rather than
	across and nothing is dropped.

	What differs between families is the night's board, the game the parameters are about, what the
	reader has to choose, and how the answer names itself, so those arrive as the four snippets.
	Everything here is the shared layout.
-->
<script lang="ts">
	import { tick } from 'svelte';

	import AdSlot from '$lib/components/AdSlot.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import { flow, MOTION_SLOW } from '$lib/motion';
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
		/**
		 * True where the address bar already names a request that was answered or refused, which
		 * stands the answer region up on arrival rather than opening it. A shared link and a reload
		 * both land that way, and neither is a reveal the reader watched.
		 */
		hasAnswer: boolean;
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
		hasAnswer,
		board,
		matchup,
		controls,
		result
	}: Props = $props();

	let answerColumn = $state<HTMLElement>();
	let controlsColumn = $state<HTMLElement>();

	/** Whether the reader has asked for an answer on this page, which is what opens the region. */
	let asked = $state(false);

	const showingAnswer = $derived(hasAnswer || asked);

	/**
	 * Opens the answer region and walks the reader to it.
	 *
	 * The region is opened by the press rather than by the answer, so the reader watches the room the
	 * answer will land in arrive with the skeleton already on it. Nothing is awaited by the caller,
	 * because the request it is answering goes out in the same breath.
	 *
	 * The walk waits a tick for the region to be in the page, because until it is there is nothing to
	 * walk to. Beside the parameters the answer almost always ends up in front of the reader anyway,
	 * so the walk does nothing there. Under them, which is every narrow screen, it is a page away
	 * from the button that asked for it.
	 *
	 * The request is the flow, so it is handed over and the page holds the answer at the top of the
	 * screen until it lands. An answer changes the height of everything it touches, and a page that
	 * stopped travelling when the button was pressed is left wherever that leaves it.
	 */
	export async function reveal(asking?: Promise<unknown>): Promise<void> {
		asked = true;

		await tick();

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
					{@render controls()}
				</section>
			</div>

			<!--
				Only once one has been asked for. It carries the room it stands off in its own margin
				rather than taking it from a gap, so the region opens out of nothing and the page under
				it is carried rather than dropped a gap's worth the moment the button is pressed.

				A page that arrived already carrying an answer renders it standing, because a transition
				does not run on the first frame and nothing about a shared link was revealed to anyone.
			-->
			{#if showingAnswer}
				<section
					class="answer"
					aria-labelledby="answer-column"
					bind:this={answerColumn}
					transition:flow={{ duration: MOTION_SLOW }}
				>
					<h2 class="column-label micro" id="answer-column">Answer</h2>
					{@render result()}
				</section>
			{/if}
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

	/* No gap of its own. The answer carries the room it stands off in its margin, so that room opens
	   with the region rather than standing empty before it. */
	.request {
		display: flex;
		flex-direction: column;
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
		margin-block-start: var(--space-6);
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
	}
</style>
