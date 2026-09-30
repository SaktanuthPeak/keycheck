<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import * as Form from '$lib/components/ui/form/index.js';
	import * as Field from '$lib/components/ui/field/index.js';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 } from 'sveltekit-superforms/adapters';
	import { loginSchema } from '../schema';
	import { toast } from 'svelte-sonner';
	import client from '$lib/api/client';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth.svelte';

	function extractErrorMessage(error: any): string {
		if (typeof error === 'object' && error !== null) {
			if ('message' in error && typeof error.message === 'string') return error.message;
			if ('detail' in error && typeof error.detail === 'string') return error.detail;
			if ('errors' in error && Array.isArray(error.errors) && error.errors[0]?.msg)
				return error.errors[0].msg;
		}
		return 'Invalid credentials or server error';
	}

	async function handleLoginSuccess(loginData: any, meData: any) {
		authStore.login(loginData, {
			username: meData.username,
			name: meData.name,
			id: meData.id,
			role: meData.role,
			is_active: meData.is_active,
			email: meData.email,
			last_login_date: meData.last_login_date,
			created_at: meData.created_at
		});
		await goto('/home');
	}

	const form = superForm(defaults(zod4(loginSchema)), {
		SPA: true,
		validators: zod4(loginSchema),
		resetForm: false,
		onUpdate: async ({ form }) => {
			if (!form.valid) {
				toast.error('Form not valid. Please check the fields.');
				return;
			}

			await toast.promise(
				(async () => {
					const { data: loginData, error: loginError } = await client.POST('/v1/auth/login', {
						body: { ...form.data, strategy: 'cookies' }
					});

					if (loginError) {
						throw new Error(extractErrorMessage(loginError));
					}
					if (!loginData) throw new Error('No login data received');

					reset();

					const { data: meData } = await client.GET('/v1/users/me', {
						headers: { Authorization: `Bearer ${loginData.access_token}` }
					});
					if (!meData) throw new Error('Failed to retrieve user data');

					await handleLoginSuccess(loginData, meData);
				})(),
				{
					loading: 'Logging in...',
					success: 'Login successful!',
					error: () => 'Login Failed'
				}
			);
		}
	});
	const { form: formData, submitting, reset } = form;
</script>

<Card.Root class="mx-auto w-full max-w-sm">
	<Card.Header>
		<Card.Title class="text-2xl">Login</Card.Title>
		<Card.Description>Enter your credentials to access your account</Card.Description>
	</Card.Header>
	<Card.Content>
		<form method="POST" use:form.enhance>
			<Field.FieldGroup>
				<Form.Field {form} name="username">
					<Form.Control>
						{#snippet children({ props })}
							<Form.Label>Username</Form.Label>
							<Input {...props} bind:value={$formData.username} />
						{/snippet}
					</Form.Control>
					<Form.FieldErrors />
				</Form.Field>
				<Form.Field {form} name="password">
					<Form.Control>
						{#snippet children({ props })}
							<Form.Label>Password</Form.Label>
							<Input
								{...props}
								type="password"
								bind:value={$formData.password}
								placeholder="Enter your password"
							/>
						{/snippet}
					</Form.Control>
					<Form.FieldErrors />
				</Form.Field>
				<Form.Button disabled={$submitting}>Login</Form.Button>
			</Field.FieldGroup>
		</form>
	</Card.Content>
</Card.Root>
