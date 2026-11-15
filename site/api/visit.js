const KEY = "friday_site_seven_bay_visits";
const HIT_URLS = [
  `https://abacus.jasoncameron.dev/hit/friday-site-seven-bay/visits`,
  `https://countapi.mileshilliard.com/api/v1/hit/${KEY}`,
];
const GET_URLS = [
  `https://abacus.jasoncameron.dev/get/friday-site-seven-bay/visits`,
  `https://countapi.mileshilliard.com/api/v1/get/${KEY}`,
];

function parseCount(data) {
  const raw = data?.value ?? data?.count ?? data?.visitors;
  const n = typeof raw === "number" ? raw : Number(raw);
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : null;
}

async function readCount(urls) {
  for (const url of urls) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) continue;
      const data = await response.json();
      const visitors = parseCount(data);
      if (visitors !== null) return visitors;
    } catch {
      // try next provider
    }
  }
  return null;
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Access-Control-Allow-Origin", "*");
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  if (req.method !== "GET" && req.method !== "POST") {
    res.status(405).json({ visitors: null });
    return;
  }

  const hit =
    req.method === "POST" ||
    req.query?.hit === "1" ||
    req.query?.hit === "true";

  const visitors = await readCount(hit ? HIT_URLS : GET_URLS);
  if (visitors === null) {
    res.status(503).json({ visitors: null });
    return;
  }
  res.status(200).json({ visitors });
}
