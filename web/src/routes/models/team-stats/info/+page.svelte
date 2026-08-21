<script lang="ts">
	import FamilyInfo from '$lib/components/FamilyInfo.svelte';

	let { data } = $props();
</script>

<FamilyInfo
	families={data.families}
	answering={data.health !== null}
	models={data.models}
	family="team_stats"
	title="Team stat models"
	description="Every team stat model and its evaluation metrics."
/>
