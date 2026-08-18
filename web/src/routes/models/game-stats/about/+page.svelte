<script lang="ts">
	import FamilyAbout from '$lib/components/FamilyAbout.svelte';

	let { data } = $props();
</script>

<FamilyAbout
	families={data.families}
	answering={data.health !== null}
	models={data.models}
	family="game_stats"
	title="How game stat models work"
	description="How the final margin, the total points and the winner of an NBA game are predicted, and how accurate the models are."
/>
