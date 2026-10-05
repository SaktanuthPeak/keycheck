<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';
</script>

<div class="flex flex-col items-center justify-center gap-4 py-16 text-center">
	<h1 class="text-4xl font-bold">{page.status}</h1>
	<p class="text-muted-foreground">
		{page.status === 404 ? 'ไม่พบหน้าที่ต้องการ' : 'เกิดข้อผิดพลาด กรุณาลองใหม่'}
	</p>
	<Button href={resolve('/')}>กลับหน้าแรก</Button>
</div>
