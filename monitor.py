"""Render monitor: what the current (or last) chain run has finished, read from the hop cache.

The hop cache keeps one entry per finished hop (a .mkv, the audio and a .json meta with
`hop`, `of`, `prev_key`, `frames`, `fps`, `written`). That is enough to follow a run from any
browser, whoever queued it: ComfyUI only sends live previews to the tab that queued the prompt,
but the cache is on disk for everyone.

`run_state()` finds the newest cached hop and walks back along `prev_key` (the exact chain of
this run); where a hop has no `prev_key` (hop 1, a restart, a hand_tie hop), it takes the
newest entry for hop n-1 of the same run length written before hop n. Labels (a title, each
shot's id, its length and its place) come from the running or last prompt's HandTieClips
`shot_plan` / `ref_plan` and the save prefix; they are kept in the cache folder so a ComfyUI
restart does not lose them. The page at /h3_ref_chain/monitor polls it and plays each hop
through the existing /hop_clip route.
"""
import glob
import json
import os
import time

from . import store as _store

META_EXT = getattr(_store, "META_EXT", ".json")
LABELS_FILE = "monitor_labels.json"


def _roots():
    for loc in ("user", "temp"):
        try:
            root = _store.cache_root(loc)
        except Exception:  # noqa: BLE001
            continue
        if os.path.isdir(root):
            yield root


def _metas():
    out = []
    for root in _roots():
        for p in glob.glob(os.path.join(root, "*" + META_EXT)):
            name = os.path.basename(p)
            if name.startswith("ptr_") or name == LABELS_FILE:
                continue
            key = name[: -len(META_EXT)]
            if not all(c in "0123456789abcdef" for c in key):
                continue
            try:
                with open(p, encoding="utf-8") as fh:
                    m = json.load(fh)
                hop, of = int(m.get("hop")), int(m.get("of"))
            except Exception:  # noqa: BLE001
                continue
            if m.get("dry_run") or hop < 1 or of < 1:
                continue
            w = float(m.get("written") or os.path.getmtime(p))
            out.append(dict(key=key, hop=hop, of=of, prev=m.get("prev_key"), written=w,
                            frames=int(m.get("frames") or 0), fps=float(m.get("fps") or 24),
                            w=int(m.get("width") or 0), h=int(m.get("height") or 0),
                            pin_mech=m.get("pin_mech")))
    return out


def _queue():
    """(running, pending count, the newest prompt dict we can see) from ComfyUI."""
    try:
        from server import PromptServer
        q = PromptServer.instance.prompt_queue
        running, pending = q.get_current_queue()
        prompt = running[0][2] if running else None
        if prompt is None:
            hist = q.get_history(max_items=1) or {}
            for v in hist.values():
                prompt = (v.get("prompt") or [None, None, None])[2]
        return len(running) > 0, len(pending), prompt
    except Exception:  # noqa: BLE001
        return None, None, None


def _labels_from_prompt(prompt):
    """Title + one label per shot from a HandTieClips node in an API prompt, or None."""
    if not isinstance(prompt, dict):
        return None
    chain = next((n for n in prompt.values() if isinstance(n, dict) and n.get("class_type") == "HandTieClips"), None)
    if not chain:
        return None
    inp = chain.get("inputs") or {}
    try:
        shots = json.loads(inp.get("shot_plan") or "{}").get("shots") or []
    except Exception:  # noqa: BLE001
        return None
    plates = set()
    try:
        for r in (json.loads(inp.get("ref_plan") or "{}").get("refs") or []):
            if r.get("retention") == "reference" and r.get("tag"):
                plates.add(str(r["tag"]))
    except Exception:  # noqa: BLE001
        pass
    title = ""
    for n in prompt.values():
        if isinstance(n, dict) and n.get("class_type") in ("HTCSaveVideo", "SaveVideo", "VHS_VideoCombine"):
            pre = str((n.get("inputs") or {}).get("filename_prefix") or "")
            if pre:
                title = pre.replace("\\", "/").rstrip("/").split("/")[-1]
                break
    out, place = [], ""
    for i, s in enumerate(shots):
        for t in (s.get("refs") or []):
            if str(t) in plates:
                place = str(t)
                break
        out.append({"id": str(s.get("id") or f"s{i + 1}"), "dur": str(s.get("duration") or ""), "place": place})
    if not out:
        return None
    return {"title": title, "shots": out, "at": time.time()}


