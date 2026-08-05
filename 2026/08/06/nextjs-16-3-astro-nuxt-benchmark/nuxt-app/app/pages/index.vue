<script setup>
import { getPosts } from '~/lib/posts'
const posts = getPosts()
</script>

<template>
  <div>
    <section class="hero">
      <h1>比較用サンプルブログ</h1>
      <p>同じデザインをNext.js / Astro / Nuxtで組んで計測する。</p>
    </section>
    <ul class="post-list">
      <li v-for="post in posts" :key="post.slug" class="post-card">
        <a :href="`/posts/${post.slug}`">{{ post.title }}</a>
        <time :datetime="post.date">{{ post.date }}</time>
        <p>{{ post.excerpt }}</p>
      </li>
    </ul>
  </div>
</template>
