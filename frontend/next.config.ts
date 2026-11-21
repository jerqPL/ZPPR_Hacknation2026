import type { NextConfig } from "next";

const internalApiUrl = (
  process.env.INTERNAL_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${internalApiUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
