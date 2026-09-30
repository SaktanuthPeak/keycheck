<script lang="ts">
	import { superForm, type Infer, type SuperValidated } from 'sveltekit-superforms';
	import * as Card from '$lib/components/ui/card';
	import * as Form from '$lib/components/ui/form';
	import { loginSchema } from '$lib/features/login/schema';
	import { zod4Client } from 'sveltekit-superforms/adapters';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import FormDebug from '$lib/components/form/form-debug.svelte';
	import { toast } from 'svelte-sonner';

	type LoginFormProps = {
		form: SuperValidated<Infer<typeof loginSchema>>;
	};

	let { form: superform }: LoginFormProps = $props();

	const form = superForm(superform, {
		validators: zod4Client(loginSchema),
		resetForm: false,
		onResult: async ({ result }) => {
			if (result.type === 'redirect') {
				toast.success('Login Success!!');
			}
			if (result.type === 'error') {
				toast.error('Login Error', {
					description: 'An error occurred during login.'
				});
			}
			if (result.type === 'failure') {
				toast.error('Login Failed', {
					description: 'Please check your credentials and try again.'
				});
			}
		}
	});

	const { form: formData, enhance, submitting, message } = form;
</script>

<Card.Root class="mx-auto w-full max-w-sm">
	<Card.Header>
		<Card.Title class="text-center text-2xl">Login</Card.Title>
	</Card.Header>
	<Card.Content>
		<form class="grid gap-4" method="POST" use:enhance>
			<Form.Field {form} name="username">
				<Form.Control>
					{#snippet children({ props })}
						<Form.Label>Username</Form.Label>
						<Input
							{...props}
							type="text"
							placeholder="Enter your username"
							bind:value={$formData.username}
						/>
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
							placeholder="Enter your password"
							bind:value={$formData.password}
						/>
					{/snippet}
				</Form.Control>
				<Form.FieldErrors />
			</Form.Field>
			{#if $message?.type === 'error'}
				<div class="text-center text-xs">
					<p class="text-destructive">{$message.text}</p>
					{#if $message?.description}
						<p class="text-destructive/75">{$message.description}</p>
					{/if}
				</div>
			{/if}

			<Button type="submit" disabled={$submitting}>
				{#if $submitting}
					<LoaderCircle class="animate-spin" />
				{/if}
				Login
			</Button>
		</form>
		<FormDebug {formData} />
	</Card.Content>
</Card.Root>
