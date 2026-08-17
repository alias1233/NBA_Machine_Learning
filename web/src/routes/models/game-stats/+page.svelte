<!--
	The game statistics page.

	A request names a game and nothing else, so choosing a card is the whole of it and the reader is
	walked straight to the button.

	A request names no team, so a model whose answer belongs to one side of the game says which side
	that is. The stat control names that team before a prediction and the answer names it beside the
	figure, because the number itself carries nothing to say whose it is.

	The form is the reader's pending request and the URL is the answered one. Editing a field or
	choosing a card changes the form, and only the button copies it into the URL, which is what runs
	a prediction.
-->
<script lang="ts">
	import { afterNavigate, goto, replaceState } from '$app/navigation';
	import { navigating, page } from '$app/state';

	import AnswerBlock from '$lib/components/AnswerBlock.svelte';
	import GameFields from '$lib/components/GameFields.svelte';
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
	import { gameHref as buildGameHref } from '$lib/predictions';
	import { scrollIntoViewIfOffScreen } from '$lib/scroll';

	import type { GameSides } from '$lib/models';
	import type { GameChoice } from '$lib/predictions';
	import type { ScheduledGame } from '$lib/types';

	let { data } = $props();

	const TITLE = 'Game stat models';
	const ABOUT = '/models/game-stats/about';

	/**
	 * The pending request. It starts as the answered one and is the reader's until the button copies
	 * it back into the URL. afterNavigate re-seeds it whenever a new answer lands.
	 */
	const seed = () => ({
		date: data.choice.date,
		awayTeam: data.choice.awayTeam,
		homeTeam: data.choice.homeTeam,
		seasonType: data.choice.seasonType,
		model: data.model
	});

	let form = $state(seed());
	let shell = $state<{ reveal: () => void }>();
	let submitButton = $state<HTMLElement>();

	// A page loaded with a prediction already in its URL renders with the column open and no
	// animation, because nothing happened there for the motion to mark.
	// svelte-ignore state_referenced_locally
	const answered = data.prediction !== null || data.error !== null;

	const selectedGame = $derived(
		data.games.find(
			(game) =>
				game.date === form.date &&
				game.away_team.abbreviation === form.awayTeam &&
				game.home_team.abbreviation === form.homeTeam &&
				game.season_type === form.seasonType
		) ?? null
	);

	const predicting = $derived(navigating.to?.route.id === '/models/game-stats');

	/** Which parameter is still missing, in at most twelve words. Empty once none are. */
	const missing = $derived(
		form.date === '' || form.awayTeam === '' || form.homeTeam === ''
			? 'Pick a game first.'
			: form.awayTeam === form.homeTeam
				? 'A game needs two different teams.'
				: ''
	);

	const teamName = (abbreviation: string) =>
		data.teams.find((team) => team.abbreviation === abbreviation)?.name ?? abbreviation;

	/** The two sides of a described game, named in full. Null until both of them are named. */
	const namedSides = (game: GameChoice): GameSides | null =>
		game.homeTeam === '' || game.awayTeam === ''
			? null
			: { home: teamName(game.homeTeam), away: teamName(game.awayTeam) };

	/**
	 * How an answer names itself: the two teams and the stat, then the day.
	 *
	 * The home team is named first, which is the order that says which way a margin counts. A model
	 * read from one side says so beside its figure, and a category naming a side is named by the team
	 * playing it, because nothing else in a game statistic's answer marks which team it is about.
	 */
	function describe(modelName: string, game: GameChoice) {
		const named = data.models.find(({ name }) => name === modelName) ?? null;
		const stat = named ? predictsPhrase(named.predicts) : '';
		const sides = namedSides(game);

		return {
			stat,
			heading: `${sides ? `${sides.home} vs ${sides.away}` : ''}, ${stat}`,
			subheading: longGameDay(game.date),
			note: figureNote(named, sides),
			categoryNames: namedCategories(named, sides)
		};
	}

	const reached = $derived(describe(data.model, data.choice));

	// While one is being worked out the block names what was asked for, not the last answer. With the
	// column open but the URL naming no answer, it says which parameter would bring one back.
	const shown = $derived(
		predicting
			? describe(form.model, {
					date: form.date,
					homeTeam: form.homeTeam,
					awayTeam: form.awayTeam,
					seasonType: form.seasonType
				})
			: data.prediction
				? reached
				: { stat: '', heading: missing, subheading: '', note: '', categoryNames: null }
	);

	// The loader only offers models the site has a reading for, so this is null while loading and
	// never because an answer arrived in a shape the block cannot draw.
	const answer = $derived(data.prediction ? readAnswer(data.prediction) : null);

	// The shape the block draws. It comes from the chosen model rather than from the answer, so the
	// space an answer will take is reserved before it lands.
	const asked = $derived(
		data.models.find(({ name }) => name === (predicting ? form.model : data.model)) ?? null
	);

	/** Which side the stat in the form is counted from, once the game names both. */
	const countedFrom = $derived.by(() => {
		const side = data.models.find(({ name }) => name === form.model)?.read_from;
		const sides = namedSides(form);

		return side && sides ? { side, team: sides[side] } : null;
	});

	// A new game or stat is a new answer, so the block starts from its own line.
	const answerKey = $derived(JSON.stringify([data.choice, data.model]));

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
		scrollIntoViewIfOffScreen(submitButton, 'end');

		if (game === selectedGame) return;

		form.date = game.date;
		form.awayTeam = game.away_team.abbreviation;
		form.homeTeam = game.home_team.abbreviation;
		form.seasonType = game.season_type;

		// The live URL, not page.url, because a shallow write does not refresh page.url and the next
		// write would put back what the last one replaced.
		const url = new URL(location.href);
		url.searchParams.set('date', game.date);
		url.searchParams.set('away', game.away_team.abbreviation);
		url.searchParams.set('home', game.home_team.abbreviation);
		url.searchParams.set('type', game.season_type);
		replaceState(url, page.state);
	}

	/**
	 * Copies the form into the URL, which is what runs a prediction.
	 *
	 * The fields name themselves, so the query is read off the form rather than restated here.
	 */
	function onSubmit(event: SubmitEvent & { currentTarget: HTMLFormElement }) {
		event.preventDefault();

		const query = new URLSearchParams();

		for (const [key, value] of new FormData(event.currentTarget)) {
			if (value !== '') query.append(key, String(value));
		}

		shell?.reveal();

		goto(`?${query}`, { noScroll: true, keepFocus: true, invalidateAll: true });
	}

	afterNavigate(({}) => {
		form = seed();
	});
