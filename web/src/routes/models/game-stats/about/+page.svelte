<script lang="ts">
	import FamilyAbout from '$lib/components/FamilyAbout.svelte';

	let { data } = $props();
</script>

<FamilyAbout
	families={data.families}
	models={data.models}
	family="game_stats"
	title="Game statistics, how it works"
	description="How the winning margin and the total points of an NBA game are predicted, and how accurate it is."
/>
