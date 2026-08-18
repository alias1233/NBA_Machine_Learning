<script lang="ts">
	import FamilyAbout from '$lib/components/FamilyAbout.svelte';

	let { data } = $props();
</script>

<FamilyAbout
	families={data.families}
	answering={data.health !== null}
	models={data.models}
	family="team_stats"
	title="How team stat models work"
	description="How the points one NBA team scores in a game are predicted, and how accurate the model is."
/>
