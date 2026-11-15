/* Standalone ComfyUI Node UI for SandTiePromptRig (MiniMax H3 Dual-Mode Rig). */
import { app } from "../../../scripts/app.js";
import { el, button, widgetByName, hideWidget, isolateEvents } from "./widget_utils.js";
import {
    h3FormatCodeFromLabel,
    mountSandTieStandalone,
    patchRigState,
    readRigState,
} from "./sandtie_ui.js";

const NODE_TYPES = new Set(["SandTiePromptRig"]);
const STYLE_ID = "h3st-node-style";
const _cssUrl = new URL("../h3_ref_chain.css", import.meta.url).href;
const SANDTIE_WRITE_URL = "/h3_ref_chain/sandtie/write";

const NODE_CSS = `
.h3st-node-card {
    display: flex; flex-direction: column; gap: 6px; padding: 8px;
    background: var(--h3-panel); color: var(--h3-text); font-family: var(--h3-sans);
    font-size: 11.5px; border-radius: 5px; border: 1px solid var(--h3-border);
    box-sizing: border-box; width: 100%; max-width: 100%; min-width: 0; height: 100%; overflow: hidden;
}
.h3st-node-card > * { min-width: 0; max-width: 100%; }
.h3st-node-card .h3st-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; max-width: 100%; }
.h3st-node-card .h3st-pill {
    display: inline-flex; align-items: center; gap: 4px; padding: 2px 6px;
    border-radius: 3px; font-size: 10.5px; font-weight: 600; max-width: 100%;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    border: 1px solid var(--h3-border); background: var(--h3-sunken); color: var(--h3-muted);
}
.h3st-node-card .h3st-pill-accent { border-color: rgba(232,255,71,0.55); background: rgba(232,255,71,0.12); color: var(--h3-accent); }
.h3st-node-card .h3st-pill-ok { border-color: rgba(95,191,122,0.5); background: rgba(95,191,122,0.13); color: #8ee5a8; }
.h3st-node-preview {
    flex: 1 1 auto; min-height: 70px; min-width: 0; max-width: 100%; overflow: auto;
    white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word;
    background: var(--h3-sunken); border: 1px solid var(--h3-border-soft);
    border-radius: 3px; padding: 6px; font-family: var(--h3-mono); font-size: 10.5px;
    color: var(--h3-muted);
}
.h3st-modal-backdrop {
    position: fixed; inset: 0; z-index: 9500;
    background: rgba(0,0,0,0.72); display: flex; align-items: center; justify-content: center;
    padding: 18px;
}
.h3st-modal-box {
    width: min(1240px, 95vw); max-height: 92vh; overflow-y: auto;
    background: var(--h3-panel); border: 1px solid var(--h3-accent);
    border-radius: 6px; padding: 12px 14px; box-shadow: 0 24px 64px rgba(0,0,0,0.85);
}
`;

function ensureStyles() {
    if (!document.querySelector(`link[href="${_cssUrl}"]`)) {
        const lk = document.createElement("link");
        lk.rel = "stylesheet";
        lk.href = _cssUrl;
        document.head.appendChild(lk);
    }
    let st = document.getElementById(STYLE_ID);
    if (!st) {
        st = document.createElement("style");
        st.id = STYLE_ID;
        document.head.appendChild(st);
    }
    if (st.textContent !== NODE_CSS) st.textContent = NODE_CSS;
}

function countCanvasWiredImages(node) {
    let n = 0;
    for (const inp of node?.inputs || []) {
        if (!inp || inp.link == null) continue;
        const nm = String(inp.name || "");
        if (nm.includes("ref_image_") || nm.endsWith("first_frame") || nm.endsWith("last_frame")) n++;
    }
    return n;
}

function countBibleRefs(refPlanJson) {
    try {
        const doc = JSON.parse(String(refPlanJson || "{}") || "{}");
        return Array.isArray(doc?.refs) ? doc.refs.filter((r) => r && r.file).length : 0;
    } catch {
        return 0;
    }
}

