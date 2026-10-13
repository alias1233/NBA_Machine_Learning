<script lang="ts">
	import { gameWhenFull } from '$lib/games';

	import type { ScheduledGame } from '$lib/types';

	type Props = {
		game: ScheduledGame | null;
		/** The game being hovered or focused. */
		previewed?: ScheduledGame | null;
	};

	let { game, previewed = null }: Props = $props();

	const shown = $derived(previewed ?? game);

	/** True when showing a previewed game and not the selected one. */
	const drawn = $derived(shown !== null && shown.id !== game?.id);

	const when = $derived(shown ? gameWhenFull(shown) : '');
</script>

<!-- A preview is hidden from screen readers. -->
<div class="matchup" class:drawn aria-hidden={drawn || undefined}>
	<p class="teams type-h2">
		{#if shown}
			<span class="team">{shown.away_team.name}</span>
			<span class="team"><span class="joiner">at</span> {shown.home_team.name}</span>
		{:else}
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
	.matchup {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		padding-block-end: var(--space-3);
		border-bottom: var(--rule-panel);
		transition: opacity var(--motion-fast) var(--ease-in);
	}

	.matchup.drawn {
		opacity: 0.45;
	}

	.teams {
		min-height: 2lh;
		text-wrap: balance;
	}

	.team {
		display: block;
	}

	.joiner {
		font-size: 0.6em;
		color: var(--ink-muted);
	}

	.when {
		min-height: 1lh;
		color: var(--ink-muted);
	}

	.blank {
		display: block;
		width: min(var(--fill), 60%);
		height: 0.62lh;
		margin-block: 0.19lh;
	}

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

	/* Stroke width is set in CSS because an SVG attribute cannot use a custom property. */
	.drawn-rule path {
		stroke-width: var(--pencil-width);
		vector-effect: non-scaling-stroke;
	}

	.matchup.drawn .drawn-rule {
		opacity: 1;
	}
</style>
