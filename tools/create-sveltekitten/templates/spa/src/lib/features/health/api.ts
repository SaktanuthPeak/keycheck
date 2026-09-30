import client, { apiRequest } from '$lib/api/client';

export const healthStatus = () => {
	// ส่ง Promise จาก openapi-fetch เข้า apiRequest ตรงๆ ได้เลย
	return apiRequest(client.GET('/v1/health'));
};
