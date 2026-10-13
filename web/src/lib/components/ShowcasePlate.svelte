<script lang="ts">
	import { prefersReducedMotion } from 'svelte/motion';

	import DistributionChart from '$lib/components/DistributionChart.svelte';
	import LineControl from '$lib/components/LineControl.svelte';
	import OddsReadout from '$lib/components/OddsReadout.svelte';
	import PencilMark from '$lib/components/PencilMark.svelte';
	import { MODELS_PATH, predictsPhrase, sentenceCase } from '$lib/models';
	import { nearHand } from '$lib/motion';
	import {
		calculateOdds,
		chartRange,
		defaultLine,
		expectedValue,
		figureText,
		highestValue,
		lowestValue,
		oddsPercentages,
		outcomes,
		readAnswer,
		sharePercentages
	} from '$lib/odds';

	import type { Answer } from '$lib/odds';
	import type { ShowcaseSample } from '$lib/types';

	import { PUBLIC_SITE_DESCRIPTION, READING_PATH } from '$lib/site';

	type Props = {
		/** Today's samples, already validated and with started games removed. */
		samples: ShowcaseSample[];
		/** Date the samples were built for, as YYYY-MM-DD, when it is not today. Null if they are today's. */
		heldOver?: string | null;
		/** False when the prediction service could not be reached. Different from a day with no samples. */
		answering?: boolean;
	};

	let { samples, heldOver = null, answering = true }: Props = $props();

	/** Maximum number of bars in a silhouette. */
	const SILHOUETTE_BARS = 24;

	/** Milliseconds each sample is shown before the next one. */
	const TURN = 7000;

	/** Hero background images. The index of the shown sample picks which one is used. */
	const COLLAGE_IMAGES = [
		'basketball_through_hoop.jpg',
		'bizarre_basketball.png',
		'basketball_on_floor.jpg',
		'dunk.jpg',
		'basketball_court.jpg',
		'basketball_court_artistic.jpg'
	];
	const SHOW_COLLAGE = false;

	/** Minimum height of a silhouette bar, as a percentage. */
	const FLOOR = 3;

	type Card = {
		sample: ShowcaseSample;
		answer: Answer;
		/** Matchup text, written as away at home. */
		matchup: string;
		/** Player or team the stat belongs to. Null for a game stat. */
		subject: string | null;
		stat: string;
		heading: string;
		/** Main label for the sample in the list. */
		who: string;
		/** Secondary label. The stat and the matchup, or only the matchup for a game stat. */
		where: string;
		/** Bar heights of the silhouette, as fractions of the tallest bar. */
		silhouette: number[];
	};

	const silhouetteOf = (probabilities: number[], bars: number): number[] => {
		const tallest = Math.max(...probabilities, 0);

		if (tallest <= 0) return [];

		const step = Math.max(Math.ceil(probabilities.length / bars), 1);

		return probabilities
			.filter((_, index) => index % step === 0)
			.map((probability) => probability / tallest);
	};

	const cards = $derived(
		samples
			.map((sample): Card | null => {
				const answer = readAnswer({
					model: sample.model,
					output: sample.output,
					values: sample.values,
					past_games: sample.past_games
				});

				if (answer === null) return null;

				const { away_team, home_team } = sample.game;
				const stat = predictsPhrase(sample.predicts);

				const subject = sample.player?.name ?? sample.team?.name ?? null;
				const matchup = `${away_team.abbreviation} at ${home_team.abbreviation}`;
				const shape =
					answer.kind === 'integer_distribution'
						? outcomes(answer.distribution).map(({ probability }) => probability)
						: answer.categories.probabilities;

				return {
					sample,
					answer,
					matchup,
					subject,
					stat,
					heading: subject ? `${subject}, ${stat}` : sentenceCase(stat),
					who: subject ?? sentenceCase(stat),
					where: subject ? `${stat} · ${matchup}` : matchup,
					silhouette: silhouetteOf(shape, SILHOUETTE_BARS),
				};
			})
			.filter((card): card is Card => card !== null)
	);

	/** Index of the sample being shown. */
	let chosen = $state(0);

	/** True once the user picks a sample. Stops the automatic rotation for the rest of the visit. */
	let settled = $state(false);

	/** True while focus is inside the hero. Pauses the rotation. */
	let held = $state(false);

	/** Keeps the rotation paused when focus only moves to another control inside the hero. */
	function releaseTurn(event: FocusEvent & { currentTarget: HTMLElement }) {
		held = event.currentTarget.contains(event.relatedTarget as Node | null);
	}

	/** Line value the user dragged to. Reset when the sample changes. */
	let dragged = $state<number | null>(null);

	const picked = $derived(cards.length === 0 ? -1 : Math.min(chosen, cards.length - 1));

	const card = $derived(cards[picked] ?? null);

	/** Rotates through the samples automatically until the user takes over. */
	$effect(() => {
		if (settled || held || cards.length < 2 || prefersReducedMotion.current) return;

		const coming = setInterval(() => {
			chosen = (chosen + 1) % cards.length;
			dragged = null;
		}, TURN);

		return () => clearInterval(coming);
	});

	const distribution = $derived(
		card && card.answer.kind === 'integer_distribution' ? card.answer.distribution : null
	);

	/** Starting line. The half number nearest the expected value, kept inside the model's range. */
	const opening = $derived(
		distribution
			? Math.min(
					Math.max(defaultLine(expectedValue(distribution)), lowestValue(distribution)),
					highestValue(distribution)
				)
			: 0
	);

	const line = $derived(dragged ?? opening);

	/** Text announced to screen readers. Only set when the user picks a sample. */
	let announced = $state('');

	function pick(index: number) {
		chosen = index;
		dragged = null;
		settled = true;
		announced = cards[index] ? `${cards[index].heading}. ${cards[index].matchup}.` : '';
	}

	/** True while the samples are rotating automatically. */
	const turning = $derived(!settled && !held && cards.length > 1 && !prefersReducedMotion.current);

	const odds = $derived(distribution ? calculateOdds(distribution, line) : null);
	const range = $derived(distribution ? chartRange(distribution, line) : null);

	const summary = $derived.by(() => {
		if (!card || !distribution || !odds) return '';

		const spoken = oddsPercentages(odds);

		return [
			`${card.heading}, ${card.matchup}.`,
			`Expected ${figureText(distribution, expectedValue(distribution))} ${card.stat}.`,
			`Under ${line}, ${spoken.under} percent.`,
			`Push ${line}, ${spoken.push} percent.`,
			`Over ${line}, ${spoken.over} percent.`
		].join(' ');
	});

	/** One-line description of a sample. */
	const named = (entry: Card) => `${entry.heading}. ${entry.matchup}.`;

	// Fixed to UTC and one locale, so a date renders the same on the server and in the browser.
	const DAY = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });

	/** Formats a date for display. */
	const dayOf = (iso: string) => {
		const at = Date.parse(`${iso}T00:00:00Z`);

		return Number.isNaN(at) ? iso : DAY.format(at);
	};

	const sampledLabel = $derived(
		(heldOver ? `Sampled predictions from ${dayOf(heldOver)}.` : "Today's sampled predictions.")
	);

	const disclaimer = `Predictions are not betting advice, and are not guaranteed.`;
