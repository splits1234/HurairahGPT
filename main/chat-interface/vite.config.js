import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'url'
import { dirname, resolve } from 'path'
import fs from 'fs'

const __dirname = dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'copy-index-to-templates',
      closeBundle: () => {
        // Copy built index.html to Flask templates folder
        const sourceIndex = resolve(__dirname, '../mysite/static/index.html')
        const targetIndex = resolve(__dirname, '../mysite/templates/index.html')
        if (fs.existsSync(sourceIndex)) {
          fs.copyFileSync(sourceIndex, targetIndex)
          console.log('[vite] Copied index.html to templates folder')
        }
      }
    }
  ],
  base: '/static/', // Flask serves static files from here
  resolve: {
    alias: {
      // Ensure consistent module resolution
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  optimizeDeps: {
    // Fix framer-motion circular dependency issues
    include: ['framer-motion', 'react', 'react-dom'],
    // Pre-scan for potential circular deps
    esbuildOptions: {
      // Enable JSX in esbuild for faster transpilation
      loader: 'jsx',
    },
  },
  esbuild: {
    // Disable minification during development for better error messages
    minify: false,
    // Ensure proper JSX transformation
    jsx: 'automatic',
  },
  build: {
    // Build directly to Flask's static folder
    outDir: resolve(__dirname, '../mysite/static'),
    emptyOutDir: true, // Clear old build files
    minify: 'esbuild', // Use esbuild instead of terser for better compatibility
    rollupOptions: {
      output: {
        entryFileNames: 'react_assets/[name]-[hash].js',
        chunkFileNames: 'react_assets/[name]-[hash].js',
        assetFileNames: 'react_assets/[name]-[hash].[ext]',
      },
    }
  }
})
