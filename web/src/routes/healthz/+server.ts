export const GET = () =>
	new Response('ok\n', {
		headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store' }
	});
