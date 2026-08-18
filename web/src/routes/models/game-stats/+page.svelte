<!--
	The game statistics page.

	A request names one of the games on the board and nothing else, so choosing a card is the whole of
	it and the reader is walked straight to the button.

	A request names no team, so a model whose answer belongs to one side of the game says which side
	that is. The stat control names that team before a prediction and the answer names it beside the
	figure, because the number itself carries nothing to say whose it is.

	The form is the reader's pending request and the URL is the answered one. Choosing a card or a
	stat changes the form, and only the button copies it into the URL, which is what runs a
	prediction. That is why choosing a card never fires a request on its own.
-->
<script lang="ts">
	import { afterNavigate, replaceState } from '$app/navigation';
	import { navigating, page } from '$app/state';

	import AnswerBlock from '$lib/components/AnswerBlock.svelte';
	import MatchupHead from '$lib/components/MatchupHead.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PredictionPage from '$lib/components/PredictionPage.svelte';
	import UpcomingGames from '$lib/components/UpcomingGames.svelte';
	import { longGameDay } from '$lib/games';
	import {
		answerSentence,
		figureNote,
		namedCategories,
		predictsPhrase,
		sentenceCase
	} from '$lib/models';
	import { flow } from '$lib/motion';
	import { readAnswer } from '$lib/odds';
	import { askPrediction, gameHref as buildGameHref } from '$lib/predictions';

	import type { GameSides } from '$lib/models';
	import type { ScheduledGame } from '$lib/types';

	let { data } = $props();

	const TITLE = 'Game stat models';
	const ABOUT = '/models/game-stats/about';

	/**
	 * The pending request. It starts as the answered one and is the reader's until the button copies
	 * it back into the URL. afterNavigate re-seeds it whenever a new answer lands.
	 */
	const seed = () => ({
		game: data.selectedGame?.id ?? null,
		model: data.model
	});

	let form = $state(seed());
	let shell = $state<{ reveal: () => void; revealControls: () => void }>();

	/** The card under the reader's pointer, which the head above the fields writes out in full. */
	let previewed = $state<ScheduledGame | null>(null);

	/** The game the form names, which is the one card standing lifted off the board. */
	const chosen = $derived(data.games.find((game) => game.id === form.game) ?? null);

	const predicting = $derived(navigating.to?.route.id === '/models/game-stats');

	/** Which parameter is still missing, in at most twelve words. Empty once none are. */
	const missing = $derived(chosen === null ? 'Pick a game first.' : '');

	/** The two sides of a game, named in full. Null before one has been chosen. */
	const namedSides = (game: ScheduledGame | null): GameSides | null =>
		game === null ? null : { home: game.home_team.name, away: game.away_team.name };

	/**
	 * How an answer names itself: the two teams and the stat, then the day.
	 *
	 * The home team is named first, which is the order that says which way a margin counts. A model
	 * read from one side says so beside its figure, and a category naming a side is named by the team
	 * playing it, because nothing else in a game statistic's answer marks which team it is about.
	 */
	function describe(modelName: string, game: ScheduledGame | null) {
		const named = data.models.find(({ name }) => name === modelName) ?? null;
		const stat = named ? predictsPhrase(named.predicts) : '';
		const sides = namedSides(game);

		return {
			stat,
			heading: `${sides ? `${sides.home} vs ${sides.away}` : ''}, ${stat}`,
			subheading: game ? longGameDay(game.date) : '',
			note: figureNote(named, sides),
			categoryNames: namedCategories(named, sides)
		};
	}

	const reached = $derived(describe(data.model, data.selectedGame));

	/** The block before anything has been asked. It never pretends to be an answer that failed. */
	const EMPTY = {
		stat: '',
		heading: 'No answer yet',
		subheading: 'Pick a game, then run the prediction.',
		note: '',
		categoryNames: null
	};

	// While one is being worked out the block names what was asked for, not the last answer.
	const shown = $derived(
		predicting ? describe(form.model, chosen) : data.prediction ? reached : EMPTY
	);

	// The loader only offers models the site has a reading for, so this is null while loading and
	// never because an answer arrived in a shape the block cannot draw.
	const answer = $derived(data.prediction ? readAnswer(data.prediction) : null);

	// The shape the block draws. It comes from the chosen model rather than from the answer, so the
	// space an answer will take is reserved before it lands.
	const asked = $derived(
		data.models.find(({ name }) => name === (predicting ? form.model : data.model)) ?? null
	);

	/** Which side the stat in the form is counted from, once a game has been chosen. */
	const countedFrom = $derived.by(() => {
		const side = data.models.find(({ name }) => name === form.model)?.read_from;
		const sides = namedSides(chosen);

		return side && sides ? { side, team: sides[side] } : null;
	});

	// A new game or stat is a new answer, so the block starts from its own line.
	const answerKey = $derived(JSON.stringify([data.selectedGame?.id, data.model]));

	/**
	 * The one sentence an answer is announced with, which is whatever its block leads with. A figure
	 * belonging to one side is spoken with that side named, as it is drawn.
	 */
	const announcement = $derived.by(() => {
		if (!answer) return '';

		const spoken = answerSentence(answer, reached.note || reached.stat, reached.categoryNames);

		return `${reached.heading}. ${spoken}`;
	});

	const gameHref = (game: ScheduledGame) => buildGameHref(game, { model: form.model });

	// The URL is rewritten in place, which runs no load, so the answer beside it keeps standing until
	// the button asks for a new one.
	function chooseGame(game: ScheduledGame) {
		// A game is what the whole request is about, so the page is put on the questions it opens
		// rather than on the button at the end of them.
		shell?.revealControls();

		if (game.id === form.game) return;

		form.game = game.id;

		// The live URL, not page.url, because a shallow write does not refresh page.url and the next
		// write would put back what the last one replaced.
		const url = new URL(location.href);
		url.searchParams.set('game', String(game.id));
		replaceState(url, page.state);
	}

	afterNavigate(({}) => {
		form = seed();
	});
