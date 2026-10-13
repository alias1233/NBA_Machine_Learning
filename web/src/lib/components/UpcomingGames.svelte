<script lang="ts">
	import FieldClear from '$lib/components/FieldClear.svelte';
	import GameCards from '$lib/components/GameCards.svelte';
	import { fullGameDay, gameDayLabel, gamesMatching, slateDays } from '$lib/games';
	import { MOTION, flow } from '$lib/motion';

	import type { ScheduledGame } from '$lib/types';

	type Props = {
		games: ScheduledGame[];
		/** The selected game, if there is one. */
		selected: ScheduledGame | null;
		hrefOf: (game: ScheduledGame) => string;
		onchoose: (game: ScheduledGame) => void;
		/** Called with the hovered game, and with null when the user leaves it. */
		onpreview?: (game: ScheduledGame | null) => void;
	};

	let { games, selected, hrefOf, onchoose, onpreview }: Props = $props();

	/** Minimum number of games before the search field is shown. */
	const WORTH_NARROWING = 6;

	const SEARCH = 'board-search';

	/** Search text used to filter the games. */
	let search = $state('');

	/** Measured width of the Clear button, so the text does not run under it. */
	let clearWidth = $state(0);

	let box = $state<HTMLInputElement>();

	/** True after the first render. */
	let drawn = $state(false);

	$effect(() => {
		drawn = true;
	});

	const narrowing = $derived(search.trim() !== '');
	const shown = $derived(gamesMatching(games, search));

	/** Games grouped by day. */
	const days = $derived(slateDays(shown));

	const counted = (of: number) => `${of} ${of === 1 ? 'game' : 'games'}`;

	const tally = $derived(
		narrowing ? `${shown.length} of ${counted(games.length)}` : counted(games.length)
	);

	/** Clears the field and keeps it focused. */
	function clear() {
		search = '';
		box?.focus();
	}
</script>

<section class="board" aria-labelledby="upcoming">
	<div class="column-label">
		<h2 class="micro" id="upcoming">Upcoming games</h2>
		{#if games.length > 0}
			<p class="micro tally" aria-live="polite">{tally}</p>
		{/if}
	</div>

	<div class="well plate">
		{#if games.length === 0}
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

						<div class="day" in:flow={{ duration: drawn ? MOTION : 0 }} out:flow>
							<div class="column-label day-head">
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

	.tally {
		color: var(--ink-muted);
		font-variant-numeric: tabular-nums;
	}

	.well {
		container-type: inline-size;
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		padding: var(--space-5);
		background: var(--plate-deep);
		border-radius: var(--radius-lg);
	}

	.narrow {
		position: relative;
		max-width: calc(var(--space-8) * 4);
		--surface: var(--plate);
	}

	.days {
		display: flex;
		flex-direction: column;
		margin-block-end: calc(var(--space-5) * -1);
	}

	.day {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		padding-block-end: var(--space-5);
	}

	.day-head {
		padding-block-start: var(--space-2);
	}

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
