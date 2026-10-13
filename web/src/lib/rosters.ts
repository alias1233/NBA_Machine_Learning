import type { Player, Roster, ScheduledGame } from '$lib/types';

/** Side of the game a roster is for, on pages that have both. */
export type RosterSide = 'home' | 'away';

export const outParameter = (side?: RosterSide) => (side ? `${side}_out` : 'out');
export const joinedParameter = (side?: RosterSide) => (side ? `${side}_joined` : 'joined');

/** Query parameter that marks a roster as set by the user and not the suggested one. */
export const ROSTER_PARAMETER = 'roster';
export const ROSTER_VALUE = 'set';

/** Returns true if the URL has a user-set roster. */
export const isReadersRoster = (parameters: URLSearchParams) =>
	parameters.get(ROSTER_PARAMETER) === ROSTER_VALUE;

/** Fetches both teams' rosters for a game, with the expected lineup changes. */
export async function fetchRosters(gameId: number): Promise<Roster[]> {
	try {
		const response = await fetch(`/api/rosters?game=${gameId}`);

		return response.ok ? await response.json() : [];
	} catch {
		return [];
	}
}

/** Returns a team's roster, or undefined if it is not loaded yet. */
export const rosterOf = (rosters: Roster[], abbreviation: string): Roster | undefined =>
	rosters.find((roster) => roster.team.abbreviation === abbreviation);

/** Returns a team's players, or an empty list if the rosters are not loaded yet. */
export const playersOf = (rosters: Roster[], abbreviation: string): Player[] =>
	rosterOf(rosters, abbreviation)?.players ?? [];

/** Returns a team's expected lineup changes, using the field names the roster controls use. */
export const expectedOf = (roster: Roster | undefined) => ({
	out: roster?.without ?? [],
	joined: roster?.returning ?? []
});

/** Returns the expected lineup changes for a player's team. The player is never listed as out. */
export const expectedAround = (roster: Roster | undefined, playerId: number | null) => {
	const expected = expectedOf(roster);

	return {
		out: expected.out.filter(({ id }) => id !== playerId),
		joined: expected.joined
	};
};

/** Returns the away and home teams of a game with their side, so each roster control can be labeled. */
export const sidesOf = (
	game: ScheduledGame | null
): { side: RosterSide; team: ScheduledGame['home_team'] }[] =>
	game === null
		? []
		: [
				{ side: 'away', team: game.away_team },
				{ side: 'home', team: game.home_team }
			];
