<script lang="ts">
	type Question = {
		question: string;
		answer: string[];
	};

	type Props = {
		questions: Question[];
		/** Name for the details group, so two FAQs on one page open and close separately. */
		name: string;
	};

	let { questions, name }: Props = $props();
</script>

<ul class="questions">
	{#each questions as { question, answer } (question)}
		<li class="panel">
			<details name="{name}-question">
				<summary>
					<h3>{question}</h3>

					<svg class="mark" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
						<path d="M5 9 L12 16 L19 9" />
					</svg>
				</summary>

				<div class="answers">
					{#each answer as paragraph}
						<p class="small answer">{paragraph}</p>
					{/each}
				</div>
			</details>
		</li>
	{/each}
</ul>

<style>
	.questions {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: 0;
		list-style: none;
	}

	.questions > li {
		padding: 0;
		transition: border-top-color var(--motion-fast) var(--ease-in);
	}

	.questions > li:has(summary:hover),
	.questions > li:has(summary:focus-visible) {
		border-top-color: var(--plane-accent);
	}

	summary {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		min-height: var(--tap-target);
		padding: var(--space-5);
		cursor: pointer;
	}

	.answers {
		padding-block-end: var(--space-4);
	}

	.answer {
		padding: 0 var(--space-5) var(--space-3);
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

	details[open] .mark {
		rotate: 180deg;
	}
</style>
