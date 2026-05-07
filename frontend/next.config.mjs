import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
// Rewrites removed: /api/v1/* is handled by the catch-all Route Handler
// at app/api/v1/[...path]/route.ts which reads API_INTERNAL_BASE_URL at runtime.
const nextConfig = {
  output: "standalone",
  typedRoutes: false,
  turbopack: {
    root: frontendRoot,
  },
};

export default nextConfig;
