/* STANDARD -- one standard MiniMax H3 prompt for a single generation.
 *
 * Plan first, then write: the model proposes a storyboard for the one clip,
 * the user edits or approves it, and the second press writes the complete
 * block. Accept puts the block in Simple mode's `prompt` with chains = 1 and
 * stashes any shot plan exactly as the Simple toggle does, so a chain on SCRIPT
 * comes back with one click on Shots.
 *
 * The mode is not chosen here: pictures on REFS make it Ref2VA, none T2VA, and a
 * MEDIA start image is pinned as the first frame by the node. The server reads
 * the same ref_plan the node renders from, so the labels the block cites are
 * the pictures the model is handed.
 */
import { el, button, widgetByName } from "./widget_utils.js";
import { parseRefPlan, refmodVoice } from "./ref_rail.js";

const STANDARD_URL = "/h3_ref_chain/standard";
const MODE_PROP = "h3_editor_mode";
const BACKUP_PROP = "h3_plan_backup";
const DRAFT_PROP = "h3_standard_draft";

function commit(node, w, value) {
    if (!w) return;
    w.value = value;
    try {
        w.callback?.(value, node.graph?.canvas, node, undefined, undefined);
    } catch (err) {
        console.error(`[HandTieClips] widget callback for ${w.name} failed:`, err);
    }
}