function attachRig(node) {
    if (node._sandtieAttached) return;
    node._sandtieAttached = true;
    ensureStyles();

    for (const wn of ["rig_state", "prompt_out", "storyboard_out", "soundscape_out", "music_out", "ref_plan_json", "flavors_json"]) {
        const w = widgetByName(node, wn);
        if (w) hideWidget(w);
    }

    const root = el("div", "h3st-node-card h3e-root");
    isolateEvents(root);

    const top = el("div", "h3st-row");
    top.style.justifyContent = "space-between";
    const title = el("strong", null, "⌖ SandTie PromptRig (H3)");
    const badge = el("span", "h3st-pill h3st-pill-accent", "H3 Auto");
    top.append(title, badge);

    const btnRow = el("div", "h3st-row");
    const openStudioBtn = button("⬒ Open SandTie Studio", "Open SandTie Scribe dials & Reference Bible studio", () => openModal(), "h3e-btn h3e-btn-accent");
    const tieBtn = button("▶ Tie", "Run instant CPU or LLM tie directly", () => quickTie(false));
    const cpuBtn = button("◩ CPU", "Instant 0-VRAM deterministic H3 tie", () => quickTie(true));
    const refsPill = el("span", "h3st-pill", "Bible: 0 · Canvas: 0");
    refsPill.style.marginLeft = "auto";
    btnRow.append(openStudioBtn, tieBtn, cpuBtn, refsPill);

    const preview = el("pre", "h3st-node-preview");

    function aspectLabel(raw) {
        const s = String(raw || "16:9 landscape").trim();
        const m = s.match(/(\d+)\s*:\s*(\d+)/);
        return m ? `${m[1]}:${m[2]}` : s;
    }

    function refreshPreview() {
        const wm = String(widgetByName(node, "wire_mode")?.value || "Prompt Only");
        const isCond = wm.includes("Direct");
        const fmt = String(widgetByName(node, "h3_format")?.value || "H3 Auto");
        const wMode = String(widgetByName(node, "write_mode")?.value || "CPU");
        const asp = aspectLabel(widgetByName(node, "aspect")?.value || "16:9 landscape");
        const dur = String(widgetByName(node, "duration")?.value || "10 s");
        badge.textContent = `${isCond ? "Direct H3" : "Prompt"} · ${fmt.split(" (")[0]} · ${asp} · ${dur}`;

        const st = readRigState(node);
        const nBible = countBibleRefs(st.ref_plan_json);
        const nCanvas = countCanvasWiredImages(node);
        refsPill.textContent = `Bible: ${nBible} · Canvas: ${nCanvas}`;
        refsPill.className = "h3st-pill" + ((nBible || nCanvas) ? " h3st-pill-ok" : "");

        const pOut = st.prompt_out.trim();
        preview.textContent = pOut || `[${wMode}] Enter brief or click ⬒ Open SandTie Studio to compose.`;
    }

    async function quickTie(forceCpu) {
        const wMode = widgetByName(node, "write_mode");
        const isCpu = forceCpu || String(wMode?.value || "").includes("CPU");
        const stage = isCpu ? "cpu" : "fast";
        const fmtCode = h3FormatCodeFromLabel(widgetByName(node, "h3_format")?.value || "");
        const st = readRigState(node);
        const flavors = Object.assign({}, st.flavors || {});
        const cw = Number(widgetByName(node, "width")?.value || 0);
        const ch = Number(widgetByName(node, "height")?.value || 0);
        flavors.aspect = (cw > 0 && ch > 0)
            ? `${cw}:${ch}`
            : aspectLabel(widgetByName(node, "aspect")?.value || "16:9 landscape");
        flavors.output_format = fmtCode;
        flavors.double_knot = String(wMode?.value || "").includes("Double-Knot");

        preview.textContent = isCpu ? "Building CPU Tie prompt…" : "Running SandTie writer…";
        try {
            const r = await fetch(SANDTIE_WRITE_URL, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    stage,
                    brief: String(widgetByName(node, "brief")?.value || ""),
                    duration: String(widgetByName(node, "duration")?.value || "10 s"),
                    ref_plan: st.ref_plan_json || "",
                    flavors,
                }),
            });
            const j = await r.json();
            if (j.block) {
                patchRigState(node, {
                    prompt_out: j.block,
                    storyboard_out: j.plan || st.storyboard_out || "",
                    ref_plan_json: j.updated_ref_plan || st.ref_plan_json || "",
                    flavors,
                });
            }
            refreshPreview();
        } catch (err) {
            preview.textContent = String(err);
        }
    }

    function openModal() {
        const backdrop = el("div", "h3st-modal-backdrop h3e-root");
        isolateEvents(backdrop);
        const box = el("div", "h3st-modal-box");
        const hdr = el("div", "h3st-head");
        hdr.style.marginBottom = "10px";
        hdr.style.paddingBottom = "8px";
        hdr.style.borderBottom = "1px solid var(--h3-border)";
        const hdrLeft = el("div", "h3st-row");
        hdrLeft.append(el("strong", null, "⌖ SandTie PromptRig — H3 Studio & Reference Bible"), el("span", "h3st-pill h3st-pill-accent", "MiniMax H3"));
        const closeBtn = button("✓ Done & Sync Node", "Sync outputs and close studio", () => {
            refreshPreview();
            backdrop.remove();
        }, "h3e-btn h3e-btn-accent");
        hdr.append(hdrLeft, closeBtn);
        const mount = el("div");
        box.append(hdr, mount);
        backdrop.appendChild(box);
        document.body.appendChild(backdrop);

        mountSandTieStandalone(node, mount, {
            onSyncOutputs: () => {
                refreshPreview();
                backdrop.remove();
            },
        });
        backdrop.addEventListener("click", (e) => {
            if (e.target === backdrop) { refreshPreview(); backdrop.remove(); }
        });
    }

    for (const wn of ["wire_mode", "h3_format", "write_mode", "aspect", "duration"]) {
        const w = widgetByName(node, wn);
        if (w && !w._sandtieWrapped) {
            w._sandtieWrapped = true;
            const prevCb = w.callback;
            w.callback = function () {
                const res = prevCb?.apply(this, arguments);
                refreshPreview();
                return res;
            };
        }
    }

    function syncCardBounds() {
        const w = Math.max(220, Math.floor((Number(node.size?.[0]) || 480) - 24));
        if (root._lastW === w && root.parentElement?._stBoundsOk) return;
        root._lastW = w;
        root.style.width = "100%";
        root.style.maxWidth = `${w}px`;
        if (root.parentElement) {
            root.parentElement.style.maxWidth = `${w}px`;
            root.parentElement.style.overflow = "hidden";
            root.parentElement._stBoundsOk = true;
        }
    }

    node._sandtieRefreshPreview = refreshPreview;
    node._sandtieSyncBounds = syncCardBounds;
    root.append(top, btnRow, preview);
    const domW = node.addDOMWidget("sandtie_rig_card", "sandtie_rig_card", root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 185,
        getMaxHeight: () => 2000,
    });
    domW.computeLayoutSize = (n) => {
        const avail = Math.max(220, Math.floor((Number(n?.size?.[0] ?? node.size?.[0]) || 480) - 24));
        return { minHeight: 185, maxHeight: 2000, minWidth: 220, maxWidth: avail };
    };
    const prevResize = node.onResize;
    node.onResize = function () {
        const r = prevResize?.apply(this, arguments);
        root._lastW = 0;
        syncCardBounds();
        return r;
    };
    const prevDraw = node.onDrawForeground;
    node.onDrawForeground = function () {
        syncCardBounds();
        return prevDraw?.apply(this, arguments);
    };
    if ((node.size?.[0] || 0) < 460) node.setSize?.([480, Math.max(540, node.size?.[1] || 540)]);
    syncCardBounds();
    requestAnimationFrame(syncCardBounds);
    refreshPreview();
}

app.registerExtension({
    name: "HandTieClips.SandTiePromptRig",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (!NODE_TYPES.has(nodeData?.name)) return;
        const onCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onCreated?.apply(this, arguments);
            attachRig(this);
            return r;
        };
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const r = onConfigure?.apply(this, arguments);
            const aw = widgetByName(this, "aspect");
            if (aw) {
                const legacyMap = { "16:9": "16:9 landscape", "9:16": "9:16 portrait", "1:1": "1:1 square" };
                if (legacyMap[aw.value]) aw.value = legacyMap[aw.value];
            }
            attachRig(this);
            this._sandtieRefreshPreview?.();
            return r;
        };
        const onConn = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function () {
            const r = onConn?.apply(this, arguments);
            this._sandtieRefreshPreview?.();
            return r;
        };
    },
});
