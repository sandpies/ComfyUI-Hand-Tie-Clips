/**
 * The RefMod builder's panel: sources on the left, dials on the right.
 *
 * `mod_plan` is the only source of truth for what goes into the mod, exactly
 * as `shot_plan` / `ref_plan` are for the chain node. The panel reads that
 * widget and writes straight back, so a builder configured here and one typed
 * by hand are the same file.
 *
 * The stills list is repeatable rather than a fixed set of slots. Fixed slots
 * are why the other packs ship a second node whose whole job is toggling
 * inputs on and off: a socket cannot be empty gracefully, and a gap in a dense
 * numbering renames everything after it -- the ordinal instability `refs.py`
 * exists to prevent. A list has no gaps to express.
 *
 * Dials are drawn with `run_panel`'s own `fieldFor`, not a second copy of it,
 * so they keep reading `widgetType()` / `widgetOptions()` and keep their
 * tooltips from `INPUT_TYPES`.
 */
import {
    el, button, widgetByName, widgetType, tooltipFor, isolateEvents,
} from "./widget_utils.js";
import { fieldFor, labelFor } from "./run_panel.js";
import { createPicker, onFilesChanged, extKind } from "./media_picker.js";
import { createTrimBar } from "./trim_bar.js";

const ESTIMATE_URL = "/h3_ref_chain/refmod_estimate";
const PLAN_URL = "/h3_ref_chain/refmod_plan";
const FILES_URL = "/h3_ref_chain/files?folder=refmods";
const INSPECT_URL = "/h3_ref_chain/refmod_inspect";
const UPDATE_URL = "/h3_ref_chain/refmod_update";
const THUMB_URL = "/h3_ref_chain/refmod_thumb";
const PREVIEW_MASK_URL = "/h3_ref_chain/refmod_preview_mask";

/** Dials the panel draws, so the mount hides exactly these. */
const DIALS = [
    "name", "subfolder", "layout", "role", "default_step_curve",
    "subject_mask", "background_mode", "background_retention",
    "fit_mode", "crop_margin", "max_tokens", "description", "save", "build",
];

export const BUILDER_WIDGETS = ["mod_plan"].concat(DIALS);

function cleanDesc(text) {
    const s = String(text ?? "").trim();
    return (s === "0" || s === "none" || s === "None" || s === "null") ? "" : s;
}

function parseModPlan(text) {
    const raw = String(text || "").trim();
    if (!raw) return { stills: [], clip: null, voice: "", voiceStart: 0, voiceEnd: 0 };
    let data;
    try {
        data = JSON.parse(raw);
    } catch (err) {
        return null;
    }
    if (Array.isArray(data)) data = { stills: data };
    if (!data || typeof data !== "object") return null;
    const stills = (Array.isArray(data.stills) ? data.stills : [])
        .map((s) => (typeof s === "string" ? s : String(s?.file || s?.name || "")))
        .filter(Boolean);
    let clip = null;
    const c = data.clip;
    if (c) {
        const file = typeof c === "string" ? c : String(c.file || c.name || "");
        if (file) {
            clip = {
                file,
                start: Number(c.start) || 0,
                end: Number(c.end) || 0,
                frames: Number(c.frames) || 0,
            };
        }
    }
    // A bare name, or `{file, start, end}` once it is trimmed (refmod.voice_window).
    const v = data.voice;
    let voice = typeof v === "string" ? v : String(v?.file || v?.name || "");
    const voiceStart = (v && typeof v === "object") ? Number(v.start) || 0 : 0;
    const voiceEnd = (v && typeof v === "object") ? Number(v.end) || 0 : 0;
    // A sound file in the clip slot is what a voice looked like before
    // this slot existed. Move it rather than dead-ending on the parser,
    // which now refuses it: the author's intent is not in doubt.
    if (clip && extKind(clip.file) === "audio") {
        if (!voice) voice = clip.file;
        clip = null;
        console.log("[HandTieClips] moved a sound file from the RefMod clip"
                    + " slot to its voice slot");
    }
    return { stills, clip, voice, voiceStart, voiceEnd };
}

