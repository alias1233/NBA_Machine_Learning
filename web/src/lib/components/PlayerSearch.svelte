<!--
	Finds a player by name and reports the one chosen.

	Given rosters it opens on them, because with a game chosen that is who the reader almost always
	wants. Typing searches the whole league instead, so a player who has just joined a team and is on
	no roster yet is still reachable. The list says which of the two it is showing, and a roster ends
	on the line that says what to do about a name that is not on it, because that is where a reader
	looks when they cannot find somebody rather than under the field.

	The prediction service is not reachable from a browser, so the lookup goes through this site's own
	/api/players route. What happens to a chosen player is the caller's business: the main picker
	keeps the name in the box, and a picker taking several players empties it and adds a pill.

	The list opens the moment it is asked for, whether or not it has anybody to show yet. While a
	roster or a search is on its way it holds pulsing rows of the size the names will take.

	A finger works the list the way it works the page. Putting one down outside the list starts a
	scroll as often as it dismisses it, so the list is only put away where a finger is lifted about
	where it landed, and an entry is taken on that lift rather than on the click the browser makes of
	it afterwards.

	A box holding words carries a Clear control at its right edge, so changing who is predicted is one
	press rather than a held backspace. It takes the words and nothing else, because the picker was
	answered by an entry and that answer stands until another entry replaces it.
