// HTC Steering Dials (MIT Clean-Room) — interactive Dial Rack + 2D X/Y Prompt Map.
// Backs the native ComfyUI widgets (`motion`, `expression`, `energy`, `mood_dial`,
// `mood_strength`, `scope`, `rack_json`) without altering `widgets_values` positions.
import { app } from "../../scripts/app.js";
import { el, button, widgetByName, hideWidget, isolateEvents } from "./editor/widget_utils.js";

const NODE = "HTCSteeringDials";
const DIALS_LIST_URL = "/h3_ref_chain/dials/list";
const STYLE_ID = "htc-steering-dials-style";

const CSS = `
.htcsd-root {
    --sd-bg: #0a0a0a;
    --sd-panel: #111111;
    --sd-sunken: #0d0d0d;
    --sd-border: #2a2a2a;
    --sd-border-soft: #1c1c1c;
    --sd-text: #e8e8e8;
    --sd-muted: #9a9a9a;
    --sd-faint: #6a6a6a;
    --sd-accent: #e8ff47;
    --sd-accent-soft: rgba(232,255,71,0.12);
    --sd-ok: #5fbf7a;
    --sd-warn: #ffb020;
    --sd-err: #ff453a;
    background: var(--sd-bg);
    color: var(--sd-text);
    border: 1px solid var(--sd-border);
    border-radius: 4px;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    font: 11.5px/1.35 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
    box-sizing: border-box;
    width: 100%;
    height: 100%;
    overflow-y: auto;
}
.htcsd-root * { box-sizing: border-box; }
.htcsd-head { display: flex; align-items: center; justify-content: space-between; gap: 6px; flex-wrap: wrap; }
.htcsd-title { font-size: 10.5px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--sd-accent); }
.htcsd-badge {
    font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;
    border: 1px solid rgba(232,255,71,0.45); background: var(--sd-accent-soft); color: var(--sd-accent);
    font-family: ui-monospace, Consolas, monospace;
}
.htcsd-grid { display: grid; grid-template-columns: 1.35fr 1fr; gap: 8px; align-items: start; }
.htcsd-col { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.htcsd-row {
    display: grid; grid-template-columns: 18px minmax(88px, 1fr) 1.2fr 44px 22px;
    align-items: center; gap: 5px; padding: 4px 6px;
    background: var(--sd-panel); border: 1px solid var(--sd-border-soft); border-radius: 3px;
}
.htcsd-row.is-muted { opacity: 0.45; }
.htcsd-row input[type="range"] { width: 100%; accent-color: var(--sd-accent); cursor: pointer; margin: 0; }
.htcsd-row input[type="checkbox"] { width: auto; accent-color: var(--sd-accent); cursor: pointer; margin: 0; }
.htcsd-row.is-hold { border-color: rgba(255,176,32,0.45); }
.htcsd-row.is-hold input[type="range"], .htcsd-row.is-hold .htcsd-num { opacity: 0.35; pointer-events: none; }
.htcsd-acts { display: inline-flex; align-items: center; gap: 3px; justify-content: flex-end; }
.htcsd-lbl { font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.htcsd-num { font-family: ui-monospace, Consolas, monospace; font-size: 10.5px; text-align: right; color: var(--sd-accent); }
.htcsd-btn {
    border: 1px solid var(--sd-border); background: var(--sd-sunken); color: var(--sd-text);
    border-radius: 3px; padding: 3px 7px; font: inherit; font-size: 10.5px; cursor: pointer;
}
.htcsd-btn:hover { border-color: var(--sd-accent); }
.htcsd-btn.on { border-color: var(--sd-warn); color: var(--sd-warn); background: rgba(255,176,32,0.14); }
.htcsd-sel {
    background: var(--sd-sunken); color: var(--sd-text); border: 1px solid var(--sd-border);
    border-radius: 3px; padding: 3px 5px; font: inherit; font-size: 11px; min-width: 0;
}
.htcsd-map-card {
    background: var(--sd-panel); border: 1px solid var(--sd-border-soft); border-radius: 3px; padding: 6px;
    display: flex; flex-direction: column; gap: 5px;
}
.htcsd-map-axes { display: grid; grid-template-columns: 1fr 14px 1fr; gap: 4px; align-items: center; }
.htcsd-map-pad {
    position: relative; width: min(100%, 168px); aspect-ratio: 1 / 1; margin: 0 auto;
    background: radial-gradient(circle at center, rgba(232,255,71,0.07) 0%, #08090b 74%);
    border: 1px solid var(--sd-border); border-radius: 3px; cursor: crosshair; overflow: hidden;
}
.htcsd-ring-ok {
    position: absolute; left: 50%; top: 50%; width: 44%; height: 44%; transform: translate(-50%,-50%);
    border: 1px dashed rgba(95,191,122,0.55); border-radius: 50%; pointer-events: none;
}
.htcsd-ring-warn {
    position: absolute; left: 50%; top: 50%; width: 72%; height: 72%; transform: translate(-50%,-50%);
    border: 1px dashed rgba(255,176,32,0.48); border-radius: 50%; pointer-events: none;
}
.htcsd-ax-x, .htcsd-ax-y { position: absolute; background: rgba(255,255,255,0.08); pointer-events: none; }
.htcsd-ax-x { left: 0; right: 0; top: 50%; height: 1px; }
.htcsd-ax-y { top: 0; bottom: 0; left: 50%; width: 1px; }
.htcsd-dot {
    position: absolute; width: 10px; height: 10px; border-radius: 50%;
    background: var(--sd-accent); border: 2px solid #0a0a0a;
    box-shadow: 0 0 0 2px rgba(232,255,71,0.35); transform: translate(-50%,-50%); pointer-events: none;
}
.htcsd-mlbl { position: absolute; font-size: 8.5px; color: var(--sd-faint); font-weight: 700; pointer-events: none; max-width: 72px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.htcsd-sub { font-size: 10px; color: var(--sd-muted); line-height: 1.3; }
.htcsd-foot { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; border-top: 1px solid var(--sd-border-soft); padding-top: 6px; }
`;

