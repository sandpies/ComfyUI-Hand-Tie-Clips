/**
 * Round-2 store: the only place that reads or writes node widgets.
 *
 * shot_plan remains the source of truth, exactly as in the shipped editor.
 * Everything here is a thin adapter so the shell, the script pane and the
 * timeline cannot drift into separate copies of the plan.
 */

import { widgetByName } from "../editor/widget_utils.js";
import { parsePlan, planToJson } from "../editor/plan_editor.js";
import { parseRefPlan, refPlanToJson } from "../editor/ref_rail.js";
import { MEDIA_WIDGETS } from "../editor/media_strip.js";
import { NOT_KEYED, forecastPlan, framesOf, parseJson, shotSig } from "../editor/timeline_model.js";

export const SHOTS_HIDDEN = [
    "prompt", "chains", "hop_script", "shot_plan", "ref_plan",
    "swap_script", "swap_refs", "establish", "tone_anchor_ref",
].concat(MEDIA_WIDGETS);

export const AXES = ["camera", "framing", "pace", "join", "tail"];
export const AXIS_LABEL = {
    camera: "camera", framing: "framing", pace: "pace", join: "join", tail: "tail",
};

export function readPlan(node) {
    const w = widgetByName(node, "shot_plan");
    const raw = String(w?.value ?? "");
    const parsed = parsePlan(raw);
    return { shots: parsed || [], bad: parsed === null, raw };
}

export function writePlan(node, shots) {
    const w = widgetByName(node, "shot_plan");
    if (!w) return;
    w.value = planToJson(shots);
    try { w.callback?.(w.value, node.graph?.canvas, node); } catch (_) { /* */ }
    node.graph?.setDirtyCanvas?.(true, true);
}

export function readPrompt(node) {
    return String(widgetByName(node, "prompt")?.value ?? "");
}

export function writePrompt(node, text) {
    const w = widgetByName(node, "prompt");
    if (!w) return;
    w.value = text;
    try { w.callback?.(w.value, node.graph?.canvas, node); } catch (_) { /* */ }
    node.graph?.setDirtyCanvas?.(true, true);
}

export function readRefs(node) {
    const plan = parseRefPlan(widgetByName(node, "ref_plan")?.value);
    return plan || { refs: [], subjects: {} };
}

export function writeRefs(node, plan) {
    const w = widgetByName(node, "ref_plan");
    if (!w) return;
    w.value = refPlanToJson(plan);
    try { w.callback?.(w.value, node.graph?.canvas, node); } catch (_) { /* */ }
    node.graph?.setDirtyCanvas?.(true, true);
}

export function refsForShot(plan, index, shot) {
    if (Array.isArray(shot?.refs)) {
        const set = new Set(shot.refs.map((t) => String(t).replace(/^@/, "").trim()));
        return (plan?.refs || []).filter((r) => set.has(r.tag));
    }
    const hop = index + 1;
    return (plan?.refs || []).filter((r) => {
        if (Array.isArray(r.shots) && r.shots.length) return r.shots.includes(hop);
        return hop === 1 || shot?.anchor === "restart";
    });
}

export function refTagCount(plan) {
    return (plan?.refs || []).length;
}

export function freeId(shots) {
    const used = new Set((shots || []).map((s) => String(s.id || "")));
    for (let n = 1; ; n += 1) {
        const id = `s${n}`;
        if (!used.has(id)) return id;
    }
}

export function blankShot(index) {
    return {
        id: `s${(index || 0) + 1}`, beat: "", directives: {}, prose: "",
        seed: null, steps: null, duration: null, locked: false,
        tone: "", anchor: "", refs: null, moment: "", moment_end: "",
    };
}

export function durationOf(node, shot) {
    return String(shot?.duration || widgetByName(node, "duration")?.value || "15 s");
}

export function seconds(label) {
    const n = parseFloat(String(label ?? "").replace(",", "."));
    return Number.isFinite(n) ? n : 15;
}

export function overlapOf(node) {
    return seconds(widgetByName(node, "overlap")?.value || "0.9 s");
}

export function deliveredSeconds(node, shot, index) {
    const raw = seconds(durationOf(node, shot));
    if (index === 0 || shot?.anchor === "restart") return raw;
    return Math.max(0.1, raw - overlapOf(node));
}

export function chainSeconds(node, shots) {
    const list = shots || [];
    if (!list.length) return 0;
    const total = list.reduce((sum, s) => sum + seconds(durationOf(node, s)), 0);
    const trims = list.reduce((n, s, i) => n + (i > 0 && s?.anchor !== "restart" ? 1 : 0), 0);
    return Math.max(0, total - overlapOf(node) * trims);
}

export function mediaCount(node) {
    return MEDIA_WIDGETS.filter((name) => {
        if (!/_file$/.test(name)) return false;
        return String(widgetByName(node, name)?.value || "").trim() !== "";
    }).length;
}

