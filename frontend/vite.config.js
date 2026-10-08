import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// During `npm run dev` the Vite server proxies /api to a locally running FastAPI,
// mirroring what Nginx (Docker) and the Ingress (Kubernetes) do in deployed setups.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': process.env.VITE_API_PROXY ?? 'http://localhost:8000',
    },
  },
});
