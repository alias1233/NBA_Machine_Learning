<!--
	The questions a reader arrives with, one panel each.

	A closed panel is its question and nothing else. Pressing one opens its answer and closes whichever
	was open, because two open answers are harder to read past than one. It opens with the same flow
	every region on the site opens with, so the page under it is carried rather than thrown.

	The question is the control's label, so the mark beside it says only which way the panel is going.
-->
<script lang="ts">
	import { flow } from '$lib/motion';

	type Question = {
		question: string;
		answer: string;
	};

	type Props = {
		questions: Question[];
		/** Names the answers, so two of these on one page cannot share an id. */
		name: string;
	};

	let { questions, name }: Props = $props();

	/** The question standing open, if one is. */
	let open = $state<string | null>(null);

	const answerId = (index: number) => `${name}-answer-${index}`;
</script>

<ul class="questions">
	{#each questions as { question, answer }, index (question)}
		{@const shown = open === question}

		<li class="panel">
			<h3>
				<button
					type="button"
					class="ask"
					aria-expanded={shown}
					aria-controls={shown ? answerId(index) : undefined}
					onclick={() => (open = shown ? null : question)}
				>
					<span>{question}</span>

					<svg class="mark" class:shown viewBox="0 0 24 24" aria-hidden="true" focusable="false">
						<path d="M5 9 L12 16 L19 9" />
					</svg>
				</button>
			</h3>

			{#if shown}
				<p id={answerId(index)} class="small answer" transition:flow>{answer}</p>
			{/if}
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

	.questions > li:has(.ask:hover),
	.questions > li:has(.ask:focus-visible) {
		border-top-color: var(--plane-accent);
	}

	/* The whole panel is the control. */
	.ask {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		width: 100%;
		min-height: var(--tap-target);
		padding: var(--space-5);
		background: none;
		border: none;
		text-align: start;
		cursor: pointer;
	}

	.answer {
		padding: 0 var(--space-5) var(--space-5);
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

	.mark.shown {
		rotate: 180deg;
	}
</style>
