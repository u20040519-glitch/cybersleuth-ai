import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const srcPath = path.resolve(__dirname, './src')

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    // Regex aliases are order-independent and avoid prefix collisions
    // (e.g. '@/ui/Card' must not be captured by the '@/...' alias).
    alias: [
      { find: /^@\/ui\//, replacement: `${srcPath}/components/ui/` },
      { find: /^@\//, replacement: `${srcPath}/` },
    ],
  },
  server: {
    port: 3000,
    // Vite blocks unknown Host headers by default (DNS-rebinding protection).
    // The leading '.' allows every subdomain of the listed domain, which is
    // required for Cloudflare quick tunnels (random <name>.trycloudflare.com).
    allowedHosts: ['.trycloudflare.com', '.loca.lt', 'localhost'],
    proxy: {
      // Keep the proxy target on IPv4 loopback: the backend uvicorn binds
      // 127.0.0.1, and "localhost" alone can hang on IPv6-first resolvers.
      '/api': 'http://127.0.0.1:8000',
    },
  },
  preview: {
    port: 4173,
    allowedHosts: ['.trycloudflare.com', '.loca.lt', 'localhost'],
  },
})
