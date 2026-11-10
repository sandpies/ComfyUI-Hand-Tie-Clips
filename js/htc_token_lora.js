// H3 Token LoRA (HTC): compact slot panel.
//
// The node's own widgets stay the source of truth and are what the workflow
// saves (widgets_values order = INPUT_TYPES order). This panel only changes
// what is shown: one row per LoRA slot (on/off box, file picker, gear for the
// eight settings, remove), an "Add LoRA" button that opens slot B, then C, then
// D, E, ... (kept as JSON in `extra_loras`), and the two global combos at the
// foot. Slots switched off are listed in `disabled_loras`.
import { app } from "../../scripts/app.js";

const NODE = "HTCTokenLoRA";
const NONE = "None";
const PROP = "htc_token_lora";
const FIELDS = ["video", "audio", "reference", "text", "refiner", "block_start", "block_end"];
const LABELS = ["Video", "Audio", "Reference", "Text", "Refiner", "Block start", "Block end"];
const EXTRA = { lora_name: NONE, video: 1, audio: 0, reference: -1, text: 0, refiner: 0,
                block_start: 0, block_end: 49, all_tokens: false };
const BOX = 16, BTN = 24, PAD = 6;

export function letterOf(index) {
    let s = "";
    for (let n = index + 1; n; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + (n - 1) % 26) + s;
    return s;
}

// Row layout (x relative to the node, y relative to the row top).
export function rowParts(width, height = 20) {
    const cy = height / 2;
    return {
        box: [12, cy - BOX / 2, BOX, BOX],
        remove: [width - 2 * BTN - 2 * PAD - 4, cy - 10, BTN, 20],
        gear: [width - BTN - PAD - 4, cy - 10, BTN, 20],
        combo: [12 + BOX + PAD, 0, width - (12 + BOX + PAD) - (2 * BTN + 2 * PAD + 8), height],
    };
}

const hit = (x, y, r) => r && x >= r[0] && x < r[0] + r[2] && y >= r[1] && y < r[1] + r[3];

export function rowHit(x, y, width, height = 20) {
    const p = rowParts(width, height);
    for (const k of ["box", "remove", "gear"]) if (hit(x, y, p[k])) return k;
    if (!hit(x, y, p.combo)) return null;
    if (x < p.combo[0] + 22) return "prev";
    if (x > p.combo[0] + p.combo[2] - 22) return "next";
    return "pick";
}

export class Panel {
    constructor(node) {
        this.node = node;
        this.native = [...node.widgets];
        this.byName = new Map(this.native.map((w) => [w.name, w]));
        this.extrasW = this.byName.get("extra_loras");
        this.disabledW = this.byName.get("disabled_loras");
        this.slots = [];
        this.extraUI = [];
        this.records = [];
        this.disabled = new Set();
        this.badJson = false;
        for (const L of ["A", "B", "C"]) {
            const p = L.toLowerCase();
            const file = this.byName.get(`lora_${p}`);
            const settings = FIELDS.map((f) => this.byName.get(`${p}_${f}`));
            settings.forEach((w, i) => { w.label = `${L} ${LABELS[i]}`; });
            this.slots.push(this.makeSlot(L, file, settings, false));
            const cb = file.callback;
            file.callback = (...a) => { cb?.apply(file, a); this.refresh(); };
        }
        // The real other_keys / add_mode widgets must keep their place: the saved
        // widgets_values are positional, so moving them shifts every value after
        // them onto the wrong widget. They stay hidden in place; UI-only stand-ins
        // (serialize false) sit at the foot and write through.
        this.footViews = ["other_keys", "add_mode"].map((name) => {
            const real = this.byName.get(name);
            const view = this.ui("combo", `${name} view`, real.value, (v) => {
                if (this.linked(real)) { this.refresh(); return; }
                real.value = v;
                real.callback?.(v);
            }, { ...real.options });
            view.label = name === "other_keys" ? "Other keys" : "Add mode";
            return { real, view };
        });
        this.addBtn = this.ui("button", "Add LoRA", null, () => this.add());
        for (const w of [this.extrasW, this.disabledW]) {
            const cb = w.callback;
            w.callback = (...a) => { cb?.apply(w, a); this.load(); };
        }
        const onConfigure = node.onConfigure;
        node.onConfigure = (...a) => { onConfigure?.apply(node, a); this.load(); };
        const onConn = node.onConnectionsChange;
        node.onConnectionsChange = (...a) => { onConn?.apply(node, a); this.refresh(); };
        this.load();
    }

