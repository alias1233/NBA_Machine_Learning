<!--
	The control that empties the box it stands in.

	A field holding words carries one at its right edge, so changing an answer is one press rather
	than a held backspace. It reads as part of the field rather than as something to act on, so it
	takes the muted ink and none of the platform's own chrome.

	It lies against the bottom of the field, which is where the box is under its label, so whatever
	holds one positions it. Its width is reported back because the words in the box have to stop
	before it rather than run under it.

	The word on it is what a reader sees and the first thing anybody hears, and what it empties is
	said after it, so a page carrying two of these is not two controls both called Clear.
-->
<script lang="ts">
	type Props = {
		/** What pressing it empties, heard after the word Clear and never drawn. */
		empties: string;
		/** How wide it prints, so the field can hold its words clear of it. */
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
	/* Inside the box, against its right edge and the full height of it, so it is a finger wide in
	   both directions without taking a row of its own. */
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
</style>
