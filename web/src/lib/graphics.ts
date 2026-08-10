/**
 * The graphic on a model family's card, found by filename.
 *
 * An image under `assets/model_graphics/` named after the family it belongs to is drawn on that
 * family's card, so dropping the file in is the whole job. Any of png, jpg, jpeg or webp, resolved
 * when the site is built, and a family with no file keeps the placeholder.
 *
 * They are bundled rather than served from `static/`, so a missing graphic costs no request and a
 * present one is fingerprinted for caching.
 */

const FILES = import.meta.glob('./assets/model_graphics/*.{png,jpg,jpeg,webp}', {
	eager: true,
	query: '?url',
	import: 'default'
}) as Record<string, string>;

const BY_FAMILY = new Map(
	Object.entries(FILES).map(([path, url]) => [
		path.split('/').pop()!.replace(/\.[^.]+$/, ''),
		url
	])
);

/** @param family The family's `name`, which is what the file is named after. */
export const familyGraphic = (family: string) => BY_FAMILY.get(family) ?? null;
