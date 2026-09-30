import { createServer } from 'node:http';

// Valid JWTs with exp: 9999999999 (year 2286) — jwt.decode() parses without verification
const MOCK_ACCESS_TOKEN =
	'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.fake';
const MOCK_REFRESH_TOKEN =
	'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ0.eyJzdWIiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.fake';

const VALID = { username: 'admin', password: 'secret' };

const CORS_HEADERS = {
	'Access-Control-Allow-Origin': 'http://localhost:4173',
	'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
	'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

const server = createServer(async (req, res) => {
	// Handle CORS preflight
	if (req.method === 'OPTIONS') {
		res.writeHead(204, CORS_HEADERS);
		res.end();
		return;
	}

	Object.entries(CORS_HEADERS).forEach(([k, v]) => res.setHeader(k, v));
	res.setHeader('Content-Type', 'application/json');

	const chunks = [];
	for await (const chunk of req) chunks.push(chunk);
	const body = JSON.parse(Buffer.concat(chunks).toString() || '{}');

	if (req.method === 'POST' && req.url === '/v1/auth/login') {
		if (body.username === VALID.username && body.password === VALID.password) {
			res.writeHead(200);
			res.end(
				JSON.stringify({
					access_token: MOCK_ACCESS_TOKEN,
					refresh_token: MOCK_REFRESH_TOKEN,
					token_type: 'bearer',
				})
			);
		} else {
			res.writeHead(401);
			res.end(JSON.stringify({ detail: 'Invalid credentials' }));
		}
		return;
	}

	if (req.method === 'GET' && req.url === '/v1/users/me') {
		res.writeHead(200);
		res.end(
			JSON.stringify({
				username: 'admin',
				name: 'Admin',
				id: 1,
				role: 'admin',
				is_active: true,
				email: 'admin@test.com',
				last_login_date: null,
				created_at: new Date().toISOString(),
			})
		);
		return;
	}

	if (req.method === 'GET' && req.url === '/v1/health') {
		res.writeHead(200);
		res.end(JSON.stringify({ status: 'ok' }));
		return;
	}

	res.writeHead(404);
	res.end(JSON.stringify({ detail: 'Not found' }));
});

server.listen(9001, () => console.log('Mock API running on http://localhost:9001'));
