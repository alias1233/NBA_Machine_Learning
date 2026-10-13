<script lang="ts">
	type Props = {
		/** Anchor and heading of each section, in page order. */
		sections: string[][];
		label: string;
	};

	let { sections, label }: Props = $props();

	/** Anchor of the section the user is in. It is the last one to pass the reading line. */
	let current = $state('');

	let open = $state(false);

	/** Divides the screen height to place the reading line, here one third of the way down. */
	const READING_LINE = 3;

	$effect(() => {
		const anchors = sections.map(([anchor]) => anchor);

		const mark = () => {
			const line = window.innerHeight / READING_LINE;
			const foot = document.documentElement.scrollHeight - window.innerHeight;

			// The last section may be too short to reach the line, so it is selected at the bottom of the page.
			if (window.scrollY >= foot - 1) {
				current = anchors[anchors.length - 1] ?? '';
				return;
			}

			let reading = anchors[0] ?? '';

			for (const anchor of anchors) {
				const top = document.getElementById(anchor)?.getBoundingClientRect().top;

				if (top !== undefined && top <= line) reading = anchor;
			}

			current = reading;
		};

		mark();

		window.addEventListener('scroll', mark, { passive: true });
		window.addEventListener('resize', mark);

		return () => {
			window.removeEventListener('scroll', mark);
			window.removeEventListener('resize', mark);
		};
	});
</script>

<nav class="index" class:open aria-label={label}>
	<ul class="entries" id="section-index">
		{#each sections as [anchor, heading] (anchor)}
			<li>
				<a
					class="small"
					href="#{anchor}"
					aria-current={anchor === current ? 'location' : undefined}
					onclick={() => (open = false)}
				>
					{heading}
				</a>
			</li>
		{/each}
	</ul>

	<button
		type="button"
		class="toggle"
		aria-expanded={open}
		aria-controls="section-index"
		onclick={() => (open = !open)}
	>
		<span class="small">Sections</span>

		<svg class="mark" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
			<path d="M5 9 L12 16 L19 9" />
		</svg>
	</button>
</nav>

<style>
	.entries {
		display: flex;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.entries li {
		display: flex;
		border-inline-start: var(--rule-accent);
		border-inline-start-color: transparent;
	}

	.entries li:has(a[aria-current]) {
		border-inline-start-color: var(--plane-accent);
	}

	.entries a {
		display: flex;
		align-items: center;
		flex: 1;
		min-height: var(--tap-target);
		padding-inline: var(--space-3);
		color: var(--ink-muted);
		text-decoration: none;
		transition: color var(--motion-fast) var(--ease-in);
	}

	.entries a:hover {
		color: var(--plane-accent);
	}

	.entries a[aria-current] {
		color: var(--plane-accent);
		font-weight: 600;
	}

	.mark {
		flex: none;
		width: var(--icon);
		height: var(--icon);
		fill: none;
		stroke: currentColor;
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
		transition: rotate var(--motion) var(--ease-in);
	}

	/* Narrow screens. A tab in the bottom corner, with the list opening above it. */
	@media (width < 64rem) {
		.index {
			position: fixed;
			z-index: var(--layer-floating);
			right: var(--space-4);
			bottom: var(--space-4);
			display: flex;
			flex-direction: column;
			align-items: flex-end;
			gap: var(--space-2);
			pointer-events: none;
		}

		.entries {
			flex-direction: column;
			visibility: hidden;
			opacity: 0;
			min-width: 12rem;
			max-width: min(20rem, calc(100vw - var(--space-4) * 2));
			padding-block: var(--space-2);
			background: var(--panel);
			border: var(--rule-panel);
			border-radius: var(--radius);
			box-shadow: var(--shadow);
			transition:
				opacity var(--motion) var(--ease-in),
				visibility var(--motion);
		}

		.index.open .entries {
			visibility: visible;
			opacity: 1;
			pointer-events: auto;
		}

		.toggle {
			display: flex;
			align-items: center;
			gap: var(--space-2);
			min-height: var(--tap-target);
			padding: var(--control-padding-y) var(--control-padding-x);
			background: var(--panel);
			border: var(--rule-panel);
			border-radius: var(--radius);
			box-shadow: var(--shadow);
			cursor: pointer;
			pointer-events: auto;
			transition: color var(--motion-fast) var(--ease-in);
		}

		.toggle:hover {
			color: var(--plane-accent);
		}

		.mark {
			rotate: 180deg;
		}

		.index.open .mark {
			rotate: 0deg;
		}
	}

	@media (orientation: portrait) and (width < 64rem) {
		.entries,
		.toggle {
			background: transparent;
		}
	}

	/* Wide screens. A column beside the content. */
	@media (min-width: 64rem) {
		.index {
			position: sticky;
			top: calc(var(--header-height) + var(--space-5));
		}

		.entries {
			flex-direction: column;
			border-inline-start: var(--rule-panel);
		}

		.entries li {
			margin-inline-start: -1px;
		}

		.toggle {
			display: none;
		}
	}
</style>
