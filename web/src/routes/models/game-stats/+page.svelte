<!--
	The game statistics page.

	A request names one of the games on the board, so choosing a card is most of it and the reader is
	walked straight to the button. What the schedule does not decide is who is playing, so both teams'
	rosters arrive with the game, already filled in with who is expected to take the floor, and stay
	the reader's to change. A game statistic is decided by both sides, so either roster changes the
	answer.

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
	import PredictionSubmit from '$lib/components/PredictionSubmit.svelte';
	import PredictionPage from '$lib/components/PredictionPage.svelte';
	import RosterControls from '$lib/components/RosterControls.svelte';
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

	import type { GameSides } from '$lib/models';
	import type { RosterSide } from '$lib/rosters';
	import type { Roster, ScheduledGame } from '$lib/types';

	let { data } = $props();

	const TITLE = 'Game stat models';
	const INFO = '/models/game-stats/info';

	/**
	 * The pending request. It starts as the answered one and is the reader's until the button copies
	 * it back into the URL. afterNavigate re-seeds it whenever a new answer lands.
	 */
	const seed = () => ({
		game: data.selectedGame?.id ?? null,
		model: data.model,
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

	// Bookkeeping, not state: which game the player lists on the page belong to.
	// svelte-ignore state_referenced_locally
	let rostersFor = data.selectedGame?.id ?? null;

	/** The card under the reader's pointer, which the head above the fields writes out in full. */
	let previewed = $state<ScheduledGame | null>(null);

	/** The game the form names, which is the one card standing lifted off the board. */
	const chosen = $derived(data.games.find((game) => game.id === form.game) ?? null);

	/** The two sides of the chosen game, away first, which is the order the board deals them. */
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
		rosters = data.rosters;
		rostersFor = data.selectedGame?.id ?? null;
	});
</script>

<PredictionPage
	bind:this={shell}
	title={TITLE}
	privateDescription="Free machine learning predictions for an upcoming NBA game's outcomes. Supports win percentages, point differentials, total box scores, and more."
	publicDescription="Predictions for the winning team, point differential, and total box score stats of an NBA game."
	standing={[
		`Pick an upcoming game and a model predicts the game itself rather than either side of it: who
		wins, the margin the home team wins or loses by, and the two teams' combined points, rebounds,
		assists or three-pointers.`,
		`An answer is a chance for every outcome rather than one number, so it also gives the over,
		under and push chance for any line drawn across it. Each model reads both teams' recent games
		and who each side is expected to have available, and the winner is its own model rather than
		the positive half of the margin, because that is the more accurate answer.`
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

				<!-- The one thing the schedule does not decide. Both sides are offered, because both
				     teams decide a game statistic. A change takes effect on the next prediction, with
				     the rest of the form, so nothing here fires a request on its own. -->
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
					figureNote={shown.note}
					categoryNames={shown.categoryNames}
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
