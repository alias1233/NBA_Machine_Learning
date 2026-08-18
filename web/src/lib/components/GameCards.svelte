<!--
	The night's games, dealt as a hand of playing cards across the board.

	Each game is one card printed on bone stock in the plate's two inks. The two sides of the game are
	the two corner indices, exactly where a card prints its own, and the tip-off is its face. Which
	suit a card carries and how far off square it lies come from the game's id, so the hand is the same
	hand on every render and means nothing beyond making a night read as a deal rather than as a grid.

	Every game is dealt face up and none of them scrolls, because choosing one is now the first thing a
	reader does and a game they cannot see is a game they cannot pick. The board fits as many across a
	row as the column holding it has room for, so the same deal reads on a phone and beside two other
	columns on a laptop.

	Choosing a card changes parameters, it does not navigate. The reader stays exactly where they were
	and the URL is rewritten by replacing rather than pushing. The href is what the card falls back to
	where scripting is off. The chosen card lifts off the board, straightens, and takes the reader's
	own grease-pencil X, drawn in the corner its two indices leave free, because the printing on a card
	is what a reader takes the game off and a mark across it is a mark over the game.
-->
<script lang="ts">
	import PencilMark from '$lib/components/PencilMark.svelte';
	import { SUIT_PATH, deal, isRed } from '$lib/cards';
	import { gameDay, tipoffTime } from '$lib/games';

	import type { ScheduledGame } from '$lib/types';

	type Props = {
		games: ScheduledGame[];
		/** The game the parameters currently describe, if they describe one. */
		selected: ScheduledGame | null;
		hrefOf: (game: ScheduledGame) => string;
		onchoose: (game: ScheduledGame) => void;
		/** The card the reader is over or has focused, and null once they leave it. */
		onpreview?: (game: ScheduledGame | null) => void;
	};

	let { games, selected, hrefOf, onchoose, onpreview }: Props = $props();

	function choose(event: MouseEvent, game: ScheduledGame) {
		event.preventDefault();
		onchoose(game);
	}

	/** The card spoken as a sentence, since a reader hearing it has no corners to read. */
	function spoken(game: ScheduledGame): string {
		const when = [gameDay(game.date), tipoffTime(game)].filter(Boolean).join(', ');

		return [`${game.away_team.name} at ${game.home_team.name}`, when, game.is_mock ? 'test game' : '']
			.filter(Boolean)
			.join('. ');
	}
</script>

