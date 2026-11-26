/**
 * In-node RefMod Workbench & Qwen/Viggle Sheet Extractor (R2 `RefMod` tab).
 *
 * Replaces the separate standalone HTCRefModBuilder workflow by putting:
 *   1. Qwen 2.1 + Viggle / RedQW2.1 / H3-Image Single-Shot Sheet Extractor — pull a clean
 *      single angle (front portrait, 3/4, full body, side profile, back, close-up, outfit)
 *      out of any character turnaround sheet and feed it straight into the RefMod stills.
 *   2. Multi-still v5 native-aspect bundle builder (or stacked_video), optional clip + audio
 *      timbre trim (pre-encoded into [1,32,2,T] audio latent when H3 Audio VAE is present),
 *      subject isolation (auto_rembg / auto_sam + blur_bg / pull_push / neutral_gray + crop),
 *      live mask preview, token estimator, and one-click auto-attach to the Refs rail.
 *   3. Stored RefMod Inspector & Header-Only Editor (description, role, default step curve,
 *      per-member removal on v5 bundles without VAE re-encode).
 */

import { el, button } from "../editor/widget_utils.js";
import { createPicker, onFilesChanged } from "../editor/media_picker.js";
import { createTrimBar } from "../editor/trim_bar.js";
import { IMAGE_MP_STOPS, previewImageDims, runForgeGraph, unloadWriterForGpu, viewUrl } from "../editor/forge_queue.js";
import { readRefs, writeRefs } from "./r2_store.js";
import { invalidateRefmods } from "../editor/ref_rail.js";
import { createSheetMaker } from "./sheet_stitch.js";

const PROP_KEY = "h3_refmod_studio";
const FILES_URL = "/h3_ref_chain/files?folder=refmods";
const ESTIMATE_URL = "/h3_ref_chain/refmod_estimate";
const PLAN_URL = "/h3_ref_chain/refmod_plan";
const INSPECT_URL = "/h3_ref_chain/refmod_inspect";
const UPDATE_URL = "/h3_ref_chain/refmod_update";
const THUMB_URL = "/h3_ref_chain/refmod_thumb";
const PREVIEW_MASK_URL = "/h3_ref_chain/refmod_preview_mask";
const CAPTION_URL = "/h3_ref_chain/refmod_caption";
const REFBANK_URL = "/h3_ref_chain/sandtie/ref_bank";
const CAPS_URL = "/h3_ref_chain/mv/capabilities";

const ROLES = [
    "identity", "wardrobe", "bodyshape", "helper",
    "pose_motion", "background", "style", "generic",
];
const STEP_CURVES = [
    ["full", "full (1.0 every step)"],
    ["early_lock", "early_lock (strong 0-40%, fades)"],
    ["late_detail", "late_detail (low early, 1.0 late)"],
    ["fade", "fade (smooth decay 1 -> 0)"],
    ["mid_peak", "mid_peak (peaks 25-75%)"],
];
const MASK_MODES = [
    ["off", "off (keep full image)"],
    ["auto_rembg", "auto_rembg (fast U2Net cutout)"],
    ["auto_sam", "auto_sam (SAM ViT-B cutout)"],
    ["auto", "auto (rembg fallback)"],
];
const BG_MODES = [
    ["blur_bg", "blur_bg (halo-free soft bokeh)"],
    ["pull_push", "pull_push (color bleed fill)"],
    ["neutral_gray", "neutral_gray (flat 50% gray)"],
];
const FIT_MODES = [
    ["crop", "crop (aspect-safe center crop)"],
    ["pad", "pad (aspect-safe letterbox)"],
    ["stretch", "stretch (fill canvas)"],
];

const EXTRACT_PRESETS = [
    {
        id: "front_portrait",
        label: "Front Portrait",
        aspect: "3:4",
        prompt: "Using the exact character, face, hair, and outfit in <image1>, render a single clean chest-up front portrait facing camera, neutral relaxed expression, plain neutral mid-gray studio backdrop, soft even studio lighting, single unified photograph.",
    },
    {
        id: "three_quarter",
        label: "3/4 Medium",
        aspect: "3:4",
        prompt: "Using the exact character, face, hair, and outfit in <image1>, render a single clean waist-up three-quarter view photograph, natural relaxed posture angled slightly sideways, plain neutral mid-gray studio backdrop, soft even lighting.",
    },
    {
        id: "full_body",
        label: "Full Body",
        aspect: "3:4",
        prompt: "Using the exact character, outfit, proportions, and footwear from <image1>, render one clean full-body standing front-facing photograph, head to toe completely visible, plain neutral mid-gray studio backdrop, even studio lighting.",
    },
    {
        id: "side_profile",
        label: "Side Profile",
        aspect: "3:4",
        prompt: "Using the exact character, hairstyle, and outfit from <image1>, render a single clean side profile portrait looking right, crisp facial silhouette and hair details, plain neutral mid-gray studio backdrop, even studio lighting.",
    },
    {
        id: "back_view",
        label: "Back View",
        aspect: "3:4",
        prompt: "Using the exact character, hairstyle, and back-of-outfit details from <image1>, render a single clean rear-view standing photograph showing the back of head, hair, and outfit, plain neutral mid-gray studio backdrop, even studio lighting.",
    },
    {
        id: "closeup_face",
        label: "Close-Up Face",
        aspect: "1:1",
        prompt: "Using the exact facial features, eyes, eyebrows, makeup, and hair framing of the character in <image1>, render a tight head-and-shoulders close-up portrait facing camera, crisp skin and eye texture, plain neutral mid-gray studio backdrop, even lighting.",
    },
    {
        id: "outfit_prop",
        label: "Outfit / Prop",
        aspect: "1:1",
        prompt: "Isolate the exact outfit or key prop shown in <image1>, centered neatly on an invisible mannequin or clean studio tabletop, plain neutral mid-gray backdrop, soft even studio lighting.",
    },
];

function cleanDesc(text) {
    const s = String(text ?? "").trim();
    return (s === "0" || s === "none" || s === "None" || s === "null") ? "" : s;
}

function slugOf(text, fallback = "hero") {
    const s = String(text || "").trim().toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_|_$/g, "");
    return s || fallback;
}

function defaultState() {
    return {
        name: "hero",
        subfolder: "",
        layout: "separate_pictures",
        role: "identity",
        default_step_curve: "full",
        subject_mask: "auto_rembg",
        background_mode: "blur_bg",
        background_retention: 0,
        fit_mode: "crop",
        crop_margin: 0,
        max_tokens: 0,
        description: "",
        stills: [],
        clip: null,
        voice: "",
        voiceStart: 0,
        voiceEnd: 0,
        auto_attach: true,
        auto_caption: true,
        attach_tag: "",
        attach_subject: "1",
        ext_sheet: "",
        ext_ref2: "",
        ext_profile: "qwen_viggle_6step",
        ext_aspect: "3:4",
        ext_mp: "0",
        ext_prompt: EXTRACT_PRESETS[0].prompt,
        ext_seed: 0,
        ext_preview: null,
        ext_kept_file: "",
        ext_preset: "front_portrait",
        ext_mode: "extract",
        sheet: {},
    };
}

