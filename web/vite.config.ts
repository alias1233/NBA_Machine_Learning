import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// Served by Node behind Caddy on one server. See docs/ARCHITECTURE.md.
			adapter: adapter()
		})
	],

	// Allowing cloudflare tunnel hosting
	server: {
		allowedHosts: [
			'pride-cow-attached-seattle.trycloudflare.com'
		]
	}
});
