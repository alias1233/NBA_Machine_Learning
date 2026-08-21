<script lang="ts">
	import FamilyInfo from '$lib/components/FamilyInfo.svelte';

	let { data } = $props();
</script>

<FamilyInfo
	families={data.families}
	answering={data.health !== null}
	models={data.models}
	family="game_stats"
	title="Game stat models"
	description="Every game stat model and its evaluation metrics."
/>
