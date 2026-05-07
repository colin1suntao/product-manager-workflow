import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
      {
        source: "/artifacts/:path*",
        destination: "http://localhost:8000/artifacts/:path*",
      },
    ];
  },
  allowedDevOrigins: ["3000-006fa7e427cb494c.monkeycode-ai.online"],
};

export default nextConfig;
