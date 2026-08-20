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
	family="team_stats"
	title="How team stat models work"
	description="How the points, rebounds, assists and three-pointers one NBA team records in a game are predicted, and how accurate the models are."
>
	{#snippet overview()}
		<p>This section is not written yet.</p>
	{/snippet}
</FamilyAbout>
