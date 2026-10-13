<script lang="ts">
	import AnswerBlock from '$lib/components/AnswerBlock.svelte';

	import type { Answer, Distribution } from '$lib/odds';
	import type { ModelOutput } from '$lib/types';

	const CENTER = 24;
	const SPREAD = 7;
	const OUTCOMES = 55;

	const weights = Array.from({ length: OUTCOMES }, (_, points) =>
		Math.exp(-((points - CENTER) ** 2) / (2 * SPREAD ** 2))
	);
	const total = weights.reduce((running, weight) => running + weight, 0);

	const EXAMPLE: Distribution = {
		minimumValue: 0,
		bucketWidth: 1,
		impossibleValue: null,
		probabilities: weights.map((weight) => weight / total)
	};

	const ANSWER: Answer = { kind: 'integer_distribution', distribution: EXAMPLE };

	const OUTPUT: ModelOutput = {
		kind: 'integer_distribution',
		minimum_value: EXAMPLE.minimumValue,
		outcomes: EXAMPLE.probabilities.length,
		bucket_width: EXAMPLE.bucketWidth,
		impossible_value: EXAMPLE.impossibleValue
	};

	const LINE = CENTER;

	/** Number of notes placed on the left side. */
	const LEFT_COLUMN = 3;

	const NOTES = [
		{
			part: 'lead',
			term: 'Expected',
			body: 'The expected value of the predicted statistic. On average, this value would be the closest to the true statistic.'
		},
		{
			part: 'chart',
			term: 'The chart',
			body: 'One bar for every outcome the model can answer with. The taller the bar, the likelier that outcome.'
		},
		{
			part: 'line',
			term: 'The line',
			body: 'Sets the line for calculating the under, push, and over values.'
		},
		{
			part: 'under',
			term: 'Under',
			body: 'The total probability the real result comes in below the line. It is the total sum of the probabilities of outcomes lower than the line.'
		},
		{
			part: 'push',
			term: 'Push',
			body: 'The chance the real result is exactly the line value. Only whole numbers can be landed on, so a line of 24.5 always reads 0 percent.'
		},
		{
			part: 'over',
			term: 'Over',
			body: 'The total probability the real result comes in above the line. It is the total sum of the probabilities of outcomes greater than the line.'
		}
	];

	type Leader = { x1: number; y1: number; x2: number; y2: number };
	type Box = { left: number; right: number; top: number; bottom: number };

	/** Distance in pixels a leader line ends inside its target. */
	const REACH = 4;

	let frame = $state<HTMLElement>();
	let subject = $state<HTMLElement>();
	let leaders = $state<Leader[]>([]);

	const labels: HTMLElement[] = [];

	const clamp = (value: number, low: number, high: number) =>
		Math.min(Math.max(value, low), high);

	/** Shrinks a box on every side, but never past its center. */
	function inset(box: Box, by: number): Box {
		const x = Math.min(by, (box.right - box.left) / 2);
		const y = Math.min(by, (box.bottom - box.top) / 2);

		return { left: box.left + x, right: box.right - x, top: box.top + y, bottom: box.bottom - y };
	}

	/** Returns the label's box without its padding. */
	function words(label: HTMLElement): Box {
		const box = label.getBoundingClientRect();
		const { paddingLeft, paddingRight, paddingTop, paddingBottom } = getComputedStyle(label);

		return {
			left: box.left + parseFloat(paddingLeft),
			right: box.right - parseFloat(paddingRight),
			top: box.top + parseFloat(paddingTop),
			bottom: box.bottom - parseFloat(paddingBottom)
		};
	}

	/** Returns the shortest line between a label and the part it points to. */
	function shortest(label: Box, part: Box): Leader {
		const x2 = clamp((label.left + label.right) / 2, part.left, part.right);
		const y2 = clamp((label.top + label.bottom) / 2, part.top, part.bottom);

		return {
			x1: clamp(x2, label.left, label.right),
			y1: clamp(y2, label.top, label.bottom),
			x2,
			y2
		};
	}

	function measure() {
		if (!frame || !subject) return;

		const box = frame.getBoundingClientRect();

		leaders = NOTES.flatMap((note, index) => {
			const label = labels[index];
			const part = subject?.querySelector(`[data-explain="${note.part}"]`);

			if (!label || !part) return [];

			const drawn = shortest(words(label), inset(part.getBoundingClientRect(), REACH));

			return [
				{
					x1: drawn.x1 - box.left,
					y1: drawn.y1 - box.top,
					x2: drawn.x2 - box.left,
					y2: drawn.y2 - box.top
				}
			];
		});
	}

	// ResizeObserver calls measure once when it starts observing.
	$effect(() => {
		if (!frame || !subject) return;

		const watch = new ResizeObserver(measure);

		watch.observe(frame);
		watch.observe(subject);

		return () => watch.disconnect();
	});
</script>

<div class="frame" bind:this={frame}>
	<svg class="leaders" aria-hidden="true">
		{#each leaders as leader}
			<line x1={leader.x1} y1={leader.y1} x2={leader.x2} y2={leader.y2} />
		{/each}
	</svg>

	<div class="subject" bind:this={subject}>
		<AnswerBlock
			answer={ANSWER}
			output={OUTPUT}
			loading={false}
			stat="points"
			heading="John Basketball, points"
			headingLevel={3}
			subheading="AWAY TEAM at HOME TEAM, January 23, 2006"
			openOn={LINE}
			example
			customRoster={false}
			pastGames={null}
		/>
	</div>

	{#each NOTES as note, index (note.part)}
		<dl
			class="note"
			class:right={index >= LEFT_COLUMN}
			style="--row: {(index % LEFT_COLUMN) + 1}"
			bind:this={labels[index]}
		>
			<dt class="micro">{note.term}</dt>
			<dd class="small muted">{note.body}</dd>
		</dl>
	{/each}
</div>

<style>
	.frame {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--space-5);
	}

	.subject {
		width: var(--answer-column);
		max-width: 100%;
		justify-self: center;
	}

	.note {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		max-width: 24rem;
		padding: var(--space-2);
		background: var(--page);
	}

	.note dd {
		margin: 0;
	}

	.leaders {
		display: none;
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		pointer-events: none;
	}

	.leaders line {
		stroke: var(--leader);
		stroke-width: 1;
	}

	@media (min-width: 40rem) {
		.frame {
			grid-template-columns: repeat(2, minmax(0, 1fr));
			gap: var(--space-6);
		}

		.subject {
			grid-column: 1 / -1;
		}
	}

	@media (min-width: 64rem) {
		.leaders {
			display: block;
		}

		.frame {
			grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
			grid-template-rows: repeat(3, auto);
			align-items: center;
		}

		.subject {
			grid-area: 1 / 2 / -1 / 3;
			align-self: start;
		}

		.note {
			grid-row: var(--row);
			grid-column: 1;
			justify-self: end;
			max-width: 100%;
			text-align: right;
		}

		.note.right {
			grid-column: 3;
			justify-self: start;
			text-align: left;
		}
	}
</style>
