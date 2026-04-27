// Catch-all API proxy route handler
// Proxies all /api/* requests to the backend server
// Required for Next.js standalone mode where next.config.mjs rewrites don't work

const BACKEND_URL = (
    process.env.INTERNAL_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "http://localhost:8000"
).replace(/\/$/, "");

async function handler(request, { params }) {
    const { path } = await params;
    const target = path ? path.join("/") : "";
    const url = new URL(request.url);
    const backendUrl = `${BACKEND_URL}/${target}${url.search}`;

    const headers = new Headers(request.headers);
    headers.delete("host");

    const init = {
        method: request.method,
        headers,
    };

    if (request.method !== "GET" && request.method !== "HEAD") {
        init.body = await request.arrayBuffer();
        init.duplex = "half";
    }

    try {
        const res = await fetch(backendUrl, init);
        const body = await res.arrayBuffer();
        return new Response(body, {
            status: res.status,
            statusText: res.statusText,
            headers: res.headers,
        });
    } catch (err) {
        return new Response(JSON.stringify({ detail: "Backend unavailable" }), {
            status: 502,
            headers: { "Content-Type": "application/json" },
        });
    }
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
