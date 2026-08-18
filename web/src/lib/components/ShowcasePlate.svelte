<!--
	The home page hero: one screen, printed in three fields.

	The plate is the site talking. It is the blue ground the whole hero is printed on, and the name is
	stamped straight onto it. Lying on that plate are two sheets of paper. The slate, on the opposite
	theme's paper, carries the day's samples. The answer, on the reader's own paper, carries the one
	that is up. Printed ground, opposite paper, the reader's paper: that is the whole composition, and
	it is why the screen is three colours rather than one.

	Everything the site is sure of is printed and everything the reader is asking is drawn. The drawn
	part is the wet-erase X over the sample they picked and the line they set across the answer.

	None of this predicts. The samples are drawn once a day by a job and read off a file, so arriving
	here costs the server no forward pass at all, and every reader of the same day sees the same set.
	See python/src/nba_ml/showcase.py.

	Left alone, the samples come up one after another on a timer, so a reader who touches nothing
	still sees the site answer several different questions. Picking one settles it there for the
	visit, focus resting anywhere in the hero holds it where it is, and reduced motion never starts
	it, which is the standing way to turn it off.

	The hero is exactly one screen tall at every size, so the page under it is always one scroll away.
	That is what decides the slate: a phone screen cannot hold the samples and a readable answer at
	once, so it is given the answer alone and the samples come round to it on the turn.
