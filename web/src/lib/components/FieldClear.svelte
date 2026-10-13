<script lang="ts">
	type Props = {
		/** Name of what the button clears. Hidden visually and announced after the word Clear. */
		empties: string;
		/** Measured width of the button, so the field can keep its text from running under it. */
		width?: number;
		onclear: () => void;
	};

	let { empties, width = $bindable(0), onclear }: Props = $props();
</script>

<button type="button" class="clear small" bind:clientWidth={width} onclick={onclear}>
	<svg
		viewBox="0 0 16 16"
		fill="none"
		stroke="currentColor"
		stroke-width="1.5"
		stroke-linecap="round"
		aria-hidden="true"
	>
		<path d="M4 4 12 12M12 4 4 12" />
	</svg>
	<span>Clear</span>
	<span class="visually-hidden">{empties}</span>
</button>

<style>
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

	.clear svg {
		width: 1em;
		height: 1em;
	}
</style>
