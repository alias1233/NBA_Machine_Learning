import type { Metric } from '$lib/types';

export type MetricWinner = 'model' | 'baseline' | null;

const displayed = (value: number, unit: Metric['unit']) =>
	Number((unit === 'probability' ? value * 100 : value).toFixed(unit === 'probability' ? 1 : 3));

/** Formats a metric value based on its unit. */
export function figure(value: number, unit: Metric['unit']): string {
	const valueAsShown = displayed(value, unit);

	if (unit === 'probability') return `${valueAsShown.toFixed(1)}%`;

	return valueAsShown.toFixed(3);
}

/** Returns whether the model or the baseline has the better displayed value, or null if they tie or there is no baseline. */
export function winner(metric: Metric): MetricWinner {
	if (metric.floor === null) return null;

	const mine = displayed(metric.value, metric.unit);
	const theirs = displayed(metric.floor, metric.unit);

	if (mine === theirs) return null;

	if (metric.ideal !== null) {
		const ideal = displayed(metric.ideal, metric.unit);
		const mineDistance = Math.abs(mine - ideal);
		const theirDistance = Math.abs(theirs - ideal);

		if (mineDistance === theirDistance) return null;

		return mineDistance < theirDistance ? 'model' : 'baseline';
	}

	const ahead = metric.higher_is_better ? mine > theirs : mine < theirs;

	return ahead ? 'model' : 'baseline';
}