</script>

<PredictionPage
	bind:this={shell}
	title={TITLE}
	description="The chance of every winning margin and every points total in one NBA game."
	aboutHref={ABOUT}
	hasModels={data.models.length > 0}
	{answered}
>
	{#snippet controls()}
		<UpcomingGames
			games={data.games}
			selected={selectedGame}
			hrefOf={gameHref}
			onchoose={chooseGame}
		/>

		<form method="GET" onsubmit={onSubmit}>
			<GameFields
				bind:date={form.date}
				bind:seasonType={form.seasonType}
				bind:awayTeam={form.awayTeam}
				bind:homeTeam={form.homeTeam}
				teams={data.teams}
			/>

			<div class="panel" role="group" aria-labelledby="prediction-group">
				<p class="micro muted" id="prediction-group">Prediction</p>

				<div class="field">
					<label class="micro" for="model">Stat to predict</label>
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

			<div class="submit" bind:this={submitButton}>
				<button class="button" type="submit" disabled={predicting || missing !== ''}>
					{predicting ? 'Predicting' : 'Run prediction'}
				</button>

				{#if missing && !predicting}
					<p class="small muted" transition:flow>{missing}</p>
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

<style>
	form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	/* The panel's own label sits above the fields it groups. */
	.panel {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.submit {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-2);
		scroll-margin-bottom: var(--space-5);
	}
</style>