def _labels(prompt):
    lab = _labels_from_prompt(prompt)
    roots = list(_roots())
    if lab and roots:
        try:
            with open(os.path.join(roots[0], LABELS_FILE), "w", encoding="utf-8") as fh:
                json.dump(lab, fh)
        except OSError:
            pass
        return lab
    for root in roots:
        try:
            with open(os.path.join(root, LABELS_FILE), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            continue
    return None


def run_state(max_age_h=36.0):
    metas = _metas()
    now = time.time()
    running, pending, prompt = _queue()
    base = {"ok": True, "running": running, "pending": pending, "now": now, "hops": [], "of": 0,
            "title": "", "shots": []}
    metas = [m for m in metas if now - m["written"] < max_age_h * 3600]
    lab = _labels(prompt)
    if not metas:
        if lab:
            base.update(title=lab.get("title", ""), shots=lab.get("shots", []))
        return base
    by_key = {m["key"]: m for m in metas}
    newest = max(metas, key=lambda m: m["written"])
    chain = {newest["hop"]: newest}
    cur = newest
    while cur["hop"] > 1:
        prev = by_key.get(cur["prev"]) if cur.get("prev") else None
        if prev is None or prev["hop"] != cur["hop"] - 1:
            cands = [m for m in metas if m["hop"] == cur["hop"] - 1 and m["of"] == cur["of"]
                     and m["written"] <= cur["written"]]
            prev = max(cands, key=lambda m: m["written"]) if cands else None
        if prev is None:
            break
        chain[prev["hop"]] = prev
        cur = prev
    hops = [chain[k] for k in sorted(chain)]
    base.update(of=newest["of"], hops=[{k: v for k, v in h.items() if k != "prev"} for h in hops],
                last_hop=newest["hop"], last_written=newest["written"])
    if lab and len(lab.get("shots") or []) == newest["of"]:
        base.update(title=lab.get("title", ""), shots=lab["shots"])
    return base


def links(port=None, listen=None):
    """Where this page can be opened from. `lan` is None when ComfyUI listens on
    loopback only (no --listen), so a phone cannot reach it. No packet is sent:
    connecting a UDP socket only asks the OS which interface routes outward."""
    import socket
    try:
        from comfy.cli_args import args  # noqa: PLC0415
        port = port or args.port
        listen = listen if listen is not None else args.listen
    except Exception:  # noqa: BLE001
        port, listen = port or 8188, listen or "127.0.0.1"
    hosts = [h.strip() for h in str(listen or "").split(",") if h.strip()]
    loopback = all(h in ("127.0.0.1", "localhost", "::1") for h in hosts) if hosts else True
    lan = None
    if not loopback:
        ip = next((h for h in hosts if h not in ("0.0.0.0", "::") and ":" not in h), None)
        if ip is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("10.255.255.255", 1))
                ip = s.getsockname()[0]
            except OSError:
                ip = None
            finally:
                s.close()
        if ip:
            lan = f"http://{ip}:{port}"
    return {"lan": lan, "port": port, "listen": listen}


PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Render Monitor</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Space+Grotesk:wght@400;600&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
/* One-column render monitor: title, status, a hop strip coloured by place, a grid of hop tiles that
   start looping as each hop finishes, and a player for one hop with sound. Dark stage look. */