export function createStandardWriter(node, { onWritten } = {}) {
    const root = el("details", "h3e-section h3e-writer h3e-standard");
    const sum = el("summary", null);
    sum.appendChild(el("span", "h3e-title", "STANDARD"));
    const badge = el("span", "h3e-count", "");
    sum.appendChild(badge);
    root.appendChild(sum);
    const body = el("div", "h3e-writer-body");
    root.appendChild(body);

    body.appendChild(el("div", "h3e-note h3e-note-hint",
        "One standard H3 prompt for a single generation (Simple mode, one hop). "
        + "Describe the clip, press Plan, edit the storyboard, then Write. "
        + "Pictures on REFS make it Ref2VA; a MEDIA start image becomes the first frame."));

    const modeLine = el("div", "h3e-draft-meta", "");
    body.appendChild(modeLine);

    const brief = el("textarea", "h3e-json");
    brief.rows = 4;
    brief.placeholder = "What happens in the clip: who, where, what they do, what is heard, the look.";
    body.appendChild(brief);

    const status = el("div", "h3e-note h3e-writer-status");
    status.style.display = "none";

    const planLabel = el("div", "h3e-draft-meta", "Storyboard (edit before Write):");
    const planBox = el("textarea", "h3e-json");
    planBox.rows = 10;
    const blockLabel = el("div", "h3e-draft-meta", "Prompt block:");
    const blockBox = el("textarea", "h3e-json");
    blockBox.rows = 14;

    const splitGrid = el("div", "h3e-standard-grid");
    const planCol = el("div", "h3e-standard-col");
    planCol.append(planLabel, planBox);
    const blockCol = el("div", "h3e-standard-col");
    blockCol.append(blockLabel, blockBox);
    splitGrid.append(planCol, blockCol);

    let busy = false;
    let draft = loadDraft();

    const planBtn = button("Plan", "Ask the model for a storyboard of this one clip", () => run("plan"));
    const writeBtn = button("Write", "Write the full prompt block from the storyboard", () => run("write"));
    const acceptBtn = button("Accept", "Put the block in Simple mode's prompt (chains = 1)", accept);
    const hopTargetSel = el("select", "h3e-select");
    hopTargetSel.style.maxWidth = "145px";
    hopTargetSel.title = "Target hop in multi-shot SCRIPT chain";
    const sendHopBtn = button("→ Script Hop", "Send this block's beat & duration into the selected hop on SCRIPT (switches to Shots mode)", sendToHop);
    const row = el("div", "h3e-writer-row");
    row.append(planBtn, writeBtn, acceptBtn, hopTargetSel, sendHopBtn);
    body.append(row, status, splitGrid);

    brief.value = draft.brief || "";
    planBox.value = draft.plan || "";
    blockBox.value = draft.block || "";
    for (const box of [brief, planBox, blockBox]) {
        box.addEventListener("input", saveDraft);
    }

    function loadDraft() {
        try { return JSON.parse(node.properties?.[DRAFT_PROP] || "{}") || {}; }
        catch { return {}; }
    }

    function saveDraft() {
        node.properties ??= {};
        node.properties[DRAFT_PROP] = JSON.stringify({
            brief: brief.value, plan: planBox.value, block: blockBox.value,
        });
        syncButtons();
    }

    function hop1Rows() {
        const plan = parseRefPlan(widgetByName(node, "ref_plan")?.value);
        if (!plan) return [];
        return (plan.refs || []).filter((r) => !Array.isArray(r.shots)
            || !r.shots.length || r.shots.includes(1));
    }

    function railPictures() {
        return hop1Rows().filter((r) => String(r.file || "").trim()
            && String(r.kind || "") !== "video").length;
    }

    function voiceFiles() {
        return ["voice_file", "voice_2_file", "voice_3_file"]
            .map((k) => String(widgetByName(node, k)?.value || "").trim())
            .filter(Boolean);
    }

    function railAudios() {
        const rowAudios = hop1Rows().filter((r) => {
            if (String(r.voice || "").trim()) return true;
            if (r.source === "refmod" && String(r.file || "").trim()) {
                return Boolean(refmodVoice(r.file)?.file);
            }
            return false;
        }).length;
        return voiceFiles().length + rowAudios;
    }

    function startImage() {
        return String(widgetByName(node, "start_image_file")?.value || "").trim();
    }

    function renderMode() {
        const n = railPictures();
        const a = railAudios();
        const parts = [];
        if (n) parts.push(`${n} picture${n > 1 ? "s" : ""}`);
        if (a) parts.push(`${a} audio${a > 1 ? "s" : ""}`);
        const mode = parts.length ? `Ref2VA, ${parts.join(", ")}` : "T2VA, no pictures";
        const dur = String(widgetByName(node, "duration")?.value || "");
        modeLine.textContent = `Mode: ${mode}${startImage() ? " + start image" : ""}`
            + (dur ? ` · ${dur}` : "");
        badge.textContent = parts.length ? "Ref2VA" : "T2VA";
    }

    let personal = null;

    function currentPlanShots() {
        const raw = String(widgetByName(node, "shot_plan")?.value || "").trim()
            || String(node.properties?.[BACKUP_PROP] || "").trim();
        if (!raw) return [];
        try {
            const parsed = JSON.parse(raw);
            const arr = Array.isArray(parsed) ? parsed : parsed?.shots;
            return Array.isArray(arr) ? arr : [];
        } catch {
            return [];
        }
    }

    function activePlanShots() {
        if (node.properties?.[MODE_PROP] !== "shots") return [];
        const raw = String(widgetByName(node, "shot_plan")?.value || "").trim();
        if (!raw) return [];
        try {
            const parsed = JSON.parse(raw);
            const arr = Array.isArray(parsed) ? parsed : parsed?.shots;
            return Array.isArray(arr) ? arr : [];
        } catch {
            return [];
        }
    }

    function refreshHopTargetSelect() {
        const shots = currentPlanShots();
        const prev = hopTargetSel.value;
        hopTargetSel.innerHTML = "";
        const appendOpt = el("option", null, `+ Append Hop (${shots.length + 1})`);
        appendOpt.value = "append";
        hopTargetSel.appendChild(appendOpt);
        for (let i = 0; i < shots.length; i++) {
            const s = shots[i] || {};
            const o = el("option", null, `Replace Hop ${i + 1} (${s.id || "s" + (i + 1)})`);
            o.value = String(i);
            hopTargetSel.appendChild(o);
        }
        if (prev && Array.from(hopTargetSel.options || hopTargetSel.children).some((o) => o.value === prev)) {
            hopTargetSel.value = prev;
        }
    }

    function syncButtons() {
        const hasBlock = Boolean(blockBox.value.trim());
        const hasPlan = Boolean(planBox.value.trim());
        const hasBriefOrDials = Boolean(brief.value.trim() || personal?.hasActiveDials?.());
        planBtn.disabled = busy || !hasBriefOrDials;
        writeBtn.disabled = busy || !hasPlan;
        acceptBtn.disabled = busy || !hasBlock;
        sendHopBtn.disabled = busy || (!hasBlock && !hasPlan);
        if (personal?.fastBtn) {
            personal.fastBtn.disabled = busy || !hasBriefOrDials;
        }
        personal?.syncBlockToolbar?.();
    }

    function setBusyState(on) {
        busy = Boolean(on);
        syncButtons();
    }

    function say(text, kind) {
        status.style.display = text ? "" : "none";
        status.className = "h3e-note h3e-writer-status"
            + (kind === "error" ? " h3e-note-error" : kind === "hint" ? " h3e-note-hint" : "");
        status.textContent = text || "";
    }

    import("./sandtie_ui.js").then((mod) => {
        if (typeof mod?.mountSandTieInStandard === "function") {
            personal = mod.mountSandTieInStandard(node, {
                body,
                row,
                brief,
                planBox,
                blockBox,
                say,
                saveDraft,
                startImage,
                voiceFiles,
                previousHopContext,
                setBusyState,
                isBusy: () => busy,
                onRefsChanged: () => renderMode(),
                onDialsChanged: () => syncButtons(),
            });
            syncButtons();
        }
    }).catch(() => {});

    function previousHopContext() {
        if (node.properties?.[MODE_PROP] !== "shots") return "";
        if (!personal?.shouldLinkPrevHop?.()) return "";
        const shots = activePlanShots();
        if (!shots.length) return "";
        const target = hopTargetSel.value;
        let prevIdx = -1;
        if (target === "append") prevIdx = shots.length - 1;
        else if (/^\d+$/.test(target)) prevIdx = Number(target) - 1;
        if (prevIdx < 0 || !shots[prevIdx]) return "";
        const prev = shots[prevIdx];
        const beatTxt = String(prev.beat || "").trim();
        if (!beatTxt) return "";
        const d = prev.directives || {};
        const dirBits = ["join", "camera", "framing", "pace", "tail"]
            .filter((k) => d[k])
            .map((k) => `${k}=${d[k]}`);
        return `Hop ${prevIdx + 1} (${prev.id || "s" + (prevIdx + 1)}`
            + `${dirBits.length ? ", " + dirBits.join(", ") : ""}): ${beatTxt}`;
    }

    async function run(stage) {
        if (busy) return;
        if (personal && personal.usePersonalEngine()) {
            return personal.runPersonal(stage, false);
        }
        busy = true;
        syncButtons();
        say(stage === "plan" ? "Planning the clip…" : "Writing the prompt block…", "hint");
        try {
            const r = await fetch(STANDARD_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    stage,
                    brief: brief.value,
                    plan: planBox.value,
                    duration: String(widgetByName(node, "duration")?.value || ""),
                    ref_plan: String(widgetByName(node, "ref_plan")?.value || ""),
                    start_image_file: startImage(),
                    voice_files: voiceFiles(),
                    prev_hop_context: previousHopContext(),
                }),
            });
            const j = await r.json();
            if (stage === "plan" && j.plan) planBox.value = j.plan;
            if (stage === "write" && j.block) blockBox.value = j.block;
            saveDraft();
            const warn = (j.warnings || []).map((w) => `• ${w}`).join("\n");
            // Notes read the finished block as a film (block_checks.py). Advisory:
            // the block is already accepted, and the model never sees them.
            const notes = (j.notes || []).map((w) => `• ${w}`).join("\n");
            if (!j.ok) {
                const errs = (j.errors || []).map((e) => `• ${e}`).join("\n");
                say((errs || j.error || "STANDARD failed")
                    + (stage === "write" && j.block
                        ? "\n\nThe last draft is below; fix it by hand or press Write again." : "")
                    + (warn ? "\n\n" + warn : ""), "error");
                return;
            }
            say((stage === "plan"
                ? `Storyboard ready (${j.mode}). Edit it, then press Write.`
                : `Block written in ${j.attempts || 1} attempt(s). The ${j.mode} contract passed`
                    + (notes ? `; ${(j.notes || []).length} note(s) on how it may play, below. Press Accept, or fix them by hand first.`
                             : `, and no notes on how it may play. Press Accept.`))
                + (notes ? "\n\n" + notes : "")
                + (warn ? "\n\n" + warn : ""), "hint");
        } catch (e) {
            say(String(e), "error");
        } finally {
            busy = false;
            syncButtons();
        }
    }

    function clearStaleSwap() {
        const swW = widgetByName(node, "swap_script");
        const srW = widgetByName(node, "swap_refs");
        const hadSwap = Boolean(swW && String(swW.value || "").trim());
        if (swW && String(swW.value || "")) commit(node, swW, "");
        if (srW && String(srW.value || "")) commit(node, srW, "");
        return hadSwap;
    }

    function accept() {
        const text = blockBox.value.trim();
        if (!text) return;
        node.properties ??= {};
        const planW = widgetByName(node, "shot_plan");
        // The same stash the Simple toggle makes: a chain on SCRIPT is kept,
        // and Shots brings it back. Simple mode needs shot_plan empty, or run()
        // would ignore the prompt and render the stale plan.
        if (planW && String(planW.value || "").trim()) {
            node.properties[BACKUP_PROP] = String(planW.value);
            commit(node, planW, "");
        }
        const clearedSwap = clearStaleSwap();
        commit(node, widgetByName(node, "prompt"), text);
        commit(node, widgetByName(node, "chains"), "1");
        node.properties[MODE_PROP] = "simple";
        onWritten?.(text, { mode: "simple" });
        say(
            "In Simple mode's prompt, chains = 1."
            + (clearedSwap ? " (Also cleared active Swap script.)" : "")
            + " Queue it.",
            "hint",
        );
    }

    function extractHopBeatFromBlock(rawText) {
        const t = String(rawText || "").trim();
        if (!t) return "";
        const mDesc = t.match(/(?:detailed_description|integrated_multimodal_description):[ \t]*\n([\s\S]*?)(?=\noverall_soundscape:|$)/i);
        if (!mDesc) return t;
        const bodyTxt = mDesc[1].trim();
        const mSound = t.match(/overall_soundscape:[ \t]*\n([\s\S]*?)(?=\nnon_diegetic_music:|$)/i);
        const soundTxt = mSound ? mSound[1].trim() : "";
        return soundTxt ? `${bodyTxt}\n\nSoundscape: ${soundTxt}` : bodyTxt;
    }

    function sendToHop() {
        const sourceText = blockBox.value.trim() || planBox.value.trim();
        if (!sourceText) return;
        node.properties ??= {};
        const planW = widgetByName(node, "shot_plan");
        const shots = currentPlanShots().slice();
        const beatText = extractHopBeatFromBlock(sourceText);
        const durVal = String(widgetByName(node, "duration")?.value || "").trim() || null;
        const target = hopTargetSel.value;
        let hopNum = shots.length + 1;
        if (target !== "append" && /^\d+$/.test(target)) {
            const idx = Number(target);
            if (shots[idx]) {
                shots[idx] = Object.assign({}, shots[idx], {
                    beat: beatText,
                    ...(durVal ? { duration: durVal } : {}),
                });
                hopNum = idx + 1;
            }
        } else {
            const newId = `s${shots.length + 1}`;
            shots.push({
                id: newId,
                beat: beatText,
                directives: shots.length === 0 ? {} : { join: "hard_cut" },
                ...(durVal ? { duration: durVal } : {}),
            });
            hopNum = shots.length;
        }
        const nextJson = JSON.stringify({ shots }, null, 2);
        delete node.properties[BACKUP_PROP];
        node.properties[MODE_PROP] = "shots";
        const clearedSwap = clearStaleSwap();
        commit(node, planW, nextJson);
        refreshHopTargetSelect();
        onWritten?.(nextJson, { mode: "shots", hopIndex: hopNum - 1 });
        say(
            `Sent to SCRIPT Hop ${hopNum} (${shots.length} total hop${shots.length > 1 ? "s" : ""}) in Shots mode.`
            + (clearedSwap ? " (Also cleared active Swap script.)" : ""),
            "hint",
        );
    }

    function render() {
        renderMode();
        refreshHopTargetSelect();
        syncButtons();
        personal?.refresh?.();
        if (root.open) {
            personal?.refreshStatus?.(false);
        }
    }

    root.addEventListener("toggle", () => {
        if (root.open) {
            personal?.refreshStatus?.(false);
        }
    });

    render();
    return { root, render };
}