export function nodeResolutionInfo(node) {
    const aspRaw = String(widgetByName(node, "aspect")?.value || "9:16 portrait").toLowerCase();
    const resRaw = String(widgetByName(node, "resolution")?.value || "1 MP (1024)").toLowerCase();
    const is169 = aspRaw.includes("16:9") || aspRaw.includes("landscape");
    const is11 = aspRaw.includes("1:1") || aspRaw.includes("square");
    const aspectLabel = is169 ? "16:9" : (is11 ? "1:1" : "9:16");
    let w = 768, h = 1344;
    if (resRaw.includes("0.25")) { w = 384; h = 672; }
    else if (resRaw.includes("0.5")) { w = 544; h = 960; }
    else if (resRaw.includes("2 mp") || resRaw.includes("1440")) { w = 1088; h = 1920; }
    if (is169) { const tmp = w; w = h; h = tmp; }
    else if (is11) { w = 1024; h = 1024; }
    return {
        aspectLabel,
        dimsLabel: `${w}\u00d7${h}`,
        isLandscape: is169,
        isSquare: is11,
    };
}

/* -- timeline record & forecast ------------------------------------------ */

export const RUN_PROP = "h3_timeline_run";
export const PENDING_PROP = "h3_timeline_pending";

export function timelineRec(node) {
    return node.properties?.[RUN_PROP] || null;
}

export function hopKey(node, index) {
    return timelineRec(node)?.hops?.[index]?.key || null;
}

export function cachedCount(node, shots, missing = null) {
    const rec = timelineRec(node);
    if (!rec) return 0;
    let n = 0;
    for (let i = 0; i < (shots || []).length; i += 1) {
        const k = rec.hops?.[i]?.key;
        if (k && !(missing && missing.has(k))) n += 1;
    }
    return n;
}

export function clipURL(key) {
    return `/h3_ref_chain/hop_clip?key=${encodeURIComponent(key)}`;
}

export function seamURL(prevKey, nextKey) {
    return `/h3_ref_chain/seam_clip?prev=${encodeURIComponent(prevKey)}&next=${encodeURIComponent(nextKey)}`;
}

export function spriteURL(key, n) {
    return `/h3_ref_chain/hop_sprite?key=${encodeURIComponent(key)}&n=${n || 1}`;
}

export function fmtTime(t) {
    t = Math.max(0, Number(t) || 0);
    const m = Math.floor(t / 60);
    const s = t - m * 60;
    return `${m < 10 ? "0" : ""}${m}:${s < 10 ? "0" : ""}${s.toFixed(1)}`;
}

export function hopStarts(node, shots) {
    const out = [];
    let t = 0;
    const list = shots || [];
    for (let i = 0; i < list.length; i += 1) {
        out.push(t);
        t += deliveredSeconds(node, list[i], i);
    }
    return out;
}

export function snapshotNow(node, shots) {
    const list = shots || [];
    const refs = parseJson(widgetByName(node, "ref_plan")?.value) || {};
    const widgets = {};
    for (const w of node.widgets || []) {
        if (!w?.name || NOT_KEYED.has(w.name) || w.name === "seed") continue;
        if (typeof w.value === "object") continue;
        widgets[w.name] = w.value;
    }
    return {
        ids: list.map((s) => String(s.id || "")),
        shots: Object.fromEntries(list.map((s) => [String(s.id || ""), shotSig(s)])),
        refs: Object.fromEntries((refs.refs || []).map((r) => [String(r.tag || ""), JSON.stringify(r)])),
        subjects: JSON.stringify(refs.subjects || {}),
        widgets,
        seed: widgetByName(node, "seed")?.value ?? null,
    };
}

export function computeForecast(node, shots, missing = new Set()) {
    const list = shots || [];
    return forecastPlan({
        shots: list,
        rec: timelineRec(node),
        now: snapshotNow(node, list),
        range: {
            from: Number(widgetByName(node, "render_from")?.value) || 0,
            through: Number(widgetByName(node, "render_through")?.value) || 0,
        },
        missing,
        seedCtl: String(widgetByName(node, "control_after_generate")?.value || "fixed"),
        refsNow: parseJson(widgetByName(node, "ref_plan")?.value)?.refs || [],
        tie: String(widgetByName(node, "pin_mech")?.value || "").startsWith("hand_tie"),
        frames: list.map((s) => framesOf(s.duration || widgetByName(node, "duration")?.value)),
    });
}

export function forecastText(node, shots, missing = new Set()) {
    const list = shots || [];
    const total = list.length;
    if (!total) return "no shots";
    const rec = timelineRec(node);
    if (!rec) return `next queue: all ${total} hops`;
    try {
        const fc = computeForecast(node, list, missing);
        if (fc && Array.isArray(fc.state)) {
            const renders = fc.state.map((st, i) => (st === "render" ? i + 1 : null)).filter(Boolean);
            const keeps = fc.state.filter((st) => st === "keep" || st === "keeps" || st === "replay").length;
            const locked = fc.state.filter((st) => st === "locked").length;
            const parts = [
                renders.length
                    ? (renders.length === total ? `next queue: all ${total} hops` : `next queue: hop${renders.length > 1 ? "s" : ""} ${renders.join(", ")}`)
                    : "next queue: nothing (all cached)",
                `${keeps} cached`,
            ];
            if (locked) parts.push(`${locked} locked`);
            return parts.join(" \u00b7 ");
        }
    } catch (_) { /* fall back to simple count */ }
    const cached = cachedCount(node, list, missing);
    const missingCount = total - cached;
    return missingCount
        ? `next queue: ${missingCount} of ${total} \u00b7 ${cached} cached`
        : `next queue: nothing \u00b7 all ${total} cached`;
}
