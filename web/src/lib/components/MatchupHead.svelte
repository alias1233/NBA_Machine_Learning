<!--
	The game a prediction is about, standing above the parameters that describe it.

	It is the one place the two teams are named in full. The board deals tricodes on a playing card,
	and a reader who has just picked one card out of fifteen should read back what they picked in
	words before choosing a stat.

	It follows the reader across the board. A card under the pointer is written here in grease
	pencil, faint and underlined by hand, because it is a question that has not been asked yet. The
	card they settle on is printed at full strength on a printed rule. That is the plate world's own
	split, printed for what is settled and drawn for what is being asked, and this is the one place
	on paper that borrows it.

	It holds its own height empty, so nothing under it moves while the reader runs across the board,
	and before a game has been picked it stands as the empty lines the two teams and the tip-off will
	be written on.
-->
<script lang="ts">
	import { gameWhenFull } from '$lib/games';

	import type { ScheduledGame } from '$lib/types';

	type Props = {
		/** The game the form names, printed. Null before one has been picked. */
		game: ScheduledGame | null;
		/** The card under the reader's pointer or keyboard focus, drawn rather than printed. */
		previewed?: ScheduledGame | null;
	};

	let { game, previewed = null }: Props = $props();

	/** A preview wins while there is one, because it is what the reader is looking at. */
	const shown = $derived(previewed ?? game);

	/** Drawn rather than printed: a game being considered rather than the one that was picked. */
	const drawn = $derived(shown !== null && shown.id !== game?.id);

	const when = $derived(shown ? gameWhenFull(shown) : '');
</script>

<!-- A preview is not announced. It is whatever the pointer happens to be over, and the card itself
     already speaks its whole game when it takes focus. -->
<div class="matchup" class:drawn aria-hidden={drawn || undefined}>
	<p class="teams type-h2">
		{#if shown}
			<span class="team">{shown.away_team.name}</span>
			<span class="team"><span class="joiner">at</span> {shown.home_team.name}</span>
		{:else}
			<!-- The two lines the two teams will be written on, standing empty. A head holding nothing
			     at all read as a gap in the page rather than as a slot waiting to be filled. -->
			<span class="team blank reserved" style="--fill: 11ch"></span>
			<span class="team blank reserved" style="--fill: 8ch"></span>
		{/if}
	</p>

	<p class="when micro">
		{#if when}
			{when}
		{:else}
			<span class="blank reserved" style="--fill: 18ch"></span>
		{/if}
	</p>

	<!-- The reader's own underline, in the same wet-erase pencil as the ring on the card they are
	     hovering, drawn over the printed rule rather than in place of it. -->
	<svg class="drawn-rule" viewBox="0 0 300 6" preserveAspectRatio="none" aria-hidden="true">
		<path
			d="M1 4.2C38 2.4 75 4.8 112 3.4 149 2 186 4.6 223 3.2 251 2.2 275 3.8 299 2.6"
			fill="none"
			stroke="currentColor"
			stroke-linecap="round"
			vector-effect="non-scaling-stroke"
		/>
	</svg>
</div>

<style>
	/*
	 * The rule under it is printed whether or not there is a game, because it is what opens the
	 * fields below and an empty head is a slot waiting to be filled rather than a gap. The pencil is
	 * drawn over that rule rather than in place of it.
	 */
	.matchup {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		padding-block-end: var(--space-3);
		border-bottom: var(--rule-panel);
		transition: opacity var(--motion-fast) var(--ease-in);
	}

	/* Faint, because it is a question rather than an answer. Not muted ink: the words are the same
	   words either way and only their weight on the page changes. */
	.matchup.drawn {
		opacity: 0.45;
	}

	/* Two lines, so the two sides read as two teams rather than as one long line that wraps wherever
	   the column happens to end. Reserved at two lines, so the head is the same height empty. */
	.teams {
		min-height: 2lh;
		text-wrap: balance;
	}

	.team {
		display: block;
	}

	/* The one word here that is not a team, so it drops out of the name's size and weight the same
	   way it does in a card's index. */
	.joiner {
		font-size: 0.6em;
		color: var(--ink-muted);
	}

	.when {
		min-height: 1lh;
		color: var(--ink-muted);
	}

	/* The line a value will be written on. It is drawn short of the line it stands in, so a slot never
	   fills the row the way the words that replace it will. */
	.blank {
		display: block;
		width: min(var(--fill), 60%);
		height: 0.62lh;
		margin-block: 0.19lh;
	}

	/* Drawn over the printed rule, wider than it at both ends, because a drawn line does not stop
	   where a printed one does. It is a mark rather than a letter, so the pencil colours it. */
	.drawn-rule {
		position: absolute;
		inset: auto calc(var(--space-2) * -1) -3px;
		display: block;
		height: 6px;
		color: var(--plane-pencil);
		opacity: 0;
		pointer-events: none;
		transition: opacity var(--motion-fast) var(--ease-in);
	}

	/* The pencil's own weight, set here rather than on the path, because a presentation attribute
	   cannot read a token. The stroke does not scale with the stretched viewBox. */
	.drawn-rule path {
		stroke-width: var(--pencil-width);
		vector-effect: non-scaling-stroke;
	}

	.matchup.drawn .drawn-rule {
		opacity: 1;
	}
</style>
