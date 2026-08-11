<!--
	The players a picker has been given, each as a removable pill.

	The hidden inputs are what put the choice in the URL when the form is submitted, so a prediction
	made with a changed roster is still a shareable link.
-->
<script lang="ts">
	import { flowingHeight } from '$lib/motion';

	import type { Player } from '$lib/types';

	type Props = {
		players: Player[];
		/** The query parameter each chosen id is submitted as. */
		name: string;
		onremove: (player: Player) => void;
	};

	let { players, name, onremove }: Props = $props();
</script>

{#each players as player (player.id)}
	<input type="hidden" {name} value={player.id} />
{/each}

<!-- Held at the height of the list, so a pill added to one already open flows the same way the first
     one arriving does. Empty it takes no height at all. -->
<div class="pills" use:flowingHeight>
	<ul>
		{#each players as player (player.id)}
			<li class="pill small">
				<span>{player.name}</span>

				<button type="button" aria-label="Remove {player.name}" onclick={() => onremove(player)}>
					<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true">
						<path d="M6 6l8 8M14 6l-8 8" fill="none" stroke="currentColor" stroke-width="1.5" />
					</svg>
				</button>
			</li>
		{/each}
	</ul>
</div>

<style>
	.pills {
		overflow: clip;
	}

	ul {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		padding: 0;
		list-style: none;
	}

	.pill {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		min-height: var(--tap-target);
		padding-left: var(--control-padding-x);
		background: var(--surface);
		border: var(--rule-control);
		border-radius: var(--radius-full);
	}

	/* The cross sits beside the player's name, which is the text label it belongs to. */
	button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: var(--tap-target);
		height: var(--tap-target);
		padding: 0;
		background: none;
		border: none;
		border-radius: var(--radius-full);
		color: var(--ink-muted);
		cursor: pointer;
		transition: color var(--motion-fast) var(--ease-in);
	}

	/* Emphasis rather than accent, because a remove control is not one of the marks the accent is
	   allowed. */
	button:hover {
		color: var(--ink);
	}
</style>
