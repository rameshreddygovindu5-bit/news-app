# Peoples Feedback — News Client

Public-facing news website. Reads from the news-platform-final API.

## Quick Start (Development)
```bash
npm install
npm run dev        # → http://localhost:3001
```
Backend must be running on port 8005 (auto-proxied by Vite).

## Build for Production
```bash
VITE_API_URL=http://your-api-server:8005 npm run build
npx serve -s dist  # test locally
```

## Deploy to AWS (auto on every git push)
1. Run `./setup-aws.sh` once to create the S3 bucket
2. Add GitHub Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `VITE_API_URL`
3. Push to `main` — GitHub Actions builds and deploys automatically

## Hostinger DNS
Add CNAME record: `www` → `peoples-feedback-news.s3-website.ap-south-1.amazonaws.com`

## Project Structure
```
src/
├── App.tsx                    — Routes
├── main.tsx                   — Entry point
├── index.css                  — Tailwind + custom styles
├── types/news.ts              — Types + display helpers
├── lib/
│   ├── api.ts                 — API client (flags=A,Y only)
│   ├── queryClient.ts         — React Query config
│   ├── share.ts               — Social sharing
│   └── utils.ts               — Tailwind merge
├── pages/
│   ├── Home.tsx               — Homepage with news grid
│   ├── News.tsx               — Category/search with pagination
│   ├── NewsDetail.tsx          — Article detail + related
│   └── NotFound.tsx
├── components/
│   ├── news/
│   │   ├── PremiumHeader.tsx  — Nav + categories + search
│   │   ├── PremiumFooter.tsx  — Footer + newsletter
│   │   ├── NewsLayout.tsx     — News grid + hero + sidebar
│   │   └── ShareMenu.tsx      — Share buttons
│   └── ui/                    — Radix UI primitives
└── hooks/
    ├── useDebounce.ts
    └── use-toast.ts
```
