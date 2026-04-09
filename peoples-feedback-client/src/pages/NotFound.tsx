import { Link } from "wouter";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-white">
      <div className="text-center space-y-6">
        <div className="text-8xl font-[900] text-zinc-200">404</div>
        <h1 className="text-2xl font-bold text-zinc-900">Page Not Found</h1>
        <p className="text-zinc-500 max-w-sm mx-auto">The page you're looking for doesn't exist or has been moved.</p>
        <Link href="/"><a className="inline-block bg-[var(--pf-orange)] text-white px-8 py-3 font-bold text-sm uppercase tracking-widest hover:bg-orange-500 transition-colors">Back to Home</a></Link>
      </div>
    </div>
  );
}
