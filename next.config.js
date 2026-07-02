/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: "https://api.schedulelink.tech",
  },
};
module.exports = nextConfig;
