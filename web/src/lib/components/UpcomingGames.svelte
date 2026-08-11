<!--
	The games that can be predicted right now, with the heading and the empty state around them.

	Every family that predicts on scheduled games opens with this, so it is one piece rather than the
	same three lines on each page.
-->
<script lang="ts">
	import GameCards from '$lib/components/GameCards.svelte';
	import Notice from '$lib/components/Notice.svelte';

	import type { ScheduledGame } from '$lib/types';

	type Props = {
		games: ScheduledGame[];
		/** The game the parameters currently describe, if they describe one. */
		selected: ScheduledGame | null;
		hrefOf: (game: ScheduledGame) => string;
		onchoose: (game: ScheduledGame) => void;
	};

	let { games, selected, hrefOf, onchoose }: Props = $props();
</script>

<section class="games">
	<h2>Upcoming games</h2>

	{#if games.length === 0}
		<Notice>No game can be predicted right now.</Notice>
	{:else}
		<GameCards {games} {selected} {hrefOf} {onchoose} />
	{/if}
</section>

<style>
	.games {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
</style>
