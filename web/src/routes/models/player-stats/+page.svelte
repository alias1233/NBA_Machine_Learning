<script lang="ts">
	import { tick } from 'svelte';

	import { afterNavigate, replaceState } from '$app/navigation';
	import { navigating, page } from '$app/state';

	import AnswerBlock from '$lib/components/AnswerBlock.svelte';
	import MatchupHead from '$lib/components/MatchupHead.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PredictionSubmit from '$lib/components/PredictionSubmit.svelte';
	import PlayerSearch from '$lib/components/PlayerSearch.svelte';
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
		expectedAround,
		fetchRosters,
		joinedParameter,
		outParameter,
		playersOf,
		rosterOf,
		ROSTER_PARAMETER,
		ROSTER_VALUE
	} from '$lib/rosters';
	import { phone } from '$lib/screen';
	import { walkTo } from '$lib/scroll';

	import type { Player, Roster, ScheduledGame, Team } from '$lib/types';

	let { data } = $props();

	const TITLE = 'Player stat models';
	const PATH = '/models/player-stats';

	/** Initial form values, taken from the request in the URL. */
	const seed = () => ({
		game: data.selectedGame?.id ?? null,
		model: data.model,
		player: data.player,
		team: data.playerTeam,
		out: data.scenario.out,
		joined: data.scenario.joined
	});

	let form = $state(seed());
	// svelte-ignore state_referenced_locally
	let rosters = $state<Roster[]>(data.rosters);
	let loadingRosters = $state(false);
	let shell = $state<{ reveal: (asking?: Promise<unknown>) => void; revealControls: () => void }>();
	let submitButton = $state<HTMLElement>();
	let teamChoice = $state<{ focus: () => void }>();
	let playerPicker = $state<{ focus: () => void; clear: () => void }>();
	let playerField = $state<HTMLElement>();

	/** The game being hovered or focused. */
	let previewed = $state<ScheduledGame | null>(null);

	// Not reactive. Id of the game the loaded rosters are for, and whether a card selected it.
	// svelte-ignore state_referenced_locally
	let rostersFor = data.selectedGame?.id ?? null;
	let chosenByCard = false;

	/** The game selected in the form. */
	const chosen = $derived(data.games.find((game) => game.id === form.game) ?? null);

	/** The two teams in the selected game, away team first. */
	const sides = $derived(chosen === null ? [] : [chosen.away_team, chosen.home_team]);

	/** Fetches both rosters when a game is selected, because selecting a game does not navigate. */
	$effect(() => {
		const game = chosen;

		if (game === null) {
			rosters = [];
			rostersFor = null;
			loadingRosters = false;
			return;
		}

		if (game.id === rostersFor) return;

		rostersFor = game.id;
		rosters = [];
		loadingRosters = true;
		clearRequest();

		if (chosenByCard) {
			chosenByCard = false;
			teamChoice?.focus();
		}

		let live = true;

		fetchRosters(game.id).then((loaded) => {
			if (!live) return;

			rosters = loaded;
			loadingRosters = false;

			if (form.player !== null) {
				const expected = expectedAround(rosterOf(loaded, form.team), form.player.id);
				form.out = expected.out;
				form.joined = expected.joined;
			}
		});

		return () => {
			live = false;
		};
	});

	/** Clears the inputs that depend on the game or the team. */
	function clearRequest({ keepTeam = false } = {}) {
		if (!keepTeam) form.team = '';

		form.player = null;
		form.out = [];
		form.joined = [];

		const url = new URL(location.href);

		url.searchParams.delete('player');
		url.searchParams.delete(outParameter());
		url.searchParams.delete(joinedParameter());
		url.searchParams.delete(ROSTER_PARAMETER);
		if (!keepTeam) url.searchParams.delete('team');

		if (url.search !== location.search) replaceState(url, page.state);
	}

	/** Players who can be marked out. The player's team, minus the player. */
	const outCandidates = $derived(
		playersOf(rosters, form.team).filter((candidate) => candidate.id !== form.player?.id)
	);

	/** Expected lineup changes for the selected player's team. The player is never listed as out. */
	const expectedRoster = $derived(expectedAround(rosterOf(rosters, form.team), form.player?.id ?? null));

	/** Roster of the selected team. */
	const namedRoster = $derived(
		rosters.find((roster) => roster.team.abbreviation === form.team) ?? null
	);

	const predicting = $derived(navigating.to?.route.id === PATH);

	/** Message for the first missing input. Empty when nothing is missing. */
	const missing = $derived(
		chosen === null
			? 'Pick a game first.'
			: form.team === ''
				? 'Pick a team first.'
				: form.player === null
					? 'Pick a player first.'
					: ''
	);

	/** Builds the headings for a result. The player and the stat, then the game. */
	function describe(player: Player | null, modelName: string, game: ScheduledGame | null) {
		const named = data.models.find(({ name }) => name === modelName);
		const stat = named ? predictsPhrase(named.predicts) : '';

		return {
			stat,
			heading: `${player?.name ?? ''}, ${stat}`,
			subheading: game
				? `${game.away_team.abbreviation} at ${game.home_team.abbreviation}, ${longGameDay(game.date)}`
				: ''
		};
	}

	const reached = $derived(describe(data.player, data.model, data.selectedGame));

	/** Result block contents before any prediction is made. */
	const EMPTY = {
		stat: '',
		heading: 'No answer yet',
		subheading: 'Pick a game, a team and a player, then run the prediction.'
	};

	const shown = $derived(
		predicting ? describe(form.player, form.model, chosen) : data.prediction ? reached : EMPTY
	);

	const answer = $derived(data.prediction ? readAnswer(data.prediction) : null);

	const asked = $derived(
		data.models.find(({ name }) => name === (predicting ? form.model : data.model)) ?? null
	);


	/** Sentence announced to screen readers when a result arrives. */
	const announcement = $derived(
		answer && data.player ? `${data.player.name}. ${answerSentence(answer, reached.stat)}` : ''
	);

	/** Key for the player picker, so it resets when the team or the predicted player changes. */
	const pickerKey = $derived(`${form.team}:${data.player?.id ?? ''}`);

	const gameHref = (game: ScheduledGame) => buildGameHref(game, { model: form.model });

	function chooseGame(game: ScheduledGame) {
		shell?.revealControls();

		if (game.id === form.game) {
			teamChoice?.focus();
			return;
		}

		chosenByCard = true;

		form.game = game.id;

		// Uses location.href because replaceState does not update page.url.
		const url = new URL(location.href);
		url.searchParams.set('game', String(game.id));
		replaceState(url, page.state);
	}

	async function chooseTeam(side: Team) {
		if (side.abbreviation !== form.team) {
			form.team = side.abbreviation;
			clearRequest({ keepTeam: true });

			const url = new URL(location.href);
			url.searchParams.set('team', side.abbreviation);
			replaceState(url, page.state);
		}

		await tick();

		if (phone.current) walkTo(playerField, { block: 'start', always: true });
		else walkTo(submitButton, { block: 'end' });

		playerPicker?.clear();
		playerPicker?.focus();
	}

	function choosePlayer(player: Player) {
		form.player = player;

		const expected = expectedAround(rosterOf(rosters, form.team), player.id);
		form.out = expected.out;
		form.joined = expected.joined;

		walkTo(submitButton, { block: 'end' });
	}

	afterNavigate(({}) => {
		form = seed();
		rosters = data.rosters;
		rostersFor = data.selectedGame?.id ?? null;
		loadingRosters = false;
	});
