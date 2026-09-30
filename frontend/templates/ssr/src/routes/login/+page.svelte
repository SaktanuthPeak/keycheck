<script lang="ts">
	import LoginForm from '$lib/features/login/components/form.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<div class="flex min-h-svh flex-col items-center justify-center gap-6 bg-muted p-6 md:p-10">
	<LoginForm form={data.form} />
</div>
