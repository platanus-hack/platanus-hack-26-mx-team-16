export const Settings = {
  apiBaseUrl:
    process.env.NEXT_PUBLIC_BACKEND_API_HOST ||
    process.env.BACKEND_API_HOST ||
    "http://localhost:8000",
  version: process.env.NEXT_PUBLIC_VERSION || "1.0.0",
  apiKey: process.env.BACKEND_API_KEY || "",
  isProd: process.env.NODE_ENV === "production",
};
