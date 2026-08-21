/**
 * The one place the site talks to the prediction service.
 *
 * The service listens on the internal network and is never reachable from a browser, so every call
 * is made here, on the server. When the PostgreSQL prediction cache is built it is read in front of
 * `predictPlayerStat`, and nothing above this file has to change.
 *
 * A failed call throws SvelteKit's HttpError carrying the service's own message, and the reason the
 * service named when it refused. A loader that lets it bubble gets the error page. A loader that
 * wants to keep rendering catches it with `isHttpError` and words the reason for a reader.
 */

import { env } from '$env/dynamic/private';
import { error } from '@sveltejs/kit';

import type {
	GamePredictionRequest,
	FamilyInfoModel,
	Health,
	Model,
	ModelEvaluation,
	Player,
	PlayerPredictionRequest,
	Prediction,
	Roster,
	ScheduledGame,
	Showcase,
	TeamPredictionRequest
} from '$lib/types';

const DEFAULT_URL = 'http://127.0.0.1:8000';

/**
 * How long any call waits before it counts as the service not being there.
 *
 * A refused connection fails at once, but a service that has accepted the connection and then
 * stopped answering does not, and without this a page waits on it for as long as the platform's own
 * default, which is minutes. Well above a prediction, which takes about half a second and may queue
 * behind the cap, so nothing that would have answered is cut off. A caller with a tighter promise to
 * keep passes its own.
 */
const PATIENCE = 15_000;

function baseUrl(): string {
	return (env.NBA_API_URL || DEFAULT_URL).replace(/\/+$/, '');
}

/**
 * FastAPI reports a refusal as `detail`. It is a message, a list of validation problems, or, when
 * the service could not answer from what it holds, a reason and a message.
 */
async function refusalOf(response: Response): Promise<App.Error> {
	const detail = await response.json().then((body) => body?.detail, () => null);

	if (typeof detail === 'string') return { message: detail };
	if (Array.isArray(detail)) {
		return { message: detail.map((problem) => problem?.msg).filter(Boolean).join('. ') };
	}
	if (typeof detail?.message === 'string') {
		return { message: detail.message, reason: detail.reason };
	}

	return { message: `The prediction service answered ${response.status}.` };
}

async function request<T>(
	path: string,
	{ patience = PATIENCE, ...init }: RequestInit & { patience?: number } = {}
): Promise<T> {
	let response: Response;

	// A call that timed out and a call that was refused are the same thing to whoever asked: no
	// answer. Both leave here as a 503, so a loader wording one has only the one case to word.
	try {
		response = await fetch(baseUrl() + path, { signal: AbortSignal.timeout(patience), ...init });
	} catch {
		error(503, 'The prediction service is not reachable.');
	}

	if (!response.ok) error(response.status, await refusalOf(response));

	return response.json() as Promise<T>;
}

export const getHealth = () => request<Health>('/health');

export const getModels = () => request<Model[]>('/models');

/** The reader-facing model cards for one family Info page, without their figures. */
export const getFamilyInfoModels = (family: string) =>
	request<FamilyInfoModel[]>(`/models/${encodeURIComponent(family)}/info`);

/** What one model measured, asked for only when a reader opens that model. Null where unscored. */
export const getModelEvaluation = (family: string, model: string) =>
	request<ModelEvaluation | null>(
		`/models/${encodeURIComponent(family)}/info/${encodeURIComponent(model)}/evaluation`
	);

/**
 * The day's sample predictions, already built by a job.
 *
 * This is a file read on the service rather than a prediction, which is the whole point of it: the
 * home page shows real answers without a visitor's arrival costing a forward pass. Null where no set
 * has been published yet, which the page draws around rather than treating as a failure.
 *
 * Given far less patience than anything else here, because it is one file read and because the home
 * page has to render. Anything slower than this is the service being unable to answer, and the plate
 * is drawn without samples rather than the page waiting on it.
 */
export const getShowcase = () => request<Showcase | null>('/showcase', { patience: 2_000 });

export const getPlayer = (id: number) => request<Player>(`/players/${id}`);

/**
 * Both sides of a chosen game, away first, which is the order a matchup is written in.
 *
 * Each side arrives with the lineup change the collected roster and injury snapshot expects of it,
 * so the roster controls open on who will actually play rather than on an empty form.
 */
export const getRosters = (gameId: number) => request<Roster[]>(`/games/${gameId}/rosters`);

/**
 * The games that can be predicted right now, soonest first. A game stays off this list until every
 * earlier game of both its teams has been collected, because until then a model would read one of
 * the two teams as a game out of date.
 */
export const getUpcomingGames = () => request<ScheduledGame[]>('/games/upcoming');

export function searchPlayers(search: string, limit = 10) {
	const query = new URLSearchParams({ search, limit: String(limit) });

	return request<Player[]>(`/players?${query}`);
}

/** One prediction endpoint per family, because what a request has to name is what a family is. */
function predict(family: string, model: string, body: unknown) {
	return request<Prediction>(`/predictions/${family}/${encodeURIComponent(model)}`, {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: JSON.stringify(body)
	});
}

export const predictPlayerStat = (model: string, body: PlayerPredictionRequest) =>
	predict('player-stats', model, body);

export const predictTeamStat = (model: string, body: TeamPredictionRequest) =>
	predict('team-stats', model, body);

export const predictGameStat = (model: string, body: GamePredictionRequest) =>
	predict('game-stats', model, body);
