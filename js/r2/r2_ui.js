/**
 * R2 Control Room — Phase 1 + Dock/Overlay Portal.
 *
 * The node is the shell: eight labelled tabs, a filmstrip, one active pane and
 * the timeline beside it. Timeline is a fullscreen tab; Split/Retake/Focus are
 * widths, not different layouts.
 *
 * Also supports popping the work area out into a fixed Bottom Dock (⬓ dock) or
 * Floating Studio Overlay (⬒ studio) while shrinking the classic node on the
 * canvas to its compact header + filmstrip strip.
 */

import { api } from "../../../scripts/api.js";
import {
    widgetByName, el, hideWidget, installHeightGuard, isolateEvents,
} from "../editor/widget_utils.js";
import { createRefRail, parseRefPlan } from "../editor/ref_rail.js";
import { createMediaStrip } from "../editor/media_strip.js";
import { createRunPanel } from "../editor/run_panel.js";
import { createWriterBar } from "../editor/writer_bar.js";
import { createVideoSwap } from "../editor/video_swap.js";
import { createStandardWriter } from "../editor/standard_writer.js";
import {
    SHOTS_HIDDEN, readPlan, readRefs, writeRefs, chainSeconds, mediaCount,
    durationOf, deliveredSeconds, cachedCount, hopKey, spriteURL, forecastText,
} from "./r2_store.js";
import { createScriptPane } from "./r2_script.js";
import { createStage } from "./r2_stage.js";
import { createStudioPane } from "./r2_studio.js";
import { createRefModPane } from "./r2_refmod.js";

const TAB_PROP = "h3_r2_tab";
const PRESET_PROP = "h3_r2_preset";
const FOCUS_PROP = "h3_r2_focus";
const COLLAPSED_PROP = "h3_r2_collapsed";
const DOCK_PROP = "h3_r2_dock"; // "node" | "dock" | "overlay"
const DOCK_H_PROP = "h3_r2_dock_h";
const SHOT_PROP = "h3_r2_shot";
const STYLE_ID = "h3r2-style";

const TABS = [
    { id: "script", label: "Script", icon: "\u270e" },
    { id: "refs", label: "Refs", icon: "\u25a6" },
    { id: "studio", label: "Studio", icon: "\u2727" },
    { id: "refmod", label: "RefMod", icon: "\u2b21" },
    { id: "timeline", label: "Timeline", icon: "\u25b6" },
    { id: "media", label: "Media", icon: "\u266b" },
    { id: "write", label: "Write", icon: "\u2726" },
    { id: "swap", label: "Swap", icon: "\u21c4" },
    { id: "standard", label: "Standard", icon: "\u25a4" },
    { id: "run", label: "Run", icon: "\u2699" },
];

const EXPANDED_H = 1140;
const COLLAPSED_H = 460;
const WIDTH = 1820;
const WIDE_TABS = new Set(["studio", "refmod", "write", "swap", "standard", "run"]);

function ensureStyles() {
    if (!document.getElementById("h3rc-style")) {
        const link = document.createElement("link");
        link.id = "h3rc-style";
        link.rel = "stylesheet";
        link.href = new URL("../h3_ref_chain.css", import.meta.url).href;
        document.head.appendChild(link);
    }
    if (!document.getElementById(STYLE_ID)) {
        const link = document.createElement("link");
        link.id = STYLE_ID;
        link.rel = "stylesheet";
        link.href = new URL("./r2.css", import.meta.url).href;
        document.head.appendChild(link);
    }
}

