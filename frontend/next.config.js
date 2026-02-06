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

  // Transpile ESM-only packages (pdfjs-dist v5 used by react-pdf v10)
  transpilePackages: ["react-pdf", "pdfjs-dist"],

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

    // Ensure .mjs files from pdfjs-dist are handled correctly
    config.module.rules.push({
      test: /\.mjs$/,
      include: /node_modules/,
      type: "javascript/auto",
    });

    return config;
  },
};

module.exports = nextConfig;
