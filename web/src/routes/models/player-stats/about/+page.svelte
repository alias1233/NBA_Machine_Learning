<script lang="ts">
	import FamilyAbout from '$lib/components/FamilyAbout.svelte';

	let { data } = $props();
</script>

<FamilyAbout
	families={data.families}
	models={data.models}
	family="player_stats"
	title="Player stat models, how it works"
	description="How points, rebounds and assists are predicted for one NBA player, and how accurate it is."
/>
