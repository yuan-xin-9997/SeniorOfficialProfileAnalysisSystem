import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ command, mode }) => {
  const envDir = "..";
  const env = loadEnv(mode, envDir, "");
  const apiTarget = env.VITE_DEV_API_TARGET || (env.APP_PORT ? `http://127.0.0.1:${env.APP_PORT}` : "");
  if (command === "serve" && !apiTarget) {
    throw new Error("Set VITE_DEV_API_TARGET or APP_PORT in the application .env file.");
  }
  return {
    envDir,
    plugins: [vue()],
    server: {
      proxy: apiTarget ? { "/api": apiTarget } : undefined
    }
  };
});
