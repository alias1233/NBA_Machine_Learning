<script lang="ts">
	import Notice from '$lib/components/Notice.svelte';
	import { SITE_NAME, pageTitle } from '$lib/site';

	// What each group of inputs says, from the grouped table in docs/STATUS.md.
	const inputs = [
		['Box score', "The player's own line in each past game, plus their team's and the opponent's."],
		['Recent form', 'The same figures over the last 15 games, and weighted towards the newest.'],
		['Long window', 'The average and the spread of the stat over 200 games.'],
		['Availability', "How much of the team's recent schedule the player was there for."],
		['Schedule load', 'Rest, length of the break, and games played in the last 7 and 14 days.'],
		['Season context', 'How far into the season the game is, and how both teams have been winning.'],
		['Teammates', 'Recent averages of the core players the team gained, lost, and is missing.'],
		['Opponent defence', 'How far the opponent lets teams beat their own recent averages.'],
		['Player', 'Age, experience, height, weight, and draft position.']
	];
</script>

<svelte:head>
	<title>{pageTitle('About')}</title>
	<meta
		name="description"
		content="How an NBA player's points, rebounds and assists are predicted, and what the prediction does not cover."
	/>
</svelte:head>

<div class="page">
	<h1 class="page-title">How it works</h1>

	<section>
		<h2>What this is</h2>
		<p>
			{SITE_NAME} predicts how an NBA player will do in a game that has not been played yet. It is
			free and it sells nothing.
		</p>
		<p>
			An answer is not one number. For points it gives the chance of exactly 0, exactly 1, and so on,
			so the odds of any line are already on the page.
		</p>
	</section>

	<section id="how">
		<h2>How a prediction is made</h2>
		<p>
			Every box score of every game played is collected and stored. From those, a set of inputs is
			worked out for each player and each game.
		</p>
		<p>
			A network reads the player's last 50 games in order, keeping a running memory of them. It joins
			that memory with what is known about the game being predicted.
		</p>
		<p>
			It then gives every whole number a share of the chance, and those shares add up to one. Over
			and under odds for a line are the shares on each side of it added up.
		</p>
	</section>

	<section id="which-games">
		<h2>Which games can be predicted</h2>
		<p>
			A game can be predicted once every earlier game of both its teams has been collected. Until
			then one of the two teams would be read a game out of date.
		</p>
		<p>
			The player also needs 20 recorded games behind them. A rookie in their first month cannot be
			predicted at all.
		</p>
	</section>

	<section id="inputs">
		<h2>What the model reads</h2>
		<p>Nine groups, all of them worked out from games that were already played.</p>

		<table class="small">
			<thead>
				<tr>
					<th scope="col">Group</th>
					<th scope="col">What it says</th>
				</tr>
			</thead>
			<tbody>
				{#each inputs as [group, says] (group)}
					<tr>
						<th scope="row">{group}</th>
						<td>{says}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>

	<section id="accuracy">
		<h2>How accurate it is</h2>
		<Notice>Accuracy is not published yet. The models are still being trained.</Notice>
	</section>

	<section id="limits">
		<h2>What it does not do</h2>
		<p>
			It has no injury report. A player who is ruled out an hour before tip-off is predicted as
			though they will play.
		</p>
		<p>
			It gives no betting advice and takes no bets. It reports what a model estimates and nothing
			more.
		</p>
		<p>
			It assumes the collected data is current. A prediction made against stale data reads the gap as
			time off and answers low.
		</p>
	</section>
</div>

<style>
	.page {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		scroll-margin-top: var(--space-8);
	}

	table {
		border-collapse: collapse;
		text-align: left;
	}

	th,
	td {
		padding: var(--space-2) var(--space-4) var(--space-2) 0;
		border-bottom: var(--rule);
		vertical-align: top;
	}

	thead th {
		color: var(--ink-muted);
	}

	tbody th {
		padding-right: var(--space-5);
	}
</style>
