import posts from './posts.json';

export function getPosts() {
  return posts;
}

export function getPost(slug) {
  return posts.find((p) => p.slug === slug);
}
