/**
 * The two ad slots, and whether ads run at all.
 *
 * Off until a consent banner exists. While it is off a
 * slot renders nothing: no label, no reserved box, no gap. Turning it on is this one line.
 */

export const ADS_ENABLED = false;

/** There are two slots and no more. A third needs the user's agreement first. */
export const AD_SLOTS = {
	homeModels: 'ad-home-models',
	modelBelowResult: 'ad-model-below-result'
} as const;