</script>

<section
	class="band hero"
	style:--turn-duration="{TURN}ms"
	onfocusin={() => (held = true)}
	onfocusout={releaseTurn}
>
	{#if SHOW_COLLAGE}
		{#if card}
			{#key picked}
				<span
					class="hero-artwork"
					style:--hero-image={`url("/collage/${COLLAGE_IMAGES[picked % COLLAGE_IMAGES.length]}")`}
					aria-hidden="true"
				></span>
			{/key}
		{/if}
	{/if}

	<span class="registration top-start" aria-hidden="true"></span>
	<span class="registration top-end" aria-hidden="true"></span>
	<span class="registration bottom-start" aria-hidden="true"></span>
	<span class="registration bottom-end" aria-hidden="true"></span>

	{#snippet intoModels()}
		<div class="act plate">
			<a class="button button--lead" href={MODELS_PATH} use:nearHand>
				See the models
				<svg class="arrow" viewBox="0 0 24 24" aria-hidden="true">
					<path d="M12 4.5v14M5.5 12.5 12 19l6.5-6.5" />
				</svg>
			</a>
		</div>
	{/snippet}

	<div class="page composition">
		<div class="colophon plate">
			<h1 class="heading">{PUBLIC_SITE_DESCRIPTION}</h1>
		</div>

		{#if cards.length === 0}
			<div class="answer empty">
				{#if answering}
					<p class="micro muted">No samples today</p>
					<p>
						There are no sampled predictions today.
					</p>
				{:else}
					<p class="micro muted">Nothing to show</p>
					<p>
						The prediction service is not answering. There are no samples to draw and no model to
						ask. Come back later.
					</p>
				{/if}
			</div>

			{#if answering}
				{@render intoModels()}
			{/if}
		{:else if card}
			<div class="answer">
				{#if turning}
					{#key picked}
						<span class="turn" aria-hidden="true"><span class="turn-left"></span></span>
					{/key}
				{/if}

				<div class="answer-head">
					<div class="titles">
						<h2 class="type-h2">{card.heading}</h2>
						<p class="small note">
							{card.matchup}, {dayOf(card.sample.game.date)}
						</p>
					</div>

					{#if odds}
						<OddsReadout {odds} large />
					{/if}
				</div>

				<p class="visually-hidden" role="status">{announced}</p>

				{#if distribution && range && odds}
					{#key picked}
						<div class="plot">
							<DistributionChart {distribution} stat={card.stat} {line} {range} {summary} />
						</div>
					{/key}

					<LineControl
						id="hero-line"
						bind:line={() => line, (value) => (dragged = value)}
						{distribution}
						{range}
					>
						<a class="text-link small" href={READING_PATH}>How to read this</a>
					</LineControl>
				{:else if card.answer.kind === 'category_distribution'}
					<dl class="categories">
						{#each card.answer.categories.names as name, index (name)}
							<div>
								<dt class="small">{name}</dt>
								<dd class="figure">
									{sharePercentages(card.answer.categories.probabilities, 1)[index]}%
								</dd>
							</div>
						{/each}
					</dl>
				{/if}

				<p class="disclaimer small muted">{disclaimer}</p>
			</div>

			{@render intoModels()}

			<div class="slate-region">
				<p class="sampled-label small muted">{sampledLabel}</p>
				<div class="slate block">
					<ul aria-label={sampledLabel}>
						{#each cards as entry, index (entry.sample.model + index)}
							<li>
								<button
									type="button"
									class="game"
									class:picked={index === picked}
									aria-label={named(entry)}
									aria-pressed={index === picked}
									onclick={() => pick(index)}
								>
									<span class="words">
										<span class="who">{entry.who}</span>
										<span class="where micro">{entry.where}</span>
									</span>

									<span class="shape" aria-hidden="true">
										{#each entry.silhouette as height, bar (bar)}
											<span
												class="bar"
												style="height: {Math.max(height * 100, FLOOR)}%"
												style:--bar={bar}
											></span>
										{/each}

										{#if index === picked}
											<PencilMark bleed="var(--space-1)" />
										{/if}
									</span>
								</button>
							</li>
						{/each}
					</ul>
				</div>
			</div>
		{/if}
	</div>
</section>

<style>
	/* Exactly one screen tall, using the small viewport height so browser bars do not stretch it. */
	.hero {
		position: sticky;
		top: 0;
		isolation: isolate;
		display: flex;
		flex-direction: column;
		min-height: 100svh;
		padding-block-end: var(--space-3);
		--band-lead: var(--space-2);
		background: var(--plate-deep);
		color: var(--plate-ink);
		overflow: clip;
	}

	@supports (animation-timeline: scroll()) {
		@media (prefers-reduced-motion: no-preference) {
			.hero {
				animation: hero-recede linear both;
				animation-timeline: scroll(root);
				animation-range: 0 100svh;
			}
		}
	}

	.hero-artwork {
		position: absolute;
		z-index: -1;
		inset: 0;
		background-image:
			linear-gradient(
				115deg,
				color-mix(in oklab, var(--plate-deep) 86%, transparent),
				color-mix(in oklab, var(--plate) 74%, transparent)
			),
			var(--hero-image);
		background-position: center;
		background-size: cover;
		background-blend-mode: multiply;
		filter: saturate(0.8) contrast(1.08);
	}

	:global(.neutral-page) .hero-artwork {
		display: none;
	}

	.composition {
		display: grid;
		flex: 1;
		grid-template-columns: minmax(0, 1fr);
		grid-template-rows: auto minmax(0, 1fr) auto auto;
		gap: var(--space-2);
		min-height: 0;
	}

	.heading {
		color: var(--plate-ink);
		font-family: var(--font-ui);
		font-size: clamp(1rem, 0.85rem + 0.75vw, 1.5rem);
		font-weight: 400;
		letter-spacing: -0.02em;
		line-height: 1.15;
		text-wrap: balance;
	}

	.colophon {
		padding-block-start: var(--space-2);
		background: none;
		border-top: var(--rule-plate);
	}

	.answer {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		min-height: 0;
		padding: var(--space-4);
		background: var(--panel);
		color: var(--ink);
		box-shadow: var(--sheet-shadow);
		--chart-height: 100%;
	}

	.turn {
		position: absolute;
		inset: 0 0 auto;
		height: 4px;
		background: color-mix(in oklab, var(--accent) 28%, transparent);
		overflow: clip;
	}

	.turn-left {
		display: block;
		height: 100%;
		background: var(--accent);
		transform-origin: left center;
		animation: empty var(--turn-duration) linear;
	}

	.empty {
		align-self: center;
		align-items: flex-start;
		gap: var(--space-3);
	}

	.empty p {
		max-width: var(--measure);
	}

	.answer-head {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--space-3) var(--space-5);
	}

	.titles {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		min-width: 0;
	}

	.titles h2 {
		overflow-wrap: break-word;
		text-wrap: balance;
	}

	.note {
		color: var(--ink-muted);
	}

	.plot {
		display: flex;
		flex: 1 1 auto;
		flex-direction: column;
		min-width: 0;
		min-height: 5rem;
	}

	.plot > :global(figure) {
		flex: 1;
		min-height: 0;
	}

	.categories {
		display: grid;
		gap: var(--space-2);
		margin: 0;
	}

	.categories > div {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--space-4);
		padding-block: var(--space-1);
		border-bottom: var(--rule);
	}

	.categories dd {
		margin: 0;
	}

	.disclaimer {
		max-width: var(--measure);
	}

	.sampled-label {
		position: absolute;
		inset-block-end: calc(100% + var(--space-1));
		inset-inline-start: 0;
		margin: 0;
		color: var(--plate-ink-muted);
	}

	.act {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
		align-items: center;
		gap: var(--space-4);
		background: none;
	}

	.act::before,
	.act::after {
		content: '';
		border-top: 1px solid color-mix(in oklab, var(--plane-accent) 45%, transparent);
	}

	@media (width < 48rem) {
		.act {
			display: flex;
			padding-inline-end: calc(var(--tap-target) * 4 + var(--space-3));
		}

		.button--lead {
			padding-inline: var(--space-3);
		}

		.act::before,
		.act::after {
			display: none;
		}

		.button--lead {
			flex: 1;
		}

		@media (orientation: portrait) {
			.act {
				padding-inline-start: calc(var(--tap-target) * 4 - var(--space-4));
				padding-inline-end: 0;
			}
		}

		@media (width < 24rem) and (orientation: portrait) {
			.button--lead {
				font-size: 1rem;
				letter-spacing: 0.04em;
			}
		}
	}

	.arrow {
		width: var(--icon);
		height: var(--icon);
		fill: none;
		stroke: currentColor;
		stroke-width: 2.5;
		stroke-linecap: round;
		stroke-linejoin: round;
		translate: 0 calc(var(--registered) * 4px);
	}

	.slate-region {
		position: relative;
		display: none;
		flex-direction: column;
	}

	.slate {
		padding: var(--space-2);
		border-top: none;
		border-radius: 0;
		box-shadow: var(--sheet-shadow);
	}

	.slate ul {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
		gap: var(--space-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.slate li {
		display: flex;
		min-width: 0;
	}

	.game {
		position: relative;
		display: grid;
		grid-template-rows: auto minmax(clamp(1.5rem, 3.5svh, 2.5rem), 1fr);
		align-items: stretch;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-2) var(--space-3);
		background: none;
		color: var(--block-ink);
		border: 1px solid var(--hairline-block);
		border-radius: 0;
		text-align: start;
		cursor: pointer;
		transition:
			border-color var(--motion-fast) var(--ease-in),
			background var(--motion-fast) var(--ease-in);
	}

	.game:hover,
	.game.picked {
		border-color: var(--block-ink);
	}

	.words {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		min-width: 0;
	}

	.who {
		overflow: hidden;
		font-size: var(--type-small);
		font-weight: 600;
		line-height: 1.2;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.where {
		color: var(--block-muted);
		font-variant-numeric: tabular-nums;
	}

	.shape {
		position: relative;
		display: flex;
		align-items: flex-end;
		gap: 1px;
		width: 100%;
	}

	.bar {
		flex: 1;
		min-width: 0;
		background: var(--block-muted);
		transform-origin: bottom;
	}

	.game.picked .bar {
		background: var(--block-ink);
	}

	@media (prefers-reduced-motion: no-preference) {
		.heading {
			animation: settle var(--motion-slow) var(--ease-in) 200ms both;
		}

		.colophon {
			animation: settle var(--motion-slow) var(--ease-in) 280ms both;
		}

		.answer {
			animation: lay 420ms var(--ease-in) 260ms both;
		}

		.slate-region {
			animation: lay 420ms var(--ease-in) 420ms both;
		}

		.act {
			animation: stamp 420ms var(--ease-in) 560ms both;
		}
	}

	/* The stamp keyframes live in app.css. */

	@keyframes settle {
		from {
			opacity: 0;
			translate: 0 var(--space-2);
		}
	}

	@keyframes lay {
		from {
			opacity: 0;
			translate: 0 var(--space-4);
		}
	}

	@keyframes empty {
		to {
			scale: 0 1;
		}
	}

	@media (min-width: 64rem) {
		.answer {
			gap: var(--space-3);
			padding: var(--space-4) var(--space-5);
		}
	}

	@media (min-width: 64rem) and (min-height: 53rem) and (orientation: landscape) {
		.hero {
			padding-block-end: calc(var(--space-3) + var(--space-6));
		}

		.act {
			margin-block-start: calc(var(--space-6) * -1);
		}

		.slate-region {
			display: flex;
		}
	}
</style>
