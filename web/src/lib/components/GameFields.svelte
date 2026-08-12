<!--
	The game being asked about, typed out rather than chosen from a card.

	Every family describes a game the same way and under the same four parameter names, so this is one
	panel rather than the same four fields on each page. The names match what `$lib/predictions.ts`
	reads back out of the address bar.
-->
<script lang="ts">
	import { PHASES } from '$lib/predictions';

	import type { SeasonType, Team } from '$lib/types';

	type Props = {
		date: string;
		seasonType: SeasonType;
		awayTeam: string;
		homeTeam: string;
		/** Every team, which is what makes any game describable and not only a scheduled one. */
		teams: Team[];
	};

	let {
		date = $bindable(),
		seasonType = $bindable(),
		awayTeam = $bindable(),
		homeTeam = $bindable(),
		teams
	}: Props = $props();
</script>

<div class="panel" role="group" aria-labelledby="game-group">
	<p class="micro muted" id="game-group">Game</p>

	<div class="fields">
		<div class="field">
			<label class="micro" for="date">Date</label>
			<input id="date" type="date" name="date" bind:value={date} />
		</div>

		<div class="field">
			<label class="micro" for="phase">Phase</label>
			<select id="phase" name="type" bind:value={seasonType}>
				{#each PHASES as [value, label] (value)}
					<option {value}>{label}</option>
				{/each}
			</select>
		</div>

		<!-- The home team first, which is the side the site reads a game from. -->
		<div class="field">
			<label class="micro" for="home">Home team</label>
			<select id="home" name="home" bind:value={homeTeam}>
				<option value="">Pick a team</option>
				{#each teams as team (team.abbreviation)}
					<option value={team.abbreviation}>{team.name}</option>
				{/each}
			</select>
		</div>

		<div class="field">
			<label class="micro" for="away">Away team</label>
			<select id="away" name="away" bind:value={awayTeam}>
				<option value="">Pick a team</option>
				{#each teams as team (team.abbreviation)}
					<option value={team.abbreviation}>{team.name}</option>
				{/each}
			</select>
		</div>
	</div>
</div>

<style>
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

	@media (min-width: 40rem) {
		.fields {
			grid-template-columns: 1fr 1fr;
		}
	}
</style>
