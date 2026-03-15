import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "farmaoliva.cdn1.dattamax.com" },
      { protocol: "https", hostname: "f.fcdn.app" },
      { protocol: "https", hostname: "www.puntofarma.com.py" },
      { protocol: "https", hostname: "www.farmaciacatedral.com.py" },
      { protocol: "https", hostname: "www.farmacenter.com.py" },
    ],
  },
};

export default nextConfig;
