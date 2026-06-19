export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-10 border-t pt-6 text-sm text-muted-foreground">
      <div>
        <div className="font-bold text-foreground">🩺 Website Audit &amp; Recommendation System</div>
        <p className="mt-1 max-w-2xl text-xs">
          Crawls a website and generates a branded, prioritised audit across SEO, performance,
          content, local SEO, UX and accessibility — exportable as PDF, Word &amp; HTML.
        </p>
      </div>
      <div className="mt-5 flex flex-col gap-2 border-t pt-4 text-xs sm:flex-row sm:items-center sm:justify-between">
        <span>© {year} Website Audit &amp; Recommendation System. All rights reserved.</span>
        <span>Performance data via Google PageSpeed Insights · Analysis by Claude</span>
      </div>
    </footer>
  );
}
