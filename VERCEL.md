# Vercel Deploy

This repository deploys the Next.js frontend on Vercel. The FastAPI backend must be deployed separately.

## Project Root

- Use the repository root with `vercel.json`, or set the Vercel project root to `apps/frontend`.

## Required Environment Variables

- `NEXT_PUBLIC_API_BASE_URL` = public backend base URL
- `NEXT_PUBLIC_LEGACY_API_BASE_URL` = public backend legacy base URL
- `NEXT_PUBLIC_METABASE_URL` = Metabase URL if embedded in the UI

## Backend Example

- `NEXT_PUBLIC_API_BASE_URL=https://your-backend.example.com`
- `NEXT_PUBLIC_LEGACY_API_BASE_URL=https://your-backend.example.com/api/v1`

## Deploy Flow

1. Deploy the backend to a host that supports FastAPI.
2. Set the frontend env vars in Vercel.
3. Deploy the frontend from this repository.
