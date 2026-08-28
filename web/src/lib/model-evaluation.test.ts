import { winner } from './model-evaluation.ts';

const metric = {
	key: 'example',
	label: 'Example',
	unit: 'probability' as const,
	higher_is_better: true
};

function expect(actual: unknown, expected: unknown) {
	if (actual !== expected) throw new Error(`Expected ${expected}, received ${actual}`);
}

expect(winner({ ...metric, value: 0.81, floor: 0.75, ideal: 0.8 }), 'model');
expect(winner({ ...metric, value: 0.9, floor: 0.81, ideal: 0.8 }), 'baseline');
expect(winner({ ...metric, value: 0.79, floor: 0.81, ideal: 0.8 }), null);
expect(winner({ ...metric, value: 0.21, floor: 0.2, ideal: null }), 'model');
