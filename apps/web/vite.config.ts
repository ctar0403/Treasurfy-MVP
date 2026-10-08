import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const apiProxy = {
  "/api": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
  },
};
const allowedDemoHosts = ["localhost", "127.0.0.1"];
if (process.env.TREASURFY_DEMO_HOST) {
  allowedDemoHosts.push(process.env.TREASURFY_DEMO_HOST);
}

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: apiProxy,
    allowedHosts: allowedDemoHosts,
  },
  preview: {
    host: "127.0.0.1",
    port: 5173,
    proxy: apiProxy,
    allowedHosts: allowedDemoHosts,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
  },
});
