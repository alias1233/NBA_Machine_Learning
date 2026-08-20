/**
 * What every prediction page that reads a roster shares.
 *
 * A roster arrives with the lineup the collected injury report and roster snapshot expects, so the
 * controls open on who will actually play rather than on an empty form. Those names are the
 * reader's from the moment they appear: they sit in the same fields, submit as the same parameters,
 * and can be removed or added to like any name the reader typed.
 *
 * The whole roster is carried in the address bar, so a prediction made with a changed one is still
 * a shareable link. A page about one player names one team's roster, so its parameters are `out`
 * and `joined`. A page about a team or a whole game names both sides, because one row carries what
 * the side it faces has available too, so each parameter says which side it belongs to.
 */

import type { Player, Roster, ScheduledGame } from '$lib/types';

/** Which side of the game a roster belongs to, where a page carries both. */
export type RosterSide = 'home' | 'away';

export const outParameter = (side?: RosterSide) => (side ? `${side}_out` : 'out');
export const joinedParameter = (side?: RosterSide) => (side ? `${side}_joined` : 'joined');

/**
 * The parameter that marks a roster as the reader's own rather than the one the page suggested.
 *
 * Without it there is no telling a reader who cleared every name apart from a reader who has not
 * touched the fields, since both submit nothing. The button writes it with the rest of the form, so
 * a link carrying it is answered exactly as it reads, empty fields included, and a link without it
 * opens on whoever is expected to play.
 */
export const ROSTER_PARAMETER = 'roster';
export const ROSTER_VALUE = 'set';

/** Whether the address bar names the reader's own roster rather than the expected one. */
export const isReadersRoster = (parameters: URLSearchParams) =>
	parameters.get(ROSTER_PARAMETER) === ROSTER_VALUE;

/**
 * Both sides of a chosen game, each with the lineup change expected of it.
 *
 * Choosing a game card changes parameters without navigating, so the player lists it opens have to
 * be fetched rather than loaded. A game the schedule no longer holds answers with no sides, which a
 * page draws as a roster it cannot offer rather than as a failure.
 */
export async function fetchRosters(gameId: number): Promise<Roster[]> {
	try {
		const response = await fetch(`/api/rosters?game=${gameId}`);

		return response.ok ? await response.json() : [];
	} catch {
		return [];
	}
}

/** The named side's roster, or nothing while the rosters are still on their way. */
export const rosterOf = (rosters: Roster[], abbreviation: string): Roster | undefined =>
	rosters.find((roster) => roster.team.abbreviation === abbreviation);

/** The named side's players, or none while the rosters are still on their way. */
export const playersOf = (rosters: Roster[], abbreviation: string): Player[] =>
	rosterOf(rosters, abbreviation)?.players ?? [];

/**
 * The lineup change expected of one side, in the words the controls use.
 *
 * Empty for a side the page is not holding yet, and for one nothing collected says anything about,
 * which is the empty form every prediction was made with before any roster was collected.
 */
export const expectedOf = (roster: Roster | undefined) => ({
	out: roster?.without ?? [],
	joined: roster?.returning ?? []
});

/**
 * The lineup expected around one player, which is what a player page's roster fields open on.
 *
 * The player themselves is never sat out by it. A statistic is about somebody taking the floor, so a
 * suggestion that leaves them off is a question with no answer. A reader naming them out by hand is
 * still answered as they asked.
 */
export const expectedAround = (roster: Roster | undefined, playerId: number | null) => {
	const expected = expectedOf(roster);

	return {
		out: expected.out.filter(({ id }) => id !== playerId),
		joined: expected.joined
	};
};

/** Which side of the chosen game each roster belongs to, so a control can be labelled by its team. */
export const sidesOf = (
	game: ScheduledGame | null
): { side: RosterSide; team: ScheduledGame['home_team'] }[] =>
	game === null
		? []
		: [
				{ side: 'away', team: game.away_team },
				{ side: 'home', team: game.home_team }
			];
