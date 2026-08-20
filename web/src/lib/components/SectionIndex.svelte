<!--
	What a page holds, listed.

	An explaining page is long and a reader usually came for one part of it, so the parts are named
	and the one they are reading is marked as they go. Wide, the list stands beside the sections in
	the column the text does not use and follows the reader down. Narrow, there is no column to stand
	in and a run of links across the top is out of reach the moment the reader is into the page, so
	it is a tab in the bottom corner instead: it follows the screen, it opens the list above itself,
	and it stays open until the reader closes it, so the page can be scrolled with it standing.

	The anchors are the sections' own, so every entry is a link to somewhere already on the page and
	travels to it rather than jumping.
-->
<script lang="ts">
	type Props = {
		/** Each section's anchor and its heading, in the order the page sets them. */
		sections: string[][];
		label: string;
	};

	let { sections, label }: Props = $props();

	/** The section the reader is in, which is the last one to have passed the reading line. */
	let current = $state('');

	let open = $state(false);

	/**
	 * How far down the screen a section counts as the one being read. A third of it, rather than the
	 * top edge, because a heading standing at the very top of the screen is one the reader has only
	 * just reached, and because a section landed on from the list starts above this line.
	 */
	const READING_LINE = 3;

	$effect(() => {
		const anchors = sections.map(([anchor]) => anchor);

		const mark = () => {
			const line = window.innerHeight / READING_LINE;
			const foot = document.documentElement.scrollHeight - window.innerHeight;

			// The last section is often shorter than the screen, so nothing below it can ever bring it
			// past the line. The bottom of the page is that section by definition.
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
				<!-- Marked as a place on the page rather than as the page itself, which is what the header
				     does for the section of the home page it points at. -->
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

	<!-- Only ever drawn where the list has no column to stand in. It says what it opens rather than
	     carrying a symbol alone, because it is the one way to the rest of a long page. -->
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

	/* Room for the mark on the section being read, held open by every entry, so nothing moves as the
	   reader passes from one to the next. */
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

	/* The section being read, in the accent and set heavier, with the rule beside it. Never colour
	   alone. */
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

	/*
	 * Narrow: a tab in the bottom corner of the screen with the list opening above it. It is the one
	 * thing on the site that follows the screen, because it is the only way into a long page once the
	 * top of it is gone. The layer takes no presses of its own, so the page under the room the list
	 * would take is worked on as though nothing were there.
	 */
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

		/* A list standing over the page, so it is on the page's own paper and carries the one shadow.
		   Closed, it is not drawn and cannot be reached by a press or by the keyboard. */
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

		/* Pointing up at the list it opens, and back down at the tab once the list is standing. */
		.mark {
			rotate: 180deg;
		}

		.index.open .mark {
			rotate: 0deg;
		}
	}

	/* Portrait, the tab and the list it opens carry no ground of their own and the page reads through
	   them. Their rule, their shadow and their ink are unchanged. */
	@media (orientation: portrait) and (width < 64rem) {
		.entries,
		.toggle {
			background: transparent;
		}
	}

	/*
	 * Wide: the column beside the reading, following the reader down it. The hairline runs the whole
	 * list and the entry being read covers its own stretch of it in the accent, so the mark is part
	 * of the same line rather than a second one beside it.
	 */
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
