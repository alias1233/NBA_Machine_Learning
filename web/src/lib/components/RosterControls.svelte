<!--
	Who one team is playing without, and who is playing for it who did not play its last game.

	Every model reads a team as the players who played its last game, and that is what these two
	fields correct. They open filled in: the collected injury report and roster snapshot say who has
	been ruled out and who is back or newly arrived, and those names are put in the fields as though
	the reader had entered them. They submit as the same parameters and can be taken out or added to
	exactly like a name the reader chose, so a prediction is right about the night without anyone
	having to look anything up, and still theirs to play with.

	The Out list is the team's own roster, because sitting somebody out means naming somebody already
	on it. Playing is a search of the whole league instead, since somebody who has just joined is on
	no roster yet, which is one of the cases the field exists for.

	Both lists go into the address bar as they are chosen, so a prediction made with a changed roster
	is still a shareable link. A change takes effect on the next prediction, with the rest of the
	form, so nothing here fires a request on its own.
-->
<script lang="ts">
	import PlayerPills from '$lib/components/PlayerPills.svelte';
	import PlayerSearch from '$lib/components/PlayerSearch.svelte';
	import { flow } from '$lib/motion';

	import type { Player } from '$lib/types';

	type Props = {
		/** Unique on the page. It ties each field to its label and the group to its heading. */
		id: string;
		/** What this roster is called, which is the team's name where a page carries both sides. */
		label: string;
		/** Who can be sat out: this team's roster, less anyone the page has already ruled out. */
		candidates: Player[];
		out: Player[];
		joined: Player[];
		/**
		 * The lineup this side is expected to field, which is what the two lists opened on.
		 *
		 * Held so the group can say whether it is still showing that or the reader's own, and put it
		 * back where they want it. Empty where nothing collected says who will play.
		 */
		expected: { out: Player[]; joined: Player[] };
		/** The query parameters the two lists are submitted as. */
		outName: string;
		joinedName: string;
		/** Called after either list changes, so a page can walk the reader on. */
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

	/** Who is left to sit out, which is the roster less whoever is already out of it. */
	const remaining = $derived(
		candidates.filter((candidate) => !out.some((player) => player.id === candidate.id))
	);

	const samePlayers = (chosen: Player[], suggested: Player[]) =>
		chosen.length === suggested.length &&
		chosen.every((player) => suggested.some(({ id }) => id === player.id));

	/** Whether the reader has moved off the lineup the fields opened on. */
	const changed = $derived(
		!samePlayers(out, expected.out) || !samePlayers(joined, expected.joined)
	);

	const anyExpected = $derived(expected.out.length > 0 || expected.joined.length > 0);

	/**
	 * The one line under the fields, which says which of three states the group is in: nobody is
	 * missing, the night's own lineup is showing, or the reader has made one of their own.
	 */
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

	/** Puts both lists back to what the page opened on, which is a name the reader cannot retype. */
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
		<!-- A name the reader took out cannot be typed back in from memory, so the lineup the fields
		     opened on stays one press away for as long as it is not the one showing. -->
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