</script>

<PredictionPage
	bind:this={shell}
	title={TITLE}
	description="The chance of every final margin, every points total, and each team winning one NBA game."
	aboutHref={ABOUT}
	hasModels={data.models.length > 0}
	answering={data.health !== null}
>
	{#snippet board()}
		<UpcomingGames
			games={data.games}
			selected={chosen}
			hrefOf={gameHref}
			onchoose={chooseGame}
			onpreview={(game) => (previewed = game)}
		/>
	{/snippet}

	{#snippet matchup()}
		<MatchupHead game={chosen} {previewed} />
	{/snippet}

	{#snippet controls()}
		<form class="form-stack" method="GET" onsubmit={(event) => askPrediction(event, shell)}>
			<div class="form-groups">
				<div class="field-group flush">
					<!-- The game is whichever card is lifted off the board, so it is carried rather than
					     asked for again. -->
					<input type="hidden" name="game" value={form.game ?? ''} />

					<div class="field">
						<label class="micro" for="model">Stat</label>
						<select id="model" name="model" bind:value={form.model}>
							{#each data.models as option (option.name)}
								<option value={option.name}>{sentenceCase(predictsPhrase(option.predicts))}</option>
							{/each}
						</select>
						<!-- A stat with a direction is counted from one side, and the answer names no team,
						     so the control choosing it says which side that is. -->
						{#if countedFrom}
							<p class="small muted" transition:flow>
								Counted from {countedFrom.team}, the {countedFrom.side} team.
							</p>
						{/if}
					</div>
				</div>
			</div>

			<div class="form-submit">
				<!-- The button carries the reason it is disabled, so it is not left to a line beside it that
				     a screen reader has no reason to reach. -->
				<button
					class="button"
					type="submit"
					disabled={predicting || missing !== ''}
					aria-describedby={missing && !predicting ? 'submit-missing' : undefined}
				>
					{predicting ? 'Predicting' : 'Run a prediction'}
				</button>

				{#if missing && !predicting}
					<p id="submit-missing" class="small muted" transition:flow>{missing}</p>
				{/if}
			</div>
		</form>
	{/snippet}

	{#snippet result()}
		<div>
			{#if data.error && !predicting}
				<Notice tone="error">{data.error}</Notice>
			{:else}
				{#key answerKey}
					<AnswerBlock
						{answer}
						output={asked?.output ?? null}
						loading={predicting}
						stat={shown.stat}
						heading={shown.heading}
						headingLevel={3}
						figureNote={shown.note}
						categoryNames={shown.categoryNames}
						subheading={shown.subheading}
						openOn={data.line}
						customRoster={false}
						pastGames={data.prediction?.past_games ?? null}
					/>
				{/key}
			{/if}
		</div>
	{/snippet}
</PredictionPage>

<p class="visually-hidden" aria-live="polite">{announcement}</p>
