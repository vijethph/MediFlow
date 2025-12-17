import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  /* config options here */
  // Fix Turbopack root directory issue
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
