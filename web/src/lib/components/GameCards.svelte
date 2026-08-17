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
				<span class="when micro muted">{gameWhen(game)}</span>

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
	   wider than --card-max however much room the column has. A width decides how many fit on a row
	   and nothing else, because the card sizes itself. */
	.cards {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, var(--card-max)));
		gap: var(--space-4);
		padding: 0;
		list-style: none;
	}

	/* Each card measures its own text, so the cell around it is what the card tokens are read
	   against. */
	.cards > li {
		container-type: inline-size;
	}

	/* Square, so a card reads as an object rather than as a row. It grows past square only where a
	   long date needs the room. */
	.card {
		display: grid;
		grid-template-rows: auto 1fr auto;
		aspect-ratio: var(--card-ratio);
		padding: var(--card-padding);
		text-align: center;
		transition: transform var(--motion) var(--ease-in);
	}

	/* The one container that lifts rather than only colouring its top edge, because a grid of
	   squares needs a stronger signal than a hairline. */
	.card:hover,
	.card:focus-visible {
		transform: scale(var(--card-hover-scale));
	}

	/* A card carries two type sizes and both are measured against the card. */
	.matchup {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		font-size: var(--card-matchup);
	}

	.when,
	.joiner,
	.tag {
		font-size: var(--card-label);
	}

	/* The one word on the card that is not a tricode, so it drops out of the serif line. */
	.joiner {
		font-family: var(--font-ui);
		color: var(--block-muted);
	}

	/* Stacked rather than wrapped, and measured by what it holds. A wrapping row counts as one line
	   however many tags are in it, so a second tag would hang out of the bottom of the card. One
	   line is reserved whether or not there is a tag, so nothing moves when one appears. */
	.tags {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-2);
		height: max-content;
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

	@media (min-width: 64rem) {
		.cards {
			grid-template-columns: repeat(5, minmax(0, var(--card-max)));
		}
	}
</style>
