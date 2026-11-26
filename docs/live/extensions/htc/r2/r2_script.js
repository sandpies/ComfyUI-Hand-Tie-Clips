/**
 * Round-2 Script pane.
 *
 * One active hop at a time, with a visible hop selector. The plan editor's
 * cards are replaced by chips + a single editor, but `shot_plan` stays the only
 * store: every edit writes planToJson back through the native widget callback.
 */

import { el, button, vocab, onVocabRefresh, widgetByName } from "../editor/widget_utils.js";
import { parsePlan, planToJson } from "../editor/plan_editor.js";
import { createTemplatePanel } from "../editor/templates.js";
import {
    AXES, readPlan, writePlan, readPrompt, writePrompt, freeId, blankShot,
    durationOf, deliveredSeconds, refsForShot, readRefs,
} from "./r2_store.js";

const MODE_PROP = "h3_editor_mode";
const SHOT_PROP = "h3_r2_shot";
const BACKUP_PROP = "h3_plan_backup";

const AXIS_LABEL = {
    camera: "camera", framing: "framing", pace: "pace", join: "join", tail: "tail",
};

function coherenceWarning(shot, index, shots) {
    if (index === 0) return null;
    const d = shot?.directives || {};
    const framing = d.framing || "";
    const camera = d.camera || "";
    if (d.join !== "continuous" || !framing || framing === "keep") return null;
    if (camera && camera !== "hold") return null;
    let prev = "";
    for (let i = index - 1; i >= 0; i -= 1) {
        const f = (((shots || [])[i] || {}).directives || {}).framing || "";
        if (f && f !== "keep") { prev = f; break; }
    }
    if (!prev || prev === framing) return null;
    return `join=continuous changes framing from ${prev} to ${framing} with a held `
        + "camera, which implies a cut. Use push_in / pull_back / pan_follow to "
        + "reach that framing on the move, or framing=keep.";
}

function directionWarning(shot) {
    const d = shot?.directives || {};
    const pair = `${d.camera || ""}|${d.framing || ""}`;
    if (pair === "push_in|wide" || pair === "pull_back|close") {
        return `camera=${d.camera} moves the opposite way from framing=${d.framing}. `
            + "Pick the framing the move actually lands on.";
    }
    return null;
}