function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const st = document.createElement("style");
    st.id = STYLE_ID;
    st.textContent = CSS;
    document.head.appendChild(st);
}

function fmtSigned(v) {
    const n = Math.round(Number(v || 0) * 100) / 100;
    return (n > 0 ? "+" : "") + n.toFixed(2);
}

function mountSteeringDialsNode(node) {
    if (node._htcSteeringMounted) return;
    node._htcSteeringMounted = true;
    ensureStyle();

    const wMotion = widgetByName(node, "motion");
    const wExpr = widgetByName(node, "expression");
    const wEnergy = widgetByName(node, "energy");
    const wSound = widgetByName(node, "sound");
    const wMood = widgetByName(node, "mood_dial");
    const wMoodStr = widgetByName(node, "mood_strength");
    const wScope = widgetByName(node, "scope");
    const wRack = widgetByName(node, "rack_json");

    for (const w of [wMotion, wExpr, wEnergy, wSound, wMood, wMoodStr, wScope, wRack]) {
        if (w) hideWidget(w);
    }

    const root = el("div", "htcsd-root");
    isolateEvents(root);

    const head = el("div", "htcsd-head");
    head.appendChild(el("span", "htcsd-title", "🎛 HTC Steering Dials (H3)"));
    const pushBadge = el("span", "htcsd-badge", "Push: 0.00×");
    head.appendChild(pushBadge);
    root.appendChild(head);

    const grid = el("div", "htcsd-grid");
    const leftCol = el("div", "htcsd-col");
    const rightCol = el("div", "htcsd-col");
    grid.append(leftCol, rightCol);
    root.appendChild(grid);

    let dialCatalog = [];
    let mapAxisX = "motion";
    let mapAxisY = "expression";

    function findCatalogItem(file) {
        if (!file) return null;
        const norm = String(file).replace(/\\/g, "/").toLowerCase();
        return dialCatalog.find((d) => String(d.file || "").replace(/\\/g, "/").toLowerCase() === norm)
            || dialCatalog.find((d) => String(d.file || "").split("/").pop().toLowerCase() === norm.split("/").pop())
            || null;
    }

    function readRack() {
        try {
            const arr = JSON.parse(String(wRack?.value || "[]"));
            return Array.isArray(arr) ? arr : [];
        } catch {
            return [];
        }
    }
    function writeRack(arr) {
        if (!wRack) return;
        wRack.value = JSON.stringify(arr);
        try { wRack.callback?.(wRack.value, node.graph?.canvas, node); } catch (_) {}
        node.graph?.setDirtyCanvas?.(true, true);
    }
    function commit(w, val) {
        if (!w) return;
        w.value = val;
        try { w.callback?.(val, node.graph?.canvas, node); } catch (_) {}
        node.graph?.setDirtyCanvas?.(true, true);
    }

    function addSliderRow(container, label, tip, getVal, setVal, { onToggle = null, isOn = () => true, isHold = false, extraRight = null } = {}) {
        const row = el("div", "htcsd-row" + (isOn() ? "" : " is-muted") + (isHold ? " is-hold" : ""));
        const chk = document.createElement("input");
        chk.type = "checkbox";
        chk.checked = isOn();
        chk.addEventListener("change", () => {
            if (onToggle) onToggle(chk.checked);
            else if (!chk.checked) setVal(0);
            paint();
        });
        const lbl = el("span", "htcsd-lbl", label);
        lbl.title = tip;
        const rng = document.createElement("input");
        rng.type = "range";
        rng.min = "-2.5"; rng.max = "2.5"; rng.step = "0.05";
        rng.value = String(getVal());
        const num = el("span", "htcsd-num", isHold ? "HOLD" : fmtSigned(getVal()));
        rng.addEventListener("input", () => {
            const v = Number(rng.value) || 0;
            setVal(v);
            num.textContent = fmtSigned(v);
            if (Math.abs(v) >= 0.01 && !chk.checked) {
                chk.checked = true;
                onToggle?.(true);
            }
            updatePushAndMap();
        });
        const rst = button("0", "Reset to 0", () => {
            setVal(0);
            paint();
        }, "htcsd-btn");
        rst.style.padding = "1px 4px";
        rst.style.fontSize = "9.5px";
        row.append(chk, lbl, rng, num, extraRight || rst);
        container.appendChild(row);
    }

    function getMapAxesList() {
        const axes = [
            { id: "motion", label: "Motion", neg: "−Mot", pos: "+Mot", file: "htc_motion.safetensors", get: () => Number(wMotion?.value || 0), set: (v) => commit(wMotion, v) },
            { id: "expression", label: "Expression", neg: "−Exp", pos: "+Exp", file: "htc_expression.safetensors", get: () => Number(wExpr?.value || 0), set: (v) => commit(wExpr, v) },
            { id: "energy", label: "Energy", neg: "−Eng", pos: "+Eng", file: "htc_energy.safetensors", get: () => Number(wEnergy?.value || 0), set: (v) => commit(wEnergy, v) },
            { id: "sound", label: "Sound", neg: "−Hush", pos: "+Foley", file: "htc_sound.safetensors", get: () => Number(wSound?.value || 0), set: (v) => commit(wSound, v) },
            { id: "mood", label: "Extra Dial", neg: "−A", pos: "+B", file: wMood?.value || "", get: () => Number(wMoodStr?.value || 0), set: (v) => commit(wMoodStr, v) },
        ];
        const rack = readRack();
        rack.forEach((rec, idx) => {
            if (rec?.hold) return;
            const nm = String(rec?.file || `Rack ${idx + 1}`).replace(/\.safetensors$/i, "");
            axes.push({
                id: `rack:${idx}`,
                label: nm,
                neg: "−A",
                pos: "+B",
                file: rec?.file || "",
                get: () => Number(readRack()[idx]?.strength || 0),
                set: (v) => {
                    const next = readRack();
                    if (next[idx]) { next[idx].strength = v; next[idx].on = true; writeRack(next); }
                },
            });
        });
        for (const ax of axes) {
            const cat = findCatalogItem(ax.file);
            ax.useful = Math.max(0.25, Number(cat?.useful || 1.0));
            ax.overcook = Math.max(ax.useful, Number(cat?.overcook || 1.5));
            if (cat?.neg_label && cat.neg_label !== "−") ax.neg = "−" + String(cat.neg_label).split("/")[0].trim().slice(0, 9);
            if (cat?.pos_label && cat.pos_label !== "+") ax.pos = "+" + String(cat.pos_label).split("/")[0].trim().slice(0, 9);
        }
        return axes;
    }

    // 2D Map (selectable X × Y axes)
    const mapCard = el("div", "htcsd-map-card");
    const mapHead = el("div", "htcsd-head");
    const mapTitleEl = el("span", "htcsd-sub", "2D Map");
    const mapCoord = el("span", "htcsd-num", "0.00 · 0.00");
    mapHead.append(mapTitleEl, mapCoord);

    const mapAxesRow = el("div", "htcsd-map-axes");
    const axisXSel = el("select", "htcsd-sel");
    axisXSel.style.fontSize = "10px"; axisXSel.style.padding = "2px 4px";
    axisXSel.title = "Horizontal X axis";
    const axisYSel = el("select", "htcsd-sel");
    axisYSel.style.fontSize = "10px"; axisYSel.style.padding = "2px 4px";
    axisYSel.title = "Vertical Y axis";
    const crossLbl = el("span", "htcsd-sub", "×");
    crossLbl.style.textAlign = "center";
    mapAxesRow.append(axisXSel, crossLbl, axisYSel);
    axisXSel.addEventListener("change", () => { mapAxisX = axisXSel.value; updatePushAndMap(); });
    axisYSel.addEventListener("change", () => { mapAxisY = axisYSel.value; updatePushAndMap(); });

    const mapPad = el("div", "htcsd-map-pad");
    const ringWarn = el("div", "htcsd-ring-warn");
    const ringOk = el("div", "htcsd-ring-ok");
    mapPad.append(el("div", "htcsd-ax-x"), el("div", "htcsd-ax-y"), ringWarn, ringOk);
    const mapDot = el("div", "htcsd-dot");
    mapPad.appendChild(mapDot);
    const l1 = el("span", "htcsd-mlbl", "−Mot"); l1.style.left = "4px"; l1.style.top = "50%"; l1.style.transform = "translateY(-50%)";
    const l2 = el("span", "htcsd-mlbl", "+Mot"); l2.style.right = "4px"; l2.style.top = "50%"; l2.style.transform = "translateY(-50%)";
    const l3 = el("span", "htcsd-mlbl", "+Exp"); l3.style.top = "3px"; l3.style.left = "50%"; l3.style.transform = "translateX(-50%)";
    const l4 = el("span", "htcsd-mlbl", "−Exp"); l4.style.bottom = "3px"; l4.style.left = "50%"; l4.style.transform = "translateX(-50%)";
    mapPad.append(l1, l2, l3, l4);
    const mapNote = el("div", "htcsd-sub", "Drag dot inside green ellipse; Shift = fine; double-click resets.");
    mapCard.append(mapHead, mapAxesRow, mapPad, mapNote);
    rightCol.appendChild(mapCard);

    function mapPadRange(axX, axY) {
        return Math.max(2.0, Math.min(2.5, Math.max(axX?.overcook || 1.5, axY?.overcook || 1.5) * 1.35));
    }

    let dragState = null;
    function updateMapFromPointer(ev) {
        const axes = getMapAxesList();
        const axX = axes.find((a) => a.id === mapAxisX) || axes[0];
        const axY = axes.find((a) => a.id === mapAxisY) || axes[1];
        const R = mapPadRange(axX, axY);
        const r = mapPad.getBoundingClientRect();
        let vx, vy;
        if (ev.shiftKey && dragState) {
            const dx = ((ev.clientX - dragState.x) / r.width) * (2 * R) * 0.2;
            const dy = -((ev.clientY - dragState.y) / r.height) * (2 * R) * 0.2;
            vx = Math.max(-2.5, Math.min(2.5, Math.round((dragState.vx + dx) * 20) / 20));
            vy = Math.max(-2.5, Math.min(2.5, Math.round((dragState.vy + dy) * 20) / 20));
        } else {
            const nx = Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width));
            const ny = Math.max(0, Math.min(1, (ev.clientY - r.top) / r.height));
            vx = Math.round(((nx * 2 * R) - R) * 20) / 20;
            vy = Math.round((((1 - ny) * 2 * R) - R) * 20) / 20;
        }
        axX?.set(vx);
        axY?.set(vy);
        paint();
    }
    mapPad.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        const axes = getMapAxesList();
        const axX = axes.find((a) => a.id === mapAxisX) || axes[0];
        const axY = axes.find((a) => a.id === mapAxisY) || axes[1];
        dragState = { x: e.clientX, y: e.clientY, vx: axX?.get() || 0, vy: axY?.get() || 0 };
        updateMapFromPointer(e);
        const mv = (ev) => updateMapFromPointer(ev);
        const up = () => { dragState = null; window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); };
        window.addEventListener("pointermove", mv);
        window.addEventListener("pointerup", up);
    });
    mapPad.addEventListener("dblclick", () => {
        const axes = getMapAxesList();
        const axX = axes.find((a) => a.id === mapAxisX) || axes[0];
        const axY = axes.find((a) => a.id === mapAxisY) || axes[1];
        axX?.set(0);
        axY?.set(0);
        paint();
    });

    function syncAxisSelects() {
        const axes = getMapAxesList();
        if (!axes.some((a) => a.id === mapAxisX)) mapAxisX = "motion";
        if (!axes.some((a) => a.id === mapAxisY)) mapAxisY = "expression";
        for (const [sel, cur] of [[axisXSel, mapAxisX], [axisYSel, mapAxisY]]) {
            sel.textContent = "";
            for (const ax of axes) {
                const o = el("option", null, ax.label);
                o.value = ax.id;
                sel.appendChild(o);
            }
            sel.value = cur;
        }
    }

    function updatePushAndMap() {
        const mv = Number(wMotion?.value || 0);
        const ev = Number(wExpr?.value || 0);
        const en = Number(wEnergy?.value || 0);
        const sv = Number(wSound?.value || 0);
        const ms = (wMood?.value && wMood.value !== "None") ? Number(wMoodStr?.value || 0) : 0;
        const rack = readRack();
        const anySolo = rack.some((r) => r.on !== false && r.solo);
        let sq = mv * mv + ev * ev + en * en + sv * sv + ms * ms;
        let holdCount = 0;
        for (const r of rack) {
            if (r.on === false) continue;
            if (anySolo && !r.solo) continue;
            if (r.hold) { holdCount += 1; continue; }
            const rs = Number(r.strength || 0);
            sq += rs * rs;
        }
        pushBadge.textContent = `Push: ${Math.sqrt(sq).toFixed(2)}×` + (holdCount ? ` · ${holdCount}H` : "");
        const axes = getMapAxesList();
        const axX = axes.find((a) => a.id === mapAxisX) || axes[0];
        const axY = axes.find((a) => a.id === mapAxisY) || axes[1];
        const xv = axX ? axX.get() : 0;
        const yv = axY ? axY.get() : 0;
        const R = mapPadRange(axX, axY);
        const px = Math.max(4, Math.min(96, ((xv + R) / (2 * R)) * 100));
        const py = Math.max(4, Math.min(96, (1 - (yv + R) / (2 * R)) * 100));
        mapDot.style.left = px + "%";
        mapDot.style.top = py + "%";
        mapCoord.textContent = `${fmtSigned(xv)} · ${fmtSigned(yv)}`;
        l1.textContent = axX?.neg || "−X";
        l2.textContent = axX?.pos || "+X";
        l3.textContent = axY?.pos || "+Y";
        l4.textContent = axY?.neg || "−Y";
        ringOk.style.width = Math.min(96, (axX.useful / R) * 100) + "%";
        ringOk.style.height = Math.min(96, (axY.useful / R) * 100) + "%";
        ringWarn.style.width = Math.min(98, (axX.overcook / R) * 100) + "%";
        ringWarn.style.height = Math.min(98, (axY.overcook / R) * 100) + "%";
        const isEarlyScope = String(wScope?.value || "").startsWith("blocks_0_24");
        if (Math.abs(sv) >= 0.05 && isEarlyScope) {
            mapNote.textContent = "Sound active: switch Scope -> all_blocks to reach late audio blocks.";
            mapNote.style.color = "var(--sd-warn)";
        } else {
            mapNote.textContent = "Drag dot inside green ellipse; Shift = fine; double-click resets.";
            mapNote.style.color = "";
        }
    }

    // Footer: Scope + Mood Dial + Add Custom Rack Row
    const foot = el("div", "htcsd-foot");
    const scopeSel = el("select", "htcsd-sel");
    scopeSel.title = "Injection scope: Blocks 0-24 protects speech & skin detail; All 50 shifts refined prompt once across every block (best for Sound/Foley dials).";
    for (const optVal of (wScope?.options?.values || ["blocks_0_24 (voice safe)", "all_blocks"])) {
        const o = el("option", null, optVal);
        o.value = optVal;
        scopeSel.appendChild(o);
    }
    scopeSel.addEventListener("change", () => { commit(wScope, scopeSel.value); updatePushAndMap(); });

    const moodSel = el("select", "htcsd-sel");
    moodSel.style.flex = "1 1 130px";
    moodSel.title = "Quick additional .safetensors dial";
    moodSel.addEventListener("change", () => { commit(wMood, moodSel.value); updatePushAndMap(); syncAxisSelects(); });

    const addRackBtn = button("+ Rack Dial", "Add another .safetensors steering dial row", () => {
        const first = dialCatalog.find((d) => !readRack().some((r) => r.file === d.file))?.file
            || (wMood?.options?.values || []).find((x) => x && x !== "None")
            || "";
        if (!first) return;
        const next = readRack();
        next.push({ file: first, strength: 0.5, on: true, solo: false, hold: false });
        writeRack(next);
        paint();
    }, "htcsd-btn");

    foot.append(el("span", "htcsd-sub", "Scope:"), scopeSel, el("span", "htcsd-sub", "Extra:"), moodSel, addRackBtn);
    root.appendChild(foot);

    function syncMoodOptions() {
        const opts = (wMood?.options?.values && wMood.options.values.length)
            ? wMood.options.values
            : ["None", ...dialCatalog.map((d) => d.file)];
        moodSel.textContent = "";
        for (const fn of opts) {
            const cat = findCatalogItem(fn);
            const o = el("option", null, fn);
            o.value = fn;
            if (cat?.description) o.title = cat.description;
            moodSel.appendChild(o);
        }
        moodSel.value = wMood?.value || "None";
        const selCat = findCatalogItem(moodSel.value);
        if (selCat?.description) moodSel.title = selCat.description;
    }

    function paint() {
        leftCol.textContent = "";
        scopeSel.value = wScope?.value || "blocks_0_24 (voice safe)";
        syncMoodOptions();
        syncAxisSelects();

        addSliderRow(leftCol, "Motion", "Freeze (-2) ↔ Zoomies (+2)", () => Number(wMotion?.value || 0), (v) => commit(wMotion, v), { isOn: () => Math.abs(Number(wMotion?.value || 0)) >= 0.01 });
        addSliderRow(leftCol, "Expression", "Stoic (-2) ↔ Vivid (+2)", () => Number(wExpr?.value || 0), (v) => commit(wExpr, v), { isOn: () => Math.abs(Number(wExpr?.value || 0)) >= 0.01 });
        addSliderRow(leftCol, "Energy", "Hushed (-2) ↔ Peak (+2)", () => Number(wEnergy?.value || 0), (v) => commit(wEnergy, v), { isOn: () => Math.abs(Number(wEnergy?.value || 0)) >= 0.01 });
        if (wSound) {
            addSliderRow(leftCol, "Sound", "Hush / Quiet Air (-2.5) ↔ Vivid Rich Foley (+2.5)", () => Number(wSound?.value || 0), (v) => commit(wSound, v), { isOn: () => Math.abs(Number(wSound?.value || 0)) >= 0.01 });
        }
        addSliderRow(leftCol, "Extra Dial", "Strength for selected Extra dial", () => Number(wMoodStr?.value || 0), (v) => commit(wMoodStr, v), { isOn: () => (wMood?.value && wMood.value !== "None" && Math.abs(Number(wMoodStr?.value || 0)) >= 0.01) });

        const rack = readRack();
        rack.forEach((rec, idx) => {
            const cat = findCatalogItem(rec.file);
            const tip = cat?.description ? `${rec.file} — ${cat.description}` : (rec.file || "");
            const acts = el("span", "htcsd-acts");
            const hBtn = button("H", "Hold: orthogonalize combined post-refiner dials away from this direction", () => {
                const next = readRack();
                if (next[idx]) {
                    next[idx].hold = !next[idx].hold;
                    writeRack(next);
                    paint();
                }
            }, "htcsd-btn" + (rec.hold ? " on" : ""));
            hBtn.style.padding = "1px 4px";
            hBtn.style.fontSize = "9.5px";
            const rm = button("×", "Remove row", () => {
                const next = readRack();
                next.splice(idx, 1);
                writeRack(next);
                paint();
            }, "htcsd-btn");
            rm.style.padding = "1px 4px";
            acts.append(hBtn, rm);
            addSliderRow(
                leftCol,
                String(rec.file || "Dial").replace(/\.safetensors$/i, ""),
                tip,
                () => Number(rec.strength || 0),
                (v) => {
                    const next = readRack();
                    if (next[idx]) { next[idx].strength = v; writeRack(next); }
                },
                {
                    isOn: () => rec.on !== false,
                    isHold: Boolean(rec.hold),
                    onToggle: (on) => {
                        const next = readRack();
                        if (next[idx]) { next[idx].on = on; writeRack(next); }
                    },
                    extraRight: acts,
                },
            );
        });
        updatePushAndMap();
    }

    const domW = node.addDOMWidget("htc_steering_dials_ui", "HTCSteeringDials", root, {
        serialize: false,
        hideOnZoom: false,
    });
    if (domW) {
        domW.computeSize = (w) => [Math.max(480, w || 540), Math.max(295, 255 + readRack().length * 32)];
    }

    fetch(DIALS_LIST_URL).then((r) => r.json()).then((j) => {
        if (j?.ok && Array.isArray(j.dials)) {
            dialCatalog = j.dials;
            paint();
        }
    }).catch(() => {});

    const origCfg = node.onConfigure;
    node.onConfigure = function (...args) {
        const res = origCfg?.apply(this, args);
        paint();
        return res;
    };

    paint();
    node.setSize([Math.max(520, Number(node.size?.[0]) || 540), Math.max(300, Number(node.size?.[1]) || 310)]);
}

app.registerExtension({
    name: "HandTieClips.SteeringDials",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE) return;
        const orig = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const res = orig?.apply(this, arguments);
            try { mountSteeringDialsNode(this); } catch (err) { console.error("[HTCSteeringDials] mount failed:", err); }
            return res;
        };
    },
});
