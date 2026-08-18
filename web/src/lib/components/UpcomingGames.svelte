<!--
	The board: the games that can be predicted right now, dealt across a well in the family's plate.

	It is the first of a prediction page's three regions, and the only one that is printed rather than
	paper, because the night's slate is the site talking and the parameters beside it are the reader
	working. Every family that predicts on scheduled games opens with this, so it is one piece rather
	than the same three lines on each page.

	A game is the one thing a request cannot be made without, so the whole night is dealt face up and
	nothing about it is hidden behind a scroll. Its head names what is being dealt, the days the board
	covers and how many games are on it, because the cards themselves cannot say that together.
-->
<script lang="ts">
	import GameCards from '$lib/components/GameCards.svelte';
	import { slateDays } from '$lib/games';

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

	/** What the board is dealing: the days it covers, then how many games are on it. */
	const slate = $derived(
		games.length === 0
			? ''
			: [slateDays(games), `${games.length} ${games.length === 1 ? 'game' : 'games'}`].join(' · ')
	);
</script>

<section class="board" aria-labelledby="upcoming">
	<div class="column-label">
		<h2 class="micro" id="upcoming">Upcoming games</h2>
		{#if slate}
			<p class="micro slate">{slate}</p>
		{/if}
	</div>

	<div class="well plate">
		{#if games.length === 0}
			<!-- Printed on the board rather than boxed on it. A panel here would be the tone of the well
			     it stands in, and an empty board is a sentence rather than an object. -->
			<p class="small empty">No game can be predicted right now.</p>
		{:else}
			<GameCards {games} {selected} {hrefOf} {onchoose} {onpreview} />
		{/if}
	</div>
</section>

<style>
	.board {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	/* What night the board is dealing and how much of it, which is the one thing the cards under it
	   cannot say together. */
	.slate {
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
		padding: var(--space-5);
		background: var(--plate-deep);
		border-radius: var(--radius-lg);
	}

	.empty {
		color: var(--plate-ink-muted);
	}
</style>
