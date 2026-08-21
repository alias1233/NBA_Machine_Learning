<script lang="ts">
	import FamilyInfo from '$lib/components/FamilyInfo.svelte';

	let { data } = $props();
</script>

<FamilyInfo
	families={data.families}
	answering={data.health !== null}
	models={data.models}
	family="player_stats"
	title="Player stat models"
	description="Every player stat model and its evaluation metrics."
/>
