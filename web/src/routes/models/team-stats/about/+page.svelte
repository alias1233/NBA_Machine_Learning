<script lang="ts">
	import FamilyAbout from '$lib/components/FamilyAbout.svelte';

	let { data } = $props();
</script>

<FamilyAbout
	families={data.families}
	models={data.models}
	family="team_stats"
	title="Team stat models, how it works"
	description="How the points one NBA team scores in a game are predicted, and how accurate it is."
/>
