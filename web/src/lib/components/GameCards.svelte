<!--
	The fast path into a prediction: one square block per game that can be predicted right now.

	Choosing a card changes parameters, it does not navigate. The reader stays exactly where they
	were, and the URL is rewritten by replacing rather than pushing. The href is what the card falls
	back to where scripting is off.
-->
<script lang="ts">
	import { gameWhen } from '$lib/games';

	import type { ScheduledGame } from '$lib/types';

	type Props = {
		games: ScheduledGame[];
		/** The game the parameters currently describe, if they describe one. */
		selected: ScheduledGame | null;
		hrefOf: (game: ScheduledGame) => string;
		onchoose: (game: ScheduledGame) => void;
	};

	let { games, selected, hrefOf, onchoose }: Props = $props();

	function choose(event: MouseEvent, game: ScheduledGame) {
		event.preventDefault();
		onchoose(game);
	}
</script>

<ul class="cards">
	{#each games as game (game.id)}
		{@const chosen = game.id === selected?.id}

		<li>
			<a
				class="block card"
				class:chosen
				href={hrefOf(game)}
				aria-current={chosen ? 'true' : undefined}
				onclick={(event) => choose(event, game)}
			>
				<span class="micro muted">{gameWhen(game)}</span>

				<span class="matchup type-h2">
					{game.away_team.abbreviation}
					<span class="joiner small">at</span>
					{game.home_team.abbreviation}
				</span>

				<span class="tags">
					{#if chosen}
						<span class="tag micro">Selected</span>
					{/if}
					{#if game.is_mock}
						<span class="tag micro">Mock</span>
					{/if}
				</span>
			</a>
		</li>
	{/each}
</ul>

<style>
	/* Small enough that the whole slate and the controls under it are one short scroll, and never
	   wider than --card-max however much room the column has. */
	.cards {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, var(--card-max)));
		gap: var(--space-4);
		padding: 0;
		list-style: none;
	}

	/* Square, so a card reads as an object rather than as a row. */
	.card {
		display: grid;
		grid-template-rows: auto 1fr auto;
		aspect-ratio: var(--card-ratio);
		padding: var(--space-4);
		text-align: center;
		transition: transform var(--motion) var(--ease-in);
	}

	/* The one container that lifts rather than only colouring its top edge, because a grid of
	   squares needs a stronger signal than a hairline. */
	.card:hover,
	.card:focus-visible {
		transform: scale(var(--card-hover-scale));
	}

	.matchup {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
	}

	/* The one word on the card that is not a tricode, so it drops out of the serif line. */
	.joiner {
		font-family: var(--font-ui);
		color: var(--block-muted);
	}

	.tags {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: var(--space-2);
		min-height: var(--space-5);
	}

	.tag {
		color: var(--block-muted);
	}

	/* Colour is never the only marker, so the chosen card also carries a tag and aria-current. It
	   holds the hover scale, so choosing one reads as picking it up. */
	.chosen {
		background: var(--accent);
		color: var(--accent-on);
		transform: scale(var(--card-hover-scale));
	}

	.chosen .muted,
	.chosen .joiner,
	.chosen .tag {
		color: var(--accent-on);
	}

	/* The accent top edge would be invisible on an accent fill, so it inverts with the card. */
	.chosen:hover,
	.chosen:focus-visible {
		border-top-color: var(--accent-on);
	}

	@media (min-width: 40rem) {
		.cards {
			grid-template-columns: repeat(3, minmax(0, var(--card-max)));
		}
	}

	@media (min-width: 64rem) {
		.cards {
			grid-template-columns: repeat(4, minmax(0, var(--card-max)));
		}
	}
</style>
