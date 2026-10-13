<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		title: string;
		/** One-line description of the page. */
		lede?: string;
		/** Main action link or button, shown under the lede. */
		action?: Snippet;
		/** Extra content shown at full width under the heading. */
		extra?: Snippet;
	};

	let { title, lede = '', action, extra }: Props = $props();
</script>

<section class="band plate" class:extended={extra}>
	<span class="registration top-start" aria-hidden="true"></span>
	<span class="registration top-end" aria-hidden="true"></span>
	<span class="registration bottom-start" aria-hidden="true"></span>
	<span class="registration bottom-end" aria-hidden="true"></span>

	<div class="page head">
		<h1 class="plate-display">{title}</h1>

		<div class="said">
			{#if lede}
				<p class="lede measure">{lede}</p>
			{/if}

			{#if action}
				<div class="action">{@render action()}</div>
			{/if}
		</div>
	</div>

	{#if extra}
		{@render extra()}
	{/if}
</section>

<style>
	.band {
		position: relative;
		padding-block-end: var(--space-6);
	}

	.band.extended {
		padding-block-end: 0;
	}

	.head {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		align-items: start;
		gap: var(--space-3);
	}

	.said {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-3);
	}

	.lede {
		color: var(--plate-ink);
		font-size: var(--type-note);
	}

	.action {
		margin-block-start: var(--space-1);
		--plane-accent: var(--plate-ink);
	}

	.band.extended .head {
		padding-block-end: var(--space-6);
	}

	@media (min-width: 64rem) {
		.head {
			grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
			align-items: end;
			column-gap: var(--space-7);
		}

		.head h1 {
			grid-row: 1 / -1;
		}

		.said {
			padding-block-end: var(--space-2);
		}
	}
</style>
