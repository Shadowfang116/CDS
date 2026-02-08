/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy API requests to backend for same-origin (no CORS needed in browser)
  // This allows browser to call /api/v1/* which gets proxied to the API container
  async rewrites() {
    // Normalize trailing slashes to avoid //api/v1
    const apiBase = (process.env.API_INTERNAL_BASE_URL || 'http://api:8000').replace(/\/+$/, '');
    
    return [
      {
        source: '/api/v1/:path*',
        destination: `${apiBase}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;

