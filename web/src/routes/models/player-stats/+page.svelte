<!--
	The player game statistics page.

	A request names a game and a player, so choosing a card fills the game and leaves the reader in
	the player picker, which is the required next step.

	The form is the reader's pending request and the URL is the answered one. Editing a field or
	choosing a card changes the form, and only the button copies it into the URL, which is what runs
	a prediction. That is why choosing a card never fires a request on its own.
-->
<script lang="ts">
	import { afterNavigate, goto, replaceState } from '$app/navigation';
	import { navigating, page } from '$app/state';

	import AnswerBlock from '$lib/components/AnswerBlock.svelte';
	import GameFields from '$lib/components/GameFields.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PlayerPills from '$lib/components/PlayerPills.svelte';
	import PlayerSearch from '$lib/components/PlayerSearch.svelte';
	import PredictionPage from '$lib/components/PredictionPage.svelte';
	import UpcomingGames from '$lib/components/UpcomingGames.svelte';
	import { longGameDay } from '$lib/games';
	import { answerSentence, predictsPhrase, sentenceCase } from '$lib/models';
	import { flow } from '$lib/motion';
	import { readAnswer } from '$lib/odds';
	import { gameHref as buildGameHref } from '$lib/predictions';
	import { scrollIntoViewIfOffScreen } from '$lib/scroll';

	import type { GameChoice } from '$lib/predictions';
	import type { Player, Roster, ScheduledGame } from '$lib/types';

	let { data } = $props();

	const TITLE = 'Player stat models';
	const ABOUT = '/models/player-stats/about';

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
		player: data.player,
		team: data.playerTeam,
		out: data.out,
		joined: data.joined
	});

	let form = $state(seed());
	// svelte-ignore state_referenced_locally
	let rosters = $state<Roster[]>(data.rosters);
	let loadingRosters = $state(false);
	let shell = $state<{ reveal: () => void }>();
	let submitButton = $state<HTMLElement>();
	let playerPicker = $state<{
		focus: () => void;
		clear: () => void;
	}>();

	// A page loaded with a prediction already in its URL renders with the column open and no
	// animation, because nothing happened there for the motion to mark.
	// svelte-ignore state_referenced_locally
	const answered = data.prediction !== null || data.error !== null;

	// Bookkeeping, not state: which game the roster list on the page belongs to, and whether the
	// reader arrived at that game by choosing a card, which is the one thing that moves focus.
	// svelte-ignore state_referenced_locally
	let rostersFor = data.selectedGame?.id ?? null;
	let chosenByCard = false;

	const selectedGame = $derived(
		data.games.find(
			(game) =>
				game.date === form.date &&
				game.away_team.abbreviation === form.awayTeam &&
				game.home_team.abbreviation === form.homeTeam &&
				game.season_type === form.seasonType
		) ?? null
	);

	/**
	 * A chosen game switches the picker to its two rosters. Nothing navigates, so the list is
	 * fetched rather than loaded.
	 *
	 * The reader is put in the picker straight away rather than when the names land, so choosing a
	 * card is answered by the page at once. The list stands open and pulsing until they arrive.
	 */
	$effect(() => {
		const game = selectedGame;

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
		clearRoster();

		if (chosenByCard) {
			chosenByCard = false;
			playerPicker?.clear();
			playerPicker?.focus();
		}

		let live = true;

		fetch(`/api/rosters?game=${game.id}`)
			.then((response) => (response.ok ? response.json() : []))
			.then((loaded: Roster[]) => {
				if (!live) return;

				rosters = loaded;
			})
			.catch(() => {})
			.finally(() => {
				if (live) loadingRosters = false;
			});

		return () => {
			live = false;
		};
	});

	/**
	 * A teammate of the last game is not a teammate of this one, so changing the game drops both
	 * roster controls. The chosen player goes with them, because a new game usually means a new
	 * player.
	 */
	function clearRoster() {
		form.out = [];
		form.joined = [];
		form.player = null;
		form.team = '';

		const url = new URL(location.href);

		url.searchParams.delete('out');
		url.searchParams.delete('joined');
		url.searchParams.delete('team');

		if (url.search !== location.search) replaceState(url, page.state);
	}

	/** Whether a roster names the chosen player, which is how their team is known without asking. */
	const knownTeam = $derived(
		form.player === null ||
			rosters.some((roster) => roster.players.some(({ id }) => id === form.player?.id))
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

	/** The roster the chosen player is on, taken from the reader's answer when no roster names them. */
	const playerRoster = $derived(
		rosters.find((roster) => roster.players.some(({ id }) => id === form.player?.id)) ??
			rosters.find((roster) => roster.team.abbreviation === form.team) ??
			null
	);

	/**
	 * Who can be sat out. Only a teammate can be missing from the game, so the list is that one team.
	 * Where no roster names the chosen player their team is not known, so both sides are offered.
	 */
	const outGroups = $derived(
		(playerRoster ? [playerRoster] : rosters).map((roster) => ({
			team: roster.team,
			players: roster.players.filter(
				(candidate) =>
					candidate.id !== form.player?.id && !form.out.some(({ id }) => id === candidate.id)
			)
		}))
	);

	const predicting = $derived(navigating.to?.route.id === '/models/player-stats');

	/** Which parameter is still missing, in at most twelve words. Empty once none are. */
	const missing = $derived(
		form.date === '' || form.awayTeam === '' || form.homeTeam === ''
			? 'Pick a game first.'
			: form.awayTeam === form.homeTeam
				? 'A game needs two different teams.'
				: form.player === null
					? 'Pick a player first.'
					: !knownTeam && form.team === ''
						? 'Say which team this player is on.'
						: ''
	);

	/** How an answer names itself: the player and the stat, then the game. */
	function describe(player: Player | null, modelName: string, game: GameChoice) {
		const named = data.models.find(({ name }) => name === modelName);
		const stat = named ? predictsPhrase(named.predicts) : '';

		return {
			stat,
			heading: `${player?.name ?? ''}, ${stat}`,
			subheading: `${game.awayTeam} at ${game.homeTeam}, ${longGameDay(game.date)}`
		};
	}

	const reached = $derived(describe(data.player, data.model, data.choice));

	// While one is being worked out the block names what was asked for, not the last answer. With
	// the column open but the URL naming no answer, it says which parameter would bring one back.
	const shown = $derived(
		predicting
			? describe(form.player, form.model, {
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
	// space an answer will take is reserved before it lands and nothing on the block is left naming
	// the last answer while this one is worked out.
	const asked = $derived(
		data.models.find(({ name }) => name === (predicting ? form.model : data.model)) ?? null
	);

	const customRoster = $derived(data.out.length > 0 || data.joined.length > 0);

	// A new game, player or stat is a new answer, so the block starts from its own line.
	const answerKey = $derived(JSON.stringify([data.choice, data.player?.id, data.model]));

	/** The one sentence an answer is announced with, which is whatever its block leads with. */
	const announcement = $derived(
		answer && data.player ? `${data.player.name}. ${answerSentence(answer, reached.stat)}` : ''
	);

	const gameHref = (game: ScheduledGame) =>
		buildGameHref(game, {
			model: form.model,
			player: form.player ? String(form.player.id) : ''
		});

	// The URL is rewritten in place, which runs no load, so the answer beside it keeps standing
	// until the button asks for a new one.
	function chooseGame(game: ScheduledGame) {
		scrollIntoViewIfOffScreen(submitButton, 'end');

		if (game === selectedGame) {
			playerPicker?.focus();
			return;
		}

		// The roster fetch above picks this up, so the picker is cleared and focused in the same
		// frame the card is chosen rather than when its names arrive.
		chosenByCard = true;

		form.date = game.date;
		form.awayTeam = game.away_team.abbreviation;
		form.homeTeam = game.home_team.abbreviation;
		form.seasonType = game.season_type;

		// The live URL, not page.url, because a shallow write does not refresh page.url and the next
		// write would put back what the last one replaced, including the roster this just cleared.
		const url = new URL(location.href);
		url.searchParams.set('date', game.date);
		url.searchParams.set('away', game.away_team.abbreviation);
		url.searchParams.set('home', game.home_team.abbreviation);
		url.searchParams.set('type', game.season_type);
		replaceState(url, page.state);
	}

	function choosePlayer(player: Player) {
		form.player = player;
		form.out = [];
		form.team = '';

		scrollIntoViewIfOffScreen(submitButton, 'end');
	}

	function addOut(event: Event & { currentTarget: HTMLSelectElement }) {
		const chosen = outGroups
			.flatMap((group) => group.players)
			.find(({ id }) => id === Number(event.currentTarget.value));

		if (chosen) form.out = [...form.out, chosen];

		event.currentTarget.value = '';

		scrollIntoViewIfOffScreen(submitButton, 'end');
	}

	function addJoined(player: Player) {
		if (!form.joined.some(({ id }) => id === player.id)) form.joined = [...form.joined, player];

		scrollIntoViewIfOffScreen(submitButton, 'end');
	}

	/**
	 * Copies the form into the URL, which is what runs a prediction.
	 *
	 * The fields name themselves, so the query is read off the form rather than restated here. A new
	 * answer opens on its own line, so the last one's is not carried over.
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
		rosters = data.rosters;
		rostersFor = data.selectedGame?.id ?? null;
		loadingRosters = false;
	});
</script>

<PredictionPage
	bind:this={shell}
	title={TITLE}
	description="The chance of every points, rebounds and assists total for an NBA player in one game."
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

			<!-- A chosen game opens the list on its two rosters, and typing searches the whole
			     league. Somebody who has just joined a team is on no roster yet, and nothing
			     collected says which side they are on, so they are the one case that is asked. -->
			<div class="panel">
				{#key data.player?.id}
					<PlayerSearch
						bind:this={playerPicker}
						id="player"
						label="Player"
						initial={form.player}
						{rosters}
						{loadingRosters}
						onchoose={choosePlayer}
					/>
				{/key}

				<input type="hidden" name="player" value={form.player?.id ?? ''} />

				{#if !knownTeam && sides.length === 2}
					<div class="field" transition:flow>
						<label class="micro" for="player-team">Team</label>
						<select id="player-team" name="team" bind:value={form.team}>
							<option value="">Pick a team</option>
							{#each sides as side (side.abbreviation)}
								<option value={side.abbreviation}>{side.name}</option>
							{/each}
						</select>
						<p class="small muted">No collected game puts this player on either side.</p>
					</div>
				{/if}
			</div>

			<div class="panel" role="group" aria-labelledby="prediction-group">
				<p class="micro muted" id="prediction-group">Prediction</p>

				<div class="field">
					<label class="micro" for="model">Stat to predict</label>
					<select id="model" name="model" bind:value={form.model}>
						{#each data.models as option (option.name)}
							<option value={option.name}>{sentenceCase(predictsPhrase(option.predicts))}</option>
						{/each}
					</select>
				</div>
			</div>

			<!-- A roster change takes effect on the next prediction, with the rest of the form.
			     Nothing here fires a request on its own. -->
			<div class="panel" role="group" aria-labelledby="roster-group">
				<p class="micro muted" id="roster-group">Roster</p>

				{#if form.player === null}
					<p class="small muted" transition:flow>Pick a player first.</p>
				{:else}
					<div class="fields" transition:flow>
						<div class="field">
							<label class="micro" for="out">Out</label>
							<select id="out" onchange={addOut}>
								<option value="">Add a player</option>
								{#each outGroups as group (group.team.abbreviation)}
									<optgroup label={group.team.name}>
										{#each group.players as candidate (candidate.id)}
											<option value={candidate.id}>{candidate.name}</option>
										{/each}
									</optgroup>
								{/each}
							</select>
							<p class="small muted">Players on this team who will not play.</p>
							<PlayerPills
								players={form.out}
								name="out"
								onremove={(player) => (form.out = form.out.filter(({ id }) => id !== player.id))}
							/>
						</div>

						<div class="field">
							<PlayerSearch id="joined" label="New teammates" clearOnChoose onchoose={addJoined} />
							<p class="small muted">Players who joined this team since its last game.</p>
							<PlayerPills
								players={form.joined}
								name="joined"
								onremove={(player) =>
									(form.joined = form.joined.filter(({ id }) => id !== player.id))}
							/>
						</div>
					</div>

					{#if form.out.length === 0 && form.joined.length === 0}
						<p class="small muted" transition:flow>No change from the last game.</p>
					{/if}
				{/if}
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
						{customRoster}
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

	.fields {
		display: grid;
		gap: var(--space-4);
	}

	.submit {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-2);
		scroll-margin-bottom: var(--space-5);
	}

	@media (min-width: 40rem) {
		.fields {
			grid-template-columns: 1fr 1fr;
		}
	}
</style>
