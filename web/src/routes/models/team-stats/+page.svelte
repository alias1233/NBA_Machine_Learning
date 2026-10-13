<script lang="ts">
	import { tick } from 'svelte';

	import { afterNavigate, replaceState } from '$app/navigation';
	import { navigating, page } from '$app/state';

	import AnswerBlock from '$lib/components/AnswerBlock.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import MatchupHead from '$lib/components/MatchupHead.svelte';
	import PredictionSubmit from '$lib/components/PredictionSubmit.svelte';
	import PredictionPage from '$lib/components/PredictionPage.svelte';
	import RosterControls from '$lib/components/RosterControls.svelte';
	import TeamChoice from '$lib/components/TeamChoice.svelte';
	import UpcomingGames from '$lib/components/UpcomingGames.svelte';
	import { longGameDay } from '$lib/games';
	import { answerSentence, predictsPhrase, sentenceCase } from '$lib/models';
	import { flow } from '$lib/motion';
	import { readAnswer } from '$lib/odds';
	import { askPrediction, gameHref as buildGameHref } from '$lib/predictions';
	import {
		expectedOf,
		fetchRosters,
		joinedParameter,
		outParameter,
		playersOf,
		rosterOf,
		ROSTER_PARAMETER,
		ROSTER_VALUE,
		sidesOf
	} from '$lib/rosters';
	import { walkTo } from '$lib/scroll';

	import type { RosterSide } from '$lib/rosters';
	import type { Roster, ScheduledGame, Team } from '$lib/types';

	let { data } = $props();

	const TITLE = 'Team stat models';
	const PATH = '/models/team-stats';

	/** Initial form values, taken from the request in the URL. */
	const seed = () => ({
		game: data.selectedGame?.id ?? null,
		model: data.model,
		team: data.team,
		rosters: {
			home: { out: data.scenarios.home.out, joined: data.scenarios.home.joined },
			away: { out: data.scenarios.away.out, joined: data.scenarios.away.joined }
		}
	});

	let form = $state(seed());
	// svelte-ignore state_referenced_locally
	let rosters = $state<Roster[]>(data.rosters);
	let shell = $state<{ reveal: (asking?: Promise<unknown>) => void; revealControls: () => void }>();
	let submitButton = $state<HTMLElement>();
	let teamChoice = $state<{ focus: () => void }>();

	// Not reactive. Id of the game the loaded rosters are for.
	// svelte-ignore state_referenced_locally
	let rostersFor = data.selectedGame?.id ?? null;

	/** The game being hovered or focused. */
	let previewed = $state<ScheduledGame | null>(null);

	/** The game selected in the form. */
	const chosen = $derived(data.games.find((game) => game.id === form.game) ?? null);

	/** The two teams in the selected game, away team first. */
	const sides = $derived(chosen === null ? [] : [chosen.away_team, chosen.home_team]);

	/** The same two teams, each with its side of the game. */
	const rosterSides = $derived(sidesOf(chosen));

	/** Fetches both rosters when a game is selected, because selecting a game does not navigate. */
	$effect(() => {
		const game = chosen;

		if (game === null) {
			rosters = [];
			rostersFor = null;
			return;
		}

		if (game.id === rostersFor) return;

		rostersFor = game.id;
		rosters = [];
		clearRosters();

		let live = true;

		fetchRosters(game.id).then((loaded) => {
			if (!live) return;

			rosters = loaded;
			form.rosters = {
				home: expectedOf(rosterOf(loaded, game.home_team.abbreviation)),
				away: expectedOf(rosterOf(loaded, game.away_team.abbreviation))
			};
		});

		return () => {
			live = false;
		};
	});

	/** Clears all roster changes, because a new game has different teams. */
	function clearRosters() {
		form.rosters = { home: { out: [], joined: [] }, away: { out: [], joined: [] } };

		const url = new URL(location.href);

		for (const side of ['home', 'away'] as RosterSide[]) {
			url.searchParams.delete(outParameter(side));
			url.searchParams.delete(joinedParameter(side));
		}

		url.searchParams.delete(ROSTER_PARAMETER);

		if (url.search !== location.search) replaceState(url, page.state);
	}

	const predicting = $derived(navigating.to?.route.id === PATH);

	/** Message for the first missing input. Empty when nothing is missing. */
	const missing = $derived(
		chosen === null ? 'Pick a game first.' : form.team === '' ? 'Pick a team first.' : ''
	);

	/** Builds the headings for a result. The team and the stat, then the game. */
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

	/** Result block contents before any prediction is made. */
	const EMPTY = {
		stat: '',
		heading: 'No answer yet',
		subheading: 'Pick a game and a team, then run the prediction.'
	};

	const shown = $derived(
		predicting ? describe(form.model, form.team, chosen) : data.prediction ? reached : EMPTY
	);

	const answer = $derived(data.prediction ? readAnswer(data.prediction) : null);

	const asked = $derived(
		data.models.find(({ name }) => name === (predicting ? form.model : data.model)) ?? null
	);

	/** Sentence announced to screen readers when a result arrives. */
	const announcement = $derived(
		answer ? `${reached.heading}. ${answerSentence(answer, reached.stat)}` : ''
	);

	const gameHref = (game: ScheduledGame) =>
		buildGameHref(game, { model: form.model, team: form.team });

	async function chooseGame(game: ScheduledGame) {
		shell?.revealControls();

		if (game.id !== form.game) {
			form.game = game.id;
			form.team = '';

			// Uses location.href because replaceState does not update page.url.
			const url = new URL(location.href);
			url.searchParams.set('game', String(game.id));
			url.searchParams.delete('team');
			replaceState(url, page.state);
		}

		await tick();

		teamChoice?.focus();
	}

	function chooseTeam(side: Team) {
		form.team = side.abbreviation;

		walkTo(submitButton, { block: 'end' });
	}

	afterNavigate(({}) => {
		form = seed();
		rosters = data.rosters;
		rostersFor = data.selectedGame?.id ?? null;
	});
