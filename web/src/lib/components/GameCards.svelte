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
	where scripting is off.

	Choosing one is a hand taking it off the board: it comes up out of the page, turns over on the
	upright axis so the reader sees its printed back at the top of the lift, and falls back square and
	clear of the deal, in warmed stock under the spot ink, ringed and marked with the reader's own
	grease-pencil X. Because it genuinely turns over, every card carries a back, and the back is the
	one printed thing on the site that belongs to the deck rather than to a game.

	The X is drawn once the card has landed, in the corner the two indices leave free, because a hand
	marks a card it is holding and not one still in the air, and because the printing on a card is what
	a reader takes the game off. A hovered card only lifts, and by half as much, so a card that has
	been chosen is never mistaken for one the pointer happens to be on.

	The turn runs only where the choice was made in front of the reader. A card that was already chosen
	when the page arrived is simply lying there, because nothing happened for it to answer. A reader
	who has asked for stillness is not given the turn at all, and their card lands marked at once.

	Every card keeps its own turn to the end. A reader who picks a second game before the first has
	landed does not have the first one snatched out of the air: it goes on turning, and because it is
	no longer the chosen card it comes down face up and square back into the deal, which is a card
	being put back.
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

	/**
	 * The crest printed on every back: the four suits set on the two axes around a centre pip.
	 *
	 * The same four paths the corner indices are drawn from, laid out here rather than in the markup
	 * so the placement is read as one figure. Each is a 24 box dropped into a 14 cell of the 48 the
	 * crest is drawn on, and the two reds sit across from each other so the emblem is balanced in both
	 * inks whichever way it is turned.
	 */
	const CREST = [
		{ suit: 'spade', at: 'translate(17 5.5) scale(0.5833)' },
		{ suit: 'heart', at: 'translate(28.5 17) scale(0.5833)' },
		{ suit: 'diamond', at: 'translate(17 28.5) scale(0.5833)' },
		{ suit: 'club', at: 'translate(5.5 17) scale(0.5833)' }
	] as const;

	/**
	 * The cards a turn is running on, which is normally one and never more than a handful.
	 *
	 * A list rather than a single card because a reader who picks a second game before the first has
	 * landed must not have the first one yanked out of the air. Each card keeps its own turn to the
	 * end, and one the choice has moved off finishes face up and settles back into the deal, which is
	 * what the animation lands on once the card is no longer the chosen one.
	 */
	let turning = $state<number[]>([]);

	/**
	 * Which game the board was last drawn for, so only a change the reader made runs the turn.
	 *
	 * Plain rather than state, because writing it is how the last choice is remembered and must not
	 * itself be a change. Undefined until the first run, which is what the board arrived with: a game
	 * already chosen then lies still, and every choice after it is turned over.
	 */
	let settled: number | null | undefined;

	$effect(() => {
		const chosen = selected?.id ?? null;

		if (settled === undefined) {
			settled = chosen;
			return;
		}

		if (chosen === settled) return;

		settled = chosen;

		/* A reader who has asked for stillness never gets a turn, so nothing may be left waiting on one
		   to finish. Asked here rather than in the stylesheet because the mark is held back until the
		   card has landed, and a card that never takes off has already landed. */
		if (chosen === null) return;
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
		if (turning.includes(chosen)) return;

		turning = [...turning, chosen];
	});

	function choose(event: MouseEvent, game: ScheduledGame) {
		event.preventDefault();
		onchoose(game);
	}

	/**
	 * The turn is over.
	 *
	 * Only the card's own animation ends it. The reader's mark draws itself on arrival and its own
	 * ending bubbles up through the same handler, which would otherwise call the turn finished before
	 * it had started.
	 */
	function landed(
		event: AnimationEvent & { currentTarget: EventTarget & HTMLAnchorElement },
		id: number
	) {
		if (event.target === event.currentTarget) turning = turning.filter((at) => at !== id);
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
		{@const overturn = turning.includes(game.id)}
		{@const { suit, tilt } = deal(game.id)}
		{@const pip = SUIT_PATH[suit]}

		<li style:--tilt="{tilt}deg" style:--order={index}>
			<a
				class="card"
				class:chosen
				class:landing={overturn}
				class:red={isRed(suit)}
				onanimationend={(event) => landed(event, game.id)}
				href={hrefOf(game)}
				aria-label={spoken(game)}
				aria-current={chosen ? 'true' : undefined}
				onclick={(event) => choose(event, game)}
				onpointerenter={() => onpreview?.(game)}
				onpointerleave={() => onpreview?.(null)}
				onfocus={() => onpreview?.(game)}
				onblur={() => onpreview?.(null)}
			>
				<span class="front">
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
					     printing is never marked across. It is laid once the card is lying still, because a
					     hand marks a card it is holding rather than one still turning. -->
					{#if chosen && !overturn}
						<span class="marked"><PencilMark bleed="0px" /></span>
					{/if}
				</span>

				<!-- The back of the deck, and the same back on every card, because a back that told you
				     which card it was would not be one. Bone margin, a field of the dark ink under a
				     printed lattice in the spot ink, and the four suits set as a crest, which is the one
				     figure on the site that stands for the deck rather than for a game. -->
				<span class="back" aria-hidden="true">
					<span class="weave"></span>
					<svg class="crest" viewBox="0 0 48 48">
						<circle class="disc" cx="24" cy="24" r="22.2" />
						{#each CREST as { suit: figure, at } (figure)}
							<path class:red={isRed(figure)} transform={at} d={SUIT_PATH[figure]} />
						{/each}
						<circle class="centre" cx="24" cy="24" r="2.3" />
					</svg>
				</span>
			</a>

			{#if chosen || game.is_mock}
				<span class="tags">
					{#if chosen}<span class="tag micro">Selected</span>{/if}
					{#if game.is_mock}<span class="tag micro">Test</span>{/if}
				</span>
			{/if}
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

	/*
	 * Each card measures its own printing, so the cell around it is what those sizes are read
	 * against and no breakpoint decides them. It is also what the reader's tag hangs off, which is
	 * the card's own footprint on the board.
	 *
	 * The cell is also where the board's vanishing point stands, one to a card and centred on it, so
	 * a card turning over turns toward the reader looking at that card and not toward the middle of
	 * the screen.
	 */
	.hand > li {
		position: relative;
		container-type: inline-size;
		perspective: var(--play-card-depth);
		/* Rows lean off each other, one to the left and the next to the right by the same amount, so no
		   two cards line up down the board and the deal reads as a hand pushed across a table rather
		   than as a grid. Which row a card is in is worked out from its place in the deal and how many
		   are dealt across, and the offset is drawn rather than laid out, so nothing about the grid
		   moves. */
		--play-card-row: round(down, calc(var(--order) / var(--play-card-columns)), 1);
		--play-card-lean: calc(mod(var(--play-card-row), 2) * 2 - 1);
		translate: calc(var(--play-card-lean) * var(--play-card-stagger)) 0;
		/* Later cards lie over earlier ones, and whichever is lifted lies over the lot. */
		z-index: var(--order);
	}

	/*
	 * How many cards the board is dealing across, which CSS has no way to ask the grid for.
	 *
	 * These are the widths `auto-fill` itself changes its answer at, worked out from the one rule
	 * above it: a row holds as many tracks of --play-card-min plus a gap as the board has room for,
	 * and --play-card-min is the clamp on the line that sets it. They are read against the board, the
	 * same container the deal is, so the two are asking about the same width.
	 *
	 * Only the stagger reads this. If a threshold ever falls a hair from where the grid puts it, one
	 * row of one board leans the other way at one width, which is a decoration disagreeing with
	 * itself and never a layout breaking. The deal itself is still the grid's own answer.
	 */
	.hand {
		--play-card-columns: 1;
	}

	@container (min-width: 11.5rem) {
		.hand {
			--play-card-columns: 2;
		}
	}

	@container (min-width: 17.75rem) {
		.hand {
			--play-card-columns: 3;
		}
	}

	@container (min-width: 25rem) {
		.hand {
			--play-card-columns: 4;
		}
	}

	@container (min-width: 45.25rem) {
		.hand {
			--play-card-columns: 5;
		}
	}

	@container (min-width: 54.5rem) {
		.hand {
			--play-card-columns: 6;
		}
	}

	@container (min-width: 63.75rem) {
		.hand {
			--play-card-columns: 7;
		}
	}

	@container (min-width: 73rem) {
		.hand {
			--play-card-columns: 8;
		}
	}

	/* A lifted card clears the whole deal and still keeps its place among the other lifted ones, so
	   the one dealt last is the one on top however many are on the board. */
	.hand > li:has(.card:hover),
	.hand > li:has(.card:focus-visible),
	.hand > li:has(.chosen) {
		z-index: calc(var(--order) + var(--dealt));
	}

	/*
	 * The card itself is the stock, which has two printed sides and no printing of its own. It holds
	 * the proportion, the angle it was dealt at, how far it lies off the board and what it casts on
	 * it, and its two faces hold everything that is printed.
	 */
	.card {
		position: relative;
		display: block;
		aspect-ratio: var(--play-card-ratio);
		border-radius: var(--radius);
		text-decoration: none;
		box-shadow: 0 2px 6px var(--acetate-shadow);
		rotate: var(--tilt);
		transform-style: preserve-3d;
		transition:
			rotate var(--motion) var(--ease-in),
			translate var(--motion) var(--ease-in),
			box-shadow var(--motion) var(--ease-in);
	}

	/*
	 * Both printed sides fill the stock exactly and neither is ever seen from behind, which is what
	 * lets one card carry a face and a back without either showing through the other.
	 */
	.front,
	.back {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		backface-visibility: hidden;
	}

	/*
	 * The face: bone stock printed in the plate's two inks. Every card is dealt the same, and
	 * everything that says one has been chosen is added to it rather than swapped in.
	 */
	.front {
		display: grid;
		grid-template-rows: auto 1fr auto;
		padding: clamp(var(--space-2), 7cqi, var(--space-3));
		background: var(--plate-ink);
		color: var(--plate-spot-on);
		transition: background var(--motion) var(--ease-in);
	}

	/* Under the pointer a card straightens and comes up a little, which is a hand about to take it. */
	.card:hover,
	.card:focus-visible {
		rotate: 0deg;
		translate: 0 calc(var(--play-card-lift) * -0.5);
		box-shadow: 0 7px 14px var(--acetate-shadow);
	}

	/*
	 * Taken. It lies square and clear of the board, in stock the spot ink has warmed, ringed in that
	 * same ink and lit from under its own edge. Twice the lift of a hovered card, so which of the two a
	 * reader is looking at is never in question.
	 */
	.card.chosen {
		rotate: 0deg;
		translate: 0 calc(var(--play-card-lift) * -1);
		box-shadow:
			0 0 0 1px var(--plate-spot),
			0 12px 22px var(--acetate-shadow),
			0 0 24px -4px color-mix(in oklab, var(--plate-spot) 60%, transparent);
	}

	.card.chosen .front {
		background: color-mix(in oklab, var(--plate-ink) 84%, var(--plate-spot));
	}

	/*
	 * The back of the deck.
	 *
	 * A real back is a margin of bare stock, a field of one ink, and a figure printed on it, and it is
	 * the same on every card in the pack. This one is exactly that, in the plate's own inks and in the
	 * plate's own manner: flat, registered, and nothing about it hand-made.
	 *
	 * It is drawn once for a card that has never been turned over, which costs the board nothing, and
	 * it is never in the accessible tree, because a reader hearing the card is being told the game and
	 * a back is not one.
	 */
	.back {
		display: grid;
		place-items: center;
		background: var(--plate-ink);
		transform: rotateY(180deg);
	}

	/*
	 * The field, held inside the bone margin and ruled in the spot ink.
	 *
	 * The lattice is two printed rules crossing at the square, one in each ink, which is how a
	 * guilloche back is actually made up. Its pitch is measured against the card, so a card dealt
	 * small carries the same figure at the same scale as one dealt large rather than a coarser one.
	 */
	.weave {
		position: absolute;
		inset: clamp(3px, 5.5cqi, 8px);
		background-color: var(--plate-spot-on);
		background-image:
			repeating-linear-gradient(
				45deg,
				transparent 0 7cqi,
				color-mix(in oklab, var(--plate-spot) 62%, transparent) 7cqi calc(7cqi + 1px)
			),
			repeating-linear-gradient(
				-45deg,
				transparent 0 7cqi,
				color-mix(in oklab, var(--plate-ink) 26%, transparent) 7cqi calc(7cqi + 1px)
			);
		box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--plate-spot) 70%, transparent);
	}

	/*
	 * The crest: the four suits on the two axes around a centre pip, printed on a disc of bare stock
	 * so the figure reads out of the lattice rather than over it. The two reds carry the spot ink and
	 * the two blacks the dark, which is the same rule the corner pips are printed by.
	 */
	.crest {
		position: relative;
		width: 52cqi;
		height: 52cqi;
	}

	.disc {
		fill: var(--plate-ink);
		stroke: var(--plate-spot);
		stroke-width: 1.1;
	}

	.crest path {
		fill: var(--plate-spot-on);
	}

	.crest path.red,
	.centre {
		fill: var(--plate-spot);
	}

	/*
	 * The turn itself: up out of the page, over on the upright axis, and down into where it now lies.
	 * A card is the one thing on the site a hand physically picks up, so a choice here is a gesture
	 * rather than a state arriving, and it is the only place on the site anything turns over.
	 *
	 * It turns the way a hand turns a card, about the axis standing up the card, so what the turn
	 * shows halfway through is the back of the deck and never the face printed backwards. It grows as
	 * it goes, against the vanishing point the cell holds over it, which is what reads as leaving the
	 * page rather than sliding across it.
	 *
	 * Two full half-turns, because it has to come back down the way it went up. The whole thing is
	 * written against where the card ends up: it starts at the angle it was dealt at and on the board,
	 * and finishes square, lifted and a whole turn round, which is exactly how a chosen card rests, so
	 * nothing snaps when the animation hands back. The transition is stood down for the turn so the
	 * two are never both moving the same card.
	 */
	@media (prefers-reduced-motion: no-preference) {
		.card.landing {
			animation:
				lift var(--play-card-turn) both,
				turn var(--play-card-turn) both;
			transition: none;
			will-change: transform, translate, scale;
		}

		/* The stock warms as the card comes back round, not while its back is to the reader, so the
		   spot ink arrives with the face rather than behind it. */
		.card.landing .front {
			animation: warm var(--play-card-turn) linear both;
			transition: none;
		}
	}

	/*
	 * The toss. Away from the board fast and settling at the top, which is the shape a thing thrown
	 * actually makes, then falling and slowing into where it comes to rest. It straightens on the way
	 * up, because a hand squares a card as it takes it and not after it has put it down.
	 *
	 * Written apart from the turn because the two are one gesture with two different rhythms: a toss
	 * is front-loaded and a turn is even, and one curve over both makes the card show its back before
	 * it has left the board.
	 */
	@keyframes lift {
		0% {
			rotate: var(--tilt);
			translate: 0 0;
			scale: 1;
			box-shadow: 0 2px 6px var(--acetate-shadow);
			animation-timing-function: cubic-bezier(0.18, 0.72, 0.36, 1);
		}

		46% {
			rotate: 0deg;
			translate: 0 calc(var(--play-card-lift) * -2.3);
			scale: var(--play-card-rise);
			box-shadow: 0 26px 38px -8px var(--acetate-shadow);
			animation-timing-function: cubic-bezier(0.5, 0, 0.22, 1);
		}
	}

	/*
	 * The turn: two half-turns about the axis standing up the card, so what the reader is shown
	 * halfway round is the back of the deck.
	 *
	 * It holds a beat at the back, at the top of the toss, because that beat is the whole reason a
	 * back is worth printing, and then carries on the way it was going rather than unwinding, which
	 * is what tells a turn from a wobble.
	 */
	@keyframes turn {
		0% {
			transform: rotateY(0deg);
			animation-timing-function: cubic-bezier(0.5, 0, 0.3, 1);
		}

		42% {
			transform: rotateY(180deg);
			animation-timing-function: linear;
		}

		56% {
			transform: rotateY(196deg);
			animation-timing-function: cubic-bezier(0.42, 0, 0.25, 1);
		}

		100% {
			transform: rotateY(360deg);
		}
	}

	@keyframes warm {
		0%,
		56% {
			background: var(--plate-ink);
		}
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

	/* Held off the corner the mark is drawn in, so a side with a long name wraps rather than running
	   under the X. The tricode is short enough never to need it. */
	.index.end .name {
		max-width: 70%;
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

	/* The room the printing leaves: the corner opposite neither index. It is measured against the
	   card, so the mark is the same size on a card dealt small as on one dealt large. */
	.marked {
		position: absolute;
		bottom: 3%;
		left: 4%;
		width: 28%;
		aspect-ratio: 1;
		--plane-pencil: var(--pencil-deep);
	}

	/*
	 * Written on the board under the card rather than across its face, in the room the lift leaves,
	 * because a card's face is printed and the printing is what a reader takes the game off. It lies
	 * on the board rather than on the card, so a card turning over turns and the tag under it does
	 * not, and a card carrying one is exactly the same card as one that is not.
	 *
	 * Colour is never the only marker of the chosen card: it lifts, it straightens, it is ringed, it
	 * carries this, and it carries aria-current.
	 */
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
		pointer-events: none;
	}
</style>