    get state() {
        const props = this.node.properties ??= {};
        return props[PROP] ??= { open: ["A"], expanded: [] };
    }

    ui(type, name, value, callback, options = {}) {
        const w = this.node.addWidget(type, name, value, callback, { ...options, serialize: false });
        w.serialize = false;
        return w;
    }

    linked(w) {
        return this.node.inputs?.some((inp, i) => inp.widget?.name === w.name && this.node.isInputConnected(i)) ?? false;
    }

    slotLinked(slot) {
        return [slot.file, ...slot.settings].some((w) => this.linked(w));
    }

    makeSlot(L, file, settings, extra) {
        const slot = { L, file, settings, extra };
        // A UI-only combo draws the row; for A/B/C the real file widget stays
        // hidden (it may be converted to an input), for extras it is the row.
        slot.row = extra ? file : this.ui("combo", `${L} row`, file.value, (v) => {
            file.value = v;
            file.callback?.(v);
        }, { ...file.options });
        slot.row.label = `LoRA ${L}`;
        this.decorate(slot);
        return slot;
    }

    decorate(slot) {
        const row = slot.row;
        row.draw = (ctx, node, width, y, height, lowQuality) => {
            slot.geom = { width, y, height };
            const p = rowParts(width, height);
            const off = this.disabled.has(slot.L);
            const outline = row.getOutlineColor();
            const text = row.text_color;
            // the file picker, inset between the box and the buttons
            ctx.save();
            ctx.translate(p.combo[0], y - row.y);
            if (off) ctx.globalAlpha *= 0.45;
            row.drawWidget(ctx, { width: p.combo[2], showText: !lowQuality });
            ctx.restore();
            ctx.save();
            ctx.translate(0, y);
            ctx.lineWidth = 1;
            // on/off box
            ctx.strokeStyle = outline;
            ctx.fillStyle = row.background_color;
            ctx.beginPath(); ctx.roundRect(...p.box, 3); ctx.fill(); ctx.stroke();
            if (!off) {
                ctx.strokeStyle = text; ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(p.box[0] + 3, p.box[1] + 8); ctx.lineTo(p.box[0] + 7, p.box[1] + 12);
                ctx.lineTo(p.box[0] + 13, p.box[1] + 4); ctx.stroke();
                ctx.lineWidth = 1;
            }
            // remove
            ctx.strokeStyle = outline;
            ctx.beginPath(); ctx.roundRect(...p.remove, 4); ctx.fill(); ctx.stroke();
            ctx.save();
            if (!this.canRemove(slot)) ctx.globalAlpha *= 0.3;
            const rx = p.remove[0] + BTN / 2, ry = p.remove[1] + 10;
            ctx.strokeStyle = "#e46b6b"; ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(rx - 4, ry - 4); ctx.lineTo(rx + 4, ry + 4);
            ctx.moveTo(rx + 4, ry - 4); ctx.lineTo(rx - 4, ry + 4); ctx.stroke();
            ctx.restore();
            // gear (settings)
            const open = this.state.expanded.includes(slot.L);
            ctx.strokeStyle = open ? text : outline;
            ctx.beginPath(); ctx.roundRect(...p.gear, 4); ctx.fill(); ctx.stroke();
            const gx = p.gear[0] + BTN / 2, gy = p.gear[1] + 10;
            ctx.strokeStyle = text;
            ctx.beginPath();
            for (let i = 0; i <= 16; i++) {
                const a = i * Math.PI / 8, r = i % 2 ? 7 : 5;
                ctx[i ? "lineTo" : "moveTo"](gx + Math.cos(a) * r, gy + Math.sin(a) * r);
            }
            ctx.stroke();
            ctx.beginPath(); ctx.arc(gx, gy, 2, 0, 2 * Math.PI); ctx.stroke();
            ctx.restore();
        };
        row.onPointerDown = (pointer, node, canvas) => {
            if (row.hidden || (pointer.eDown && pointer.eDown.button !== 0)) return true;
            const g = slot.geom ?? { width: node.size[0], y: row.y, height: 20 };
            const x = canvas.graph_mouse[0] - node.pos[0];
            const y = canvas.graph_mouse[1] - node.pos[1] - g.y;
            const what = rowHit(x, y, g.width, g.height);
            if (!what) return true;   // gaps: swallow, or the full-width combo opens
            pointer.onClick = (e) => {
                if (row.hidden || !this.slots.includes(slot)) return;
                if (what === "box") this.setOn(slot.L, this.disabled.has(slot.L));
                else if (what === "gear") this.toggle(slot.L);
                else if (what === "remove") this.remove(slot.L);
                else if (!this.linked(slot.file)) {
                    const opts = { e, node, canvas };
                    if (what === "prev") row.decrementValue(opts);
                    else if (what === "next") row.incrementValue(opts);
                    else {
                        // the native combo re-checks its arrows from the raw event:
                        // present the click at the node's centre
                        const cx = e.canvasX;
                        e.canvasX = node.pos[0] + (row.width || node.size[0]) / 2;
                        try { row.onClick(opts); } finally { e.canvasX = cx; }
                    }
                }
            };
            return true;
        };
    }

