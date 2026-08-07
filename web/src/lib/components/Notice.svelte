<!--
	A notice, in one of three tones. It is a panel, so it sits in the flow where the thing it is about
	would have been. It never floats, never appears as a toast, and never dismisses itself. R10.24.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		/** Neutral is an empty state, warning is something stale or partial, error is a failure. */
		tone?: 'neutral' | 'warning' | 'error';
		children: Snippet;
	};

	let { tone = 'neutral', children }: Props = $props();
</script>

<div class="panel {tone}">
	<p class="small">{@render children()}</p>
</div>

<style>
	.warning {
		background: var(--warn-wash);
		border: var(--rule-panel);
		border-color: var(--warn-border);
	}

	/* The one place a data colour is allowed outside data, because a red error is a convention older
	   than this site. The tone is carried by the words as well, never by the colour alone. R3.9. */
	.error p {
		color: var(--under);
	}
</style>
