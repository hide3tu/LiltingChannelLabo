export default defineNuxtConfig({
  compatibilityDate: '2026-08-05',
  css: ['~/assets/style.css'],
  app: {
    head: {
      htmlAttrs: { lang: 'ja' },
      title: 'FW Compare Blog',
      meta: [
        { name: 'description', content: 'Framework comparison sample blog' },
      ],
    },
  },
})
