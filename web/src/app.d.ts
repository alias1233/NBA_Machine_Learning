// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	interface Window {
		dataLayer?: Record<string, unknown>[];
	}

	namespace App {
		interface Error {
			message: string;
			/** Reason code from the prediction service, if it sent one. */
			reason?: string;
		}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