    // --- extras (D, E, ...) ------------------------------------------------
    load() {
        this.slots = this.slots.filter((s) => !s.extra);
        this.node.widgets = this.node.widgets.filter((w) => !this.extraUI.includes(w));
        this.extraUI = [];
        this.records = [];
        this.badJson = false;
        try {
            const recs = JSON.parse(this.extrasW.value);
            if (!Array.isArray(recs) || recs.some((r) => !r || typeof r !== "object" || Array.isArray(r))) throw new TypeError();
            this.records = recs.map((r) => ({ ...EXTRA, ...r }));
        } catch (err) {
            if (!(err instanceof SyntaxError || err instanceof TypeError)) throw err;
            this.badJson = true;   // leave the saved text editable, never replace it
        }
        this.records.forEach((r, i) => this.makeExtra(r, i));
        this.disabled = new Set();
        try {
            const d = JSON.parse(this.disabledW.value);
            if (!Array.isArray(d) || d.some((L) => !this.slots.some((s) => s.L === L))) throw new TypeError();
            this.disabled = new Set(d);
        } catch (err) {
            if (!(err instanceof SyntaxError || err instanceof TypeError)) throw err;
            this.badJson = true;
        }
        this.refresh();
    }

    makeExtra(rec, index) {
        const L = letterOf(index + 3);
        const made = [];
        const add = (type, field, options) => {
            const w = this.ui(type, `${L} ${field}`, rec[field], (v) => { rec[field] = v; this.writeExtras(); }, options);
            made.push(w);
            return w;
        };
        const file = add("combo", "lora_name", { ...this.byName.get("lora_c").options });
        const settings = FIELDS.map((f, i) => {
            const tpl = this.byName.get(`c_${f}`);
            const w = add(tpl.type, f, { ...tpl.options });
            w.label = `${L} ${LABELS[i]}`;
            return w;
        });
        const all = add("toggle", "all_tokens", { on: "all tokens", off: "skip",
            tooltip: "This slot's parts that cannot be split by token: apply everywhere at 1.0, or skip." });
        all.label = `${L} Other keys`;
        settings.push(all);
        this.slots.push(this.makeSlot(L, file, settings, true));
        this.extraUI.push(...made);
    }

    writeExtras() {
        this.extrasW.value = JSON.stringify(this.records);
        this.node.setDirtyCanvas?.(true, true);
    }

    writeDisabled() {
        this.disabledW.value = JSON.stringify([...this.disabled]);
    }

    // --- actions -------------------------------------------------------------
    setOn(L, on) {
        if (this.badJson || this.linked(this.disabledW)) return;
        if (on) this.disabled.delete(L); else this.disabled.add(L);
        this.writeDisabled();
        this.refresh();
        this.node.graph?.incrementVersion();
    }

