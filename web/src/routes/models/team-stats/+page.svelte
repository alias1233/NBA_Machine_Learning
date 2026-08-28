<!--
	The team statistics page.

	A request names one of the games on the board and one of its two sides, so choosing a card fills
	the game and puts the reader on its two sides, which is the one thing left to say. The two sides
	are printed as the choice itself rather than folded into a list, because a game has exactly two
	of them and a list that has to be opened is a control standing in front of a choice that fits.

	Both teams' rosters are the reader's to change, not only the named team's. A team's row carries
	what the side it faces has available, so a defense missing its best player changes what the named
	team is expected to do. Each side opens already filled in with who is expected to take the floor,
	so a reader who changes nothing is still answered about the game that will actually be played.

	Nothing is asked before it can be answered. Which side to predict means nothing without a game, so
	it arrives with one, and so do the two rosters.

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
	const INFO = '/models/team-stats/info';

	/**
	 * The pending request. It starts as the answered one and is the reader's until the button copies
	 * it back into the URL. afterNavigate re-seeds it whenever a new answer lands.
	 */
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

	// Bookkeeping, not state: which game the player lists on the page belong to.
	// svelte-ignore state_referenced_locally
	let rostersFor = data.selectedGame?.id ?? null;

	/** The card under the reader's pointer, which the head above the fields writes out in full. */
	let previewed = $state<ScheduledGame | null>(null);

	/** The game the form names, which is the one card standing lifted off the board. */
	const chosen = $derived(data.games.find((game) => game.id === form.game) ?? null);

	/** The two sides of the chosen game, away first, which is the order the board deals them. */
	const sides = $derived(chosen === null ? [] : [chosen.away_team, chosen.home_team]);

	/** The same two, each knowing which side of the game it is, which names its roster parameters. */
	const rosterSides = $derived(sidesOf(chosen));

	/**
	 * A chosen game brings both rosters with it. Nothing navigates, so they are fetched rather than
	 * loaded, and the Out list of each side opens on the players it just brought.
	 */
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
			// A roster arrives with the lineup its side expects, and the fields open on that, exactly
			// as they would on a name the reader had chosen.
			form.rosters = {
				home: expectedOf(rosterOf(loaded, game.home_team.abbreviation)),
				away: expectedOf(rosterOf(loaded, game.away_team.abbreviation))
			};
		});

		return () => {
			live = false;
		};
	});

	/**
	 * Every roster change, dropped. A new game has two different sides, so none of it still stands,
	 * and the lineups it expects are not known until its rosters arrive.
	 *
	 * The mark saying the roster is the reader's own goes with them. Without that, the new game
	 * would open on empty fields rather than on who is expected to play in it.
	 */
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
		rosters = data.rosters;
		rostersFor = data.selectedGame?.id ?? null;
	});
</script>

<PredictionPage
	bind:this={shell}
	title={TITLE}
	privateDescription="Free machine learning predictions for an NBA team's total points, rebounds, assists and other box score totals for an upcoming game."
	publicDescription="Predictions for every point, rebound, assist and three-pointer total that an NBA team scores in a game."
	standing={[
		`Pick an upcoming game and one of the two teams in it, and a model predicts what that team
		records over the whole game: its points, its rebounds, its assists or its three-pointers.`,
		`An answer is a chance for every total the team could reach rather than one number, so it also
		gives the over, under and push chance for any line drawn across it. Each model reads both
		teams' recent games and who each side is expected to have available, so a team missing a
		starter is not read as the team that played last week.`
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

				<!-- The one thing the schedule does not decide. Both sides are offered, because one
				     team's row carries what the other has available, so either roster changes the
				     answer. A change takes effect on the next prediction, with the rest of the form. -->
				{#if rosters.length > 0}
					<!-- The mark that says both lists are the reader's own rather than the ones the page
					     suggested. Without it a reader who cleared every name would be answered with the
					     suggestions back, because an empty field submits nothing to tell them apart.

					     It waits for the rosters, because until they land the fields are empty for want of
					     an answer rather than by choice, and a prediction asked for in that moment should
					     be the expected one. -->
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
