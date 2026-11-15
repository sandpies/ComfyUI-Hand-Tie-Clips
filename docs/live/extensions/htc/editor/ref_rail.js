/**
 * The reference rail: what each wired still is, and what it is for.
 *
 * Mirrors `refs.py`. Two things it surfaces that the console only told you
 * about after you queued:
 *
 *   - a ref whose picture is missing or never chosen (refs.check)
 *   - duplicate tags (parse_ref_plan raises on these, so a typo used to cost
 *     you a failed run instead of a red row)
 *   - a ref carried over from when references were wired to ref_image_N
 *     sockets, which cannot be migrated automatically: the socket held a
 *     tensor and there is no filename to recover, so the row says which
 *     slot it used to be and asks for the picture.
 *
 * The ordinal badge is the point of the whole module. Core assigns
 * `<Picture N>` by position, so pulling a Load Image out renumbers everything
 * after it; here the ordinal is derived and shown live, and prose refers to the
 * stable @tag instead.
 */

import { api } from "../../../scripts/api.js";
import { el, button, select, vocab, onVocabRefresh } from "./widget_utils.js";
import { createPicker } from "./media_picker.js";
import { createTrimBar } from "./trim_bar.js";
import { stripGeometry, columnAt } from "./strip_geometry.js";

/* The width the hop bar lays out on, derived the SAME way the Script score
 * strip derives its own (plan_editor.js `stripWidth()`), because the two have
 * to line up column-for-column and `node.size` is the only thing both modules
 * can read -- the panel has no shared layout context, and measuring the DOM is
 * not available before first paint.
 *
 * If the two ever diverge, the symptom is subtle and worth naming: the hop bar's
 * cells stop lining up with the strip's columns, and a click that looks like it
 * selected hop 3 selects hop 5. The geometry module is the single place the
 * column width is decided; this is only the viewport it is decided over. */
function hopBarWidth(node) {
  const w = Number(node?.size?.[0]) - 24;
  return Number.isFinite(w) && w > 120 ? w : 536;
}

const MAX_SLOTS = 9;

