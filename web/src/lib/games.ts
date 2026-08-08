/**
 * Writing a scheduled game out for a reader.
 *
 * Dates cross the wire as YYYY-MM-DD and are the date the game is played on, so they are read as a
 * plain calendar day rather than a moment in time. A tip-off is a real moment and is sent in UTC.
 */

import type { ScheduledGame } from '$lib/types';

export const gameDay = (date: string) =>
	new Date(`${date}T00:00:00`).toLocaleDateString(undefined, {
		weekday: 'short',
		month: 'short',
		day: 'numeric'
	});

export const longGameDay = (date: string) =>
	new Date(`${date}T00:00:00`).toLocaleDateString(undefined, { dateStyle: 'long' });

export const tipoffTime = (game: ScheduledGame) =>
	game.tipoff
		? new Date(game.tipoff).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
		: null;

/** The day and the tip-off on one line, which is the top row of a game card. */
export const gameWhen = (game: ScheduledGame) =>
	[gameDay(game.date), tipoffTime(game)].filter(Boolean).join(', ');
