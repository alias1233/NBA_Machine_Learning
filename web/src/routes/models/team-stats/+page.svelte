<!--
	The team statistics page.

	A request names one of the games on the board and one of its two sides, so choosing a card fills
	the game and puts the reader on its two sides, which is the one thing left to say. The two sides
	are printed as the choice itself rather than folded into a list, because a game has exactly two
	of them and a list that has to be opened is a control standing in front of a choice that fits.

	Nothing is asked before it can be answered. Which side to predict means nothing without a game, so
	it arrives with one.

	The form is the reader's pending request and the URL is the answered one. Choosing a card or a
	field changes the form, and only the button copies it into the URL, which is what runs a
	prediction.
-->
<script lang="ts">
	import { tick } from 'svelte';

	import { afterNavigate, replaceState } from '$app/navigation';
	import { navigating, page } from '$app/state';

	import AnswerBlock from '$lib/components/AnswerBlock.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import MatchupHead from '$lib/components/MatchupHead.svelte';
	import PredictionPage from '$lib/components/PredictionPage.svelte';
	import TeamChoice from '$lib/components/TeamChoice.svelte';
	import UpcomingGames from '$lib/components/UpcomingGames.svelte';
	import { longGameDay } from '$lib/games';
	import { answerSentence, predictsPhrase, sentenceCase } from '$lib/models';
	import { flow } from '$lib/motion';
	import { readAnswer } from '$lib/odds';
	import { askPrediction, gameHref as buildGameHref } from '$lib/predictions';
	import { walkTo } from '$lib/scroll';

	import type { ScheduledGame, Team } from '$lib/types';

	let { data } = $props();

	const TITLE = 'Team stat models';
	const ABOUT = '/models/team-stats/about';

	/**
	 * The pending request. It starts as the answered one and is the reader's until the button copies
	 * it back into the URL. afterNavigate re-seeds it whenever a new answer lands.
	 */
	const seed = () => ({
		game: data.selectedGame?.id ?? null,
		model: data.model,
		team: data.team
	});

	let form = $state(seed());
	let shell = $state<{ reveal: () => void; revealControls: () => void }>();
	let submitButton = $state<HTMLElement>();
	let teamChoice = $state<{ focus: () => void }>();

	/** The card under the reader's pointer, which the head above the fields writes out in full. */
	let previewed = $state<ScheduledGame | null>(null);

	/** The game the form names, which is the one card standing lifted off the board. */
	const chosen = $derived(data.games.find((game) => game.id === form.game) ?? null);

	/** The two sides of the chosen game, away first, which is the order the board deals them. */
	const sides = $derived(chosen === null ? [] : [chosen.away_team, chosen.home_team]);

	const predicting = $derived(navigating.to?.route.id === '/models/team-stats');

	/** Which parameter is still missing, in at most twelve words. Empty once none are. */
	const missing = $derived(
		chosen === null ? 'Pick a game first.' : form.team === '' ? 'Pick a team first.' : ''
	);

	/** How an answer names itself: the team and the stat, then the game. */
	function describe(modelName: string, team: string, game: ScheduledGame | null) {
		const named = data.models.find(({ name }) => name === modelName);
		const stat = named ? predictsPhrase(named.predicts) : '';
		const playing = game
			? [game.home_team, game.away_team].find(({ abbreviation }) => abbreviation === team)
			: undefined;

		return {
			stat,
			heading: `${playing?.name ?? team}, ${stat}`,
			subheading: game
				? `${game.away_team.abbreviation} at ${game.home_team.abbreviation}, ${longGameDay(game.date)}`
				: ''
		};
	}

	const reached = $derived(describe(data.model, data.team, data.selectedGame));

	/** The block before anything has been asked. It never pretends to be an answer that failed. */
	const EMPTY = {
		stat: '',
		heading: 'No answer yet',
		subheading: 'Pick a game and a team, then run the prediction.'
	};

	// While one is being worked out the block names what was asked for, not the last answer.
	const shown = $derived(
		predicting ? describe(form.model, form.team, chosen) : data.prediction ? reached : EMPTY
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
	const answerKey = $derived(JSON.stringify([data.selectedGame?.id, data.team, data.model]));

	/** The one sentence an answer is announced with, which is whatever its block leads with. */
	const announcement = $derived(
		answer ? `${reached.heading}. ${answerSentence(answer, reached.stat)}` : ''
	);

	const gameHref = (game: ScheduledGame) =>
		buildGameHref(game, { model: form.model, team: form.team });

	// The URL is rewritten in place, which runs no load, so the answer beside it keeps standing until
	// the button asks for a new one.
	async function chooseGame(game: ScheduledGame) {
		// A game is what the whole request is about, so the page is put on the questions it opens
		// rather than on the button at the end of them.
		shell?.revealControls();

		if (game.id !== form.game) {
			// A new game has two different sides, so whichever was chosen is no longer one of them.
			form.game = game.id;
			form.team = '';

			// The live URL, not page.url, because a shallow write does not refresh page.url and the
			// next write would put back what the last one replaced, including the team just cleared.
			const url = new URL(location.href);
			url.searchParams.set('game', String(game.id));
			url.searchParams.delete('team');
			replaceState(url, page.state);
		}

		// The two sides arrive with the game, so they are there to put the reader on only once the page
		// has caught up with the card that opened them.
		await tick();

		// Which side to answer for is the one thing left to say, so the reader is put on it at once.
		teamChoice?.focus();
	}

	function chooseTeam(side: Team) {
		form.team = side.abbreviation;

		walkTo(submitButton, { block: 'end' });
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

					<!-- The answer belongs to one side of the game, so the two sides are the only choices
					     and neither is picked for the reader. With no game there are no sides, so nothing
					     is asked: the line under the button is what says why, and it says it once. -->
					{#if sides.length === 2}
						<div transition:flow>
							<TeamChoice
								bind:this={teamChoice}
								id="team"
								label="Team"
								name="team"
								{sides}
								value={form.team}
								onchoose={chooseTeam}
							/>
						</div>
					{/if}

					<div class="field">
						<label class="micro" for="model">Stat</label>
						<select id="model" name="model" bind:value={form.model}>
							{#each data.models as option (option.name)}
								<option value={option.name}>{sentenceCase(predictsPhrase(option.predicts))}</option>
							{/each}
						</select>
					</div>
				</div>
			</div>

			<div class="form-submit" bind:this={submitButton}>
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
