/** @type {import('next').NextConfig} */
const backendBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

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
