<script setup>
import { getPost } from '~/lib/posts'
const route = useRoute()
const post = getPost(route.params.slug)
useHead({ title: post.title })
</script>

<template>
  <article class="post">
    <h1>{{ post.title }}</h1>
    <time :datetime="post.date">{{ post.date }}</time>
    <div class="body">
      <p v-for="(para, i) in post.body" :key="i">{{ para }}</p>
    </div>
    <a href="/" class="back-link">← 一覧へ戻る</a>
  </article>
</template>
