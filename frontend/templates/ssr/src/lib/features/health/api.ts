import fastapiClient from '$lib/api/fastapi-client';

export const healthStatus = async () => {
	const { data } = await fastapiClient.GET('/v1/health');
	return data;
};
