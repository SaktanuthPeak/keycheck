export const load = async ({ locals }) => {
	const result = await locals.fastapiClient.GET('/v1/health');
	return { health: result.error ? null : result.data };
};
