<script lang="ts">
	import FamilyAbout from '$lib/components/FamilyAbout.svelte';

	let { data } = $props();
</script>

<FamilyAbout
	families={data.families}
	family="player_stats"
	title="Player game statistics, how it works"
	description="How points, rebounds and assists are predicted for one NBA player, and how accurate it is."
/>
