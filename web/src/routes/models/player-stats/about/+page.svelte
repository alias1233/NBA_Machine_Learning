<script lang="ts">
	import FamilyAbout from '$lib/components/FamilyAbout.svelte';

	let { data } = $props();
</script>

<FamilyAbout
	families={data.families}
	answering={data.health !== null}
	models={data.models}
	family="player_stats"
	title="How player stat models work"
	description="How one NBA player's box score numbers are predicted, and how accurate the models are."
/>
