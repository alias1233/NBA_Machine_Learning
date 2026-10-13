<script lang="ts">
	import PlayerPills from '$lib/components/PlayerPills.svelte';
	import PlayerSearch from '$lib/components/PlayerSearch.svelte';
	import { flow } from '$lib/motion';

	import type { Player } from '$lib/types';

	type Props = {
		/** Must be unique on the page. */
		id: string;
		/** Label for this roster. */
		label: string;
		/** Players who can be marked out. The team's roster, minus anyone the page already excluded. */
		candidates: Player[];
		out: Player[];
		joined: Player[];
		/** Expected lineup changes for this team. Both lists start with these. */
		expected: { out: Player[]; joined: Player[] };
		/** Query parameters the two lists are submitted under. */
		outName: string;
		joinedName: string;
		/** Called after either list changes, so the page can scroll to the next step. */
		onchange?: () => void;
	};

	let {
		id,
		label,
		candidates,
		out = $bindable(),
		joined = $bindable(),
		expected,
		outName,
		joinedName,
		onchange
	}: Props = $props();

	const remaining = $derived(
		candidates.filter((candidate) => !out.some((player) => player.id === candidate.id))
	);

	const samePlayers = (chosen: Player[], suggested: Player[]) =>
		chosen.length === suggested.length &&
		chosen.every((player) => suggested.some(({ id }) => id === player.id));

	/** True if the user changed the lineup from the expected one. */
	const changed = $derived(
		!samePlayers(out, expected.out) || !samePlayers(joined, expected.joined)
	);

	const anyExpected = $derived(expected.out.length > 0 || expected.joined.length > 0);

	/** Status line under the fields. One of three messages. */
	const state = $derived(
		changed
			? 'Your own lineup.'
			: anyExpected
				? 'Who is expected to play, from the latest injury report and rosters.'
				: 'No change from the last game.'
	);

	function addOut(event: Event & { currentTarget: HTMLSelectElement }) {
		const chosen = Number(event.currentTarget.value);
		const sittingOut = remaining.find((candidate) => candidate.id === chosen);

		event.currentTarget.value = '';

		if (!sittingOut) return;

		out = [...out, sittingOut];
		onchange?.();
	}

	function addJoined(player: Player) {
		if (joined.some((chosen) => chosen.id === player.id)) return;

		joined = [...joined, player];
		onchange?.();
	}

	/** Resets both lists to the expected lineup. */
	function reset() {
		out = expected.out;
		joined = expected.joined;
		onchange?.();
	}

	const removeFrom = (players: Player[], removed: Player) =>
		players.filter((player) => player.id !== removed.id);
</script>

<div class="field-group" role="group" aria-labelledby="{id}-label" transition:flow>
	<p class="micro group-label" id="{id}-label">{label}</p>

	<div class="field-pair">
		<div class="field">
			<label class="micro" for="{id}-out">Out</label>
			<select id="{id}-out" onchange={addOut}>
				<option value="">Add a player</option>
				{#each remaining as candidate (candidate.id)}
					<option value={candidate.id}>{candidate.name}</option>
				{/each}
			</select>
			<p class="small muted">Players on this team who will not play.</p>
			<PlayerPills
				players={out}
				name={outName}
				onremove={(player) => (out = removeFrom(out, player))}
			/>
		</div>

		<div class="field">
			<PlayerSearch id="{id}-joined" label="New" clearOnChoose onchoose={addJoined} />
			<p class="small muted">New players who will play and did not play this team's last game.</p>
			<PlayerPills
				players={joined}
				name={joinedName}
				onremove={(player) => (joined = removeFrom(joined, player))}
			/>
		</div>
	</div>

	<p class="small muted state" transition:flow>
		{state}
		{#if changed}
			<button type="button" class="text-link" onclick={reset}>
				{anyExpected ? 'Back to the expected lineup' : 'Clear both lists'}
			</button>
		{/if}
	</p>
</div>

<style>
	.state {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		align-items: baseline;
	}
</style>
