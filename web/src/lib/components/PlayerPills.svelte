<script lang="ts">
	import { flowingHeight } from '$lib/motion';

	import type { Player } from '$lib/types';

	type Props = {
		players: Player[];
		/** Query parameter each selected player id is submitted under. */
		name: string;
		onremove: (player: Player) => void;
	};

	let { players, name, onremove }: Props = $props();
</script>

{#each players as player (player.id)}
	<input type="hidden" {name} value={player.id} />
{/each}

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

	button:hover {
		color: var(--ink);
	}
</style>
