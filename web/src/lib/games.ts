/**
 * Writing a scheduled game out for a reader, and reading the two ways it names when it is played.
 *
 * Dates cross the wire as YYYY-MM-DD and are the date the game is played on, so they are read as a
 * plain calendar day rather than a moment in time. A tip-off is a real moment and is sent in UTC.
 */

import type { ScheduledGame } from '$lib/types';

/*
 * Built once and reused. `toLocaleDateString` builds a formatter on every call, which measured 0.35ms
 * against 0.012ms for a reused one, and a list of games pays that per card. The reader's own locale
 * is read here rather than named, and it cannot change while the page is open.
 */
const DAY = new Intl.DateTimeFormat(undefined, {
	weekday: 'short',
	month: 'short',
	day: 'numeric'
});
const LONG_DAY = new Intl.DateTimeFormat(undefined, { dateStyle: 'long' });
const FULL_DAY = new Intl.DateTimeFormat(undefined, {
	weekday: 'long',
	month: 'long',
	day: 'numeric'
});
const TIME = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' });

/*
 * A game is filed under its United States eastern date, which is the date its box score is written
 * under, so that is the day the site means by today whatever the reader's or the server's clock
 * says. `en-CA` is the one common locale that writes a date the way the wire does. The rule is the
 * same one `python/src/nba_ml/season.py` states, and the two have to agree or a set built this
 * morning reads as yesterday's for five hours.
 */
const GAME_DAY = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York' });

/** Today, as the schedule counts days: YYYY-MM-DD in United States eastern time. */
export const gameDayNow = (at: number | Date = Date.now()) => GAME_DAY.format(at);

/**
 * A moment the service sent, as milliseconds, which is UTC whether or not it wrote the zone down.
 *
 * The same rule the collector reads a tip-off by, in `python/src/nba_ml/upcoming.py`. Left to the
 * browser, a moment with no zone on it is read as the reader's own, which moves a tip-off by
 * however far from UTC they happen to be. NaN where there is no moment to read.
 */
export const utcMoment = (iso: string) =>
	Date.parse(/(?:Z|[+-]\d\d:?\d\d)$/.test(iso) ? iso : `${iso}Z`);

export const gameDay = (date: string) => DAY.format(new Date(`${date}T00:00:00`));

export const longGameDay = (date: string) => LONG_DAY.format(new Date(`${date}T00:00:00`));

export const tipoffTime = (game: ScheduledGame) =>
	game.tipoff ? TIME.format(utcMoment(game.tipoff)) : null;

/** The day and the tip-off on one line, which is the top row of a game card. */
export const gameWhen = (game: ScheduledGame) =>
	[gameDay(game.date), tipoffTime(game)].filter(Boolean).join(', ');

/** The day written out with its weekday, which is how the game a form is about names itself. */
export const fullGameDay = (date: string) => FULL_DAY.format(new Date(`${date}T00:00:00`));

/** The day and the tip-off written out in full, for the head above a prediction's parameters. */
export const gameWhenFull = (game: ScheduledGame) =>
	[fullGameDay(game.date), tipoffTime(game)].filter(Boolean).join(', ');

/**
 * The days a board is dealing, which is what its head names beside the count.
 *
 * A slate almost always covers one day. Where it covers more, the first and the last are what say
 * how far ahead the board reaches, and the days between them are on the cards themselves.
 */
export function slateDays(games: ScheduledGame[]): string {
	const days = [...new Set(games.map(({ date }) => date))].sort();

	if (days.length === 0) return '';

	return days.length === 1 ? gameDay(days[0]) : `${gameDay(days[0])} to ${gameDay(days[days.length - 1])}`;
}
