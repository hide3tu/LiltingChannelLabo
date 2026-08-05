import { getPost, getPosts } from '../../../lib/posts';

export function generateStaticParams() {
  return getPosts().map((p) => ({ slug: p.slug }));
}

export default async function PostPage({ params }) {
  const { slug } = await params;
  const post = getPost(slug);
  return (
    <article className="post">
      <h1>{post.title}</h1>
      <time dateTime={post.date}>{post.date}</time>
      <div className="body">
        {post.body.map((para, i) => (
          <p key={i}>{para}</p>
        ))}
      </div>
      <a href="/" className="back-link">← 一覧へ戻る</a>
    </article>
  );
}