    toggle(L) {
        const ex = this.state.expanded, i = ex.indexOf(L);
        if (i < 0) ex.push(L); else ex.splice(i, 1);
        this.refresh();
        this.node.graph?.incrementVersion();
    }

    add() {
        if (this.badJson) return;
        for (const L of ["B", "C"]) {
            const slot = this.slots.find((s) => s.L === L);
            if (!this.state.open.includes(L) && !this.slotLinked(slot)) {
                this.state.open.push(L);
                this.refresh();
                return;
            }
        }
        if (this.linked(this.extrasW)) return;
        const rec = { ...EXTRA };
        this.records.push(rec);
        this.writeExtras();
        this.makeExtra(rec, this.records.length - 1);
        this.refresh();
        this.node.graph?.incrementVersion();
    }

    canRemove(slot) {
        return slot.L !== "A" && !this.slotLinked(slot) && !this.badJson && !this.linked(this.disabledW)
            && !(slot.extra && this.linked(this.extrasW));
    }

    remove(L) {
        const slot = this.slots.find((s) => s.L === L);
        if (!slot || !this.canRemove(slot)) return;
        if (slot.extra) {
            const idx = this.slots.filter((s) => s.extra).indexOf(slot);
            this.records.splice(idx, 1);
            // letters after the removed slot move down one
            const shift = (letters) => letters.flatMap((name) => {
                const pos = this.slots.findIndex((s) => s.L === name);
                if (pos < idx + 3) return [name];
                if (pos === idx + 3) return [];
                return [letterOf(pos - 1)];
            });
            this.state.open = shift(this.state.open);
            this.state.expanded = shift(this.state.expanded);
            this.disabled = new Set(shift([...this.disabled]));
            this.writeDisabled();
            this.writeExtras();
            this.load();
        } else {
            slot.file.value = NONE;
            this.disabled.delete(L);
            this.writeDisabled();
            slot.file.callback?.(NONE);
            this.state.open = this.state.open.filter((n) => n !== L);
            this.state.expanded = this.state.expanded.filter((n) => n !== L);
            this.refresh();
        }
        this.node.graph?.incrementVersion();
    }

    // --- layout --------------------------------------------------------------
    refresh() {
        const open = new Set(this.state.open);
        open.add("A");
        const expanded = new Set(this.state.expanded);
        for (const s of this.slots) {
            if (s.extra || this.slotLinked(s) || (s.file.value && s.file.value !== NONE)) open.add(s.L);
            const show = open.has(s.L);
            s.row.hidden = !show;
            s.row.value = s.file.value;
            s.file.hidden = !show || (!s.extra && !this.linked(s.file));
            for (const w of s.settings) w.hidden = !show || (!expanded.has(s.L) && !this.linked(w));
        }
        this.state.open = [...open];
        // native widgets keep their saved order (never move one: widgets_values is
        // positional); UI-only rows sit right before their file widget
        const ordered = [];
        const foot = [];
        for (const { real, view } of this.footViews) {
            real.hidden = !this.linked(real);
            view.hidden = this.linked(real);
            view.value = real.value;
            foot.push(view);
        }
        for (const w of this.native) {
            const s = this.slots.find((x) => !x.extra && x.file === w);
            if (s) ordered.push(s.row);
            ordered.push(w);
        }
        for (const s of this.slots.filter((x) => x.extra)) ordered.push(s.file, ...s.settings);
        ordered.push(this.addBtn, ...foot);
        ordered.push(...this.node.widgets.filter((w) => !ordered.includes(w)));
        this.extrasW.hidden = !this.badJson && !this.linked(this.extrasW);
        this.disabledW.hidden = !this.badJson && !this.linked(this.disabledW);
        this.addBtn.disabled = this.badJson;
        this.node.widgets = ordered;
        const [w, h] = this.node.computeSize();
        this.node.setSize([Math.max(340, this.node.size[0], w), h]);
        for (const s of this.slots) s.row.triggerDraw?.();
        this.node.setDirtyCanvas?.(true, true);
    }
}

app.registerExtension({
    name: "HTC.TokenLoRA",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE) return;
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...a) {
            const r = onNodeCreated?.apply(this, a);
            new Panel(this);
            return r;
        };
    },
});
