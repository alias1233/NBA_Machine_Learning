<!--
	What a reader can do here, printed at the foot of the home page.

	The hero shows the site answering and the Models section is the way in. Neither says what any of
	it costs, how current it is, or what happens after the button is pressed, and this is the one
	place on the home page that does. It is standing prose: the hero's words change every morning
	with the samples, and everything else on the page is the header, the footer and the model
	catalog, all of which is printed on every other page too.

	It is not the About page's opening. That says what the site is and teaches reading one answer, so
	this does not define the site again. It takes the reader's own side of it instead: what it costs,
	how fresh it is, and the four steps between landing here and holding a prediction.

	The four steps are drawn as a flight of stairs, because that is what the heading says they are.
	Every tread is set in from the one above it and printed one plane deeper, so the run descends to
	the right and the numbers down its leading edge are the composition. The last tread is block
	paper, which is the plane a prediction page reads its answer on, so the descent ends on the
	ground the reader is being walked to.

	The section opens with the heading and what the site costs standing side by side, which is the
	landing the stairs start from.
-->
<script lang="ts">
	import { MODELS_PATH } from '$lib/models';
	import { SITE_NAME } from '$lib/site';
</script>

<section class="band brief" id="how-to-predict">
	<div class="page inside">
		<div class="head">
			<h2 class="page-title type-h1">Free NBA predictions, in four steps</h2>

			<p class="statement measure">
				{SITE_NAME}
				is free to use and asks nobody to sign in. Every answer on it is about a game that has not
				been played yet, and the games behind that answer are collected every hour of a game day, so
				a prediction is made on the season as it stands right now.
			</p>
		</div>

		<ol class="flight">
			<li class="tread">
				<span class="number figure-lead" aria-hidden="true"></span>
				<h3 class="type-h2">Choose a category</h3>
				<p class="muted">
					One player's own line, one team's line, or the game itself. A category is the thing a
					request has to name, and the
					<a href={MODELS_PATH}>three frames above</a>
					are all of them.
				</p>
			</li>
			<li class="tread">
				<span class="number figure-lead" aria-hidden="true"></span>
				<h3 class="type-h2">Pick the game</h3>
				<p class="muted">
					Every upcoming game the models can already read is dealt onto the board at the top of the
					page. Pick one, and the rest of the page is about that game.
				</p>
			</li>
			<li class="tread">
				<span class="number figure-lead" aria-hidden="true"></span>
				<h3 class="type-h2">Say what to predict</h3>
				<p class="muted">
					Name the statistic, and the player or team the category asks for. Who is expected to play
					is filled in for you, injuries and trades included, and you are free to take somebody out,
					put somebody in, and ask again.
				</p>
			</li>
			<!-- The one tread that changes paper, so it names its plane here rather than in the ladder
			     below. The three above it are tints of the page and need nothing but a tone. -->
			<li class="tread block-plane">
				<span class="number figure-lead" aria-hidden="true"></span>
				<h3 class="type-h2">Read the whole answer</h3>
				<p class="muted">
					The answer is drawn as a chart, and the line across it is yours to move. Every figure
					beside it follows the line, so the number you read is the one you asked about rather than
					the one the page opened on.
				</p>
			</li>
		</ol>
	</div>
</section>

<style>
	/*
	 * The one stretch of the home page that is nothing but text, so it is given room on the page
	 * plane rather than a frame of its own.
	 *
	 * Held well clear of the listing above it, which stands exactly one screen tall. A reader leaves
	 * that screen, passes a stretch of open page, and only then finds the site talking again, so this
	 * is somewhere they arrive rather than the next thing stacked under the frames.
	 */
	.brief {
		padding-block: calc(var(--space-8) + var(--space-6)) var(--space-7);
	}

	/* The stairs are set against the page column, so their descent keeps its shape once the column
	   has stopped growing rather than carrying on across a wide screen. */
	.inside {
		display: flex;
		container-type: inline-size;
		flex-direction: column;
		gap: var(--space-6);
	}

	.head {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.head h2 {
		text-wrap: balance;
	}

	/* What the site is worth knowing before any of the steps. Everything under it is one of them. */
	.statement {
		font-size: var(--type-note);
	}

	/*
	 * The flight. Treads meet with nothing between them, so the four read as one stepped mass cut out
	 * of the page rather than as four bars lying on it.
	 */
	.flight {
		display: grid;
		margin: 0;
		padding: 0;
		list-style: none;
		counter-reset: step;
		/* How far one tread is set in from the one above it. */
		--tread: clamp(0.75rem, 3.2cqi, 3.5rem);
	}

	/* The number leads the tread and the step's name stands beside it. Narrow, what the step means
	   drops under both rather than squeezing into a third of the width. */
	.tread {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		align-content: center;
		align-items: baseline;
		gap: var(--space-3) var(--space-4);
		padding: var(--space-5);
		counter-increment: step;
	}

	.tread p {
		grid-column: 1 / -1;
	}

	.tread:nth-child(2) {
		margin-inline-start: var(--tread);
	}

	.tread:nth-child(3) {
		margin-inline-start: calc(var(--tread) * 2);
	}

	.tread:nth-child(4) {
		margin-inline-start: calc(var(--tread) * 3);
	}

	/* The tint ladder, one plane deeper a step. Square cut, because a tread is a field of a printed
	   composition and not an object lying on the page. */
	.tread:nth-child(1) {
		background: var(--surface);
	}

	.tread:nth-child(2) {
		background: var(--panel);
	}

	.tread:nth-child(3) {
		background: var(--surface-sunken);
	}

	/* The tread's number, set in the face every figure on the site takes and given the size a lead
	   figure takes. It counts itself, so the order is never written down twice, and the list carries
	   it to a screen reader either way. */
	.number::before {
		content: counter(step, decimal-leading-zero);
	}

	/*
	 * Wide: the number, the step and what it means stand in one row, all three hung off the number's
	 * baseline. The numbers then step down and in along the leading edge of the flight, which is the
	 * whole of what makes the four read as stairs rather than as four bars.
	 */
	@media (min-width: 64rem) {
		/* Every riser the same, because a flight with four different ones is not one a reader can
		   walk. Only where all four are on the screen at once: narrower, a tread taking the height of
		   the deepest is a screen of empty paper nobody can see the shape of anyway. */
		.flight {
			grid-auto-rows: 1fr;
		}

		.head {
			display: grid;
			grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
			align-items: end;
			gap: var(--space-6);
		}

		.tread {
			grid-template-columns: auto minmax(0, 0.8fr) minmax(0, 1.2fr);
			gap: var(--space-5);
			padding: var(--space-6);
		}

		.tread p {
			grid-column: auto;
		}
	}
</style>
