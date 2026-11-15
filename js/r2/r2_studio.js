/**
 * Checkpointable MV Studio & Image/Song Forge (R2 Studio Tab).
 *
 * Four vetted stages inside one cohesive workspace:
 *   1. Concept & Lyrics   — nInfer/LLM generates YuE2 style, lyrics, and asset blueprints.
 *   2. Song & Beat Lock   — Generate via YuE2 (or pick/upload audio) -> songmap + mv_solver -> Lock Cuts.
 *   3. Visual Asset Forge — Paint cast sheets, plates, props via Qwen 2.1 Viggle / RedQW Unlocked / MOSS / H3-Image -> Keep to Refs.
 *   4. Direct & Hand-Off  — Send vetted brief + section beats + locked cuts to Write.
 */

import { el, button, widgetByName } from "../editor/widget_utils.js";
import { IMAGE_MP_STOPS, previewImageDims, runForgeGraph, unloadWriterForGpu, viewUrl } from "../editor/forge_queue.js";
import { readPlan, writePlan, readRefs, writeRefs, durationOf } from "./r2_store.js";

const STUDIO_PROP = "h3_mv_studio";
const LLM_URL = "/h3_ref_chain/llm";
const SECTION_KINDS = ["intro", "verse", "pre_chorus", "chorus", "bridge", "drop", "instrumental", "outro"];
const MV_VIBE_PRESETS = [
    ["", "Preset Vibe (Optional)…", null],
    ["anime_jrock_jp", "🇯🇵 Anime OP / J-Rock Storm (Japanese · 168 BPM)", { idea: "High-velocity anime J-Rock opening MV shifting from moonlit shrine steps to a dramatic storm-lit rooftop battle clash, driving guitars and soaring chorus, 168 BPM", vocal: "female", aspect: "16:9", lang: "Japanese" }],
    ["tokyo_citypop_jp", "🇯🇵 Tokyo City Pop Midnight Cruise (Japanese · 114 BPM)", { idea: "Glossy 80s Tokyo City Pop MV cruising along wet neon Shuto expressways and shimmering diner glass at midnight, nostalgic synth brass and slap bass, 114 BPM", vocal: "female", aspect: "16:9", lang: "Japanese" }],
    ["shibuya_idol_jp", "🇯🇵 Shibuya Electro Idol Stage (Japanese · 138 BPM)", { idea: "Hyper-bright Shibuya neon idol performance MV with crisp synchronized choreography inside a mirrored laser rehearsal stage, 138 BPM", vocal: "female", aspect: "9:16", lang: "Japanese" }],
    ["kpop_studio", "🇰🇷 K-Pop / Idol Studio Stage (Korean · 124 BPM)", { idea: "High-gloss K-Pop idol performance MV inside an architectural neon & chrome rehearsal studio and rain-slicked rooftop stage, sharp choreography snaps, 124 BPM", vocal: "female", aspect: "9:16", lang: "Korean" }],
    ["seoul_dark_rnb_kr", "🇰🇷 Seoul Midnight R&B / Hip-Hop Duet (Korean · 94 BPM)", { idea: "Moody late-night Seoul penthouse and rain-streaked balcony duet MV with sultry R&B vocals and tight melodic rap verse, 94 BPM", vocal: "duet", aspect: "16:9", lang: "Korean" }],
    ["guofeng_wuxia_cn", "🇨🇳 Guofeng Wuxia Silk-Flute Ballad (Chinese · 96 BPM)", { idea: "Poetic snowy bamboo forest and lantern courtyard Guofeng wuxia MV blending guzheng, bamboo flute, and sweeping silk sleeves, 96 BPM", vocal: "female", aspect: "16:9", lang: "Chinese" }],
    ["chongqing_trap_cn", "🇨🇳 Chongqing Neon Cyber Trap (Chinese · 134 BPM)", { idea: "Futuristic rain-glossed Chongqing neon overpass rap MV with heavy 808 sub-bass, fast tracking shots, and cyberpunk streetwear, 134 BPM", vocal: "rap", aspect: "9:16", lang: "Chinese" }],
    ["latin_rooftop_es", "🇪🇸 Latin Reggaeton / Rooftop Night (Spanish · 98 BPM)", { idea: "Warm twilight Miami rooftop club MV with infectious dembow reggaeton percussion, golden-hour sunset glow, and duet vocals, 98 BPM", vocal: "duet", aspect: "9:16", lang: "Spanish" }],
    ["french_touch_fr", "🇫🇷 Parisian French-Touch Synth Disco (French · 120 BPM)", { idea: "Velvet Parisian Haussmann apartment and midnight cobblestone café MV driven by filtered French-touch disco bassline and airy vocals, 120 BPM", vocal: "female", aspect: "16:9", lang: "French" }],
    ["street_phonk", "Street Rap / Dark Phonk Night (English · 136 BPM)", { idea: "Gritty dark Memphis phonk & street rap MV across a wet neon Tokyo back-alley and midnight parking garage, low-angle handheld energy, 136 BPM", vocal: "rap", aspect: "16:9", lang: "English" }],
    ["synthwave_drive", "Synthwave Midnight Diner & Cruise (English · 108 BPM)", { idea: "Nocturnal dark synthwave pop MV starting at a rain-streaked 2AM neon diner and expanding onto a glowing wet coastal overpass, 108 BPM", vocal: "female", aspect: "16:9", lang: "English" }],
    ["indie_story", "Indie Folk / Acoustic Story Arc (English · 92 BPM)", { idea: "Warm golden-hour indie rock storytelling MV moving from a sunlit artist loft into an autumn city street walk, intimate honest performance, 92 BPM", vocal: "male", aspect: "16:9", lang: "English" }],
    ["metal_stage", "Rock / Metal Underground Warehouse (English · 144 BPM)", { idea: "Raw industrial rock / metal live MV inside a smoke-filled brick warehouse lit by warm tungsten backlights and strobes, fierce physical energy, 144 BPM", vocal: "male", aspect: "16:9", lang: "English" }],
    ["noir_jazz_lounge", "90s Velvet Noir Jazz Lounge (English · 74 BPM)", { idea: "Smoky 35mm neo-noir jazz lounge MV sliced by venetian-blind light, upright bass, tenor sax, and velvet vocal storytelling, 74 BPM", vocal: "female", aspect: "16:9", lang: "English" }],
    ["hyperpop_rave", "Cyber Rave / Hyperpop Glitch Club (English · 154 BPM)", { idea: "Strobe-lit underground neon rave MV with glitching laser beams, rapid jump-cut choreography, and distorted hyperpop synth drops, 154 BPM", vocal: "female", aspect: "9:16", lang: "English" }],
    ["epic_instrumental", "Epic Cinematic Instrumental Score (116 BPM)", { idea: "Sweeping orchestral-electronic trailer visual journey across misty mountain peaks, glass towers, and rain-slicked streets, purely instrumental, 116 BPM", vocal: "instrumental", aspect: "16:9", lang: "auto" }],
];
const DEFAULT_DURATION_LABELS = {
    124: "5 s", 141: "6 s", 175: "7 s", 192: "8 s", 209: "9 s",
    243: "10 s", 260: "11 s", 294: "12 s", 311: "13 s", 328: "14 s",
    362: "15 s", 379: "16 s", 413: "17 s", 430: "18 s", 464: "19 s", 481: "20 s",
};

function uid() {
    return "st_" + Math.random().toString(36).slice(2, 9);
}

function defaultState() {
    return {
        idea: "",
        title: "",
        aspect: "16:9",
        duration_target_s: 105,
        language: "auto",
        vocal_mode: "auto",
        auto_wake: true,
        song_style: "",
        lyrics: "",
        brief: "",
        song_file: "",
        song_engine: "",
        song_mode: "full",
        vocals_only: false,
        listen: false,
        image_profile: "qwen_viggle_6step",
        image_mp: "0",
        assets: [],
        song_analysis: null,
    };
}

