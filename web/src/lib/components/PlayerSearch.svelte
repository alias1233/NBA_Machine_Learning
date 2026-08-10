<!--
	Finds a player by name and reports the one chosen.

	Given rosters it opens on them, because with a game chosen that is who the reader almost always
	wants. Typing searches the whole league instead, so a player who has just joined a team and is on
	no roster yet is still reachable.

	The prediction service is not reachable from a browser, so the lookup goes through this site's own
	/api/players route. What happens to a chosen player is the caller's business: the main picker
	keeps the name in the box, and a picker taking several players empties it and adds a pill.
-->
<script lang="ts">
	import { onDestroy } from 'svelte';

	import { appear } from '$lib/motion';

	import type { Player, Roster } from '$lib/types';

	type Props = {
		/** Unique on the page. It ties the field, its label and its listbox together. */
		id: string;
		label: string;
		/** Who the box names to begin with. */
		initial?: Player | null;
		/** Offered before anything is typed. Empty means the box opens only on a search. */
		rosters?: Roster[];
		/** Empties the box after a choice, which is what a picker taking several players wants. */
		clearOnChoose?: boolean;
		onchoose: (player: Player) => void;
	};

	let { id, label, initial = null, rosters = [], clearOnChoose = false, onchoose }: Props = $props();

	const TYPING_DELAY = 200;
	const SHORTEST_SEARCH = 2;

	// Deliberately the initial value only. Once the box is on screen the reader owns it.
	// svelte-ignore state_referenced_locally
	let text = $state(initial?.name ?? '');
	let results = $state<Player[]>([]);
	let open = $state(false);
	let active = $state(-1);
	let searching = $state(false);
	let box = $state<HTMLInputElement>();
	let field = $state<HTMLDivElement>();

	/** Puts the reader in the box. The page is moved by whoever called, not by the focus. */
	export function focus() {
		box?.focus({ preventScroll: true });
	}

	export function clear() {
		text = '';
	}

	let timer: ReturnType<typeof setTimeout>;
	let inFlight: AbortController | undefined;

	const searchable = $derived(text.trim().length >= SHORTEST_SEARCH);

	/** What the listbox is showing, and the flat position of each entry for the arrow keys. */
	const shown = $derived.by(() => {
		const groups = searchable
			? [{ label: '', players: results }]
			: rosters.map((roster) => ({ label: roster.team.name, players: roster.players }));

		let position = 0;

		return groups.map((group) => ({
			label: group.label,
			entries: group.players.map((player) => ({ player, position: position++ }))
		}));
	});

	const options = $derived(shown.flatMap((group) => group.entries.map(({ player }) => player)));

	async function search(term: string) {
		inFlight?.abort();

		// The service refuses a search shorter than this, so the rosters are what is left to show.
		if (term.trim().length < SHORTEST_SEARCH) {
			results = [];
			active = -1;
			open = rosters.length > 0;
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
		active = -1;
		results = [];
		onchoose(player);
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			open = false;
			return;
		}

		if (options.length === 0) return;

		if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
			event.preventDefault();

			// The first arrow on a closed box opens it rather than moving anything.
			if (!open) {
				open = true;
				return;
			}

			const step = event.key === 'ArrowDown' ? 1 : -1;
			active = (active + step + options.length) % options.length;
		} else if (event.key === 'Enter' && open) {
			// The marked entry, or the first match for a reader who typed the name and carried on.
			// A roster the box merely opened on was not asked for, so nothing is taken from it.
			const taken = active >= 0 ? options[active] : searchable ? options[0] : null;
			if (taken === null) return;

			event.preventDefault();
			choose(taken);
		}
	}

	/**
	 * The list closes when the reader goes somewhere else, and taking an entry is not that.
	 *
	 * A tap on an entry takes focus off the box and names nothing that took it, because an option is
	 * not focusable, so closing on blur alone would pull the list out from under the tap before it
	 * became a choice. A press outside the field is what closes it in that case.
	 */
	function onFocusOut(event: FocusEvent) {
		const next = event.relatedTarget;

		if (next instanceof Node && !field?.contains(next)) open = false;
	}

	$effect(() => {
		if (!open) return;

		const closeOutside = (event: PointerEvent) => {
			if (!field?.contains(event.target as Node)) open = false;
		};

		document.addEventListener('pointerdown', closeOutside);

		return () => document.removeEventListener('pointerdown', closeOutside);
	});

	onDestroy(() => {
		clearTimeout(timer);
		inFlight?.abort();
	});
</script>

<div class="field search" bind:this={field} onfocusout={onFocusOut}>
	<label class="micro" for={id}>{label}</label>

	<input
		bind:this={box}
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
		oninput={onInput}
		onkeydown={onKeydown}
		onfocus={() => (open = options.length > 0)}
	/>

	{#if open}
		<ul
			class="panel"
			id="{id}-options"
			role="listbox"
			aria-label={searchable ? 'Players' : 'This game'}
			transition:appear
		>
			{#if options.length === 0}
				<li class="empty muted small">{searching ? 'Searching' : 'No player found.'}</li>
			{:else}
				{#each shown as group (group.label)}
					{#if group.label}
						<li class="group micro muted" role="presentation">{group.label}</li>
					{/if}

					{#each group.entries as entry (entry.player.id)}
						<!-- The input keeps focus and owns the keyboard, so the option only handles pointers.
						     A mouse press is refused so the box keeps focus, and a touch press is not,
						     because a prevented one never becomes a tap. -->
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<li
							id="{id}-option-{entry.position}"
							role="option"
							aria-selected={entry.position === active}
							class:active={entry.position === active}
							onpointerdown={(event) => event.pointerType === 'mouse' && event.preventDefault()}
							onclick={() => choose(entry.player)}
						>
							{entry.player.name}
						</li>
					{/each}
				{/each}
			{/if}
		</ul>
	{/if}
</div>

<style>
	.search {
		position: relative;
	}

	/* Floats above the page, so it is the one other thing besides the models menu that is raised. */
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

	li.empty,
	li.group {
		cursor: default;
	}

	/* Names which side of the game a run of players is, so the two rosters read as two lists. */
	li.group {
		min-height: var(--space-6);
	}

	li[role='option']:hover,
	li.active {
		background: var(--surface);
		color: var(--accent);
	}
</style>
