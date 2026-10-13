<script lang="ts">
	import { flip } from 'svelte/animate';

	import PencilMark from '$lib/components/PencilMark.svelte';
	import { SUIT_PATH, deal, isRed } from '$lib/cards';
	import { gameDay, tipoffTime } from '$lib/games';
	import { MOTION, dealing, timed } from '$lib/motion';

	import type { ScheduledGame } from '$lib/types';

	type Props = {
		games: ScheduledGame[];
		/** The selected game, if there is one. */
		selected: ScheduledGame | null;
		hrefOf: (game: ScheduledGame) => string;
		onchoose: (game: ScheduledGame) => void;
		/** Called with the hovered or focused game, and with null when the user leaves it. */
		onpreview?: (game: ScheduledGame | null) => void;
	};

	let { games, selected, hrefOf, onchoose, onpreview }: Props = $props();

	/** Ids of the cards that are currently flipping. */
	let turning = $state<number[]>([]);

	/** Id of the last selected game. Not reactive, so writing it does not rerun the effect. */
	let settled: number | null | undefined;

	/** True after the first render. */
	let drawn = $state(false);

	$effect(() => {
		drawn = true;
	});

	$effect(() => {
		const chosen = selected?.id ?? null;

		if (settled === undefined) {
			settled = chosen;
			return;
		}

		if (chosen === settled) return;

		settled = chosen;

		// No flip if nothing is selected or the user prefers reduced motion.
		if (chosen === null) return;
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
		if (turning.includes(chosen)) return;

		turning = [...turning, chosen];
	});

	function choose(event: MouseEvent, game: ScheduledGame) {
		event.preventDefault();
		onchoose(game);
	}

	/** Ends a flip. Ignores animation events that bubble up from child elements. */
	function landed(
		event: AnimationEvent & { currentTarget: EventTarget & HTMLAnchorElement },
		id: number
	) {
		if (event.target === event.currentTarget) turning = turning.filter((at) => at !== id);
	}

	/** Returns the card's text for screen readers. */
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

		<li
			style:--tilt="{tilt}deg"
			style:--order={index}
			animate:flip={{ duration: timed(MOTION) }}
			in:dealing={{ duration: drawn ? MOTION : 0 }}
			out:dealing
		>
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

					<span class="face">
						<svg class="watermark" viewBox="0 0 24 24" aria-hidden="true"><path d={pip} /></svg>
						<span class="time numeric">{tipoffTime(game) ?? 'Time to come'}</span>
					</span>

					<span class="index end">
						<svg class="pip" viewBox="0 0 24 24" aria-hidden="true"><path d={pip} /></svg>
						<span class="name">{game.home_team.name}</span>
						<span class="tricode"><span class="joiner">at</span> {game.home_team.abbreviation}</span>
					</span>

					{#if chosen && !overturn}
						<span class="marked"><PencilMark bleed="0px" /></span>
					{/if}
				</span>

				<span class="back" aria-hidden="true">
					<span class="weave"></span>
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
	.hand {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(var(--play-card-min), 1fr));
		gap: var(--space-5) var(--space-4);
		isolation: isolate;
		--play-card-min: clamp(var(--play-card-floor), 22cqi, var(--play-card-wide));
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.hand > li {
		position: relative;
		container-type: inline-size;
		perspective: var(--play-card-depth);
		--play-card-row: round(down, calc(var(--order) / var(--play-card-columns)), 1);
		--play-card-lean: calc(mod(var(--play-card-row), 2) * 2 - 1);
		translate: calc(var(--play-card-lean) * var(--play-card-stagger)) 0;
		z-index: var(--order);
	}

	/* Number of card columns. The breakpoints match where `auto-fill` adds a column. */
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

	.hand > li:has(.card:hover),
	.hand > li:has(.card:focus-visible),
	.hand > li:has(.chosen) {
		z-index: calc(var(--order) + var(--dealt));
	}

	.card {
		position: relative;
		display: block;
		aspect-ratio: var(--play-card-ratio);
		border-radius: var(--radius);
		text-decoration: none;
		box-shadow: var(--play-card-shadow);
		rotate: var(--tilt);
		transform-style: preserve-3d;
		transition:
			rotate var(--motion) var(--ease-in),
			translate var(--motion) var(--ease-in),
			box-shadow var(--motion) var(--ease-in);
	}

	.front,
	.back {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		backface-visibility: hidden;
	}

	.front {
		display: grid;
		grid-template-rows: auto 1fr auto;
		padding: clamp(0.375rem, 7cqi, var(--space-3));
		background: var(--plate-ink);
		color: var(--plate-spot-on);
		transition: background var(--motion) var(--ease-in);
	}

	.card:hover,
	.card:focus-visible {
		rotate: 0deg;
		translate: 0 calc(var(--play-card-lift) * -0.5);
		box-shadow: var(--play-card-shadow-near);
	}

	.card.chosen {
		rotate: 0deg;
		translate: 0 calc(var(--play-card-lift) * -1);
		box-shadow:
			0 0 0 1px var(--plate-spot),
			var(--play-card-shadow-taken),
			0 0 24px -4px color-mix(in oklab, var(--plate-spot) 60%, transparent);
	}

	.card.chosen .front {
		background: color-mix(in oklab, var(--plate-ink) 84%, var(--plate-spot));
	}

	/* Back face of a card. */
	.back {
		background: var(--plate-ink);
		transform: rotateY(180deg);
	}

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

	@media (prefers-reduced-motion: no-preference) {
		.card.landing {
			animation:
				lift var(--play-card-turn) both,
				turn var(--play-card-turn) both;
			transition: none;
			will-change: transform, translate, scale;
		}

		.card.landing .front {
			animation: warm var(--play-card-turn) linear both;
			transition: none;
		}
	}

	@keyframes lift {
		0% {
			rotate: var(--tilt);
			translate: 0 0;
			scale: 1;
			box-shadow: var(--play-card-shadow);
			animation-timing-function: cubic-bezier(0.18, 0.72, 0.36, 1);
		}

		46% {
			rotate: 0deg;
			translate: 0 calc(var(--play-card-lift) * -2.3);
			scale: var(--play-card-rise);
			box-shadow: var(--play-card-shadow-air);
			animation-timing-function: cubic-bezier(0.5, 0, 0.22, 1);
		}
	}

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

	.name {
		font-size: clamp(0.625rem, 10cqi, 0.875rem);
		font-weight: 500;
		line-height: 1.1;
		text-wrap: balance;
	}

	.index.end .name {
		max-width: 70%;
		text-align: end;
	}

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

	/* The highlight color has 3:1 contrast on the card face but not 4.5:1, so it is used for the suit icons and never for text. */
	.card.red .pip,
	.card.red .watermark {
		color: var(--plate-spot);
	}

	.face {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		text-align: center;
	}

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

	.marked {
		position: absolute;
		bottom: 3%;
		left: 4%;
		width: 28%;
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
		pointer-events: none;
	}
</style>
