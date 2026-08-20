<script lang="ts">
	import FamilyAbout from '$lib/components/FamilyAbout.svelte';

	let { data } = $props();
</script>

<!--
	The overview is this page's own. Write it here, and add whole sections of this family's own with
	the component's `extra` prop.
-->
<FamilyAbout
	families={data.families}
	answering={data.health !== null}
	models={data.models}
	family="game_stats"
	title="How game stat models work"
	description="How the final margin, the winner and the combined totals of an NBA game are predicted, and how accurate the models are."
>
	{#snippet overview()}
		<p>This section is not written yet.</p>
	{/snippet}
</FamilyAbout>
