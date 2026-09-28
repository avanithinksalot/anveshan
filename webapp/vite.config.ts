import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  base: '/anveshan/',
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
})