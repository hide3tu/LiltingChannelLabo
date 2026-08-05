import './globals.css';

export const metadata = {
  title: 'FW Compare Blog',
  description: 'Framework comparison sample blog',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ja">
      <body>
        <header className="site-header">
          <a href="/" className="logo">FW Compare</a>
          <nav>
            <a href="/">Home</a>
          </nav>
        </header>
        <main>{children}</main>
        <footer className="site-footer">Built for framework comparison</footer>
      </body>
    </html>
  );
}
