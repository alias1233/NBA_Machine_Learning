<!--
	The answer block as a drawing, which is how the About page teaches reading a prediction.

	It is the block a prediction page draws, at the width it draws it, holding a made-up answer. The
	line drags and the odds answer it, so a reader learns the block by moving it, and it can never
	fall out of step with the real thing because it is the real thing. It carries no footer, because
	its way out leads to the section it is already standing in, and it writes no line into the address
	bar, because nothing here was asked for.

	The terms sit around it. On a wide page, a hairline leader runs from each to the part it names. A
	leader is the shortest segment from the words of a term to just inside that part, measured off the
	page rather than drawn by hand. On a narrower page, the terms follow the block without leaders.

	A part names itself with `data-explain`, which is the whole of what the real components carry for
	this. Grep that attribute to find them.
-->
<script lang="ts">
	import AnswerBlock from '$lib/components/AnswerBlock.svelte';

	import type { Answer, Distribution } from '$lib/odds';
	import type { ModelOutput } from '$lib/types';

	/** A made-up points answer, shaped like the ones a player model gives: a chance per whole number. */
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

	// The shape a model would have declared, read off the answer rather than written twice, because
	// the block takes what the figure is called from the model and what it draws from the answer.
	const OUTPUT: ModelOutput = {
		kind: 'integer_distribution',
		minimum_value: EXAMPLE.minimumValue,
		outcomes: EXAMPLE.probabilities.length,
		bucket_width: EXAMPLE.bucketWidth,
		impossible_value: EXAMPLE.impossibleValue
	};

	// A whole number rather than the half one a real answer opens on, so all three odds carry a
	// figure and the push this names is worth reading.
	const LINE = CENTER;

	/** Which column a term sits in on a wide page. The first three take the left of the block. */
	const LEFT_COLUMN = 3;

	// Read down the left of the block and then down its right, which is the order the parts they name
	// run in. The three odds keep the order they are read in everywhere else on the site.
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

	/** How far inside the part a leader ends, so it lands on the thing rather than beside it. */
	const REACH = 4;

	let frame = $state<HTMLElement>();
	let subject = $state<HTMLElement>();
	let leaders = $state<Leader[]>([]);

	// Plain, because nothing reads them except the measuring below.
	const labels: HTMLElement[] = [];

	const clamp = (value: number, low: number, high: number) =>
		Math.min(Math.max(value, low), high);

	/** A box brought in on every side, never past its own middle. */
	function inset(box: Box, by: number): Box {
		const x = Math.min(by, (box.right - box.left) / 2);
		const y = Math.min(by, (box.bottom - box.top) / 2);

		return { left: box.left + x, right: box.right - x, top: box.top + y, bottom: box.bottom - y };
	}

	/** The words rather than the box drawn around them, so a leader starts where the sentence ends. */
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

	/**
	 * The two ends of the shortest segment between a label and the part it names.
	 *
	 * Clamping the label's center into the part gives the nearest point on the part, and clamping that
	 * back into the label gives the nearest point on the label. One rule, so a leader points the same
	 * way whether the label sits beside the block or under it, and reaches the edge of neither box.
	 */
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

	// A resize is every reason the two boxes move: the viewport and a font arriving. The observer
	// measures on its own first call, so nothing else has to run one.
	$effect(() => {
		if (!frame || !subject) return;

		const watch = new ResizeObserver(measure);

		watch.observe(frame);
		watch.observe(subject);

		return () => watch.disconnect();
	});
</script>

<div class="frame" bind:this={frame}>
	<!-- Behind the labels, so a leader passing one runs under its words rather than through them. -->
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
	/*
	 * One grid holding the block and every term, so a leader between any two of them is measured
	 * inside one box. A phone gets one column, a tablet two under the block, and a page wide enough
	 * for the composition sets the terms either side of it.
	 */
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

	/* Positioned and on the page tone, so a leader running past a term passes under its words rather
	   than through them. The block is in the flow and the leaders are over it, and positioning these
	   is what puts them over the leaders in turn. The padding keeps a line off the letters as well as
	   off the box. */
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

	/* Over the block, under the terms, and taking no presses, so the block below works exactly as it
	   does on a prediction page. */
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

		/* Each term shrinks to its own words and sits against the block, so a leader starts where the
		   sentence ends rather than at the edge of an empty column. */
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
