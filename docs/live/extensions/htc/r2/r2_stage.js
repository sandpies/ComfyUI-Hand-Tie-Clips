/**
 * Round-2 timeline stage: a real monitor + scrubber in the node.
 *
 * It reads the same run record the shipped timeline writes
 * (`node.properties.h3_timeline_run`) and plays `/h3_ref_chain/hop_clip`
 * (or `/h3_ref_chain/seam_clip` when inspecting a join).
 * Selecting a hop calls back to the shell, which drives the Script pane.
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { el, findNodeByQualifiedId } from "../editor/widget_utils.js";
import {
    RUN_PROP, PENDING_PROP, hopKey, timelineRec, clipURL, seamURL, spriteURL,
    durationOf, deliveredSeconds, chainSeconds, hopStarts, fmtTime, cachedCount,
    forecastText, snapshotNow, nodeResolutionInfo,
} from "./r2_store.js";

export function createStage(node, { getShots, getActive, onSelect } = {}) {
    const shots = () => getShots() || [];
    const root = el("div", "r2-stage");

    /* -- head ------------------------------------------------------------- */
    const head = el("div", "r2-stage-head");
    head.appendChild(el("span", "title", "Timeline"));
    const headSub = el("span", "sub");
    head.appendChild(headSub);
    head.appendChild(el("span", "spacer"));
    const fitChip = el("span", "r2-chip", "fit");
    const fpsChip = el("span", "r2-chip", "24 fps");
    const expandBtn = el("button", "r2-mini", "\u26f6");
    expandBtn.type = "button";
    expandBtn.title = "Fullscreen timeline (T)";

    expandBtn.addEventListener("click", () => {
        const tab = node._h3R2?.root?.querySelector('[data-r2-tab="timeline"]');
        tab?.click();
    });
    const wallBtn = el("button", "r2-chip r2-wallbtn", "▦ wall");
    wallBtn.type = "button";
    wallBtn.title = "Wall: every rendered hop looping at once (click a tile to open it)";
    // Pop the wall out into the render monitor page (monitor.py): a browser tab
    // with the desktop layout, or a phone-sized window. The phone button also
    // copies the address a phone on the same network can open (needs --listen).
    const MONITOR = "/h3_ref_chain/monitor";
    // The offline docs/live demo serves the page beside itself (a pop-out at the
    // site root would leave its service worker's scope); ComfyUI never sets this.
    const MONITOR_PAGE = globalThis.HTC_MONITOR_PAGE || MONITOR;
    const popDesk = el("button", "r2-chip r2-wallbtn r2-popbtn", "\u29c9 browser");
    popDesk.type = "button";
    popDesk.title = "Open the wall in a browser tab (desktop layout; click a hop to play it with sound)";
    popDesk.addEventListener("click", () => {
        window.open(`${MONITOR_PAGE}?view=desktop`, "htc_monitor_desktop");
    });
    const popPhone = el("button", "r2-chip r2-wallbtn r2-popbtn", "\u{1F4F1} phone");
    popPhone.type = "button";
    popPhone.title = "Open the phone view in a small window and copy its link for your phone";
    popPhone.addEventListener("click", async () => {
        window.open(`${MONITOR_PAGE}?view=phone`, "htc_monitor_phone", "popup,width=430,height=900");
        let link = null;
        let why = "";
        try {
            const st = await (await fetch(`${MONITOR}/state`)).json();
            link = st?.links?.lan ? `${st.links.lan}${MONITOR}?view=phone` : null;
            if (!link) why = "start ComfyUI with --listen to open it on your phone";
        } catch (e) { why = "monitor not reachable"; }
        if (link) {
            try { await navigator.clipboard.writeText(link); why = "link copied"; }
            catch (e) { why = link; }
        }
        popPhone.title = link ? `Phone link: ${link}` : why;
        const was = "\u{1F4F1} phone";
        popPhone.textContent = why.length > 34 ? "\u{1F4F1} see tooltip" : `\u{1F4F1} ${why}`;
        setTimeout(() => { popPhone.textContent = was; }, 3500);
    });
    head.append(popDesk, popPhone, wallBtn, fitChip, fpsChip, expandBtn);
    root.appendChild(head);

    /* -- body ------------------------------------------------------------- */
    const body = el("div", "r2-stage-body");

    const monitor = el("div", "r2-monitor");
    const frame = el("div", "r2-frame");
    const video = el("video", "r2-video");
    video.playsInline = true;
    video.preload = "metadata";
    const placeholder = el("div", "r2-placeholder");
    const playBtn = el("button", "r2-bigplay", "\u25b6");
    playBtn.type = "button";
    const label = el("span", "r2-flabel", "hop 1");
    const tc = el("span", "r2-tc", "00:00.0");
    frame.append(video, placeholder, playBtn, label, tc);
    monitor.appendChild(frame);
    const mmeta = el("div", "r2-mmeta");
    const mleft = el("span", null, "9:16");
    const mmid = el("span", null, "768\u00d71344");
    const mright = el("span", null, "not cached");
    mmeta.append(mleft, mmid, mright);
    monitor.appendChild(mmeta);
    body.appendChild(monitor);

    const side = el("div", "r2-stage-side");
    const now = el("div", "r2-now");
    const noEl = el("span", "r2-no", "1");
    const nameEl = el("b", null, "s1");
    const infoEl = el("span", "r2-muted");
    const stateEl = el("span", "r2-ok", "cached");
    now.append(noEl, nameEl, infoEl, el("span", "spacer"), stateEl);
    side.appendChild(now);

    const scrub = el("div", "r2-scrub");
    const segs = el("div", "r2-segs");
    const headEl = el("div", "r2-playhead");
    scrub.append(segs, headEl);
    side.appendChild(scrub);

    const ticks = el("div", "r2-ticks");
    side.appendChild(ticks);

    const transport = el("div", "r2-transport");
    const prevBtn = el("button", "r2-mini", "\u23ee");
    const smallPlay = el("button", "r2-mini", "\u25b6 play");
    const nextBtn = el("button", "r2-mini", "\u23ed");
    prevBtn.type = smallPlay.type = nextBtn.type = "button";
    const tc2 = el("span", "r2-timecode", "00:00.0");
    const totalTc = el("span", "r2-muted", "/ 01:41.4");
    transport.append(prevBtn, smallPlay, nextBtn, tc2, totalTc, el("span", "spacer"),
        el("span", "r2-muted", "space play \u00b7 \u2190\u2192 frame"));
    side.appendChild(transport);

    const joins = el("div", "r2-joins");
    side.appendChild(joins);
    const hoplist = el("div", "r2-hoplist");
    side.appendChild(hoplist);
    const forecast = el("div", "r2-forecast");
    side.appendChild(forecast);
    body.appendChild(side);
    root.appendChild(body);

    const film = el("div", "r2-film");
    root.appendChild(film);

    /* -- wall: every cached hop looping, muted; only visible tiles play ---- */
    const WALL_PROP = "h3_r2_wall";
    const wall = el("div", "r2-wall");
    wall.hidden = true;
    root.insertBefore(wall, film);
    const wallIO = typeof IntersectionObserver === "function"
        ? new IntersectionObserver((es) => {
            for (const e of es) {
                const v = e.target.querySelector("video");
                if (!v) continue;
                // A tile's clip is requested only once it is on screen, so the server
                // builds the visible ones first instead of the whole wall at once.
                if (e.isIntersecting && !v.getAttribute("src") && v.dataset.src) v.src = v.dataset.src;
                if (e.isIntersecting && !document.hidden && !wall.hidden) v.play?.().catch(() => {});
                else v.pause?.();
            }
        }, { root: wall, threshold: 0.15 })
        : null;
    function wallVideos() { return Array.from(wall.querySelectorAll("video")); }
    function wallPauseAll() { wallVideos().forEach((v) => v.pause?.()); }
    const onVis = () => { if (document.hidden || wall.hidden) wallPauseAll(); else buildWall(); };
    document.addEventListener("visibilitychange", onVis);
    function setWall(on) {
        node.properties ??= {};
        node.properties[WALL_PROP] = !!on;
        wall.hidden = !on;
        body.hidden = !!on;
        wallBtn.classList.toggle("on", !!on);
        if (on) { stop(); buildWall(); } else { wallPauseAll(); }
    }
    function buildWall() {
        if (wall.hidden || !root.isConnected) return;
        const list = currentShots();
        wall.classList.toggle("portrait", !nodeResolutionInfo(node).isLandscape && !nodeResolutionInfo(node).isSquare);
        while (wall.children.length > list.length) {
            const last = wall.lastElementChild;
            wallIO?.unobserve(last);
            last.querySelector("video")?.pause?.();
            last.remove();
        }
        list.forEach((s, i) => {
            let t = wall.children[i];
            if (!t) {
                t = el("button", "r2-wtile");
                t.type = "button";
                t.append(el("span", "ph", "not rendered"), el("span", "no", String(i + 1)), el("span", "cap"));
                t.addEventListener("click", () => { setWall(false); pick(i); play(); });
                wall.appendChild(t);
                wallIO?.observe(t);
            }
            t.querySelector(".no").textContent = String(i + 1);
            t.querySelector(".cap").textContent = `${s.id || "s" + (i + 1)} · ${durationOf(node, s)}`;
            t.classList.toggle("sel", i === active());
            const key = hopKey(node, i);
            const ph = t.querySelector(".ph");
            if (key && t.dataset.key !== key) {
                t.dataset.key = key;
                t.querySelector("video")?.remove();
                const v = el("video");
                v.muted = true; v.loop = true; v.playsInline = true; v.preload = "none";
                if (wallIO) v.dataset.src = clipURL(key);   // loaded when the tile scrolls into view
                else { v.src = clipURL(key); if (!document.hidden) v.play?.().catch(() => {}); }
                t.insertBefore(v, t.firstChild);
                ph.hidden = true;
                if (wallIO) { wallIO.unobserve(t); wallIO.observe(t); }  // re-fires for a tile already on screen
            } else if (!key) {
                t.dataset.key = "";
                t.querySelector("video")?.remove();
                ph.hidden = false;
                ph.textContent = recState(i) === "queued" ? "not rendered" : "…";
            }
        });
    }
    wallBtn.addEventListener("click", () => setWall(wall.hidden));

    /* -- state ------------------------------------------------------------ */
    const st = { t: 0, hop: 0, playing: false, timer: 0, key: null };

    function currentShots() { return shots(); }
    function active() { return Math.max(0, Math.min(getActive?.() ?? 0, currentShots().length - 1)); }

    function setPlayGlyph() {
        const glyph = st.playing ? "\u275a\u275a" : "\u25b6";
        playBtn.textContent = glyph;
        smallPlay.textContent = `${glyph} ${st.playing ? "pause" : "play"}`;
    }

    function paintAspect() {
        const info = nodeResolutionInfo(node);
        mleft.textContent = info.aspectLabel;
        if (!(video.videoWidth && video.videoHeight && !video.hidden)) {
            mmid.textContent = info.dimsLabel;
        }
        monitor.classList.toggle("landscape", info.isLandscape);
        monitor.classList.toggle("square", info.isSquare);
    }

    video.addEventListener("loadedmetadata", () => {
        if (video.videoWidth && video.videoHeight) {
            mmid.textContent = `${video.videoWidth}\u00d7${video.videoHeight}`;
            monitor.classList.toggle("landscape", video.videoWidth > video.videoHeight);
            monitor.classList.toggle("square", video.videoWidth === video.videoHeight);
        }
    });

    function paint() {
        const list = currentShots();
        const total = Math.max(0.1, chainSeconds(node, list));
        const pct = Math.max(0, Math.min(100, (st.t / total) * 100));
        headEl.style.left = `${pct}%`;
        const t = fmtTime(st.t);
        tc.textContent = t;
        tc2.textContent = t;
        totalTc.textContent = `/ ${fmtTime(total)}`;
        setPlayGlyph();
    }

    function recState(i) {
        const h = timelineRec(node)?.hops?.[i];
        if (!h?.key) return "queued";
        return h.status || "cached";
    }

    function playSeam(i) {
        const kPrev = hopKey(node, i);
        const kNext = hopKey(node, i + 1);
        pick(i + 1);
        if (!kPrev || !kNext) return;
        const url = seamURL(kPrev, kNext);
        st.key = `seam:${kPrev}:${kNext}`;
        video.dataset.key = st.key;
        video.src = url;
        video.load?.();
        video.hidden = false;
        placeholder.hidden = true;
        label.textContent = `join ${i + 1}\u2192${i + 2} \u00b7 seam`;
        st.playing = true;
        video.play?.().catch(() => { st.playing = false; paint(); });
        paint();
    }

    function build() {
        const list = currentShots();
        const starts = hopStarts(node, list);
        const total = Math.max(0.1, chainSeconds(node, list));
        const cached = cachedCount(node, list);
        headSub.textContent = list.length
            ? `${cached} of ${list.length} cached \u00b7 ${total.toFixed(1)} s`
            : "no shots";
        paintAspect();
        mright.textContent = `${cached} cached`;
        forecast.textContent = forecastText(node, list);

        segs.textContent = "";
        list.forEach((s, i) => {
            const deliv = deliveredSeconds(node, s, i);
            const seg = el("div", "r2-seg " + (recState(i) === "queued" ? "queued" : "cached"));
            seg.style.flex = `${deliv} 1 0`;
            seg.appendChild(el("span", "sn", String(i + 1)));
            segs.appendChild(seg);
            if (i < list.length - 1) {
                const at = (starts[i] + deliv) / total;
                const mark = el("i", "r2-joinmark");
                mark.style.left = `${at * 100}%`;
                segs.appendChild(mark);
            }
        });

        ticks.textContent = "";
        const tickAt = [0, 0.2, 0.4, 0.6, 0.8, 1];
        for (const f of tickAt) {
            ticks.appendChild(el("span", null, fmtTime(total * f)));
        }

        joins.textContent = "";
        for (let i = 0; i < Math.max(0, list.length - 1); i += 1) {
            const j = el("button", "r2-join");
            j.type = "button";
            const th = el("span", "th");
            const kPrev = hopKey(node, i);
            const kNext = hopKey(node, i + 1);
            if (kPrev) th.style.backgroundImage = `url("${spriteURL(kPrev, 1)}")`;
            j.append(th, el("span", "jl", `${i + 1}\u2192${i + 2}`));
            j.title = kPrev && kNext
                ? `Play seam preview: hop ${i + 1} \u2192 ${i + 2}`
                : `Join hop ${i + 1} \u2192 ${i + 2}`;
            j.addEventListener("click", () => playSeam(i));
            joins.appendChild(j);
        }

        hoplist.textContent = "";
        list.forEach((s, i) => {
            const r = el("button", "r2-hoprow");
            r.type = "button";
            r.append(
                el("span", "n", String(i + 1)),
                el("span", "nm", s.id || `s${i + 1}`),
                el("span", "d", durationOf(node, s)),
                el("span", "st " + (recState(i) === "queued" ? "q" : ""),
                    recState(i) === "queued" ? "queued" : (s.locked ? "locked" : "cached")),
            );
            r.addEventListener("click", () => pick(i));
            hoplist.appendChild(r);
        });

        film.textContent = "";
        list.forEach((s, i) => {
            const deliv = deliveredSeconds(node, s, i);
            const c = el("button", "r2-cell" + (i === active() ? " sel" : "")
                + (s.locked ? " locked" : "") + (recState(i) === "queued" ? " queued" : ""));
            c.type = "button";
            c.style.flex = `${deliv} 1 0`;
            const key = hopKey(node, i);
            if (key) {
                c.style.backgroundImage =
                    `linear-gradient(rgba(0,0,0,.15),rgba(0,0,0,.55)), url("${spriteURL(key, 1)}")`;
                c.style.backgroundSize = "cover";
            }
            c.append(el("span", "cap",
                `${i + 1} \u00b7 ${recState(i) === "queued" ? "queued" : durationOf(node, s)}`));
            c.addEventListener("click", () => pick(i));
            film.appendChild(c);
        });
    }

    function show(i) {
        paintAspect();
        const list = currentShots();
        if (!list.length) {
            st.hop = 0;
            st.t = 0;
            label.textContent = "no shots";
            placeholder.textContent = "Add a shot to see the timeline";
            placeholder.hidden = false;
            video.hidden = true;
            paint();
            return;
        }
        const idx = Math.max(0, Math.min(i, list.length - 1));
        const starts = hopStarts(node, list);
        const keyNow = hopKey(node, idx);
        const same = st.hop === idx && st.key === keyNow && keyNow;
        if (!same) st.t = starts[idx] || 0;
        st.hop = idx;
        const s = list[idx];
        noEl.textContent = String(idx + 1);
        nameEl.textContent = s.id || `s${idx + 1}`;
        const joinMode = idx === 0
            ? "start"
            : (s.anchor === "restart" ? "restart" : (s.directives?.join || "continuous"));
        infoEl.textContent = `${durationOf(node, s)} \u00b7 ${joinMode}`;
        const state = recState(idx);
        stateEl.textContent = state;
        stateEl.className = state === "queued" ? "r2-warn" : "r2-ok";
        label.textContent = `hop ${idx + 1} \u00b7 ${state}`;
        mright.textContent = state;
        const key = keyNow;
        st.key = key;
        if (key) {
            if (video.dataset.key !== key) {
                video.dataset.key = key;
                video.src = clipURL(key);
                video.load?.();
            }
            video.hidden = false;
            placeholder.hidden = true;
        } else {
            video.pause?.();
            video.removeAttribute("src");
            video.dataset.key = "";
            video.load?.();
            video.hidden = true;
            placeholder.hidden = false;
            placeholder.textContent = `hop ${idx + 1} \u00b7 not cached yet`;
        }
        Array.from(film.children || []).forEach((c, j) => c.classList.toggle("sel", j === idx));
        Array.from(hoplist.children || []).forEach((r, j) => r.classList.toggle("sel", j === idx));
        paint();
    }

    function pick(i) {
        const list = currentShots();
        if (!list.length) return;
        const idx = Math.max(0, Math.min(i, list.length - 1));
        show(idx);
        onSelect?.(idx, "stage");
    }

    function chainAt(t) {
        const list = currentShots();
        const starts = hopStarts(node, list);
        let hop = 0;
        for (let i = 0; i < starts.length; i += 1) {
            if (t >= starts[i]) hop = i;
        }
        return { hop, offset: Math.max(0, t - (starts[hop] || 0)) };
    }

    function setTime(t) {
        const list = currentShots();
        const total = Math.max(0.1, chainSeconds(node, list));
        st.t = Math.max(0, Math.min(total, t));
        const at = chainAt(st.t);
        if (at.hop !== active()) {
            show(at.hop);
            onSelect?.(at.hop, "stage");
        }
        if (st.key && !String(st.key).startsWith("seam:") && video.readyState >= 1) {
            try { video.currentTime = Math.min(at.offset, video.duration || at.offset); } catch (_) { /* */ }
        }
        paint();
    }

    function stop() {
        st.playing = false;
        if (st.timer) { clearInterval(st.timer); st.timer = 0; }
        video.pause?.();
        paint();
    }

    function play() {
        if (st.playing) { stop(); return; }
        if (st.key) {
            st.playing = true;
            video.play?.().catch(() => { st.playing = false; paint(); });
            paint();
            return;
        }
        st.playing = true;
        st.timer = setInterval(() => {
            st.t += 0.28;
            const at = chainAt(st.t);
            if (at.hop !== st.hop) {
                const key = hopKey(node, at.hop);
                show(at.hop);
                onSelect?.(at.hop);
                if (key) { stop(); return; }
            }
            const total = chainSeconds(node, currentShots());
            if (st.t >= total) { st.t = total; stop(); }
            paint();
        }, 120);
        paint();
    }

    /* -- events ----------------------------------------------------------- */
    playBtn.addEventListener("click", play);
    smallPlay.addEventListener("click", play);
    prevBtn.addEventListener("click", () => pick(active() - 1));
    nextBtn.addEventListener("click", () => pick(active() + 1));
    scrub.addEventListener("click", (e) => {
        const r = scrub.getBoundingClientRect();
        const list = currentShots();
        const total = Math.max(0.1, chainSeconds(node, list));
        setTime(((e.clientX - r.left) / r.width) * total);
    });
    video.addEventListener("timeupdate", () => {
        if (!st.key || String(st.key).startsWith("seam:") || !st.playing) return;
        const starts = hopStarts(node, currentShots());
        st.t = (starts[st.hop] || 0) + (video.currentTime || 0);
        paint();
    });
    video.addEventListener("ended", () => {
        if (String(st.key).startsWith("seam:")) {
            stop();
            show(active());
            return;
        }
        // Issue #2: advance only into a hop that has a rendered clip. A
        // mid-run chain has later hops "not cached yet"; play() on one of
        // those starts the storyboard timer and keeps scrubbing through
        // placeholders, so stop on the last rendered clip instead.
        const next = st.hop + 1;
        if (next < currentShots().length && hopKey(node, next)) {
            pick(next);
            play();
        } else {
            stop();
        }
    });
    video.addEventListener("play", () => { st.playing = true; paint(); });
    video.addEventListener("pause", () => { st.playing = false; paint(); });

    document.addEventListener("keydown", (e) => {
        if (!root.isConnected) return;
        if (!root.contains(e.target)) return;
        if (e.target && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
        if (e.code === "Space") { e.preventDefault(); play(); }
        else if (e.key === "ArrowLeft") { e.preventDefault(); setTime(st.t - 1 / 24); }
        else if (e.key === "ArrowRight") { e.preventDefault(); setTime(st.t + 1 / 24); }
    });

    const onQueued = () => {
        node.properties ??= {};
        node.properties[PENDING_PROP] = snapshotNow(node, currentShots());
    };

    const onPreview = (ev) => {
        const d = ev.detail;
        if (d?.node_id != null && app?.graph) {
            const matched = findNodeByQualifiedId(app.graph, d.node_id);
            if (matched && matched !== node) return;
        }
        if (Array.isArray(d?.ht_previs_warn)) {
            const rec0 = node.properties?.[RUN_PROP];
            if (rec0) {
                rec0.previs_warn = d.ht_previs_warn;
                node.properties[RUN_PROP] = rec0;
                node._h3Warn?.show?.(d.ht_previs_warn);
                build();
            }
            return;
        }
        if (!d?.timeline) return;
        const hop = Number(d.hop) || 0;
        if (hop < 1) return;
        node.properties ??= {};
        let rec = node.properties[RUN_PROP];
        if (!rec || hop === 1) {
            const old = rec?.hops || [];
            rec = {
                at: Date.now(),
                total: Number(d.total) || old.length,
                snapshot: node.properties[PENDING_PROP] || rec?.snapshot || null,
                hops: old.map((h) => (h ? { ...h, older: true } : h)),
            };
            delete node.properties[PENDING_PROP];
            node.properties[RUN_PROP] = rec;
        }
        rec.total = Number(d.total) || rec.total;
        rec.hops = rec.hops || [];
        rec.hops[hop - 1] = {
            ...d.timeline,
            pin_mech: d.pin_mech || null,
            unpaired: Boolean(d.unpaired),
        };
        rec.hops.length = Math.max(rec.hops.length, rec.total);
        node.properties[RUN_PROP] = rec;
        build();
        show(active());
        buildWall();
    };
    api.addEventListener("promptQueued", onQueued);
    api.addEventListener("h3_refchain_preview", onPreview);

    function destroy() {
        stop();
        wallPauseAll();
        wallIO?.disconnect();
        document.removeEventListener("visibilitychange", onVis);
        api.removeEventListener("promptQueued", onQueued);
        api.removeEventListener("h3_refchain_preview", onPreview);
    }

    function render() {
        build();
        show(active());
        buildWall();
    }

    if (node.properties?.[WALL_PROP]) setWall(true);
    render();

    return {
        root,
        render,
        show,
        pick,
        active,
        setTime,
        destroy,
    };
}
