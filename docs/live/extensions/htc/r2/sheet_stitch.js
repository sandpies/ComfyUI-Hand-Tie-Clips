/**
 * Sheet Stitcher (R2 RefMod tab): lay the RefMod stills out as one character
 * sheet, in the browser, at the stills' own pixels.
 *
 * No model runs: every still is drawn as-is (aspect kept, never cropped), so a
 * set of 2 MP singles becomes one large sheet with exactly the faces they had.
 * At "Overall image size" 100 % no still loses pixels: the most-shrunk still
 * lands at exactly 1:1 and the others (a hero, a smaller single) are enlarged
 * to fit around it. (11-18: the first cut anchored on "nothing enlarged", which
 * shrank hero-layout extras to ~30 % and turned 6x 2 MP into a ~5 MP sheet.)
 *
 * The layout is computed in shape units first (`layoutSheet`, pure, tested by
 * tools/check_sheet_stitch.mjs) and scaled to pixels last, so margins and gaps
 * are an exact percentage of the sheet's longer side.
 */
import { el, button } from "../editor/widget_utils.js";
import { upload, viewUrl } from "../editor/media_picker.js";

export const ARRANGEMENTS = [
    { id: "auto", label: "Auto", tip: "Rows chosen so the sheet comes out closest to 16:9." },
    { id: "row", label: "Single row", tip: "Every still side by side, same height." },
    { id: "grid", label: "Grid", tip: "Equal cells; each still fitted whole inside its cell." },
    { id: "hero_left", label: "Hero left", tip: "First still big on the left, the rest stacked beside it." },
    { id: "hero_right", label: "Hero right", tip: "First still big on the right, the rest stacked beside it." },
    { id: "hero_top", label: "Hero top", tip: "First still big on top, the rest underneath." },
    { id: "lossless", label: "Lossless (1:1 pixels)", tip: "Every still at its own pixel size, nothing resized or cropped; the tightest rows-or-columns packing is picked automatically. With \"Fit for H3\" the short side is a ceiling, not a target." },
];

export const SHEET_DEFAULTS = {
    arrangement: "auto",
    hero_pct: 45,
    rows: 0,
    split: "",
    margin_pct: 3,
    gap_pct: 3,
    link_gap: true,
    size_pct: 100,
    size_mode: "short",      // "short": short side = short_px (H3 input target) | "native": size_pct of native
    short_px: 2048,
    align: "center",
    background: "#000000",
};

const MAX_SIDE = 16384;          // browser canvas side limit (Chrome/Firefox safe)
const MAX_AREA = 150e6;          // stay well under the ~268 MP canvas area limit
const AUTO_ASPECT = 16 / 9;

const asp = (it) => it.w / it.h;

