<!--
	The player game statistics page.

	A request names one of the games on the board, one of its two teams and a player on that team, and
	the reader is asked for them in that order. Nothing that means nothing yet is on the page: which
	team arrives with a game, the player picker arrives with a team, and the roster changes arrive
	with a player. Each answer is what opens the next question, so the form leads rather than waits.

	Asking for the team before the player is what makes the picker readable. One team is fifteen or so
	names, which is a list a reader can see the whole of, where the two rosters of a game stacked into
	one list were thirty of them with the second team's players a scroll below the first.

	The roster is the one thing the schedule does not decide, so it stays the reader's to change: who
	is sitting this game out, and who is playing who did not play the team's last game. It opens
	already filled in from the injury report and the collected rosters, so a reader who changes
	nothing is still answered about the game that will actually be played. Somebody who has just
	joined is on no roster yet, which is what the search in the picker is for, and the list says so
	where a reader looking for a missing name will read it.

	The form is the reader's pending request and the URL is the answered one. Choosing a card or a
	field changes the form, and only the button copies it into the URL, which is what runs a
	prediction. That is why choosing a card never fires a request on its own.
-->
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
	const INFO = '/models/player-stats/info';

	/**
	 * The pending request. It starts as the answered one and is the reader's until the button copies
	 * it back into the URL. afterNavigate re-seeds it whenever a new answer lands.
	 */
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

	/** The card under the reader's pointer, which the head above the fields writes out in full. */
	let previewed = $state<ScheduledGame | null>(null);

	// Bookkeeping, not state: which game the roster list on the page belongs to, and whether the
	// reader arrived at that game by choosing a card, which is the one thing that moves focus.
	// svelte-ignore state_referenced_locally
	let rostersFor = data.selectedGame?.id ?? null;
	let chosenByCard = false;

	/** The game the form names, which is the one card standing lifted off the board. */
	const chosen = $derived(data.games.find((game) => game.id === form.game) ?? null);

	/** The two sides of the chosen game, away first, which is the order the board deals them. */
	const sides = $derived(chosen === null ? [] : [chosen.away_team, chosen.home_team]);

	/**
	 * A chosen game brings its two rosters with it. Nothing navigates, so they are fetched rather
	 * than loaded, and the picker below opens on whichever of the two the reader names.
	 */
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

		// The card is answered by the page in the same frame it is chosen, by putting the reader on
		// the question a game opens, rather than when the names behind it arrive.
		if (chosenByCard) {
			chosenByCard = false;
			teamChoice?.focus();
		}

		let live = true;

		fetchRosters(game.id).then((loaded) => {
			if (!live) return;

			rosters = loaded;
			loadingRosters = false;

			// A player picked out of the league search before the rosters landed has none of the lineup
			// expected around them yet, so it is filled in the moment it arrives.
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

	/**
	 * Everything a game or a team decides, dropped.
	 *
	 * A player belongs to one team of one game, and so does every roster change made around them, so
	 * changing either of those two leaves none of it standing.
	 */
	function clearRequest({ keepTeam = false } = {}) {
		if (!keepTeam) form.team = '';

		form.player = null;
		form.out = [];
		form.joined = [];

		const url = new URL(location.href);

		url.searchParams.delete('player');
		url.searchParams.delete(outParameter());
		url.searchParams.delete(joinedParameter());
		// The mark saying the roster is the reader's own goes with it, or the next player would open
		// on empty fields rather than on who is expected to play around them.
		url.searchParams.delete(ROSTER_PARAMETER);
		if (!keepTeam) url.searchParams.delete('team');

		if (url.search !== location.search) replaceState(url, page.state);
	}

	/** Who can be sat out: the player's own team, less the player themselves. */
	const outCandidates = $derived(
		playersOf(rosters, form.team).filter((candidate) => candidate.id !== form.player?.id)
	);

	/**
	 * The lineup expected around the chosen player, which is what the roster fields open on.
	 *
	 * The player themselves is never in it. A statistic is about somebody taking the floor, so a
	 * suggestion that sits them out is a question with no answer. A reader naming them out by hand is
	 * still answered as they asked.
	 */
	const expectedRoster = $derived(expectedAround(rosterOf(rosters, form.team), form.player?.id ?? null));

	/** The named team's roster, which is who the player picker opens on. */
	const namedRoster = $derived(
		rosters.find((roster) => roster.team.abbreviation === form.team) ?? null
	);

	const predicting = $derived(navigating.to?.route.id === '/models/player-stats');

	/** Which parameter is still missing, in at most twelve words. Empty once none are. */
	const missing = $derived(
		chosen === null
			? 'Pick a game first.'
			: form.team === ''
				? 'Pick a team first.'
				: form.player === null
					? 'Pick a player first.'
					: ''
	);

	/** How an answer names itself: the player and the stat, then the game. */
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

	/** The block before anything has been asked. It never pretends to be an answer that failed. */
	const EMPTY = {
		stat: '',
		heading: 'No answer yet',
		subheading: 'Pick a game, a team and a player, then run the prediction.'
	};

	// While one is being worked out the block names what was asked for, not the last answer.
	const shown = $derived(
		predicting ? describe(form.player, form.model, chosen) : data.prediction ? reached : EMPTY
	);

	// The loader only offers models the site has a reading for, so this is null while loading and
	// never because an answer arrived in a shape the block cannot draw.
	const answer = $derived(data.prediction ? readAnswer(data.prediction) : null);

	// The shape the block draws. It comes from the chosen model rather than from the answer, so the
	// space an answer will take is reserved before it lands and nothing on the block is left naming
	// the last answer while this one is worked out.
	const asked = $derived(
		data.models.find(({ name }) => name === (predicting ? form.model : data.model)) ?? null
	);


	/** The one sentence an answer is announced with, which is whatever its block leads with. */
	const announcement = $derived(
		answer && data.player ? `${data.player.name}. ${answerSentence(answer, reached.stat)}` : ''
	);

	/** What the picker is keyed on, so a new team or a new answer opens it on an empty box. */
	const pickerKey = $derived(`${form.team}:${data.player?.id ?? ''}`);

	// Only the stat survives a change of game. The team and the player belong to the game that was on
	// the board when they were picked.
	const gameHref = (game: ScheduledGame) => buildGameHref(game, { model: form.model });

	// The URL is rewritten in place, which runs no load, so the answer beside it keeps standing
	// until the button asks for a new one.
	function chooseGame(game: ScheduledGame) {
		// A game is what the whole request is about, so the page is put on the questions it opens
		// rather than on the button at the end of them.
		shell?.revealControls();

		if (game.id === form.game) {
			teamChoice?.focus();
			return;
		}

		// The roster effect above picks this up, so the reader is put on the two teams in the same
		// frame the card is chosen rather than when the rosters behind them arrive.
		chosenByCard = true;

		form.game = game.id;

		// The live URL, not page.url, because a shallow write does not refresh page.url and the next
		// write would put back what the last one replaced, including what this just cleared.
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

		// The picker arrives with the team, so it is there to be walked to, emptied and put the reader
		// in only once the page has caught up with the choice that opened it.
		await tick();

		// On a phone the picker and the roster it opens on take the whole screen and the button is a
		// page below them, so the page is put on the picker itself. Its list opens downward, which is
		// why it goes to the top of the screen rather than merely into view. Wider, everything left to
		// answer fits at once, so the reader is walked to the end of the form instead.
		if (phone.current) walkTo(playerField, { block: 'start', always: true });
		else walkTo(submitButton, { block: 'end' });

		playerPicker?.clear();
		playerPicker?.focus();
	}

	function choosePlayer(player: Player) {
		form.player = player;

		// Whatever was in the fields was measured against whoever was chosen before, so the lineup
		// expected around this one takes its place, exactly as it does when a game is chosen.
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
	privateDescription="Free machine learning predictions for an NBA player's points, rebounds, assists and other box score totals for an upcoming game."
	publicDescription="Predictions for the points, rebounds, assists and other box score totals an NBA player scores in a game."
	standing={[
		`Pick an upcoming game, a team playing in it and a player on that team, and a model predicts
		what that player records: points, rebounds, assists, three-pointers, steals, blocks,
		turnovers, four combined totals, and whether the night reaches a double-double or a
		triple-double.`,
		`An answer is a chance for every outcome the statistic can take rather than one number, so it
		also gives the over, under and push chance for any line drawn across it. Each model reads the
		player's run of past games, the game ahead of them, and who is expected to be on the floor for
		both teams, which the roster controls leave you free to change.`
	]}
	infoHref={INFO}
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
				<!-- A team of the chosen game, a player on it, and a statistic. Each of the first two
				     opens the next, so nothing on the page is a question the reader has nothing to
				     answer it with yet. -->
				<div class="field-group flush">
					<!-- The game is whichever card is lifted off the board, so it is carried rather than
					     asked for again. -->
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

					<!-- The picker opens on the named team's roster, and typing searches the whole league
					     instead, which is how somebody who has just joined and is on no roster yet is
					     reached. The list says so itself, where a reader missing a name will read it. -->
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

				<!-- The one thing the schedule does not decide, and the last thing asked, because every
				     name in it is measured against the player above. A roster change takes effect on the
				     next prediction, with the rest of the form, and nothing here fires a request on its
				     own. -->
				{#if form.player !== null}
					<!-- The mark that says both lists are the reader's own rather than the ones the page
					     suggested. Without it a reader who cleared every name would be answered with the
					     suggestions back, because an empty field submits nothing to tell them apart.

					     It waits for the roster, because until it lands the fields are empty for want of an
					     answer rather than by choice, and a prediction asked for in that moment should be
					     the expected one. -->
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
