// Answers the editor's API calls and /view images from canned data (see tools/build_live_demo.py).
const BASE = new URL("./", self.location).pathname;
let ROUTES = null, MEDIA = null;
const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "Content-Type": "application/json" } });
async function load() {
  if (!ROUTES) ROUTES = await (await fetch(BASE + "data/routes.json")).json();
  if (!MEDIA) MEDIA = await (await fetch(BASE + "data/media.json")).json();
}
async function media(u) {
  await load();
  const fn = (u.searchParams.get("filename") || u.searchParams.get("file") || u.searchParams.get("name") || "").split("/").pop();
  const hit = MEDIA[fn] || MEDIA[(fn.match(/hop[_-]?(\d)/) || [])[1] ? "hop" + fn.match(/hop[_-]?(\d)/)[1] + ".jpg" : ""];
  if (!hit) return new Response("", { status: 404 });
  const b = Uint8Array.from(atob(hit.split(",")[1]), (c) => c.charCodeAt(0));
  return new Response(b, { headers: { "Content-Type": "image/jpeg" } });
}
async function route(req, p) {
  await load();
  let key = req.method + " " + p;
  if (p.endsWith("/sandtie/write") && req.method === "POST") {
    let stage = "";
    try { stage = String((await req.clone().json()).stage || ""); } catch (_) {}
    if (stage === "cpu" || stage === "skeleton") key += "#cpu";
  }
  const hit = ROUTES[key] ?? ROUTES[req.method === "POST" ? "GET " + p : "POST " + p];
  return json(hit ?? ROUTES["*"]);
}
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (u.origin !== location.origin) return;
  let p = u.pathname;
  if (p.startsWith(BASE)) return;
  if (p.startsWith("/api/")) p = p.slice(4);
  if (p === "/view" || /thumb|sprite/.test(p)) { e.respondWith(media(u)); return; }
  if (/^\/(h3_ref_chain|sandtie_rig|prompt|queue|history|object_info|system_stats|upload|interrupt|free|userdata)\b/.test(p)) {
    e.respondWith(route(e.request, p));
  }
});