function median(xs) {
    const s = [...xs].sort((a, b) => a - b);
    const m = s.length >> 1;
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** "2,4" -> [2, 4] when the numbers are positive integers summing to n, else null. */
export function parseSplit(text, n) {
    const parts = String(text || "").split(/[,\s/]+/).filter(Boolean).map(Number);
    if (!parts.length || parts.some((x) => !Number.isInteger(x) || x < 1)) return null;
    return parts.reduce((a, b) => a + b, 0) === n ? parts : null;
}

/** n items over `rows` rows, extra items in the top rows. */
export function balancedCounts(n, rows) {
    const r = Math.max(1, Math.min(n, Math.round(rows) || 1));
    const base = Math.floor(n / r), extra = n % r;
    return Array.from({ length: r }, (_, i) => base + (i < extra ? 1 : 0));
}

/** Justified rows: every row exactly `W` wide, each still at its own aspect. */
function justify(items, counts, W, gap, offset = 0) {
    const rects = [];
    let y = 0, k = 0;
    counts.forEach((c, ri) => {
        const row = items.slice(k, k + c);
        const sa = row.reduce((s, it) => s + asp(it), 0);
        const h = Math.max(1e-6, (W - gap * (c - 1)) / sa);
        let x = 0;
        row.forEach((it, j) => {
            const w = h * asp(it);
            rects.push({ i: offset + k + j, x, y, w, h });
            x += w + gap;
        });
        y += h + (ri < counts.length - 1 ? gap : 0);
        k += c;
    });
    return { rects, w: W, h: y };
}

/** Whole still inside a box, aspect kept. align: start | center | end. */
function fit(it, bx, by, bw, bh, align, i) {
    const s = Math.min(bw / it.w, bh / it.h);
    const w = it.w * s, h = it.h * s;
    const f = align === "start" ? 0 : align === "end" ? 1 : 0.5;
    return { i, x: bx + (bw - w) * f, y: by + (bh - h) * f, w, h };
}

/** Pick the row count whose justified block is closest (log aspect) to `target`. */
function bestCounts(items, target, W = 1000) {
    let best = null;
    for (let r = 1; r <= items.length; r++) {
        const counts = balancedCounts(items.length, r);
        const b = justify(items, counts, W, 0);
        const err = Math.abs(Math.log((b.w / b.h) / target));
        if (!best || err < best.err - 1e-9) best = { counts, err };
    }
    return best.counts;
}

function countsFor(items, opts, autoTarget) {
    const n = items.length;
    const split = parseSplit(opts.split, n);
    if (split) return split;
    if (opts.rows > 0) return balancedCounts(n, opts.rows);
    return bestCounts(items, autoTarget);
}

/** Content block (no margin) in shape units for one gap value. */
function layoutContent(items, opts, gap) {
    const n = items.length;
    const arr = opts.arrangement;
    const align = opts.align || "center";

    if (arr === "row") return justify(items, [n], 1000, gap);

    if (arr === "grid") {
        const split = parseSplit(opts.split, n);
        const counts = split || (opts.rows > 0
            ? balancedCounts(n, opts.rows)
            : balancedCounts(n, Math.ceil(n / Math.ceil(Math.sqrt(n)))));
        const cols = Math.max(...counts);
        const ch = 1000, cw = median(items.map(asp)) * ch;
        const W = cols * cw + gap * (cols - 1);
        const rects = [];
        let k = 0;
        counts.forEach((c, ri) => {
            const rowW = c * cw + gap * (c - 1);
            const f = align === "start" ? 0 : align === "end" ? 1 : 0.5;
            const x0 = (W - rowW) * f;
            for (let j = 0; j < c; j++, k++) {
                rects.push(fit(items[k], x0 + j * (cw + gap), ri * (ch + gap), cw, ch, align, k));
            }
        });
        return { rects, w: W, h: counts.length * ch + gap * (counts.length - 1) };
    }

    if (arr.startsWith("hero") && n > 1) {
        const hero = items[0], rest = items.slice(1);
        const p = Math.min(0.85, Math.max(0.15, (Number(opts.hero_pct) || 45) / 100));
        const hh = 1000, hw = asp(hero) * hh;
        const rects = [];
        if (arr === "hero_top") {
            const W = hw;
            const regionH = Math.max(1, hh / p - hh - gap);
            const counts = countsFor(rest, opts, W / regionH);
            const b = justify(rest, counts, W, gap, 1);
            const s = Math.min(1, regionH / b.h);
            const f = align === "start" ? 0 : align === "end" ? 1 : 0.5;
            const ox = (W - b.w * s) * f;
            const oy = hh + gap + (regionH - b.h * s) * f;
            rects.push({ i: 0, x: 0, y: 0, w: hw, h: hh });
            for (const r of b.rects) rects.push({ i: r.i, x: ox + r.x * s, y: oy + r.y * s, w: r.w * s, h: r.h * s });
            return { rects, w: W, h: hh + gap + regionH };
        }
        const regionW = Math.max(1, hw / p - hw - gap);
        const counts = countsFor(rest, opts, regionW / hh);
        const b = justify(rest, counts, regionW, gap, 1);
        const s = Math.min(1, hh / b.h);
        const f = align === "start" ? 0 : align === "end" ? 1 : 0.5;
        const left = arr === "hero_left";
        const rx = left ? hw + gap : 0;
        const ox = rx + (regionW - b.w * s) * f;
        const oy = (hh - b.h * s) * f;
        rects.push({ i: 0, x: left ? 0 : regionW + gap, y: 0, w: hw, h: hh });
        for (const r of b.rects) rects.push({ i: r.i, x: ox + r.x * s, y: oy + r.y * s, w: r.w * s, h: r.h * s });
        return { rects, w: hw + gap + regionW, h: hh };
    }

    // auto (and a hero mode with a single still)
    return justify(items, countsFor(items, opts, AUTO_ASPECT), 1000, gap);
}

/**
 * Lossless packing: every still at its native pixel size, on integer pixels, in
 * groups along `axis` ("rows": left to right, groups stacked down; "cols": top
 * to bottom, groups side by side). Nothing is scaled, so the saved PNG holds
 * each still byte-for-byte (drawImage at 1:1 on whole pixels is a plain copy).
 */
function packLossless(items, counts, axis, gap, align) {
    const f = align === "start" ? 0 : align === "end" ? 1 : 0.5;
    const along = (it) => (axis === "rows" ? it.w : it.h);
    const across = (it) => (axis === "rows" ? it.h : it.w);
    const groups = [];
    let k = 0;
    for (const c of counts) {
        const g = items.slice(k, k + c).map((it, j) => ({ it, i: k + j }));
        k += c;
        groups.push({
            g,
            len: g.reduce((s, { it }) => s + along(it), 0) + gap * (c - 1),
            thick: Math.max(...g.map(({ it }) => across(it))),
        });
    }
    const LEN = Math.max(...groups.map((x) => x.len));
    const THICK = groups.reduce((s, x) => s + x.thick, 0) + gap * (groups.length - 1);
    const rects = [];
    let a = 0;
    for (const grp of groups) {
        let p = Math.round((LEN - grp.len) * f);
        for (const { it, i } of grp.g) {
            const q = a + Math.round((grp.thick - across(it)) * f);
            rects.push(axis === "rows" ? { i, x: p, y: q, w: it.w, h: it.h } : { i, x: q, y: p, w: it.w, h: it.h });
            p += along(it) + gap;
        }
        a += grp.thick + gap;
    }
    return axis === "rows" ? { rects, w: LEN, h: THICK } : { rects, w: THICK, h: LEN };
}

/**
 * "Lossless" arrangement: tries every row count and every column count (order
 * kept) at 1:1 pixels and keeps the tightest one. With size_mode "short" the
 * short side is a CEILING: only packings whose short side fits short_px are
 * considered; when none can fit without resizing, the one with the smallest
 * short side is used and `overLimit` says so. Stills are only ever shrunk when
 * the sheet would pass the browser canvas limit (`clamped`).
 */
function layoutLossless(items, opts) {
    const n = items.length;
    const align = opts.align || "center";
    const split = parseSplit(opts.split, n);
    const fixed = split || (opts.rows > 0 ? balancedCounts(n, opts.rows) : null);
    const countSets = fixed ? [fixed] : Array.from({ length: n }, (_, r) => balancedCounts(n, r + 1));
    const axes = fixed ? ["rows"] : ["rows", "cols"];
    const limit = opts.size_mode === "short"
        ? Math.max(256, Math.min(MAX_SIDE, Math.round(Number(opts.short_px) || 2048)))
        : Infinity;
    const area = items.reduce((s, it) => s + it.w * it.h, 0);
    const marginPct = Math.max(0, Number(opts.margin_pct) || 0);
    const gapPct = opts.link_gap ? marginPct : Math.max(0, Number(opts.gap_pct) || 0);

    const score = (c) => (1 - area / (c.W * c.H)) + 0.25 * Math.abs(Math.log((c.W / c.H) / AUTO_ASPECT));
    function choose(gap, margin) {
        const all = [];
        for (const axis of axes) for (const counts of countSets) {
            const b = packLossless(items, counts, axis, gap, align);
            all.push({ ...b, W: b.w + 2 * margin, H: b.h + 2 * margin });
        }
        const canvasOk = all.filter((c) => c.W <= MAX_SIDE && c.H <= MAX_SIDE && c.W * c.H <= MAX_AREA);
        const pool = canvasOk.length ? canvasOk : all;
        const fits = pool.filter((c) => Math.min(c.W, c.H) <= limit);
        const best = fits.length
            ? fits.reduce((p, c) => (score(c) < score(p) - 1e-9 ? c : p))
            : pool.reduce((p, c) => {
                const d = Math.min(c.W, c.H) - Math.min(p.W, p.H);
                return d < 0 || (d === 0 && score(c) < score(p)) ? c : p;
            });
        return { best, fits: fits.length > 0 };
    }
    // Margin / gap % refer to the side of a square holding all the stills, not to
    // the packing's long side: a long strip would otherwise get huge gaps that
    // push it over the short-side ceiling.
    const S = Math.sqrt(area);
    const gap = Math.round(gapPct / 100 * S);
    const margin = Math.round(marginPct / 100 * S);
    const { best, fits } = choose(gap, margin);

    let K = Math.min(1, MAX_SIDE / best.W, MAX_SIDE / best.H, Math.sqrt(MAX_AREA / (best.W * best.H)));
    const clamped = K < 1;
    const rects = best.rects.map((r) => (clamped
        ? { i: r.i, x: (r.x + margin) * K, y: (r.y + margin) * K, w: r.w * K, h: r.h * K }
        : { i: r.i, x: r.x + margin, y: r.y + margin, w: r.w, h: r.h }));
    return {
        width: Math.max(1, Math.round(best.W * K)),
        height: Math.max(1, Math.round(best.H * K)),
        rects,
        scale: K,
        clamped,
        maxUpscale: K,
        minScale: K,
        lossless: !clamped,
        overLimit: Number.isFinite(limit) && !fits,
        limit,
    };
}

/**
 * items: [{w, h}] native pixel sizes, in sheet order (hero = first).
 * -> { width, height, rects: [{i, x, y, w, h}] in pixels, scale, clamped, maxUpscale }
 */
export function layoutSheet(items, options = {}) {
    const opts = { ...SHEET_DEFAULTS, ...options };
    if (!items.length) return { width: 0, height: 0, rects: [], scale: 0, clamped: false, maxUpscale: 0, minScale: 0 };
    if (opts.arrangement === "lossless") return layoutLossless(items, opts);
    // Pass 1 without gaps fixes the reference size the percentages refer to.
    const c0 = layoutContent(items, opts, 0);
    const S = Math.max(c0.w, c0.h);
    const marginPct = Math.max(0, Number(opts.margin_pct) || 0);
    const gapPct = opts.link_gap ? marginPct : Math.max(0, Number(opts.gap_pct) || 0);
    const gap = gapPct / 100 * S;
    const margin = marginPct / 100 * S;
    const c = layoutContent(items, opts, gap);
    // Global pixel scale: at 100 % the most-shrunk still lands at exactly 1:1,
    // so every still keeps all of its pixels.
    const minRel = Math.min(...c.rects.map((r) => r.w / items[r.i].w));
    let K = (1 / minRel) * Math.max(0.05, (Number(opts.size_pct) || 100) / 100);
    if (opts.size_mode === "short") {
        // H3 input target: the sheet's short side lands at short_px (default 2048).
        const px = Math.max(256, Math.min(MAX_SIDE, Math.round(Number(opts.short_px) || 2048)));
        K = px / Math.min(c.w + 2 * margin, c.h + 2 * margin);
    }
    const W0 = (c.w + 2 * margin) * K, H0 = (c.h + 2 * margin) * K;
    const lim = Math.min(1, MAX_SIDE / W0, MAX_SIDE / H0, Math.sqrt(MAX_AREA / (W0 * H0)));
    const clamped = lim < 1;
    K *= lim;
    const rects = c.rects.map((r) => ({
        i: r.i, x: (r.x + margin) * K, y: (r.y + margin) * K, w: r.w * K, h: r.h * K,
    }));
    return {
        width: Math.max(1, Math.round((c.w + 2 * margin) * K)),
        height: Math.max(1, Math.round((c.h + 2 * margin) * K)),
        rects,
        scale: K,
        clamped,
        maxUpscale: Math.max(...rects.map((r) => r.w / items[r.i].w)),
        minScale: Math.min(...rects.map((r) => r.w / items[r.i].w)),
    };
}

/** Paint a layout onto a canvas context at `k` x the layout's pixel size. */
function paint(ctx, layout, imgs, background, k = 1) {
    ctx.fillStyle = background || "#000000";
    ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    for (const r of layout.rects) {
        const img = imgs[r.i];
        if (img) ctx.drawImage(img, r.x * k, r.y * k, r.w * k, r.h * k);
    }
}

function iconSvg(id) {
    const R = {
        auto: [[1, 1, 7, 4], [9, 1, 6, 4], [1, 7, 4, 4], [6, 7, 9, 4]],
        row: [[1, 2, 3, 8], [5, 2, 3, 8], [9, 2, 3, 8], [13, 2, 2, 8]],
        grid: [[1, 1, 4, 4], [6, 1, 4, 4], [11, 1, 4, 4], [1, 7, 4, 4], [6, 7, 4, 4], [11, 7, 4, 4]],
        hero_left: [[1, 1, 7, 10], [9, 1, 3, 3], [13, 1, 2, 3], [9, 5, 3, 3], [13, 5, 2, 3], [9, 9, 6, 2]],
        hero_right: [[1, 1, 3, 3], [5, 1, 2, 3], [1, 5, 3, 3], [5, 5, 2, 3], [1, 9, 6, 2], [8, 1, 7, 10]],
        hero_top: [[1, 1, 14, 6], [1, 8, 4, 3], [6, 8, 4, 3], [11, 8, 4, 3]],
        lossless: [[1, 1, 4, 6], [6, 1, 5, 4], [12, 1, 3, 5], [1, 8, 6, 3], [8, 7, 3, 4], [12, 7, 3, 4]],
    }[id] || [];
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 16 12");
    svg.setAttribute("class", "r2-sh-icon");
    for (const [x, y, w, h] of R) {
        const rc = document.createElementNS(ns, "rect");
        Object.entries({ x, y, width: w, height: h, rx: 0.6 }).forEach(([a, v]) => rc.setAttribute(a, v));
        svg.appendChild(rc);
    }
    return svg;
}

/**
 * The panel. `getFiles()` -> h3_refs filenames in sheet order; `getState()` ->
 * the persisted settings object (mutated in place); `save()` persists it;
 * `getSlug()` names the output; `onSaved(name)` after a keep.
 */
export function createSheetMaker({ getFiles, getState, save, getSlug, onSaved } = {}) {
    const root = el("div", "r2-sh");
    const controls = el("div", "r2-sh");
    const cache = new Map();   // name -> Promise<HTMLImageElement>

    function st() {
        const s = getState();
        for (const [k, v] of Object.entries(SHEET_DEFAULTS)) if (s[k] === undefined) s[k] = v;
        return s;
    }

    function load(name) {
        if (!cache.has(name)) {
            cache.set(name, new Promise((res, rej) => {
                const im = new Image();
                im.decoding = "async";
                im.onload = () => res(im);
                im.onerror = () => { cache.delete(name); rej(new Error(`could not load ${name}`)); };
                im.src = viewUrl(name);
            }));
        }
        return cache.get(name);
    }

    /* -- controls ------------------------------------------------------- */
    const sec = (title) => {
        const box = el("div", "r2-sh-sec");
        box.appendChild(el("div", "r2-sh-sectitle", title));
        controls.appendChild(box);
        return box;
    };

    const arrSec = sec("Arrangement");
    const arrGrid = el("div", "r2-sh-arr");
    const arrBtns = {};
    for (const a of ARRANGEMENTS) {
        const b = el("button", a.id === "lossless" ? "r2-sh-arrbtn r2-sh-arrwide" : "r2-sh-arrbtn");
        b.type = "button";
        b.title = a.tip;
        b.append(iconSvg(a.id), el("span", null, a.label));
        b.addEventListener("click", () => { st().arrangement = a.id; save(); sync(); });
        arrBtns[a.id] = b;
        arrGrid.appendChild(b);
    }
    arrSec.appendChild(arrGrid);

    function slider(parent, label, key, min, max, step, fmt, hint) {
        const wrap = el("div", "r2-sh-slider");
        const head = el("div", "r2-sh-sliderhead");
        const val = el("span", "r2-sh-val");
        head.append(el("span", null, label), val);
        const inp = el("input");
        inp.type = "range";
        inp.min = String(min); inp.max = String(max); inp.step = String(step);
        inp.addEventListener("input", () => { st()[key] = Number(inp.value); val.textContent = fmt(Number(inp.value)); save(); schedule(); });
        wrap.append(head, inp);
        if (hint) wrap.appendChild(el("div", "r2-sh-hint", hint));
        parent.appendChild(wrap);
        return {
            wrap, inp,
            set(v, maxV) { if (maxV !== undefined) inp.max = String(maxV); inp.value = String(v); val.textContent = fmt(Number(v)); },
        };
    }

    const heroS = slider(arrSec, "Hero image size", "hero_pct", 20, 80, 1, (v) => `${v} %`);
    const rowsS = slider(arrSec, "Rows", "rows", 0, 6, 1, (v) => String(v), "0 = automatic, otherwise a fixed number");
    const splitWrap = el("div", "r2-sh-slider");
    splitWrap.appendChild(el("div", "r2-sh-sliderhead", "Custom split"));
    const splitIn = el("input", "r2-sh-text");
    splitIn.placeholder = "e.g. 2,4 = two on top, four below";
    const splitHint = el("div", "r2-sh-hint");
    splitIn.addEventListener("input", () => { st().split = splitIn.value; save(); schedule(); });
    splitWrap.append(splitIn, splitHint);
    arrSec.appendChild(splitWrap);

    const chipRow = (parent, key, opts) => {
        const row = el("div", "r2-sh-chips");
        const btns = {};
        for (const [v, lbl] of opts) {
            const b = button(lbl, "", () => { st()[key] = v; save(); sync(); }, "h3e-btn h3e-refmod-chip");
            btns[v] = b;
            row.appendChild(b);
        }
        parent.appendChild(row);
        return btns;
    };
    const spSec = sec("Spacing");
    const marginS = slider(spSec, "Margin", "margin_pct", 0, 15, 0.25, (v) => `${v.toFixed(2)} %`);
    const linkRow = el("label", "r2-sh-check");
    const linkIn = el("input");
    linkIn.type = "checkbox";
    linkIn.addEventListener("change", () => { st().link_gap = linkIn.checked; save(); sync(); });
    linkRow.append(linkIn, el("span", null, "Gaps = margin (equal everywhere)"));
    spSec.appendChild(linkRow);
    const gapS = slider(spSec, "Gap", "gap_pct", 0, 15, 0.25, (v) => `${v.toFixed(2)} %`);
    spSec.appendChild(el("div", "r2-sh-sliderhead", "Output size"));
    const sizeModeBtns = chipRow(spSec, "size_mode", [["short", "Fit for H3 (short side)"], ["native", "Native pixels"]]);
    const shortWrap = el("div", "r2-sh-slider");
    const shortHead = el("div", "r2-sh-sliderhead");
    const shortIn = el("input", "r2-sh-text");
    shortIn.type = "number"; shortIn.min = "256"; shortIn.max = "16384"; shortIn.step = "64";
    shortIn.title = "Short side of the saved sheet in pixels (2048 = H3's best input size).";
    shortIn.addEventListener("change", () => {
        st().short_px = Math.max(256, Math.min(16384, Math.round(Number(shortIn.value) || 2048)));
        shortIn.value = String(st().short_px);
        save(); schedule();
    });
    shortHead.append(el("span", null, "Short side (px)"), shortIn);
    const SHORT_HINT = "2048 = the largest input H3 takes in well; the long side follows the layout.";
    const SHORT_HINT_LOSSLESS = "Lossless: a ceiling. Stills stay 1:1, so the packing whose short side fits under this is picked; nothing is resized up or down.";
    const shortHint = el("div", "r2-sh-hint", SHORT_HINT);
    shortWrap.append(shortHead, shortHint);
    spSec.appendChild(shortWrap);
    const sizeS = slider(spSec, "Overall image size", "size_pct", 25, 200, 5, (v) => `${v} %`,
        "100 % = every still keeps all its pixels (the smallest-drawn one at 1:1; a hero is enlarged to fit). Lower it for a smaller file.");

    const alSec = sec("Alignment & background");
    alSec.appendChild(el("div", "r2-sh-hint", "Where a still sits when its cell or region is not filled"));
    const alignBtns = chipRow(alSec, "align", [["start", "Start"], ["center", "Center"], ["end", "End"]]);
    const bgBtns = chipRow(alSec, "background", [["#000000", "Black"], ["#808080", "Grey"], ["#ffffff", "White"]]);

    /* -- preview + actions -------------------------------------------- */
    const prevBox = el("div", "r2-sh-prev");
    const cv = el("canvas", "r2-sh-canvas");
    const empty = el("div", "r2-rm-extempty", "Add 2+ stills below, then pick an arrangement");
    prevBox.append(cv, empty);
    const badge = el("div", "r2-st-chip r2-st-dim");
    const actRow = el("div", "r2-st-row");
    const saveBtn = button("💾 Save Sheet → h3_refs", "Render the sheet at full size and save it into input/h3_refs/ as one PNG", () => doSave(), "h3e-btn h3e-btn-accent");
    const dlBtn = button("⬇ Download", "Render the sheet at full size and download the PNG", () => doSave({ download: true }));
    actRow.append(badge, saveBtn, dlBtn);
    const status = el("div", "h3e-note");
    status.style.display = "none";
    root.append(prevBox, actRow, status, controls);
    root.appendChild(el("div", "r2-sh-hint",
        "Order = the Stills list order (use its ↑ ↓); hero modes make the first still the hero. Stills are drawn whole, never cropped or redrawn."));

    function setStatus(msg, level = "hint") {
        status.style.display = msg ? "" : "none";
        status.className = `h3e-note h3e-note-${level}`;
        status.textContent = msg || "";
    }

    let current = null;      // { files, imgs, layout }
    let raf = 0, gen = 0;
    function schedule() {
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => draw());
    }

    async function prepare() {
        const files = (getFiles() || []).filter(Boolean);
        const imgs = await Promise.all(files.map((f) => load(f).catch(() => null)));
        const ok = files.map((f, i) => [f, imgs[i]]).filter(([, im]) => im);
        const items = ok.map(([, im]) => ({ w: im.naturalWidth, h: im.naturalHeight }));
        const layout = layoutSheet(items, st());
        return { files: ok.map(([f]) => f), imgs: ok.map(([, im]) => im), items, layout, missing: files.length - ok.length };
    }

    async function draw() {
        const my = ++gen;
        let p;
        try { p = await prepare(); } catch (e) { setStatus(String(e), "error"); return; }
        if (my !== gen) return;
        current = p;
        const n = p.files.length;
        const hasAny = n > 0;
        cv.style.display = hasAny ? "" : "none";
        empty.style.display = hasAny ? "none" : "";
        saveBtn.disabled = n < 2;
        dlBtn.disabled = n < 1;
        if (!hasAny) { badge.textContent = "no stills"; return; }
        const L = p.layout;
        const k = Math.min(1, 560 / L.width, 300 / L.height);
        cv.width = Math.max(1, Math.round(L.width * k));
        cv.height = Math.max(1, Math.round(L.height * k));
        paint(cv.getContext("2d"), L, p.imgs, st().background, k);
        const mp = (L.width * L.height / 1e6).toFixed(1);
        let txt = `${L.width}×${L.height} · ${mp} MP · ${n} still${n === 1 ? "" : "s"}`;
        if (L.lossless) txt += " · lossless 1:1";
        if (L.overLimit) txt += ` · short side ${Math.min(L.width, L.height)} > ${L.limit}: no 1:1 packing fits (use Native pixels, or fewer/smaller stills)`;
        if (L.minScale < 0.999) txt += ` · stills shrunk to ${Math.round(L.minScale * 100)} %`;
        if (L.maxUpscale > 1.001) txt += ` · largest enlarged ${L.maxUpscale.toFixed(2)}×`;
        if (L.clamped) txt += " · capped at canvas limit";
        if (p.missing) txt += ` · ${p.missing} not loaded`;
        badge.textContent = txt;
        const sp = String(st().split || "").trim();
        const restN = st().arrangement.startsWith("hero") ? n - 1 : n;
        splitHint.textContent = !sp ? ""
            : parseSplit(sp, restN) ? "✓ split applied"
            : `✗ ignored: numbers must add up to ${restN}${st().arrangement.startsWith("hero") ? " (stills after the hero)" : ""}`;
    }

    async function doSave({ download = false } = {}) {
        saveBtn.disabled = true; dlBtn.disabled = true;
        try {
            setStatus("Rendering full-size sheet...");
            const p = await prepare();
            if (!p.files.length) throw new Error("No stills to stitch.");
            const L = p.layout;
            const big = document.createElement("canvas");
            big.width = L.width; big.height = L.height;
            const ctx = big.getContext("2d");
            if (!ctx) throw new Error(`Browser refused a ${L.width}×${L.height} canvas; lower Overall image size.`);
            paint(ctx, L, p.imgs, st().background, 1);
            const blob = await new Promise((res) => big.toBlob(res, "image/png"));
            big.width = big.height = 1;   // release the bitmap
            if (!blob) throw new Error("PNG encode failed (sheet too large?); lower Overall image size.");
            const name = `${(getSlug?.() || "char")}_sheet_${p.files.length}up.png`;
            if (download) {
                const a = document.createElement("a");
                a.href = URL.createObjectURL(blob);
                a.download = name;
                a.click();
                setTimeout(() => URL.revokeObjectURL(a.href), 4000);
                setStatus(`Downloaded ${name} (${L.width}×${L.height}).`);
                return;
            }
            setStatus(`Uploading ${(blob.size / 1e6).toFixed(1)} MB...`);
            const got = await upload([new File([blob], name, { type: "image/png" })]);
            const saved = got[0]?.name || name;
            setStatus(`Saved ${saved} (${L.width}×${L.height}) to input/h3_refs/. Use it as one reference picture.`);
            onSaved?.(saved);
        } catch (e) {
            setStatus(String(e.message || e), "error");
        } finally {
            saveBtn.disabled = false; dlBtn.disabled = false;
            schedule();
        }
    }

    function sync() {
        const s = st();
        for (const [k, b] of Object.entries(arrBtns)) b.classList.toggle("r2-sh-on", k === s.arrangement);
        heroS.wrap.style.display = s.arrangement.startsWith("hero") ? "" : "none";
        rowsS.wrap.style.display = s.arrangement === "row" ? "none" : "";
        splitWrap.style.display = s.arrangement === "row" ? "none" : "";
        const n = (getFiles() || []).filter(Boolean).length;
        heroS.set(s.hero_pct);
        rowsS.set(Math.min(s.rows, Math.max(6, n)), Math.max(6, n));
        if (document.activeElement !== splitIn) splitIn.value = s.split || "";
        marginS.set(s.margin_pct);
        linkIn.checked = !!s.link_gap;
        gapS.wrap.style.display = s.link_gap ? "none" : "";
        gapS.set(s.gap_pct);
        sizeS.set(s.size_pct);
        const shortMode = s.size_mode === "short";
        const lossless = s.arrangement === "lossless";
        sizeS.wrap.style.display = shortMode || lossless ? "none" : "";
        shortHint.textContent = lossless ? SHORT_HINT_LOSSLESS : SHORT_HINT;
        shortWrap.style.display = shortMode ? "" : "none";
        if (document.activeElement !== shortIn) shortIn.value = String(s.short_px);
        for (const [k, b] of Object.entries(sizeModeBtns)) b.classList.toggle("h3e-refmod-chip-on", k === s.size_mode);
        for (const [k, b] of Object.entries(alignBtns)) b.classList.toggle("h3e-refmod-chip-on", k === s.align);
        for (const [k, b] of Object.entries(bgBtns)) b.classList.toggle("h3e-refmod-chip-on", k === s.background);
        schedule();
    }

    return { root, refresh: sync };
}
