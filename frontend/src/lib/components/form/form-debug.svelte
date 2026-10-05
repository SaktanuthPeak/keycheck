<script lang="ts">
	import { dev } from '$app/environment';
	import SuperDebug from 'sveltekit-superforms';

	let { formData } = $props();
</script>

{#if dev}
	<div class="my-3">
		<SuperDebug data={formData} />
	</div>
{/if}
