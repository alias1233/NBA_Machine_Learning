<!--
	One family's prediction page. See section 11.3.

	Two columns from 64rem up: the upcoming games, the parameter panels and the button on the left,
	and the answer on the right. Below 64rem the
	same order runs down the page with the answer last.

	The form is the reader's pending request and the URL is the answered one. Editing a field or
	choosing a card changes the form, and only the button copies it into the URL, which is what runs a
	prediction. That is why choosing a card never fires a request on its own. R10.10 and R11.10.
-->
<script lang="ts">
	import { afterNavigate, goto, replaceState } from '$app/navigation';
	import { navigating, page } from '$app/state';
	import { prefersReducedMotion } from 'svelte/motion';

	import AdSlot from '$lib/components/AdSlot.svelte';
	import AnswerBlock from '$lib/components/AnswerBlock.svelte';
	import GameCards from '$lib/components/GameCards.svelte';
	import Notice from '$lib/components/Notice.svelte';
	import PlayerPills from '$lib/components/PlayerPills.svelte';
	import PlayerSearch from '$lib/components/PlayerSearch.svelte';
	import { longGameDay } from '$lib/games';
	import { sentenceCase, statPhrase } from '$lib/models';
	import { pageTitle } from '$lib/site';

	import type { Player, Roster, ScheduledGame } from '$lib/types';

	let { data } = $props();

	const TITLE = 'Player game statistics';

	const PHASES = [
		['REGULAR_SEASON', 'Regular season'],
		['PLAYOFFS', 'Playoffs'],
		['PLAY_IN', 'Play-in'],
		['PRESEASON', 'Preseason']
	] as const;

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
		out: data.out,
		joined: data.joined
	});

	let form = $state(seed());
	// svelte-ignore state_referenced_locally
	let rosters = $state<Roster[]>(data.rosters);
	let answerColumn = $state<HTMLElement>();
	let predictButton = $state<HTMLElement>();

	const scrollToPredictButton = (delayInMilli: number = 0): void => {
		const func = (): void => {
			predictButton?.scrollIntoView({
				behavior: prefersReducedMotion.current ? 'auto' : 'smooth',
				block: 'end'
			})
		}
		if (delayInMilli <= 0) {
			func();
		}
		else {
			setTimeout(func, delayInMilli);
		}
	};

	// Bookkeeping, not state: which game the roster list on the page belongs to.
	// svelte-ignore state_referenced_locally
	let rostersFor = data.selectedGame?.id ?? null;

	const selectedGame = $derived(
		data.games.find(
			(game) =>
				game.date === form.date &&
				game.away_team.abbreviation === form.awayTeam &&
				game.home_team.abbreviation === form.homeTeam &&
				game.season_type === form.seasonType
		) ?? null
	);

	// A chosen game switches the picker to its two rosters. Nothing navigates, so the list is
	// fetched rather than loaded. R10.5.
	$effect(() => {
		const game = selectedGame;

		if (game === null) {
			rosters = [];
			rostersFor = null;
			return;
		}

		if (game.id === rostersFor) return;

		rostersFor = game.id;
		let live = true;

		fetch(`/api/rosters?game=${game.id}`)
			.then((response) => (response.ok ? response.json() : []))
			.then((loaded: Roster[]) => {
				if (!live) return;

				rosters = loaded;
				fitToRosters(loaded);
			})
			.catch(() => {});

		return () => {
			live = false;
		};
	});

	/** A player or a roster change left over from another game is dropped, not asked about in this one. */
	function fitToRosters(loaded: Roster[]) {
		const playing = loaded.flatMap((roster) => roster.players);

		if (form.player && !playing.some(({ id }) => id === form.player?.id)) form.player = null;

		form.out = [];
		form.joined = [];

		const url = new URL(location.href);

		url.searchParams.delete('out');
		url.searchParams.delete('joined');
		if (form.player === null) url.searchParams.delete('player');

		if (url.search !== location.search) replaceState(url, page.state);
	}

	const playerTeam = $derived(
		rosters.find((roster) => roster.players.some(({ id }) => id === form.player?.id)) ?? null
	);

	// Only a teammate can be missing from the game, so the Out list is that one team. R10.6.
	const outOptions = $derived(
		(playerTeam?.players ?? []).filter(
			(candidate) =>
				candidate.id !== form.player?.id && !form.out.some(({ id }) => id === candidate.id)
		)
	);

	const predicting = $derived(navigating.to?.route.id === '/models/player-stats');

	/** Which parameter is still missing, in at most twelve words. Empty once none are. R11.10. */
	const missing = $derived(
		form.date === '' || form.awayTeam === '' || form.homeTeam === ''
			? 'Pick a game first.'
			: form.awayTeam === form.homeTeam
				? 'A game needs two different teams.'
				: form.player === null
					? 'Pick a player first.'
					: ''
	);

	/** How an answer names itself: the player and the stat, then the game. */
	function describe(player: Player | null, modelName: string, game: typeof data.choice) {
		const named = data.models.find(({ name }) => name === modelName);
		const stat = named ? statPhrase(named.stats) : '';

		return {
			stat,
			heading: `${player?.name ?? ''}, ${stat}`,
			subheading: `${game.awayTeam} at ${game.homeTeam}, ${longGameDay(game.date)}`
		};
	}

	const answered = $derived(describe(data.player, data.model, data.choice));

	// While one is being worked out the block names what was asked for, not the last answer.
	const shown = $derived(
		predicting
			? describe(form.player, form.model, {
					date: form.date,
					homeTeam: form.homeTeam,
					awayTeam: form.awayTeam,
					seasonType: form.seasonType
				})
			: data.prediction
				? answered
				: { stat: '', heading: 'Pick a game and a player.', subheading: '' }
	);

	const customRoster = $derived(data.out.length > 0 || data.joined.length > 0);

	// A new game, player or stat is a new answer, so the block starts from its own line.
	const answerKey = $derived(JSON.stringify([data.choice, data.player?.id, data.model]));

	const announcement = $derived(
		data.prediction && data.player
			? `${data.player.name}. Expected ${data.prediction.expected_value.toFixed(1)} ${answered.stat}.`
			: ''
	);

	/** What the card falls back to where scripting is off: the same request with its game filled in. */
	function gameHref(game: ScheduledGame) {
		const query = new URLSearchParams({
			date: game.date,
			away: game.away_team.abbreviation,
			home: game.home_team.abbreviation,
			type: game.season_type
		});

		if (form.model) query.set('model', form.model);
		if (form.player) query.set('player', String(form.player.id));

		return `?${query}`;
	}

	// The URL is rewritten in place, which runs no load, so the answer beside it keeps standing 
	// until the button asks for a new one. R10.10.
	function chooseGame(game: ScheduledGame) {
		form.date = game.date;
		form.awayTeam = game.away_team.abbreviation;
		form.homeTeam = game.home_team.abbreviation;
		form.seasonType = game.season_type;

		// The live URL, not page.url, because a shallow write does not refresh page.url and the next
		// write would put the old game back.
		const url = new URL(location.href);
		url.searchParams.set('date', game.date);
		url.searchParams.set('away', game.away_team.abbreviation);
		url.searchParams.set('home', game.home_team.abbreviation);
		url.searchParams.set('type', game.season_type);

		replaceState(url, page.state);

		scrollToPredictButton();
	}

	function choosePlayer(player: Player | null) {
		form.player = player;
		form.out = [];

		scrollToPredictButton(50);
	}

	function addOut(event: Event & { currentTarget: HTMLSelectElement }) {
		const chosen = outOptions.find(({ id }) => id === Number(event.currentTarget.value));

		if (chosen) form.out = [...form.out, chosen];

		event.currentTarget.value = '';

		scrollToPredictButton(50);
	}

	function addJoined(player: Player) {
		if (!form.joined.some(({ id }) => id === player.id)) form.joined = [...form.joined, player];

		scrollToPredictButton(50);
	}

	function onPredict({}) {
		answerColumn?.scrollIntoView({
			behavior: prefersReducedMotion.current ? 'auto' : 'smooth',
			block: 'start'
		})
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

		goto(`?${query}`, { noScroll: true, keepFocus: true, invalidateAll: true });
	}

	afterNavigate(({}) => {
		form = seed();
		rosters = data.rosters;
		rostersFor = data.selectedGame?.id ?? null;
	});
