import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  distDir: "out",
  images: {
    unoptimized: true,
  },
  trailingSlash: true,
  allowedDevOrigins: ["3000-006fa7e427cb494c.monkeycode-ai.online"],
};

export default nextConfig;
