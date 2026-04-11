/** @type {import('next').NextConfig} */
const isDocker = process.env.DOCKER === "true";
const backendBaseUrl = (process.env.INTERNAL_BACKEND_URL || process.env.NEXT_PUBLIC_API_BASE_URL || (isDocker ? "http://backend:8000" : "http://localhost:8000")).replace(/\/$/, "");

const nextConfig = {
  ...(process.env.DOCKER === "true" ? { output: "standalone" } : {}),
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendBaseUrl}/api/v1/:path*`,
      },
      {
        source: "/api/:path*",
        destination: `${backendBaseUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
