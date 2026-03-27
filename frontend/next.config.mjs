/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable typedRoutes validator that enforces Promise-based params/searchParams
  typedRoutes: false,
  experimental: {
    // Also ensure experimental toggle is off if present
    typedRoutes: false,
  },
};

export default nextConfig;