-->
<script lang="ts">
	import { onDestroy } from 'svelte';

	import { appear, flowingHeight } from '$lib/motion';
	import { isTap } from '$lib/touch';

	import type { Player, Roster } from '$lib/types';

	type Props = {
		/** Unique on the page. It ties the field, its label and its listbox together. */
		id: string;
		label: string;
		/** Who the box names to begin with. */
		initial?: Player | null;
		/** Offered before anything is typed. Empty means the box opens only on a search. */
		rosters?: Roster[];
		/** True while the rosters above are still coming, which is what the list waits on. */
		loadingRosters?: boolean;
		/** Empties the box after a choice, which is what a picker taking several players wants. */
		clearOnChoose?: boolean;
		onchoose: (player: Player) => void;
	};

	let {
		id,
		label,
		initial = null,
		rosters = [],
		loadingRosters = false,
		clearOnChoose = false,
		onchoose
	}: Props = $props();

	const TYPING_DELAY = 200;
	const SHORTEST_SEARCH = 2;

	/** How many names the list stands in for while it waits for them. */
	const RESERVED_ROWS = 5;

	/** What the list calls a search, which is the whole league rather than the game's own teams. */
	const LEAGUE = 'Across the league';

	// Deliberately the initial value only. Once the box is on screen the reader owns it.
	// svelte-ignore state_referenced_locally
	let text = $state(initial?.name ?? '');
	let results = $state<Player[]>([]);
	let open = $state(false);
	let active = $state(-1);
	let searching = $state(false);
	let box = $state<HTMLInputElement>();
	let field = $state<HTMLDivElement>();

	/** Measured rather than reserved, so the words never run under the Clear control beside them. */
	let clearWidth = $state(0);

	/** Puts the reader in the box. The page is moved by whoever called, not by the focus. */
	export function focus() {
		box?.focus({ preventScroll: true });
	}

	export function clear() {
		text = '';
	}

	/**
	 * Empties the box and leaves the reader in it with the list open.
	 *
	 * A search already on its way is dropped, because its answers are to words that are no longer
	 * there. Opening is set here rather than left to the focus, since a box that already had focus
	 * fires no focus event.
	 */
	function clearAndFocus() {
		clearTimeout(timer);
		inFlight?.abort();

		text = '';
		results = [];
		active = -1;
		searching = false;
		open = rosters.length > 0 || loadingRosters;

		box?.focus();
	}

	let timer: ReturnType<typeof setTimeout>;
	let inFlight: AbortController | undefined;

	const searchable = $derived(text.trim().length >= SHORTEST_SEARCH);

	/** What the listbox is showing, and the flat position of each entry for the arrow keys. */
	const shown = $derived.by(() => {
		// One roster names itself in the field above the list, so a heading over it would say the
		// team's name twice. Two need telling apart, and a search is neither of them.
		const groups = searchable
			? [{ label: LEAGUE, players: results }]
			: rosters.map((roster) => ({
					label: rosters.length > 1 ? roster.team.name : '',
					players: roster.players
				}));

		let position = 0;

		return groups.map((group) => ({
			label: group.label,
			entries: group.players.map((player) => ({ player, position: position++ }))
		}));
	});

	const options = $derived(shown.flatMap((group) => group.entries.map(({ player }) => player)));

	/** Whether the names the list is going to hold are still on their way. */
	const waiting = $derived(searchable ? searching : loadingRosters);

	async function search(term: string) {
		inFlight?.abort();

		// The service refuses a search shorter than this, so the rosters are what is left to show.
		if (term.trim().length < SHORTEST_SEARCH) {
			results = [];
			active = -1;
			open = rosters.length > 0 || loadingRosters;
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
		// A press landing after the list has closed is the tail of one already taken. A touch takes an
		// entry the moment it is lifted, and the click the browser makes of it arrives afterwards.
		if (!open) return;

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

	/**
	 * A press outside the field closes the list, and a scroll is not one.
	 *
	 * A mouse press is a press the moment it goes down. A finger is not: putting one on the page is
	 * as often the start of a scroll as it is a dismissal, and closing on that alone took the list
	 * away from every reader who tried to scroll it into view. So a touch closes the list only where
	 * it is lifted roughly where it landed. A scroll is canceled rather than lifted, and one that
	 * travels is a drag rather than a press either way.
	 */
	$effect(() => {
		if (!open) return;

		/** Where a finger went down outside the field, until it becomes a press or a scroll. */
		let from: { x: number; y: number } | null = null;

		const outside = (event: PointerEvent) => !field?.contains(event.target as Node);

		const onDown = (event: PointerEvent) => {
			if (!outside(event)) return;

			if (event.pointerType === 'mouse') open = false;
			else from = { x: event.clientX, y: event.clientY };
		};

		const onUp = (event: PointerEvent) => {
			if (from === null) return;

			if (isTap(from, event) && outside(event)) open = false;

			from = null;
		};

		const onCancel = () => (from = null);

		document.addEventListener('pointerdown', onDown);
		document.addEventListener('pointerup', onUp);
		document.addEventListener('pointercancel', onCancel);

		return () => {
			document.removeEventListener('pointerdown', onDown);
			document.removeEventListener('pointerup', onUp);
			document.removeEventListener('pointercancel', onCancel);
		};
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
		style:padding-right={text === '' ? null : `calc(${clearWidth}px + var(--space-2))`}
		oninput={onInput}
		onkeydown={onKeydown}
		onfocus={() => (open = options.length > 0 || waiting)}
	/>

	<!-- Inside the box it empties, and only while there is something to empty. -->
	{#if text !== ''}
		<button type="button" class="clear small" bind:clientWidth={clearWidth} onclick={clearAndFocus}>
			<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">
				<path d="M4 4 12 12M12 4 4 12" />
			</svg>
			<span>Clear</span>
		</button>
	{/if}

	{#if open}
		<!-- It floats, so it fades where it stands. Its height flows, so names arriving under a
		     reader who is already looking at the list do not throw it open in one frame. -->
		<div class="floating panel" transition:appear use:flowingHeight>
			<ul
				id="{id}-options"
				role="listbox"
				aria-label={searchable ? 'Players matching your search' : 'Players in this game'}
				aria-busy={waiting || undefined}
			>
				{#if waiting && options.length === 0}
					{#each Array(RESERVED_ROWS) as _, row (row)}
						<li class="reserved" role="presentation"><span class="waiting"></span></li>
					{/each}
				{:else if options.length === 0}
					<li class="empty muted small">No player matches that name.</li>
				{:else}
					{#each shown as group (group.label)}
						{#if group.label}
							<li class="group micro muted" role="presentation">{group.label}</li>
						{/if}

						{#each group.entries as entry (entry.player.id)}
							<!--
								The input keeps focus and owns the keyboard, so the option only handles pointers.
								A mouse press is refused so the box keeps focus, and a touch press is not,
								because a prevented one never becomes a tap.

								A finger takes the entry the moment it is lifted off it. The click a browser
								makes of a tap is dispatched after the box has given up focus, which on a phone
								hides the keyboard and moves the page out from under the finger, so by then the
								click can land on anything or on nothing. Lifting is unambiguous: a swipe that
								scrolls the list is canceled rather than lifted, so it takes nobody.

								The click is still handled, because that is what assistive technology and a
								mouse send. Whichever of the two arrives second finds the list closed.
							-->
							<!-- svelte-ignore a11y_click_events_have_key_events -->
							<li
								id="{id}-option-{entry.position}"
								role="option"
								aria-selected={entry.position === active}
								class:active={entry.position === active}
								onpointerdown={(event) => event.pointerType === 'mouse' && event.preventDefault()}
								onpointerup={(event) => event.pointerType !== 'mouse' && choose(entry.player)}
								onclick={() => choose(entry.player)}
							>
								{entry.player.name}
							</li>
						{/each}
					{/each}

					<!-- Where a roster runs out, which is exactly where a reader who cannot find their
					     player is looking. It is not an option, so it is not reachable by arrow key. -->
					{#if !searchable}
						<li class="hint muted small" role="presentation">
							Somebody missing? Type a name to search the whole league.
						</li>
					{/if}
				{/if}
			</ul>
		</div>
	{/if}
</div>

<style>
	.search {
		position: relative;
	}

	/* Inside the box, against its right edge and the full height of it, so it is a finger wide in
	   both directions without taking a row of its own. It reads as part of the field rather than as
	   something to act on, so it takes the muted ink and none of the platform's own chrome. */
	.clear {
		position: absolute;
		right: var(--space-2);
		bottom: 0;
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		height: var(--tap-target);
		padding-block: 0;
		padding-inline: var(--space-2);
		background: none;
		border: none;
		color: var(--ink-muted);
		cursor: pointer;
	}

	/* Current color, a stroke and no fill, at the size of the word beside it. */
	.clear svg {
		width: 1em;
		height: 1em;
	}

	/* Floats above the page, so it is the one other thing besides the models menu that is raised. */
	.floating {
		position: absolute;
		z-index: var(--layer-floating);
		top: 100%;
		left: 0;
		right: 0;
		margin-top: var(--space-1);
		padding: var(--space-2);
		overflow: clip;
		box-shadow: var(--shadow);
	}

	/*
	 * The list is what runs out of room, so it is what scrolls. The panel around it flows to whatever
	 * height that settles at.
	 *
	 * It is given the room a whole roster needs, because a list showing five of eighteen names reads
	 * as a short list rather than as a long one the reader has to scroll. The screen is the other
	 * ceiling, so a list on a phone never runs past the bottom of it.
	 */
	ul {
		margin: 0;
		padding: 0;
		list-style: none;
		max-height: min(60svh, calc(var(--space-8) * 4));
		overflow-y: auto;
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
	li.group,
	li.hint,
	li.reserved {
		cursor: default;
	}

	/* Set off from the names above it by a rule, because it is about the list rather than in it. */
	li.hint {
		align-items: start;
		margin-top: var(--space-1);
		padding-block: var(--space-2);
		border-top: var(--rule-panel);
		border-radius: 0;
	}

	/* Given its size, because a name it is standing in for has none to take. It is what says the
	   list is still on its way rather than one with nobody in it. */
	.waiting {
		width: 100%;
		max-width: calc(var(--space-8) * 2);
		height: var(--type-body);
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
