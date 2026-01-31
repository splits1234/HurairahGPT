import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/static/', // Flask serves static files from here
  build: {
    // Build directly to Flask's static folder
    outDir: '../HurairahGPT/mysite/static',
    emptyOutDir: false, // Important!
    rollupOptions: {
      output: {
        entryFileNames: 'react_assets/[name]-[hash].js',
        chunkFileNames: 'react_assets/[name]-[hash].js',
        assetFileNames: 'react_assets/[name]-[hash].[ext]',
      },
    }
  }
})
