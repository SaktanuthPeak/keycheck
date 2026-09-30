<script>
	import client from '$lib/api/client';
	import Button from '$lib/components/ui/button/button.svelte';
	import { authStore } from '$lib/stores/auth.svelte';
	import { toast } from 'svelte-sonner';

	async function logout() {
		authStore.logout();
		await client.POST('/v1/auth/logout', {
			credentials: 'include'
		});
		toast.error('Logged out successfully');
	}
</script>

<Button variant="destructive" onclick={logout}>Logout</Button>
