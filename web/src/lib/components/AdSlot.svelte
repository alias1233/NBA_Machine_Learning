<script lang="ts">
	import { ADS_ENABLED, AD_SLOTS } from '$lib/ads';

	let { place }: { place: keyof typeof AD_SLOTS } = $props();
</script>

{#if ADS_ENABLED}
	<div class="slot">
		<p class="micro muted">Advertisement</p>
		<div class="frame" id={AD_SLOTS[place]}></div>
	</div>
{/if}

<style>
	.slot {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.frame {
		height: var(--ad-height);
		background: var(--surface-sunken);
		border-radius: var(--radius);
	}

	@media (min-width: 40rem) {
		.frame {
			height: var(--ad-height-wide);
		}
	}
</style>