export function createRefModPane(node, { onChange } = {}) {
    const root = el("div", "r2-rm");

    function loadState() {
        node.properties ??= {};
        const raw = node.properties[PROP_KEY];
        const base = defaultState();
        if (raw && typeof raw === "object") {
            Object.assign(base, raw);
            if (!Array.isArray(base.stills)) base.stills = [];
            if (!base.sheet || typeof base.sheet !== "object") base.sheet = {};
            base.description = cleanDesc(base.description);
        }
        return base;
    }

    const state = loadState();
    let userTouched = false;
    function saveState() {
        userTouched = true;
        node.properties ??= {};
        node.properties[PROP_KEY] = JSON.parse(JSON.stringify(state));
    }
    function hydrateFromProps() {
        if (userTouched) return;
        const raw = node.properties?.[PROP_KEY];
        if (raw && typeof raw === "object") {
            const fresh = loadState();
            Object.assign(state, fresh);
        }
    }

    let caps = null;
    let capsLoaded = false;
    let lastProfSig = "";
    let modFiles = [];
    let est = null;
    let estSeq = 0;
    let lastInspected = null;
    let maskObjUrl = "";
    let busyExtract = false;
    let busyBuild = false;
    let extractCounter = 1;

    function fullModName() {
        const nm = String(state.name || "").trim();
        const sub = String(state.subfolder || "").trim().replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
        if (!nm) return "";
        return sub ? `${sub}/${nm}` : nm;
    }

    function setBanner(targetEl, msg, level = "") {
        targetEl.style.display = msg ? "" : "none";
        targetEl.className = "h3e-note" + (level ? ` h3e-note-${level}` : "");
        targetEl.textContent = msg || "";
    }

    /* ====================================================================
     * TOP HEADER BAR: Identity, Library Load, Auto-Attach to Refs
     * ==================================================================== */
    const topBar = el("div", "r2-rm-top");
    topBar.appendChild(el("span", "r2-st-title", "RefMod Studio"));

    const storedSel = el("select", "h3e-select");
    storedSel.title = "Load an existing RefMod from models/refmods/ (or RefLoRA) to inspect, edit header metadata, or rebuild.";
    storedSel.appendChild(el("option", null, "— load existing RefMod —")).value = "";

    const newBtn = button("+ New Blank", "Reset fields for a brand-new RefMod", () => {
        const keepProf = state.ext_profile;
        Object.assign(state, defaultState(), { ext_profile: keepProf });
        saveState();
        syncInputsFromState();
        renderInspector(null);
        maskBox.hidden = true;
        renderAll();
        setBanner(buildStatus, "Ready for a new RefMod.", "hint");
    });

    const refreshBtn = button("↻ Refresh", "Re-scan RefMods on disk and Image Forge profiles", () => {
        fetchCaps();
        refreshStoredList();
        invalidateRefmods(false);
    });

    const freeVramBtn = button("☕ Free LLM VRAM", "Unload the local writer model (nInfer or local server) before Qwen-Viggle or H3 VAE", async () => {
        setBanner(extStatus, "Unloading LLM writer from VRAM...", "hint");
        await unloadWriterForGpu();
        setBanner(extStatus, "Writer unloaded — VRAM ready for Qwen-Viggle & RefMod baking.", "hint");
    });

    topBar.append(storedSel, newBtn, refreshBtn, el("span", "r2-st-spacer"), freeVramBtn);
    root.appendChild(topBar);

    const idRow = el("div", "r2-rm-idbar");
    const nameIn = el("input", "h3e-input");
    nameIn.type = "text";
    nameIn.placeholder = "mod name (e.g. kaede)";
    nameIn.title = "Output filename under models/refmods/<name>.safetensors";
    nameIn.addEventListener("input", () => {
        state.name = nameIn.value;
        saveState();
    });

    const subIn = el("input", "h3e-input");
    subIn.type = "text";
    subIn.placeholder = "subfolder (optional)";
    subIn.title = "Optional folder under models/refmods/";
    subIn.addEventListener("input", () => {
        state.subfolder = subIn.value;
        saveState();
    });

    const roleSel = el("select", "h3e-select");
    roleSel.title = "Semantic concept role stored in header & surfaced in Refs browser filters.";
    for (const r of ROLES) {
        const o = el("option", null, r);
        o.value = r;
        roleSel.appendChild(o);
    }
    roleSel.addEventListener("change", () => {
        state.role = roleSel.value;
        if (state.role === "helper" || state.role === "bodyshape" || state.role === "pose_motion") {
            if (state.default_step_curve === "full") {
                state.default_step_curve = "early_lock";
                curveSel.value = "early_lock";
            }
        }
        saveState();
    });

    const curveSel = el("select", "h3e-select");
    curveSel.title = "Default per-step denoising strength curve when wired in Refs.";
    for (const [val, lbl] of STEP_CURVES) {
        const o = el("option", null, lbl);
        o.value = val;
        curveSel.appendChild(o);
    }
    curveSel.addEventListener("change", () => {
        state.default_step_curve = curveSel.value;
        saveState();
    });

    const attachWrap = el("label", "r2-st-chk");
    const attachChk = el("input");
    attachChk.type = "checkbox";
    attachChk.checked = state.auto_attach !== false;
    attachChk.addEventListener("change", () => {
        state.auto_attach = attachChk.checked;
        saveState();
    });
    attachWrap.append(attachChk, el("span", null, "Attach → Refs"));
    attachWrap.title = "Automatically add or update this RefMod as an @tag row in the Refs rail after baking.";

    const attachTagIn = el("input", "h3e-input r2-rm-tag");
    attachTagIn.type = "text";
    attachTagIn.placeholder = "@tag (auto)";
    attachTagIn.title = "Optional custom @tag name for the Refs rail (blank = uses RefMod name).";
    attachTagIn.addEventListener("input", () => {
        state.attach_tag = attachTagIn.value;
        saveState();
    });

    const attachSubjSel = el("select", "h3e-select");
    attachSubjSel.title = "Subject number when auto-attaching an identity RefMod to Refs.";
    attachSubjSel.appendChild(el("option", null, "No subject")).value = "";
    for (let s = 1; s <= 9; s += 1) {
        const o = el("option", null, `Subject ${s}`);
        o.value = String(s);
        attachSubjSel.appendChild(o);
    }
    attachSubjSel.addEventListener("change", () => {
        state.attach_subject = attachSubjSel.value;
        saveState();
    });

    const mkField = (lbl, ctrl) => {
        const w = el("label", "h3e-field r2-rm-f");
        w.append(el("span", null, lbl), ctrl);
        return w;
    };
    idRow.append(
        mkField("Name", nameIn),
        mkField("Subfolder", subIn),
        mkField("Role", roleSel),
        mkField("Default Curve", curveSel),
        attachWrap,
        attachTagIn,
        attachSubjSel,
    );
    root.appendChild(idRow);

    /* ====================================================================
     * BODY: 2-COLUMN WORKBENCH
     * ==================================================================== */
    const bodyGrid = el("div", "r2-rm-cols");
    const leftCol = el("div", "r2-rm-col");
    const rightCol = el("div", "r2-rm-col");
    bodyGrid.append(leftCol, rightCol);
    root.appendChild(bodyGrid);

    /* -- LEFT 1: Qwen / Viggle Sheet Extractor --------------------------- */
    const extSec = el("details", "h3e-section r2-rm-extractor");
    extSec.open = true;
    const extSum = el("summary", "r2-rm-sum");
    const extSumTitle = el("span", "h3e-title");
    const extSumCount = el("span", "h3e-count");
    extSum.append(extSumTitle, extSumCount);
    extSec.appendChild(extSum);

    /* Mode switch: Sheet -> Single Shot (Qwen extractor) | Shots -> Sheet (stitcher). */
    const modeRow = el("div", "r2-sh-mode");
    const modeBtns = {
        extract: button("✨ Sheet → Single Shot", "Extract one clean angle out of a turnaround sheet (Qwen / Viggle)", () => setExtMode("extract"), "h3e-btn h3e-refmod-chip"),
        sheet: button("▦ Shots → Sheet", "Stitch the Stills below into one high-res character sheet (no model; every still kept whole at its own pixels)", () => setExtMode("sheet"), "h3e-btn h3e-refmod-chip"),
    };
    modeRow.append(modeBtns.extract, modeBtns.sheet);
    extSec.appendChild(modeRow);

    const extBody = el("div", "r2-rm-extbody");
    extSec.appendChild(extBody);

    const sheetMaker = createSheetMaker({
        getFiles: () => state.stills.filter(Boolean),
        getState: () => state.sheet,
        save: () => saveState(),
        getSlug: () => slugOf(state.name || "char", "char"),
        onSaved: (name) => {
            state.ext_sheet = name;
            saveState();
            sheetPick.render();
        },
    });
    const sheetBody = el("div", "r2-rm-extbody");
    sheetBody.appendChild(sheetMaker.root);
    extSec.appendChild(sheetBody);

    function setExtMode(mode) {
        state.ext_mode = mode === "sheet" ? "sheet" : "extract";
        saveState();
        paintExtMode();
    }
    function paintExtMode() {
        const sheet = state.ext_mode === "sheet";
        extBody.style.display = sheet ? "none" : "";
        sheetBody.style.display = sheet ? "" : "none";
        for (const [k, b] of Object.entries(modeBtns)) b.classList.toggle("h3e-refmod-chip-on", k === state.ext_mode);
        extSumTitle.textContent = sheet ? "▦ SHOTS → SHEET STITCHER" : "✨ SHEET → SINGLE SHOT EXTRACTOR (QWEN / VIGGLE)";
        extSumCount.textContent = sheet ? "lay the Stills out as one high-res character sheet" : "pull one clean angle from a turnaround sheet";
        if (sheet) sheetMaker.refresh();
    }

    const extPickRow = el("div", "r2-rm-extpicks");
    const sheetPick = createPicker({
        kind: "image",
        title: "Drop a character reference sheet (or photo) from disk, or choose from input/h3_refs/.",
        get: () => state.ext_sheet || "",
        set: (v) => {
            state.ext_sheet = v || "";
            saveState();
        },
        onChange: () => { sheetPick.render(); },
    });
    const sheetWrap = el("div", "r2-rm-pickcell");
    sheetWrap.append(el("span", "h3e-media-label", "Sheet / Source <image1>"), sheetPick.root);

    const ref2Pick = createPicker({
        kind: "image",
        title: "Optional <image2> outfit, pose, or lighting helper.",
        get: () => state.ext_ref2 || "",
        set: (v) => {
            state.ext_ref2 = v || "";
            saveState();
        },
        onChange: () => { ref2Pick.render(); },
    });
    const ref2Wrap = el("div", "r2-rm-pickcell");
    ref2Wrap.append(el("span", "h3e-media-label", "Optional Ref <image2>"), ref2Pick.root);

    const extPreviewBox = el("div", "r2-rm-extprev");
    const extImg = el("img", "r2-rm-extimg");
    extImg.alt = "Extracted single shot preview";
    extImg.style.display = "none";
    const extEmpty = el("div", "r2-rm-extempty", "Extracted shot appears here");
    extPreviewBox.append(extImg, extEmpty);

    extPickRow.append(sheetWrap, ref2Wrap, extPreviewBox);
    extBody.appendChild(extPickRow);

    const presetRow = el("div", "r2-rm-presets");
    presetRow.appendChild(el("span", "h3e-chips-label", "Extract angle:"));
    const presetBtns = {};
    for (const p of EXTRACT_PRESETS) {
        const pb = button(p.label, p.prompt, () => {
            state.ext_preset = p.id;
            state.ext_aspect = p.aspect;
            state.ext_prompt = p.prompt;
            extAspSel.value = p.aspect;
            extPromptArea.value = p.prompt;
            saveState();
            for (const [k, b] of Object.entries(presetBtns)) {
                b.classList.toggle("h3e-refmod-chip-on", k === p.id);
            }
            syncExtDim();
        }, "h3e-btn h3e-refmod-chip" + (state.ext_preset === p.id ? " h3e-refmod-chip-on" : ""));
        presetBtns[p.id] = pb;
        presetRow.appendChild(pb);
    }
    extBody.appendChild(presetRow);

    const extPromptArea = el("textarea", "r2-st-area");
    extPromptArea.rows = 2;
    extPromptArea.placeholder = "Extraction instruction citing <image1> (and optional <image2>)...";
    extPromptArea.value = state.ext_prompt || EXTRACT_PRESETS[0].prompt;
    extPromptArea.addEventListener("input", () => {
        state.ext_prompt = extPromptArea.value;
        saveState();
    });
    extBody.appendChild(extPromptArea);

    const extCtlRow = el("div", "r2-st-row");
    const extProfSel = el("select", "h3e-select r2-st-grow");
    extProfSel.title = "Image Forge model used to isolate & re-frame the character angle.";
    extProfSel.addEventListener("change", () => {
        state.ext_profile = extProfSel.value;
        saveState();
        syncExtDim();
    });

    const extAspSel = el("select", "h3e-select");
    extAspSel.title = "Target aspect ratio of the extracted shot (3:4 recommended for portraits/full-body; 1:1 for close-ups/props).";
    for (const [val, lbl] of [
        ["3:4", "3:4 Portrait"],
        ["1:1", "1:1 Square"],
        ["9:16", "9:16 Tall"],
        ["4:3", "4:3 Medium"],
        ["16:9", "16:9 Wide"],
        ["match", "Match Sheet"],
    ]) {
        const o = el("option", null, lbl);
        o.value = val;
        extAspSel.appendChild(o);
    }
    extAspSel.value = state.ext_aspect || "3:4";
    extAspSel.addEventListener("change", () => {
        state.ext_aspect = extAspSel.value;
        saveState();
        syncExtDim();
    });

    const extMpSel = el("select", "h3e-select");
    extMpSel.title = "Target megapixel budget (Auto uses 3 MP on RedQW2.1 Unlocked, 4 MP on H3 Image, and 1 MP on fast Turbo models).";
    for (const [val, lbl] of IMAGE_MP_STOPS) {
        const o = el("option", null, lbl);
        o.value = val;
        extMpSel.appendChild(o);
    }
    extMpSel.value = String(state.ext_mp ?? "0");
    extMpSel.addEventListener("change", () => {
        state.ext_mp = extMpSel.value;
        saveState();
        syncExtDim();
    });

    const extDimBadge = el("span", "r2-st-chip r2-st-dim", "");
    function syncExtDim() {
        const profObj = (caps?.image_profiles || []).find((x) => x.id === (extProfSel.value || state.ext_profile)) || null;
        const d = previewImageDims(profObj, extAspSel.value || state.ext_aspect || "3:4", extMpSel.value || state.ext_mp || "0");
        extDimBadge.textContent = d.label;
    }

    const extSeedIn = el("input", "r2-st-num");
    extSeedIn.type = "number";
    extSeedIn.min = "0";
    extSeedIn.value = String(state.ext_seed || 0);
    extSeedIn.title = "Seed (0 = random each run).";
    extSeedIn.addEventListener("change", () => {
        state.ext_seed = Math.max(0, Number(extSeedIn.value) || 0);
        saveState();
    });

    const extractBtn = button("🎨 Extract Shot", "Run the selected Image Forge model to pull this single angle out of <image1> (Ctrl+Enter inside Extractor)", () => runExtractShot(), "h3e-btn h3e-btn-accent");
    const rerollBtn = button("↻ Reroll", "Roll a new random seed and extract again", () => {
        state.ext_seed = 0;
        extSeedIn.value = "0";
        saveState();
        runExtractShot();
    });
    const addStillBtn = button("✓ Keep & Add to Stills", "Import extracted shot into input/h3_refs/ and append it to RefMod Stills below", () => keepExtractedToStills({ alsoBuild: false }));
    const keepBakeBtn = button("⚡ Keep & Bake RefMod", "Import extracted shot into Stills and bake the RefMod immediately", () => keepExtractedToStills({ alsoBuild: true }));
    addStillBtn.disabled = true;
    keepBakeBtn.disabled = true;

    extCtlRow.append(extProfSel, extAspSel, extMpSel, extDimBadge, extSeedIn, extractBtn, rerollBtn, addStillBtn, keepBakeBtn);
    extBody.appendChild(extCtlRow);

    extSec.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation?.();
            runExtractShot();
        }
    });

    const extStatus = el("div", "h3e-note");
    extStatus.style.display = "none";
    extBody.appendChild(extStatus);

    leftCol.appendChild(extSec);

    function paintExtPreview() {
        const hasPrev = Boolean(state.ext_preview?.filename);
        if (hasPrev) {
            extImg.src = viewUrl(state.ext_preview);
            extImg.style.display = "";
            extEmpty.style.display = "none";
        } else if (state.ext_kept_file) {
            extImg.src = `/view?filename=${encodeURIComponent(state.ext_kept_file)}&type=input&subfolder=h3_refs`;
            extImg.style.display = "";
            extEmpty.style.display = "none";
        } else {
            extImg.removeAttribute("src");
            extImg.style.display = "none";
            extEmpty.style.display = "";
        }
        addStillBtn.disabled = !hasPrev;
        keepBakeBtn.disabled = !hasPrev;
    }

    async function runExtractShot() {
        if (busyExtract) return;
        const srcSheet = String(state.ext_sheet || "").trim();
        if (!srcSheet) {
            setBanner(extStatus, "Pick or drop a Sheet / Source image into <image1> first.", "error");
            return;
        }
        const promptText = String(extPromptArea.value || "").trim() || EXTRACT_PRESETS[0].prompt;
        busyExtract = true;
        extractBtn.disabled = true;
        rerollBtn.disabled = true;
        addStillBtn.disabled = true;
        keepBakeBtn.disabled = true;
        setBanner(extStatus, "Queueing Qwen/Viggle extraction...", "hint");
        try {
            const refs = [srcSheet, state.ext_ref2].filter(Boolean);
            const slug = slugOf(state.name || srcSheet.replace(/\.[^.]+$/, ""), "extract");
            const activeProf = extProfSel.value || state.ext_profile || "qwen_viggle_6step";
            const mpVal = Number(extMpSel.value || state.ext_mp || 0) || 0;
            const res = await runForgeGraph({
                kind: "image",
                profile_id: activeProf,
                prompt: promptText,
                ref_files: refs,
                aspect: state.ext_aspect || "3:4",
                megapixels: mpVal,
                seed: Number(state.ext_seed) || 0,
                filename_prefix: `mv_forge/refmod_${slug}`,
            }, {
                onStatus: (m) => setBanner(extStatus, m, "hint"),
                onProgress: (v, max) => setBanner(extStatus, `Extracting shot (${v}/${max})...`, "hint"),
            });
            state.ext_preview = res.file;
            state.ext_seed = res.meta?.seed || 0;
            extSeedIn.value = String(state.ext_seed);
            saveState();
            paintExtPreview();
            setBanner(extStatus, `Shot ready (${res.meta?.width || "?"}×${res.meta?.height || "?"}, ${res.meta?.steps || "?"} steps). Click ✓ Keep & Add to Stills or ⚡ Keep & Bake RefMod.`, "hint");
        } catch (err) {
            setBanner(extStatus, String(err), "error");
        } finally {
            busyExtract = false;
            extractBtn.disabled = false;
            rerollBtn.disabled = false;
            paintExtPreview();
            try { extractBtn.focus?.(); } catch (_) { /* */ }
        }
    }

    async function keepExtractedToStills({ alsoBuild = false } = {}) {
        if (!state.ext_preview?.filename) return;
        addStillBtn.disabled = true;
        keepBakeBtn.disabled = true;
        setBanner(extStatus, "Importing extracted shot into input/h3_refs/...", "hint");
        try {
            const slug = slugOf(state.name || "char", "char");
            const presetSlug = slugOf(state.ext_preset || "shot", "shot");
            const seq = extractCounter++;
            const destName = `${slug}_${presetSlug}_${seq}.png`;
            const res = await fetch("/h3_ref_chain/mv/import_output", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    filename: state.ext_preview.filename,
                    subfolder: state.ext_preview.subfolder || "",
                    output_type: state.ext_preview.type || "output",
                    dest_name: destName,
                    kind: "image",
                    tag: slug,
                    desc: cleanDesc(state.description) || String(state.ext_prompt || "").slice(0, 140),
                    role: state.role === "wardrobe" ? "wardrobe" : (state.role === "helper" ? "prop" : "cast"),
                    register_bible: false,
                }),
            });
            const j = await res.json();
            if (!res.ok || !j.ok) throw new Error(j.error || "Import failed.");
            state.ext_kept_file = j.filename;
            const list = state.stills.filter(Boolean);
            if (!list.includes(j.filename)) list.push(j.filename);
            state.stills = list;
            saveState();
            renderStills();
            estimate();
            setBanner(extStatus, `Added ${j.filename} to RefMod Stills!`, "hint");
            if (alsoBuild) {
                await buildRefMod();
            }
        } catch (err) {
            setBanner(extStatus, String(err), "error");
        } finally {
            paintExtPreview();
        }
    }

    /* -- LEFT 2: RefMod Stills, Clip, Voice ------------------------------- */
    const stillsSec = el("div", "h3e-section h3e-mod-stills");
    const stillsHead = el("div", "h3e-mod-head");
    stillsHead.appendChild(el("span", "h3e-title", "STILLS"));
    const stillsCount = el("span", "h3e-count");
    stillsHead.appendChild(stillsCount);
    stillsHead.appendChild(button("+ add still", "Add another still slot to this RefMod", () => {
        state.stills.push("");
        saveState();
        renderStills();
        estimate();
    }));
    stillsSec.appendChild(stillsHead);
    const stillsGrid = el("div", "h3e-mod-grid");
    stillsSec.appendChild(stillsGrid);
    stillsSec.appendChild(el("div", "h3e-note h3e-note-hint",
        "v5 separate_pictures preserves each still's own natural aspect ratio as an independent <Picture N>. Use the Extractor above to turn multi-panel sheets into clean angles."));
    leftCol.appendChild(stillsSec);

    function renderStills() {
        stillsGrid.textContent = "";
        const filled = state.stills.filter(Boolean).length;
        stillsCount.textContent = filled ? `${filled}` : "none yet";
        state.stills.forEach((name, i) => {
            const cell = el("div", "h3e-mod-cell");
            const pick = createPicker({
                kind: "image",
                title: "Drop a still here, or click to browse input/h3_refs/.",
                get: () => state.stills[i] || "",
                set: (v) => { state.stills[i] = v || ""; },
                onChange: () => { saveState(); renderStills(); estimate(); },
            });
            cell.appendChild(pick.root);
            pick.render();
            const bar = el("div", "h3e-mod-cellbar");
            bar.appendChild(button("◀", "Move earlier", () => {
                if (i === 0) return;
                [state.stills[i - 1], state.stills[i]] = [state.stills[i], state.stills[i - 1]];
                saveState();
                renderStills();
                estimate();
            }));
            bar.appendChild(el("span", "h3e-count", `${i + 1}`));
            bar.appendChild(button("▶", "Move later", () => {
                if (i >= state.stills.length - 1) return;
                [state.stills[i + 1], state.stills[i]] = [state.stills[i], state.stills[i + 1]];
                saveState();
                renderStills();
                estimate();
            }));
            if (name) {
                bar.appendChild(button("✀", "Load this still into Sheet Extractor above", () => {
                    state.ext_sheet = name;
                    saveState();
                    sheetPick.render();
                    extSec.open = true;
                    setBanner(extStatus, `Loaded ${name} into Sheet Extractor <image1>.`, "hint");
                }));
            }
            bar.appendChild(button("×", "Remove this still", () => {
                state.stills.splice(i, 1);
                saveState();
                renderStills();
                estimate();
            }, "h3e-btn h3e-x"));
            cell.appendChild(bar);
            stillsGrid.appendChild(cell);
        });
        if (!state.stills.length) {
            stillsGrid.appendChild(el("div", "h3e-note h3e-note-hint",
                "No stills yet — extract a shot from a sheet above, or click + add still."));
        }
        if (state.ext_mode === "sheet") sheetMaker.refresh();
    }

    const clipVoiceGrid = el("div", "r2-rm-cvgrid");

    const clipSec = el("div", "h3e-section h3e-mod-clip");
    const clipHead = el("div", "h3e-mod-head");
    clipHead.appendChild(el("span", "h3e-title", "CLIP"));
    const clipCount = el("span", "h3e-count", "optional");
    clipHead.appendChild(clipCount);
    clipSec.appendChild(clipHead);
    const clipRow = el("div", "h3e-mod-cliprow");
    const clipPick = createPicker({
        kind: "video",
        title: "Optional motion/angle reference clip (snapped to 17k+5 frames).",
        get: () => state.clip?.file || "",
        set: (v) => {
            state.clip = v ? { file: v, start: 0, end: 0, frames: 0 } : null;
        },
        onChange: () => { saveState(); renderClip(); estimate(); },
    });
    clipRow.appendChild(clipPick.root);
    clipPick.render();
    const clipTrim = el("div", "h3e-mod-trim");
    clipRow.appendChild(clipTrim);
    clipSec.appendChild(clipRow);

    const voiceSec = el("div", "h3e-section h3e-mod-sec");
    const voiceHead = el("div", "h3e-mod-head");
    voiceHead.appendChild(el("span", "h3e-title", "VOICE"));
    const voiceCount = el("span", "h3e-count", "optional");
    voiceHead.appendChild(voiceCount);
    voiceSec.appendChild(voiceHead);
    const voicePick = createPicker({
        kind: "audio",
        title: "Optional voice reference. Auto-encoded into portable [1,32,2,T] audio latent when H3 Audio VAE is present.",
        get: () => state.voice || "",
        set: (v) => {
            if ((v || "") !== state.voice) {
                state.voiceStart = 0;
                state.voiceEnd = 0;
            }
            state.voice = v || "";
        },
        onChange: () => { saveState(); renderVoice(); estimate(); },
    });
    voiceSec.appendChild(voicePick.root);
    voicePick.render();
    const voiceBar = createTrimBar({
        kind: "audio",
        name: () => state.voice || "",
        get: () => ({ start: state.voiceStart || 0, end: state.voiceEnd || 0 }),
        set: (a, b) => {
            state.voiceStart = Number(a) || 0;
            state.voiceEnd = Number(b) || 0;
            saveState();
        },
        onChange: () => { saveState(); },
    });
    voiceSec.appendChild(voiceBar.root);

    clipVoiceGrid.append(clipSec, voiceSec);
    leftCol.appendChild(clipVoiceGrid);

    let clipBar = null;
    function renderClip() {
        clipBar?.destroy?.();
        clipBar = null;
        clipTrim.textContent = "";
        clipCount.textContent = state.clip?.file || "optional";
        clipPick.render();
        if (!state.clip?.file) return;
        clipBar = createTrimBar({
            kind: "video",
            name: () => state.clip?.file || "",
            get: () => ({ start: state.clip.start || 0, end: state.clip.end || 0 }),
            set: (s, e) => {
                state.clip.start = Number(s) || 0;
                state.clip.end = Number(e) || 0;
                saveState();
            },
            onChange: () => { saveState(); estimate(); },
        });
        clipTrim.appendChild(clipBar.root);
        clipBar.render();
    }

    function renderVoice() {
        voiceCount.textContent = state.voice || "optional";
        voicePick.render();
        voiceBar.render();
    }

    /* ====================================================================
     * RIGHT COLUMN: Build Dials, Mask Preview, Bake & Stored Inspector
     * ==================================================================== */
    const dialSec = el("div", "h3e-section h3e-mod-dials");
    const dialHead = el("div", "h3e-mod-head");
    dialHead.appendChild(el("span", "h3e-title", "ENCODE & ISOLATION"));
    const vaeBadge = el("span", "h3e-count", "VAE: checking...");
    dialHead.appendChild(vaeBadge);
    dialSec.appendChild(dialHead);

    const dialGrid = el("div", "h3e-grid");

    const layoutSel = el("select", "h3e-select");
    layoutSel.title = "separate_pictures (v5 bundle): native aspect per still, zero <Video> slot loss. stacked_video: shared canvas concat.";
    for (const [val, lbl] of [
        ["separate_pictures", "separate_pictures (v5 native-aspect)"],
        ["stacked_video", "stacked_video (single canvas)"],
    ]) {
        const o = el("option", null, lbl);
        o.value = val;
        layoutSel.appendChild(o);
    }
    layoutSel.addEventListener("change", () => {
        state.layout = layoutSel.value;
        saveState();
        estimate();
    });

    const maskSel = el("select", "h3e-select");
    maskSel.title = "Subject cutout before encoding. auto_rembg is instant; auto_sam uses SAM ViT-B on GPU.";
    for (const [val, lbl] of MASK_MODES) {
        const o = el("option", null, lbl);
        o.value = val;
        maskSel.appendChild(o);
    }
    maskSel.addEventListener("change", () => {
        state.subject_mask = maskSel.value;
        saveState();
    });

    const bgModeSel = el("select", "h3e-select");
    bgModeSel.title = "How masked background pixels are treated before VAE encoding.";
    for (const [val, lbl] of BG_MODES) {
        const o = el("option", null, lbl);
        o.value = val;
        bgModeSel.appendChild(o);
    }
    bgModeSel.addEventListener("change", () => {
        state.background_mode = bgModeSel.value;
        saveState();
    });

    const retIn = el("input", "h3e-input");
    retIn.type = "number";
    retIn.min = "0";
    retIn.max = "1";
    retIn.step = "0.05";
    retIn.title = "0 removes/blurs masked background completely; 1 keeps the original background.";
    retIn.addEventListener("change", () => {
        state.background_retention = Math.min(1, Math.max(0, Number(retIn.value) || 0));
        retIn.value = String(state.background_retention);
        saveState();
    });

    const fitSel = el("select", "h3e-select");
    fitSel.title = "How images resize onto a canvas (crop preserves natural aspect without distortion).";
    for (const [val, lbl] of FIT_MODES) {
        const o = el("option", null, lbl);
        o.value = val;
        fitSel.appendChild(o);
    }
    fitSel.addEventListener("change", () => {
        state.fit_mode = fitSel.value;
        saveState();
    });

    const cropIn = el("input", "h3e-input");
    cropIn.type = "number";
    cropIn.min = "0";
    cropIn.max = "2.5";
    cropIn.step = "0.05";
    cropIn.title = "Subject-centered auto-crop expansion (e.g. 1.6x). 0 keeps full original framing.";
    cropIn.addEventListener("change", () => {
        state.crop_margin = Math.min(2.5, Math.max(0, Number(cropIn.value) || 0));
        cropIn.value = String(state.crop_margin);
        saveState();
    });

    const maxTokIn = el("input", "h3e-input");
    maxTokIn.type = "number";
    maxTokIn.min = "0";
    maxTokIn.max = "1048576";
    maxTokIn.step = "64";
    maxTokIn.title = "Optional token budget per member/video (0 = unlimited).";
    maxTokIn.addEventListener("change", () => {
        state.max_tokens = Math.max(0, Math.round(Number(maxTokIn.value) || 0));
        maxTokIn.value = String(state.max_tokens);
        saveState();
    });

    const descIn = el("input", "h3e-input");
    descIn.type = "text";
    descIn.placeholder = "one-sentence caption (auto-fills empty Refs row description & retention_analysis)";
    descIn.addEventListener("input", () => {
        state.description = descIn.value;
        saveState();
    });

    const captionBtn = button("✨ Auto-Caption",
        "Inspect staged stills (or stored RefMod looks) with your VLM writer and generate an H3 studio-safe description",
        () => autoCaption({ autoWake: true, saveMeta: false, silentOnOffline: false }));
    const autoCapChkWrap = el("label", "r2-st-chk");
    const autoCapChk = el("input");
    autoCapChk.type = "checkbox";
    autoCapChk.checked = state.auto_caption !== false;
    autoCapChk.addEventListener("change", () => {
        state.auto_caption = autoCapChk.checked;
        saveState();
    });
    autoCapChkWrap.append(autoCapChk, el("span", null, "Auto-caption if blank"));
    autoCapChkWrap.title = "If Description is empty and your LLM writer is running, automatically caption before baking.";

    const descRow = el("div", "r2-rm-descrow");
    descRow.append(descIn, captionBtn, autoCapChkWrap);
    const descWrap = mkField("Description", descRow);
    descWrap.classList.add("h3e-run-wide");

    dialGrid.append(
        mkField("Layout", layoutSel),
        mkField("Subject Mask", maskSel),
        mkField("Background Mode", bgModeSel),
        mkField("Bg Retention", retIn),
        mkField("Fit Mode", fitSel),
        mkField("Crop Margin", cropIn),
        mkField("Max Tokens", maxTokIn),
        descWrap,
    );
    dialSec.appendChild(dialGrid);

    const actionBar = el("div", "h3e-mod-actions");
    const buildBtn = button("⚡ Build & Save RefMod",
        "Queue H3 VAE encoding via ComfyUI (zero VRAM collision), write models/refmods/<name>.safetensors, and attach to Refs",
        () => buildRefMod(), "h3e-btn h3e-btn-accent");
    const previewStillSel = el("select", "h3e-select");
    previewStillSel.title = "Which still to preview subject masking on.";
    const previewMaskBtn = button("👁 Preview Mask",
        "Preview subject cutout + background_mode + crop_margin before baking",
        () => previewMask());
    const saveMetaBtn = button("💾 Save Header Only",
        "Update description, role, default curve, and voice metadata in existing .safetensors without re-encoding",
        () => saveHeaderOnly());
    const loadSourcesBtn = button("📂 Load Sources",
        "Read stored stills, clip, voice, and metadata back from models/refmods/<name>.safetensors",
        () => loadStoredPlan({ keepSourcesIfEmpty: false }));
    const saveBibleBtn = button("📖 Save to Ref Bible",
        "Save or update this RefMod entry in SandTie Reference Bible (with description, voice & step curve)",
        () => saveToRefBible());

    actionBar.append(buildBtn, previewStillSel, previewMaskBtn, saveMetaBtn, loadSourcesBtn, saveBibleBtn);
    dialSec.appendChild(actionBar);
    rightCol.appendChild(dialSec);

    const buildStatus = el("div", "h3e-note h3e-mod-summary");
    rightCol.appendChild(buildStatus);

    const maskBox = el("div", "h3e-section h3e-mod-maskbox");
    maskBox.hidden = true;
    const maskHead = el("div", "h3e-mod-head");
    maskHead.appendChild(el("span", "h3e-title", "MASK CUTOUT PREVIEW"));
    maskHead.appendChild(button("×", "Hide mask preview", () => { maskBox.hidden = true; }, "h3e-btn h3e-x"));
    const maskImg = el("img", "h3e-mod-maskimg");
    maskImg.alt = "RefMod subject cutout preview";
    const maskNote = el("div", "h3e-note h3e-note-hint");
    maskBox.append(maskHead, maskImg, maskNote);
    rightCol.appendChild(maskBox);

    const inspectorBox = el("div", "h3e-section h3e-mod-inspector");
    inspectorBox.hidden = true;
    rightCol.appendChild(inspectorBox);

    function syncPreviewStillOptions() {
        const filled = state.stills.filter(Boolean);
        const prev = previewStillSel.value;
        previewStillSel.textContent = "";
        if (!filled.length) {
            previewStillSel.appendChild(el("option", null, "still #1")).value = "0";
            return;
        }
        filled.forEach((fn, idx) => {
            const o = el("option", null, `#${idx + 1} ${fn}`);
            o.value = String(idx);
            previewStillSel.appendChild(o);
        });
        if (prev && Number(prev) < filled.length) previewStillSel.value = prev;
    }

    function syncInputsFromState() {
        nameIn.value = state.name || "";
        subIn.value = state.subfolder || "";
        roleSel.value = ROLES.includes(state.role) ? state.role : "identity";
        curveSel.value = state.default_step_curve || "full";
        attachChk.checked = state.auto_attach !== false;
        attachTagIn.value = state.attach_tag || "";
        attachSubjSel.value = state.attach_subject ?? "";
        layoutSel.value = state.layout || "separate_pictures";
        maskSel.value = state.subject_mask || "auto_rembg";
        bgModeSel.value = state.background_mode || "blur_bg";
        retIn.value = String(state.background_retention ?? 0);
        fitSel.value = state.fit_mode || "crop";
        cropIn.value = String(state.crop_margin ?? 0);
        maxTokIn.value = String(state.max_tokens ?? 0);
        descIn.value = cleanDesc(state.description);
        autoCapChk.checked = state.auto_caption !== false;
        extAspSel.value = state.ext_aspect || "3:4";
        extMpSel.value = String(state.ext_mp ?? "0");
        if (state.ext_profile && [...(extProfSel.options || [])].some((o) => o.value === state.ext_profile)) {
            extProfSel.value = state.ext_profile;
        }
        extPromptArea.value = state.ext_prompt || EXTRACT_PRESETS[0].prompt;
        extSeedIn.value = String(state.ext_seed || 0);
        syncExtDim();
        syncPreviewStillOptions();
        paintExtPreview();
    }

    function renderInspector(info) {
        lastInspected = info || null;
        inspectorBox.textContent = "";
        if (!info) {
            inspectorBox.hidden = true;
            return;
        }
        inspectorBox.hidden = false;
        const head = el("div", "h3e-mod-head");
        head.appendChild(el("span", "h3e-title", `STORED: ${info.name}`));
        const badges = el("div", "h3e-mod-badges");
        badges.appendChild(el("span", "h3e-count", `${info.format || "v4"} · ${info.role || "generic"} · ${info.tokens || 0} tok`));
        head.appendChild(badges);
        inspectorBox.appendChild(head);

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
                                setBanner(buildStatus, j.error || "Member removal failed.", "error");
                                return;
                            }
                            renderInspector(j.inspect);
                            refreshStoredList();
                            invalidateRefmods(true);
                            if (typeof window !== "undefined") {
                                window.dispatchEvent?.(new CustomEvent("htc:refmods-changed"));
                            }
                            setBanner(buildStatus, `Removed member #${m.index + 1} from ${info.name}.`, "hint");
                        } catch (err) {
                            setBanner(buildStatus, String(err), "error");
                        }
                    }, "h3e-btn h3e-x"));
                }
                rowWrap.appendChild(chip);
            }
            details.appendChild(rowWrap);
        }
        card.appendChild(details);
        inspectorBox.appendChild(card);
    }

    function paintEstimate(error) {
        if (error) {
            setBanner(buildStatus, String(error), "error");
            return;
        }
        const filled = state.stills.filter(Boolean);
        if (!filled.length && !state.clip?.file) {
            setBanner(buildStatus,
                "Extract a clean shot from a sheet on the left (or add stills), then click ⚡ Build & Save RefMod.",
                "hint");
            return;
        }
        const bits = [];
        if (filled.length) bits.push(`${filled.length} still${filled.length === 1 ? "" : "s"}`);
        if (est?.clip_frames) bits.push(`${est.clip_frames}f clip`);
        else if (state.clip?.file) bits.push("clip");
        let line = bits.join(" + ");
        const lay = est?.layout || state.layout || "separate_pictures";
        if (est?.canvas) {
            if (lay === "separate_pictures" && filled.length > 0 && !state.clip?.file) {
                line += ` → v5 native-aspect bundle (${est.still_tokens} tokens total)`;
            } else {
                line += ` → ${est.canvas[0]}×${est.canvas[1]} canvas, ${est.per_frame_tokens} tokens/frame`;
                if (filled.length && !state.clip?.file) line += `, ${est.still_tokens} total`;
            }
        }
        if (state.voice) line += `, voice ${state.voice}`;
        if (est?.clip_dropped) line += ` — ${est.clip_dropped} frame(s) trimmed by 17k+5 snap`;
        if (est?.problems?.length) {
            setBanner(buildStatus, `${line} — ${est.problems.join("; ")}`, "error");
            return;
        }
        setBanner(buildStatus, line, "hint");
    }

    function estimate() {
        syncPreviewStillOptions();
        const seq = ++estSeq;
        const filled = state.stills.filter(Boolean);
        if (!filled.length && !state.clip?.file) {
            est = null;
            paintEstimate();
            return;
        }
        if (typeof fetch !== "function") {
            paintEstimate();
            return;
        }
        fetch(ESTIMATE_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                stills: filled,
                clip: state.clip?.file ? state.clip : null,
                voice: state.voice || "",
                layout: state.layout || "separate_pictures",
            }),
        })
            .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
            .then((j) => {
                if (seq !== estSeq) return;
                est = j && j.ok ? j : null;
                paintEstimate(j && !j.ok ? j.error : "");
            })
            .catch(() => {
                if (seq !== estSeq) return;
                est = null;
                paintEstimate();
            });
    }

    async function previewMask() {
        const filled = state.stills.filter(Boolean);
        if (!filled.length) {
            setBanner(buildStatus, "Add or extract at least one still first to preview subject masking.", "error");
            return;
        }
        const idx = Math.min(filled.length - 1, Math.max(0, Number(previewStillSel.value) || 0));
        const target = filled[idx];
        const useBackend = state.subject_mask === "off" ? "auto_rembg" : (state.subject_mask || "auto_rembg");
        maskBox.hidden = false;
        maskNote.textContent = `Running ${useBackend} (${state.background_mode || "blur_bg"}) on ${target}...`;
        try {
            const res = await fetch(PREVIEW_MASK_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    image: target,
                    subject_mask: useBackend,
                    background_retention: Number(state.background_retention) || 0,
                    background_mode: state.background_mode || "blur_bg",
                    crop_margin: Number(state.crop_margin) || 0,
                }),
            });
            if (!res.ok) {
                const ej = await res.json().catch(() => ({}));
                maskNote.textContent = ej.error || `Mask preview failed (HTTP ${res.status})`;
                return;
            }
            const blob = await res.blob();
            if (maskObjUrl) URL.revokeObjectURL(maskObjUrl);
            maskObjUrl = URL.createObjectURL(blob);
            maskImg.src = maskObjUrl;
            maskNote.textContent = state.subject_mask === "off"
                ? `Previewed ${useBackend} (${state.background_mode}). Note: Subject Mask is 'off' — set it to ${useBackend} to apply when building.`
                : `Previewing #${idx + 1} (${target}) · ${useBackend} · ${state.background_mode} · retention ${Number(state.background_retention || 0).toFixed(2)}`
                  + (Number(state.crop_margin) > 0 ? ` · crop ${Number(state.crop_margin).toFixed(2)}x` : "");
        } catch (err) {
            maskNote.textContent = `Mask preview failed: ${err}`;
        }
    }

    function attachRefModToRail(finalName) {
        const plan = readRefs(node);
        const refs = Array.isArray(plan?.refs) ? [...plan.refs] : [];
        const subjects = { ...(plan?.subjects || {}) };
        const cleanTag = slugOf(state.attach_tag || state.name || finalName, "refmod");
        const curve = state.default_step_curve || "full";
        const desc = cleanDesc(state.description);
        const subjNum = state.attach_subject ? Number(state.attach_subject) : null;
        const retention = state.role === "background"
            ? "reference"
            : (state.role === "helper" ? "prop" : "fully_preserved");

        const existingIdx = refs.findIndex((r) => String(r.tag || "").toLowerCase() === cleanTag
            || (r.source === "refmod" && r.file === finalName));
        if (existingIdx >= 0) {
            const cur = refs[existingIdx];
            refs[existingIdx] = {
                ...cur,
                source: "refmod",
                file: finalName,
                legacy_slot: null,
                members: null,
                retention: cur.retention || retention,
                desc: desc || cur.desc || "",
                ...(subjNum != null ? { subject: subjNum } : {}),
                ...(curve !== "full" ? { step_curve: curve } : {}),
            };
        } else {
            refs.push({
                tag: cleanTag,
                source: "refmod",
                file: finalName,
                slot: refs.length + 1,
                subject: subjNum,
                retention,
                desc,
                ...(curve !== "full" ? { step_curve: curve } : {}),
            });
        }
        if (subjNum != null) {
            if (!subjects[String(subjNum)]) {
                subjects[String(subjNum)] = {
                    name: cleanTag.replace(/_/g, " "),
                    locked: desc,
                    context: "",
                };
            } else if (desc && !String(subjects[String(subjNum)].locked || "").trim()) {
                subjects[String(subjNum)].locked = desc;
            }
        }
        writeRefs(node, { refs, subjects });
        onChange?.();
        return cleanTag;
    }

    async function autoCaption({ autoWake = true, saveMeta = false, silentOnOffline = false } = {}) {
        const filled = state.stills.filter(Boolean);
        const modName = fullModName();
        if (!filled.length && !modName) {
            if (!silentOnOffline) setBanner(buildStatus, "Add a still or load a stored RefMod first.", "error");
            return false;
        }
        captionBtn.disabled = true;
        if (!silentOnOffline) {
            setBanner(buildStatus, "Captioning RefMod via VLM (studio-backdrop safe)...", "hint");
        }
        try {
            const res = await fetch(CAPTION_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: modName,
                    stills: filled,
                    role: state.role || "identity",
                    auto_wake: Boolean(autoWake),
                    save_meta: Boolean(saveMeta),
                    unload_after: Boolean(silentOnOffline),
                }),
            });
            const j = await res.json();
            if (!res.ok || !j.ok || !j.description) {
                if (!silentOnOffline) {
                    setBanner(buildStatus, j?.error || "Auto-caption failed.", "error");
                }
                return false;
            }
            state.description = cleanDesc(j.description);
            descIn.value = state.description;
            saveState();
            if (j.inspect) {
                renderInspector(j.inspect);
                refreshStoredList();
                invalidateRefmods(true);
            }
            if (!silentOnOffline) {
                const hint = (lastInspected?.name === modName && !saveMeta)
                    ? "Captioned! Click 💾 Save Header Only (or ⚡ Build & Save RefMod) to save."
                    : "Captioned! Ready to bake into RefMod header & Refs.";
                setBanner(buildStatus, hint, "hint");
            }
            return true;
        } catch (err) {
            if (!silentOnOffline) setBanner(buildStatus, `Auto-caption failed: ${err}`, "error");
            return false;
        } finally {
            captionBtn.disabled = false;
        }
    }

    async function buildRefMod() {
        if (busyBuild) return;
        const modName = String(state.name || "").trim();
        const filled = state.stills.filter(Boolean);
        if (!modName) {
            setBanner(buildStatus, "Enter a RefMod Name first.", "error");
            return;
        }
        if (!filled.length && !state.clip?.file) {
            setBanner(buildStatus, "Add at least one still or clip (or extract a shot from a sheet) first.", "error");
            return;
        }
        busyBuild = true;
        buildBtn.disabled = true;
        try {
            if (state.auto_caption !== false && !cleanDesc(state.description) && filled.length > 0) {
                setBanner(buildStatus, "Auto-captioning from stills (if VLM online)...", "hint");
                await autoCaption({ autoWake: false, saveMeta: false, silentOnOffline: true });
            }
            setBanner(buildStatus, `Queueing RefMod bake for "${fullModName()}"...`, "hint");
            const res = await runForgeGraph({
                kind: "refmod",
                name: modName,
                stills: filled,
                clip: state.clip?.file ? state.clip : null,
                voice: state.voice || "",
                subfolder: String(state.subfolder || "").trim(),
                description: cleanDesc(state.description),
                layout: state.layout || "separate_pictures",
                role: state.role || "identity",
                default_step_curve: state.default_step_curve || "full",
                subject_mask: state.subject_mask || "off",
                background_retention: Number(state.background_retention) || 0,
                background_mode: state.background_mode || "blur_bg",
                fit_mode: state.fit_mode || "crop",
                crop_margin: Number(state.crop_margin) || 0,
                max_tokens: Number(state.max_tokens) || 0,
            }, {
                onStatus: (m) => setBanner(buildStatus, m, "hint"),
            });
            const finalName = res.refmod_name || fullModName();
            await saveToRefBible(finalName, { quiet: true });
            await refreshStoredList();
            invalidateRefmods(true);
            if (typeof window !== "undefined") {
                window.dispatchEvent?.(new CustomEvent("htc:refmods-changed"));
            }
            const insp = await fetch(`${INSPECT_URL}?name=${encodeURIComponent(finalName)}`)
                .then((r) => (r.ok ? r.json() : null))
                .catch(() => null);
            if (insp?.ok) renderInspector(insp);

            if (state.auto_attach !== false) {
                const tag = attachRefModToRail(finalName);
                setBanner(buildStatus, `Built RefMod "${finalName}" and attached @${tag} to Refs rail!`, "hint");
            } else {
                setBanner(buildStatus, `Built RefMod "${finalName}" in models/refmods/!`, "hint");
            }
        } catch (err) {
            setBanner(buildStatus, String(err), "error");
        } finally {
            busyBuild = false;
            buildBtn.disabled = false;
        }
    }

    async function saveToRefBible(modNameOverride = "", { quiet = false } = {}) {
        const modName = String(modNameOverride || fullModName() || "").trim();
        if (!modName) {
            if (!quiet) setBanner(buildStatus, "Name or load a RefMod first.", "error");
            return false;
        }
        const roleMap = { background: "place", helper: "prop" };
        const cleanTag = slugOf(state.attach_tag || state.name || modName.split("/").pop(), "refmod");
        try {
            const res = await fetch(REFBANK_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: "save",
                    item: {
                        file: modName,
                        source: "refmod",
                        tag: cleanTag,
                        role: roleMap[state.role] || "subject",
                        voice: state.voice || "",
                        desc: cleanDesc(state.description),
                        step_curve: state.default_step_curve || "full",
                        strength: 1.0,
                    },
                }),
            });
            const j = await res.json();
            if (!res.ok || !j?.ok) {
                if (!quiet) setBanner(buildStatus, j?.error || "Save to Ref Bible failed.", "error");
                return false;
            }
            if (typeof window !== "undefined") {
                window.dispatchEvent?.(new CustomEvent("htc:refmods-changed"));
            }
            if (!quiet) {
                setBanner(buildStatus, `Saved RefMod "${modName}" (@${cleanTag}) to Reference Bible!`, "hint");
            }
            return true;
        } catch (err) {
            if (!quiet) setBanner(buildStatus, `Save to Ref Bible failed: ${err}`, "error");
            return false;
        }
    }

    async function saveHeaderOnly() {
        const modName = fullModName();
        if (!modName) {
            setBanner(buildStatus, "Name or load a RefMod first.", "error");
            return;
        }
        try {
            const res = await fetch(UPDATE_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: modName,
                    action: "meta",
                    description: cleanDesc(state.description),
                    role: state.role || "identity",
                    default_step_curve: state.default_step_curve || "full",
                    voice: state.voice || "",
                    voice_start: state.voiceStart || 0,
                    voice_end: state.voiceEnd || 0,
                }),
            });
            const j = await res.json();
            if (!res.ok || !j.ok) {
                setBanner(buildStatus, j.error || "Header save failed.", "error");
                return;
            }
            renderInspector(j.inspect);
            await refreshStoredList();
            invalidateRefmods(true);
            if (typeof window !== "undefined") {
                window.dispatchEvent?.(new CustomEvent("htc:refmods-changed"));
            }
            setBanner(buildStatus, `Saved header metadata for "${modName}" (zero re-encode).`, "hint");
        } catch (err) {
            setBanner(buildStatus, String(err), "error");
        }
    }

    async function loadStoredPlan({ keepSourcesIfEmpty = false } = {}) {
        const modName = fullModName();
        if (!modName) {
            setBanner(buildStatus, "Pick an existing RefMod or type its name first.", "error");
            return;
        }
        try {
            const res = await fetch(PLAN_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: modName }),
            });
            const data = await res.json();
            if (!data.ok) {
                setBanner(buildStatus, data.error || "Could not read RefMod.", "error");
                return;
            }
            const stored = data.plan || {};
            const insp = data.inspect || null;
            renderInspector(insp);

            const descText = cleanDesc(data.description || insp?.description || "");
            state.description = descText;
            if (insp?.role && ROLES.includes(insp.role)) state.role = insp.role;
            if (insp?.default_step_curve) state.default_step_curve = insp.default_step_curve;

            const stills = Array.isArray(stored.stills) ? stored.stills.slice() : [];
            if (stills.length || stored.clip || stored.voice) {
                state.stills = stills;
                state.clip = stored.clip ? { ...stored.clip } : null;
                state.voice = stored.voice || "";
                state.voiceStart = Number(stored.voice_start) || 0;
                state.voiceEnd = Number(stored.voice_end) || 0;
            } else if (!keepSourcesIfEmpty) {
                setBanner(buildStatus, `"${modName}" carries header/latents only (no source list stored).`, "hint");
            }
            saveState();
            syncInputsFromState();
            renderStills();
            renderClip();
            renderVoice();
            estimate();
        } catch (err) {
            setBanner(buildStatus, `Failed reading RefMod: ${err}`, "error");
        }
    }

    storedSel.addEventListener("change", () => {
        const chosen = storedSel.value;
        if (!chosen) return;
        const slash = chosen.lastIndexOf("/");
        if (slash >= 0) {
            state.subfolder = chosen.slice(0, slash);
            state.name = chosen.slice(slash + 1);
        } else {
            state.subfolder = "";
            state.name = chosen;
        }
        saveState();
        syncInputsFromState();
        loadStoredPlan({ keepSourcesIfEmpty: true });
    });

    async function refreshStoredList() {
        if (typeof fetch !== "function") return;
        try {
            const r = await fetch(FILES_URL);
            const j = await r.json();
            if (!Array.isArray(j.files)) return;
            modFiles = j.files;
            const cur = fullModName();
            storedSel.textContent = "";
            storedSel.appendChild(el("option", null, `— existing RefMods (${modFiles.length}) —`)).value = "";
            for (const f of modFiles) {
                const badge = f.format ? ` [${f.format}${f.members_count > 1 ? `·${f.members_count}m` : ""}·${f.role || "gen"}]` : "";
                const o = el("option", null, `${f.name}${badge}`);
                o.value = f.name;
                storedSel.appendChild(o);
            }
            if (cur && modFiles.some((f) => f.name === cur)) {
                storedSel.value = cur;
            }
        } catch (_) { /* offline in mount_test */ }
    }

    async function fetchCaps() {
        if (typeof fetch !== "function") return;
        try {
            const r = await fetch(CAPS_URL, { cache: "no-store" });
            const j = await r.json();
            if (!j.ok) return;
            caps = j;
            capsLoaded = true;
            const profs = Array.isArray(j.image_profiles) ? j.image_profiles : [];
            const editProfs = profs.filter((p) => p.supports_edit);
            const list = editProfs.length ? editProfs : profs;
            const profSig = list.map((p) => `${p.id}:${p.ready}:${p.label}`).join("|");
            if (profSig !== lastProfSig) {
                lastProfSig = profSig;
                extProfSel.textContent = "";
                for (const p of list) {
                    const o = el("option", null, p.ready ? p.label : `${p.label} (missing weights)`);
                    o.value = p.id;
                    o.title = p.note || "";
                    extProfSel.appendChild(o);
                }
            }
            if (!list.some((p) => p.id === state.ext_profile)) {
                const firstReady = list.find((p) => p.ready)?.id || j.default_image_profile || "qwen_viggle_6step";
                state.ext_profile = firstReady;
                saveState();
            }
            if (extProfSel.value !== state.ext_profile) {
                extProfSel.value = state.ext_profile;
            }
            syncExtDim();

            const vaes = j.h3_vaes || {};
            if (vaes.video) {
                vaeBadge.textContent = vaes.audio
                    ? `VAE: ${vaes.video} + audio`
                    : `VAE: ${vaes.video}`;
            } else {
                vaeBadge.textContent = "VAE: missing H3 video VAE";
            }
        } catch (_) { /* offline in mount_test */ }
    }

    const stopFiles = onFilesChanged(() => {
        sheetPick.render();
        ref2Pick.render();
        renderStills();
        renderClip();
        renderVoice();
    });
    const onRefmodsEvt = () => {
        refreshStoredList();
        if (lastInspected?.name && typeof fetch === "function") {
            fetch(`${INSPECT_URL}?name=${encodeURIComponent(lastInspected.name)}`)
                .then((r) => (r.ok ? r.json() : null))
                .then((j) => { if (j?.ok) renderInspector(j); })
                .catch(() => {});
        }
    };
    if (typeof window !== "undefined") {
        window.addEventListener?.("htc:refmods-changed", onRefmodsEvt);
    }

    function renderAll() {
        syncInputsFromState();
        paintExtMode();
        sheetPick.render();
        ref2Pick.render();
        renderStills();
        renderClip();
        renderVoice();
        estimate();
    }

    function openForRefMod(modName) {
        const clean = String(modName || "").trim();
        if (!clean) return;
        const slash = clean.lastIndexOf("/");
        if (slash >= 0) {
            state.subfolder = clean.slice(0, slash);
            state.name = clean.slice(slash + 1);
        } else {
            state.subfolder = "";
            state.name = clean;
        }
        saveState();
        renderAll();
        loadStoredPlan({ keepSourcesIfEmpty: true });
    }

    fetchCaps();
    refreshStoredList();
    renderAll();

    return {
        root,
        render: () => {
            hydrateFromProps();
            if (!capsLoaded) fetchCaps();
            refreshStoredList();
            renderAll();
        },
        openForRefMod,
        modCount: () => modFiles.length,
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
            voiceBar?.destroy?.();
        },
    };
}
