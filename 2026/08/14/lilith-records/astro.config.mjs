import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://lilith-records.example.com',
  output: 'static',
  i18n: {
    defaultLocale: 'ja',
    locales: ['ja'],
  },
});