export function createScriptPane(node, { onChange, onSelect } = {}) {
    let shots = [];
    let active = Math.max(0, Number(node.properties?.[SHOT_PROP]) || 0);
    let mode = node.properties?.[MODE_PROP] === "simple" ? "simple" : "shots";
    let bad = false;
    let rawPlan = "";
    let V = null;
    let busy = false;
    let beatTimer = 0;
    let promptTimer = 0;

    const root = el("div", "r2-script");

    /* -- header ----------------------------------------------------------- */
    const head = el("div", "r2-script-head");
    head.appendChild(el("span", "title", "Script"));
    const count = el("span", "sub");
    head.appendChild(count);
    const spacer = el("span", "spacer");
    head.appendChild(spacer);

    const modeBox = el("span", "r2-mode");
    const shotBtn = el("button", null, "Shots");
    const simpleBtn = el("button", null, "Simple");
    shotBtn.type = simpleBtn.type = "button";
    modeBox.append(shotBtn, simpleBtn);
    head.appendChild(modeBox);

    const addBtn = el("button", "r2-mini", "+ shot");
    addBtn.type = "button";
    head.appendChild(addBtn);

    const templates = createTemplatePanel({
        onPick: (picked) => {
            flush();
            if (mode === "shots") {
                for (const sh of picked) {
                    shots.push({ ...blankShot(shots.length), ...sh, id: freeId(shots) });
                }
                writePlan(node, shots);
                active = Math.max(0, shots.length - 1);
                persistActive();
                render();
                onSelect?.(active);
                onChange?.();
            } else {
                const blocks = picked
                    .map((sh) => String(sh.beat || sh.prose || "").trim())
                    .filter(Boolean);
                if (blocks.length) {
                    const existing = String(promptEl.value || "").trim();
                    const joined = (existing ? [existing] : []).concat(blocks).join("\n\n---\n\n");
                    promptEl.value = joined;
                    writePrompt(node, joined);
                    renderSimpleBlocks();
                    onChange?.();
                }
            }
            templates.hide();
            tplBtn.classList.remove("on");
        },
    });
    const tplBtn = el("button", "r2-mini", "Templates");
    tplBtn.type = "button";
    tplBtn.title = "Insert a ready-made pattern. Appends, and stays in the mode you are in.";
    tplBtn.addEventListener("click", () => {
        tplBtn.classList.toggle("on", templates.toggle());
    });
    head.appendChild(tplBtn);

    root.appendChild(head);
    root.appendChild(templates.root);

    /* -- hop selector ----------------------------------------------------- */
    const chips = el("div", "r2-chips");
    root.appendChild(chips);

    /* -- active shot editor ----------------------------------------------- */
    const editor = el("div", "r2-shot-editor");

    const row = el("div", "r2-shot-row");
    const noEl = el("span", "r2-no", "1");
    const idEl = el("b", "r2-id", "s1");
    const durChip = el("span", "r2-chip", "15 s");
    const lockBtn = el("button", "r2-chip r2-lock", "lock");
    lockBtn.type = "button";
    const seedNote = el("span", "r2-muted");
    const dupBtn = el("button", "r2-mini", "duplicate");
    const delBtn = el("button", "r2-mini r2-danger", "delete");
    dupBtn.type = delBtn.type = "button";
    row.append(noEl, idEl, durChip, lockBtn, el("span", "spacer"), seedNote, dupBtn, delBtn);
    editor.appendChild(row);

    const beat = el("textarea", "r2-beat");
    beat.placeholder = "What happens in this hop: who, where, the action, what is heard. @tags cite refs.";
    editor.appendChild(beat);

    const warnBox = el("div", "r2-script-warns");
    warnBox.hidden = true;
    editor.appendChild(warnBox);

    const axes = el("div", "r2-axes");
    const selects = {};
    for (const axis of AXES) {
        const fld = el("label", "r2-fld");
        fld.appendChild(el("span", "r2-label", AXIS_LABEL[axis] || axis));
        const sel = el("select", "r2-select");
        sel.addEventListener("change", () => commit());
        selects[axis] = sel;
        fld.appendChild(sel);
        axes.appendChild(fld);
    }
    editor.appendChild(axes);

    const meta = el("div", "r2-meta");
    const seedEl = el("input", "r2-input");
    seedEl.type = "text";
    seedEl.inputMode = "numeric";
    seedEl.placeholder = "inherit";
    const stepsEl = el("input", "r2-input");
    stepsEl.type = "text";
    stepsEl.inputMode = "numeric";
    stepsEl.placeholder = "inherit";
    const durSel = el("select", "r2-select");
    const seedFld = el("label", "r2-fld");
    seedFld.append(el("span", "r2-label", "seed"), seedEl);
    const stepsFld = el("label", "r2-fld");
    stepsFld.append(el("span", "r2-label", "steps"), stepsEl);
    const durFld = el("label", "r2-fld");
    durFld.append(el("span", "r2-label", "duration"), durSel);
    const acts = el("div", "r2-actions");
    const renderBtn = el("button", "r2-primary", "\u25b5 render hop");
    renderBtn.type = "button";
    renderBtn.title = "Solo this hop on the next queue (sets render_from and render_through to this hop; click again to clear).";
    acts.appendChild(renderBtn);
    meta.append(seedFld, stepsFld, durFld, acts);
    editor.appendChild(meta);

    const footRow = el("div", "r2-shot-row");
    const cites = el("span", "r2-cites");
    const wordCount = el("span", "r2-cites");
    footRow.append(cites, el("span", "spacer"), wordCount);
    editor.appendChild(footRow);

    /* -- advanced per-shot fields (prose, anchor, refs, id, moments) ------ */
    const adv = el("details", "r2-adv");
    adv.appendChild(el("summary", null, "advanced (prose \u00b7 anchor \u00b7 @refs \u00b7 id \u00b7 hand-tie moments)"));
    const advGrid = el("div", "r2-adv-grid");

    const idIn = el("input", "r2-input");
    idIn.type = "text";
    idIn.placeholder = "s1";
    idIn.title = "Stable shot id (used as cache pointer for locked hops).";
    const idFld = el("label", "r2-fld");
    idFld.append(el("span", "r2-label", "shot id"), idIn);

    const anchorSel = el("select", "r2-select");
    for (const [val, txt] of [["", "relay (default)"], ["restart", "restart (fresh start)"], ["extend", "extend (hand-tie: own previs)"]]) {
        const o = el("option", null, txt);
        o.value = val;
        anchorSel.appendChild(o);
    }
    anchorSel.title = "restart: re-anchor on the start image instead of relaying the previous hop. extend: start a new hand-tie previs section.";
    const anchorFld = el("label", "r2-fld");
    anchorFld.append(el("span", "r2-label", "anchor"), anchorSel);

    const refsIn = el("input", "r2-input");
    refsIn.type = "text";
    refsIn.placeholder = "register default (or @tag / none)";
    refsIn.title = "Which stills ride this hop. Blank = register default; 'none' = no stills; '@tag1 @tag2' = explicit override.";
    const refsFld = el("label", "r2-fld");
    refsFld.append(el("span", "r2-label", "refs override"), refsIn);

    advGrid.append(idFld, anchorFld, refsFld);
    adv.appendChild(advGrid);

    const proseIn = el("textarea", "r2-beat r2-adv-box");
    proseIn.rows = 2;
    proseIn.placeholder = "prose appended verbatim (affirmative phrasing only)...";
    adv.appendChild(proseIn);

    const momentIn = el("textarea", "r2-beat r2-adv-box");
    momentIn.rows = 2;
    momentIn.placeholder = "moment (hand-tie): what is on screen as this hop starts, or a line crossing the join <d>[English] ...</d>";
    const momentEndIn = el("textarea", "r2-beat r2-adv-box");
    momentEndIn.rows = 2;
    momentEndIn.placeholder = "moment_end (hand-tie, last hop): a spoken line ending with the film <d>[English] ...</d>";
    adv.append(momentIn, momentEndIn);
    editor.appendChild(adv);

    root.appendChild(editor);

    /* -- simple mode ------------------------------------------------------ */
    const simple = el("div", "r2-simple");
    const simpleNote = el("div", "r2-note",
        "Simple mode: this prompt drives the whole run. Separate blocks with a line of --- to give each hop its own text. "
        + "Your Shots plan is safely stashed and returns when you click Shots.");
    const simpleBlocks = el("div", "r2-simple-blocks");
    const promptEl = el("textarea", "r2-beat r2-prompt");
    promptEl.placeholder = "Paste a standard H3 ref2va / t2va prompt, or plain prose.";
    simple.append(simpleNote, simpleBlocks, promptEl);
    root.appendChild(simple);

    /* -- unreadable plan -------------------------------------------------- */
    const badBox = el("div", "r2-bad");
    badBox.appendChild(el("div", "r2-note",
        "shot_plan is not valid JSON. Fix it here and the editor will take over again."));
    const rawEl = el("textarea", "r2-beat r2-raw");
    badBox.appendChild(rawEl);
    root.appendChild(badBox);

    /* -- JSON escape hatch (matches Refs tab JSON drawer) ----------------- */
    const jsonWrap = el("details", "h3e-json-wrap");
    const jsonSum = el("summary", null, "JSON");
    jsonSum.title = "The literal shot_plan value. Editing here updates the shots.";
    jsonWrap.appendChild(jsonSum);
    const jsonArea = el("textarea", "h3e-json");
    jsonArea.spellcheck = false;
    jsonArea.placeholder = '{"shots": [{"id": "s1", "beat": "...", "directives": {"camera": "hold"}}]}';
    jsonWrap.appendChild(jsonArea);
    const jsonErr = el("div", "h3e-note h3e-note-error");
    jsonErr.hidden = true;
    jsonWrap.appendChild(jsonErr);
    root.appendChild(jsonWrap);

    /* -- solo range helpers ----------------------------------------------- */
    function getRenderRange() {
        return {
            from: Number(widgetByName(node, "render_from")?.value) || 0,
            through: Number(widgetByName(node, "render_through")?.value) || 0,
        };
    }

    function isShotSoloed(shotNo) {
        const r = getRenderRange();
        return r.from === shotNo && r.through === shotNo;
    }

    function toggleSolo(shotNo) {
        const f = widgetByName(node, "render_from");
        const t = widgetByName(node, "render_through");
        if (!f || !t) return;
        const solo = isShotSoloed(shotNo);
        const nextVal = solo ? 0 : shotNo;
        f.value = nextVal;
        t.value = nextVal;
        try { f.callback?.(f.value, node.graph?.canvas, node); } catch (_) { /* */ }
        try { t.callback?.(t.value, node.graph?.canvas, node); } catch (_) { /* */ }
        node.graph?.setDirtyCanvas?.(true, true);
        render();
        onChange?.("solo");
    }

    /* -- vocab ------------------------------------------------------------ */
    function loadVocab() {
        return vocab().then((v) => {
            V = v;
            buildSelects();
            render();
        }).catch(() => { /* selects keep their current values */ });
    }

    function options(axis) {
        const set = new Set(Object.keys(V?.vocab?.[axis] || {}));
        const cur = shots[active]?.directives?.[axis] || "";
        if (cur) set.add(cur);
        return ["", ...set];
    }

    function buildSelects() {
        const titlesByAxis = V?.vocab || {};
        const defaults = V?.defaults || {};
        for (const axis of AXES) {
            const sel = selects[axis];
            const cur = shots[active]?.directives?.[axis] || "";
            sel.textContent = "";
            if (axis === "join" && active === 0) {
                const o = el("option", null, "start (hop 1)");
                o.value = "";
                sel.appendChild(o);
                sel.value = "";
                sel.disabled = true;
                continue;
            }
            sel.disabled = false;
            const def = defaults[axis];
            const blankLbl = def ? `${def.replace(/_/g, " ")} (default)` : "\u2014 inherit";
            for (const v of options(axis)) {
                const o = el("option", null, v || blankLbl);
                o.value = v;
                if (v && titlesByAxis[axis]?.[v]) o.title = titlesByAxis[axis][v];
                sel.appendChild(o);
            }
            if (cur && ![...(sel.options || sel.children)].some((o) => o.value === cur)) {
                const o = el("option", null, cur);
                o.value = cur;
                sel.appendChild(o);
            }
            sel.value = cur;
        }
        const durs = new Set(Object.keys(V?.durations || {}));
        const curDur = shots[active]?.duration || "";
        if (curDur) durs.add(curDur);
        durSel.textContent = "";
        const baseDur = String(widgetByName(node, "duration")?.value || "15 s");
        const inherit = el("option", null, `${baseDur} (default)`);
        inherit.value = "";
        durSel.appendChild(inherit);
        for (const d of durs) {
            const o = el("option", null, d);
            o.value = d;
            durSel.appendChild(o);
        }
        durSel.value = curDur;
    }

    function paintWordCount() {
        const s = shots[active];
        if (!s) {
            wordCount.textContent = "";
            return;
        }
        const label = durationOf(node, s);
        const band = (V?.beat_table || {})[label];
        const n = String(s.beat || "").trim().split(/\s+/).filter(Boolean).length;
        if (!band) {
            wordCount.textContent = n ? `${n} words` : "";
            wordCount.className = "r2-cites";
            return;
        }
        const [w0, w1] = band;
        const over = n > w1;
        wordCount.textContent = `${n} / ${w0}\u2013${w1} words`;
        wordCount.className = over ? "r2-cites r2-warn" : "r2-cites";
        wordCount.title = over
            ? `Exceeds the ${w0}-${w1} word band for a ${label} hop (dialogue/action may overrun).`
            : `Target word band for a ${label} hop: ${w0}-${w1} words.`;
    }

    function paintWarnings() {
        warnBox.textContent = "";
        const s = shots[active];
        if (!s) { warnBox.hidden = true; return; }
        const cw = coherenceWarning(s, active, shots);
        const dw = directionWarning(s);
        if (!cw && !dw) { warnBox.hidden = true; return; }
        warnBox.hidden = false;
        if (cw) warnBox.appendChild(el("div", "r2-note r2-warn", `\u26a0 ${cw}`));
        if (dw) warnBox.appendChild(el("div", "r2-note r2-danger", `\u26a0 ${dw}`));
    }

    function renderSimpleBlocks() {
        simpleBlocks.textContent = "";
        const text = String(promptEl.value || "");
        const raw = text.trim()
            ? text.split(/^\s*---\s*$/m).map((b) => b.trim()).filter(Boolean)
            : [];
        if (!raw.length) {
            simpleBlocks.hidden = true;
            return;
        }
        simpleBlocks.hidden = false;
        const baseDur = String(widgetByName(node, "duration")?.value || "15 s");
        const band = (V?.beat_table || {})[baseDur];
        const chainsN = Math.max(1, parseInt(widgetByName(node, "chains")?.value, 10) || 1);
        const parts = raw.map((b, idx) => {
            const words = b.split(/\s+/).filter(Boolean).length;
            const bandStr = band ? `/${band[0]}-${band[1]}w` : "w";
            return `${raw.length === 1 ? "1 block" : `block ${idx + 1}`}: ${words}${bandStr}`;
        });
        if (raw.length === 1 && chainsN > 1) {
            parts.push(`repeated across ${chainsN} hops`);
        }
        simpleBlocks.textContent = parts.join(" \u00b7 ");
    }

    function parseRefsField(raw) {
        const t = String(raw || "").trim();
        if (!t) return null;
        if (t.toLowerCase() === "none" || t === "-") return [];
        return t.split(/[\s,]+/).map((x) => x.replace(/^@/, "").trim()).filter(Boolean);
    }

    /* -- writes ----------------------------------------------------------- */
    function persistActive() {
        node.properties ??= {};
        node.properties[SHOT_PROP] = active;
        node.properties[MODE_PROP] = mode;
    }

    function applyFormToShot(s) {
        if (!s) return;
        s.beat = beat.value;
        s.seed = seedEl.value.trim() === "" ? null : Number(seedEl.value);
        s.steps = stepsEl.value.trim() === "" ? null : Number(stepsEl.value);
        s.duration = durSel.value || null;
        s.directives = Object.assign({}, s.directives || {});
        for (const axis of AXES) {
            if (axis === "join" && active === 0) continue;
            const v = selects[axis].value;
            if (v) s.directives[axis] = v;
            else delete s.directives[axis];
        }
        const nextId = idIn.value.trim();
        if (nextId) s.id = nextId;
        if (active > 0) s.anchor = anchorSel.value || "";
        s.refs = parseRefsField(refsIn.value);
        s.prose = proseIn.value;
        s.moment = momentIn.value;
        if (active === shots.length - 1) s.moment_end = momentEndIn.value;
    }

    function commit() {
        if (busy) return;
        persistActive();
        if (mode === "simple") {
            writePrompt(node, promptEl.value);
            renderSimpleBlocks();
            onChange?.();
            return;
        }
        const s = shots[active];
        if (!s) return;
        applyFormToShot(s);
        writePlan(node, shots);
        idEl.textContent = s.id || `s${active + 1}`;
        durChip.textContent = durationOf(node, s);
        paintWordCount();
        paintWarnings();
        updateChips();
        onChange?.();
    }

    // Write immediately to widget on input so Ctrl+Enter Queue never misses the last keystrokes
    beat.addEventListener("input", () => {
        if (busy) return;
        const s = shots[active];
        if (s) {
            s.beat = beat.value;
            writePlan(node, shots);
            paintWordCount();
        }
        clearTimeout(beatTimer);
        beatTimer = setTimeout(commit, 260);
    });
    beat.addEventListener("blur", () => { clearTimeout(beatTimer); commit(); });

    promptEl.addEventListener("input", () => {
        if (busy) return;
        writePrompt(node, promptEl.value);
        renderSimpleBlocks();
        clearTimeout(promptTimer);
        promptTimer = setTimeout(commit, 260);
    });
    promptEl.addEventListener("blur", () => { clearTimeout(promptTimer); commit(); });

    seedEl.addEventListener("change", commit);
    stepsEl.addEventListener("change", commit);
    durSel.addEventListener("change", commit);
    idIn.addEventListener("change", commit);
    anchorSel.addEventListener("change", commit);
    refsIn.addEventListener("change", commit);
    proseIn.addEventListener("input", () => {
        if (busy || !shots[active]) return;
        shots[active].prose = proseIn.value;
        writePlan(node, shots);
    });
    proseIn.addEventListener("change", commit);
    momentIn.addEventListener("input", () => {
        if (busy || !shots[active]) return;
        shots[active].moment = momentIn.value;
        writePlan(node, shots);
    });
    momentIn.addEventListener("change", commit);
    momentEndIn.addEventListener("input", () => {
        if (busy || !shots[active]) return;
        shots[active].moment_end = momentEndIn.value;
        writePlan(node, shots);
    });
    momentEndIn.addEventListener("change", commit);

    lockBtn.addEventListener("click", () => {
        flush();
        const s = shots[active];
        if (!s) return;
        s.locked = !s.locked;
        writePlan(node, shots);
        render();
        onChange?.();
    });
    dupBtn.addEventListener("click", () => {
        flush();
        const s = shots[active];
        if (!s) return;
        const copy = JSON.parse(JSON.stringify(s));
        copy.id = freeId(shots);
        copy.locked = false;
        shots.splice(active + 1, 0, copy);
        writePlan(node, shots);
        pick(active + 1);
        onChange?.();
    });
    delBtn.addEventListener("click", () => {
        flush();
        if (!shots.length) return;
        shots.splice(active, 1);
        active = Math.max(0, Math.min(active, shots.length - 1));
        writePlan(node, shots);
        if (!shots.length && readPrompt(node).trim()) {
            mode = "simple";
        }
        persistActive();
        render();
        onSelect?.(active);
        onChange?.();
    });
    addBtn.addEventListener("click", () => {
        flush();
        if (mode !== "shots") setMode("shots");
        const s = blankShot(shots.length);
        s.id = freeId(shots);
        if (shots.length) s.directives = { join: "continuous" };
        shots.push(s);
        writePlan(node, shots);
        active = shots.length - 1;
        persistActive();
        render();
        onSelect?.(active);
        onChange?.();
    });
    renderBtn.addEventListener("click", () => {
        flush();
        if (!shots.length) return;
        toggleSolo(active + 1);
    });

    shotBtn.addEventListener("click", () => setMode("shots"));
    simpleBtn.addEventListener("click", () => setMode("simple"));

    function setMode(next) {
        flush();
        node.properties ??= {};
        const target = next === "simple" ? "simple" : "shots";
        if (target === "simple") {
            const p = readPlan(node);
            if (!p.bad && p.shots.length) {
                node.properties[BACKUP_PROP] = planToJson(p.shots);
                writePlan(node, []);
            }
        } else {
            const p = readPlan(node);
            if (!p.bad && !p.shots.length) {
                const stashed = parsePlan(node.properties?.[BACKUP_PROP]);
                if (stashed && stashed.length) {
                    shots = stashed;
                    delete node.properties[BACKUP_PROP];
                    writePlan(node, shots);
                } else {
                    const text = readPrompt(node).trim();
                    const n = Math.max(1, parseInt(widgetByName(node, "chains")?.value, 10) || 1);
                    if (text) {
                        const blocks = text.split(/^\s*---\s*$/m).map((b) => b.trim()).filter(Boolean);
                        const use = blocks.length > 1 ? blocks.slice(0, n) : [text];
                        while (use.length < n) use.push("");
                        shots = use.map((b, i) => ({
                            ...blankShot(i),
                            id: `s${i + 1}`,
                            beat: b,
                            directives: i === 0 ? {} : { join: "continuous" },
                        }));
                    } else {
                        shots = [blankShot(0)];
                    }
                    writePlan(node, shots);
                }
            }
        }
        mode = target;
        persistActive();
        render();
        onChange?.();
    }

    /* -- selection -------------------------------------------------------- */
    function flush() {
        const had = Boolean(beatTimer || promptTimer);
        clearTimeout(beatTimer);
        clearTimeout(promptTimer);
        beatTimer = 0;
        promptTimer = 0;
        if (had) commit();
    }

    function pick(i) {
        flush();
        if (i < 0 || i >= shots.length) return;
        active = i;
        persistActive();
        render();
        onSelect?.(i);
    }

    function setActive(i) {
        flush();
        if (i < 0 || i >= shots.length) return;
        active = i;
        persistActive();
        render();
    }

    /* -- render ----------------------------------------------------------- */
    function updateChips() {
        chips.textContent = "";
        if (mode === "simple") return;
        const range = getRenderRange();
        shots.forEach((s, i) => {
            const shotNo = i + 1;
            const soloed = range.from === shotNo && range.through === shotNo;
            const b = el("button", "r2-hop" + (i === active ? " on" : "") + (s.locked ? " lk" : "") + (soloed ? " solo" : ""));
            b.type = "button";
            const deliv = deliveredSeconds(node, s, i);
            b.title = `${s.id || "s" + shotNo} \u00b7 ${deliv.toFixed(1)}s delivered${soloed ? " (soloed)" : ""}`;
            b.append(el("b", null, String(shotNo)), el("span", "d", durationOf(node, s)));
            if (soloed) b.appendChild(el("i", "solodot", "\u25b5"));
            if (s.locked) b.appendChild(el("i", "lockdot", "\u25a0"));
            b.addEventListener("click", () => pick(i));
            chips.appendChild(b);
        });
        const add = el("button", "r2-hop r2-hop-add", "+");
        add.type = "button";
        add.title = "Append a shot";
        add.addEventListener("click", () => addBtn.click());
        chips.appendChild(add);
    }

    function render() {
        busy = true;
        const p = readPlan(node);
        shots = p.shots;
        bad = p.bad;
        rawPlan = p.raw;

        // Always sync mode from node.properties so Standard Accept / -> Script Hop are reflected
        const propMode = node.properties?.[MODE_PROP];
        if (propMode === "simple" || propMode === "shots") {
            mode = propMode;
        } else {
            mode = shots.length ? "shots" : "simple";
        }
        if (active >= shots.length) active = Math.max(0, shots.length - 1);
        if (p.bad) mode = "simple";

        if (mode === "simple") {
            const ch = Math.max(1, parseInt(widgetByName(node, "chains")?.value, 10) || 1);
            count.textContent = ch === 1 ? "Standard (1 clip)" : `${ch} hops (Simple)`;
        } else {
            count.textContent = `${shots.length} shot${shots.length === 1 ? "" : "s"}`;
        }
        shotBtn.classList.toggle("on", mode === "shots");
        simpleBtn.classList.toggle("on", mode === "simple");
        editor.hidden = mode !== "shots" || bad;
        chips.hidden = mode !== "shots" || bad;
        simple.hidden = mode !== "simple" || bad;
        badBox.hidden = !bad;
        jsonWrap.hidden = bad;
        addBtn.hidden = mode !== "shots" || bad;
        modeBox.hidden = bad;

        if (bad) {
            rawEl.value = rawPlan;
            busy = false;
            return;
        }

        if (typeof document === "undefined" || document.activeElement !== jsonArea) {
            jsonArea.value = rawPlan;
            jsonErr.hidden = true;
        }

        if (mode === "simple") {
            if (document.activeElement !== promptEl) {
                promptEl.value = readPrompt(node);
            }
            renderSimpleBlocks();
            busy = false;
            return;
        }

        const s = shots[active];
        if (!s) {
            updateChips();
            beat.value = "";
            seedEl.value = "";
            stepsEl.value = "";
            durSel.value = "";
            cites.textContent = "no shots \u2014 click + shot to start";
            wordCount.textContent = "";
            warnBox.hidden = true;
            busy = false;
            return;
        }
        const shotNo = active + 1;
        noEl.textContent = String(shotNo);
        idEl.textContent = s.id || `s${shotNo}`;
        const deliv = deliveredSeconds(node, s, active);
        durChip.textContent = `${durationOf(node, s)} (${deliv.toFixed(1)}s net)`;
        lockBtn.classList.toggle("on", Boolean(s.locked));
        lockBtn.textContent = s.locked ? "locked" : "lock";
        seedNote.textContent = `seed ${s.seed == null ? "inherit" : s.seed}`;

        const soloed = isShotSoloed(shotNo);
        renderBtn.classList.toggle("on", soloed);
        renderBtn.textContent = soloed ? "\u25b5 soloed (clear)" : "\u25b5 render hop";

        if (document.activeElement !== beat) {
            beat.value = s.beat || "";
        }
        seedEl.value = s.seed == null ? "" : String(s.seed);
        stepsEl.value = s.steps == null ? "" : String(s.steps);

        idIn.value = s.id || `s${shotNo}`;
        anchorFld.hidden = active === 0;
        anchorSel.value = s.anchor || "";
        refsIn.value = s.refs == null
            ? ""
            : (s.refs.length ? s.refs.map((t) => "@" + t).join(" ") : "none");
        if (document.activeElement !== proseIn) proseIn.value = s.prose || "";
        if (document.activeElement !== momentIn) momentIn.value = s.moment || "";
        if (document.activeElement !== momentEndIn) momentEndIn.value = s.moment_end || "";
        const isHandTie = String(widgetByName(node, "pin_mech")?.value || "").startsWith("hand_tie");
        momentIn.hidden = !isHandTie && !s.moment;
        momentEndIn.hidden = (!isHandTie && !s.moment_end) || active !== shots.length - 1;

        buildSelects();
        paintWordCount();
        paintWarnings();
        const plan = readRefs(node);
        const tags = refsForShot(plan, active, s).map((r) => `@${r.tag}`);
        cites.textContent = tags.length ? `cites ${tags.join(" ")}` : "no refs on this hop";
        updateChips();
        busy = false;
    }

    /* external refresh after a writer / swap / standard writes widgets */
    function refresh() {
        const before = active;
        render();
        if (before >= shots.length) active = Math.max(0, shots.length - 1);
    }

    jsonArea.addEventListener("input", () => {
        const parsed = parsePlan(jsonArea.value);
        if (parsed === null) {
            jsonErr.textContent = "Not valid JSON \u2014 the shots view is keeping the last good version.";
            jsonErr.hidden = false;
            return;
        }
        jsonErr.hidden = true;
        shots = parsed;
        if (mode === "simple" && parsed.length) {
            node.properties ??= {};
            mode = "shots";
            node.properties[MODE_PROP] = "shots";
            delete node.properties[BACKUP_PROP];
        }
        writePlan(node, shots);
        render();
        onChange?.();
    });

    rawEl.addEventListener("input", () => {
        const w = node.widgets?.find((x) => x.name === "shot_plan");
        if (!w) return;
        w.value = rawEl.value;
        try { w.callback?.(w.value, node.graph?.canvas, node); } catch (_) { /* */ }
        node.graph?.setDirtyCanvas?.(true, true);
        if (parsePlan(rawEl.value) !== null) {
            render();
            onChange?.();
        }
    });

    loadVocab();
    onVocabRefresh(() => { loadVocab(); });
    render();

    return {
        root,
        render,
        refresh,
        reload: refresh,
        setActive,
        active: () => active,
        mode: () => mode,
        shots: () => shots,
        setMode,
        toggleSolo,
    };
}
