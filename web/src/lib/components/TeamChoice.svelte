<script lang="ts">
	import PencilMark from '$lib/components/PencilMark.svelte';

	import type { Team } from '$lib/types';

	type Props = {
		/** Must be unique on the page. */
		id: string;
		label: string;
		/** Form field the selected team is submitted under. */
		name: string;
		/** The two teams in the selected game, away team first. */
		sides: Team[];
		/** Abbreviation of the selected team, or an empty string. */
		value: string;
		onchoose: (team: Team) => void;
	};

	let { id, label, name, sides, value, onchoose }: Props = $props();

	let group = $state<HTMLDivElement>();

	/** Focuses the radio group. */
	export function focus() {
		// A radio group has one tab stop. It is the checked option if there is one.
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

				<span class="said">
					<span class="micro role">{index === 0 ? 'Away' : 'Home'}</span>
					<span class="type-h3 name">{side.name}</span>
				</span>

				<span class="marking">
					{#if chosen}
						<PencilMark bleed="0px" />
					{/if}
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

	.side {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
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
		text-align: start;
	}

	/* The input must stay in the accessibility tree, so do not use display: none. */
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

	.role {
		color: var(--ink-muted);
	}

	.name {
		text-wrap: balance;
	}
</style>
