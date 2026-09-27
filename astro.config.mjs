// @ts-check
import { defineConfig } from 'astro/config';

// Élesítéskor ide kerül a saját domain, pl. 'https://www.pelda.hu'
export default defineConfig({
  trailingSlash: 'ignore',
});