export function createStudioPane(node, { onChange, onSendToWrite } = {}) {
    const root = el("div", "r2-st");

    let caps = null;
    let capsLoaded = false;
    let lastImgProfSig = "";
    let busyConcept = false;
    let busySong = false;
    let llmLoaded = false;
    let llmLoadSeq = 0;
    let llmState = { running: false, online: false, backend: "lmstudio", backend_label: "LM Studio", model: "", startup_error: "" };

    function loadState() {
        node.properties ??= {};
        const raw = node.properties[STUDIO_PROP];
        const base = defaultState();
        if (raw && typeof raw === "object") {
            Object.assign(base, raw);
            if (!Array.isArray(base.assets)) base.assets = [];
        }
        return base;
    }

    const state = loadState();
    let userTouched = false;
    function saveState() {
        userTouched = true;
        node.properties ??= {};
        node.properties[STUDIO_PROP] = JSON.parse(JSON.stringify(state));
    }
    function hydrateFromProps() {
        if (userTouched) return;
        const raw = node.properties?.[STUDIO_PROP];
        if (raw && typeof raw === "object") {
            Object.assign(state, loadState());
        }
    }

    function commitWidget(name, val) {
        const w = widgetByName(node, name);
        if (!w) return false;
        w.value = val;
        try {
            w.callback?.(val, node.graph?.canvas, node, undefined, undefined);
        } catch (_) { /* */ }
        node.graph?.setDirtyCanvas?.(true, true);
        return true;
    }

    /* -- top header bar -------------------------------------------------- */
    const topBar = el("div", "r2-st-top");
    const topTitle = el("div", "r2-st-title", "MV & Asset Ideation Studio");
    const topHint = el("span", "r2-st-sub", "Checkpointable pipeline: Concept \u2192 Song & Beat Lock \u2192 Visual Forge \u2192 Write");
    const refreshCapsBtn = button("\u21bb Refresh Models", "Re-scan installed image & YuE2 models, audio files, and LLM writer status", () => {
        fetchCaps(true);
        loadLlmSettings({ quiet: true });
    });
    const freeGpuBtn = button("\u2615 Free LLM VRAM", "Unload local nInfer / LM Studio writer model before queueing generation", async () => {
        setStatus(conceptStatus, "Unloading LLM writer from VRAM...", "hint");
        await unloadWriterForGpu();
        await loadLlmSettings({ quiet: true });
        setStatus(conceptStatus, "Writer unloaded (VRAM free for image / YuE2 / video).", "hint");
    });
    topBar.append(topTitle, topHint, refreshCapsBtn, freeGpuBtn);
    root.appendChild(topBar);

    const pipeBar = el("div", "r2-st-pipe");
    const pipeStep1 = el("span", "r2-st-step", "1. Concept & Lyrics");
    const pipeStep2 = el("span", "r2-st-step", "2. Song & Cuts");
    const pipeStep3 = el("span", "r2-st-step", "3. Plates & Cast");
    const pipeStep4 = el("span", "r2-st-step", "4. Write Ready");
    pipeBar.append(
        pipeStep1, el("span", "r2-st-arrow", "\u2192"),
        pipeStep2, el("span", "r2-st-arrow", "\u2192"),
        pipeStep3, el("span", "r2-st-arrow", "\u2192"),
        pipeStep4,
    );
    root.appendChild(pipeBar);

    function syncPipelineStrip() {
        const hasConcept = Boolean(String(state.song_style || "").trim() && String(state.lyrics || "").trim());
        const hasSong = Boolean(state.song_file && state.song_analysis?.solved?.ok);
        const lockedAudio = String(widgetByName(node, "master_audio_file")?.value || "").trim();
        const hasLocked = Boolean(hasSong && lockedAudio && lockedAudio === state.song_file && (readPlan(node).shots || []).length > 0);
        const totalAssets = (state.assets || []).length;
        const readyAssets = (state.assets || []).filter((a) => Boolean(a.kept_file || a.baked_refmod)).length;
        const railRefs = (readRefs(node)?.refs || []).filter((r) => Boolean(r.file)).length;
        const hasAssets = readyAssets > 0 || railRefs > 0;

        pipeStep1.className = "r2-st-step " + (hasConcept ? "is-done" : "is-next");
        pipeStep1.textContent = hasConcept ? "1. Concept \u2713" : "1. Spark Concept";

        pipeStep2.className = "r2-st-step " + (hasLocked ? "is-done" : (hasConcept || state.song_file ? "is-next" : ""));
        pipeStep2.textContent = hasLocked ? `2. Cuts Locked (${(readPlan(node).shots || []).length}h) \u2713` : (hasSong ? "2. Lock Cuts \u2192 Chain" : "2. Song & Beat Lock");

        pipeStep3.className = "r2-st-step " + (hasAssets && (!totalAssets || readyAssets === totalAssets) ? "is-done" : (hasConcept ? "is-next" : ""));
        pipeStep3.textContent = totalAssets
            ? `3. Assets (${readyAssets}/${totalAssets} in Refs)${readyAssets === totalAssets ? " \u2713" : ""}`
            : (railRefs ? `3. Refs (${railRefs}) \u2713` : "3. Paint & Keep Assets");

        pipeStep4.className = "r2-st-step " + (hasLocked && hasAssets ? "is-next" : "");
        pipeStep4.textContent = (hasLocked && hasAssets) ? "4. Send to Write \u25b8" : "4. Send to Write";
    }

    function setStatus(box, msg, kind = "") {
        box.style.display = msg ? "" : "none";
        box.className = "r2-st-status" + (kind === "error" ? " is-err" : kind === "hint" ? " is-ok" : "");
        box.textContent = msg || "";
    }

    /* ====================================================================
     * CARD 1: CONCEPT & LYRICS (nInfer / LLM)
     * ==================================================================== */
    const c1 = el("section", "r2-st-card");
    const c1Head = el("div", "r2-st-chead");

    const llmBackSel = el("select", "r2-st-sel");
    llmBackSel.title = "Writer backend (shared with Write / Standard / Swap)";
    for (const [bid, blbl] of [["lmstudio", "LM Studio"], ["ninfer", "nInfer"]]) {
        const o = el("option", null, blbl);
        o.value = bid;
        llmBackSel.appendChild(o);
    }

    const llmPill = el("span", "r2-st-pill", "Checking writer…");
    const llmStartBtn = button("Start", "Launch local nInfer writer server", () => toggleLlmServer("start"));
    const llmStopBtn = button("Stop", "Stop local writer to free VRAM", () => toggleLlmServer("stop"));

    const wakeWrap = el("label", "r2-st-chk");
    const wakeChk = el("input");
    wakeChk.type = "checkbox";
    wakeChk.checked = state.auto_wake !== false;
    wakeChk.addEventListener("change", () => {
        state.auto_wake = wakeChk.checked;
        saveState();
    });
    wakeWrap.append(wakeChk, el("span", null, "\u2615 Auto-Wake"));
    wakeWrap.title = "Auto-start nInfer from a cold start when Spark Concept & Assets is clicked";

    const llmCfgBtn = button("\u2699 LLM Settings", "Configure nInfer / LM Studio URL, model ID & .ninfer paths", () => {
        const open = llmDrawer.hidden;
        llmDrawer.hidden = !open;
        llmCfgBtn.classList.toggle("h3e-on", open);
        if (open) loadLlmSettings({ quiet: true });
    });

    const llmCtlGroup = el("div", "r2-st-llm-bar");
    llmCtlGroup.append(llmBackSel, llmPill, llmStartBtn, llmStopBtn, wakeWrap, llmCfgBtn);

    c1Head.append(
        el("span", "r2-st-badge", "1"),
        el("span", "r2-st-clabel", "Concept & Song Spec"),
        llmCtlGroup,
    );
    c1.appendChild(c1Head);

    const llmDrawer = el("div", "r2-st-drawer");
    llmDrawer.hidden = true;
    const cfgBackSel = el("select", "r2-st-sel");
    const cfgUrlInp = el("input", "r2-st-input");
    cfgUrlInp.type = "text";
    cfgUrlInp.placeholder = "http://127.0.0.1:1234";
    cfgUrlInp.style.flex = "1 1 170px";
    const cfgModelInp = el("input", "r2-st-input");
    cfgModelInp.type = "text";
    cfgModelInp.placeholder = "model id (optional / auto after Start)";
    cfgModelInp.title = "API model ID reported over /v1/models (not a file path; leave blank to auto-pick once running).";
    cfgModelInp.style.flex = "1 1 170px";
    const cfgModelPick = el("select", "r2-st-sel");
    cfgModelPick.style.maxWidth = "210px";
    cfgModelPick.addEventListener("change", () => {
        if (cfgModelPick.value) cfgModelInp.value = cfgModelPick.value;
    });
    const cfgKeepWarmWrap = el("label", "r2-st-chk");
    const cfgKeepWarmChk = el("input");
    cfgKeepWarmChk.type = "checkbox";
    cfgKeepWarmChk.checked = true;
    cfgKeepWarmWrap.append(cfgKeepWarmChk, el("span", null, "Keep Warm"));
    const cfgUnloadWrap = el("label", "r2-st-chk");
    const cfgUnloadChk = el("input");
    cfgUnloadChk.type = "checkbox";
    cfgUnloadChk.checked = true;
    cfgUnloadWrap.append(cfgUnloadChk, el("span", null, "Unload on Run"));
    const cfgSaveBtn = button("Save & Test", "Save writer connection and refresh model list", () => saveLlmSettings(), "h3e-btn h3e-btn-accent");
    const cfgRow = el("div", "r2-st-row");
    cfgRow.append(el("span", "r2-st-lbl", "WRITER"), cfgBackSel, cfgUrlInp, cfgModelInp, cfgModelPick, cfgKeepWarmWrap, cfgUnloadWrap, cfgSaveBtn);

    const cfgPathRow = el("div", "r2-st-row");
    const cfgExeInp = el("input", "r2-st-input");
    cfgExeInp.type = "text";
    cfgExeInp.placeholder = "nInfer exe path (e.g. C:\\ninfer\\ninfer-serve.exe)";
    cfgExeInp.title = "Full path to ninfer-serve.exe (or its folder). Leave blank to auto-detect in C:\\ninfer, D:\\ninfer, or C:\\AI\\NInfer.";
    cfgExeInp.style.flex = "1 1 220px";
    const cfgModelFileInp = el("input", "r2-st-input");
    cfgModelFileInp.type = "text";
    cfgModelFileInp.placeholder = "nInfer .ninfer file (or models folder / blank = auto)";
    cfgModelFileInp.title = "Full path to your .ninfer model file, a models folder containing one, or blank to auto-pick from models\\.";
    cfgModelFileInp.style.flex = "1 1 240px";
    const cfgCtxSel = el("select", "h3e-select");
    cfgCtxSel.style.maxWidth = "160px";
    cfgCtxSel.title = "nInfer startup max context & KV reservation (--max-context / --kv-capacity). Lower to 16k-32k on tighter VRAM GPUs so workflow renders have room.";
    for (const [val, txt] of [
        [16384, "16k ctx (tight VRAM)"],
        [24576, "24k ctx"],
        [32768, "32k ctx (low VRAM)"],
        [49152, "48k ctx"],
        [65536, "64k ctx (default)"],
        [98304, "96k ctx"],
        [131072, "128k ctx"],
    ]) {
        const o = el("option", null, txt);
        o.value = String(val);
        cfgCtxSel.appendChild(o);
    }
    cfgCtxSel.value = "65536";
    cfgPathRow.append(el("span", "r2-st-lbl", "PATHS"), cfgExeInp, cfgModelFileInp, cfgCtxSel);
    cfgPathRow.hidden = true;
    llmDrawer.append(cfgRow, cfgPathRow);
    c1.appendChild(llmDrawer);

    function paintLlmBar() {
        const lbl = llmState.backend_label || (llmState.backend === "ninfer" ? "nInfer" : "LM Studio");
        if (llmState.backend) llmBackSel.value = llmState.backend;
        const isRunning = Boolean(llmState.running || llmState.online);
        if (isRunning) {
            const mTail = llmState.model ? ` (${llmState.model})` : "";
            llmPill.textContent = `${lbl} Ready${mTail}`;
            llmPill.className = "r2-st-pill is-ready";
        } else {
            llmPill.textContent = `${lbl} Offline`;
            llmPill.className = "r2-st-pill";
        }
        llmStartBtn.disabled = Boolean(llmState.running) || llmState.backend !== "ninfer";
        llmStartBtn.style.display = llmState.backend === "ninfer" ? "" : "none";
        llmStopBtn.disabled = !isRunning;
    }

    async function switchLlmBackend(nextBack) {
        const lbl = nextBack === "ninfer" ? "nInfer" : "LM Studio";
        llmBackSel.value = nextBack;
        cfgBackSel.value = nextBack;
        cfgPathRow.hidden = nextBack !== "ninfer";
        llmPill.textContent = `Checking ${lbl}…`;
        llmPill.className = "r2-st-pill";
        try {
            await fetch(LLM_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ backend: nextBack }),
            });
            await loadLlmSettings({ quiet: true });
        } catch (_) { /* */ }
    }
    llmBackSel.addEventListener("change", () => switchLlmBackend(llmBackSel.value));
    cfgBackSel.addEventListener("change", () => switchLlmBackend(cfgBackSel.value));

    async function loadLlmSettings({ quiet = true } = {}) {
        if (typeof fetch !== "function") return null;
        const mySeq = ++llmLoadSeq;
        try {
            const r = await fetch(LLM_URL);
            const j = await r.json();
            if (!j.ok || mySeq !== llmLoadSeq) return null;
            llmLoaded = true;
            const backs = Array.isArray(j.backends) && j.backends.length
                ? j.backends
                : [{ id: "lmstudio", label: "LM Studio", program: false }, { id: "ninfer", label: "nInfer", program: true }];
            cfgBackSel.textContent = "";
            for (const b of backs) {
                const o = el("option", null, b.label || b.id);
                o.value = b.id;
                cfgBackSel.appendChild(o);
            }
            const activeBack = j.backend || "lmstudio";
            cfgBackSel.value = activeBack;
            llmBackSel.value = activeBack;
            cfgUrlInp.value = j.server_url || "";
            cfgModelInp.value = j.model || "";
            cfgModelInp.placeholder = activeBack === "ninfer"
                ? "model id (auto after Start; blank = auto)"
                : "model id (optional on LM Studio)";
            cfgKeepWarmChk.checked = j.keep_warm !== false;
            cfgUnloadChk.checked = j.unload_on_run !== false;
            const curPaths = (j.server_paths && j.server_paths[activeBack]) || {};
            const hasProg = (backs.find((b) => b.id === activeBack)?.program) || activeBack === "ninfer";
            cfgPathRow.hidden = !hasProg;
            cfgExeInp.value = curPaths.exe || "";
            cfgExeInp.placeholder = curPaths.found_exe
                ? `Auto-detected: ${curPaths.found_exe}`
                : "nInfer exe path (e.g. C:\\ninfer\\ninfer-serve.exe)";
            cfgModelFileInp.value = curPaths.model_file || "";
            const ctxVal = String(curPaths.ctx_size || j.ctx_size || 65536);
            if (!Array.from(cfgCtxSel.options || cfgCtxSel.children || []).some((o) => o.value === ctxVal)) {
                const co = el("option", null, `${ctxVal} ctx (custom)`);
                co.value = ctxVal;
                cfgCtxSel.appendChild(co);
            }
            cfgCtxSel.value = ctxVal;

            cfgModelPick.textContent = "";
            const list = Array.isArray(j.models) ? j.models : [];
            const ph = el("option", null, list.length ? "— Pick loaded model —" : "— No models listed —");
            ph.value = "";
            cfgModelPick.appendChild(ph);
            for (const m of list) {
                const mid = typeof m === "string" ? m : (m?.id || "");
                if (!mid) continue;
                const mark = m?.loaded === true ? "● " : (m?.loaded === false ? "○ " : "");
                const o = el("option", null, mark + mid);
                o.value = mid;
                cfgModelPick.appendChild(o);
            }

            llmState = {
                running: Boolean(j.running),
                online: Boolean(j.online),
                backend: activeBack,
                backend_label: j.backend_label || (activeBack === "ninfer" ? "nInfer" : "LM Studio"),
                model: j.model || "",
                startup_error: j.startup_error || "",
            };
            paintLlmBar();
            if (!quiet) {
                const lbl = llmState.backend_label;
                if (j.online) {
                    setStatus(conceptStatus, `${lbl} online (${j.model || "auto"}).`, "hint");
                } else {
                    setStatus(conceptStatus, `${lbl} saved (${j.server_url}), currently offline.`, "hint");
                }
            }
            return j;
        } catch (_) {
            return null;
        }
    }

    async function saveLlmSettings({ quiet = false } = {}) {
        try {
            const activeBack = cfgBackSel.value || llmBackSel.value || "lmstudio";
            const patch = {
                backend: activeBack,
                server_url: cfgUrlInp.value.trim(),
                model: cfgModelInp.value.trim(),
                keep_warm: cfgKeepWarmChk.checked,
                unload_on_run: cfgUnloadChk.checked,
            };
            if (activeBack === "ninfer" || !cfgPathRow.hidden) {
                const ctxNum = Number(cfgCtxSel.value) || 65536;
                patch.ctx_size = ctxNum;
                patch.servers = {
                    [activeBack]: {
                        exe: cfgExeInp.value.trim(),
                        model_file: cfgModelFileInp.value.trim(),
                        ctx_size: ctxNum,
                    },
                };
            }
            const r = await fetch(LLM_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(patch),
            });
            const j = await r.json();
            if (!j.ok) {
                setStatus(conceptStatus, j.error || "Failed to save LLM settings.", "error");
                return false;
            }
            await loadLlmSettings({ quiet });
            return true;
        } catch (err) {
            setStatus(conceptStatus, String(err), "error");
            return false;
        }
    }

    async function toggleLlmServer(action) {
        const btn = action === "start" ? llmStartBtn : llmStopBtn;
        btn.disabled = true;
        try {
            if (action === "start" && llmLoaded) {
                const okSave = await saveLlmSettings({ quiet: true });
                if (!okSave) return;
            }
            if (action === "stop" && llmState.backend !== "ninfer") {
                setStatus(conceptStatus, "Unloading LM Studio model from VRAM...", "hint");
                await unloadWriterForGpu();
                await loadLlmSettings({ quiet: true });
                setStatus(conceptStatus, "LM Studio model unloaded.", "hint");
                return;
            }
            setStatus(conceptStatus, action === "start" ? "Starting nInfer writer..." : "Stopping nInfer writer...", "hint");
            const reqBody = { action };
            if (action === "start" && llmLoaded) {
                if (cfgModelFileInp.value.trim()) reqBody.model_file = cfgModelFileInp.value.trim();
                if (cfgCtxSel.value) reqBody.ctx_size = Number(cfgCtxSel.value);
            }
            const r = await fetch(LLM_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(reqBody),
            });
            const j = await r.json();
            if (!j.ok) {
                await loadLlmSettings({ quiet: true });
                setStatus(conceptStatus, j.error || j.note || `Failed to ${action} writer.`, "error");
                return;
            }
            if (action === "stop") {
                await loadLlmSettings({ quiet: true });
                setStatus(conceptStatus, j.note || "Stopped nInfer writer.", "hint");
                return;
            }
            if (j.running) {
                await loadLlmSettings({ quiet: true });
                setStatus(conceptStatus, `${llmState.backend_label || "Writer"} Ready!`, "hint");
                return;
            }
            llmPill.textContent = "Starting nInfer…";
            setStatus(conceptStatus, j.note || "Starting nInfer... waiting for model load (~15-30s).", "hint");
            for (let i = 0; i < 45; i++) {
                await new Promise((res) => setTimeout(res, 1500));
                const st = await loadLlmSettings({ quiet: true });
                if (st?.running || st?.online) {
                    setStatus(conceptStatus, `${llmState.backend_label || "Writer"} Ready!`, "hint");
                    return;
                }
                if (st?.startup_error) {
                    setStatus(conceptStatus, `nInfer stopped during startup: ${st.startup_error}`, "error");
                    return;
                }
            }
            setStatus(conceptStatus, "Timed out waiting for nInfer — check server.err in your nInfer folder.", "error");
        } catch (err) {
            setStatus(conceptStatus, String(err), "error");
        } finally {
            paintLlmBar();
        }
    }

    function countLyricMetrics(txt) {
        let lines = 0;
        let secs = 0;
        for (const rawLn of String(txt || "").split(/\r?\n/)) {
            const trimmed = rawLn.trim();
            if (!trimmed) continue;
            if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
                secs += 1;
                continue;
            }
            if (/[A-Za-z0-9\u00C0-\u024F\u0400-\u04FF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]/.test(trimmed)) {
                lines += 1;
            }
        }
        return { lines, secs, estSec: lines > 0 ? Math.max(25, Math.round(lines * 4.2)) : 0 };
    }

    function expectedLinesForDuration(durSec, vocalMode) {
        if (String(vocalMode || "auto").toLowerCase() === "instrumental") return 0;
        const d = Number(durSec) || 105;
        if (d <= 52) return 10;
        if (d <= 75) return 16;
        if (d <= 97) return 20;
        if (d <= 112) return 24;
        if (d <= 135) return 30;
        if (d <= 165) return 36;
        return 42;
    }

    const ideaRow = el("div", "r2-st-row");
    const ideaInput = el("input", "r2-st-input");
    ideaInput.type = "text";
    ideaInput.placeholder = "Describe MV vibe / story (e.g. '2AM neon diner breakup duet, rain on glass, dark synthwave 108 BPM')";
    ideaInput.value = state.idea || "";
    ideaInput.addEventListener("input", () => {
        state.idea = ideaInput.value;
        saveState();
    });

    const aspectSel = el("select", "r2-st-sel");
    aspectSel.title = "MV frame aspect ratio";
    for (const asp of ["16:9", "9:16", "1:1", "4:3", "3:4"]) {
        const opt = el("option", null, asp);
        opt.value = asp;
        aspectSel.appendChild(opt);
    }
    aspectSel.value = state.aspect || "16:9";
    aspectSel.addEventListener("change", () => {
        state.aspect = aspectSel.value;
        saveState();
        syncDimPreview();
    });

    const durSel = el("select", "r2-st-sel");
    durSel.title = "Target song duration — scales lyric section count, sung line budget, and YuE2 max_seconds";
    for (const [secVal, lbl] of [
        [45, "~45 s (Hook)"],
        [60, "~60 s (Short)"],
        [90, "~90 s (Std)"],
        [105, "~105 s (MV)"],
        [120, "~120 s (Full)"],
        [150, "~150 s (Long)"],
        [180, "~180 s (Epic)"],
    ]) {
        const opt = el("option", null, lbl);
        opt.value = String(secVal);
        durSel.appendChild(opt);
    }
    durSel.value = String(state.duration_target_s || 105);
    durSel.addEventListener("change", () => {
        state.duration_target_s = Number(durSel.value) || 105;
        saveState();
        syncLyricsMetrics();
    });

    const langSel = el("select", "r2-st-sel");
    langSel.title = "Song & lyric language preference";
    for (const [lVal, lLbl] of [
        ["auto", "Lang: Auto"],
        ["English", "English"],
        ["Japanese", "Japanese (日本語)"],
        ["Korean", "Korean (한국어)"],
        ["Chinese", "Chinese (中文)"],
        ["Spanish", "Spanish (Español)"],
        ["French", "French (Français)"],
        ["Russian", "Russian (Русский)"],
        ["Portuguese", "Portuguese (Português)"],
        ["Italian", "Italian (Italiano)"],
        ["German", "German (Deutsch)"],
        ["Thai", "Thai (ไทย)"],
    ]) {
        const opt = el("option", null, lLbl);
        opt.value = lVal;
        langSel.appendChild(opt);
    }
    langSel.value = state.language || "auto";
    langSel.addEventListener("change", () => {
        state.language = langSel.value;
        saveState();
    });

    const vocalSel = el("select", "r2-st-sel");
    vocalSel.title = "Vocal delivery preference for YuE2 style & lyrics";
    for (const [vVal, vLbl] of [
        ["auto", "Vocals: Auto"],
        ["female", "Female Lead"],
        ["male", "Male Lead"],
        ["duet", "Duet"],
        ["rap", "Rap / Flow"],
        ["choir", "Choir / Harmonies"],
        ["instrumental", "Instrumental"],
    ]) {
        const opt = el("option", null, vLbl);
        opt.value = vVal;
        vocalSel.appendChild(opt);
    }
    vocalSel.value = state.vocal_mode || "auto";
    vocalSel.addEventListener("change", () => {
        state.vocal_mode = vocalSel.value;
        saveState();
        syncLyricsMetrics();
    });

    const vibePresetSel = el("select", "r2-st-sel");
    vibePresetSel.title = "1-click starting MV genre/BPM preset (fills Idea, Vocal mode & Aspect)";
    for (const [pid, plbl] of MV_VIBE_PRESETS) {
        const opt = el("option", null, plbl);
        opt.value = pid;
        vibePresetSel.appendChild(opt);
    }
    vibePresetSel.addEventListener("change", () => {
        const hit = MV_VIBE_PRESETS.find((x) => x[0] === vibePresetSel.value)?.[2];
        if (!hit) return;
        state.idea = hit.idea;
        ideaInput.value = hit.idea;
        if (hit.vocal) { state.vocal_mode = hit.vocal; vocalSel.value = hit.vocal; }
        if (hit.aspect) { state.aspect = hit.aspect; aspectSel.value = hit.aspect; }
        if (hit.lang) { state.language = hit.lang; langSel.value = hit.lang; }
        saveState();
        syncLyricsMetrics();
        syncDimPreview();
    });

    const sparkBtn = button("\u2728 Spark Concept & Assets", "Generate rich YuE2 style, duration-scaled lyrics, and cast/plate/prop blueprints with local LLM", () => runIdeate({ lyricsOnly: false }), "h3e-btn h3e-btn-accent");
    const resparkLyricsBtn = button("\u21bb Scale Lyrics", "Rewrite & scale ONLY Style/Lyrics to the chosen timing dropdown (keeps your Card 3 assets untouched)", () => runIdeate({ lyricsOnly: true }));
    ideaRow.append(vibePresetSel, ideaInput, aspectSel, durSel, langSel, vocalSel, sparkBtn, resparkLyricsBtn);
    c1.appendChild(ideaRow);

    const specGrid = el("div", "r2-st-grid2");
    const styleBox = el("div", "r2-st-field");
    styleBox.appendChild(el("label", "r2-st-lbl", "YuE2 Music Style (Language · Genre · Vocals · Instruments · Phrasing · BPM)"));
    const styleArea = el("textarea", "r2-st-area");
    styleArea.rows = 4;
    styleArea.placeholder = "English, nocturnal dark synthwave pop, smoky female lead vocal with airy chorus harmonies, pulsing analog Moog bass, gated-reverb snare, Juno arpeggios, soaring hook, 4/4, 108 BPM";
    styleArea.value = state.song_style || "";
    styleArea.addEventListener("input", () => {
        state.song_style = styleArea.value;
        saveState();
    });
    styleBox.appendChild(styleArea);

    const lyricsBox = el("div", "r2-st-field");
    const lyricsLblRow = el("div", "r2-st-lbl-row");
    lyricsLblRow.appendChild(el("label", "r2-st-lbl", "Tagged Lyrics ([Intro], [Verse], [Pre-Chorus], [Chorus], [Bridge], [Outro])"));
    const lyricsStatsEl = el("span", "r2-st-lyrics-meta", "");
    lyricsLblRow.appendChild(lyricsStatsEl);
    lyricsBox.appendChild(lyricsLblRow);
    const lyricsArea = el("textarea", "r2-st-area");
    lyricsArea.rows = 9;
    lyricsArea.placeholder = "[Intro]\n\n[Verse 1]\nRain streaks down the neon diner glass...\n\n[Pre-Chorus]\nStatic hums beneath the counter light...\n\n[Chorus]\nLeave the midnight sign burning till dawn...";
    lyricsArea.value = state.lyrics || "";
    lyricsArea.addEventListener("input", () => {
        state.lyrics = lyricsArea.value;
        saveState();
        syncLyricsMetrics();
    });
    lyricsBox.appendChild(lyricsArea);
    specGrid.append(styleBox, lyricsBox);
    c1.appendChild(specGrid);

    const conceptStatus = el("div", "r2-st-status");
    conceptStatus.style.display = "none";
    c1.appendChild(conceptStatus);
    root.appendChild(c1);

    function syncLyricsMetrics() {
        const tgtS = Number(state.duration_target_s) || 105;
        const tgtLines = expectedLinesForDuration(tgtS, state.vocal_mode);
        const m = countLyricMetrics(lyricsArea.value);
        if (tgtLines === 0) {
            lyricsStatsEl.textContent = "Instrumental · 0 sung lines";
            lyricsStatsEl.className = "r2-st-lyrics-meta";
            return;
        }
        if (!m.lines) {
            lyricsStatsEl.textContent = `Target: ~${tgtLines} lines for ~${tgtS} s`;
            lyricsStatsEl.className = "r2-st-lyrics-meta";
            return;
        }
        const under = m.lines < Math.round(tgtLines * 0.72);
        lyricsStatsEl.textContent = `${m.lines} lines · ${m.secs} sec(s) · ~${m.estSec}s (target ~${tgtS}s / ${tgtLines}L)`;
        lyricsStatsEl.className = "r2-st-lyrics-meta" + (under ? " is-short" : "");
    }

    async function runIdeate({ lyricsOnly = false } = {}) {
        if (busyConcept) return;
        const txt = String(ideaInput.value || "").trim();
        if (!txt) {
            setStatus(conceptStatus, "Type a short concept or vibe first.", "error");
            return;
        }
        busyConcept = true;
        sparkBtn.disabled = true;
        resparkLyricsBtn.disabled = true;
        const coldWake = !llmState.running && llmState.backend === "ninfer" && state.auto_wake !== false;
        if (coldWake) {
            llmPill.textContent = "Starting nInfer…";
            setStatus(conceptStatus, "Waking nInfer from cold start & writing scaled MV concept (~15-30s)...", "hint");
        } else {
            setStatus(
                conceptStatus,
                lyricsOnly
                    ? `Scaling & rewriting YuE2 style + lyrics for ~${Number(state.duration_target_s) || 105} s...`
                    : `Sparking MV concept, ~${Number(state.duration_target_s) || 105} s lyrics & asset prompts via local LLM...`,
                "hint",
            );
        }
        try {
            const refPlan = readRefs(node);
            const castRows = (refPlan?.refs || []).map((r) => ({
                tag: r.tag || "",
                file: r.file || "",
                desc: r.desc || "",
                retention: r.retention || "",
                subject: r.subject ?? null,
            }));
            const r = await fetch("/h3_ref_chain/mv/ideate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    idea: txt,
                    cast_rows: castRows,
                    aspect: state.aspect || "16:9",
                    duration_target_s: Number(state.duration_target_s) || 105,
                    image_profile: state.image_profile || "qwen_viggle_6step",
                    language: state.language || "auto",
                    vocal_mode: state.vocal_mode || "auto",
                    lyrics_only: Boolean(lyricsOnly),
                    song_style: state.song_style || "",
                    title: state.title || "",
                    auto_wake: state.auto_wake !== false,
                }),
            });
            const j = await r.json();
            if (!j.ok) {
                setStatus(conceptStatus, j.error || "Ideation failed.", "error");
                return;
            }
            if (!lyricsOnly && j.title) state.title = j.title;
            if (j.song_style) state.song_style = j.song_style;
            state.lyrics = j.lyrics || "";
            if (!lyricsOnly && j.brief) state.brief = j.brief;
            styleArea.value = state.song_style;
            lyricsArea.value = state.lyrics;
            briefArea.value = state.brief;
            syncLyricsMetrics();

            const nextAssets = [];
            if (!lyricsOnly) {
                for (const item of j.cast_assets || []) {
                    nextAssets.push({
                        id: uid(),
                        tag: item.tag || "cast",
                        role: "cast",
                        aspect: state.aspect === "16:9" ? "3:4" : (state.aspect || "3:4"),
                        mp: "inherit",
                        prompt: item.prompt || "",
                        ref1: "",
                        ref2: "",
                        seed: 0,
                        preview: null,
                        kept_file: "",
                    });
                }
                for (const item of j.plate_assets || []) {
                    nextAssets.push({
                        id: uid(),
                        tag: item.tag || "plate",
                        role: "plate",
                        section: item.section || "",
                        aspect: state.aspect || "16:9",
                        mp: "inherit",
                        prompt: item.prompt || "",
                        ref1: "",
                        ref2: "",
                        seed: 0,
                        preview: null,
                        kept_file: "",
                    });
                }
                for (const item of j.prop_assets || []) {
                    nextAssets.push({
                        id: uid(),
                        tag: item.tag || "prop",
                        role: "prop",
                        aspect: "1:1",
                        mp: "inherit",
                        prompt: item.prompt || "",
                        ref1: "",
                        ref2: "",
                        seed: 0,
                        preview: null,
                        kept_file: "",
                    });
                }
                if (nextAssets.length) {
                    state.assets = nextAssets;
                    renderAssets();
                }
            }
            saveState();
            syncPipelineStrip();
            const tp = j.timing_plan || {};
            const lyricInfo = tp.sung_lines != null
                ? `${tp.sung_lines} sung lines / ${tp.sections || "?"} sections${tp.bpm ? ` @ ${tp.bpm} BPM` : ""}`
                : "lyrics updated";
            setStatus(
                conceptStatus,
                lyricsOnly
                    ? `Lyrics scaled for ~${tp.target_s || state.duration_target_s} s (${lyricInfo}). Existing assets preserved.`
                    : `Concept ready (${j.title || "MV"}): ${lyricInfo}, ${nextAssets.length} asset prompt(s) added below.`,
                "hint",
            );
        } catch (err) {
            setStatus(conceptStatus, String(err), "error");
        } finally {
            busyConcept = false;
            sparkBtn.disabled = false;
            resparkLyricsBtn.disabled = false;
            loadLlmSettings({ quiet: true });
        }
    }

    /* ====================================================================
     * CARD 2: SONG FORGE & BEAT LOCK (YuE2 + songmap + mv_solver)
     * ==================================================================== */
    const c2 = el("section", "r2-st-card");
    const c2Head = el("div", "r2-st-chead");
    const yueBadge = el("span", "r2-st-pill", "YuE2: checking...");
    c2Head.append(
        el("span", "r2-st-badge", "2"),
        el("span", "r2-st-clabel", "Song Forge & Downbeat Solver"),
        yueBadge,
    );
    c2.appendChild(c2Head);

    const songCtrlRow = el("div", "r2-st-row");
    const songPickSel = el("select", "r2-st-sel r2-st-grow");
    songPickSel.title = "Pick an existing audio track from input/h3_refs/";
    songPickSel.addEventListener("change", () => {
        state.song_file = songPickSel.value;
        saveState();
        syncAudioPreview();
    });

    const uploadInput = el("input");
    uploadInput.type = "file";
    uploadInput.accept = "audio/*,.mp3,.wav,.flac,.ogg,.m4a";
    uploadInput.style.display = "none";
    uploadInput.addEventListener("change", async () => {
        const file = uploadInput.files?.[0];
        if (!file) return;
        const fd = new FormData();
        fd.append("files", file);
        setStatus(songStatus, `Uploading ${file.name} to h3_refs/...`, "hint");
        try {
            const upRes = await fetch("/h3_ref_chain/upload", { method: "POST", body: fd });
            const upJson = await upRes.json();
            const first = upJson?.files?.[0]?.name;
            if (!upRes.ok || !first) {
                throw new Error(upJson?.error || "Upload failed.");
            }
            await fetchCaps(false);
            state.song_file = first;
            songPickSel.value = first;
            saveState();
            syncAudioPreview();
            await runAnalyzeSong();
        } catch (err) {
            setStatus(songStatus, String(err), "error");
        } finally {
            uploadInput.value = "";
        }
    });
    const uploadAudioBtn = button("\u21ea Upload Song", "Upload an .mp3 / .wav / .flac song directly into input/h3_refs/", () => uploadInput.click());

    const songEngineSel = el("select", "r2-st-sel");
    songEngineSel.addEventListener("change", () => {
        state.song_engine = songEngineSel.value;
        saveState();
    });

    const songModeSel = el("select", "r2-st-sel");
    for (const [m, lbl] of [["full", "ABC: Full (Melody+Chords)"], ["melody", "ABC: Melody Only"], ["off", "Direct (No ABC)"]]) {
        const opt = el("option", null, lbl);
        opt.value = m;
        songModeSel.appendChild(opt);
    }
    songModeSel.value = state.song_mode || "full";
    songModeSel.addEventListener("change", () => {
        state.song_mode = songModeSel.value;
        saveState();
    });

    const vocalsChkWrap = el("label", "r2-st-chk");
    const vocalsChk = el("input");
    vocalsChk.type = "checkbox";
    vocalsChk.checked = Boolean(state.vocals_only);
    vocalsChk.addEventListener("change", () => {
        state.vocals_only = vocalsChk.checked;
        saveState();
    });
    vocalsChkWrap.append(vocalsChk, el("span", null, "Vocals Stem"));
    vocalsChkWrap.title = "If pytraveler YuE2-ComfyUI is installed, also separate vocals via RoFormer.";

    const genSongBtn = button("\ud83c\udfb5 Generate Song (YuE2)", "Queue YuE2 song generation on ComfyUI using Style + Lyrics above", () => runGenerateSong());
    songCtrlRow.append(songPickSel, uploadInput, uploadAudioBtn, songEngineSel, songModeSel, vocalsChkWrap, genSongBtn);
    c2.appendChild(songCtrlRow);

    const songAnalyzeRow = el("div", "r2-st-row");
    const audioEl = el("audio", "r2-st-audio");
    audioEl.controls = true;
    const listenWrap = el("label", "r2-st-chk");
    const listenChk = el("input");
    listenChk.type = "checkbox";
    listenChk.checked = Boolean(state.listen);
    listenChk.addEventListener("change", () => {
        state.listen = listenChk.checked;
        saveState();
    });
    listenWrap.append(listenChk, el("span", null, "Listen (Vocals/Lyrics)"));
    listenWrap.title = "Also run vocal stem separation + Whisper lyrics alignment (uses GPU if >=4 GB free VRAM, else CPU with chunk progress). Unchecked = ~1s tempo + beat solver.";

    const analyzeBtn = button("\ud83d\udcca Analyze Beats & Solve Cuts", "Run songmap.py + mv_solver.py on the active audio track", () => runAnalyzeSong());
    const resolveBtn = button("\u21bb Re-Solve Sections", "Recompute cut alignment using your edited section rows below", () => runResolveSections());
    const lockCutsBtn = button("\ud83d\udd12 Lock Song & Cuts \u2192 Chain", "Write master_audio_file, master_audio_start_s, and downbeat-aligned hop durations to the node", () => lockSongAndCuts(), "h3e-btn h3e-btn-accent");
    songAnalyzeRow.append(audioEl, listenWrap, analyzeBtn, resolveBtn, lockCutsBtn);
    c2.appendChild(songAnalyzeRow);

    const songProgWrap = el("div", "r2-st-prog");
    songProgWrap.style.display = "none";
    const songProgTrack = el("div", "r2-st-prog-track");
    const songProgFill = el("div", "r2-st-prog-fill");
    songProgTrack.appendChild(songProgFill);
    const songProgMeta = el("div", "r2-st-prog-meta");
    songProgWrap.append(songProgTrack, songProgMeta);
    c2.appendChild(songProgWrap);

    const songMetaBar = el("div", "r2-st-meta");
    c2.appendChild(songMetaBar);

    const sectionTableWrap = el("div", "r2-st-table-wrap");
    c2.appendChild(sectionTableWrap);

    const hopStripWrap = el("div", "r2-st-hops");
    c2.appendChild(hopStripWrap);

    const songStatus = el("div", "r2-st-status");
    songStatus.style.display = "none";
    c2.appendChild(songStatus);
    root.appendChild(c2);

    function syncAudioPreview() {
        const fn = String(state.song_file || "").trim();
        if (!fn) {
            audioEl.removeAttribute("src");
            audioEl.style.display = "none";
            return;
        }
        audioEl.style.display = "";
        audioEl.src = `/view?filename=${encodeURIComponent(fn)}&type=input&subfolder=h3_refs`;
    }

    function renderSongAnalysis() {
        sectionTableWrap.textContent = "";
        hopStripWrap.textContent = "";
        songMetaBar.textContent = "";
        const sa = state.song_analysis;
        if (!sa) {
            songMetaBar.textContent = "Pick or generate an audio track, then click Analyze Beats & Solve Cuts.";
            return;
        }
        const sol = sa.solved || {};
        const pills = [
            `${sa.bpm || "?"} BPM`,
            `${sa.beats_per_bar || 4}/4`,
            `bar ${sa.bar_s || "?"}s`,
            `end ${sa.ends_on_sound ?? sa.dur ?? "?"}s`,
            `grid: ${sa.grid || "fixed"} (drift ${sa.drift_f ?? 0}f)`,
        ];
        if (sol.ok) {
            const totalS = sol.end_s != null ? sol.end_s : ((sol.total_frames || 0) / 24).toFixed(1);
            pills.push(`start_s=${sol.master_audio_start_s}`);
            pills.push(`worst_cut=${sol.worst_cut_f}f`);
            pills.push(`${(sol.hops || []).length} hops / ${totalS}s`);
        }
        for (const text of pills) {
            songMetaBar.appendChild(el("span", "r2-st-chip", text));
        }

        const secs = Array.isArray(sa.sections) ? sa.sections : [];
        if (secs.length) {
            const tbl = el("table", "r2-st-tbl");
            const thead = el("thead");
            const hr = el("tr");
            for (const h of ["#", "Bar", "Span", "Kind", "Sung", "Lyrics / Reason"]) {
                hr.appendChild(el("th", null, h));
            }
            thead.appendChild(hr);
            tbl.appendChild(thead);

            const tbody = el("tbody");
            secs.forEach((sec, idx) => {
                const tr = el("tr");
                tr.appendChild(el("td", null, String(idx + 1)));

                const barTd = el("td");
                const barIn = el("input", "r2-st-num");
                barIn.type = "number";
                barIn.min = "1";
                barIn.value = String(sec.bar || 1);
                barIn.addEventListener("change", () => {
                    sec.bar = Math.max(1, Number(barIn.value) || 1);
                    saveState();
                });
                barTd.appendChild(barIn);
                tr.appendChild(barTd);

                tr.appendChild(el("td", null, `${sec.from_s ?? "?"}–${sec.to_s ?? "?"}s`));

                const kindTd = el("td");
                const kSel = el("select", "r2-st-sel-sm");
                for (const k of SECTION_KINDS) {
                    const o = el("option", null, k);
                    o.value = k;
                    kSel.appendChild(o);
                }
                kSel.value = SECTION_KINDS.includes(sec.kind) ? sec.kind : "verse";
                kSel.addEventListener("change", () => {
                    sec.kind = kSel.value;
                    saveState();
                });
                kindTd.appendChild(kSel);
                tr.appendChild(kindTd);

                const sungLbl = sec.sung === true ? "SINGS" : (sec.sung === false ? "inst" : "—");
                tr.appendChild(el("td", sec.sung === true ? "is-sung" : "", sungLbl));
                tr.appendChild(el("td", "r2-st-lyric", sec.lyric || sec.why || ""));
                tbody.appendChild(tr);
            });
            tbl.appendChild(tbody);
            sectionTableWrap.appendChild(tbl);
        }

        if (sol.ok && Array.isArray(sol.hops) && sol.hops.length) {
            hopStripWrap.appendChild(el("span", "r2-st-lbl", "Solved Hops:"));
            sol.hops.forEach((h, i) => {
                const durLbl = h.duration || DEFAULT_DURATION_LABELS[h.frames] || `${Math.round((h.frames || 243) / 24)} s`;
                const isRestart = h.kind === "R" || h.kind === "restart";
                const tag = el(
                    "span",
                    "r2-st-hop" + (isRestart ? " is-restart" : ""),
                    `H${i + 1} ${durLbl} [${isRestart ? "R" : "C"}]`,
                );
                const tA = h.song_a ?? h.start_s ?? "?";
                const tB = h.song_b ?? h.end_s ?? "?";
                tag.title = `${tA}s–${tB}s · ${h.frames}f` + (h.section_kind ? ` · ${h.section_kind}` : "") + (h.sung ? " · singing" : "");
                hopStripWrap.appendChild(tag);
            });
        } else if (sol.error) {
            hopStripWrap.appendChild(el("span", "r2-st-err", "Solver: " + sol.error));
        }
    }

    async function runGenerateSong() {
        if (busySong) return;
        const stTxt = String(styleArea.value || "").trim();
        if (!stTxt) {
            setStatus(songStatus, "Write or Spark a YuE2 music style in Card 1 first.", "error");
            return;
        }
        busySong = true;
        genSongBtn.disabled = true;
        setStatus(songStatus, "Queueing YuE2 song generation...", "hint");
        try {
            const res = await runForgeGraph({
                kind: "song",
                engine: state.song_engine || "",
                style: stTxt,
                lyrics: String(lyricsArea.value || ""),
                mode: state.song_mode || "full",
                max_duration: Number(state.duration_target_s) || 120,
                vocals_only: Boolean(state.vocals_only),
                seed: 0,
            }, {
                onStatus: (m) => setStatus(songStatus, m, "hint"),
                onProgress: (v, max) => setStatus(songStatus, `YuE2 sampling ${v}/${max}...`, "hint"),
            });
            const slug = String(state.title || "yue2_song").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "yue2_song";
            const impRes = await fetch("/h3_ref_chain/mv/import_output", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    filename: res.file?.filename || "",
                    subfolder: res.file?.subfolder || "",
                    output_type: res.file?.type || "output",
                    dest_name: `${slug}_${res.meta?.seed || "song"}`,
                    kind: "audio",
                }),
            });
            const impJson = await impRes.json();
            if (!impRes.ok || !impJson.ok) {
                throw new Error(impJson?.error || "Failed importing YuE2 audio into h3_refs.");
            }
            await fetchCaps(false);
            state.song_file = impJson.filename;
            songPickSel.value = impJson.filename;
            saveState();
            syncAudioPreview();
            setStatus(songStatus, `Generated & imported ${impJson.filename}. Analyzing beats...`, "hint");
            await runAnalyzeSong();
        } catch (err) {
            setStatus(songStatus, String(err), "error");
        } finally {
            busySong = false;
            genSongBtn.disabled = false;
        }
    }

    function startSongProgressPoll(fn, initialMsg) {
        const t0 = Date.now();
        songProgWrap.style.display = "";
        songProgFill.style.width = "6%";
        songProgMeta.textContent = initialMsg || "Starting...";
        let stopped = false;
        const tick = async () => {
            if (stopped) return;
            const localSec = ((Date.now() - t0) / 1000).toFixed(0);
            try {
                const sr = await fetch(`/h3_ref_chain/mv/song_map_status?song=${encodeURIComponent(fn)}`, { cache: "no-store" });
                const sj = await sr.json();
                if (!stopped && sj?.ok && sj.stage) {
                    const pct = Math.max(6, Math.min(100, Number(sj.pct) || 8));
                    songProgFill.style.width = `${pct}%`;
                    const elSec = sj.elapsed_s != null ? Number(sj.elapsed_s).toFixed(1) : localSec;
                    const devTag = sj.device ? ` [${sj.device}]` : "";
                    songProgMeta.textContent = `${pct}% · ${elSec}s${devTag} — ${sj.stage}`;
                    setStatus(songStatus, `${sj.stage} (${elSec}s)`, "hint");
                    return;
                }
            } catch (_) { /* offline in mount_test */ }
            if (!stopped) {
                songProgMeta.textContent = `${initialMsg || "Analyzing..."} (${localSec}s)`;
            }
        };
        const id = typeof setInterval === "function" ? setInterval(tick, 600) : 0;
        tick();
        return () => {
            stopped = true;
            if (id && typeof clearInterval === "function") clearInterval(id);
            songProgWrap.style.display = "none";
        };
    }

    async function runAnalyzeSong() {
        const fn = String(state.song_file || songPickSel.value || "").trim();
        if (!fn) {
            setStatus(songStatus, "Pick or upload an audio file first.", "error");
            return;
        }
        analyzeBtn.disabled = true;
        const initMsg = state.listen ? "Running songmap (tempo + vocal listen) & solver..." : "Running songmap tempo analysis & solver...";
        setStatus(songStatus, initMsg, "hint");
        const stopPoll = startSongProgressPoll(fn, initMsg);
        try {
            const r = await fetch("/h3_ref_chain/mv/song_map", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ song: fn, listen: Boolean(state.listen) }),
            });
            const j = await r.json();
            if (!r.ok || !j.ok) {
                setStatus(songStatus, j.error || "Song analysis failed.", "error");
                return;
            }
            state.song_analysis = j;
            saveState();
            renderSongAnalysis();
            syncPipelineStrip();
            setStatus(songStatus, `Analyzed ${j.file}: ${j.bpm} BPM, ${(j.sections || []).length} sections, ${(j.solved?.hops || []).length} solved hops.`, "hint");
        } catch (err) {
            setStatus(songStatus, String(err), "error");
        } finally {
            stopPoll();
            analyzeBtn.disabled = false;
        }
    }

    async function runResolveSections() {
        const sa = state.song_analysis;
        if (!sa || !state.song_file) {
            setStatus(songStatus, "Analyze a song first.", "error");
            return;
        }
        resolveBtn.disabled = true;
        const stopPoll = startSongProgressPoll(state.song_file, "Re-solving downbeat cuts...");
        try {
            const r = await fetch("/h3_ref_chain/mv/solve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    song: state.song_file,
                    sections: sa.sections || [],
                    listen: Boolean(state.listen),
                }),
            });
            const j = await r.json();
            if (!r.ok || !j.ok) {
                setStatus(songStatus, j.error || "Re-solve failed.", "error");
                return;
            }
            state.song_analysis = j;
            saveState();
            renderSongAnalysis();
            syncPipelineStrip();
            setStatus(songStatus, `Re-solved ${(j.solved?.hops || []).length} hops (worst cut ${j.solved?.worst_cut_f ?? "?"}f, start_s=${j.solved?.master_audio_start_s ?? 0}).`, "hint");
        } catch (err) {
            setStatus(songStatus, String(err), "error");
        } finally {
            stopPoll();
            resolveBtn.disabled = false;
        }
    }

    function resolveAssetRefsForSection(secKind) {
        const sk = String(secKind || "").toLowerCase();
        const plan = readRefs(node);
        const railRefs = Array.isArray(plan?.refs) ? plan.refs.filter((r) => r.file) : [];
        const picks = [];
        const pushTag = (t) => {
            const clean = String(t || "").trim().replace(/^@/, "");
            if (clean && !picks.includes(clean)) picks.push(clean);
        };
        for (const a of (state.assets || [])) {
            if (a.role === "cast" && (a.kept_file || a.baked_refmod)) pushTag(a.tag);
        }
        for (const r of railRefs) {
            if (r.subject != null) pushTag(r.tag);
        }
        const keptPlates = (state.assets || []).filter((a) => a.role === "plate" && (a.kept_file || a.baked_refmod));
        const matchedPlate = keptPlates.find((p) => {
            const ps = String(p.section || "").toLowerCase();
            if (!ps || !sk) return false;
            if (ps.includes(sk)) return true;
            if (sk === "drop" && ps.includes("chorus")) return true;
            if (sk === "pre_chorus" && (ps.includes("verse") || ps.includes("chorus"))) return true;
            return false;
        }) || keptPlates[0] || null;
        if (matchedPlate) {
            pushTag(matchedPlate.tag);
        } else {
            const railPlate = railRefs.find((r) => r.subject == null && r.retention !== "prop");
            if (railPlate) pushTag(railPlate.tag);
        }
        for (const a of (state.assets || [])) {
            if (a.role === "prop" && (a.kept_file || a.baked_refmod)) pushTag(a.tag);
        }
        for (const r of railRefs) {
            if (r.retention === "prop") pushTag(r.tag);
        }
        return picks;
    }

    function lockSongAndCuts() {
        const sa = state.song_analysis;
        const hops = sa?.solved?.hops;
        if (!state.song_file || !Array.isArray(hops) || !hops.length) {
            setStatus(songStatus, "Analyze & solve a song first before locking cuts.", "error");
            return false;
        }
        commitWidget("master_audio_file", state.song_file);
        commitWidget("master_audio_start_s", Number(sa.solved.master_audio_start_s || 0));

        const sectionsList = Array.isArray(sa.sections) ? sa.sections : [];
        const existingShots = readPlan(node).shots || [];
        const nextShots = hops.map((h, idx) => {
            const prev = existingShots[idx] || {};
            const durLbl = h.duration || DEFAULT_DURATION_LABELS[h.frames] || durationOf(node, prev) || "10 s";
            const isRestart = h.kind === "R" || h.kind === "restart";
            const kindAnchor = isRestart ? "restart" : (idx === 0 ? "restart" : "continuous");
            const secName = h.section_kind || h.section || "";
            const secNote = secName ? `[${secName}${h.sung ? " · SINGS" : ""}] ` : "";
            const tA = Number(h.song_a ?? h.start_s ?? 0);
            const tB = Number(h.song_b ?? h.end_s ?? (tA + 8));
            const secHit = sectionsList.find((s) => Number(s.from_s || 0) <= tA + 1.5 && Number(s.to_s || 0) >= tA + 0.2)
                || sectionsList.find((s) => String(s.kind || "").toLowerCase() === String(secName || "").toLowerCase());
            const lyricCue = String(secHit?.lyric || "").trim();
            const autoRefs = resolveAssetRefsForSection(secName);
            const castLead = autoRefs.find((t) => (state.assets || []).some((a) => a.tag === t && a.role === "cast")) || autoRefs[0] || "";
            const whoStr = castLead ? `@${castLead}` : "Performer";
            const singNote = h.sung
                ? `${whoStr} sings in rhythm${lyricCue ? ` ("${lyricCue}")` : ""}.`
                : `${whoStr} performs kinetic instrumental choreography matching the beat.`;
            const useRefs = (Array.isArray(prev.refs) && prev.refs.length) ? prev.refs : autoRefs;
            return {
                id: prev.id || `mv_${idx + 1}`,
                duration: durLbl,
                anchor: kindAnchor,
                beat: String(prev.beat || "").trim() || `${secNote}${singNote}`,
                ...(useRefs.length ? { refs: useRefs } : {}),
                ...(prev.directives ? { directives: prev.directives } : {}),
            };
        });
        writePlan(node, nextShots);
        node.properties.h3_editor_mode = "shots";
        onChange?.();
        syncPipelineStrip();
        setStatus(
            songStatus,
            `Locked ${state.song_file} @ ${sa.solved.master_audio_start_s}s and ${nextShots.length} downbeat-aligned hops (with section @refs) onto the node!`,
            "hint",
        );
        return true;
    }

    /* ====================================================================
     * CARD 3: VISUAL ASSET FORGE (Sheets, Plates, Props)
     * ==================================================================== */
    const c3 = el("section", "r2-st-card");
    const c3Head = el("div", "r2-st-chead");
    const imgProfSel = el("select", "r2-st-sel");
    imgProfSel.title = "Image Forge Engine Profile (uses local models already on disk)";
    imgProfSel.addEventListener("change", () => {
        state.image_profile = imgProfSel.value;
        saveState();
        syncProfileNote();
        syncDimPreview();
    });
    const imgMpLbl = el("span", "r2-st-lbl", "Resolution:");
    const imgMpSel = el("select", "r2-st-sel");
    imgMpSel.title = "Target megapixel budget for Visual Asset Forge (Auto uses 3 MP on RedQW2.1 Unlocked, 4 MP on H3-Image/P-H3-Image, and 1 MP on fast Turbo models). Each asset card can also override this individually.";
    for (const [val, lbl] of IMAGE_MP_STOPS) {
        const o = el("option", null, lbl);
        o.value = val;
        imgMpSel.appendChild(o);
    }
    imgMpSel.value = String(state.image_mp ?? "0");
    imgMpSel.addEventListener("change", () => {
        state.image_mp = imgMpSel.value;
        saveState();
        syncDimPreview();
    });
    const imgDimBadge = el("span", "r2-st-chip r2-st-dim", "");
    const imgProfNote = el("span", "r2-st-cnote");
    c3Head.append(
        el("span", "r2-st-badge", "3"),
        el("span", "r2-st-clabel", "Visual Asset Forge"),
        imgProfSel,
        imgMpLbl,
        imgMpSel,
        imgDimBadge,
        imgProfNote,
    );
    c3.appendChild(c3Head);

    const addAssetBar = el("div", "r2-st-row");
    const bakeCastBtn = button("⚡ Bake Kept Cast → v5 Bundle", "Bake all kept Cast Sheet cards into a single multi-angle v5 RefMod bundle (native aspect ratios, zero distortion) and attach to Refs", async () => {
        const castAssets = (state.assets || []).filter((a) => a.role === "cast" && a.kept_file);
        if (!castAssets.length) {
            setStatus(conceptStatus, "Keep at least one Cast Sheet first (✓ Keep → Refs) to bake a cast bundle.", "error");
            return;
        }
        const slug = String(state.title || "cast").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "cast";
        const modName = `${slug}_cast`;
        bakeCastBtn.disabled = true;
        setStatus(conceptStatus, `Baking ${castAssets.length}-still v5 RefMod bundle "${modName}"...`, "hint");
        try {
            const stills = [...new Set(castAssets.map((a) => a.kept_file))];
            const desc = castAssets.map((a) => String(a.prompt || "").trim()).filter(Boolean)[0] || "";
            const res = await runForgeGraph({
                kind: "refmod",
                name: modName,
                stills,
                description: desc,
                layout: "separate_pictures",
                role: "identity",
                default_step_curve: "full",
                subject_mask: "auto_rembg",
                background_mode: "blur_bg",
                fit_mode: "crop",
            }, {
                onStatus: (m) => setStatus(conceptStatus, m, "hint"),
            });
            const finalName = res.refmod_name || modName;
            upsertRefPlanRow(modName, finalName, "cast", desc, { source: "refmod" });
            if (typeof window !== "undefined") {
                window.dispatchEvent?.(new CustomEvent("htc:refmods-changed"));
            }
            setStatus(conceptStatus, `Baked v5 RefMod "${finalName}" (${stills.length} angle(s)) and wired @${modName} to Refs!`, "hint");
        } catch (err) {
            setStatus(conceptStatus, String(err), "error");
        } finally {
            bakeCastBtn.disabled = false;
        }
    });
    let busyBatchForge = false;
    const paintMissingBtn = button("\ud83c\udfa8 Paint Missing", "Sequentially paint all unpainted asset cards below using the selected profile", async () => {
        if (busyBatchForge) return;
        const todo = (state.assets || []).filter((a) => String(a.prompt || "").trim() && !a.preview?.filename && !a.kept_file);
        if (!todo.length) {
            setStatus(conceptStatus, "All asset cards already have previews or kept files.", "hint");
            return;
        }
        busyBatchForge = true;
        paintMissingBtn.disabled = true;
        keepAllBtn.disabled = true;
        try {
            let doneN = 0;
            for (const a of todo) {
                doneN += 1;
                setStatus(conceptStatus, `Painting asset ${doneN}/${todo.length}: @${a.tag || "asset"}...`, "hint");
                const refs = [a.ref1, a.ref2].filter(Boolean);
                const mpChoice = (a.mp && a.mp !== "inherit")
                    ? (Number(a.mp) || 0)
                    : (Number(imgMpSel.value || state.image_mp || 0) || 0);
                const res = await runForgeGraph({
                    kind: "image",
                    profile_id: imgProfSel.value || state.image_profile || "qwen_viggle_6step",
                    prompt: a.prompt,
                    ref_files: refs,
                    aspect: a.aspect || "16:9",
                    megapixels: mpChoice,
                    seed: Number(a.seed) || 0,
                    filename_prefix: `mv_forge/${(a.tag || "asset").replace(/[^a-zA-Z0-9_-]/g, "_")}`,
                }, {
                    onStatus: (m) => setStatus(conceptStatus, `[@${a.tag}] ${m}`, "hint"),
                });
                a.preview = res.file;
                a.seed = res.meta?.seed || 0;
                saveState();
                renderAssets();
            }
            setStatus(conceptStatus, `Painted ${todo.length} asset(s)! Click "✓ Keep All → Refs" to wire them into the chain.`, "hint");
        } catch (err) {
            setStatus(conceptStatus, String(err), "error");
        } finally {
            busyBatchForge = false;
            paintMissingBtn.disabled = false;
            keepAllBtn.disabled = false;
            syncPipelineStrip();
        }
    });

    const keepAllBtn = button("\u2713 Keep All \u2192 Refs", "Import every painted preview into input/h3_refs/, Reference Bible, and the Refs rail", async () => {
        if (busyBatchForge) return;
        const ready = (state.assets || []).filter((a) => a.preview?.filename && !a.kept_file);
        if (!ready.length) {
            setStatus(conceptStatus, "Paint at least one asset preview first (or all painted assets are already kept).", "hint");
            return;
        }
        busyBatchForge = true;
        paintMissingBtn.disabled = true;
        keepAllBtn.disabled = true;
        try {
            let keptN = 0;
            for (const a of ready) {
                keptN += 1;
                setStatus(conceptStatus, `Keeping ${keptN}/${ready.length} (@${a.tag}) into h3_refs/ & Refs rail...`, "hint");
                const r = await fetch("/h3_ref_chain/mv/import_output", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        filename: a.preview.filename,
                        subfolder: a.preview.subfolder || "",
                        output_type: a.preview.type || "output",
                        dest_name: `${a.tag || "asset"}.png`,
                        kind: "image",
                        tag: a.tag || "asset",
                        desc: a.prompt || "",
                        role: a.role || "cast",
                        register_bible: true,
                    }),
                });
                const j = await r.json();
                if (!r.ok || !j.ok) throw new Error(j.error || `Failed importing @${a.tag}`);
                a.kept_file = j.filename;
                saveState();
                upsertRefPlanRow(a.tag, j.filename, a.role, a.prompt || "");
            }
            await fetchCaps(false);
            renderAssets();
            setStatus(conceptStatus, `Kept & wired ${keptN} asset(s) to Refs & Reference Bible!`, "hint");
        } catch (err) {
            setStatus(conceptStatus, String(err), "error");
        } finally {
            busyBatchForge = false;
            paintMissingBtn.disabled = false;
            keepAllBtn.disabled = false;
            syncPipelineStrip();
        }
    });

    addAssetBar.append(
        button("+ Cast Sheet", "Add a character sheet generator card", () => addAsset("cast")),
        button("+ Location Plate", "Add an empty camera-first location plate generator card", () => addAsset("plate")),
        button("+ Key Prop", "Add an isolated prop sheet generator card", () => addAsset("prop")),
        paintMissingBtn,
        keepAllBtn,
        el("span", "r2-st-spacer"),
        bakeCastBtn,
    );
    c3.appendChild(addAssetBar);

    const assetListEl = el("div", "r2-st-assets");
    c3.appendChild(assetListEl);
    root.appendChild(c3);

    const assetDimListeners = [];

    function activeProfileObj() {
        return (caps?.image_profiles || []).find((x) => x.id === (imgProfSel.value || state.image_profile)) || null;
    }

    function syncDimPreview() {
        const profObj = activeProfileObj();
        const d = previewImageDims(profObj, state.aspect || "16:9", imgMpSel.value || state.image_mp || "0");
        imgDimBadge.textContent = `${state.aspect || "16:9"}: ${d.label}`;
        imgDimBadge.title = "Preview output pixel resolution for the selected profile & MP setting";
        for (const fn of assetDimListeners) fn();
    }

    function syncProfileNote() {
        const p = activeProfileObj();
        if (!p) {
            imgProfNote.textContent = "";
            return;
        }
        imgProfNote.textContent = p.ready
            ? p.note
            : `Not ready — missing: ${(p.missing || []).join(", ")}`;
    }

    function addAsset(role) {
        const count = (state.assets || []).filter((a) => a.role === role).length + 1;
        state.assets.push({
            id: uid(),
            tag: `${role}_${count}`,
            role,
            aspect: role === "cast" ? "3:4" : (role === "prop" ? "1:1" : (state.aspect || "16:9")),
            mp: "inherit",
            prompt: "",
            ref1: "",
            ref2: "",
            seed: 0,
            preview: null,
            kept_file: "",
        });
        saveState();
        renderAssets();
    }

    function upsertRefPlanRow(tag, filename, role, desc, { source = "image", stepCurve = "full" } = {}) {
        const plan = readRefs(node);
        const refs = Array.isArray(plan?.refs) ? [...plan.refs] : [];
        const subjects = (plan?.subjects && typeof plan.subjects === "object") ? { ...plan.subjects } : {};
        const cleanTag = String(tag || "").toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_|_$/g, "") || "ref";
        const retention = role === "prop" ? "prop" : (role === "plate" ? "reference" : "fully_preserved");
        const existingIdx = refs.findIndex((r) => String(r.tag || "").toLowerCase() === cleanTag);
        const modFields = source === "refmod"
            ? { source: "refmod", ...(stepCurve && stepCurve !== "full" ? { step_curve: stepCurve } : {}) }
            : {};
        let assignedSubj = null;
        if (existingIdx >= 0) {
            assignedSubj = refs[existingIdx].subject ?? null;
            if (role === "cast" && assignedSubj == null) {
                assignedSubj = refs.filter((r) => r.subject != null).length + 1;
            }
            refs[existingIdx] = {
                ...refs[existingIdx],
                file: filename,
                subject: assignedSubj,
                retention: refs[existingIdx].retention || retention,
                desc: refs[existingIdx].desc || desc,
                ...modFields,
            };
        } else {
            assignedSubj = role === "cast" ? (refs.filter((r) => r.subject != null).length + 1) : null;
            refs.push({
                tag: cleanTag,
                file: filename,
                slot: refs.length + 1,
                subject: assignedSubj,
                retention,
                desc,
                ...modFields,
            });
        }
        if (assignedSubj != null) {
            const sk = String(assignedSubj);
            const curS = subjects[sk] || {};
            if (!curS.locked && desc) {
                subjects[sk] = {
                    name: curS.name || cleanTag.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()),
                    locked: String(desc).slice(0, 260),
                    context: curS.context || "",
                };
            }
        }
        writeRefs(node, { ...plan, refs, subjects });
        onChange?.();
        syncPipelineStrip();
    }

    function renderAssets() {
        assetListEl.textContent = "";
        assetDimListeners.length = 0;
        const list = state.assets || [];
        if (!list.length) {
            assetListEl.appendChild(el("div", "r2-st-empty", "No asset cards yet — click ✨ Spark Concept above or + Cast Sheet / + Location Plate."));
            return;
        }
        const imgChoices = caps?.media?.image || [];

        list.forEach((asset, idx) => {
            const box = el("div", "r2-st-asset");
            const head = el("div", "r2-st-row");

            const tagIn = el("input", "r2-st-tag");
            tagIn.type = "text";
            tagIn.value = asset.tag || "";
            tagIn.placeholder = "tag";
            tagIn.addEventListener("input", () => {
                asset.tag = tagIn.value;
                saveState();
            });

            const roleSel = el("select", "r2-st-sel-sm");
            for (const rName of ["cast", "plate", "prop"]) {
                const o = el("option", null, rName);
                o.value = rName;
                roleSel.appendChild(o);
            }
            roleSel.value = asset.role || "cast";
            roleSel.addEventListener("change", () => {
                asset.role = roleSel.value;
                saveState();
            });

            const aspSel = el("select", "r2-st-sel-sm");
            for (const aName of ["16:9", "9:16", "1:1", "3:4", "4:3", "match"]) {
                const o = el("option", null, aName === "match" ? "Match Ref 1" : aName);
                o.value = aName;
                aspSel.appendChild(o);
            }
            aspSel.value = asset.aspect || "16:9";
            aspSel.addEventListener("change", () => {
                asset.aspect = aspSel.value;
                saveState();
                refreshAssetDim();
            });

            const assetMpSel = el("select", "r2-st-sel-sm");
            assetMpSel.title = "Target megapixels for this card (MP: Studio inherits Card 3's Resolution dropdown)";
            assetMpSel.appendChild(el("option", null, "MP: Studio")).value = "inherit";
            for (const [mpVal, mpLbl] of IMAGE_MP_STOPS) {
                const o = el("option", null, mpLbl);
                o.value = mpVal;
                assetMpSel.appendChild(o);
            }
            assetMpSel.value = asset.mp != null ? String(asset.mp) : "inherit";
            assetMpSel.addEventListener("change", () => {
                asset.mp = assetMpSel.value;
                saveState();
                refreshAssetDim();
            });

            const assetDimChip = el("span", "r2-st-chip r2-st-dim", "");
            function refreshAssetDim() {
                const mpRaw = (asset.mp && asset.mp !== "inherit") ? asset.mp : (imgMpSel.value || state.image_mp || "0");
                const dims = previewImageDims(activeProfileObj(), asset.aspect || "16:9", mpRaw);
                assetDimChip.textContent = dims.label;
                assetDimChip.title = "Output dimensions when Paint is clicked";
            }
            assetDimListeners.push(refreshAssetDim);
            refreshAssetDim();

            const ref1Sel = el("select", "r2-st-sel-sm");
            ref1Sel.title = "Optional <Picture 1> source image from h3_refs/ for multi-ref editing";
            ref1Sel.appendChild(el("option", null, "Ref 1: None")).value = "";
            for (const fn of imgChoices) {
                const o = el("option", null, fn);
                o.value = fn;
                ref1Sel.appendChild(o);
            }
            ref1Sel.value = asset.ref1 || "";
            ref1Sel.addEventListener("change", () => {
                asset.ref1 = ref1Sel.value;
                saveState();
            });

            const ref2Sel = el("select", "r2-st-sel-sm");
            ref2Sel.title = "Optional <Picture 2> reference image from h3_refs/";
            ref2Sel.appendChild(el("option", null, "Ref 2: None")).value = "";
            for (const fn of imgChoices) {
                const o = el("option", null, fn);
                o.value = fn;
                ref2Sel.appendChild(o);
            }
            ref2Sel.value = asset.ref2 || "";
            ref2Sel.addEventListener("change", () => {
                asset.ref2 = ref2Sel.value;
                saveState();
            });

            const delBtn = button("\u2715", "Remove this asset card", () => {
                state.assets.splice(idx, 1);
                saveState();
                renderAssets();
            });
            head.append(tagIn, roleSel, aspSel, assetMpSel, assetDimChip, ref1Sel, ref2Sel, delBtn);

            const bodyRow = el("div", "r2-st-asset-body");
            const promptArea = el("textarea", "r2-st-area");
            promptArea.rows = 3;
            promptArea.placeholder = "Describe the sheet, empty camera-first plate, or prop...";
            promptArea.value = asset.prompt || "";
            promptArea.addEventListener("input", () => {
                asset.prompt = promptArea.value;
                saveState();
            });

            const sideCol = el("div", "r2-st-asset-side");
            const thumb = el("img", "r2-st-thumb");
            thumb.alt = asset.tag || "preview";
            if (asset.preview?.filename) {
                thumb.src = viewUrl(asset.preview);
            } else if (asset.kept_file) {
                thumb.src = `/view?filename=${encodeURIComponent(asset.kept_file)}&type=input&subfolder=h3_refs`;
            } else {
                thumb.style.display = "none";
            }

            const actRow = el("div", "r2-st-row");
            const stLine = el("div", "r2-st-mini-status");
            const paintBtn = button("\ud83c\udfa8 Paint", "Generate this asset using the selected Image Forge profile & MP resolution", async () => {
                paintBtn.disabled = true;
                stLine.textContent = "Queueing...";
                try {
                    const refs = [asset.ref1, asset.ref2].filter(Boolean);
                    const mpChoice = (asset.mp && asset.mp !== "inherit")
                        ? (Number(asset.mp) || 0)
                        : (Number(imgMpSel.value || state.image_mp || 0) || 0);
                    const res = await runForgeGraph({
                        kind: "image",
                        profile_id: imgProfSel.value || state.image_profile || "qwen_viggle_6step",
                        prompt: promptArea.value,
                        ref_files: refs,
                        aspect: asset.aspect || "16:9",
                        megapixels: mpChoice,
                        seed: Number(asset.seed) || 0,
                        filename_prefix: `mv_forge/${(asset.tag || "asset").replace(/[^a-zA-Z0-9_-]/g, "_")}`,
                    }, {
                        onStatus: (m) => { stLine.textContent = m; },
                        onProgress: (v, max) => { stLine.textContent = `Step ${v}/${max}`; },
                    });
                    asset.preview = res.file;
                    asset.seed = res.meta?.seed || 0;
                    saveState();
                    thumb.src = viewUrl(res.file);
                    thumb.style.display = "";
                    keepBtn.disabled = false;
                    bakeBtn.disabled = false;
                    const wh = (res.meta?.width && res.meta?.height) ? `${res.meta.width}×${res.meta.height}, ` : "";
                    stLine.textContent = `Ready (${wh}${res.meta?.steps || "?"} steps)`;
                } catch (err) {
                    stLine.textContent = String(err);
                } finally {
                    paintBtn.disabled = false;
                }
            });

            const keepBtn = button(
                asset.kept_file ? `\u2713 Kept (${asset.kept_file})` : "\u2713 Keep \u2192 Refs",
                "Import into input/h3_refs/, register in Reference Bible, and attach to Refs rail",
                async () => {
                    if (!asset.preview?.filename) return;
                    keepBtn.disabled = true;
                    stLine.textContent = "Importing to h3_refs/...";
                    try {
                        const r = await fetch("/h3_ref_chain/mv/import_output", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                filename: asset.preview.filename,
                                subfolder: asset.preview.subfolder || "",
                                output_type: asset.preview.type || "output",
                                dest_name: `${asset.tag || "asset"}.png`,
                                kind: "image",
                                tag: asset.tag || "asset",
                                desc: promptArea.value,
                                role: asset.role || "cast",
                                register_bible: true,
                            }),
                        });
                        const j = await r.json();
                        if (!r.ok || !j.ok) throw new Error(j.error || "Import failed.");
                        asset.kept_file = j.filename;
                        saveState();
                        upsertRefPlanRow(asset.tag, j.filename, asset.role, promptArea.value);
                        await fetchCaps(false);
                        keepBtn.textContent = `\u2713 Kept (${j.filename})`;
                        bakeBtn.disabled = false;
                        stLine.textContent = "Added to Refs rail & Bible!";
                    } catch (err) {
                        stLine.textContent = String(err);
                    } finally {
                        keepBtn.disabled = false;
                    }
                },
            );
            keepBtn.disabled = !asset.preview?.filename;

            const bakeBtn = button(
                asset.baked_refmod ? `\u26a1 Baked (${asset.baked_refmod})` : "\u26a1 Bake RefMod",
                "Encode into a fast-loading v5 RefMod .safetensors in models/refmods/ (with auto subject cutout for cast/props) and bind @tag to it",
                async () => {
                    bakeBtn.disabled = true;
                    try {
                        if (!asset.kept_file && asset.preview?.filename) {
                            stLine.textContent = "Importing to h3_refs/ first...";
                            const impRes = await fetch("/h3_ref_chain/mv/import_output", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    filename: asset.preview.filename,
                                    subfolder: asset.preview.subfolder || "",
                                    output_type: asset.preview.type || "output",
                                    dest_name: `${asset.tag || "asset"}.png`,
                                    kind: "image",
                                    tag: asset.tag || "asset",
                                    desc: promptArea.value,
                                    role: asset.role || "cast",
                                    register_bible: true,
                                }),
                            });
                            const impJson = await impRes.json();
                            if (!impRes.ok || !impJson.ok) throw new Error(impJson?.error || "Import failed.");
                            asset.kept_file = impJson.filename;
                            keepBtn.textContent = `\u2713 Kept (${impJson.filename})`;
                        }
                        if (!asset.kept_file) {
                            throw new Error("Paint or Keep an image first.");
                        }
                        const cleanTag = String(asset.tag || "asset")
                            .toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_|_$/g, "") || "asset";
                        const modRole = asset.role === "plate" ? "background"
                            : (asset.role === "prop" ? "helper" : "identity");
                        const modCurve = asset.role === "prop" ? "early_lock" : "full";
                        const modMask = asset.role === "plate" ? "off" : "auto_rembg";
                        stLine.textContent = `Baking RefMod "${cleanTag}"...`;
                        const res = await runForgeGraph({
                            kind: "refmod",
                            name: cleanTag,
                            stills: [asset.kept_file],
                            description: promptArea.value,
                            layout: "separate_pictures",
                            role: modRole,
                            default_step_curve: modCurve,
                            subject_mask: modMask,
                            background_mode: "blur_bg",
                            fit_mode: "crop",
                        }, {
                            onStatus: (m) => { stLine.textContent = m; },
                        });
                        asset.baked_refmod = res.refmod_name || cleanTag;
                        saveState();
                        upsertRefPlanRow(asset.tag, asset.baked_refmod, asset.role, promptArea.value, {
                            source: "refmod",
                            stepCurve: modCurve,
                        });
                        await fetchCaps(false);
                        if (typeof window !== "undefined") {
                            window.dispatchEvent?.(new CustomEvent("htc:refmods-changed"));
                        }
                        bakeBtn.textContent = `\u26a1 Baked (${asset.baked_refmod})`;
                        stLine.textContent = `Baked v5 RefMod & bound @${cleanTag}!`;
                    } catch (err) {
                        stLine.textContent = String(err);
                    } finally {
                        bakeBtn.disabled = false;
                    }
                },
            );
            bakeBtn.disabled = !asset.kept_file && !asset.preview?.filename;
            actRow.append(paintBtn, keepBtn, bakeBtn);
            sideCol.append(thumb, actRow, stLine);
            bodyRow.append(promptArea, sideCol);
            box.append(head, bodyRow);
            assetListEl.appendChild(box);
        });
    }

    /* ====================================================================
     * CARD 4: DIRECT & HAND-OFF -> WRITE
     * ==================================================================== */
    const c4 = el("section", "r2-st-card");
    const c4Head = el("div", "r2-st-chead");
    c4Head.append(
        el("span", "r2-st-badge", "4"),
        el("span", "r2-st-clabel", "Direct & Hand-Off to Write"),
        el("span", "r2-st-cnote", "Bundles concept, song sections & forged @refs straight into the Write tab"),
    );
    c4.appendChild(c4Head);

    const handoffRow = el("div", "r2-st-row");
    const briefArea = el("textarea", "r2-st-area r2-st-grow");
    briefArea.rows = 2;
    briefArea.placeholder = "MV directing brief for Write tab...";
    briefArea.value = state.brief || "";
    briefArea.addEventListener("input", () => {
        state.brief = briefArea.value;
        saveState();
    });
    const sendWriteBtn = button("\u2192 Auto-Lock & Send Blueprint to Write", "Ensure kept assets & solved cuts are synced onto the node, then bundle @tags, sections & lyrics straight into Write", () => {
        if (state.song_file && state.song_analysis?.solved?.ok) {
            const curAudio = String(widgetByName(node, "master_audio_file")?.value || "").trim();
            const solvedLen = state.song_analysis.solved.hops?.length || 0;
            if (curAudio !== state.song_file || (readPlan(node).shots || []).length !== solvedLen) {
                lockSongAndCuts();
            }
        }
        const hops = state.song_analysis?.solved?.hops || [];
        const hopCount = hops.length || readPlan(node).shots.length || 6;
        const rail = (readRefs(node)?.refs || []).filter((r) => r.file);
        const refSummary = rail.map((r) => `@${r.tag} (${r.subject != null ? `subject ${r.subject}` : (r.retention === "prop" ? "prop" : "plate")})`).join(", ");
        const secLines = (state.song_analysis?.sections || [])
            .map((s) => `${s.from_s}-${s.to_s}s ${s.kind}${s.sung ? " (SINGS)" : ""}${s.lyric ? `: "${s.lyric}"` : ""}`)
            .join(" | ");
        const fullBrief = [
            state.title ? `MV "${state.title}".` : "",
            String(briefArea.value || state.idea || "").trim(),
            refSummary ? `Active refs: ${refSummary}.` : "",
            secLines ? `Song sections: ${secLines}.` : "",
        ].filter(Boolean).join(" ");
        onSendToWrite?.({
            brief: fullBrief,
            hops: hopCount,
            mv: Boolean(state.song_file || state.song_analysis),
            song_file: state.song_file || "",
            master_audio_start_s: state.song_analysis?.solved?.master_audio_start_s,
        });
    }, "h3e-btn h3e-btn-accent");
    handoffRow.append(briefArea, sendWriteBtn);
    c4.appendChild(handoffRow);
    root.appendChild(c4);

    async function fetchCaps(showToast = false) {
        try {
            const r = await fetch("/h3_ref_chain/mv/capabilities");
            const j = await r.json();
            if (!j.ok) return;
            caps = j;
            capsLoaded = true;

            const prevPick = state.song_file || songPickSel.value;
            songPickSel.textContent = "";
            songPickSel.appendChild(el("option", null, "— Pick Audio in h3_refs/ —")).value = "";
            for (const fn of j.media?.audio || []) {
                const o = el("option", null, fn);
                o.value = fn;
                songPickSel.appendChild(o);
            }
            if (prevPick && (j.media?.audio || []).includes(prevPick)) {
                songPickSel.value = prevPick;
            }

            songEngineSel.textContent = "";
            for (const eng of j.song_engines || []) {
                const lbl = eng.ready ? `\u2713 ${eng.label}` : `\u26a0 ${eng.label}`;
                const o = el("option", null, lbl);
                o.value = eng.id;
                o.title = (eng.missing || []).join(" | ");
                songEngineSel.appendChild(o);
            }
            if (state.song_engine && (j.song_engines || []).some((e) => e.id === state.song_engine)) {
                songEngineSel.value = state.song_engine;
            } else {
                state.song_engine = j.default_song_engine || "yue2_pytraveler";
                songEngineSel.value = state.song_engine;
            }
            const activeEng = (j.song_engines || []).find((e) => e.id === state.song_engine)
                || (j.song_engines || []).find((e) => e.ready);
            const anyYuE2Ready = (j.song_engines || []).some((e) => e.ready);
            if (anyYuE2Ready) {
                yueBadge.textContent = `YuE2 Ready (${activeEng?.checkpoint || "installed"})`;
                yueBadge.classList.add("is-ready");
                yueBadge.title = "";
            } else {
                yueBadge.textContent = "YuE2: Needs yue2_3b_int8_convrot.safetensors (or pick/upload audio)";
                yueBadge.classList.remove("is-ready");
                yueBadge.title = (activeEng?.missing || []).join("\n");
            }

            const imgProfSig = (j.image_profiles || []).map((p) => `${p.id}:${p.ready}:${p.label}`).join("|");
            if (imgProfSig !== lastImgProfSig) {
                lastImgProfSig = imgProfSig;
                imgProfSel.textContent = "";
                for (const prof of j.image_profiles || []) {
                    const lbl = prof.ready ? `\u2713 ${prof.label}` : `\u26a0 ${prof.label} (missing weights)`;
                    const o = el("option", null, lbl);
                    o.value = prof.id;
                    o.title = prof.ready ? prof.note : `Missing: ${(prof.missing || []).join(", ")}`;
                    imgProfSel.appendChild(o);
                }
            }
            if (state.image_profile && (j.image_profiles || []).some((p) => p.id === state.image_profile)) {
                if (imgProfSel.value !== state.image_profile) imgProfSel.value = state.image_profile;
            } else {
                state.image_profile = j.default_image_profile || "qwen_viggle_6step";
                imgProfSel.value = state.image_profile;
            }
            syncProfileNote();
            syncDimPreview();
            renderAssets();
            if (showToast) {
                setStatus(conceptStatus, "Scanned installed Image Forge & YuE2 capabilities.", "hint");
            }
        } catch (_) { /* */ }
    }

    function render() {
        hydrateFromProps();
        durSel.value = String(state.duration_target_s || 105);
        langSel.value = state.language || "auto";
        vocalSel.value = state.vocal_mode || "auto";
        aspectSel.value = state.aspect || "16:9";
        imgMpSel.value = String(state.image_mp ?? "0");
        if (document.activeElement !== ideaInput) ideaInput.value = state.idea || "";
        if (document.activeElement !== styleArea) styleArea.value = state.song_style || "";
        if (document.activeElement !== lyricsArea) lyricsArea.value = state.lyrics || "";
        if (document.activeElement !== briefArea) briefArea.value = state.brief || "";
        syncLyricsMetrics();
        syncDimPreview();
        if (!capsLoaded) fetchCaps(false);
        if (!llmLoaded) loadLlmSettings({ quiet: true });
        syncAudioPreview();
        renderSongAnalysis();
        renderAssets();
        syncPipelineStrip();
    }

    syncLyricsMetrics();
    syncDimPreview();
    syncAudioPreview();
    renderSongAnalysis();
    renderAssets();
    syncPipelineStrip();

    return {
        root,
        render,
        refresh: render,
    };
}