export function mountR2(node) {
    if (node._h3R2) return node._h3R2;
    if (typeof node.addDOMWidget !== "function") {
        console.warn("[HandTieClips R2] no addDOMWidget on this frontend");
        return null;
    }
    ensureStyles();
    node.properties ??= {};

    /* -- shared state ----------------------------------------------------- */
    let active = Math.max(0, Number(node.properties?.[SHOT_PROP]) || 0);
    let tab = node.properties?.[TAB_PROP] || "script";
    let lastTab = tab === "timeline" ? "script" : tab;
    let preset = node.properties?.[PRESET_PROP] || "split";
    let focus = Boolean(node.properties?.[FOCUS_PROP]);
    let userSplitFocus = WIDE_TABS.has(tab) ? false : focus;
    let collapsed = Boolean(node.properties?.[COLLAPSED_PROP]);
    let dockMode = node.properties?.[DOCK_PROP] || "node"; // "node" | "dock" | "overlay"
    let savedExpandedH = EXPANDED_H;
    const shots = () => readPlan(node).shots;
    let refPlan = readRefs(node);
    let refPlanRaw = String(widgetByName(node, "ref_plan")?.value ?? "");
    function syncRefPlanIfChanged() {
        const curRaw = String(widgetByName(node, "ref_plan")?.value ?? "");
        if (curRaw !== refPlanRaw) {
            refPlanRaw = curRaw;
            refPlan = readRefs(node);
        }
        return refPlan;
    }

    // Include h3e-root so all shared .h3e-root styles (and sandtie_ui.js) apply
    const root = el("div", "r2-root h3e-root");
    isolateEvents(root);

    /* -- header ----------------------------------------------------------- */
    const head = el("div", "r2-head");
    head.appendChild(el("span", "r2-brand", "H3 Ref2VA Chain"));
    const project = el("span", "r2-project", node.title || "Service Entrance");
    head.appendChild(project);

    const warnChip = el("span", "r2-chip r2-warn");
    warnChip.hidden = true;
    head.appendChild(warnChip);
    node._h3Warn = {
        show(warns) {
            if (!warns || !warns.length) {
                warnChip.hidden = true;
                warnChip.textContent = "";
                warnChip.title = "";
                return;
            }
            warnChip.hidden = false;
            warnChip.textContent = `\u26a0 ${warns.length} previs cut${warns.length === 1 ? "" : "s"}`;
            warnChip.title = warns.map((w) => w.label).join("\n");
        },
    };

    const status = el("span", "r2-status");
    head.appendChild(status);

    const presets = el("span", "r2-presets");
    const presetBtns = {};
    for (const p of ["split", "retake"]) {
        const b = el("button", "r2-pbtn", p === "retake" ? "Retake" : "Split");
        b.type = "button";
        b.title = p === "retake"
            ? "Retake split: compact editor (38%) beside expanded timeline & monitor (62%) (2)"
            : "Editor split: wide editor (66%) beside compact timeline (34%) (1)";
        b.addEventListener("click", () => setPreset(p));
        presetBtns[p] = b;
        presets.appendChild(b);
    }
    const focusBtn = el("button", "r2-pbtn", "\u2922 focus");
    focusBtn.type = "button";
    focusBtn.title = "Hide the timeline and give the section the whole width (F)";
    focusBtn.addEventListener("click", () => setFocus(!focus));
    presets.appendChild(focusBtn);
    head.appendChild(presets);

    const dockBtn = el("button", "r2-mini r2-dockbtn", "\u2b13 dock");
    dockBtn.type = "button";
    dockBtn.title = "Detach the work area into a fixed Bottom Dock and shrink the node (D)";
    dockBtn.addEventListener("click", () => setDockMode(dockMode === "dock" ? "node" : "dock"));
    head.appendChild(dockBtn);

    const overlayBtn = el("button", "r2-mini r2-overlaybtn", "\u2b12 studio");
    overlayBtn.type = "button";
    overlayBtn.title = "Pop the work area into a Floating Studio Overlay over the canvas";
    overlayBtn.addEventListener("click", () => setDockMode(dockMode === "overlay" ? "node" : "overlay"));
    head.appendChild(overlayBtn);

    const collapseBtn = el("button", "r2-mini r2-collapse", "\u25b4 compact");
    collapseBtn.type = "button";
    collapseBtn.title = "Compact node (hide work area)";
    collapseBtn.addEventListener("click", () => {
        if (dockMode !== "node") {
            setDockMode("node");
            setCollapsed(false);
        } else {
            setCollapsed(!collapsed);
        }
    });
    head.appendChild(collapseBtn);
    root.appendChild(head);

    /* -- section bar ------------------------------------------------------ */
    const bar = el("nav", "r2-bar");
    const tabBtns = {};
    for (const t of TABS) {
        const b = el("button", "r2-tab");
        b.type = "button";
        b.dataset.r2Tab = t.id;
        b.append(el("span", "ic", t.icon), el("span", "lb", t.label));
        const count = el("span", "ct");
        b.appendChild(count);
        b.addEventListener("click", () => {
            if (t.id === "timeline" && tab === "timeline") setTab(lastTab);
            else setTab(t.id);
        });
        tabBtns[t.id] = { btn: b, count };
        bar.appendChild(b);
    }
    root.appendChild(bar);

    /* -- filmstrip -------------------------------------------------------- */
    const film = el("div", "r2-filmstrip");
    root.appendChild(film);

    /* -- main ------------------------------------------------------------- */
    const main = el("div", "r2-main");

    const panes = el("div", "r2-panes");
    const paneEls = {};
    for (const t of TABS) {
        if (t.id === "timeline") continue;
        const p = el("section", "r2-pane r2-pane-" + t.id);
        p.hidden = true;
        paneEls[t.id] = p;
        panes.appendChild(p);
    }
    main.appendChild(panes);

    const stageHost = el("section", "r2-stage-host");
    main.appendChild(stageHost);
    root.appendChild(main);

    /* -- footer ----------------------------------------------------------- */
    const foot = el("div", "r2-foot");
    const footNext = el("span", "r2-muted");
    const footCache = el("span", "r2-muted");
    const footPreset = el("span", "r2-muted");
    foot.append(el("span", "r2-ok", "\u25cf ready"), footNext, el("span", "spacer"),
        footCache, footPreset, el("span", "r2-key", "space play"),
        el("span", "r2-key", "1 split"), el("span", "r2-key", "2 retake"),
        el("span", "r2-key", "F focus"), el("span", "r2-key", "D dock"));
    root.appendChild(foot);

    /* -- external dock / overlay portal ----------------------------------- */
    const portalBackdrop = el("div", "r2-portal-backdrop");
    portalBackdrop.hidden = true;
    const portal = el("div", "r2-portal r2-root h3e-root");
    portal.hidden = true;
    isolateEvents(portal);

    const dockGrip = el("div", "r2-dock-grip");
    dockGrip.title = "Drag up or down to resize Bottom Dock height (double-click to reset)";
    dockGrip.addEventListener("pointerdown", (e) => {
        if (dockMode !== "dock") return;
        e.preventDefault();
        e.stopPropagation();
        dockGrip.setPointerCapture?.(e.pointerId);
        const startY = e.clientY;
        const startH = portal.getBoundingClientRect().height;
        const onMove = (ev) => {
            const maxH = Math.floor(window.innerHeight * 0.96);
            const nextH = Math.max(360, Math.min(maxH, Math.round(startH + (startY - ev.clientY))));
            portal.style.height = `${nextH}px`;
            node.properties[DOCK_H_PROP] = nextH;
        };
        const onUp = (ev) => {
            dockGrip.releasePointerCapture?.(ev.pointerId);
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onUp);
        };
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
    });
    dockGrip.addEventListener("dblclick", (e) => {
        e.preventDefault();
        delete node.properties[DOCK_H_PROP];
        portal.style.height = "";
    });

    const portalHead = el("div", "r2-head r2-portal-head");
    const portalTitle = el("span", "r2-brand", "H3 Control Room");
    const portalSub = el("span", "r2-project", "Docked Studio");
    const portalStatus = el("span", "r2-status");
    const portalPresets = el("span", "r2-presets");
    const portalPresetBtns = {};
    for (const p of ["split", "retake"]) {
        const b = el("button", "r2-pbtn", p === "retake" ? "Retake" : "Split");
        b.type = "button";
        b.title = p === "retake"
            ? "Retake split: compact editor (38%) beside expanded timeline & monitor (62%) (2)"
            : "Editor split: wide editor (66%) beside compact timeline (34%) (1)";
        b.addEventListener("click", () => setPreset(p));
        portalPresetBtns[p] = b;
        portalPresets.appendChild(b);
    }
    const portalFocusBtn = el("button", "r2-pbtn", "\u2922 focus");
    portalFocusBtn.type = "button";
    portalFocusBtn.title = "Hide the timeline and give the section the whole width (F)";
    portalFocusBtn.addEventListener("click", () => setFocus(!focus));
    portalPresets.appendChild(portalFocusBtn);

    const portalModeBtn = el("button", "r2-mini", "\u2b12 switch to overlay");
    portalModeBtn.type = "button";
    portalModeBtn.addEventListener("click", () => {
        setDockMode(dockMode === "dock" ? "overlay" : "dock");
    });

    const portalCloseBtn = el("button", "r2-mini r2-primary", "\u2715 return to node");
    portalCloseBtn.type = "button";
    portalCloseBtn.addEventListener("click", () => setDockMode("node"));

    portalHead.append(portalTitle, portalSub, portalStatus, portalPresets, portalModeBtn, portalCloseBtn);

    const portalBar = el("nav", "r2-bar");
    const portalTabBtns = {};
    for (const t of TABS) {
        const b = el("button", "r2-tab");
        b.type = "button";
        b.dataset.r2Tab = t.id;
        b.append(el("span", "ic", t.icon), el("span", "lb", t.label));
        const count = el("span", "ct");
        b.appendChild(count);
        b.addEventListener("click", () => {
            if (t.id === "timeline" && tab === "timeline") setTab(lastTab);
            else setTab(t.id);
        });
        portalTabBtns[t.id] = { btn: b, count };
        portalBar.appendChild(b);
    }
    portal.append(dockGrip, portalHead, portalBar);
    portalBackdrop.addEventListener("click", (e) => {
        if (e.target === portalBackdrop) setDockMode("node");
    });

    /* -- modules ---------------------------------------------------------- */
    const script = createScriptPane(node, {
        onChange: () => {
            runPanel?.sync();
            syncFilm();
            syncCounts();
            stage.render();
            syncDigest();
        },
        onSelect: (i) => {
            active = i;
            node.properties[SHOT_PROP] = i;
            stage.show(i);
            syncFilm();
        },
    });
    paneEls.script.appendChild(script.root);

    const stage = createStage(node, {
        getShots: shots,
        getActive: () => active,
        onSelect: (i) => {
            active = i;
            node.properties[SHOT_PROP] = i;
            script.setActive(i);
            syncFilm();
        },
    });
    stageHost.appendChild(stage.root);

    let refModPane = null;

    const refRail = createRefRail(node, {
        getPlan: () => syncRefPlanIfChanged(),
        setPlan: (plan) => {
            refPlan = plan;
            writeRefs(node, plan);
            refPlanRaw = String(widgetByName(node, "ref_plan")?.value ?? "");
            syncCounts();
            script.render();
            swap?.render?.();
            standard?.render?.();
        },
        getRaw: () => String(widgetByName(node, "ref_plan")?.value || ""),
        isBad: () => parseRefPlan(widgetByName(node, "ref_plan")?.value) === null,
        onChange: () => {
            refPlan = readRefs(node);
            refPlanRaw = String(widgetByName(node, "ref_plan")?.value ?? "");
            syncCounts();
            script.render();
            swap?.render?.();
            standard?.render?.();
        },
        hopCount: () => shots().length || Math.max(1, Number(widgetByName(node, "chains")?.value) || 1),
        onBuildRefMod: (modName) => {
            if (modName && refModPane?.openForRefMod) refModPane.openForRefMod(modName);
            setTab("refmod");
        },
    });
    paneEls.refs.appendChild(refRail.root);

    refModPane = createRefModPane(node, {
        onChange: () => {
            refreshAll();
        },
    });
    paneEls.refmod.appendChild(refModPane.root);

    const media = createMediaStrip(node, {
        onChange: () => {
            syncCounts();
            script.render();
            standard?.render?.();
        },
        chainSeconds: () => chainSeconds(node, shots()),
    });
    paneEls.media.appendChild(media.root);

    let runPanel = null;

    function writerWritten(shotJson, refJson, extra) {
        if (shotJson) {
            const w = widgetByName(node, "shot_plan");
            if (w) {
                w.value = shotJson;
                try { w.callback?.(w.value, node.graph?.canvas, node); } catch (_) { /* */ }
            }
            node.properties.h3_editor_mode = "shots";
        }
        if (refJson) {
            const w = widgetByName(node, "ref_plan");
            if (w) {
                w.value = refJson;
                try { w.callback?.(w.value, node.graph?.canvas, node); } catch (_) { /* */ }
            }
        }
        if (extra && extra.master_audio_start_s != null) {
            const w = widgetByName(node, "master_audio_start_s");
            if (w) w.value = Number(extra.master_audio_start_s);
            const a = widgetByName(node, "master_audio_file");
            if (a && !String(a.value || "").trim() && extra.song_file) a.value = extra.song_file;
        }
        refreshAll();
        setTab("script");
    }

    const writer = createWriterBar(node, {
        hopCount: () => shots().length || Math.max(1, Number(widgetByName(node, "chains")?.value) || 1),
        onWritten: writerWritten,
    });
    writer.root.open = true;
    paneEls.write.appendChild(writer.root);

    const studio = createStudioPane(node, {
        onChange: () => {
            refreshAll();
        },
        onSendToWrite: ({ brief: bText, hops: hCount, song_file: sFile, master_audio_start_s: sStart } = {}) => {
            if (sFile) {
                const aw = widgetByName(node, "master_audio_file");
                if (aw) {
                    aw.value = String(sFile);
                    try { aw.callback?.(aw.value, node.graph?.canvas, node); } catch (_) { /* */ }
                }
            }
            if (sStart != null && Number.isFinite(Number(sStart))) {
                const sw = widgetByName(node, "master_audio_start_s");
                if (sw) {
                    sw.value = Number(sStart);
                    try { sw.callback?.(sw.value, node.graph?.canvas, node); } catch (_) { /* */ }
                }
            }
            writer.setBrief?.(bText, { hops: hCount });
            refreshAll();
            setTab("write");
        },
    });
    paneEls.studio.appendChild(studio.root);

    const swap = createVideoSwap(node, {
        onWritten: (shotJson, extra) => {
            if (extra && extra.swap_script !== undefined) {
                const w = widgetByName(node, "swap_script");
                if (w) {
                    w.value = String(extra.swap_script || "");
                    try { w.callback?.(w.value, node.graph?.canvas, node); } catch (_) { /* */ }
                }
                const r = widgetByName(node, "swap_refs");
                if (r && extra.swap_refs !== undefined) {
                    r.value = String(extra.swap_refs || "");
                    try { r.callback?.(r.value, node.graph?.canvas, node); } catch (_) { /* */ }
                }
            }
            if (extra?.reference_video_desc) {
                const d = widgetByName(node, "reference_video_desc");
                if (d) {
                    d.value = extra.reference_video_desc;
                    try { d.callback?.(d.value, node.graph?.canvas, node); } catch (_) { /* */ }
                }
            }
            refreshAll();
            setTab("swap");
        },
    });
    swap.root.open = true;
    paneEls.swap.appendChild(swap.root);

    const standard = createStandardWriter(node, {
        onWritten: (_text, meta) => {
            if (meta && Number.isFinite(meta.hopIndex) && meta.hopIndex >= 0) {
                active = meta.hopIndex;
                node.properties[SHOT_PROP] = active;
            }
            refreshAll();
            if (meta?.mode === "shots" && Number.isFinite(meta.hopIndex)) {
                script.setActive(active);
                stage.show(active);
                syncFilm();
            }
        },
    });
    standard.root.open = true;
    paneEls.standard.appendChild(standard.root);

    runPanel = createRunPanel(node, {
        onChange: () => {
            script.render();
            stage.render();
            standard?.render?.();
            syncDigest();
            syncCounts();
        },
        suppressed: () => (script.mode() === "shots" ? ["chains", "hop_script"] : []),
        hopCount: () => shots().length || Math.max(1, Number(widgetByName(node, "chains")?.value) || 1),
        onBack: () => setTab("script"),
    });
    runPanel.root.open = true;
    runPanel.back.hidden = true;
    paneEls.run.appendChild(runPanel.root);

    /* -- visibility ------------------------------------------------------- */
    function hideOwned() {
        runPanel.sync();
        const hidden = new Set(SHOTS_HIDDEN.concat(runPanel.ownedNames()));
        for (const w of node.widgets || []) {
            if (hidden.has(w.name)) hideWidget(w);
        }
    }

    /* -- tabs / layout / portal ------------------------------------------- */
    function layout() {
        main.classList.toggle("timeline", tab === "timeline");
        main.classList.toggle("retake", preset === "retake" && tab !== "timeline");
        main.classList.toggle("focus", focus && tab !== "timeline");
        for (const t of TABS) {
            if (t.id === "timeline") continue;
            if (paneEls[t.id]) paneEls[t.id].hidden = t.id !== tab || tab === "timeline";
        }
        for (const t of TABS) {
            tabBtns[t.id].btn.classList.toggle("on", t.id === tab);
            portalTabBtns[t.id].btn.classList.toggle("on", t.id === tab);
        }
        footPreset.textContent = focus
            ? "focus (full)"
            : (preset === "retake" ? "retake (38/62)" : "split (66/34)");
    }

    function setTab(id, { restore: isRestore = false } = {}) {
        if (!isRestore && collapsed && dockMode === "node") setCollapsed(false);
        if (id !== "timeline") lastTab = id;
        tab = id;
        node.properties[TAB_PROP] = id;
        if (id === "timeline") {
            focus = false;
            node.properties[FOCUS_PROP] = false;
            renderPresetButtons();
            stage.render();
        } else if (WIDE_TABS.has(id)) {
            focus = true;
            node.properties[FOCUS_PROP] = true;
            renderPresetButtons();
        } else if (!isRestore) {
            focus = userSplitFocus;
            node.properties[FOCUS_PROP] = focus;
            renderPresetButtons();
        }
        if (id === "studio") studio.render();
        if (id === "refs") { syncRefPlanIfChanged(); refRail.render(); }
        if (id === "refmod") { refModPane.render(); }
        if (id === "media") media.render();
        if (id === "write") { writer.root.open = true; writer.refreshIfLoaded?.(); }
        if (id === "swap") { swap.root.open = true; swap.render?.(); }
        if (id === "standard") { standard.root.open = true; standard.render?.(); }
        if (id === "run") { runPanel.sync(); }
        layout();
        syncCounts();
        node.graph?.setDirtyCanvas?.(true, true);
    }

    function setPreset(p) {
        preset = p === "retake" ? "retake" : "split";
        node.properties[PRESET_PROP] = preset;
        if (tab === "timeline") setTab(lastTab);
        focus = false;
        if (!WIDE_TABS.has(tab)) userSplitFocus = false;
        node.properties[FOCUS_PROP] = false;
        renderPresetButtons();
        layout();
    }

    function setFocus(on) {
        focus = Boolean(on);
        if (!WIDE_TABS.has(tab) && tab !== "timeline") userSplitFocus = focus;
        node.properties[FOCUS_PROP] = focus;
        if (focus && tab === "timeline") setTab(lastTab);
        renderPresetButtons();
        layout();
    }

    function renderPresetButtons() {
        presetBtns.split.classList.toggle("on", preset === "split" && !focus);
        presetBtns.retake.classList.toggle("on", preset === "retake" && !focus);
        focusBtn.classList.toggle("on", focus);
        portalPresetBtns.split.classList.toggle("on", preset === "split" && !focus);
        portalPresetBtns.retake.classList.toggle("on", preset === "retake" && !focus);
        portalFocusBtn.classList.toggle("on", focus);
    }

    function setDockMode(nextMode) {
        const valid = nextMode === "dock" || nextMode === "overlay" ? nextMode : "node";
        const wasNode = dockMode === "node";
        dockMode = valid;
        node.properties[DOCK_PROP] = dockMode;

        const isDetached = dockMode !== "node";
        dockBtn.classList.toggle("on", dockMode === "dock");
        overlayBtn.classList.toggle("on", dockMode === "overlay");
        dockBtn.textContent = dockMode === "dock" ? "\u2b13 docked" : "\u2b13 dock";
        overlayBtn.textContent = dockMode === "overlay" ? "\u2b12 studio on" : "\u2b12 studio";

        if (isDetached) {
            if (wasNode && !collapsed) {
                const curH = Number(node.size?.[1]) || 0;
                if (curH > COLLAPSED_H + 60) savedExpandedH = Math.max(EXPANDED_H, curH);
            }
            if (!portal.isConnected && !portal.parentNode) {
                document.body.appendChild(portalBackdrop);
                document.body.appendChild(portal);
            }
            portal.classList.toggle("is-dock", dockMode === "dock");
            portal.classList.toggle("is-overlay", dockMode === "overlay");
            dockGrip.hidden = dockMode !== "dock";
            const savedDockH = Number(node.properties?.[DOCK_H_PROP]) || 0;
            portal.style.height = (dockMode === "dock" && savedDockH >= 360)
                ? `${Math.min(Math.floor(window.innerHeight * 0.96), savedDockH)}px`
                : "";
            portalBackdrop.hidden = dockMode !== "overlay";
            portal.hidden = false;
            portalSub.textContent = `${node.title || "H3 Ref2VA Chain"} \u00b7 ${dockMode === "dock" ? "Bottom Dock" : "Floating Studio"}`;
            portalModeBtn.textContent = dockMode === "dock" ? "\u2b12 float overlay" : "\u2b13 bottom dock";
            portal.append(main, foot);
            root.classList.add("collapsed");
            collapseBtn.textContent = "\u25be in-node";
            const w = Math.max(1180, Number(node.size?.[0]) || WIDTH);
            node.setSize([w, COLLAPSED_H]);
        } else {
            portal.hidden = true;
            portalBackdrop.hidden = true;
            root.append(main, foot);
            try {
                portal.remove();
                portalBackdrop.remove();
            } catch (_) { /* */ }
            collapsed = false;
            node.properties[COLLAPSED_PROP] = false;
            root.classList.remove("collapsed");
            collapseBtn.textContent = "\u25b4 compact";
            const w = Math.max(1180, Number(node.size?.[0]) || WIDTH);
            node.setSize([w, Math.max(EXPANDED_H, savedExpandedH)]);
            layout();
        }
        node.graph?.setDirtyCanvas?.(true, true);
    }

    function setCollapsed(on) {
        if (!on && collapsed) {
            collapsed = false;
            node.properties[COLLAPSED_PROP] = false;
        } else {
            if (on && !collapsed && dockMode === "node") {
                const curH = Number(node.size?.[1]) || 0;
                if (curH > COLLAPSED_H + 60) savedExpandedH = Math.max(EXPANDED_H, curH);
            }
            collapsed = Boolean(on);
            node.properties[COLLAPSED_PROP] = collapsed;
        }
        if (dockMode !== "node") return;
        root.classList.toggle("collapsed", collapsed);
        collapseBtn.textContent = collapsed ? "\u25be open" : "\u25b4 compact";
        const w = Math.max(1180, Number(node.size?.[0]) || WIDTH);
        node.setSize([w, collapsed ? COLLAPSED_H : Math.max(EXPANDED_H, savedExpandedH)]);
        node.graph?.setDirtyCanvas?.(true, true);
    }

    /* -- film / counts ---------------------------------------------------- */
    function syncFilm() {
        film.textContent = "";
        const list = shots();
        if (!list.length) {
            const emptyMsg = script.mode() === "simple"
                ? "Simple mode active \u2014 prompt drives the run (switch to Shots in Script for multi-hop filmstrip)"
                : "no shots \u2014 add one in Script";
            film.appendChild(el("span", "r2-film-empty", emptyMsg));
            return;
        }
        list.forEach((s, i) => {
            const b = el("button", "r2-poster" + (i === active ? " on" : "") + (s.locked ? " lk" : ""));
            b.type = "button";
            const deliv = deliveredSeconds(node, s, i);
            b.title = `${s.id || "s" + (i + 1)} \u00b7 ${durationOf(node, s)} (${deliv.toFixed(1)}s net)`;
            const th = el("span", "r2-th");
            const key = hopKey(node, i);
            if (key) {
                th.style.backgroundImage =
                    `linear-gradient(rgba(0,0,0,.15),rgba(0,0,0,.5)), url("${spriteURL(key, 1)}")`;
                th.style.backgroundSize = "cover";
            }
            const meta = el("span", "r2-pmeta");
            meta.append(el("b", null, String(i + 1)), el("span", "d", durationOf(node, s)));
            b.append(th, meta);
            b.addEventListener("click", () => {
                active = i;
                node.properties[SHOT_PROP] = i;
                script.setActive(i);
                stage.show(i);
                syncFilm();
                setTab("script");
            });
            film.appendChild(b);
        });
    }

    function setCount(id, value) {
        const text = value == null ? "" : String(value);
        const disp = value ? "" : "none";
        for (const map of [tabBtns, portalTabBtns]) {
            const b = map[id];
            if (!b) continue;
            b.count.textContent = text;
            b.count.style.display = disp;
        }
    }

    function syncCounts() {
        const list = shots();
        const ch = Math.max(1, Number(widgetByName(node, "chains")?.value) || 1);
        setCount("studio", (node.properties?.h3_mv_studio?.assets || []).length || "");
        setCount("script", script.mode() === "simple" ? `${ch} (S)` : list.length);
        setCount("refs", (refPlan?.refs || []).length);
        setCount("refmod", refModPane?.modCount?.() || "");
        setCount("timeline", list.length ? `${cachedCount(node, list)}/${list.length}` : "");
        setCount("media", mediaCount(node));
        setCount("write", "");
        setCount("swap", String(widgetByName(node, "swap_script")?.value || "").trim() ? "on" : "");
        setCount("standard", (refPlan?.refs || []).some((r) => r.file) ? "Ref2VA" : "T2VA");
        setCount("run", runPanel ? runPanel.ownedNames().length : "");
        footNext.textContent = list.length ? forecastText(node, list) : (script.mode() === "simple" ? `Simple mode \u00b7 ${ch} hop(s)` : "no shots");
        footCache.textContent = `${cachedCount(node, list)} cached`;
    }

    function syncDigest() {
        const txt = runPanel?.digestEl?.textContent || "";
        status.textContent = txt;
        portalStatus.textContent = txt;
    }

    /* -- refresh ---------------------------------------------------------- */
    function refreshAll() {
        refPlan = readRefs(node);
        refPlanRaw = String(widgetByName(node, "ref_plan")?.value ?? "");
        active = Math.min(active, Math.max(0, shots().length - 1));
        node.properties[SHOT_PROP] = active;
        script.refresh();
        stage.render();
        refRail.render();
        refModPane?.render?.();
        media.render();
        writer.restore?.();
        writer.syncHops?.();
        swap.render?.();
        standard.render?.();
        runPanel.sync();
        hideOwned();
        syncFilm();
        syncCounts();
        syncDigest();
        layout();
    }

    function restore() {
        const savedTab = node.properties?.[TAB_PROP];
        const savedShot = Number(node.properties?.[SHOT_PROP]);
        preset = node.properties?.[PRESET_PROP] === "retake" ? "retake" : "split";
        focus = Boolean(node.properties?.[FOCUS_PROP]);
        if (Number.isFinite(savedShot) && savedShot >= 0) active = savedShot;
        if (savedTab && TABS.some((t) => t.id === savedTab)) tab = savedTab;
        if (tab === "timeline") lastTab = "script";
        refreshAll();
        script.setActive(Math.min(active, Math.max(0, shots().length - 1)));
        renderPresetButtons();
        const savedCollapsed = Boolean(node.properties?.[COLLAPSED_PROP]);
        if (savedCollapsed !== collapsed) {
            setCollapsed(savedCollapsed);
        }
        const savedDock = node.properties?.[DOCK_PROP] || "node";
        if (savedDock !== dockMode) {
            setDockMode(savedDock);
        } else if (dockMode === "node" && !collapsed) {
            const curH = Number(node.size?.[1]) || 0;
            if (curH < EXPANDED_H) {
                const w = Math.max(1180, Number(node.size?.[0]) || WIDTH);
                node.setSize([w, EXPANDED_H]);
            }
        }
    }

    /* -- mount ------------------------------------------------------------ */
    const domWidget = node.addDOMWidget("h3_r2", "h3_r2", root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 140,
    });
    domWidget.serialize = false;

    const guard = installHeightGuard(node, domWidget, {
        minHeight: 140,
        minWidth: 1180,
        root,
        pinProp: "h3_r2_height_pin",
    });
    guard.setPinned(true);

    node._h3R2 = {
        root, portal, script, stage, refRail, refMod: refModPane, media, runPanel, writer, swap, standard,
        setTab, setPreset, setFocus, setCollapsed, setDockMode, refreshAll, hideOwned,
    };
    node._h3Editor = {
        refresh: restore,
        rail: refRail,
        refRail,
        script,
        editor: script,
        stage,
        timeline: stage,
        writer,
        swap,
        standard,
        runPanel,
        run: {
            render: () => {
                runPanel.sync();
                syncDigest();
                syncCounts();
            },
        },
        setTab,
        tabs: {
            active: () => tab,
            show: (id) => setTab(id),
        },
        getSurface: () => (tab === "run" ? "run" : "work"),
        setSurface: (s) => {
            if (s === "run") setTab("run");
            else if (tab === "run") setTab(lastTab || "script");
        },
    };

    const onQueued = () => {
        try {
            runPanel.sync();
            syncDigest();
            syncCounts();
            writer.refreshIfLoaded?.();
            setTimeout(() => {
                try {
                    writer.refreshIfLoaded?.();
                    standard.render?.();
                } catch (_) { /* */ }
            }, 2500);
        } catch (_) { /* */ }
    };
    api.addEventListener("promptQueued", onQueued);
    const prevRemoved = node.onRemoved;
    node.onRemoved = function (...args) {
        api.removeEventListener("promptQueued", onQueued);
        try { stage.destroy(); } catch (_) { /* */ }
        try { media.destroy?.(); } catch (_) { /* */ }
        try { swap.destroy?.(); } catch (_) { /* */ }
        try { portal.remove(); portalBackdrop.remove(); } catch (_) { /* */ }
        return prevRemoved?.apply(this, args);
    };

    hideOwned();
    refreshAll();
    setTab(tab, { restore: true });
    setCollapsed(collapsed);
    if (dockMode !== "node") setDockMode(dockMode);
    renderPresetButtons();

    /* Keyboard: 1 split, 2 retake, F focus, T timeline, D dock. */
    const onKey = (e) => {
        if (e.target && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        if (e.key === "1") setPreset("split");
        else if (e.key === "2") setPreset("retake");
        else if (e.key === "f" || e.key === "F") setFocus(!focus);
        else if (e.key === "t" || e.key === "T") {
            setTab(tab === "timeline" ? lastTab : "timeline");
        } else if (e.key === "d" || e.key === "D") {
            setDockMode(dockMode === "dock" ? "node" : "dock");
        } else if (e.key === "Escape" && dockMode !== "node") {
            setDockMode("node");
        }
    };
    root.addEventListener("keydown", onKey);
    portal.addEventListener("keydown", onKey);

    return node._h3R2;
}
