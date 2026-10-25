import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { host: '0.0.0.0', port: 3000, strictPort: true, allowedHosts: ['3000-iu0k5xhtrnkzhxs3o6zso-41fb5d91.sg2.manus.computer'], proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } } },
  preview: { host: '0.0.0.0', port: 3000, strictPort: true },
});
