export const Settings = {
  apiBaseUrl:
    process.env.NEXT_PUBLIC_BACKEND_API_HOST ||
    process.env.BACKEND_API_HOST ||
    "http://localhost:8000",
  version: process.env.NEXT_PUBLIC_VERSION || "1.0.0",
  apiKey: process.env.BACKEND_API_KEY || "",
  isProd: process.env.NODE_ENV === "production",
  /** Google OAuth (server-only; never inline into the client bundle). */
  google: {
    clientId: process.env.GOOGLE_CLIENT_ID || "",
    /** Where Google sends the user back with `?code=`. Must match the
     * console + backend `GOOGLE_REDIRECT_URI`. */
    redirectUri: process.env.GOOGLE_REDIRECT_URI || "",
  },
};
