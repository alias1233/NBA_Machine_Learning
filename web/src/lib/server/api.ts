import { env } from '$env/dynamic/private';
import { error } from '@sveltejs/kit';

import type {
	GamePredictionRequest,
	ScoredModel,
	Health,
	MetricDefinition,
	Model,
	Player,
	PlayerPredictionRequest,
	Prediction,
	Roster,
	ScheduledGame,
	Showcase,
	TeamPredictionRequest
} from '$lib/types';

const DEFAULT_URL = 'http://127.0.0.1:8000';

/** Default timeout for a request to the service, in milliseconds. */
const PATIENCE = 15_000;

function baseUrl(): string {
	return (env.NBA_API_URL || DEFAULT_URL).replace(/\/+$/, '');
}

/** Gets the error `detail` from a FastAPI response. */
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

	// A timeout and a refused connection both become a 503.
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

/** Returns the definitions of the evaluation metrics the models use. */
export const getMetricDefinitions = () => request<MetricDefinition[]>('/models/metrics');

/** Returns every model in a family with its evaluation results. */
export const getScoredModels = (family: string) =>
	request<ScoredModel[]>(`/models/${encodeURIComponent(family)}/info`);

/** Returns the day's sample predictions, or null if none have been published yet. */
export const getShowcase = () => request<Showcase | null>('/showcase', { patience: 2_000 });

export const getPlayer = (id: number) => request<Player>(`/players/${id}`);

/** Returns both teams' rosters for a game, away team first. */
export const getRosters = (gameId: number) => request<Roster[]>(`/games/${gameId}/rosters`);

/** Returns the games that can be predicted right now, soonest first. */
export const getUpcomingGames = () => request<ScheduledGame[]>('/games/upcoming');

export function searchPlayers(search: string, limit = 10) {
	const query = new URLSearchParams({ search, limit: String(limit) });

	return request<Player[]>(`/players?${query}`);
}

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
