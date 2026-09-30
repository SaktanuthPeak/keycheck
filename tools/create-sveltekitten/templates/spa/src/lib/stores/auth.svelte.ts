import { browser } from '$app/environment';
import type { components } from '$lib/api/openapi';

type Token = components['schemas']['Token'];
type User = components['schemas']['UserResponse'];

const AUTH_KEY = 'auth_state';

interface AuthState {
	user: User | null;
	accessToken: string | null;
	tokenType: string | null;
	expiresAt: string | null;
	isAuthenticated: boolean;
}

class AuthStore {
	private state = $state<AuthState>({
		user: null,
		accessToken: null,
		tokenType: null,
		expiresAt: null,
		isAuthenticated: false
	});

	private initPromise: Promise<void> | null = null;
	private initialized = false;

	constructor() {
		if (browser) {
			this.loadFromStorage();
		}
	}

	/**
	 * Ensure auth store is initialized before use
	 */
	ensureInitialized() {
		if (this.initialized) {
			return;
		}
		// Since loadFromStorage is now synchronous, just mark as initialized
		this.initialized = true;
	}

	get user() {
		return this.state.user;
	}
	get accessToken() {
		return this.state.accessToken;
	}
	get tokenType() {
		return this.state.tokenType;
	}
	get expiresAt() {
		return this.state.expiresAt;
	}
	get isAuthenticated() {
		return this.state.isAuthenticated;
	}

	login(tokens: Token, user: User) {
		this.state = {
			user,
			accessToken: tokens.access_token,
			tokenType: tokens.token_type,
			expiresAt: tokens.expires_at,
			isAuthenticated: true
		};
		this.saveToStorage();
	}

	updateTokens(tokens: Token) {
		this.state.accessToken = tokens.access_token;
		this.state.tokenType = tokens.token_type;
		this.state.expiresAt = tokens.expires_at;
		this.saveToStorage();
	}

	/**
	 * Update only access token (for refresh_token endpoint that returns GetAccessTokenResponse)
	 */
	updateAccessToken(accessToken: string, tokenType: string) {
		this.state.accessToken = accessToken;
		this.state.tokenType = tokenType;
		this.saveToStorage();
	}

	logout() {
		this.state = {
			user: null,
			accessToken: null,
			tokenType: null,
			expiresAt: null,
			isAuthenticated: false
		};
		if (browser) {
			localStorage.removeItem(AUTH_KEY);
		}
	}

	/**
	 * Decode JWT payload (base64url decode)
	 */
	private decodeJwtPayload(token: string): { exp?: number; iat?: number; sub?: string } | null {
		try {
			const parts = token.split('.');
			if (parts.length !== 3 || !parts[1]) return null;

			// Base64url to Base64
			const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
			const payload = JSON.parse(atob(base64));
			return payload;
		} catch (e) {
			return null;
		}
	}

	/**
	 * Check if a JWT token is expired
	 * @param token - JWT token string
	 * @param bufferTime - Buffer time in seconds before expiration (default: 60 = 1 minute)
	 */
	private isJwtExpired(token: string | null, bufferTime = 60): boolean {
		if (!token) return true;

		const payload = this.decodeJwtPayload(token);
		if (!payload?.exp) return true;

		const nowInSeconds = Date.now() / 1000;
		const isExpired = nowInSeconds >= payload.exp - bufferTime;

		return isExpired;
	}

	/**
	 * Check if access token is expired
	 * @param bufferTime - Buffer time in seconds (default: 60 = 1 minute)
	 */
	isTokenExpired(bufferTime = 60): boolean {
		return this.isJwtExpired(this.state.accessToken, bufferTime);
	}

	/**
	 * Check if access token is about to expire (within specified seconds)
	 * @param bufferTime - Buffer time in seconds (default: 120 = 2 minutes)
	 */
	isTokenExpiringSoon(bufferTime = 120): boolean {
		return this.isJwtExpired(this.state.accessToken, bufferTime);
	}

	private saveToStorage() {
		if (browser) {
			try {
				localStorage.setItem(AUTH_KEY, JSON.stringify(this.state));
			} catch (e) {
				// Failed to save to localStorage
			}
		}
	}

	private loadFromStorage() {
		try {
			const value = localStorage.getItem(AUTH_KEY);
			if (value) {
				const parsed = JSON.parse(value);
				this.state = parsed;
			}
		} catch (e) {
			localStorage.removeItem(AUTH_KEY);
		} finally {
			this.initialized = true;
		}
	}
}

export const authStore = new AuthStore();
