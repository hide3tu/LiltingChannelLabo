import { getPosts } from '../lib/posts';

export default function Home() {
  const posts = getPosts();
  return (
    <>
      <section className="hero">
        <h1>比較用サンプルブログ</h1>
        <p>同じデザインをNext.js / Astro / Nuxtで組んで計測する。</p>
      </section>
      <ul className="post-list">
        {posts.map((post) => (
          <li className="post-card" key={post.slug}>
            <a href={`/posts/${post.slug}`}>{post.title}</a>
            <time dateTime={post.date}>{post.date}</time>
            <p>{post.excerpt}</p>
          </li>
        ))}
      </ul>
    </>
  );
}
