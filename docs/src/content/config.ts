import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const docs = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/docs' }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    sidebar: z.object({
      label: z.string().optional(),
      order: z.number().optional(),
      hidden: z.boolean().optional(),
    }).optional(),
    tags: z.array(z.string()).optional(),
    lastUpdated: z.date().optional(),
    draft: z.boolean().optional(),
  }),
});

const guides = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/guides' }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    sidebar: z.object({
      label: z.string().optional(),
      order: z.number().optional(),
      hidden: z.boolean().optional(),
    }).optional(),
    tags: z.array(z.string()).optional(),
    difficulty: z.enum(['beginner', 'intermediate', 'advanced']).optional(),
    estimatedTime: z.string().optional(),
    prerequisites: z.array(z.string()).optional(),
  }),
});

const api = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/api' }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    sidebar: z.object({
      label: z.string().optional(),
      order: z.number().optional(),
      hidden: z.boolean().optional(),
    }).optional(),
    endpoint: z.string().optional(),
    method: z.enum(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']).optional(),
    version: z.string().optional(),
    deprecated: z.boolean().optional(),
  }),
});

export const collections = { docs, guides, api };