/** @type {import('next').NextConfig} */
const nextConfig = process.env.DOCKER === "true" ? { output: "standalone" } : {};

export default nextConfig;