-->
<script lang="ts">
	import { prefersReducedMotion } from 'svelte/motion';

	import DistributionChart from '$lib/components/DistributionChart.svelte';
	import LineControl from '$lib/components/LineControl.svelte';
	import OddsReadout from '$lib/components/OddsReadout.svelte';
	import PencilMark from '$lib/components/PencilMark.svelte';
	import { MODELS_PATH, predictsPhrase, sentenceCase } from '$lib/models';
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
	import { READING_PATH, SITE_DESCRIPTION, SITE_NAME } from '$lib/site';

	import type { Answer } from '$lib/odds';
	import type { ShowcaseSample } from '$lib/types';

	type Props = {
		/** The day's samples, already checked and already short of any game that has been played. */
		samples: ShowcaseSample[];
		/**
		 * The day a set that is not this one's was drawn for, as YYYY-MM-DD.
		 *
		 * Null while the set on hand is today's own, which is every ordinary day. A set the job has
		 * not rebuilt is still worth drawing while its games are ahead, and the hero names the
		 * morning it came from rather than claiming this one.
		 */
		heldOver?: string | null;
		/** False where the prediction service did not answer at all, which is not an empty day. */
		answering?: boolean;
	};

	let { samples, heldOver = null, answering = true }: Props = $props();

	/** How many bars a silhouette draws. Enough to read a shape, few enough to stay a mark. */
	const SILHOUETTE_BARS = 24;

	/** How long a sample stays up before the next comes round. Long enough to read the answer. */
	const TURN = 7000;

	type Card = {
		sample: ShowcaseSample;
		answer: Answer;
		/** The matchup, as a reader reads it: away at home. */
		matchup: string;
		/** Whose number it is. Null for a game statistic, which is nobody's. */
		subject: string | null;
		stat: string;
		heading: string;
		/** The bar heights of the silhouette, as fractions of its tallest. */
		silhouette: number[];
	};

	/**
	 * Bar heights as fractions of the tallest, which is what makes a silhouette a shape rather than a
	 * scale. Both kinds of answer are drawn this way, so a sample is read the same whichever it holds.
	 */
	const silhouetteOf = (probabilities: number[]): number[] => {
		const tallest = Math.max(...probabilities, 0);

		if (tallest <= 0) return [];

		// Thinned by taking every nth outcome rather than by summing runs of them, because this is a
		// shape to recognise the answer by and not a figure anything is read off.
		const step = Math.max(Math.ceil(probabilities.length / SILHOUETTE_BARS), 1);

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

				// A game statistic names no side, so it has no subject at all and the statistic is what
				// the sample is called. Everything else was asked about somebody.
				const subject = sample.player?.name ?? sample.team?.name ?? null;

				return {
					sample,
					answer,
					matchup: `${away_team.abbreviation} at ${home_team.abbreviation}`,
					subject,
					stat,
					heading: subject ? `${subject}, ${stat}` : sentenceCase(stat),
					silhouette: silhouetteOf(
						answer.kind === 'integer_distribution'
							? outcomes(answer.distribution).map(({ probability }) => probability)
							: answer.categories.probabilities
					)
				};
			})
			.filter((card): card is Card => card !== null)
	);

	/** Which sample is up as the answer. The first one until the turn or the reader moves it. */
	let chosen = $state(0);

	/** True once the reader has picked a sample themselves, which ends the turn for the visit. */
	let settled = $state(false);

	/** True while focus is resting somewhere in the hero, which holds the turn where it is. */
	let held = $state(false);

	/** Focus moving from one control in the hero to another is still focus in the hero. */
	function releaseTurn(event: FocusEvent & { currentTarget: HTMLElement }) {
		held = event.currentTarget.contains(event.relatedTarget as Node | null);
	}

	/**
	 * Where the reader dragged the line to, cleared whenever a different sample comes up.
	 *
	 * A line belongs to the answer it was set against, so carrying one across to a different
	 * statistic would open the next sample on a number nobody chose for it. Cleared where the sample
	 * changes rather than watched for afterwards, so the new answer is never drawn, even for one
	 * frame, split at the line the last one was asking about.
	 */
	let dragged = $state<number | null>(null);

	// Held inside what there is to pick from, so a set that came back shorter than the last one still
	// has exactly one sample marked rather than an answer up with nothing on the slate.
	const picked = $derived(cards.length === 0 ? -1 : Math.min(chosen, cards.length - 1));

	const card = $derived(cards[picked] ?? null);

	/**
	 * The samples come round on their own until the reader takes over.
	 *
	 * Reduced motion never starts it, which is the standing way to stop it, and anybody reading one
	 * sample holds it simply by being in the hero. `chosen` is written rather than read here, so the
	 * turn it sets off does not restart the timer that set it.
	 */
	$effect(() => {
		if (settled || held || cards.length < 2 || prefersReducedMotion.current) return;

		const turning = setInterval(() => {
			chosen = (chosen + 1) % cards.length;
			dragged = null;
		}, TURN);

		return () => clearInterval(turning);
	});

	const distribution = $derived(
		card && card.answer.kind === 'integer_distribution' ? card.answer.distribution : null
	);

	/** Where an answer opens: the half number nearest what it expects, inside what it can answer. */
	const opening = $derived(
		distribution
			? Math.min(
					Math.max(defaultLine(expectedValue(distribution)), lowestValue(distribution)),
					highestValue(distribution)
				)
			: 0
	);

	const line = $derived(dragged ?? opening);

	/**
	 * What a reader who cannot see the swap is told, and only for a sample they picked themselves.
	 *
	 * One arriving on the turn is not announced. Nobody asked for it, and a live region firing every
	 * few seconds is noise rather than news.
	 */
	let announced = $state('');

	function pick(index: number) {
		chosen = index;
		dragged = null;
		settled = true;
		announced = cards[index] ? `${cards[index].heading}. ${cards[index].matchup}.` : '';
	}

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

	/** A sample in one line, which is what a narrow screen printing it as a mark alone is named by. */
	const named = (entry: Card) => `${entry.heading}. ${entry.matchup}.`;

	/*
	 * Built once, and pinned to one language and to UTC.
	 *
	 * A game date is a plain calendar day rather than a moment, so reading it in the reader's own zone
	 * would move a late game to the day before. Pinned to one language because the server and the
	 * browser both render these words into the same paragraph, and two locales there would have the
	 * sentence rewrite itself on arrival.
	 */
	const DAY = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
	const COUNT = new Intl.NumberFormat('en-US');

	/** A day as a reader reads it. A date the site cannot read is written as it came, never as an error. */
	const dayOf = (iso: string) => {
		const at = Date.parse(`${iso}T00:00:00Z`);

		return Number.isNaN(at) ? iso : DAY.format(at);
	};
</script>