</script>

<PredictionPage
	bind:this={shell}
	title={TITLE}
	path={PATH}
	privateDescription="Free machine learning predictions for an NBA team's total points, rebounds, assists and other box score totals for an upcoming game."
	publicDescription="Free predictions for every point, rebound, assist and three-pointer total that an NBA team scores in a game."
	standing="Pick an upcoming game, and one of the two teams playing in that game."
	scored={data.scored}
	hasModels={data.models.length > 0}
	answering={data.health !== null}
	prediction={data.prediction}
	model={data.model}
	hasAnswer={data.prediction !== null || data.error !== null}
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
					<input type="hidden" name="game" value={form.game ?? ''} />

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

				{#if rosters.length > 0}
					<!-- Marks the roster as set by the user, so cleared fields stay cleared. -->
					<input type="hidden" name={ROSTER_PARAMETER} value={ROSTER_VALUE} />
				{/if}

				{#each rosterSides as { side, team } (team.abbreviation)}
					<RosterControls
						id="{side}-roster"
						label={team.name}
						candidates={playersOf(rosters, team.abbreviation)}
						bind:out={form.rosters[side].out}
						bind:joined={form.rosters[side].joined}
						expected={expectedOf(rosterOf(rosters, team.abbreviation))}
						outName={outParameter(side)}
						joinedName={joinedParameter(side)}
						onchange={() => walkTo(submitButton, { block: 'end' })}
					/>
				{/each}
			</div>

			<div class="form-submit" bind:this={submitButton}>
				<PredictionSubmit pending={predicting} {missing} />
			</div>
		</form>
	{/snippet}

	{#snippet result(opening: boolean)}
		<div>
			{#if data.error && !predicting && !opening}
				<Notice tone="error">{data.error}</Notice>
			{:else}
				<AnswerBlock
					answer={opening ? null : answer}
					output={asked?.output ?? null}
					loading={predicting || opening}
					stat={shown.stat}
					heading={shown.heading}
					headingLevel={3}
					subheading={shown.subheading}
					openOn={data.line}
					customRoster={data.customRoster}
					pastGames={data.prediction?.past_games ?? null}
				/>
			{/if}
		</div>
	{/snippet}
</PredictionPage>

<p class="visually-hidden" aria-live="polite">{announcement}</p>