function modPlanToJson(plan) {
    if (!plan.stills.length && !plan.clip && !plan.voice) return "";
    const out = {};
    if (plan.stills.length) out.stills = plan.stills.map((f) => ({ file: f }));
    if (plan.clip) {
        const c = { file: plan.clip.file };
        if (plan.clip.start) c.start = Math.round(plan.clip.start * 1000) / 1000;
        if (plan.clip.end) c.end = Math.round(plan.clip.end * 1000) / 1000;
        if (plan.clip.frames) c.frames = plan.clip.frames;
        out.clip = c;
    }
    // Omitted when empty, so a mod_plan written before the voice
    // slot existed round-trips through the panel byte for byte.
    if (plan.voice) {
        // The object form only when trimmed, for the same byte-for-byte reason.
        if (plan.voiceStart || plan.voiceEnd) {
            const v = { file: plan.voice };
            if (plan.voiceStart) v.start = Math.round(plan.voiceStart * 1000) / 1000;
            if (plan.voiceEnd) v.end = Math.round(plan.voiceEnd * 1000) / 1000;
            out.voice = v;
        } else {
            out.voice = plan.voice;
        }
    }
    return JSON.stringify(out, null, 2);
}

export function createModBuilder(node, { onChange } = {}) {
    const root = el("div", "h3e-root h3e-mod");
    isolateEvents(root);

    const planWidget = widgetByName(node, "mod_plan");

    // A mod_plan that does not parse is NOT silently replaced with an empty
    // one: the panel would then write "" over it on the next edit and destroy
    // whatever the author was in the middle of repairing.
    let planBad = false;
    const readPlan = () => {
        const parsed = parseModPlan(planWidget?.value);
        planBad = parsed === null;
        return parsed || { stills: [], clip: null, voice: "", voiceStart: 0, voiceEnd: 0 };
    };
    let plan = readPlan();

    const writePlan = () => {
        if (!planWidget) return;
        const text = modPlanToJson(plan);
        planWidget.value = text;
        // Setting `.value` alone leaves anything bound to this widget unaware
        // that it changed -- the same reason the media strip and the run panel
        // both fire the callback rather than assigning.
        try {
            planWidget.callback?.(text, node.graph?.canvas, node, undefined, undefined);
        } catch (err) {
            console.error("[HandTieClips] mod_plan callback failed:", err);
        }
        planBad = false;
        node.graph?.setDirtyCanvas(true, true);
        onChange?.();
        estimate();
    };

    /* -- sources ---------------------------------------------------------- */

    const left = el("div", "h3e-mod-left");

    const stillsSec = el("div", "h3e-section h3e-mod-stills");
    const stillsHead = el("div", "h3e-mod-head");
    stillsHead.appendChild(el("span", "h3e-title", "STILLS"));
    const stillsCount = el("span", "h3e-count");
    stillsHead.appendChild(stillsCount);
    stillsHead.appendChild(button("+ add", "Add another still. Each one becomes a latent frame of the mod.", () => {
        plan.stills.push("");
        writePlan();
        renderStills();
    }));
    stillsSec.appendChild(stillsHead);
    const stillsGrid = el("div", "h3e-mod-grid");
    stillsSec.appendChild(stillsGrid);
    stillsSec.appendChild(el("div", "h3e-note h3e-note-hint",
        "Several views of one character: face, upper body, profile, outfit. "
        + "Order is the order they occupy latent frames."));
    left.appendChild(stillsSec);

    function renderStills() {
        stillsGrid.textContent = "";
        stillsCount.textContent = plan.stills.length
            ? `${plan.stills.length}` : "none yet";
        plan.stills.forEach((name, i) => {
            const cell = el("div", "h3e-mod-cell");
            const pick = createPicker({
                kind: "image",
                title: "Drop a still here, or click to browse.",
                get: () => plan.stills[i] || "",
                set: (v) => { plan.stills[i] = v; },
                onChange: () => { writePlan(); renderStills(); },
            });
            cell.appendChild(pick.root);
            pick.render();
            const bar = el("div", "h3e-mod-cellbar");
            bar.appendChild(button("◀", "Move earlier", () => {
                if (i === 0) return;
                [plan.stills[i - 1], plan.stills[i]] = [plan.stills[i], plan.stills[i - 1]];
                writePlan();
                renderStills();
            }));
            bar.appendChild(el("span", "h3e-count", `${i + 1}`));
            bar.appendChild(button("▶", "Move later", () => {
                if (i >= plan.stills.length - 1) return;
                [plan.stills[i + 1], plan.stills[i]] = [plan.stills[i], plan.stills[i + 1]];
                writePlan();
                renderStills();
            }));
            bar.appendChild(button("remove", "Drop this still from the mod", () => {
                plan.stills.splice(i, 1);
                writePlan();
                renderStills();
            }, "h3e-btn h3e-x"));
            cell.appendChild(bar);
            stillsGrid.appendChild(cell);
        });
        if (!plan.stills.length) {
            stillsGrid.appendChild(el("div", "h3e-note h3e-note-hint",
                "No stills yet. A single face still is the minimum for an identity mod."));
        }
    }

    const clipSec = el("div", "h3e-section h3e-mod-clip");
    const clipHead = el("div", "h3e-mod-head");
    clipHead.appendChild(el("span", "h3e-title", "CLIP"));
    const clipCount = el("span", "h3e-count", "optional");
    clipHead.appendChild(clipCount);
    clipSec.appendChild(clipHead);

    const clipRow = el("div", "h3e-mod-cliprow");
    const clipPick = createPicker({
        kind: "video",
        title: "Drop a clip here. Its frames follow the stills.",
        get: () => plan.clip?.file || "",
        set: (v) => {
            plan.clip = v ? { file: v, start: 0, end: 0, frames: 0 } : null;
        },
        onChange: () => { writePlan(); renderClip(); },
    });
    clipRow.appendChild(clipPick.root);
    clipPick.render();
    const clipTrim = el("div", "h3e-mod-trim");
    clipRow.appendChild(clipTrim);
    clipSec.appendChild(clipRow);
    clipSec.appendChild(el("div", "h3e-note h3e-note-hint",
        "Motion and a range of angles, from one take. Frames are snapped to "
        + "the H3 17k+5 grid; how many latent frames they become is the VAE's call."));
    left.appendChild(clipSec);

    /* The voice. Not encoded into the latent -- a RefMod holds pictures --
     * but recorded in the file, so a reference row citing this mod speaks
     * with it without naming it a second time. That is the difference
     * between a face and a character. */
    const voiceSec = el("div", "h3e-mod-sec");
    const voiceHead = el("div", "h3e-mod-head", "VOICE");
    const voiceCount = el("span", "h3e-count", "optional");
    voiceHead.appendChild(voiceCount);
    voiceSec.appendChild(voiceHead);
    const voicePick = createPicker({
        kind: "audio",
        title: "Drop a voice here. It is stored by name, not encoded.",
        get: () => plan.voice || "",
        set: (v) => {
            // A window belongs to the file it was cut from.
            if ((v || "") !== plan.voice) { plan.voiceStart = 0; plan.voiceEnd = 0; }
            plan.voice = v || "";
        },
        onChange: () => { writePlan(); renderVoice(); },
    });
    voiceSec.appendChild(voicePick.root);
    voicePick.render();
    /* The window a reference row inherits with the voice. Core encodes the
     * whole file, and a hop whose lines run out replays it -- so hand over
     * one clean sentence of timbre, not a script. */
    const voiceBar = createTrimBar({
        kind: "audio",
        name: () => plan.voice || "",
        get: () => ({ start: plan.voiceStart || 0, end: plan.voiceEnd || 0 }),
        set: (a, b) => {
            plan.voiceStart = Number(a) || 0;
            plan.voiceEnd = Number(b) || 0;
        },
        onChange: () => { writePlan(); },
    });
    voiceSec.appendChild(voiceBar.root);
    voiceSec.appendChild(el("div", "h3e-note h3e-note-hint",
        "A timbre reference. It rides the hops the reference row rides, "
        + "hop 2+ only as voice_every_hop allows. The sound file "
        + "stays in h3_refs -- the mod names it, it is not inside it. "
        + "Trim it to one clean sentence: the whole window is encoded."));
    left.appendChild(voiceSec);

    function renderVoice() {
        voiceCount.textContent = plan.voice || "optional";
        voicePick.render();
        voiceBar.render();
    }

    // The live bar, so a repaint can be told to let go of its <video> element.
    let clipBar = null;

    function renderClip() {
        clipBar?.destroy?.();
        clipBar = null;
        clipTrim.textContent = "";
        clipCount.textContent = plan.clip ? plan.clip.file : "optional";
        if (!plan.clip) return;
        clipBar = createTrimBar({
            kind: "video",
            name: () => plan.clip?.file || "",
            get: () => ({ start: plan.clip.start, end: plan.clip.end }),
            set: (s, e) => {
                plan.clip.start = Number(s) || 0;
                plan.clip.end = Number(e) || 0;
            },
            onChange: () => { writePlan(); },
        });
        clipTrim.appendChild(clipBar.root);
        clipBar.render();
    }

    /* -- dials ------------------------------------------------------------ */

    const right = el("div", "h3e-mod-right");
    const dialSec = el("div", "h3e-section h3e-mod-dials");
    const dialHead = el("div", "h3e-mod-head");
    dialHead.appendChild(el("span", "h3e-title", "BUILD & INSPECT"));
    const storedSelect = el("select", "h3e-select");
    storedSelect.title = "Pick an existing RefMod in models/refmods/ to inspect, load sources, or edit header metadata.";
    storedSelect.appendChild(el("option", null, "— existing RefMod —")).value = "";
    storedSelect.addEventListener("change", () => {
        const chosen = storedSelect.value;
        if (!chosen) return;
        const slash = chosen.lastIndexOf("/");
        const nameW = widgetByName(node, "name");
        const subW = widgetByName(node, "subfolder");
        if (slash >= 0) {
            if (subW) { subW.value = chosen.slice(0, slash); subW.callback?.(subW.value, node.graph?.canvas, node); }
            if (nameW) { nameW.value = chosen.slice(slash + 1); nameW.callback?.(nameW.value, node.graph?.canvas, node); }
        } else {
            if (subW) { subW.value = ""; subW.callback?.("", node.graph?.canvas, node); }
            if (nameW) { nameW.value = chosen; nameW.callback?.(nameW.value, node.graph?.canvas, node); }
        }
        renderDials();
        loadStoredPlan({ keepSourcesIfEmpty: true });
    });
    dialHead.appendChild(storedSelect);
    dialSec.appendChild(dialHead);

    const dialGrid = el("div", "h3e-grid");
    dialSec.appendChild(dialGrid);

    const actionBar = el("div", "h3e-mod-actions");
    dialSec.appendChild(actionBar);
    right.appendChild(dialSec);

    function fullModName() {
        const nm = String(widgetByName(node, "name")?.value || "").trim();
        const sub = String(widgetByName(node, "subfolder")?.value || "")
            .trim().replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
        if (!nm) return "";
        return sub ? `${sub}/${nm}` : nm;
    }

    function currentLayout() {
        return String(widgetByName(node, "layout")?.value || "separate_pictures");
    }

    let modFiles = [];
    async function refreshStoredList() {
        try {
            const r = await fetch(FILES_URL);
            const j = await r.json();
            if (!Array.isArray(j.files)) return;
            modFiles = j.files;
            const cur = fullModName();
            storedSelect.textContent = "";
            storedSelect.appendChild(el("option", null, "— existing RefMod —")).value = "";
            for (const f of modFiles) {
                const badge = f.format ? ` [${f.format}${f.members_count > 1 ? ` · ${f.members_count}m` : ""}]` : "";
                const o = el("option", null, `${f.name}${badge}`);
                o.value = f.name;
                storedSelect.appendChild(o);
            }
            if (cur && modFiles.some((f) => f.name === cur)) {
                storedSelect.value = cur;
            }
        } catch (_) { /* server offline during headless mount */ }
    }

    const owned = [];
    const readers = [];

    function renderDials() {
        dialGrid.textContent = "";
        actionBar.textContent = "";
        owned.length = 0;
        readers.length = 0;
        const rejected = [];
        for (const name of DIALS) {
            const w = widgetByName(node, name);
            if (!w) continue;
            if (name === "description") {
                const cleaned = cleanDesc(w.value);
                if (cleaned !== String(w.value ?? "").trim()) w.value = cleaned;
            }
            const f = fieldFor(node, w, () => {
                paintSummary();
                onChange?.();
                if (name === "layout") estimate();
            });
            if (!f) {
                rejected.push(`${name}:${widgetType(w) || "?"}`);
                continue;
            }
            const l = el("label", "h3e-field");
            l.appendChild(el("span", null, labelFor(w)));
            l.appendChild(f.input);
            const tip = tooltipFor(node, w);
            if (tip) { l.title = tip; f.input.title = tip; }
            dialGrid.appendChild(l);
            owned.push(name);
            if (f.read) readers.push(f.read);
        }
        if (rejected.length) {
            console.warn("[HandTieClips] RefMod dials left native:", rejected.join(", "));
        }
        actionBar.appendChild(button("load sources",
            "Read back the stills, clip, voice, and header metadata stored in this RefMod.",
            () => loadStoredPlan()));
        actionBar.appendChild(button("preview mask",
            "Run subject mask isolation on the first still so you can inspect the cutout before building.",
            () => previewFirstMask()));
        actionBar.appendChild(button("save header only",
            "Update description, role, default step curve, and voice metadata inside the existing .safetensors file without re-encoding.",
            () => saveHeaderOnly()));
    }

    /* -- summary + mask preview + stored mod inspector -------------------- */

    const summary = el("div", "h3e-note h3e-mod-summary");
    right.appendChild(summary);

    const maskPreviewBox = el("div", "h3e-section h3e-mod-maskbox");
    maskPreviewBox.hidden = true;
    const maskHead = el("div", "h3e-mod-head");
    const maskTitle = el("span", "h3e-title", "MASK PREVIEW");
    maskHead.appendChild(maskTitle);
    maskHead.appendChild(button("×", "Hide mask preview", () => {
        maskPreviewBox.hidden = true;
    }, "h3e-btn h3e-x"));
    const maskImg = el("img", "h3e-mod-maskimg");
    maskImg.alt = "Subject mask preview";
    const maskNote = el("div", "h3e-note h3e-note-hint");
    maskPreviewBox.append(maskHead, maskImg, maskNote);
    right.appendChild(maskPreviewBox);

    const modInspector = el("div", "h3e-section h3e-mod-inspector");
    modInspector.hidden = true;
    right.appendChild(modInspector);

    let maskObjUrl = "";
    let lastInspected = null;

    function renderInspector(info) {
        lastInspected = info || null;
        modInspector.textContent = "";
        if (!info) {
            modInspector.hidden = true;
            return;
        }
        modInspector.hidden = false;
        const head = el("div", "h3e-mod-head");
        head.appendChild(el("span", "h3e-title", `STORED: ${info.name}`));
        const badges = el("div", "h3e-mod-badges");
        badges.appendChild(el("span", "h3e-count", `${info.format || "v4"} · ${info.role || "generic"} · ${info.tokens || 0} tok`));
        head.appendChild(badges);
        modInspector.appendChild(head);

        const card = el("div", "h3e-mod-card");
        if (info.has_looks) {
            const thumb = el("img", "h3e-mod-thumb");
            thumb.src = `${THUMB_URL}?name=${encodeURIComponent(info.name)}&member=0&w=160&t=${Date.now()}`;
            thumb.alt = info.name;
            thumb.addEventListener("error", () => { thumb.style.display = "none"; });
            card.appendChild(thumb);
        }
        const details = el("div", "h3e-mod-members");
        const metaLine = [
            `curve: ${info.default_step_curve || "full"}`,
            info.has_audio_latent ? "audio latent embedded" : (info.voice?.file ? `voice: ${info.voice.file}` : "no voice"),
            info.description ? `"${info.description}"` : "(empty description)",
        ].join(" · ");
        details.appendChild(el("div", "h3e-note h3e-note-hint", metaLine));

        const members = Array.isArray(info.members) ? info.members : [];
        if (members.length > 0) {
            const rowWrap = el("div", "h3e-mod-members");
            for (const m of members) {
                const chip = el("div", "h3e-mod-mchip");
                const shapeStr = m.kind === "audio"
                    ? `${m.tokens || 0} tok`
                    : `${(m.shape?.[2] || 0) * 16}×${(m.shape?.[1] || 0) * 16} (${m.tokens || 0} tok)`;
                chip.appendChild(el("span", null, `#${m.index + 1} ${m.kind} ${shapeStr}`));
                if (members.length > 1 && info.kind === "bundle") {
                    chip.appendChild(button("×", "Remove this member from the v5 bundle (header+tensor rewrite, no re-encode)", async () => {
                        try {
                            const r = await fetch(UPDATE_URL, {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    name: info.name,
                                    action: "remove_member",
                                    member_idx: m.index,
                                }),
                            });
                            const j = await r.json();
                            if (!r.ok || !j.ok) {
                                setSummary("error", j.error || "member removal failed");
                                return;
                            }
                            renderInspector(j.inspect);
                            refreshStoredList();
                            if (typeof window !== "undefined") {
                                window.dispatchEvent?.(new CustomEvent("htc:refmods-changed"));
                            }
                            setSummary("hint", `Removed member #${m.index + 1} from ${info.name}.`);
                        } catch (err) {
                            setSummary("error", String(err));
                        }
                    }, "h3e-btn h3e-x"));
                }
                rowWrap.appendChild(chip);
            }
            details.appendChild(rowWrap);
        }
        card.appendChild(details);
        modInspector.appendChild(card);
    }

    async function previewFirstMask() {
        const firstStill = plan.stills.find((s) => Boolean(s));
        if (!firstStill) {
            setSummary("error", "Add a still first to preview subject masking.");
            return;
        }
        const subjMaskRaw = String(widgetByName(node, "subject_mask")?.value || "off");
        const useBackend = subjMaskRaw === "off" ? "auto_rembg" : subjMaskRaw;
        const ret = Number(widgetByName(node, "background_retention")?.value || 0);
        const bgMode = String(widgetByName(node, "background_mode")?.value || "blur_bg");
        const margin = Number(widgetByName(node, "crop_margin")?.value || 0);
        maskPreviewBox.hidden = false;
        maskNote.textContent = `Generating ${useBackend} (${bgMode}) preview for ${firstStill}...`;
        try {
            const res = await fetch(PREVIEW_MASK_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    image: firstStill,
                    subject_mask: useBackend,
                    background_retention: ret,
                    background_mode: bgMode,
                    crop_margin: margin,
                }),
            });
            if (!res.ok) {
                const errJson = await res.json().catch(() => ({}));
                maskNote.textContent = errJson.error || `Mask preview failed (HTTP ${res.status})`;
                return;
            }
            const blob = await res.blob();
            if (maskObjUrl) URL.revokeObjectURL(maskObjUrl);
            maskObjUrl = URL.createObjectURL(blob);
            maskImg.src = maskObjUrl;
            maskNote.textContent = subjMaskRaw === "off"
                ? `Previewed ${useBackend} (${bgMode}). Note: subject_mask dial is currently 'off' — set it to ${useBackend} to apply when building.`
                : `Previewing ${useBackend} · ${bgMode} · retention ${ret.toFixed(2)}` + (margin > 0 ? ` · crop ${margin.toFixed(2)}x` : "");
        } catch (err) {
            maskNote.textContent = `Mask preview failed: ${err}`;
        }
    }

    async function saveHeaderOnly() {
        const name = fullModName();
        if (!name) { setSummary("error", "Name a mod first."); return; }
        const desc = cleanDesc(widgetByName(node, "description")?.value || "");
        const role = String(widgetByName(node, "role")?.value || "identity");
        const sc = String(widgetByName(node, "default_step_curve")?.value || "full");
        try {
            const res = await fetch(UPDATE_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name,
                    action: "meta",
                    description: desc,
                    role,
                    default_step_curve: sc,
                    voice: plan.voice || "",
                    voice_start: plan.voiceStart || 0,
                    voice_end: plan.voiceEnd || 0,
                }),
            });
            const data = await res.json();
            if (!res.ok || !data.ok) {
                setSummary("error", data.error || "header update failed");
                return;
            }
            renderInspector(data.inspect);
            refreshStoredList();
            if (typeof window !== "undefined") {
                window.dispatchEvent?.(new CustomEvent("htc:refmods-changed"));
            }
            setSummary("hint", `Saved header metadata for ${name} (no VAE re-encode).`);
        } catch (err) {
            setSummary("error", `Header save failed: ${err}`);
        }
    }

    async function loadStoredPlan({ keepSourcesIfEmpty = false } = {}) {
        const name = fullModName();
        if (!name) { setSummary("error", "Name a mod first."); return; }
        try {
            const res = await fetch(PLAN_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name }),
            });
            const data = await res.json();
            if (!data.ok) { setSummary("error", data.error || "read failed"); return; }
            const stored = data.plan || {};
            const stills = Array.isArray(stored.stills) ? stored.stills : [];
            const inspect = data.inspect || null;
            renderInspector(inspect);

            const cap = widgetByName(node, "description");
            const descText = cleanDesc(data.description || inspect?.description || "");
            if (cap && descText && !cleanDesc(cap.value)) {
                cap.value = descText;
                cap.callback?.(cap.value, node.graph?.canvas, node);
            }
            if (inspect?.role) {
                const rw = widgetByName(node, "role");
                if (rw) { rw.value = inspect.role; rw.callback?.(rw.value, node.graph?.canvas, node); }
            }
            if (inspect?.default_step_curve) {
                const sw = widgetByName(node, "default_step_curve");
                if (sw) { sw.value = inspect.default_step_curve; sw.callback?.(sw.value, node.graph?.canvas, node); }
            }
            renderDials();

            if (!stills.length && !stored.clip && !stored.voice) {
                if (!keepSourcesIfEmpty) {
                    setSummary("hint", `${name} carries no source list.`);
                }
                return;
            }
            plan.stills = stills.slice();
            plan.clip = stored.clip ? { ...stored.clip } : null;
            plan.voice = stored.voice || "";
            plan.voiceStart = Number(stored.voice_start) || 0;
            plan.voiceEnd = Number(stored.voice_end) || 0;
            writePlan();
            renderStills();
            renderClip();
            renderVoice();
        } catch (err) {
            console.warn("[HandTieClips] RefMod plan read failed:", err);
            setSummary("error", "could not reach the server");
        }
    }

    let est = null;
    let estSeq = 0;

    function estimate() {
        const seq = ++estSeq;
        if (!plan.stills.filter(Boolean).length && !plan.clip) {
            est = null;
            paintSummary();
            return;
        }
        fetch(ESTIMATE_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                stills: plan.stills.filter(Boolean),
                clip: plan.clip,
                voice: plan.voice || "",
                layout: currentLayout(),
            }),
        })
            .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
            .then((j) => {
                // A slow answer to a plan the user has already changed must not
                // overwrite the fresh one.
                if (seq !== estSeq) return;
                est = j && j.ok ? j : null;
                paintSummary(j && !j.ok ? j.error : "");
            })
            .catch((err) => {
                if (seq !== estSeq) return;
                est = null;
                paintSummary();
                console.warn("[HandTieClips] RefMod estimate unavailable:", err);
            });
    }

    // hint / warn / error are three different notes and the stylesheet keys
    // them off a modifier on the note itself, not on anything inside it.
    function setSummary(level, text) {
        summary.className = "h3e-note h3e-mod-summary"
            + (level ? ` h3e-note-${level}` : "");
        summary.textContent = text;
    }

    function paintSummary(error) {
        if (planBad) {
            setSummary("error",
                "mod_plan is not valid JSON. It is left exactly as written; "
                + "fix it in the widget and the panel will pick it up.");
            return;
        }
        if (error) {
            setSummary("error", String(error));
            return;
        }
        const nStills = plan.stills.filter(Boolean).length;
        if (!nStills && !plan.clip) {
            setSummary("hint",
                "Add a still to begin. Build writes models/refmods/<name>.safetensors; "
                + "put that name in a reference row's file field.");
            return;
        }
        const bits = [];
        if (nStills) bits.push(`${nStills} still${nStills === 1 ? "" : "s"}`);
        if (est?.clip_frames) bits.push(`${est.clip_frames}f clip`);
        else if (plan.clip) bits.push("clip");
        let line = bits.join(" + ");
        const lay = est?.layout || currentLayout();
        if (est?.canvas) {
            if (lay === "separate_pictures" && nStills > 0 && !plan.clip) {
                line += ` → v5 native-aspect bundle (${est.still_tokens} tokens total)`;
            } else {
                line += ` → ${est.canvas[0]}×${est.canvas[1]} canvas, `
                    + `${est.per_frame_tokens} tokens a frame`;
                if (nStills && !plan.clip) {
                    line += `, ${est.still_tokens} total`;
                }
            }
        }
        if (plan.voice) {
            line += `, voice ${plan.voice}`;
        }
        if (est?.clip_dropped) {
            line += ` — ${est.clip_dropped} frame(s) trimmed by the 17k+5 snap.`;
        }
        // The server phrases these: a name can be absent, the wrong kind,
        // or unreadable, and "not in h3_refs" was wrong for two of the three.
        if (est?.problems?.length) {
            setSummary("error", `${line} — ${est.problems.join("; ")}`);
            return;
        }
        setSummary("hint", line);
    }

    root.appendChild(left);
    root.appendChild(right);

    const stopFiles = onFilesChanged(
        () => { renderStills(); renderClip(); renderVoice(); refreshStoredList(); });
    const onRefmodsEvt = () => {
        refreshStoredList();
        if (lastInspected?.name) {
            fetch(`${INSPECT_URL}?name=${encodeURIComponent(lastInspected.name)}`)
                .then((r) => (r.ok ? r.json() : null))
                .then((j) => { if (j?.ok) renderInspector(j); })
                .catch(() => {});
        }
    };
    if (typeof window !== "undefined") {
        window.addEventListener?.("htc:refmods-changed", onRefmodsEvt);
    }

    function refresh() {
        plan = readPlan();
        renderStills();
        renderClip();
        renderVoice();
        renderDials();
        refreshStoredList();
        estimate();
    }

    refresh();

    return {
        root,
        refresh,
        /** Widget names the panel drew, so the mount hides exactly those. */
        ownedNames: () => ["mod_plan"].concat(owned),
        dispose: () => {
            stopFiles?.();
            if (typeof window !== "undefined") {
                window.removeEventListener?.("htc:refmods-changed", onRefmodsEvt);
            }
            if (maskObjUrl) {
                URL.revokeObjectURL(maskObjUrl);
                maskObjUrl = "";
            }
            clipBar?.destroy?.();
            voiceBar.destroy();
        },
    };
}
