/**
 * Whether this process is still serving. Read by the container's health check and nothing else.
 *
 * It calls no service and renders no page, so it answers only the question it is asked: the Node
 * server is up and its router is running. Whether the prediction service can answer is `/health`,
 * which the proxy sends straight there.
 */

export const GET = () =>
	new Response('ok\n', {
		headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store' }
	});
