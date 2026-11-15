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
.htcsd-map-pad {
    position: relative; width: min(100%, 156px); aspect-ratio: 1 / 1; margin: 0 auto;
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
.htcsd-mlbl { position: absolute; font-size: 9px; color: var(--sd-faint); font-weight: 700; pointer-events: none; }
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
    const wMood = widgetByName(node, "mood_dial");
    const wMoodStr = widgetByName(node, "mood_strength");
    const wScope = widgetByName(node, "scope");
    const wRack = widgetByName(node, "rack_json");

    for (const w of [wMotion, wExpr, wEnergy, wMood, wMoodStr, wScope, wRack]) {
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

    function addSliderRow(container, label, tip, getVal, setVal, { onToggle = null, isOn = () => true, extraRight = null } = {}) {
        const row = el("div", "htcsd-row" + (isOn() ? "" : " is-muted"));
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
        const num = el("span", "htcsd-num", fmtSigned(getVal()));
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

    // 2D Map (X = Motion, Y = Expression)
    const mapCard = el("div", "htcsd-map-card");
    const mapHead = el("div", "htcsd-head");
    mapHead.appendChild(el("span", "htcsd-sub", "2D Map (Motion × Expr)"));
    const mapCoord = el("span", "htcsd-num", "0.00 · 0.00");
    mapHead.appendChild(mapCoord);
    const mapPad = el("div", "htcsd-map-pad");
    mapPad.append(el("div", "htcsd-ax-x"), el("div", "htcsd-ax-y"), el("div", "htcsd-ring-warn"), el("div", "htcsd-ring-ok"));
    const mapDot = el("div", "htcsd-dot");
    mapPad.appendChild(mapDot);
    const l1 = el("span", "htcsd-mlbl", "−Mot"); l1.style.left = "4px"; l1.style.top = "50%"; l1.style.transform = "translateY(-50%)";
    const l2 = el("span", "htcsd-mlbl", "+Mot"); l2.style.right = "4px"; l2.style.top = "50%"; l2.style.transform = "translateY(-50%)";
    const l3 = el("span", "htcsd-mlbl", "+Exp"); l3.style.top = "3px"; l3.style.left = "50%"; l3.style.transform = "translateX(-50%)";
    const l4 = el("span", "htcsd-mlbl", "−Exp"); l4.style.bottom = "3px"; l4.style.left = "50%"; l4.style.transform = "translateX(-50%)";
    mapPad.append(l1, l2, l3, l4);
    const mapNote = el("div", "htcsd-sub", "Drag dot inside green ring (0.5..1.0 sweet spot); double-click resets.");
    mapCard.append(mapHead, mapPad, mapNote);
    rightCol.appendChild(mapCard);

    function updateMapFromPointer(ev) {
        const r = mapPad.getBoundingClientRect();
        const nx = Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width));
        const ny = Math.max(0, Math.min(1, (ev.clientY - r.top) / r.height));
        const vx = Math.round(((nx * 4) - 2) * 20) / 20;
        const vy = Math.round((((1 - ny) * 4) - 2) * 20) / 20;
        commit(wMotion, vx);
        commit(wExpr, vy);
        paint();
    }
    mapPad.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        updateMapFromPointer(e);
        const mv = (ev) => updateMapFromPointer(ev);
        const up = () => { window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); };
        window.addEventListener("pointermove", mv);
        window.addEventListener("pointerup", up);
    });
    mapPad.addEventListener("dblclick", () => {
        commit(wMotion, 0);
        commit(wExpr, 0);
        paint();
    });

    function updatePushAndMap() {
        const mv = Number(wMotion?.value || 0);
        const ev = Number(wExpr?.value || 0);
        const en = Number(wEnergy?.value || 0);
        const ms = (wMood?.value && wMood.value !== "None") ? Number(wMoodStr?.value || 0) : 0;
        const rack = readRack();
        const anySolo = rack.some((r) => r.on !== false && r.solo);
        let sq = mv * mv + ev * ev + en * en + ms * ms;
        for (const r of rack) {
            if (r.on === false) continue;
            if (anySolo && !r.solo) continue;
            const rs = Number(r.strength || 0);
            sq += rs * rs;
        }
        pushBadge.textContent = `Push: ${Math.sqrt(sq).toFixed(2)}×`;
        const px = Math.max(4, Math.min(96, ((mv + 2) / 4) * 100));
        const py = Math.max(4, Math.min(96, (1 - (ev + 2) / 4) * 100));
        mapDot.style.left = px + "%";
        mapDot.style.top = py + "%";
        mapCoord.textContent = `${fmtSigned(mv)} · ${fmtSigned(ev)}`;
    }

    // Footer: Scope + Mood Dial + Add Custom Rack Row
    const foot = el("div", "htcsd-foot");
    const scopeSel = el("select", "htcsd-sel");
    scopeSel.title = "Injection scope: Blocks 0-24 protects speech & skin detail; All 50 shifts post-refiner once.";
    for (const optVal of (wScope?.options?.values || ["blocks_0_24 (voice safe)", "all_blocks"])) {
        const o = el("option", null, optVal);
        o.value = optVal;
        scopeSel.appendChild(o);
    }
    scopeSel.addEventListener("change", () => commit(wScope, scopeSel.value));

    const moodSel = el("select", "htcsd-sel");
    moodSel.style.flex = "1 1 130px";
    moodSel.title = "Quick additional .safetensors dial";
    moodSel.addEventListener("change", () => { commit(wMood, moodSel.value); updatePushAndMap(); });

    const addRackBtn = button("+ Rack Dial", "Add another .safetensors steering dial row", () => {
        const first = dialCatalog.find((d) => !readRack().some((r) => r.file === d.file))?.file
            || (wMood?.options?.values || []).find((x) => x && x !== "None")
            || "";
        if (!first) return;
        const next = readRack();
        next.push({ file: first, strength: 0.5, on: true, solo: false });
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
            const o = el("option", null, fn);
            o.value = fn;
            moodSel.appendChild(o);
        }
        moodSel.value = wMood?.value || "None";
    }

    function paint() {
        leftCol.textContent = "";
        scopeSel.value = wScope?.value || "blocks_0_24 (voice safe)";
        syncMoodOptions();

        addSliderRow(leftCol, "Motion", "Freeze (-2) ↔ Zoomies (+2)", () => Number(wMotion?.value || 0), (v) => commit(wMotion, v), { isOn: () => Math.abs(Number(wMotion?.value || 0)) >= 0.01 });
        addSliderRow(leftCol, "Expression", "Stoic (-2) ↔ Vivid (+2)", () => Number(wExpr?.value || 0), (v) => commit(wExpr, v), { isOn: () => Math.abs(Number(wExpr?.value || 0)) >= 0.01 });
        addSliderRow(leftCol, "Energy", "Hushed (-2) ↔ Peak (+2)", () => Number(wEnergy?.value || 0), (v) => commit(wEnergy, v), { isOn: () => Math.abs(Number(wEnergy?.value || 0)) >= 0.01 });
        addSliderRow(leftCol, "Extra Dial", "Strength for selected Extra dial", () => Number(wMoodStr?.value || 0), (v) => commit(wMoodStr, v), { isOn: () => (wMood?.value && wMood.value !== "None" && Math.abs(Number(wMoodStr?.value || 0)) >= 0.01) });

        const rack = readRack();
        rack.forEach((rec, idx) => {
            const rm = button("×", "Remove row", () => {
                const next = readRack();
                next.splice(idx, 1);
                writeRack(next);
                paint();
            }, "htcsd-btn");
            rm.style.padding = "1px 4px";
            addSliderRow(
                leftCol,
                String(rec.file || "Dial").replace(/\.safetensors$/i, ""),
                rec.file || "",
                () => Number(rec.strength || 0),
                (v) => {
                    const next = readRack();
                    if (next[idx]) { next[idx].strength = v; writeRack(next); }
                },
                {
                    isOn: () => rec.on !== false,
                    onToggle: (on) => {
                        const next = readRack();
                        if (next[idx]) { next[idx].on = on; writeRack(next); }
                    },
                    extraRight: rm,
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
        domW.computeSize = (w) => [Math.max(460, w || 520), Math.max(255, 220 + readRack().length * 32)];
    }

    fetch(DIALS_LIST_URL).then((r) => r.json()).then((j) => {
        if (j?.ok && Array.isArray(j.dials)) {
            dialCatalog = j.dials;
            syncMoodOptions();
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