</script>

<svelte:head>
	<title>{pageTitle(TITLE)}</title>
	<meta
		name="description"
		content="The chance of every points, rebounds and assists total for an NBA player in one game."
	/>
</svelte:head>

<div class="page page--wide sections">
	<div class="work">
		<h1 class="page-title">{TITLE}</h1>

		{#if data.models.length === 0}
			<!-- With nothing published there is nothing to offer, so the page is this and no more. R11.9. -->
			<Notice>No model is published right now.</Notice>
		{:else}
			<div class="columns">
				<div class="controls sections">
					<section class="games">
						<div class="heading">
							<h2>Upcoming games</h2>
							<a class="small" href="/about#which-games">Why?</a>
						</div>

						{#if data.games.length === 0}
							<Notice>No game can be predicted right now.</Notice>
						{:else}
							<GameCards
								games={data.games}
								selected={selectedGame}
								hrefOf={gameHref}
								onchoose={chooseGame}
							/>
						{/if}
					</section>

					<form method="GET" onsubmit={onSubmit}>
						<div class="panel" role="group" aria-labelledby="game-group">
							<p class="micro muted" id="game-group">Game</p>

							<div class="fields">
								<div class="field">
									<label class="micro" for="date">Date</label>
									<input id="date" type="date" name="date" bind:value={form.date} />
								</div>

								<div class="field">
									<label class="micro" for="phase">Phase</label>
									<select id="phase" name="type" bind:value={form.seasonType}>
										{#each PHASES as [value, label] (value)}
											<option {value}>{label}</option>
										{/each}
									</select>
								</div>

								<div class="field">
									<label class="micro" for="away">Away team</label>
									<select id="away" name="away" bind:value={form.awayTeam}>
										<option value="">Pick a team</option>
										{#each data.teams as team (team.abbreviation)}
											<option value={team.abbreviation}>{team.name}</option>
										{/each}
									</select>
								</div>

								<div class="field">
									<label class="micro" for="home">Home team</label>
									<select id="home" name="home" bind:value={form.homeTeam}>
										<option value="">Pick a team</option>
										{#each data.teams as team (team.abbreviation)}
											<option value={team.abbreviation}>{team.name}</option>
										{/each}
									</select>
								</div>
							</div>
						</div>

						<!-- A chosen game confines the list to its two teams. Without one the whole league
						     is searched. The one field's label is the panel's label. R10.5. -->
						<div class="panel">
							{#if selectedGame}
								<div class="field">
									<label class="micro" for="player">Player</label>
									<select
										id="player"
										name="player"
										value={form.player?.id ?? ''}
										onchange={(event) =>
											choosePlayer(
												rosters
													.flatMap((roster) => roster.players)
													.find(({ id }) => id === Number(event.currentTarget.value)) ?? null
											)}
									>
										<option value="">Pick a player</option>
										{#each rosters as roster (roster.team.abbreviation)}
											<optgroup label={roster.team.name}>
												{#each roster.players as option (option.id)}
													<option value={option.id}>{option.name}</option>
												{/each}
											</optgroup>
										{/each}
									</select>
								</div>
							{:else}
								<PlayerSearch
									id="player"
									label="Player"
									initial={form.player}
									onchoose={choosePlayer}
								/>
								<input type="hidden" name="player" value={form.player?.id ?? ''} />
							{/if}
						</div>

						<div class="panel" role="group" aria-labelledby="prediction-group">
							<p class="micro muted" id="prediction-group">Prediction</p>

							<div class="field">
								<label class="micro" for="model">Stat to predict</label>
								<select id="model" name="model" bind:value={form.model}>
									{#each data.models as option (option.name)}
										<option value={option.name}>{sentenceCase(statPhrase(option.stats))}</option>
									{/each}
								</select>
							</div>
						</div>

						<!-- A roster change takes effect on the next prediction, with the rest of the form.
						     Nothing here fires a request on its own. R10.14. -->
						<div class="panel" role="group" aria-labelledby="roster-group">
							<p class="micro muted" id="roster-group">Roster</p>

							{#if playerTeam === null}
								<p class="small muted">Pick a player first.</p>
							{:else}
								<div class="fields">
									<div class="field">
										<label class="micro" for="out">Out</label>
										<select id="out" onchange={addOut}>
											<option value="">Add a player</option>
											{#each outOptions as candidate (candidate.id)}
												<option value={candidate.id}>{candidate.name}</option>
											{/each}
										</select>
										<p class="small muted">Players on this team who will not play.</p>
										<PlayerPills
											players={form.out}
											name="out"
											onremove={(player) =>
												(form.out = form.out.filter(({ id }) => id !== player.id))}
										/>
									</div>

									<div class="field">
										<PlayerSearch
											id="joined"
											label="New teammates"
											clearOnChoose
											onchoose={addJoined}
										/>
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
									<p class="small muted">No change from the last game.</p>
								{/if}
							{/if}
						</div>

						<div class="submit" bind:this={predictButton}>
							<button class="button" type="submit" disabled={predicting || missing !== ''} onclick={onPredict}>
								{predicting ? 'Predicting' : 'Run prediction'}
							</button>

							{#if missing && !predicting}
								<p class="small muted">{missing}</p>
							{/if}
						</div>
					</form>
				</div>

				<div class="answer" bind:this={answerColumn}>
					{#if data.error && !predicting}
						<Notice tone="error">{data.error}</Notice>
					{:else}
						{#key answerKey}
							<AnswerBlock
								prediction={data.prediction}
								loading={predicting}
								stat={shown.stat}
								heading={shown.heading}
								subheading={shown.subheading}
								openOn={data.line}
								{customRoster}
							/>
						{/key}
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<AdSlot place="modelBelowResult" />
</div>

<p class="visually-hidden" aria-live="polite">{announcement}</p>

<style>
	.work {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.columns,
	.controls {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.games,
	form {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.heading {
		display: flex;
		align-items: center;
		gap: var(--space-4);
	}

	.heading a {
		display: inline-flex;
		align-items: center;
		min-height: var(--tap-target);
	}

	/* The panel's own label sits above the fields it groups. R11.13. */
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
		scroll-margin-bottom: var(--space-2);
	}

	.answer {
		scroll-margin-top: var(--space-7);
	}

	@media (min-width: 40rem) {
		.columns,
		.controls {
			gap: var(--space-7);
		}

		.fields {
			grid-template-columns: 1fr 1fr;
		}
	}

	@media (min-width: 64rem) {
		.columns {
			display: grid;
			grid-template-columns: minmax(0, 1fr) minmax(0, var(--answer-column));
			align-items: start;
			gap: var(--space-6);
		}
	}
</style>
