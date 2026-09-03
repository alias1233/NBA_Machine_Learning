<!--
	The board: the games that can be predicted right now, dealt across a well in the family's plate.

	It is the first of a prediction page's three regions, and the only one that is printed rather than
	paper, because the night's slate is the site talking and the parameters beside it are the reader
	working. Every family that predicts on scheduled games opens with this, so it is one piece rather
	than the same three lines on each page.

	A game is the one thing a request cannot be made without, so the whole slate is dealt face up and
	nothing about it is hidden behind a scroll. Its head names what is being dealt and how much of it,
	because the cards themselves cannot say that together.

	The slate is dealt a day at a time, each day stamped with its own name and count above the hand it
	holds. A reader hunting for a game knows its day before they know anything else about it, and a
	day named once over a run of cards is both easier to find and quieter on the board than the same
	date printed again on every card in the run.
-->
<script lang="ts">
	import GameCards from '$lib/components/GameCards.svelte';
	import { fullGameDay, gameDayLabel, slateDays } from '$lib/games';

	import type { ScheduledGame } from '$lib/types';

	type Props = {
		games: ScheduledGame[];
		/** The game the parameters currently describe, if they describe one. */
		selected: ScheduledGame | null;
		hrefOf: (game: ScheduledGame) => string;
		onchoose: (game: ScheduledGame) => void;
		/** The card the reader is over, or null once they leave it. */
		onpreview?: (game: ScheduledGame | null) => void;
	};

	let { games, selected, hrefOf, onchoose, onpreview }: Props = $props();

	/** The slate a day at a time, which is how the board deals it. */
	const days = $derived(slateDays(games));

	/** How many games are being dealt, said the way a reader counts them. */
	const counted = (of: number) => `${of} ${of === 1 ? 'game' : 'games'}`;
</script>

<section class="board" aria-labelledby="upcoming">
	<div class="column-label">
		<h2 class="micro" id="upcoming">Upcoming games</h2>
		{#if games.length > 0}
			<p class="micro tally">{counted(games.length)}</p>
		{/if}
	</div>

	<div class="well plate">
		{#if games.length === 0}
			<!-- Printed on the board rather than boxed on it. A panel here would be the tone of the well
			     it stands in, and an empty board is a sentence rather than an object. -->
			<p class="small empty">No game can be predicted right now.</p>
		{:else}
			{#each days as { date, games: dealt } (date)}
				{@const label = gameDayLabel(date)}
				{@const written = fullGameDay(date)}

				<!-- A heading and the run of cards under it, rather than a region of its own. The board is
				     already one, and a landmark per day would bury it in a list of five. -->
				<div class="day">
					<div class="column-label">
						<!-- The day stamped, then written out beside it wherever the stamp is a word rather
						     than a date, because "Today" alone never says which day it was read on. -->
						<h3 class="day-name">
							{label}
							{#if label !== written}<span class="micro day-date">{written}</span>{/if}
						</h3>
						<p class="micro tally">{counted(dealt.length)}</p>
					</div>

					<GameCards games={dealt} {selected} {hrefOf} {onchoose} {onpreview} />
				</div>
			{/each}
		{/if}
	</div>
</section>

<style>
	.board {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	/* How many games are on the board, or on one of its days, which is the one thing the cards under
	   either cannot say together. */
	.tally {
		color: var(--ink-muted);
		font-variant-numeric: tabular-nums;
	}

	/*
	 * A well printed darker than the plate, which is what the plate does with an area waiting to be
	 * filled. The board is exactly that: it holds a hand until the reader takes one off it, and it is
	 * one of the few things on this site that genuinely is an object rather than a region.
	 */
	.well {
		/* The cards measure themselves against the board rather than against the screen, so how many
		   are dealt across a row follows the column this stands in. */
		container-type: inline-size;
		display: flex;
		flex-direction: column;
		/* The days stand far enough apart that a card lifted off the last row of one never reaches the
		   rule the next is stamped under. */
		gap: var(--space-6);
		padding: var(--space-5);
		background: var(--plate-deep);
		border-radius: var(--radius-lg);
	}

	.day {
		display: flex;
		flex-direction: column;
		/* Room for a card in the first row to be lifted and ringed without reaching the rule the day
		   is stamped under. */
		gap: var(--space-5);
	}

	/*
	 * The day, stamped in the plate's own face. It is set above the micro labels around it because it
	 * is what a reader scanning for a date lands on, and it is the one word on the board large enough
	 * to be found without reading anything else.
	 */
	.day-name {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--space-1) var(--space-3);
		font-size: var(--type-h3);
		font-weight: 700;
		letter-spacing: 0.06em;
		line-height: 1.1;
		text-transform: uppercase;
	}

	.day-date {
		color: var(--ink-muted);
	}

	.empty {
		color: var(--plate-ink-muted);
	}
</style>
