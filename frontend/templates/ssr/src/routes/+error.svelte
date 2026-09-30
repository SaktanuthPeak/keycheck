<script lang="ts">
  import { page } from '$app/state';
</script>

<div class="flex min-h-svh flex-col items-center justify-center gap-4">
  <h1 class="text-4xl font-bold">{page.status}</h1>
  <p class="text-muted-foreground">{page.error?.message ?? 'Something went wrong'}</p>
  <a href="/" class="underline">Go home</a>
</div>
