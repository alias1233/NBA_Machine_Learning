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

	A board holding more than a night's worth of cards also carries a field to narrow it by, stamped
	at the head of the well. It belongs to the board rather than to the parameters beside it, because
	it only ever changes which cards are on the table and never what is being asked of the model. It
	is a filter and not a second way to choose: the cards are still the only thing that picks a game,
	and every one of them stays face up.
-->
<script lang="ts">
	import FieldClear from '$lib/components/FieldClear.svelte';
	import GameCards from '$lib/components/GameCards.svelte';
	import { fullGameDay, gameDayLabel, gamesMatching, slateDays } from '$lib/games';
	import { MOTION, flow } from '$lib/motion';

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

	/**
	 * How large the board has to be before it is worth carrying a field to narrow it.
	 *
	 * A night or two of cards is read in one look, and a control over a board a reader can already
	 * take in is furniture. Roughly a full evening's slate, which is where scanning for one matchup
	 * starts to be work.
	 */
	const WORTH_NARROWING = 6;

	/** One board to a page, so the field can be named on it rather than told what to call itself. */
	const SEARCH = 'board-search';

	/** What the reader is narrowing the board by, and empty whenever they are not. */
	let search = $state('');

	/** Measured rather than reserved, so the words never run under the Clear control beside them. */
	let clearWidth = $state(0);

	let box = $state<HTMLInputElement>();

	/**
	 * Whether the board has been drawn once, so a day opens in motion only where the reader closed
	 * or opened it themselves. The cards keep the same rule for the same reason. See GameCards.
	 */
	let drawn = $state(false);

	$effect(() => {
		drawn = true;
	});

	const narrowing = $derived(search.trim() !== '');
	const shown = $derived(gamesMatching(games, search));

	/** The slate a day at a time, which is how the board deals it. */
	const days = $derived(slateDays(shown));

	/** How many games are being dealt, said the way a reader counts them. */
	const counted = (of: number) => `${of} ${of === 1 ? 'game' : 'games'}`;

	/* Narrowed, the count says how much of the board is left as well as how much of it there is, so
	   a reader who has typed something knows they are looking at part of it. */
	const tally = $derived(
		narrowing ? `${shown.length} of ${counted(games.length)}` : counted(games.length)
	);

	/** Empties the field and leaves the reader in it, because clearing is rarely the last thing done. */
	function clear() {
		search = '';
		box?.focus();
	}
</script>

<section class="board" aria-labelledby="upcoming">
	<div class="column-label">
		<h2 class="micro" id="upcoming">Upcoming games</h2>
		{#if games.length > 0}
			<!-- Spoken as it settles, because a reader narrowing the board by ear has nothing else that
			     says how much of it answered. -->
			<p class="micro tally" aria-live="polite">{tally}</p>
		{/if}
	</div>

	<div class="well plate">
		{#if games.length === 0}
			<!-- Printed on the board rather than boxed on it. A panel here would be the tone of the well
			     it stands in, and an empty board is a sentence rather than an object. -->
			<p class="small empty">No game can be predicted right now.</p>
		{:else}
			{#if games.length >= WORTH_NARROWING}
				<div class="field narrow">
					<label class="micro" for={SEARCH}>Find a game</label>

					<input
						bind:this={box}
						id={SEARCH}
						type="text"
						autocomplete="off"
						placeholder="Search by a team in the game"
						bind:value={search}
						style:padding-right={search === '' ? null : `calc(${clearWidth}px + var(--space-2))`}
						onkeydown={(event) => event.key === 'Escape' && clear()}
					/>

					<!-- Inside the box it empties, and only while there is something to empty. -->
					{#if search !== ''}
						<FieldClear empties="game search" bind:width={clearWidth} onclear={clear} />
					{/if}
				</div>
			{/if}

			{#if days.length === 0}
				<p class="small empty" in:flow>No upcoming game is between those teams.</p>
			{:else}
				<div class="days">
					{#each days as { date, games: dealt } (date)}
						{@const label = gameDayLabel(date)}
						{@const written = fullGameDay(date)}

						<!--
							A heading and the run of cards under it, rather than a region of its own. The board
							is already one, and a landmark per day would bury it in a list of five.

							A day the search has emptied closes rather than being taken away, so the board
							settles under the reader instead of jumping to its new height.
						-->
						<div class="day" in:flow={{ duration: drawn ? MOTION : 0 }} out:flow>
							<div class="column-label day-head">
								<!-- The day stamped, then written out beside it wherever the stamp is a word
								     rather than a date, because "Today" alone never says which day it was read on. -->
								<h3 class="day-name">
									{label}
									{#if label !== written}<span class="micro day-date">{written}</span>{/if}
								</h3>
								<p class="micro tally">{counted(dealt.length)}</p>
							</div>

							<GameCards games={dealt} {selected} {hrefOf} {onchoose} {onpreview} />
						</div>
					{/each}
				</div>
			{/if}
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
		gap: var(--space-5);
		padding: var(--space-5);
		background: var(--plate-deep);
		border-radius: var(--radius-lg);
	}

	/*
	 * The field the board is narrowed by, stamped at the head of the well.
	 *
	 * Its box is printed in the plate's own stock rather than the well's, because a control drawn in
	 * the tone of the area it stands on is a hairline and nothing else. It is held to the width a
	 * couple of team names need, so a board given the whole page does not stamp a search box across
	 * all of it.
	 */
	.narrow {
		position: relative;
		max-width: calc(var(--space-8) * 4);
		--surface: var(--plate);
	}

	/*
	 * The days, and the room between them.
	 *
	 * Each day carries the space under it rather than the run of days carrying gaps between them, so
	 * a day the search closes takes its own room with it as it goes instead of leaving a gap behind
	 * that collapses in one frame once it is gone. The last day's is given back to the well.
	 */
	.days {
		display: flex;
		flex-direction: column;
		margin-block-end: calc(var(--space-5) * -1);
	}

	.day {
		display: flex;
		flex-direction: column;
		/* Room for a card in the first row to be lifted and ringed without reaching the rule the day
		   is stamped under. */
		gap: var(--space-5);
		padding-block-end: var(--space-5);
	}

	/* Stamped nearer its own rule than a region's label is to the page's. The board prints one of
	   these per day, so what a region spends once on air above its label this spends on every night
	   it is holding. */
	.day-head {
		padding-block-start: var(--space-2);
	}

	/*
	 * The day, stamped in the plate's own face. It is set above the micro labels around it because it
	 * is what a reader scanning for a date lands on, and it is the one word on the board large enough
	 * to be found without reading anything else. Weight, face and case are what rank it, so it is
	 * stamped no larger than a run of days can afford down the board.
	 */
	.day-name {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--space-1) var(--space-3);
		font-size: var(--type-small);
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