:root{
  --bg:#0a0d16; --panel:#121827; --panel2:#0e1320; --line:#243049; --fg:#eef2ff; --muted:#9aa6c4;
  --run:#3ee6ff; --ok:#9ff03a; --wait:#ffb347; --bad:#ff4d6a; --accent:#ffb347;
  --display:"Dela Gothic One","Arial Black",Impact,sans-serif; --body:"Space Grotesk",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,Consolas,monospace; color-scheme:dark;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 var(--body);
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
main{max-width:1180px;margin:0 auto;padding-block:30px 60px;display:grid;gap:26px}
.eyebrow{font:600 12px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin:0 0 6px}
h1{font-family:var(--display);font-weight:400;font-size:clamp(32px,6.5vw,62px);line-height:1;margin:0;text-wrap:balance;word-break:break-word}
h1 .t{color:var(--accent)}
.sub{color:var(--muted);margin:10px 0 0;max-width:65ch}
.state{display:flex;flex-wrap:wrap;gap:12px 28px;align-items:center}
.pill{font:600 13px var(--mono);padding:4px 12px;border-radius:999px;border:1px solid currentColor}
.pill.run{color:var(--run)} .pill.done{color:var(--ok)} .pill.idle{color:var(--wait)}
.kv{display:flex;flex-direction:column;gap:2px;min-width:0}
.kv b{font:600 19px var(--mono);font-variant-numeric:tabular-nums}
.kv small{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.1em}
.strip{display:flex;gap:3px}
.seg{height:30px;border-radius:3px;background:var(--panel);border:1px solid var(--line);position:relative;overflow:hidden;min-width:0}
.seg.done{background:var(--c);border-color:var(--c)}
.seg.now{border-color:var(--c);background:repeating-linear-gradient(135deg,var(--c) 0 5px,transparent 5px 10px);background-size:200% 100%;animation:slide 1.2s linear infinite}
@keyframes slide{to{background-position:-28px 0}}
.seg i{position:absolute;inset:auto 0 2px;text-align:center;font:600 9px var(--mono);color:#fff;mix-blend-mode:difference;font-style:normal}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:10px;color:var(--muted);font-size:13px}
.legend span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:2px;background:var(--c);margin-right:6px;vertical-align:-1px}
h2{font-family:var(--display);font-weight:400;font-size:20px;margin:0 0 12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:9px;overflow:hidden;display:flex;flex-direction:column;min-width:0;
  padding:0;color:inherit;font:inherit;text-align:left;cursor:pointer}
.tile:focus-visible{outline:2px solid var(--run);outline-offset:2px}
.tile.now{border-color:var(--run)}
.tile.sel{border-color:var(--accent)}
.shot{aspect-ratio:16/9;max-width:100%;background:#000;position:relative;display:grid;place-items:center}
.portrait .shot{aspect-ratio:9/16}
.shot video{width:100%;height:100%;object-fit:cover;display:block}
.shot .ph{font:600 12px var(--mono);color:var(--muted)}
.shot .no{position:absolute;top:7px;left:7px;font:600 11px var(--mono);background:var(--c);color:#0a0d16;padding:1px 7px;border-radius:3px}
.meta{padding:9px 11px 10px;display:grid;gap:2px}
.meta b{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.meta .t{font:12px var(--mono);color:var(--muted);font-variant-numeric:tabular-nums}
.player{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:16px;display:grid;gap:10px}
.player[hidden]{display:none}
.player video{width:100%;max-height:70vh;border-radius:8px;background:#000}
.phead{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.phead b{font-family:var(--display);font-weight:400;font-size:18px}
.phead .sp{flex:1}
.btn{font:600 13px var(--body);color:var(--fg);background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:6px 12px;cursor:pointer}
.btn:focus-visible{outline:2px solid var(--run)}
.err{color:var(--bad);font:13px var(--mono)}
.err[hidden]{display:none}
@media (prefers-reduced-motion:reduce){.seg.now{animation:none}}
/* ?view=desktop: full-width wall; the open hop plays in a sticky column on the right. */
body.desktop main{max-width:none;padding-block:22px 40px;gap:20px}
body.desktop .grid{grid-template-columns:repeat(auto-fill,minmax(250px,1fr))}
body.desktop h1{font-size:clamp(28px,3.2vw,44px)}
@media (min-width:1100px){
  body.desktop:has(#player:not([hidden])) main{grid-template-columns:minmax(0,1fr) minmax(380px,38%)}
  body.desktop main>*{grid-column:1/-1}
  body.desktop:has(#player:not([hidden])) #hops{grid-column:1;grid-row:4}
  body.desktop #player{grid-column:2;grid-row:4;position:sticky;top:16px;align-self:start}
}
</style></head><body>
<main>
  <header>
    <p class="eyebrow">Hand-Tie-Clips · render monitor</p>
    <h1 id="title"><span class="t">Waiting</span><br>for a render</h1>
    <p class="sub" id="sub">Each tile starts looping as soon as its hop is finished. Tap one to watch it with sound. Updates every 15 s.</p>
  </header>
  <section class="state" aria-live="polite">
    <span id="pill" class="pill idle">IDLE</span>
    <div class="kv"><small>Hop</small><b id="hop">–</b></div>
    <div class="kv"><small>Per hop</small><b id="per">–</b></div>
    <div class="kv"><small>Est. finish</small><b id="eta">–</b></div>
    <div class="kv"><small>Updated</small><b id="upd">–</b></div>
  </section>
  <section>
    <div class="strip" id="strip"></div>
    <div class="legend" id="legend"></div>
    <p class="err" id="err" hidden></p>
  </section>
  <section class="player" id="player" hidden>
    <div class="phead"><b id="ptitle">hop</b><span class="sp"></span><button class="btn" id="prev" type="button">◀ prev</button><button class="btn" id="next" type="button">next ▶</button><button class="btn" id="close" type="button">close</button></div>
    <video id="pvideo" controls playsinline preload="metadata"></video>
  </section>
  <section id="hops">
    <h2>Hops</h2>
    <div class="grid" id="grid"></div>
  </section>
</main>
<script>
const $=id=>document.getElementById(id);
// ?view=desktop | phone (the node's pop-out buttons pass one); otherwise by width.
const VIEW=new URLSearchParams(location.search).get("view")||(matchMedia("(min-width:1100px)").matches?"desktop":"phone");
document.body.classList.add(VIEW==="desktop"?"desktop":"phone");
const PAL=["#4f7dff","#b9f5d0","#d8dcff","#3ee6ff","#ffb347","#ff6fd8","#9ff03a","#ff8a5b","#c9a7ff","#5ef2c1"];
const hhmm=t=>new Date(t*1000).toTimeString().slice(0,5);
const tiles=new Map(); let S=null, sel=0;
const io=("IntersectionObserver" in window)?new IntersectionObserver(es=>{for(const e of es){const v=e.target.querySelector("video");if(!v)continue;
  if(e.isIntersecting&&!document.hidden)v.play().catch(()=>{});else v.pause();}},{threshold:.15}):null;
document.addEventListener("visibilitychange",()=>{for(const t of tiles.values()){const v=t.querySelector("video");if(v){document.hidden?v.pause():v.play().catch(()=>{});}} if(!document.hidden) poll();});
function colours(){const m=new Map();for(const s of (S&&S.shots)||[]){if(s.place&&!m.has(s.place))m.set(s.place,PAL[m.size%PAL.length]);}return m;}
function colourOf(n){const sh=(S&&S.shots||[])[n-1];const m=colours();return (sh&&m.get(sh.place))||"#9aa6c4";}
function label(n){const sh=(S&&S.shots||[])[n-1];return sh?sh.id:("hop "+n);}
function hopOf(n){return ((S&&S.hops)||[]).find(h=>h.hop===n);}
function openHop(n){
  const h=hopOf(n); if(!h) return; sel=n;
  const v=$("pvideo"); v.src="/h3_ref_chain/hop_clip?key="+encodeURIComponent(h.key); v.muted=false;
  $("ptitle").textContent=n+" · "+label(n); $("player").hidden=false; v.play().catch(()=>{});
  for(const [k,t] of tiles) t.classList.toggle("sel",k===n);
  $("player").scrollIntoView({behavior:"smooth",block:"start"});
}
$("close").onclick=()=>{const v=$("pvideo");v.pause();v.removeAttribute("src");v.load();$("player").hidden=true;for(const t of tiles.values())t.classList.remove("sel");};
$("prev").onclick=()=>{for(let n=sel-1;n>=1;n--) if(hopOf(n)) return openHop(n);};
$("next").onclick=()=>{for(let n=sel+1;n<=(S?S.of:0);n++) if(hopOf(n)) return openHop(n);};
$("pvideo").addEventListener("ended",()=>$("next").click());
function tile(n){
  let t=tiles.get(n); if(t) return t;
  t=document.createElement("button"); t.type="button"; t.className="tile";
  const sh=document.createElement("div"); sh.className="shot";
  const ph=document.createElement("span"); ph.className="ph"; ph.textContent="waiting";
  const no=document.createElement("span"); no.className="no"; no.textContent=n;
  const m=document.createElement("div"); m.className="meta";
  const b=document.createElement("b"); const tt=document.createElement("span"); tt.className="t";
  m.append(b,tt); sh.append(ph,no); t.append(sh,m); t.onclick=()=>openHop(n);
  const g=$("grid"); const after=[...tiles.keys()].filter(k=>k>n).sort((a,b)=>a-b)[0];
  g.insertBefore(t, after?tiles.get(after):null); tiles.set(n,t); io&&io.observe(t); return t;
}
async function poll(){
  try{ const r=await fetch("/h3_ref_chain/monitor/state",{cache:"no-store"}); S=await r.json(); $("err").hidden=true; }
  catch(e){ $("err").hidden=false; $("err").textContent="Can't reach ComfyUI. Is it running, and (from another device) started with --listen?"; return; }
  const of=S.of||0, hops=S.hops||[], last=hops.length?hops[hops.length-1].hop:0, running=!!S.running;
  const busy=running&&last<of;
  const title=S.title||"";
  if(title){$("title").replaceChildren();const a=document.createElement("span");a.className="t";a.textContent=title;$("title").append(a,document.createElement("br"),busy?"rendering":(of&&last>=of?"rendered":"render"));document.title=title+" · Render Monitor";}
  else if(of){$("title").replaceChildren();const a=document.createElement("span");a.className="t";a.textContent=of+" hops";$("title").append(a,document.createElement("br"),busy?"rendering":"rendered");}
  const portrait=hops.length&&hops[0].h>hops[0].w;
  $("grid").classList.toggle("portrait",!!portrait);
  if(hops.length){const h0=hops[0];$("sub").textContent=of+" hops · "+h0.w+"×"+h0.h+" · "+(h0.pin_mech||"chain")+". Each tile starts looping as soon as its hop is finished. Tap one to watch it with sound.";}
  const pill=$("pill");
  if(busy){pill.className="pill run";pill.textContent="RENDERING";}
  else if(of&&last>=of){pill.className="pill done";pill.textContent="DONE";}
  else {pill.className="pill idle";pill.textContent=running?"RUNNING":"IDLE";}
  $("hop").textContent=of?(Math.min(last+(busy?1:0),of)+" / "+of):"–";
  $("upd").textContent=hhmm(S.now);
  let per=null;
  if(hops.length>=2){const a=hops[0],b=hops[hops.length-1];const f=hops.slice(1).reduce((x,h)=>x+h.frames,0);per=(b.written-a.written)/Math.max(1,f);}
  if(per){const avgF=hops.reduce((x,h)=>x+h.frames,0)/hops.length;$("per").textContent=Math.max(1,Math.round(per*avgF/60))+" min";$("eta").textContent=busy?hhmm(S.last_written+per*avgF*(of-last)):(of&&last>=of?"done":"–");}
  else {$("per").textContent="–";$("eta").textContent=busy?"after hop 2":"–";}
  const strip=$("strip"); strip.replaceChildren();
  for(let i=1;i<=of;i++){const d=document.createElement("div");d.className="seg"+(i<=last?" done":(busy&&i===last+1?" now":""));d.style.setProperty("--c",colourOf(i));
    const sh=(S.shots||[])[i-1]; d.style.flex=(sh&&parseFloat(sh.dur))?parseFloat(sh.dur)+" 1 0":"1 1 0";
    const k=document.createElement("i");k.textContent=i;d.appendChild(k);d.title=i+" · "+label(i);strip.appendChild(d);}
  const leg=$("legend"); leg.replaceChildren();
  for(const [p,c] of colours()){const s=document.createElement("span");s.style.setProperty("--c",c);s.textContent=p;leg.appendChild(s);}
  for(let i=1;i<=of;i++) tile(i);
  for(const [n,t] of [...tiles]){ if(n>of){io&&io.unobserve(t);t.remove();tiles.delete(n);} }
  for(let n=1;n<=of;n++){
    const t=tiles.get(n), sh=t.querySelector(".shot"), h=hopOf(n), s=(S.shots||[])[n-1];
    t.style.setProperty("--c",colourOf(n)); t.classList.toggle("now",busy&&n===last+1);
    t.querySelector(".meta b").textContent=(s&&s.place?s.place+" · ":"")+label(n);
    if(h){
      t.querySelector(".meta .t").textContent=hhmm(h.written)+" · "+(h.frames/h.fps).toFixed(1)+" s";
      if(sh.dataset.key!==h.key){
        sh.dataset.key=h.key; sh.querySelectorAll("video").forEach(v=>v.remove());
        const v=document.createElement("video"); v.muted=true; v.loop=true; v.playsInline=true; v.preload="none";
        v.src="/h3_ref_chain/hop_clip?key="+encodeURIComponent(h.key);
        sh.insertBefore(v,sh.firstChild); sh.querySelector(".ph").hidden=true;
        if(!document.hidden) v.play().catch(()=>{});
      }
    } else {
      sh.dataset.key=""; sh.querySelectorAll("video").forEach(v=>v.remove());
      const ph=sh.querySelector(".ph"); ph.hidden=false; ph.textContent=(busy&&n===last+1)?"rendering…":"waiting";
      t.querySelector(".meta .t").textContent=s&&s.dur?s.dur:"";
    }
  }
}
poll(); setInterval(()=>{ if(!document.hidden) poll(); },15000);
</script></body></html>"""