/** `[{name, kind, role, format, tokens, members_count, description, voice, ...}]` from refmods listing. */
let _refmods = null;
const _inspectCache = new Map();
// The builder writes its file on a queue, so a list cached at mount never
// learns about it until a browser refresh. Re-read after every finished
// prompt and re-render only when a name or a caption actually moved, so a
// queue that built nothing does not rebuild a rail being edited.
const _refmodListeners = new Set();
export function invalidateRefmods(forceRender = true) {
    _refmods = null;
    _inspectCache.clear();
    return refmodRows().then((rows) => {
        if (forceRender) {
            for (const fn of _refmodListeners) fn();
        }
        return rows;
    });
}
api.addEventListener("execution_success", () => {
    const before = JSON.stringify(_refmods || []);
    _refmods = null;
    _inspectCache.clear();
    refmodRows().then((rows) => {
        if (JSON.stringify(rows) === before) return;
        for (const fn of _refmodListeners) fn();
    });
});
if (typeof window !== "undefined") {
    window.addEventListener?.("htc:refmods-changed", () => {
        invalidateRefmods(true);
    });
}
function refmodRows() {
    if (_refmods) return Promise.resolve(_refmods);
    return fetch("/h3_ref_chain/files?folder=refmods")
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
        .then((j) => {
            _refmods = Array.isArray(j.files) ? j.files : [];
            return _refmods;
        })
        .catch(() => {
            _refmods = [];
            return _refmods;
        });
}
function refmodInspect(name) {
    if (!name) return Promise.resolve(null);
    if (_inspectCache.has(name)) return Promise.resolve(_inspectCache.get(name));
    return fetch(`/h3_ref_chain/refmod_inspect?name=${encodeURIComponent(name)}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((j) => {
            if (j?.ok) {
                _inspectCache.set(name, j);
                return j;
            }
            return null;
        })
        .catch(() => null);
}
function refmodRowMeta(name) {
    return (_refmods || []).find((f) => f.name === name) || null;
}
/** The voice a mod's header names, `{file, start, end}`, or null. A row that
 *  cites the mod with no voice of its own inherits exactly this. */
export function refmodVoice(name) {
    const row = (_refmods || []).find((f) => f.name === name);
    return row?.voice?.file ? row.voice : null;
}
/** The caption stored in a mod's header, from the cached listing. */
function refmodCaption(name) {
    const row = (_refmods || []).find((f) => f.name === name);
    const s = String(row?.description || "").trim();
    return (s === "0" || s === "none" || s === "None" || s === "null") ? "" : s;
}

function blankRef(existing) {
    let n = existing.length + 1;
    const tags = new Set(existing.map((r) => r.tag));
    while (tags.has(`ref_${n}`)) n += 1;
    // slot is the row's position, same as parseRefPlan / refs.py. Leaving it
    // unset made a freshly added row with a picture still fail validate
    // (`wired.has(undefined)`), so the rail showed "no picture chosen" over
    // the thumbnail that was just picked.
    return { tag: `ref_${n}`, file: "", slot: n, subject: null, retention: "", desc: "" };
}

function reindex(plan) {
    (plan.refs || []).forEach((r, i) => { r.slot = i + 1; });
}

/** Drop subject blocks no remaining row claims.
 *
 *  × on the last ref used to leave `subjects` behind, so the JSON box
 *  stayed populated with a cook who no longer had a picture. */
function pruneSubjects(plan) {
    const used = new Set(
        (plan.refs || [])
            .filter((r) => r.subject != null)
            .map((r) => String(r.subject)),
    );
    for (const k of Object.keys(plan.subjects || {})) {
        if (!used.has(String(k))) delete plan.subjects[k];
    }
}

const STEP_CURVES = [
    ["full", "full"],
    ["early_lock", "early lock"],
    ["late_detail", "late detail"],
    ["fade", "fade out"],
    ["mid_peak", "mid peak"],
];
const CONCEPT_ROLES = [
    "generic", "identity", "wardrobe", "bodyshape",
    "helper", "pose_motion", "background", "style",
];

export function parseRefPlan(text) {
    // A widget value is not guaranteed to be a string. ComfyUI restores
    // `widgets_values` POSITIONALLY, so a node whose widget list changed can
    // hand this an int or a bool from a neighbouring widget. Coerce rather
    // than throw: a wrong-typed plan should show the JSON tab, not abort the
    // whole workflow load.
    const t = String(text ?? "").trim();
    if (!t) return { refs: [], subjects: {} };
    let data;
    try {
        data = JSON.parse(t);
    } catch (_) {
        return null; // caller keeps the raw text and shows the JSON tab
    }
    // Same guard as plan_editor: valid JSON that is not a plan.
    if (data === null || typeof data !== "object") return null;
    const refs = Array.isArray(data) ? data : (data.refs || []);
    /* Normalised, not taken as written. refs.py requires each subject to be an
     * object of name/locked/context and hard-fails otherwise; this used to pass
     * whatever was in the JSON straight through, so `{"1": "the cook"}` drew a
     * subject row with three empty boxes, wrote itself back out unchanged on the
     * next edit, and was refused by the backend only once a render was started.
     * The editor showing an invalid plan as if it were valid is the same fault
     * as the encoder being handed an uncited photograph: wrong, and silent.
     *
     * A bare string becomes `name`, which is what anyone writing one means.
     * Anything else that is not an object becomes an empty subject rather than
     * being dropped, so the number itself survives and the row stays visible
     * for the author to fill in. */
    const rawSubjects = (Array.isArray(data) ? {} : (data.subjects || {})) || {};
    const subjects = {};
    for (const [k, v] of Object.entries(rawSubjects)) {
        const src = (typeof v === "string") ? { name: v }
            : (v && typeof v === "object" && !Array.isArray(v)) ? v : {};
        subjects[k] = {
            name: String(src.name ?? ""),
            locked: String(src.locked ?? ""),
            context: String(src.context ?? ""),
        };
    }
    return {
        refs: refs.map((r, i) => ({
            tag: String(r.tag || "").replace(/^@/, ""),
            file: String(r.file || ""),
            // A plan authored against the sockets carries a slot and no file.
            // Kept only so the row can say what it used to be plugged into.
            legacy_slot: (!r.file && r.slot != null) ? Number(r.slot) : null,
            // Derived, never authored -- mirrors refs.py.
            slot: i + 1,
            subject: r.subject == null ? null : Number(r.subject),
            retention: r.retention || "",
            desc: r.desc || "",
            shots: Array.isArray(r.shots) ? r.shots.slice() : null,
            mp: r.mp == null ? 0 : Number(r.mp) || 0,
            qwen_mp: r.qwen_mp == null ? 0 : Number(r.qwen_mp) || 0,
            source: r.source === "refmod" ? "refmod" : "image",
            strength: r.strength == null ? 1 : Number(r.strength),
            step_curve: typeof r.step_curve === "string" && r.step_curve ? r.step_curve : "full",
            members: Array.isArray(r.members)
                ? r.members.map((x) => Number(x)).filter((x) => Number.isInteger(x) && x >= 0)
                : null,
            shot_strengths: (r.shot_strengths && typeof r.shot_strengths === "object" && !Array.isArray(r.shot_strengths))
                ? { ...r.shot_strengths } : null,
            voice: r.voice || "",
            voice_start: Number(r.voice_start) || 0,
            voice_end: Number(r.voice_end) || 0,
        })),
        subjects,
    };
}

/* Offered pixel budgets, in MP. The floor mirrors refs.REF_MP_MIN -- below it
 * you can no longer tell a room from another room. There is no ceiling entry:
 * "full" (no cap) is the blank option.
 *
 * The list used to stop at 2.0, which quietly put the high-resolution face
 * plate out of reach: core scales a reference to 2048 on its SHORT edge under
 * ref_image_size=max, so a 2:3 portrait arrives at 2048x3072 -- 6.3 MP -- and a
 * 9:16 one at 7.5 MP. Capping the rail at 2.0 meant the only way to ask for
 * that was to hand-edit the ref_plan JSON. It now runs to 8.0, which is the
 * last value core can still reach; anything past it is a dial wired to nothing,
 * because H3 only ever scales a reference DOWN.
 *
 * Worth knowing when picking one: on the DEFAULT ref_image_size=match every
 * reference is first scaled to the output's pixel area, and mp only caps
 * further -- so at 768p (~1.03 MP) every value above 1.0 here does nothing at
 * all. The high values are the max half of a pair, not a slider on their own.
 *
 * Adding options to an existing combo is safe; adding widgets is not. */
const REF_MP = [0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0];

export function refPlanToJson(plan) {
    if (!plan.refs.length && !Object.keys(plan.subjects).length) return "";
    const refs = plan.refs.map((r) => {
        // `slot` is deliberately not written back: it is derived from row
        // order on both sides, and persisting it would resurrect the socket
        // number a legacy plan is trying to leave behind.
        const out = { tag: r.tag };
        if (r.file) out.file = r.file;
        else if (r.legacy_slot) out.slot = r.legacy_slot;
        if (r.subject != null) out.subject = r.subject;
        if (r.retention) out.retention = r.retention;
        if (r.desc) out.desc = r.desc;
        if (r.shots && r.shots.length) out.shots = r.shots;
        // Omitted when uncapped, so a plan authored before this existed round
        // trips byte-identical and no diff appears from merely opening it.
        if (r.mp) out.mp = r.mp;
        // Same rule: absent is "auto", so old plans round trip unchanged.
        if (r.qwen_mp) out.qwen_mp = r.qwen_mp;
        // Omitted when empty, so a plan written before row voices existed
        // round trips byte-identical.
        if (r.voice) out.voice = r.voice;
        // Same rule for the trim: absent is the whole file.
        if (r.voice_start) out.voice_start = Math.round(r.voice_start * 1000) / 1000;
        if (r.voice_end) out.voice_end = Math.round(r.voice_end * 1000) / 1000;
        // Omitted on a still, and at defaults, for byte-identical round trips.
        if (r.source === "refmod") {
            out.source = "refmod";
            if (r.strength != null && Number(r.strength) !== 1) out.strength = Number(r.strength);
            if (r.step_curve && r.step_curve !== "full") out.step_curve = r.step_curve;
            if (Array.isArray(r.members) && r.members.length) out.members = r.members;
            if (r.shot_strengths && Object.keys(r.shot_strengths).length) {
                out.shot_strengths = r.shot_strengths;
            }
        }
        return out;
    });
    const body = { refs };
    if (Object.keys(plan.subjects).length) body.subjects = plan.subjects;
    return JSON.stringify(body, null, 2);
}

/** Rows that actually name a picture. Only these take a <Picture N> ordinal. */
function wiredSlots(plan) {
    const out = new Set();
    (plan.refs || []).forEach((r, i) => {
        if (r.file) out.add(i + 1);
    });
    return out;
}

/**
 * Per-hop ordinals, exactly as `refs.active_refs` + `refs.ordinals` compute
 * them: slot order, restricted to slots with an image.
 */
function ordinalsFor(plan, wired) {
    const active = plan.refs
        .filter((r) => wired.has(r.slot))
        .sort((a, b) => a.slot - b.slot);
    const ords = new Map();
    active.forEach((r, i) => ords.set(r.tag, i + 1));
    return ords;
}

function validate(plan, wired) {
    const problems = new Map(); // tag -> message
    const seenTag = new Map();
    const seenSlot = new Map();
    for (const r of plan.refs) {
        if (!r.tag) {
            problems.set(r, "a tag is required — prose refers to it as @tag");
            continue;
        }
        if (seenTag.has(r.tag)) {
            problems.set(r, `@${r.tag} is already used — tags must be unique`);
        }
        seenTag.set(r.tag, r);
        if (seenSlot.has(r.slot)) {
            problems.set(r, `slot ${r.slot} is already taken by @${seenSlot.get(r.slot).tag}`);
        }
        seenSlot.set(r.slot, r);
        // The picture, not the slot. `wired` is derived from row index; a
        // freshly clicked-in row used to have file set and slot unset, so
        // this branch fired "no picture chosen" over a visible thumbnail.
        if (!String(r.file || "") && !String(r.voice || "")) {
            problems.set(r, r.legacy_slot
                ? `was wired to ref_image_${r.legacy_slot}, which no longer exists `
                  + `— pick its picture to bring this ref back`
                : (r.source === "refmod"
                    ? "no refmod chosen — this ref is inactive"
                    : "no picture chosen — this ref is inactive"));
        }
    }
    // A subject block nothing points at is continuity prose for someone who
    // never appears; parse_ref_plan rejects it outright.
    const used = new Set(plan.refs.filter((r) => r.subject != null).map((r) => String(r.subject)));
    const orphans = Object.keys(plan.subjects).filter((k) => !used.has(String(k)));
    return { problems, orphans };
}

export function createRefRail(node, { getPlan, setPlan, onChange, hopCount,
                                      getRaw, isBad, onBuildRefMod }) {
    const root = el("div", "h3e-section");
    const head = el("div", "h3e-head");
    const title = el("span", "h3e-title", "REFERENCES");
    const count = el("span", "h3e-count");
    head.appendChild(title);
    head.appendChild(count);
    head.appendChild(el("span", "h3e-spacer"));
    if (typeof onBuildRefMod === "function") {
        head.appendChild(button("\u2b21 RefMod Builder", "Open the in-node RefMod Workbench & Sheet Extractor", () => {
            onBuildRefMod("");
        }));
    }
    head.appendChild(button("+ ref", "Add a reference row", () => {
        const plan = getPlan();
        plan.refs.push(blankRef(plan.refs));
        reindex(plan);
        setPlan(plan);
        render();
        onChange?.();
    }));
    root.appendChild(head);

    const list = el("div", "h3e-refs");
    root.appendChild(list);

    /* JSON escape hatch, mirroring the one in the SCRIPT section.
     *
     * Without it the rail was the ONLY editor for `ref_plan`, which made a
     * model-authored register unpastable: prompt_pack hands the author two
     * JSON documents and only `shot_plan` had a box to paste into.
     *
     * It also closes a quieter bug. `parseRefPlan` returns null on text it
     * cannot read, and the caller swapped in an empty plan -- so the next rail
     * edit wrote "" over the very text the author was trying to repair. The
     * paste was destroyed by the act of fixing it. Now the raw value stays in
     * the widget until something parses, and this box is where it shows.
     */
    const jsonWrap = el("details", "h3e-json-wrap");
    const jsonSum = el("summary", null, "JSON");
    jsonSum.title = "The literal ref_plan value. Editing here updates the rows.";
    jsonWrap.appendChild(jsonSum);
    const jsonArea = el("textarea", "h3e-json");
    jsonArea.spellcheck = false;
    jsonArea.placeholder = '{"refs": [{"tag": "hero_face", "file": "face.jpg", '
        + '"subject": 1, "retention": "fully_preserved", "shots": [1, 2]}], '
        + '"subjects": {"1": {"name": "the cook", "locked": "..."}}}';
    jsonWrap.appendChild(jsonArea);
    const jsonErr = el("div", "h3e-note");
    jsonErr.style.display = "none";
    jsonWrap.appendChild(jsonErr);
    jsonArea.addEventListener("input", () => {
        const parsed = parseRefPlan(jsonArea.value);
        if (parsed === null) {
            jsonErr.textContent =
                "Not valid JSON -- the rows are showing the last good version.";
            jsonErr.classList.add("h3e-note-error");
            jsonErr.style.display = "";
            return;
        }
        jsonErr.style.display = "none";
        jsonErr.classList.remove("h3e-note-error");
        setPlan(parsed);
        onChange?.();
        render();
    });
    root.appendChild(jsonWrap);

    let V = null;
    vocab().then((v) => { V = v; render(); });
    // Re-render when a retry in the plan editor reloads the vocabulary.
    onVocabRefresh(() => {
        _refmods = null;
        vocab().then((v) => { V = v; render(); });
    });
    _refmodListeners.add(() => render());

    function commit() {
        setPlan(getPlan());
        onChange?.();
        render();
    }

    function renderSubject(num) {
        const plan = getPlan();
        const s = plan.subjects[num] || (plan.subjects[num] = { name: "", locked: "", context: "" });
        const box = el("div", "h3e-subject");
        box.appendChild(el("span", "h3e-subj-badge", `Subject ${num}`));

        const mk = (key, placeholder, hint) => {
            const i = el("input", "h3e-input");
            i.type = "text";
            i.value = s[key] || "";
            i.placeholder = placeholder;
            i.title = hint;
            i.addEventListener("input", () => { s[key] = i.value; setPlan(plan); onChange?.(); });
            // Same as the row's desc: `input` writes the widget but does not
            // re-render, so without this the JSON box kept the pre-edit text,
            // and an edit made in that box wrote the stale subject back.
            i.addEventListener("change", commit);
            return i;
        };
        box.appendChild(mk("name", "what to call them",
            "Used as “<Subject N> is <name>, the person in <Picture …>”. A role works better than a proper name."));
        box.appendChild(mk("locked", "traits that must not drift",
            "Injected verbatim on every hop. Only put things that are actually in the photograph here — at cfg 1.0 every word is additive."));
        box.appendChild(mk("context", "current standing state",
            "Same as locked but less rigid: what they are wearing right now, current mood."));
        return box;
    }

    // Each bar runs an animation frame and holds an <audio>; a render that
    // drops the row has to let go of both. Pickers hold shared file-list
    // subscriptions that must also be unsubscribed on re-render.
    const trimBars = [];
    const pickers = [];
    let openDrawerKey = null;
    let drawerQuery = "";
    let drawerRole = "all";

    function renderRefmodDrawer(container, r, plan) {
        container.textContent = "";
        const filterRow = el("div", "h3e-refmod-filter");
        const qIn = el("input", "h3e-input");
        qIn.type = "text";
        qIn.placeholder = "search refmods by name, role, or description...";
        qIn.value = drawerQuery;
        qIn.addEventListener("input", () => {
            drawerQuery = qIn.value;
            paintGrid();
        });
        filterRow.appendChild(qIn);

        const roleChips = el("div", "h3e-refmod-chips");
        const roleFilterOpts = ["all", "identity", "wardrobe", "bodyshape", "helper", "pose_motion", "background", "style", "reflora"];
        for (const rf of roleFilterOpts) {
            const b = button(rf.replace("_", " "), `Filter RefMods by ${rf}`, () => {
                drawerRole = rf;
                renderRefmodDrawer(container, r, plan);
            }, "h3e-btn h3e-refmod-chip" + (drawerRole === rf ? " h3e-refmod-chip-on" : ""));
            roleChips.appendChild(b);
        }
        filterRow.appendChild(roleChips);
        filterRow.appendChild(button("↻", "Refresh RefMods list from disk", () => {
            invalidateRefmods(true);
        }));
        container.appendChild(filterRow);

        const grid = el("div", "h3e-refmod-grid");
        container.appendChild(grid);

        const inspectWrap = el("div", "h3e-refmod-inspect");
        container.appendChild(inspectWrap);

        function paintGrid() {
            grid.textContent = "";
            const rows = _refmods || [];
            if (_refmods === null) {
                grid.appendChild(el("div", "h3e-note h3e-note-hint", "Loading RefMods..."));
                refmodRows().then(() => renderRefmodDrawer(container, r, plan));
                return;
            }
            const q = String(drawerQuery || "").trim().toLowerCase();
            const filtered = rows.filter((f) => {
                if (drawerRole !== "all") {
                    if (drawerRole === "reflora") {
                        if (f.format !== "reflora") return false;
                    } else if ((f.role || "generic") !== drawerRole) {
                        return false;
                    }
                }
                if (q) {
                    const hay = `${f.name || ""} ${f.role || ""} ${f.description || ""}`.toLowerCase();
                    if (!hay.includes(q)) return false;
                }
                return true;
            });
            if (!filtered.length) {
                grid.appendChild(el("div", "h3e-note h3e-note-hint",
                    rows.length ? "No RefMods match this filter." : "No .safetensors found in models/refmods/ (or RefLoRAs in models/loras/)."));
                return;
            }
            for (const f of filtered) {
                const card = el("div", "h3e-refmod-card" + (r.file === f.name ? " h3e-refmod-card-on" : ""));
                card.title = `${f.name} · ${f.format || "v4"} · ${f.role || "generic"} · ${f.tokens || 0} tokens`;
                if (f.has_looks) {
                    const img = el("img", "h3e-refmod-cardimg");
                    img.loading = "lazy";
                    img.src = `/h3_ref_chain/refmod_thumb?name=${encodeURIComponent(f.name)}&member=0&w=160`;
                    img.alt = f.name;
                    img.addEventListener("error", () => { img.style.display = "none"; });
                    card.appendChild(img);
                } else {
                    card.appendChild(el("div", "h3e-refmod-cardimg", f.kind === "audio" ? "♪ audio" : "no looks"));
                }
                const meta = el("div", "h3e-refmod-cardmeta");
                meta.appendChild(el("div", null, f.name));
                const pills = el("div", "h3e-refmod-chips");
                pills.appendChild(el("span", "h3e-refmod-pill", `${f.format || "v4"}${f.members_count > 1 ? ` · ${f.members_count}m` : ""}`));
                pills.appendChild(el("span", "h3e-refmod-pill", f.role || "generic"));
                if (f.tokens) pills.appendChild(el("span", "h3e-refmod-pill", `${f.tokens}t`));
                if (f.has_audio_latent || f.voice?.file) pills.appendChild(el("span", "h3e-refmod-pill", "♪"));
                meta.appendChild(pills);
                card.appendChild(meta);
                card.addEventListener("click", () => {
                    r.file = f.name;
                    r.legacy_slot = null;
                    r.members = null;
                    if (!String(r.desc || "").trim()) {
                        const cap = refmodCaption(f.name);
                        if (cap) r.desc = cap;
                    }
                    if (f.default_step_curve && f.default_step_curve !== "full" && (!r.step_curve || r.step_curve === "full")) {
                        r.step_curve = f.default_step_curve;
                    }
                    commit();
                });
                grid.appendChild(card);
            }
        }

        function paintInspector() {
            inspectWrap.textContent = "";
            if (!r.file) return;
            const targetFile = r.file;
            refmodInspect(targetFile).then((info) => {
                if (!info || r.file !== targetFile) return;
                inspectWrap.textContent = "";
                const visMembers = (info.members || []).filter((m) => m.kind === "image" || m.kind === "video");
                if (visMembers.length > 1) {
                    const mHead = el("div", "h3e-note h3e-note-hint",
                        `v5 Bundle Members (${visMembers.length} visual): click to filter which members load on this row`);
                    inspectWrap.appendChild(mHead);
                    const mRow = el("div", "h3e-refmod-mchips");
                    const activeSet = new Set(
                        Array.isArray(r.members) && r.members.length
                            ? r.members
                            : visMembers.map((m) => m.index),
                    );
                    for (const m of visMembers) {
                        const isOn = activeSet.has(m.index);
                        const chip = el("button", "h3e-btn h3e-refmod-mchip" + (isOn ? " h3e-refmod-mchip-on" : ""));
                        chip.type = "button";
                        const dim = `${(m.shape?.[2] || 0) * 16}×${(m.shape?.[1] || 0) * 16}`;
                        chip.title = `Member #${m.index + 1} (${m.kind} ${dim}, ${m.tokens || 0} tok)`;
                        if (m.has_looks) {
                            const mi = el("img", "h3e-refmod-thumb");
                            mi.src = `/h3_ref_chain/refmod_thumb?name=${encodeURIComponent(targetFile)}&member=${m.index}&w=96`;
                            mi.alt = `#${m.index + 1}`;
                            mi.addEventListener("error", () => { mi.style.display = "none"; });
                            chip.appendChild(mi);
                        }
                        chip.appendChild(el("span", null, `#${m.index + 1} ${dim}`));
                        chip.addEventListener("click", () => {
                            const next = new Set(activeSet);
                            if (next.has(m.index)) {
                                if (next.size <= 1) return;
                                next.delete(m.index);
                            } else {
                                next.add(m.index);
                            }
                            const sorted = [...next].sort((a, b) => a - b);
                            r.members = sorted.length === visMembers.length ? null : sorted;
                            commit();
                        });
                        mRow.appendChild(chip);
                    }
                    inspectWrap.appendChild(mRow);
                }

                // Header-only quick metadata editor (scrubs legacy "0" descriptions, sets role / curve)
                const editRow = el("div", "h3e-refmod-edit");
                const descIn = el("input", "h3e-input");
                descIn.type = "text";
                descIn.placeholder = "stored header description (empty)";
                descIn.value = info.description || "";
                descIn.title = "Stored inside the .safetensors header (does not touch the latent).";

                const roleSel = el("select", "h3e-select");
                for (const rc of CONCEPT_ROLES) {
                    const o = el("option", null, rc);
                    o.value = rc;
                    roleSel.appendChild(o);
                }
                roleSel.value = CONCEPT_ROLES.includes(info.role) ? info.role : "generic";

                const scSel = el("select", "h3e-select");
                for (const [val, lbl] of STEP_CURVES) {
                    const o = el("option", null, lbl);
                    o.value = val;
                    scSel.appendChild(o);
                }
                scSel.value = info.default_step_curve || "full";

                const saveStatus = el("span", "h3e-count");
                const capBtn = button("✨", "Auto-caption from stored RefMod looks via your VLM writer", async () => {
                    capBtn.disabled = true;
                    saveStatus.textContent = "captioning...";
                    try {
                        const res = await fetch("/h3_ref_chain/refmod_caption", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                name: targetFile,
                                role: roleSel.value || "identity",
                                auto_wake: true,
                                save_meta: false,
                            }),
                        });
                        const j = await res.json();
                        if (!res.ok || !j.ok || !j.description) {
                            saveStatus.textContent = j.error || "caption failed";
                        } else {
                            descIn.value = j.description;
                            saveStatus.textContent = "captioned — click save header";
                        }
                    } catch (err) {
                        saveStatus.textContent = String(err);
                    } finally {
                        capBtn.disabled = false;
                    }
                });
                const saveBtn = button("save header", "Write description, role & default curve to the .safetensors header without re-encoding", async () => {
                    saveBtn.disabled = true;
                    saveStatus.textContent = "saving...";
                    try {
                        const res = await fetch("/h3_ref_chain/refmod_update", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                name: targetFile,
                                action: "meta",
                                description: descIn.value,
                                role: roleSel.value,
                                default_step_curve: scSel.value,
                            }),
                        });
                        const j = await res.json();
                        if (!res.ok || !j.ok) {
                            saveStatus.textContent = j.error || "failed";
                        } else {
                            if (Array.isArray(j.files)) _refmods = j.files;
                            if (j.inspect) _inspectCache.set(targetFile, j.inspect);
                            if (typeof window !== "undefined") {
                                window.dispatchEvent?.(new CustomEvent("htc:refmods-changed"));
                            }
                            saveStatus.textContent = "saved!";
                        }
                    } catch (err) {
                        saveStatus.textContent = String(err);
                    } finally {
                        saveBtn.disabled = false;
                    }
                });
                editRow.append(el("span", "h3e-chips-label", "header"), descIn, capBtn, roleSel, scSel, saveBtn, saveStatus);
                inspectWrap.appendChild(editRow);
            });
        }

        paintGrid();
        paintInspector();
    }

    function commitLive(planObj) {
        setPlan(planObj || getPlan());
        onChange?.();
        render();
    }

    function render() {
        for (const b of trimBars.splice(0)) b.destroy();
        for (const p of pickers.splice(0)) p.destroy?.();
        list.textContent = "";
        // Never while focused: it would reformat mid-keystroke and steal the caret.
        if (document.activeElement !== jsonArea) jsonArea.value = getRaw?.() ?? "";
        const plan = getPlan();
        if (!plan) return;
        reindex(plan);
        if (isBad?.()) {
            jsonWrap.open = true;
            list.appendChild(el("div", "h3e-note h3e-note-error",
                "ref_plan is not valid JSON. Fix it in the JSON section below "
                + "and the rows will come back."));
        }
        const wired = wiredSlots(plan);
        const ords = ordinalsFor(plan, wired);
        const { problems, orphans } = validate(plan, wired);
        count.textContent = `${plan.refs.length} · ${wired.size} with a picture`;

        if (!plan.refs.length) {
            const empty = el("div", "h3e-empty",
                "No references. Add one per picture, then write @tag in your beats.");
            list.appendChild(empty);
        }

        const bySubject = new Map();
        for (const r of plan.refs) {
            const row = el("div", "h3e-ref");
            const bad = problems.get(r);
            if (bad) row.classList.add("h3e-bad");
            if (!wired.has(r.slot) && !String(r.voice || "")) row.classList.add("h3e-inactive");

            const ord = ords.get(r.tag);
            const badge = el("span", "h3e-ord", ord ? String(ord) : (r.voice ? "♪" : "–"));
            badge.title = ord
                ? `Resolves to <Picture ${ord}> on every hop this ref is active.`
                : (r.voice
                    ? "Audio-only reference (<Audio N> on the hops it rides); takes no <Picture N> ordinal."
                    : "No picture, so it takes no ordinal this run.");
            row.appendChild(badge);

            const tag = el("input", "h3e-input h3e-tag");
            tag.type = "text";
            tag.value = "@" + r.tag;
            tag.title = "Stable name. Write this in a beat and it resolves to the right picture per hop.";
            // Push to the widget per keystroke; commit() re-renders and would
            // steal the caret, so only the blur handler may call it.
            tag.addEventListener("input", () => {
                r.tag = tag.value.trim().replace(/^@/, "").replace(/[^A-Za-z0-9_]/g, "_");
                setPlan(plan);
            });
            tag.addEventListener("change", commit);
            row.appendChild(tag);

            const source = el("select", "h3e-select");
            for (const [value, label] of [["image", "still"], ["refmod", "refmod"]]) {
                const o = el("option", null, label);
                o.value = value;
                source.appendChild(o);
            }
            source.value = r.source === "refmod" ? "refmod" : "image";
            source.title = "A still is a file in input/h3_refs. A refmod is a safetensors "
                + "file in models/refmods, scheduled onto hops the same way.";
            source.addEventListener("change", () => {
                r.source = source.value;
                r.file = "";
                if (r.source !== "refmod") {
                    r.strength = 1;
                    r.step_curve = "full";
                    r.members = null;
                    r.shot_strengths = null;
                }
                commit();
            });
            row.appendChild(source);

            // Was a `slot N` dropdown naming one of nine IMAGE sockets. The
            // picture itself lives here now: drop a file on it, click to
            // browse, or choose one already in the reference folder.
            const rowSlot = r.slot;
            const rowTag = r.tag;
            const resolveLiveRow = () => {
                const livePlan = getPlan();
                const live = (livePlan?.refs || []).find(
                    (x) => (rowTag && x.tag === rowTag) || x.slot === rowSlot,
                ) || r;
                return { livePlan, live };
            };
            let pendingPlan = null;
            const pick = createPicker({
                kind: "image",
                get: () => r.file || "",
                set: (v) => {
                    const { livePlan, live } = resolveLiveRow();
                    live.file = v;
                    // Choosing a picture is what retires a legacy row, so the
                    // "was wired to slot N" note has to go with it.
                    if (v) live.legacy_slot = null;
                    pendingPlan = livePlan;
                },
                // Rebuild on a later turn. `commit` tears down this <select>
                // in the middle of its own `change`; the browser then fires
                // again with value "", which used to wipe `file` and leave
                // the red "no picture chosen" banner on a row that just
                // showed a thumbnail. Paste-JSON never hit this because it
                // never goes through the dropdown.
                onChange: () => queueMicrotask(() => {
                    const p = pendingPlan || getPlan();
                    pendingPlan = null;
                    commitLive(p);
                }),
                title: "The picture this reference stands for. Drop a file, or click to browse.",
            });
            pickers.push(pick);
            pick.root.classList.add("h3e-slot");
            const rowKey = r.tag || String(r.slot);
            if (r.source === "refmod") {
                const modWrap = el("div", "h3e-slot h3e-refmod-slot");
                if (r.file) {
                    const th = el("img", "h3e-refmod-thumb");
                    th.src = `/h3_ref_chain/refmod_thumb?name=${encodeURIComponent(r.file)}&member=${Array.isArray(r.members) && r.members.length ? r.members[0] : 0}&w=96`;
                    th.alt = r.file;
                    th.addEventListener("error", () => { th.style.display = "none"; });
                    modWrap.appendChild(th);
                }
                const mod = el("select", "h3e-select");
                const blank = el("option", null, "choose a refmod");
                blank.value = "";
                mod.appendChild(blank);
                const have = new Set();
                const addOption = (item) => {
                    const name = typeof item === "string" ? item : item?.name;
                    if (!name || have.has(name)) return;
                    have.add(name);
                    const label = (typeof item === "object" && item)
                        ? `${name} [${item.format || "v4"}${item.members_count > 1 ? `·${item.members_count}m` : ""}·${item.role || "gen"}]`
                        : name;
                    const o = el("option", null, label);
                    o.value = name;
                    mod.appendChild(o);
                };
                if (r.file) addOption(refmodRowMeta(r.file) || r.file);
                refmodRows().then((rows) => {
                    for (const item of rows) addOption(item);
                    if (mod.value !== (r.file || "")) mod.value = r.file || "";
                });
                mod.value = r.file || "";
                mod.title = "A safetensors file in models/refmods (or RefLoRA in models/loras).";
                mod.addEventListener("change", () => {
                    r.file = mod.value;
                    r.members = null;
                    if (r.file) r.legacy_slot = null;
                    if (r.file && !String(r.desc || "").trim()) {
                        const cap = refmodCaption(r.file);
                        if (cap) r.desc = cap;
                    }
                    const meta = refmodRowMeta(r.file);
                    if (meta?.default_step_curve && meta.default_step_curve !== "full" && (!r.step_curve || r.step_curve === "full")) {
                        r.step_curve = meta.default_step_curve;
                    }
                    queueMicrotask(() => commit());
                });
                modWrap.appendChild(mod);
                const browseBtn = button(
                    openDrawerKey === rowKey ? "▾" : "▤",
                    "Browse RefMods visually, toggle v5 bundle members, or edit header metadata",
                    () => {
                        openDrawerKey = openDrawerKey === rowKey ? null : rowKey;
                        render();
                    },
                );
                if (Array.isArray(r.members) && r.members.length) {
                    browseBtn.textContent = `${r.members.length}m`;
                }
                modWrap.appendChild(browseBtn);
                if (typeof onBuildRefMod === "function") {
                    modWrap.appendChild(button(
                        "\u270e",
                        r.file ? `Open ${r.file} in the RefMod Builder tab` : "Build a new RefMod in the RefMod tab",
                        () => onBuildRefMod(r.file || ""),
                    ));
                }
                row.appendChild(modWrap);
            } else {
                row.appendChild(pick.root);
            }

            const subj = el("select", "h3e-select h3e-subj");
            const none = el("option", null, "setting/prop");
            none.value = "";
            subj.appendChild(none);
            // The ceiling is `MAX_REF_IMAGES`, served by routes.py: there
            // cannot be more distinct subjects than there are pictures. It was
            // hard-coded to 4 here, so a register with more than four people
            // had no option to select for subjects 5+ -- and a <select> given a
            // value with no matching <option> falls back to the FIRST one,
            // which is "setting/prop". Those rows did not read as blank, they
            // read as "this picture is scenery", the exact opposite of the
            // JSON, and touching one wrote that back and demoted a character
            // out of `_identity_lock`.
            const maxSubj = Math.max(1, Number(V?.max_ref_images) || 9);
            const nums = [];
            for (let i = 1; i <= maxSubj; i += 1) nums.push(i);
            // Belt and braces against this ever recurring: a subject number
            // from outside the generated range still gets an option, so the
            // value round-trips instead of silently becoming setting/prop.
            if (r.subject != null && !nums.includes(Number(r.subject))) {
                nums.push(Number(r.subject));
                nums.sort((a, b) => a - b);
            }
            for (const i of nums) {
                const o = el("option", null, `Subject ${i}`);
                o.value = String(i);
                subj.appendChild(o);
            }
            subj.value = r.subject == null ? "" : String(r.subject);
            subj.title = "Group pictures of the SAME person under one subject number. "
                + "Two different people sharing a number makes the model render the average of their faces.";
            subj.addEventListener("change", () => {
                r.subject = subj.value === "" ? null : Number(subj.value);
                if (!r.retention) r.retention = r.subject ? "fully_preserved" : "reference";
                commit();
            });
            row.appendChild(subj);

            const retOpts = Object.keys(V?.retention || {});
            const ret = select(retOpts, r.retention, (v) => { r.retention = v; commit(); }, {
                blankLabel: r.subject ? "fully preserved" : "reference",
                titles: V?.retention || {},
            });
            ret.classList.add("h3e-ret");
            ret.title = "How much of this picture carries over. Hover an option for the exact sentence.";
            row.appendChild(ret);

            /* Pixel budget for THIS picture.
             *
             * A token dial, not a quality one: H3 turns each reference into
             * latent_h*latent_w entries in the DiT payload and attends over all
             * of them on every step of every hop, so a location plate costing
             * what a face costs is waste.
             *
             * "full" is the top and it is not a number, because H3 only ever
             * scales a reference DOWN -- a cap above the file's own size is a
             * dial wired to nothing, and a number there would imply upscaling
             * that never happens. */
            /* A cap that is not one of the offered values still has to SHOW.
             * `select` assigns a value matching no option, which renders the
             * control blank -- and blank here reads as "full", so a row capped
             * at 0.54 looked uncapped while it was working. Offer the row's
             * own value alongside the standard ones. */
            const mpOpts = REF_MP.map(String);
            if (r.mp && !mpOpts.includes(String(r.mp))) {
                mpOpts.push(String(r.mp));
                mpOpts.sort((a, b) => Number(a) - Number(b));
            }
            const mp = select(mpOpts, r.mp ? String(r.mp) : "", (v) => {
                r.mp = v ? Number(v) : 0;
                commit();
            }, {
                blankLabel: "full",
                titles: Object.fromEntries(mpOpts.map((v) =>
                    [String(v), `Cap the video model's copy of this picture at ${v} MP.`])),
            });
            mp.classList.add("h3e-mp");
            mp.title = r.source === "refmod"
                ? "Caps the picture shown to the text encoder. The stored latent is unchanged."
                : "Pixel budget for this reference. Lower is fewer tokens and a "
                  + "faster step; 'full' leaves the file alone. Feed a face big and a "
                  + "location plate small.";
            row.appendChild(mp);

            /* What Qwen3-VL (the text encoder) is shown of this picture,
             * apart from the copy `mp` caps for the video model. Read from
             * the ORIGINAL file, so it can be bigger than the render.
             * Blank = auto (qwen_view.py): sheets and garments ~1 MP, props
             * ~0.15 MP, everything else as Core sends it. Costs a few seconds
             * of text encode, almost nothing in the sampler. A RefMod row has
             * no file to read, and puts its strength in this cell instead. */
            if (r.source !== "refmod") {
                const qOpts = REF_MP.map(String);
                if (r.qwen_mp && !qOpts.includes(String(r.qwen_mp))) {
                    qOpts.push(String(r.qwen_mp));
                    qOpts.sort((a, b) => Number(a) - Number(b));
                }
                const qmp = select(qOpts, r.qwen_mp ? String(r.qwen_mp) : "", (v) => {
                    r.qwen_mp = v ? Number(v) : 0;
                    commit();
                }, {
                    blankLabel: "auto",
                    titles: Object.fromEntries(qOpts.map((v) =>
                        [String(v), `Show the text encoder the original file at ${v} MP.`])),
                });
                qmp.classList.add("h3e-qmp");
                qmp.title = "What the text encoder (Qwen) sees of this picture, read from the "
                    + "original file. 'auto': character sheets and garments ~1 MP, props "
                    + "~0.15 MP, plates as rendered. Bigger helps likeness; the video "
                    + "model's copy (the MP box) is unchanged.";
                row.appendChild(qmp);
            }

            if (r.source === "refmod") {
                const ctrl = el("div", "h3e-qmp h3e-refmod-ctrl");
                const strength = el("input", "h3e-input");
                strength.type = "number";
                strength.min = "0";
                strength.max = "3";
                strength.step = "0.05";
                strength.value = String(r.strength == null ? 1 : r.strength);
                strength.title = "RefMod strength (0..3). 1.0 keeps the stored latent; <1 blends toward blur; >1 stacks copies + blur residual for stronger lock.";
                strength.addEventListener("input", () => {
                    const n = Number(strength.value);
                    if (Number.isFinite(n)) r.strength = Math.min(3, Math.max(0, n));
                    setPlan(plan);
                });
                strength.addEventListener("change", commit);

                const curveSel = el("select", "h3e-select");
                for (const [val, lbl] of STEP_CURVES) {
                    const o = el("option", null, lbl);
                    o.value = val;
                    curveSel.appendChild(o);
                }
                curveSel.value = r.step_curve || "full";
                curveSel.title = "Per-step denoising curve: early lock anchors anatomy/helpers in steps 0-40%; late detail refines textures; fade decays smoothly.";
                curveSel.addEventListener("change", () => {
                    r.step_curve = curveSel.value || "full";
                    commit();
                });
                ctrl.append(strength, curveSel);
                row.appendChild(ctrl);
            }

            // The voice this reference speaks with. Bound to the ROW, not
            // to the run, so it rides exactly the hops the row rides --
            // voice_file 1-3 are global and cannot say which of two faces
            // owns which of two recordings.
            let pendingVoicePlan = null;
            const voice = createPicker({
                kind: "audio",
                get: () => r.voice || "",
                set: (v) => {
                    const { livePlan, live } = resolveLiveRow();
                    live.voice = v;
                    pendingVoicePlan = livePlan;
                },
                onChange: () => queueMicrotask(() => {
                    const p = pendingVoicePlan || getPlan();
                    pendingVoicePlan = null;
                    commitLive(p);
                }),
                title: "Optional voice for this reference. It rides beside the "
                    + "picture or clip as its own <Audio N>, cited on the hops "
                    + "this row rides. Empty on a RefMod row uses the mod's own "
                    + "voice. Trim it below to one clean sentence: H3 encodes "
                    + "the whole file, and a hop whose lines run out replays it.",
            });
            pickers.push(voice);
            voice.root.classList.add("h3e-slot", "h3e-voice");
            row.appendChild(voice.root);

            // The cell, not the input, carries .h3e-desc: it holds the grid
            // track, so the caption button below cannot push × to a new line.
            const descCell = el("div", "h3e-desc h3e-desc-cell");
            const desc = el("input", "h3e-input");
            desc.type = "text";
            desc.value = r.desc || "";
            desc.placeholder = "describe this photo";
            desc.title = "Goes into retention_analysis verbatim. Describe the picture you actually wired — "
                + "at cfg 1.0 a detail that is not there is asked for, not ignored.";
            desc.addEventListener("input", () => { r.desc = desc.value; setPlan(plan); });
            desc.addEventListener("change", commit);
            descCell.appendChild(desc);
            row.appendChild(descCell);
            if (r.source === "refmod" && r.file) {
                // Shown only when the row's text and the file's caption
                // differ. The row's text is what reaches the prompt; the
                // file's is never read at render time.
                const useCap = button("↺", "", () => {
                    r.desc = refmodCaption(r.file);
                    commit();
                });
                useCap.style.display = "none";
                descCell.appendChild(useCap);
                refmodRows().then(() => {
                    const cap = refmodCaption(r.file);
                    if (!cap || String(r.desc || "").trim() === cap) return;
                    useCap.title = `Use the text stored in ${r.file}: "${cap}"`;
                    useCap.style.display = "";
                    if (!String(r.desc || "").trim()) desc.placeholder = cap;
                });
            }

            row.appendChild(button("×", "Remove this reference", () => {
                const p = getPlan();
                p.refs.splice(p.refs.indexOf(r), 1);
                pruneSubjects(p);
                reindex(p);
                setPlan(p);
                onChange?.();
                render();
            }, "h3e-btn h3e-x"));

/* Which hops this photograph rides. An empty schedule means hop 1
         * only on a `next` chain -- that is the pin-only recipe
         * chain_00037/00038 were rendered with, and until now it could
         * only be set by hand in the JSON.
         *
         * D6: this was one numbered chip per hop per row -- 133 of them at a
         * 19-hop plan, wrapping to four lines, where selecting hop 13 meant
         * counting. It is now a continuous BAR on the score strip's geometry, so
         * it lines up column-for-column with the strip above and with the
         * filmstrip: the same x is the same hop in all three, and a click reads
         * as "this column", not "the thirteenth chip".
         *
         * Writes are unchanged: `r.shots` in ref_plan, via the same commit().
         * The brief asks for drag-to-set ranges, and that is what the bar does
         * -- press picks the anchor, drag extends, release commits ONE write for
         * the whole run, not one per column. */
      const hops = Math.max(1, Number(hopCount?.() || 1));
      const hopbar = el("div", "h3e-hopbar");
      hopbar.appendChild(el("span", "h3e-chips-label", "rides hops"));
      const bar = el("div", "h3e-hopbar-track");
      bar.title = "Click a hop to toggle it. Drag across hops to set a range. "
        + "Leave every hop off to let the motion pin carry wardrobe and room.";
      const geo = stripGeometry(hops, hopBarWidth(node), 1, { autoZoom: false });

      const isOn = (h) => Array.isArray(r.shots) && r.shots.includes(h);
      // One writer for the whole bar. Called per column during a drag with
      // `preview`, and once at the end with `preview` false -- so a drag across
      // 12 hops is ONE undo step and ONE ref_plan write, not twelve.
      const writeHops = (hopList, preview) => {
        const cur = hopList.slice().sort((a, b) => a - b);
        r.shots = cur.length ? cur : null;
        if (preview) { paintBar(); return; }
        commit();
        render();
      };
      const paintBar = () => {
        bar.textContent = "";
        for (let h = 1; h <= hops; h += 1) {
          const cell = el("span", "h3e-hopcell" + (isOn(h) ? " h3e-hopcell-on" : ""));
          cell.style.width = `${geo.colW}px`;
          cell.dataset.hop = String(h);
          cell.appendChild(el("span", "h3e-hopcell-no", String(h)));
          bar.appendChild(cell);
        }
      };
      paintBar();

      // Toggle from the CURRENT state, ignoring what is in between: a drag is
      // "set these hops ON", not "flip every hop I passed over", so dragging
      // back over a hop you already had leaves it on.
      let dragFrom = null;
      const cellsAt = (e) => {
        const rect = bar.getBoundingClientRect?.();
        if (rect && rect.width > 0) {
          const hit = e.target?.closest?.("[data-hop]");
          if (hit && dragFrom == null) {
            const dh = Number(hit.dataset?.hop);
            if (dh >= 1 && dh <= hops) return dh;
          }
          const relX = ((e.clientX ?? 0) - rect.left) * (geo.width / rect.width);
          const idx = columnAt(geo, relX, bar.scrollLeft || 0);
          return idx < 0 ? -1 : idx + 1;
        }
        const i = columnAt(geo, e.clientX ?? 0, 0);
        return i < 0 ? -1 : i + 1;
      };
      bar.addEventListener("pointerdown", (e) => {
        const h = cellsAt(e);
        if (h < 1) return;
        dragFrom = h;
        bar.setPointerCapture?.(e.pointerId);
        // The first cell FLIPS (that is a click, and a click must toggle). The
        // rest of the drag only ever adds.
        const cur = Array.isArray(r.shots) ? r.shots.slice() : [];
        const at = cur.indexOf(h);
        if (at >= 0) cur.splice(at, 1); else cur.push(h);
        writeHops(cur, true);
      });
      bar.addEventListener("pointermove", (e) => {
        if (dragFrom == null) return;
        const h = cellsAt(e);
        if (h < 1) return;
        const lo = Math.min(dragFrom, h);
        const hi = Math.max(dragFrom, h);
        const cur = Array.isArray(r.shots) ? r.shots.slice() : [];
        for (let k = lo; k <= hi; k++) if (!cur.includes(k)) cur.push(k);
        writeHops(cur, true);
      });
      const endDrag = (e) => {
        if (dragFrom == null) return;
        try { bar.releasePointerCapture?.(e.pointerId); } catch (_) { /* not captured */ }
        dragFrom = null;
        writeHops(Array.isArray(r.shots) ? r.shots : [], false);
      };
      bar.addEventListener("pointerup", endDrag);
      bar.addEventListener("pointercancel", endDrag);
      hopbar.appendChild(bar);
            if (!Array.isArray(r.shots) || !r.shots.length) {
                const note = el("span", "h3e-chips-label", "— unscheduled: hop 1 only");
                note.title = "With no hops selected this still stays off hop 2+ of a `next` chain, "
                    + "so the motion pin carries continuity instead of the photograph.";
                hopbar.appendChild(note);
            }
            row.appendChild(hopbar);

            /* The voice's trim, under the row, for whichever recording will
             * actually ride: the row's own, or the RefMod's. Core encodes a
             * voice whole, and a 26 s take behind a 4 s exchange was recited
             * into the frames the lines left over (2026-09-26). A window set
             * here outranks the mod's own; both at 0 falls back to it. */
            const modVoice = r.source === "refmod" && r.file && !r.voice
                ? refmodVoice(r.file) : null;
            const voiceFile = r.voice || modVoice?.file || "";
            if (voiceFile) {
                const trimRow = el("div", "h3e-trimrow h3e-ref-trim");
                trimRow.appendChild(el("span", "h3e-media-label",
                    modVoice ? "voice (from the RefMod)" : "voice"));
                const ownWindow = () => Boolean(r.voice_start || r.voice_end);
                const bar = createTrimBar({
                    kind: "audio",
                    name: () => voiceFile,
                    get: () => (ownWindow() || !modVoice
                        ? { start: r.voice_start || 0, end: r.voice_end || 0 }
                        : { start: modVoice.start || 0, end: modVoice.end || 0 }),
                    set: (a, b) => {
                        r.voice_start = a || 0;
                        r.voice_end = b || 0;
                        setPlan(plan);
                    },
                    onChange: () => queueMicrotask(() => commit()),
                });
                trimBars.push(bar);
                trimRow.appendChild(bar.root);
                row.appendChild(trimRow);
            } else if (r.source === "refmod" && r.file && _refmods === null) {
                // The listing that says whether this mod has a voice is not
                // in yet; draw again once it is.
                refmodRows().then(() => render());
            } else if (r.source === "refmod" && r.file && refmodRowMeta(r.file)?.has_audio_latent) {
                const aNote = el("div", "h3e-trimrow h3e-ref-trim");
                aNote.appendChild(el("span", "h3e-media-label", "audio: pre-encoded inside RefMod (zero re-encode)"));
                row.appendChild(aNote);
            }

            if (r.source === "refmod" && openDrawerKey === rowKey) {
                const drawer = el("div", "h3e-refmod-drawer");
                renderRefmodDrawer(drawer, r, plan);
                row.appendChild(drawer);
            }

            list.appendChild(row);
            if (bad) {
                const note = el("div", "h3e-note h3e-note-error", bad);
                list.appendChild(note);
            }
            if (r.subject != null) bySubject.set(r.subject, true);
        }

        for (const num of [...bySubject.keys()].sort((a, b) => a - b)) {
            list.appendChild(renderSubject(num));
        }
        for (const num of orphans) {
            const warn = el("div", "h3e-note",
                `Subject ${num} has continuity text but no ref claims it. Give a ref that subject number, or clear the text — the run will refuse otherwise.`);
            list.appendChild(warn);
        }
    }

    /* D3: the score strip's under-band needs to know WHICH plate rides each hop,
   and this module already holds `getPlan` -- the same reader the entry uses.
   Exposed so the strip can ask without a second reader for ref_plan. */
  return { root, render, getPlan };
}
