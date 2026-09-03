<!--
	The home page hero: one screen, printed as a poster.

	The plate is the site talking. Its transparent header names the site, then an answer sheet carries
	the sample that is up. The slate, on the opposite theme's paper, carries the day's set at the foot.

	It reads down in four printed registers. The foot line says what the site does, and it is the
	page's heading, because the sample under it carries a different question every morning. The
	answer is given the whole page column, because a distribution is a drawing and every pixel of
	width is another outcome a reader can tell apart. The one action of the site is stamped in spot
	ink between two printed rules. Then the slate is the day's index rather than the day's answer, so
	it lies under the action rather than over it.

	Everything the site is sure of is printed and everything the reader is asking is drawn. The drawn
	part is the wet-erase X over the sample they picked and the line they set across the answer.

	None of this predicts. The samples are drawn once a day by a job and read off a file, so arriving
	here costs the server no forward pass at all, and every reader of the same day sees the same set.
	See python/src/nba_ml/showcase.py.

	Left alone, the samples come up one after another on a timer, so a reader who touches nothing
	still sees the site answer several different questions. A thin run of spot ink along the top edge
	of the answer says how much of the turn is left, emptying from the right, so nothing on the screen
	changes without the reader having seen it coming. Picking one settles it there for the visit, focus
	resting anywhere in the hero holds it where it is, and reduced motion never starts it, which is the
	standing way to turn it off. The run is drawn only while the turn is actually running, so it never
	claims a change that is not coming.

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

	/** The daily sample order also chooses the printed plate's photograph. */
	const COLLAGE_IMAGES = [
		'basketball_through_hoop.jpg',
		'bizarre_basketball.png',
		'basketball_on_floor.jpg',
		'dunk.jpg',
		'basketball_court.jpg',
		'basketball_court_artistic.jpg'
	];
	const SHOW_COLLAGE = false;

	/** How short a bar of a silhouette may be drawn, as a percentage. Below this it is not a bar. */
	const FLOOR = 3;

	type Card = {
		sample: ShowcaseSample;
		answer: Answer;
		/** The matchup, as a reader reads it: away at home. */
		matchup: string;
		/** Whose number it is. Null for a game statistic, which is nobody's. */
		subject: string | null;
		stat: string;
		heading: string;
		/** What a sample is called on the slate, which is whose number it is or else the statistic. */
		who: string;
		/** What it answers and which game, in that order, so a narrow tile gives up the game first. */
		where: string;
		/** The bar heights of the silhouette, as fractions of its tallest. */
		silhouette: number[];
	};

	/**
	 * Bar heights as fractions of the tallest, which is what makes a silhouette a shape rather than a
	 * scale. Both kinds of answer are drawn this way, so a sample is read the same whichever it holds.
	 */
	const silhouetteOf = (probabilities: number[], bars: number): number[] => {
		const tallest = Math.max(...probabilities, 0);

		if (tallest <= 0) return [];

		// Thinned by taking every nth outcome rather than by summing runs of them, because this is a
		// shape to recognize the answer by and not a figure anything is read off.
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

				// A game statistic names no side, so it has no subject at all and the statistic is what
				// the sample is called. Everything else was asked about somebody.
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

		const coming = setInterval(() => {
			chosen = (chosen + 1) % cards.length;
			dragged = null;
		}, TURN);

		return () => clearInterval(coming);
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

	/**
	 * Whether the samples are actually coming round, which is the one thing the indicator may say.
	 *
	 * The same four conditions the timer above runs under, read rather than restated, so a run of ink
	 * along the answer can never promise a change that is not on its way.
	 */
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

	/** A day as a reader reads it. A date the site cannot read is written as it came, never as an error. */
	const dayOf = (iso: string) => {
		const at = Date.parse(`${iso}T00:00:00Z`);

		return Number.isNaN(at) ? iso : DAY.format(at);
	};

	const sampledLabel = $derived(
		(heldOver ? `Sampled predictions from ${dayOf(heldOver)}.` : "Today's sampled predictions.")
	);

	const disclaimer = `Predictions are not betting advice, and are not guaranteed.`;
</script>

<!-- Focus landing anywhere in the hero holds the turn, because somebody dragging the line or moving
     across the slate is working on the sample that is up. -->
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

	<!-- The crosses a press registers the plate by. They say nothing to a reader. They are what makes
	     the ground read as something printed rather than as a coloured box, and the printing keeps
	     inside them, the way an image keeps inside a plate's margin. -->
	<span class="registration top-start" aria-hidden="true"></span>
	<span class="registration top-end" aria-hidden="true"></span>
	<span class="registration bottom-start" aria-hidden="true"></span>
	<span class="registration bottom-end" aria-hidden="true"></span>

	<!-- The one action of the screen, and the most important thing on it. Written once, because a day
	     with no samples leads to exactly the same place as a day with them. The arrow points down
	     because that is where the listing is: the next thing on this page rather than another one.

	     It answers a hand coming toward it, which is the whole of what marks it as the thing to
	     press. The stylesheet draws that from --hand. See .button--lead in app.css. -->
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
			<!-- Held on the same paper the answer takes, so a day with nothing drawn is the same hero
			     rather than a shorter one. A service that never answered is not the same thing as an
			     empty day, and it is not offered an action it could not carry out either. -->
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
			<!-- The reader's own paper, with a real answer lying on it. Everything here is a component a
			     prediction page draws, on the plane it draws it on, so the hero teaches the page it
			     leads to rather than resembling it. -->
			<div class="answer">
				<!-- How much of the turn is left, emptying from the right along the sheet's top edge.
				     Drawn only while the turn is actually running, and keyed on the pick so each turn
				     starts its own run rather than carrying the last one's. -->
				{#if turning}
					{#key picked}
						<span class="turn" aria-hidden="true"><span class="turn-left"></span></span>
					{/key}
				{/if}

				<!-- The heading carries its own weight. Nothing is set above it: the game, the day and
				     what answered are facts about the answer, so they read under it. The three figures
				     stand at the other end of that line, because on a sheet this wide they are what the
				     reader is here for and they roll as the line under the chart is dragged. -->
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
					>
						<a class="text-link small" href={READING_PATH}>How to read this</a>
					</LineControl>
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

				<p class="disclaimer small muted">{disclaimer}</p>
			</div>

			{@render intoModels()}

			<!-- The day's index, at the foot of the plate: every sample as the shape of its own answer,
			     with the reader's X on the one that is up. It lies under the action rather than over it,
			     because the listing is what the screen is for and the set is how a reader changes what
			     it is answering. -->
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

									<!-- The shape of the answer, which is what the sample is picked by, and the
									     room the drawn mark goes in rather than over the words above it. -->
									<span class="shape" aria-hidden="true">
										{#each entry.silhouette as height, bar (bar)}
											<span
												class="bar"
												style="height: {Math.max(height * 100, FLOOR)}%"
												style:--bar={bar}
											></span>
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
			</div>
		{/if}
	</div>
</section>

<style>
	/*
	 * The printed ground, and exactly one screen of it, so whatever the device the page under the
	 * hero is one scroll away. Its photograph is the older collage treatment, held under enough blue
	 * ink for the plate lettering to keep its contrast. A minimum rather than a height, because a
	 * screen too short to hold the answer should grow rather than cut it off.
	 *
	 * A phone's browser bars change the dynamic viewport while a reader scrolls. The hero must keep its
	 * printed proportions, so it uses the smallest viewport instead of stretching the chart with them.
	 */
	.hero {
		position: sticky;
		top: 0;
		isolation: isolate;
		display: flex;
		flex-direction: column;
		min-height: 100svh;
		padding-block-end: var(--space-3);
		/* Only the room the header needs. The hero is one screen, so the answer takes the rest. */
		--band-lead: var(--space-2);
		background: var(--plate-deep);
		color: var(--plate-ink);
		overflow: clip;
	}

	/* Browsers with scroll-driven animation let the plate yield as the page reaches it. Without it,
	   sticky positioning still leaves the Models page free to cover the hero. */
	@supports (animation-timeline: scroll()) {
		@media (prefers-reduced-motion: no-preference) {
			.hero {
				animation: hero-recede linear both;
				animation-timeline: scroll(root);
				animation-range: 0 100svh;
			}
		}
	}

	/* The shared collage treatment, re-inked as a plate so unrelated photographs read as one ground. */
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

	/* Home is a neutral page, so its opening ground is the block plane rather than a tinted photograph. */
	:global(.neutral-page) .hero-artwork {
		display: none;
	}

	/*
	 * Four printed registers down one screen: the plate's foot line, the answer, the action, and the
	 * day's index under it. The answer takes whatever the screen has left, so the
	 * chart is as tall as the device allows and the four never add up to more than a screen.
	 */
	.composition {
		display: grid;
		flex: 1;
		grid-template-columns: minmax(0, 1fr);
		grid-template-rows: auto minmax(0, 1fr) auto auto;
		gap: var(--space-2);
		min-height: 0;
	}

	/*
	 * The page's heading, and the first thing said on the plate under the wordmark.
	 *
	 * Set in the interface face rather than stamped in the plate's own, because it is a sentence and
	 * not a name. Every plate band on the site already reads that way: the stamp says what the page
	 * is and the line under it, set in this face, says what the page answers. This one is that line,
	 * given the heading level because the home page has no other. Stamped, it was the same condensed
	 * face at the same weight as the wordmark directly above it, and the two read as one long mark.
	 *
	 * Set a step under the wordmark at every width, and on the same ramp as it, so the name stays
	 * the larger of the two down to the narrowest screen. The wordmark is what is being said loudly
	 * and this is the sentence under it, which is the order a poster puts them in. It takes the full
	 * plate ink, since the face tells it apart from the wordmark without giving up any weight.
	 */
	.heading {
		color: var(--plate-ink);
		font-family: var(--font-ui);
		font-size: clamp(1rem, 0.85rem + 0.75vw, 1.5rem);
		font-weight: 400;
		letter-spacing: -0.02em;
		line-height: 1.15;
		text-wrap: balance;
	}

	/* The heading is printed on the separating rule rather than in the stronger one, which is a box
	   a figure sits in and carries a meaning of its own. */
	.colophon {
		padding-block-start: var(--space-2);
		background: none;
		border-top: var(--rule-plate);
	}

	/*
	 * The answer, on the reader's own paper, given the whole page column. It is the page plane, so the
	 * chart, the handle and the three figures are drawn exactly as a prediction page draws them, in
	 * the over, under and push colors the whole site reads a distribution in.
	 */
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
		/* The drawing takes whatever the screen has left once everything around it is set. */
		--chart-height: 100%;
	}

	/*
	 * How much of the turn is left, printed along the top edge of the sheet the answer is on. The
	 * track is the whole turn and the run inside it is what is left of it, emptying from the right,
	 * which is the direction the next sample comes from.
	 *
	 * Spot ink, because the turn is the site's own doing rather than the reader's, and a bar rather
	 * than a figure, because a countdown in numbers on a page nobody asked to wait on is pressure.
	 */
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

	/* A day with nothing drawn is the same hero rather than a shorter one, but a whole screen of empty
	   paper is a void. The sheet takes the height its words need and lies in the middle of the plate,
	   which reads as a note left on the ground rather than as an answer that failed to arrive. */
	.empty {
		align-self: center;
		align-items: flex-start;
		gap: var(--space-3);
	}

	.empty p {
		max-width: var(--measure);
	}

	/* What the answer is of at one end and what it came to at the other, on one line wherever the
	   sheet has room for both. */
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

	/* A heading here is a person's whole name and everything the model answers about them, so it runs
	   to two or three lines often enough that where those lines break is part of the setting. */
	.titles h2 {
		overflow-wrap: break-word;
		text-wrap: balance;
	}

	.note {
		color: var(--ink-muted);
	}

	/* What the sheet has left, down to a floor the shape stays readable at. */
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

	/*
	 * The one action of the site, stamped in spot ink on the plate between two printed rules. It is
	 * the middle of the screen and the whole point of it, so nothing else on the ground competes: the
	 * rules run out to both edges of the column and leave it standing alone in the center.
	 */
	.act {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
		align-items: center;
		gap: var(--space-4);
		background: none;
	}

	/* Drawn in the spot ink the block is stamped in, so the two rules belong to the action rather than
	   separating the screen. The plate's own strong rule is a box a figure is printed inside, and on
	   the home page's stock it is a hairline nobody can see. */
	.act::before,
	.act::after {
		content: '';
		border-top: 1px solid color-mix(in oklab, var(--plane-accent) 45%, transparent);
	}

	/* Narrow, there is no room either side of the block for a rule to run, so the block takes the whole
	   column and the rules that centered it come off. The action leaves room at the lower right for the
	   page edge that meets it there. */
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

		/* The Models folder begins at the lower-left edge of a portrait screen. Keep the hero's action
		   on its clear side, while narrow landscape keeps the balanced layout above. */
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

	/* Down the page, which is where the listing is. It sets off as the block is reached for, so the
	   control says what it does before it is read. */
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

	/*
	 * The slate: the opposite theme's paper, with the day's samples lying on it as a strip at the foot
	 * of the plate. A field of the composition rather than a container, so it takes the block's plane
	 * and none of its shape. Square, because everything the plate carries is.
	 *
	 * It stands only where the screen has room for it under a readable answer. Narrow, the answer takes
	 * the whole sheet and the turn is what moves between samples.
	 */
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

	/* As many samples across as the strip has room for, measured against the page, so a set of four
	   and a set of eight both lie on it in as few rows as they fit in. */
	.slate ul {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
		gap: var(--space-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	/* A sample fills its place on the strip, so the sheet is covered whatever the day's set holds. */
	.slate li {
		display: flex;
		min-width: 0;
	}

	/* The words, then the shape taking whatever the tile has left, so every silhouette on the strip is
	   drawn as large as the day's set allows. */
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

	/* A name is held to one line, because a tile is wide enough for one and a name broken across two
	   is the wrong thing to give the strip's height to. What it answers and which game wrap instead,
	   because cutting the tail off a statistic would leave a sample nobody can tell from another. */
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
		transform-origin: bottom;
	}

	/* The tile the turn is on takes the full ink, and nothing about its shape moves. A silhouette on
	   the slate is the same shape before and after the turn reaches it, so drawing it in would say a
	   value had changed when none had. */
	.game.picked .bar {
		background: var(--block-ink);
	}

	/* The plate prints itself once: its foot line settles, then the sheet and its action arrive. */
	@media (prefers-reduced-motion: no-preference) {
		.heading {
			animation: settle var(--motion-slow) var(--ease-in) 200ms both;
		}

		.colophon {
			animation: settle var(--motion-slow) var(--ease-in) 280ms both;
		}

		/* Laid onto the ink rather than faded up, which is what a sheet of paper landing on a plate
		   does. Both sheets, in the order they are read. */
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

	/* stamp is the site's own impression and lives in app.css, because this action and a landing answer
	   are the same press. */

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

	/* Wider: the sheet has room for both ends of the answer's head line and for the day's index under
	   the action, which is the one thing a narrow screen cannot hold beside a readable answer. */
	@media (min-width: 64rem) {
		.answer {
			gap: var(--space-3);
			padding: var(--space-4) var(--space-5);
		}
	}

	/*
	 * The day's index stands only where the screen has both the width for six samples across and the
	 * height to spare under a readable answer. A short laptop is given the answer alone for the same
	 * reason a phone is: the hero is one screen, and a drawing squeezed to a sliver to make room for
	 * an index of six is the wrong half to keep.
	 */
	@media (min-width: 64rem) and (min-height: 53rem) and (orientation: landscape) {
		/* Keep the action over the chosen sheet and lift the slate as one desktop composition. */
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
