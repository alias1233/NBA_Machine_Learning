<!--
	Finds a player by name and reports the one chosen.

	The prediction service is not reachable from a browser, so the lookup goes through this site's own
	/api/players route. What happens to a chosen player is the caller's business: the main picker
	keeps the name in the box, and a picker taking several players empties it and adds a pill. R10.12.
-->
<script lang="ts">
	import { onDestroy } from 'svelte';

	import type { Player } from '$lib/types';

	type Props = {
		/** Unique on the page. It ties the field, its label and its listbox together. */
		id: string;
		label: string;
		/** Who the box names to begin with. */
		initial?: Player | null;
		/** Empties the box after a choice, which is what a picker taking several players wants. */
		clearOnChoose?: boolean;
		disabled?: boolean;
		onchoose: (player: Player) => void;
	};

	let { id, label, initial = null, clearOnChoose = false, disabled = false, onchoose }: Props =
		$props();

	const TYPING_DELAY = 200;
	const SHORTEST_SEARCH = 2;

	// Deliberately the initial value only. Once the box is on screen the reader owns it.
	// svelte-ignore state_referenced_locally
	let text = $state(initial?.name ?? '');
	let results = $state<Player[]>([]);
	let open = $state(false);
	let active = $state(-1);
	let searching = $state(false);

	let timer: ReturnType<typeof setTimeout>;
	let inFlight: AbortController | undefined;

	async function search(term: string) {
		inFlight?.abort();

		// The service refuses a search shorter than this, so there is nothing to ask for yet.
		if (term.trim().length < SHORTEST_SEARCH) {
			open = false;
			results = [];
			return;
		}

		const controller = new AbortController();
		inFlight = controller;
		searching = true;
		open = true;

		try {
			const response = await fetch(`/api/players?search=${encodeURIComponent(term)}`, {
				signal: controller.signal
			});

			results = response.ok ? await response.json() : [];
			active = -1;
		} catch {
			// Aborted, because a newer keystroke replaced this request.
		} finally {
			if (inFlight === controller) searching = false;
		}
	}

	function onInput(event: Event & { currentTarget: HTMLInputElement }) {
		text = event.currentTarget.value;

		clearTimeout(timer);
		timer = setTimeout(() => search(text), TYPING_DELAY);
	}

	function choose(player: Player) {
		text = clearOnChoose ? '' : player.name;
		open = false;
		results = [];
		onchoose(player);
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			open = false;
			return;
		}

		if (!open || results.length === 0) return;

		if (event.key === 'ArrowDown') {
			event.preventDefault();
			active = (active + 1) % results.length;
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			active = (active - 1 + results.length) % results.length;
		} else if (event.key === 'Enter' && active >= 0) {
			event.preventDefault();
			choose(results[active]);
		}
	}

	onDestroy(() => {
		clearTimeout(timer);
		inFlight?.abort();
	});
</script>

<div class="field search">
	<label class="micro" for={id}>{label}</label>

	<input
		{id}
		type="text"
		role="combobox"
		aria-expanded={open}
		aria-controls="{id}-options"
		aria-autocomplete="list"
		aria-activedescendant={active >= 0 ? `${id}-option-${active}` : undefined}
		autocomplete="off"
		placeholder="Search players"
		value={text}
		{disabled}
		oninput={onInput}
		onkeydown={onKeydown}
		onblur={() => (open = false)}
	/>

	{#if open}
		<ul class="panel" id="{id}-options" role="listbox" aria-label="Players">
			{#if results.length === 0}
				<li class="empty muted small">{searching ? 'Searching' : 'No player found.'}</li>
			{:else}
				{#each results as player, index (player.id)}
					<!-- The input keeps focus and owns the keyboard, so the option only handles pointers. -->
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<li
						id="{id}-option-{index}"
						role="option"
						aria-selected={index === active}
						class:active={index === active}
						onpointerdown={(event) => event.preventDefault()}
						onclick={() => choose(player)}
					>
						{player.name}
					</li>
				{/each}
			{/if}
		</ul>
	{/if}
</div>

<style>
	.search {
		position: relative;
	}

	/* Floats above the page, so it is the one other thing besides the models menu that is raised.
	   R5.5 and R10.12. */
	ul {
		position: absolute;
		z-index: 10;
		top: 100%;
		left: 0;
		right: 0;
		margin-top: var(--space-1);
		padding: var(--space-2);
		list-style: none;
		max-height: calc(var(--space-8) * 2.5);
		overflow-y: auto;
		box-shadow: var(--shadow);
	}

	li {
		display: flex;
		align-items: center;
		min-height: var(--tap-target);
		padding-inline: var(--control-padding-x);
		border-radius: var(--radius);
		cursor: pointer;
	}

	li.empty {
		cursor: default;
	}

	li[role='option']:hover,
	li.active {
		background: var(--surface);
		color: var(--accent);
	}
</style>
