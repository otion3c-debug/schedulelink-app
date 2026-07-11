/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: "https://api.schedulelink.tech",
  },
  // Fix for Vercel deploy: ensure next package is resolved from correct root
  // See https://nextjs.org/docs/app/api-reference/config/next-config-js/turbopack
  experimental: {},
};
module.exports = nextConfig;
