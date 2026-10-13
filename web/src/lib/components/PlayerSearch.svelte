<script lang="ts">
	import { onDestroy } from 'svelte';

	import FieldClear from '$lib/components/FieldClear.svelte';
	import { appear, flowingHeight } from '$lib/motion';
	import { isTap } from '$lib/touch';

	import type { Player, Roster } from '$lib/types';

	type Props = {
		/** Must be unique on the page. */
		id: string;
		label: string;
		/** Player shown in the box at the start. */
		initial?: Player | null;
		/** Players suggested before anything is typed. If empty, the list only opens for a search. */
		rosters?: Roster[];
		/** True while the rosters are still loading. */
		loadingRosters?: boolean;
		/** Clears the box after a player is chosen. */
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

	/** Number of placeholder rows shown while names load. */
	const RESERVED_ROWS = 5;

	const LEAGUE = 'Across the league';

	// svelte-ignore state_referenced_locally
	let text = $state(initial?.name ?? '');
	let results = $state<Player[]>([]);
	let open = $state(false);
	let active = $state(-1);
	let searching = $state(false);
	let box = $state<HTMLInputElement>();
	let field = $state<HTMLDivElement>();

	/** Measured width of the Clear button, so the text does not run under it. */
	let clearWidth = $state(0);

	/** Focuses the search box. */
	export function focus() {
		box?.focus({ preventScroll: true });
	}

	export function clear() {
		text = '';
	}

	/** Clears the box, keeps it focused and opens the list. */
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

	/** Groups shown in the list. Each entry has a flat index for arrow key navigation. */
	const shown = $derived.by(() => {
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

	/** True while the names for the list are still loading. */
	const waiting = $derived(searchable ? searching : loadingRosters);

	async function search(term: string) {
		inFlight?.abort();

		// The service rejects shorter searches, so the rosters are shown.
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
		// Ignores a click after the list has closed. It comes from a touch that was already handled.
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

			if (!open) {
				open = true;
				return;
			}

			const step = event.key === 'ArrowDown' ? 1 : -1;
			active = (active + step + options.length) % options.length;
		} else if (event.key === 'Enter' && open) {
			const taken = active >= 0 ? options[active] : searchable ? options[0] : null;
			if (taken === null) return;

			event.preventDefault();
			choose(taken);
		}
	}

	/** Closes the list when focus moves to something outside the field. */
	function onFocusOut(event: FocusEvent) {
		const next = event.relatedTarget;

		if (next instanceof Node && !field?.contains(next)) open = false;
	}

	/** Closes the list on a click or tap outside the field. A scroll does not close it. */
	$effect(() => {
		if (!open) return;

		/** Where a touch started outside the field. Cleared once it turns out to be a tap or a scroll. */
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

	{#if text !== ''}
		<FieldClear empties="player search" bind:width={clearWidth} onclear={clearAndFocus} />
	{/if}

	{#if open}
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
							<!-- The input keeps focus and handles the keyboard, so options only handle pointer events. -->
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

	li.hint {
		align-items: start;
		margin-top: var(--space-1);
		padding-block: var(--space-2);
		border-top: var(--rule-panel);
		border-radius: 0;
	}

	.waiting {
		width: 100%;
		max-width: calc(var(--space-8) * 2);
		height: var(--type-body);
	}

	li.group {
		min-height: var(--space-6);
	}

	li[role='option']:hover,
	li.active {
		background: var(--surface);
		color: var(--accent);
	}
</style>