</script>

<PredictionPage
	bind:this={shell}
	title={TITLE}
	path={PATH}
	privateDescription="Free machine learning predictions for an NBA player's points, rebounds, assists and other box score totals for an upcoming game."
	publicDescription="Free predictions for the points, rebounds, assists and other box score totals an NBA player scores in a game."
	standing="Pick an upcoming game, a team playing in the game, and a player on that team."
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

					{#if form.team !== ''}
						<div bind:this={playerField} transition:flow>
							{#key pickerKey}
								<PlayerSearch
									bind:this={playerPicker}
									id="player"
									label="Player"
									initial={form.player}
									rosters={namedRoster ? [namedRoster] : []}
									{loadingRosters}
									onchoose={choosePlayer}
								/>
							{/key}

							<input type="hidden" name="player" value={form.player?.id ?? ''} />
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

				{#if form.player !== null}
					<!-- Marks the roster as set by the user, so cleared fields stay cleared. -->
					{#if rosters.length > 0}
						<input type="hidden" name={ROSTER_PARAMETER} value={ROSTER_VALUE} />
					{/if}

					<RosterControls
						id="roster"
						label="Roster"
						candidates={outCandidates}
						bind:out={form.out}
						bind:joined={form.joined}
						expected={expectedRoster}
						outName={outParameter()}
						joinedName={joinedParameter()}
						onchange={() => walkTo(submitButton, { block: 'end' })}
					/>
				{/if}
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
