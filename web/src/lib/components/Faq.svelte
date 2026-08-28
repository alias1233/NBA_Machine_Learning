<!--
	The questions a reader arrives with, one panel each.

	Every answer is in the document whether its panel is folded open or not. The page publishes the
	same questions and answers as structured data, so an answer the document did not contain would be
	describing content that is not there, and a search engine reads that as a claim rather than as an
	answer.

	A closed panel shows its question and nothing else. Pressing one opens its answer and closes
	whichever was open, because two open answers are harder to read past than one, which the panels
	do between themselves by sharing a name.

	The question is the control's label, so the mark beside it says only which way the panel is going.
-->
<script lang="ts">
	type Question = {
		question: string;
		answer: string[];
	};

	type Props = {
		questions: Question[];
		/** Names the group, so two of these on one page fold independently. */
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

	/* The panel carries no padding of its own, because the question and its answer each need their
	   own, and the accent arrives on the top edge, which is what a container that does something
	   looks like on the rest of the site. */
	.questions > li {
		padding: 0;
		transition: border-top-color var(--motion-fast) var(--ease-in);
	}

	.questions > li:has(summary:hover),
	.questions > li:has(summary:focus-visible) {
		border-top-color: var(--plane-accent);
	}

	/* The whole question is the control. */
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
