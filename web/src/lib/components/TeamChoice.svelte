<!--
	Which side of a game an answer is about, asked as the two sides themselves.

	A game has exactly two answers to this, so a list that has to be opened is a control standing in
	front of a choice that already fits on the page. Both sides are printed side by side, away first,
	which is the order the board deals them and the order an answer names them.

	The side the reader settles on is marked with the same wet-erase X the card they picked took,
	because both are the reader's own question rather than something the model measured. Every tile
	holds the box that mark lands in, so choosing one moves nothing.

	It is a radio group rather than two buttons, so the arrow keys move between the two sides, one of
	two is what a screen reader is told, and a form submits the answer without a hidden field.
-->
<script lang="ts">
	import PencilMark from '$lib/components/PencilMark.svelte';

	import type { Team } from '$lib/types';

	type Props = {
		/** Unique on the page. It ties the group's label to the two controls under it. */
		id: string;
		label: string;
		/** The field the chosen side is sent as. */
		name: string;
		/** The two sides of the chosen game, away first. */
		sides: Team[];
		/** The abbreviation of the chosen side, or empty. */
		value: string;
		onchoose: (team: Team) => void;
	};

	let { id, label, name, sides, value, onchoose }: Props = $props();

	let group = $state<HTMLDivElement>();

	/** Puts the reader on the group. The page is moved by whoever called, not by the focus. */
	export function focus() {
		// A radio group holds one tab stop, and it is the chosen side once there is one.
		const marked = group?.querySelector<HTMLInputElement>('input:checked');
		const opening = marked ?? group?.querySelector<HTMLInputElement>('input');

		opening?.focus({ preventScroll: true });
	}
</script>

<div class="field" role="radiogroup" aria-labelledby="{id}-label">
	<p class="micro" id="{id}-label">{label}</p>

	<div class="sides" bind:this={group}>
		{#each sides as side, index (side.abbreviation)}
			{@const chosen = side.abbreviation === value}

			<label class="side" class:chosen>
				<input
					type="radio"
					{name}
					value={side.abbreviation}
					checked={chosen}
					onchange={() => onchoose(side)}
				/>

				<!-- The box the reader marks. It is held whether or not this side is the one, so the two
				     tiles are the same size and neither moves when the choice is made. -->
				<span class="marking">
					{#if chosen}
						<PencilMark bleed="0px" />
					{/if}
				</span>

				<span class="said">
					<span class="micro role">{index === 0 ? 'Away' : 'Home'}</span>
					<span class="type-h3 name">{side.name}</span>
				</span>
			</label>
		{/each}
	</div>
</div>

<style>
	.sides {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-4);
	}

	/*
	 * A surface with the stroke that says a thing takes input, which is what every field on this page
	 * takes. Picking one is marked by the ring, by full-strength ink and by the control's own checked
	 * state, so nothing about the choice is carried by colour.
	 */
	.side {
		position: relative;
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		align-items: center;
		gap: var(--space-3);
		min-height: var(--tap-target);
		padding: var(--space-3);
		background: var(--surface);
		border: var(--rule-control);
		border-radius: var(--radius);
		color: var(--ink-muted);
		cursor: pointer;
		transition:
			color var(--motion-fast) var(--ease-in),
			border-color var(--motion-fast) var(--ease-in);
	}

	.side:hover,
	.side.chosen {
		color: var(--ink);
	}

	.side.chosen {
		border-color: var(--ink);
	}

	/* Where the reader's X lands. It is the one part of the tile the printing leaves empty, which is
	   what makes it the part a mark can be drawn in. */
	.marking {
		position: relative;
		width: 1.5rem;
		height: 1.5rem;
	}

	.said {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		min-width: 0;
	}

	/* The control itself is what the keyboard and the assistive tree work with, so it is present and
	   the label draws around it. Never display: none, which takes it out of both. */
	.side input {
		position: absolute;
		opacity: 0;
		pointer-events: none;
	}

	.side:has(input:focus-visible) {
		outline: var(--rule-accent);
		outline-color: var(--plane-accent);
		outline-offset: 2px;
	}

	/* Which side of the game this is, which is the one thing the name under it does not say. */
	.role {
		color: var(--ink-muted);
	}

	/* The name wraps rather than the tile growing, so the two sides are always the same size. */
	.name {
		text-wrap: balance;
	}
</style>
