/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy API requests to FastAPI backend during development
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },

  // Webpack configuration for react-pdf/pdfjs-dist compatibility
  webpack: (config) => {
    // Resolve canvas as false for client-side (used by pdfjs-dist)
    config.resolve.alias.canvas = false;

    // Handle pdfjs-dist's optional dependencies
    config.resolve.fallback = {
      ...config.resolve.fallback,
      canvas: false,
      encoding: false,
    };

    return config;
  },
};

module.exports = nextConfig;
