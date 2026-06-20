import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import mdx from '@astrojs/mdx';
import node from '@astrojs/node';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://docs.doxiq.io',
  base: '/',
  trailingSlash: 'ignore',
  build: {
    assets: 'assets',
    inlineStylesheets: 'auto',
  },
  integrations: [
    react(),
    mdx(),
  ],
  adapter: node({ mode: 'standalone' }),
  vite: {
    plugins: [tailwindcss()],
    server: {
      port: 4321,
    },
  },
  output: 'server',
  compressHTML: true,
  prefetch: {
    prefetchAll: true,
    defaultStrategy: 'viewport',
  },
});