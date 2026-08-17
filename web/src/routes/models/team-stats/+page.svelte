<!--
	The team statistics page.

	A request names a game and one of its two sides, so choosing a card fills the game and leaves the
	reader in the team field with its two teams shown, which is the one thing left to say.

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
	import { answerSentence, predictsPhrase, sentenceCase } from '$lib/models';
	import { flow } from '$lib/motion';
	import { gameHref as buildGameHref } from '$lib/predictions';
	import { readAnswer } from '$lib/odds';
	import { scrollIntoViewIfOffScreen } from '$lib/scroll';

	import type { GameChoice } from '$lib/predictions';
	import type { ScheduledGame } from '$lib/types';

	let { data } = $props();

	const TITLE = 'Team stat models';
	const ABOUT = '/models/team-stats/about';

	/**
	 * The pending request. It starts as the answered one and is the reader's until the button copies
	 * it back into the URL. afterNavigate re-seeds it whenever a new answer lands.
	 */
	const seed = () => ({
		date: data.choice.date,
		awayTeam: data.choice.awayTeam,
		homeTeam: data.choice.homeTeam,
		seasonType: data.choice.seasonType,
		model: data.model,
		team: data.team
	});

	let form = $state(seed());
	let shell = $state<{ reveal: () => void }>();
	let submitButton = $state<HTMLElement>();
	let teamField = $state<HTMLSelectElement>();

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

	/** The two sides of the described game, named, home first. The only answers to which team. */
	const sides = $derived(
		[form.homeTeam, form.awayTeam]
			.filter((abbreviation) => abbreviation !== '')
			.map((abbreviation) => ({
				abbreviation,
				name: data.teams.find((team) => team.abbreviation === abbreviation)?.name ?? abbreviation
			}))
	);

	const predicting = $derived(navigating.to?.route.id === '/models/team-stats');

	/** Which parameter is still missing, in at most twelve words. Empty once none are. */
	const missing = $derived(
		form.date === '' || form.awayTeam === '' || form.homeTeam === ''
			? 'Pick a game first.'
			: form.awayTeam === form.homeTeam
				? 'A game needs two different teams.'
				: form.team === ''
					? 'Pick a team first.'
					: ''
	);

	/** How an answer names itself: the team and the stat, then the game. */
	function describe(modelName: string, team: string, game: GameChoice) {
		const named = data.models.find(({ name }) => name === modelName);
		const stat = named ? predictsPhrase(named.predicts) : '';
		const fullName = data.teams.find(({ abbreviation }) => abbreviation === team)?.name ?? team;

		return {
			stat,
			heading: `${fullName}, ${stat}`,
			subheading: `${game.awayTeam} at ${game.homeTeam}, ${longGameDay(game.date)}`
		};
	}

	const reached = $derived(describe(data.model, data.team, data.choice));

	// While one is being worked out the block names what was asked for, not the last answer. With the
	// column open but the URL naming no answer, it says which parameter would bring one back.
	const shown = $derived(
		predicting
			? describe(form.model, form.team, {
					date: form.date,
					homeTeam: form.homeTeam,
					awayTeam: form.awayTeam,
					seasonType: form.seasonType
				})
			: data.prediction
				? reached
				: { stat: '', heading: missing, subheading: '' }
	);

	// The loader only offers models the site has a reading for, so this is null while loading and
	// never because an answer arrived in a shape the block cannot draw.
	const answer = $derived(data.prediction ? readAnswer(data.prediction) : null);

	// The shape the block draws. It comes from the chosen model rather than from the answer, so the
	// space an answer will take is reserved before it lands.
	const asked = $derived(
		data.models.find(({ name }) => name === (predicting ? form.model : data.model)) ?? null
	);

	// A new game, team or stat is a new answer, so the block starts from its own line.
	const answerKey = $derived(JSON.stringify([data.choice, data.team, data.model]));

	/** The one sentence an answer is announced with, which is whatever its block leads with. */
	const announcement = $derived(
		answer ? `${reached.heading}. ${answerSentence(answer, reached.stat)}` : ''
	);

	const gameHref = (game: ScheduledGame) =>
		buildGameHref(game, { model: form.model, team: form.team });

	/**
	 * Opens the team field's own list, which is the reveal the player picker gets from a focus.
	 *
	 * A native field only opens when asked, and only while the press that asked for it still counts.
	 * A reader who has moved on in the meantime is left alone, and a browser that cannot open a list
	 * on request leaves the field focused, which is where this started.
	 */
	function revealTeams() {
		if (document.activeElement !== teamField) return;

		try {
			teamField?.showPicker();
		} catch {
			// Nothing to fall back to. The field is focused and the reader opens it themselves.
		}
	}

	// The URL is rewritten in place, which runs no load, so the answer beside it keeps standing until
	// the button asks for a new one.
	function chooseGame(game: ScheduledGame) {
		// The list is opened once the page has stopped moving, because a native one closes the moment
		// it scrolls. The focus below is not, since nothing takes that away.
		scrollIntoViewIfOffScreen(submitButton, 'end').then(revealTeams);

		if (game !== selectedGame) {
			// A new game has two different sides, so whichever was chosen is no longer one of them.
			form.date = game.date;
			form.awayTeam = game.away_team.abbreviation;
			form.homeTeam = game.home_team.abbreviation;
			form.seasonType = game.season_type;
			form.team = '';

			// The live URL, not page.url, because a shallow write does not refresh page.url and the
			// next write would put back what the last one replaced, including the team just cleared.
			const url = new URL(location.href);
			url.searchParams.set('date', game.date);
			url.searchParams.set('away', game.away_team.abbreviation);
			url.searchParams.set('home', game.home_team.abbreviation);
			url.searchParams.set('type', game.season_type);
			url.searchParams.delete('team');
			replaceState(url, page.state);
		}

		// Which side to answer for is the one thing left to say, so the reader is put in it at once.
		teamField?.focus({ preventScroll: true });
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
	description="The chance of every points total an NBA team can score in one game."
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

				<!-- The answer belongs to one side of the game, so the two sides are the only choices
				     and neither is picked for the reader. -->
				<div class="field">
					<label class="micro" for="team">Team</label>
					<select id="team" name="team" bind:this={teamField} bind:value={form.team}>
						<option value="">Pick a team</option>
						{#each sides as side (side.abbreviation)}
							<option value={side.abbreviation}>{side.name}</option>
						{/each}
					</select>
					{#if sides.length < 2}
						<p class="small muted" transition:flow>Pick a game first.</p>
					{/if}
				</div>

				<div class="field">
					<label class="micro" for="model">Stat to predict</label>
					<select id="model" name="model" bind:value={form.model}>
						{#each data.models as option (option.name)}
							<option value={option.name}>{sentenceCase(predictsPhrase(option.predicts))}</option>
						{/each}
					</select>
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
