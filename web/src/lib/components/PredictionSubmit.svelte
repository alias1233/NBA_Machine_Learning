<script lang="ts">
	import { flow } from '$lib/motion';

	type Props = {
		pending: boolean;
		missing: string;
	};

	let { pending, missing }: Props = $props();
</script>

<button
	class="button"
	type="submit"
	disabled={pending || missing !== ''}
	aria-describedby={missing && !pending ? 'submit-missing' : undefined}
>
	{pending ? 'Predicting' : 'Run a prediction'}
</button>

{#if missing && !pending}
	<p id="submit-missing" class="small muted" transition:flow>{missing}</p>
{/if}
