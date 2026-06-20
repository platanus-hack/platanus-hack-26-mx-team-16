// Cookie names
export const COOKIE_ACCESS_TOKEN = "___AT5___";
export const COOKIE_REFRESH_TOKEN = "___RT5___";
export const COOKIE_REFRESH_ATTEMPTS = "___RA5___";

// Token expiration times (in seconds)
export const ACCESS_TOKEN_MAX_AGE = 60 * 10; // 10 minutes
export const REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 7; // 7 days
export const REFRESH_ATTEMPTS_MAX_AGE = 60; // 60s — short window to bound a redirect loop

// Max consecutive failed refresh attempts before we wipe the session
export const MAX_REFRESH_ATTEMPTS = 3;