<!-- Focus landing anywhere in the hero holds the turn, because somebody dragging the line or moving
     across the slate is working on the sample that is up. -->
<section class="band hero" data-hero onfocusin={() => (held = true)} onfocusout={releaseTurn}>
	<!-- The plate's own printing: the crosses a press registers it by, and its number. Neither says
	     anything to a reader. They are what makes the ground read as something printed rather than as
	     a coloured box. -->
	<span class="registration top-start" aria-hidden="true"></span>
	<span class="registration top-end" aria-hidden="true"></span>
	<span class="registration bottom-start" aria-hidden="true"></span>
	<span class="registration bottom-end" aria-hidden="true"></span>
	<span class="plate-number micro" aria-hidden="true">
		BB-{cards.length.toString().padStart(3, '0')}
	</span>

	<div class="page composition">
		<div class="masthead plate">
			<div class="name">
				<h1 class="display">{SITE_NAME}</h1>
				<p class="lede">{SITE_DESCRIPTION}</p>
			</div>

			<!-- The header holds itself away over this screen, so the hero carries the one way out of
			     it that is not the models listed under it. -->
			<a class="masthead-link text-link small" href="/about">About this site</a>
		</div>

		{#if cards.length === 0}
			<!-- Held on the same paper the answer takes, so a day with nothing drawn is the same hero
			     rather than a shorter one. A service that never answered is not the same thing as an
			     empty day, and it is not offered an action it could not carry out either. -->
			<div class="answer empty">
				{#if answering}
					<p class="micro muted">No samples today</p>
					<p>
						Samples are drawn once a day, from games the models can already answer. There are none
						today, which is what an off day looks like.
					</p>
					<a class="button button--lead" href={MODELS_PATH}>See the models</a>
				{:else}
					<p class="micro muted">Nothing to show</p>
					<p>
						The prediction service is not answering, so there are no samples to draw and no model to
						ask. Nothing is lost. It is worth coming back in a few minutes.
					</p>
				{/if}
			</div>
		{:else}
			<div class="slate block">
				<p class="micro label" id="slate-label">
					{heldOver ? `Drawn ${dayOf(heldOver)}` : 'Today'}, {cards.length}
					{cards.length === 1 ? 'sample' : 'samples'}
				</p>

				<ul aria-labelledby="slate-label">
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
									<span class="matchup">{entry.matchup}</span>
									{#if entry.subject}<span class="who small">{entry.subject}</span>{/if}
									<span class="stat micro">{entry.stat}</span>
								</span>

								<!-- The shape of the answer, which is what the sample is picked by. Narrow, it is
								     the whole of the sample, and the drawn mark goes across it either way rather
								     than across the words above it. -->
								<span class="shape" aria-hidden="true">
									{#each entry.silhouette as height, bar (bar)}
										<span class="bar" style="height: {Math.max(height * 100, 3)}%"></span>
									{/each}

									<!-- The one drawn mark on the slate. It is the reader's pick, so it is grease
									     pencil rather than print, and it arrives as though it were sprayed on. -->
									{#if index === picked}
										<PencilMark bleed="var(--space-1)" />
									{/if}
								</span>
							</button>
						</li>
					{/each}
				</ul>
			</div>

			<!-- The reader's own paper, with a real answer lying on it. Everything here is a component a
			     prediction page draws, on the plane it draws it on, so the hero teaches the page it
			     leads to rather than resembling it. -->
			{#if card}
				<div class="answer">
					<!-- The heading carries its own weight. Nothing is set above it: the game, the day and
					     what answered are facts about the answer, so they read under it. -->
					<div class="answer-head">
						<h2 class="type-h2">{card.heading}</h2>
						<p class="small note">
							{card.matchup}, {dayOf(card.sample.game.date)}. The {card.sample.title.toLowerCase()}
							model, built from {COUNT.format(card.sample.past_games)} earlier games.
						</p>
					</div>

					<p class="visually-hidden" role="status">{announced}</p>

					{#if distribution && range && odds}
						<!-- Keyed on the pick, so a new answer is drawn in rather than snapping from the shape
						     of the last one. It is a different model answering a different game, and the draw
						     is what says so. -->
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
						/>

						<OddsReadout {odds} />
					{:else if card.answer.kind === 'category_distribution'}
						<!-- A model answering in named categories has no number line, so there is nothing to
						     draw a line across. It is printed as what it is: a chance per category. -->
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

					<div class="ways">
						<a class="button button--lead" href={MODELS_PATH}>See the models</a>
						<a class="text-link small" href={READING_PATH}>How to read this</a>
					</div>

					<p class="caveat small muted">
						A sample, drawn at random {heldOver ? `on ${dayOf(heldOver)}` : 'this morning'}. A
						prediction is not a promise about one game.
					</p>
				</div>
			{/if}
		{/if}
	</div>
</section>

<style>
	/*
	 * The printed ground, and exactly one screen of it, so whatever the device the page under the
	 * hero is one scroll away. A minimum rather than a height, because a screen too short to hold the
	 * answer should grow rather than cut it off.
	 */
	.hero {
		position: relative;
		display: flex;
		flex-direction: column;
		min-height: 100svh;
		padding-block-end: var(--space-5);
		/* Only what a returning header needs, rather than the room a band gives its own printing. The
		   hero is one screen and every millimetre above the name is a millimetre off the answer. */
		--band-lead: var(--space-3);
		background: var(--plate);
		color: var(--plate-ink);
		overflow: clip;
	}

	/*
	 * The masthead across the top and the two sheets under it. They meet along one edge rather than
	 * standing apart, so the pair reads as one composition laid on the plate and not as two cards
	 * floating on it.
	 */
	.composition {
		display: grid;
		flex: 1;
		grid-template-columns: minmax(0, 1fr);
		grid-template-rows: auto minmax(0, 1fr);
		gap: var(--space-4);
		min-height: 0;
	}

	/*
	 * The plate's own trim marks need a margin to sit in, and a narrow screen has none: the sheets
	 * run to the gutter. So the foot of the plate is printed only where there is room for it.
	 */
	.plate-number,
	.registration.bottom-start,
	.registration.bottom-end {
		display: none;
	}

	.plate-number {
		position: absolute;
		bottom: var(--space-3);
		left: calc(var(--space-3) + var(--registration) + var(--space-3));
		color: var(--plate-rule-strong);
	}

	/* Printed straight onto the plate, so it brings the plate's inks and no ground of its own. */
	.masthead {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--space-2) var(--space-5);
		background: none;
	}

	.name {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	/*
	 * Printed, not drawn. The name is the one thing on this screen the reader is not asking about, so
	 * it belongs to the plate and never to the pencil.
	 *
	 * Set in the interface face at its heaviest rather than in the site's serif, because plate
	 * lettering is stamped and a serif reads as something typeset elsewhere and pasted on. It costs
	 * no fourth font: the interface face is already loaded and already carries this weight.
	 *
	 * Its size is held against the screen's height as well as its width, because the hero is one
	 * screen and a name set by width alone takes the answer's room on a short one.
	 */
	.masthead h1 {
		color: var(--plate-ink);
		font-family: var(--font-ui);
		font-size: clamp(2.5rem, min(10vw, 13svh), 8rem);
		font-weight: 800;
		letter-spacing: -0.035em;
		line-height: 0.86;
		text-transform: uppercase;
		/* Never broken inside a word. A name too long for the screen wraps between its words, and
		   letting it break inside one would cut the mark itself in half. */
		overflow-wrap: normal;
	}

	.lede {
		max-width: 34ch;
		color: var(--plate-ink);
		font-size: var(--type-note);
	}

	.masthead-link {
		color: var(--plate-ink);
	}

	.label {
		color: var(--block-muted);
	}

	/*
	 * The slate: the opposite theme's paper, with the day's samples lying on it. A field of the
	 * composition rather than a container, so it takes the block's plane and none of its shape.
	 * Square, because everything the plate carries is.
	 *
	 * It stands only where the screen has room for it beside a readable answer. Narrow, the answer
	 * takes the whole sheet and the turn is what moves between samples.
	 */
	.slate {
		display: none;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-4);
		border-top: none;
		border-radius: 0;
	}

	/* As many samples across as the sheet has room for, measured against the page, so a set of four
	   and a set of eight both lie on the slate in as few rows as they fit in. */
	.slate ul {
		display: grid;
		flex: 1;
		grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
		gap: var(--space-3);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	/* A sample fills its place on the slate, so the sheet is covered whatever the day's set holds. */
	.slate li {
		display: flex;
		min-width: 0;
	}

	/* The words, then the shape taking whatever the tile has left, so the slate fills its sheet and
	   every silhouette on it is drawn as large as the day's set allows. */
	.game {
		position: relative;
		display: grid;
		grid-template-rows: auto minmax(var(--space-5), 1fr);
		align-items: stretch;
		gap: var(--space-3);
		width: 100%;
		padding: var(--space-3);
		background: none;
		color: var(--block-ink);
		border: 1px solid var(--hairline-block);
		border-radius: 0;
		text-align: start;
		cursor: pointer;
		transition: border-color var(--motion-fast) var(--ease-in);
	}

	.game:hover,
	.game.picked {
		border-color: var(--block-ink);
	}

	.words {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.matchup {
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.stat {
		color: var(--block-muted);
	}

	/* The shape of the answer, and the room the words leave, which is where the reader's mark goes.
	   Sharp edges, like every bar on this site. */
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
	}

	.game.picked .bar {
		background: var(--block-ink);
	}

	/*
	 * The answer, on the reader's own paper. It is the page plane, so the chart, the handle and the
	 * three figures are drawn exactly as a prediction page draws them, in the over, under and push
	 * colours the whole site reads a distribution in.
	 */
	.answer {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		min-height: 0;
		padding: var(--space-3);
		background: var(--page);
		color: var(--ink);
		/* The drawing takes whatever the screen has left once everything around it is set. */
		--chart-height: 100%;
	}

	.empty {
		align-items: flex-start;
		justify-content: center;
		gap: var(--space-4);
	}

	.answer-head {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	/* A heading here is a person's whole name and everything the model answers about them, so it runs
	   to two or three lines often enough that where those lines break is part of the setting. */
	.answer-head h2 {
		overflow-wrap: break-word;
		text-wrap: balance;
	}

	.note {
		color: var(--ink-muted);
	}

	/* What the screen has left, between a floor the shape stays readable at and a ceiling past which
	   a sample is drawn larger than a sample needs to be. */
	.plot {
		display: flex;
		flex: 1 1 auto;
		flex-direction: column;
		min-width: 0;
		min-height: 7.5rem;
		max-height: 26rem;
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

	/* The one action of the screen, held at the foot of the sheet whatever height the drawing above
	   it settles at, so it is in the same place on every device. */
	.ways {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-4);
		margin-block-start: auto;
	}

	.caveat {
		max-width: var(--measure);
	}

	/*
	 * Wider: the masthead takes the top and the two sheets stand side by side under it, meeting on
	 * one edge and running to the bottom of the screen. This is where the slate stands, because it is
	 * where the screen has room for the samples and a readable answer at once.
	 */
	@media (min-width: 64rem) {
		.composition {
			grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
			grid-template-rows: auto minmax(0, 1fr);
			gap: var(--space-4) 0;
		}

		.masthead {
			grid-column: 1 / -1;
		}

		.plate-number {
			display: block;
		}

		.registration.bottom-start,
		.registration.bottom-end {
			display: block;
		}

		.slate {
			display: flex;
			grid-column: 1;
		}

		/* Lower than the floor a phone holds, because here the slate beside it decides the height of
		   the row and the drawing has to be able to give way to it. */
		.plot {
			min-height: 6rem;
		}

		.answer {
			grid-column: 2;
			grid-row: 2;
			gap: var(--space-3);
			padding: var(--space-5);
		}

		/* A day with nothing drawn has no slate to stand beside, so what is said instead takes the
		   whole sheet rather than one column of it. */
		.answer.empty {
			grid-column: 1 / -1;
		}
	}
</style>