<ul class="hand" style:--dealt={games.length}>
	{#each games as game, index (game.id)}
		{@const chosen = game.id === selected?.id}
		{@const { suit, tilt } = deal(game.id)}
		{@const pip = SUIT_PATH[suit]}

		<li style:--tilt="{tilt}deg" style:--order={index}>
			<a
				class="card"
				class:chosen
				class:red={isRed(suit)}
				href={hrefOf(game)}
				aria-label={spoken(game)}
				aria-current={chosen ? 'true' : undefined}
				onclick={(event) => choose(event, game)}
				onpointerenter={() => onpreview?.(game)}
				onpointerleave={() => onpreview?.(null)}
				onfocus={() => onpreview?.(game)}
				onblur={() => onpreview?.(null)}
			>
				<span class="index start">
					<span class="tricode">{game.away_team.abbreviation}</span>
					<span class="name">{game.away_team.name}</span>
					<svg class="pip" viewBox="0 0 24 24" aria-hidden="true"><path d={pip} /></svg>
				</span>

				<!-- The card's face: what a reader picking a game actually needs off it. The suit stands
				     behind it as a watermark, printed faintly, the way a card's own face is. -->
				<span class="face">
					<svg class="watermark" viewBox="0 0 24 24" aria-hidden="true"><path d={pip} /></svg>
					<span class="time numeric">{tipoffTime(game) ?? 'Time to come'}</span>
					<span class="day micro">{gameDay(game.date)}</span>
				</span>

				<span class="index end">
					<svg class="pip" viewBox="0 0 24 24" aria-hidden="true"><path d={pip} /></svg>
					<span class="name">{game.home_team.name}</span>
					<span class="tricode"><span class="joiner">at</span> {game.home_team.abbreviation}</span>
				</span>

				<!-- The reader's own X, drawn in the corner the two indices leave free, so the card's
				     printing is never marked across. -->
				{#if chosen}
					<span class="marked"><PencilMark bleed="0" /></span>
				{/if}

				{#if chosen || game.is_mock}
					<span class="tags">
						{#if chosen}<span class="tag micro">Selected</span>{/if}
						{#if game.is_mock}<span class="tag micro">Test</span>{/if}
					</span>
				{/if}

			</a>
		</li>
	{/each}
</ul>

<style>
	/*
	 * A spread, not a fan. Cards lie side by side so both indices stay readable, and each sits at its
	 * own small angle so the deal reads as dealt rather than as ruled.
	 *
	 * As many across a row as the column has room for, measured against that column rather than
	 * against the screen, so one rule deals three across a narrow column and eight across the whole
	 * page. The row gap is what a lifted and ringed card needs above it.
	 */
	.hand {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(var(--play-card-min), 1fr));
		gap: var(--space-5) var(--space-4);
		/* The cards stack against each other and against nothing else. A lifted card belongs to the
		   board, not over the page, so its order can never reach the header above it. */
		isolation: isolate;
		/* How wide a card may print at, measured against the board rather than against the screen. It
		   grows with the board until a card is as large as one wants to be, which is what deals four
		   across the column a prediction page gives it and a whole row more across a wider one. */
		--play-card-min: clamp(var(--play-card-floor), 22cqi, var(--play-card-wide));
		margin: 0;
		padding: 0;
		list-style: none;
	}

	/* Each card measures its own printing, so the cell around it is what those sizes are read
	   against and no breakpoint decides them. It is also what the reader's mark is drawn on, which is
	   the card's own footprint on the board. */
	.hand > li {
		position: relative;
		container-type: inline-size;
		/* Later cards lie over earlier ones, and whichever is lifted lies over the lot. */
		z-index: var(--order);
	}

	/* A lifted card clears the whole deal and still keeps its place among the other lifted ones, so
	   the one dealt last is the one on top however many are on the board. */
	.hand > li:has(.card:hover),
	.hand > li:has(.card:focus-visible),
	.hand > li:has(.chosen) {
		z-index: calc(var(--order) + var(--dealt));
	}

	/*
	 * Bone stock printed in the plate's two inks, and it never changes colour. A card is one object
	 * whether or not it has been picked: what picking does is lift it off the board and mark it.
	 */
	.card {
		position: relative;
		display: grid;
		grid-template-rows: auto 1fr auto;
		aspect-ratio: var(--play-card-ratio);
		padding: clamp(var(--space-2), 7cqi, var(--space-3));
		background: var(--plate-ink);
		color: var(--plate-spot-on);
		border-radius: var(--radius);
		text-decoration: none;
		box-shadow: 0 2px 6px var(--acetate-shadow);
		rotate: var(--tilt);
		transition:
			rotate var(--motion) var(--ease-in),
			translate var(--motion) var(--ease-in),
			box-shadow var(--motion) var(--ease-in);
	}

	/* Picked up off the board: it straightens and lifts, which is what a hand does with a card. */
	.card:hover,
	.card:focus-visible,
	.card.chosen {
		rotate: 0deg;
		translate: 0 calc(var(--play-card-lift) * -1);
		box-shadow: 0 10px 20px var(--acetate-shadow);
	}

	.index {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: clamp(1px, 1cqi, var(--space-1));
		line-height: 1;
	}

	.index.end {
		align-items: flex-end;
	}

	.tricode {
		font-size: clamp(0.8125rem, 17cqi, 1.375rem);
		font-weight: 800;
		letter-spacing: -0.02em;
	}

	/*
	 * The side written out, under the tricode that stands for it. A card printed small has no room
	 * for it and drops it, the same way a real index carries a rank and nothing else, so it appears
	 * only once the board is dealing cards large enough to read one on.
	 */
	.name {
		display: none;
		font-size: clamp(0.625rem, 8cqi, var(--type-micro));
		font-weight: 500;
		line-height: 1.15;
		opacity: 0.7;
	}

	@container (min-width: 8rem) {
		.name {
			display: block;
		}
	}

	.index.end .name {
		text-align: end;
	}

	/* The one word on the card that is not a tricode, so it drops out of the index's weight. */
	.joiner {
		font-size: 0.6em;
		font-weight: 500;
		opacity: 0.65;
	}

	.pip {
		width: clamp(0.5rem, 11cqi, 0.9375rem);
		height: clamp(0.5rem, 11cqi, 0.9375rem);
		fill: currentColor;
	}

	/* Hearts and diamonds print in the plate's spot ink. It clears 3:1 against bone and not 4.5:1, so
	   it colours the pip and never a letter: every word on a card is printed in the one dark ink. */
	.card.red .pip,
	.card.red .watermark {
		color: var(--plate-spot);
	}

	.face {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: clamp(1px, 1cqi, var(--space-1));
		text-align: center;
	}

	/* The suit printed large and faint behind the face, which is what a card's own face carries. */
	.watermark {
		position: absolute;
		width: 62cqi;
		height: 62cqi;
		fill: currentColor;
		opacity: 0.09;
	}

	.time {
		position: relative;
		font-family: var(--font-mono);
		font-size: clamp(0.625rem, 13cqi, 1rem);
		font-weight: 500;
		letter-spacing: -0.02em;
		white-space: nowrap;
	}

	.day {
		position: relative;
		font-size: clamp(0.5625rem, 8.5cqi, var(--type-micro));
		opacity: 0.75;
	}

	/*
	 * Written on the board under the card rather than across its face, in the room the lift leaves,
	 * because a card's face is printed and the printing is what a reader takes the game off. Out of
	 * the flow, so a card carrying a tag is exactly the same card as one that is not.
	 *
	 * Colour is never the only marker of the chosen card: it lifts, it straightens, it is ringed, it
	 * carries this, and it carries aria-current.
	 */
	/* The room the printing leaves: the corner opposite neither index. It is measured against the
	   card, so the mark is the same size on a card dealt small as on one dealt large. */
	.marked {
		position: absolute;
		bottom: 4%;
		left: 5%;
		width: 34%;
		aspect-ratio: 1;
		--plane-pencil: var(--pencil-deep);
	}

	.tags {
		position: absolute;
		inset: 100% 0 auto 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-1);
		padding-block-start: var(--space-1);
		color: var(--plate-ink);
		font-size: clamp(0.5rem, 7cqi, var(--type-micro));
	}
</style>
