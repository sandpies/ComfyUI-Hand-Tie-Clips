/* SWAP -- standalone one-hop identity swap from a reference clip.
 *
 * Writes `swap_script` (the complete six-field H3 contract) and `swap_refs`
 * (the plate whitelist), plus `reference_video_desc` when captioned. It never
 * writes `shot_plan` and never writes `ref_plan`, so your multi-shot chain on
 * SCRIPT and your pictures on REFERENCES stay untouched.
 *
 * One or more identities may be added in left-to-right order:
 *   1st chip -> <Subject 1> (left performer)
 *   2nd chip -> <Subject 2> (middle / right performer)
 *   ...
 *
 * Trim the clip on MEDIA. SWAP reads the same widgets (slot 1).
 * LLM settings live on WRITE.
 */
import { el, button, widgetByName } from "./widget_utils.js";
import { parseRefPlan } from "./ref_rail.js";
import { createPicker } from "./media_picker.js";

const SWAP_PLAN_URL = "/h3_ref_chain/swap_plan";
const SWAP_IDS_PROP = "h3_swap_identities";
const SWAP_PINS_PROP = "h3_swap_pins";

function commit(node, w, value) {
    if (!w) return;
    w.value = value;
    try {
        w.callback?.(value, node.graph?.canvas, node, undefined, undefined);
    } catch (err) {
        console.error(`[HandTieClips] widget callback for ${w.name} failed:`, err);
    }
    node.graph?.setDirtyCanvas?.(true, true);
}

export function createVideoSwap(node, { onWritten } = {}) {
    const root = el("details", "h3e-section h3e-writer h3e-swap");
    const sum = el("summary", null);
    sum.appendChild(el("span", "h3e-title", "SWAP"));
    const badge = el("span", "h3e-count", "");
    sum.appendChild(badge);
    root.appendChild(sum);

    const body = el("div", "h3e-writer-body");
    root.appendChild(body);

    const hint = el("div", "h3e-note h3e-note-hint");
    hint.textContent = "Viggle Remake swap & edit: automatically loads viggle_remake_swap "
        + "or viggle_remake_edit LoRA @ 1.0 via LoraLoaderBypassModelOnly, places clip 1 "
        + "as <Video 1> with optional keyframe pins (held until sigma < 0.9), and runs "
        + "the 6-step euler schedule. Leaves SCRIPT and REFERENCES untouched.";
    body.appendChild(hint);

    const wVideo = widgetByName(node, "reference_video_file");
    const wStart = widgetByName(node, "reference_video_start_s");
    const wEnd = widgetByName(node, "reference_video_end_s");
    const wDesc = widgetByName(node, "reference_video_desc");
    const wSwapScript = widgetByName(node, "swap_script");
    const wSwapRefs = widgetByName(node, "swap_refs");

    /* D1h: a DIV, not a <label>. */
    const cell = el("div", "h3e-media-cell");
    cell.appendChild(el("span", "h3e-media-label", "clip 1"));
    const pick = createPicker({
        kind: "video",
        get: () => String(wVideo?.value || ""),
        set: (v) => {
            commit(node, wVideo, v);
            if (wStart) commit(node, wStart, 0);
        },
        title: "Reference clip. Same file as MEDIA slot 1.",
    });
    cell.appendChild(pick.root);
    body.appendChild(cell);

    // Ordered left-to-right identity list. 1 tag = single swap (<Subject 1>);
    // 2+ tags = multi-person swap (<Subject 1..N> assigned left to right).
    let selectedTags = [];
    const savedIds = node.properties?.[SWAP_IDS_PROP];
    if (Array.isArray(savedIds)) {
        selectedTags = savedIds
            .map((t) => String(t || "").replace(/^@/, "").trim())
            .filter(Boolean);
    }

    function saveSelectedTags() {
        node.properties ??= {};
        node.properties[SWAP_IDS_PROP] = selectedTags.slice();
    }

    const identRow = el("div", "h3e-writer-row");
    const identLabel = el("span", "h3e-chips-label", "PEOPLE (L\u2192R)");
    const chipWrap = el("div", "h3e-writer-row");
    const identSel = el("select", "h3e-select");
    identSel.title = "Add one or more identity pictures from the REFERENCES rail, "
        + "in left-to-right order in the clip.";
    identRow.appendChild(identLabel);
    identRow.appendChild(chipWrap);
    identRow.appendChild(identSel);
    body.appendChild(identRow);

    function railRows() {
        const plan = parseRefPlan(widgetByName(node, "ref_plan")?.value);
        if (!plan) return [];
        return (plan.refs || []).filter((r) => String(r.file || "").trim()
            && String(r.tag || "").trim());
    }

    function renderIdentityChips(rows) {
        const validSet = new Set(
            rows.map((r) => String(r.tag || "").replace(/^@/, "")),
        );
        selectedTags = selectedTags.filter((t) => validSet.has(t));
        chipWrap.textContent = "";
        selectedTags.forEach((tag, idx) => {
            const chip = button(
                `${idx + 1}: @${tag} \u00d7`,
                `Subject ${idx + 1} (performer ${idx + 1} from the left). Click to remove.`,
                () => {
                    selectedTags = selectedTags.filter((t) => t !== tag);
                    saveSelectedTags();
                    fillIdentity();
                },
                "h3e-btn h3e-draft-chip",
            );
            chipWrap.appendChild(chip);
        });
    }

    function fillIdentity() {
        const rows = railRows();
        renderIdentityChips(rows);
        identSel.textContent = "";
        const blank = el("option", null,
            selectedTags.length
                ? "\u2014 + add next person (L\u2192R) \u2014"
                : "\u2014 pick an identity \u2014");
        blank.value = "";
        identSel.appendChild(blank);
        for (const r of rows) {
            const tag = String(r.tag || "").replace(/^@/, "");
            if (selectedTags.includes(tag)) continue;
            const o = el("option", null, "@" + tag);
            o.value = tag;
            identSel.appendChild(o);
        }
        identSel.value = "";
        fillTagPicker(bgTagSel, "\u2014 @tag background plate \u2014");
        rebuildWardrobeDropdown();
        syncControls();
    }

    identSel.addEventListener("change", () => {
        const picked = String(identSel.value || "").replace(/^@/, "").trim();
        if (picked && !selectedTags.includes(picked)) {
            selectedTags.push(picked);
            saveSelectedTags();
        }
        identSel.value = "";
        fillIdentity();
    });

    const MODES = [
        ["replace_person", "Swap person / character (Viggle Swap)",
         "Viggle Remake swap LoRA: full character replacement (face, build, hairstyle and wardrobe from reference plates)."],
        ["head_swap", "Head swap (head + hair, Viggle Swap)",
         "Viggle Remake swap LoRA: face, hair and skin tone from reference plates; body and clothing stay with the clip."],
        ["face_only", "Face only (features, Viggle Swap)",
         "Viggle Remake swap LoRA: only facial features come from reference plates; hair, body and clothes stay with the clip."],
        ["keep_person", "Edit scene / Keep person (Viggle Edit)",
         "Viggle Remake edit LoRA: keeps the clip's people and edits objects, background, weather or lighting."],
    ];
    const BACKGROUNDS = [
        ["clip", "Background: from the clip", "Same place, props and light as the clip."],
        ["picture", "Background: from a picture (@tag)", "Pick a rail @tag below. The action still follows the clip."],
        ["free", "Background: free", "The beat chooses the setting from your brief."],
    ];

    function picker(options, title) {
        const sel = el("select", "h3e-select");
        sel.title = title;
        for (const [value, label, hintText] of options) {
            const o = el("option", null, label);
            o.value = value;
            o.title = hintText;
            sel.appendChild(o);
        }
        return sel;
    }

    const modeRow = el("div", "h3e-writer-row");
    const modeSel = picker(MODES, "Viggle Remake mode (Swap vs. Edit) and what the reference contributes.");
    const bgSel = picker(BACKGROUNDS, "Where the setting comes from.");
    const bgTagSel = el("select", "h3e-select");
    bgTagSel.title = "The @tag on the REFERENCES rail the background comes from (used when Background: from a picture is selected).";
    modeRow.append(modeSel, bgSel, bgTagSel);
    body.appendChild(modeRow);

    const plateRow = el("div", "h3e-writer-row");
    const wardSel = el("select", "h3e-select");
    wardSel.title = "Optional wardrobe from an @tag plate on the REFERENCES rail.";
    const wardInput = el("input", "h3e-writer-brief");
    wardInput.type = "text";
    wardInput.placeholder = "optional wardrobe / outfit text (e.g. black bikini, red dress, or @tag)";
    wardInput.title = "Optional custom wardrobe from text (or an @tag on the rail). "
        + "Overrides the clothing from the reference photo and the clip.";

    function rebuildWardrobeDropdown() {
        const prev = wardSel.value;
        wardSel.textContent = "";
        const defOpt = el("option", null, "\ud83d\udc57 Wardrobe: Keep Reference / Clip");
        defOpt.value = "";
        wardSel.appendChild(defOpt);
        const rows = railRows();
        if (rows.length) {
            const railGrp = document.createElement("optgroup");
            railGrp.label = "\ud83d\udccc From REFERENCES Rail (@tag Plate)";
            for (const r of rows) {
                const tag = String(r.tag || "").replace(/^@/, "");
                const o = el("option", null, `@${tag} (Rail Wardrobe Plate)`);
                o.value = `@${tag}`;
                railGrp.appendChild(o);
            }
            wardSel.appendChild(railGrp);
        }
        if (prev) wardSel.value = prev;
    }

    wardSel.addEventListener("change", () => {
        const val = wardSel.value;
        if (!val) {
            wardInput.value = "";
            return;
        }
        wardInput.value = val;
    });

    const pinsInput = el("input", "h3e-writer-brief");
    pinsInput.type = "text";
    pinsInput.style.maxWidth = "190px";
    pinsInput.placeholder = "pins: e.g. 0 or 12, 184 (optional)";
    pinsInput.title = "Optional 0-based frame indices (one per reference plate, in order) "
        + "when your reference plates are painted keyframes of the source clip. "
        + "Held in minimax_keyframes until sigma < 0.9. Leave blank for unpinned reference plates.";
    if (node.properties?.[SWAP_PINS_PROP]) {
        pinsInput.value = String(node.properties[SWAP_PINS_PROP]);
    }
    pinsInput.addEventListener("change", () => {
        node.properties ??= {};
        node.properties[SWAP_PINS_PROP] = String(pinsInput.value || "").trim();
    });
    plateRow.append(wardSel, wardInput, pinsInput);
    body.appendChild(plateRow);

    // Optional local add-on (not shipped): may add rows to SWAP and extra
    // request fields. Absent = nothing happens.
    let extras = null;
    import("./personal_studio.js").then((mod) => {
        if (typeof mod?.mountSwapExtras === "function") {
            extras = mod.mountSwapExtras(node, {
                body, bgSel, wardInput, syncControls: () => syncControls(),
            });
        }
    }).catch(() => {});

    function fillTagPicker(sel, blankLabel) {
        const rows = railRows();
        const prev = sel.value;
        sel.textContent = "";
        const blank = el("option", null, blankLabel);
        blank.value = "";
        sel.appendChild(blank);
        for (const r of rows) {
            const tag = String(r.tag || "").replace(/^@/, "");
            const o = el("option", null, "@" + tag);
            o.value = tag;
            sel.appendChild(o);
        }
        sel.value = rows.some((r) => String(r.tag).replace(/^@/, "") === prev)
            ? prev : "";
    }

    function syncControls() {
        const needsIdentity = modeSel.value !== "keep_person";
        identSel.disabled = !needsIdentity;
        identRow.style.opacity = needsIdentity ? "" : "0.45";
        identSel.title = needsIdentity
            ? "Add one or more identity pictures from the REFERENCES rail (L\u2192R)."
            : "Not used: this mode keeps the person who is already in the clip.";
        const usesBgTag = bgSel.value === "picture";
        bgTagSel.disabled = !usesBgTag;
        bgTagSel.style.opacity = usesBgTag ? "" : "0.45";
    }
    modeSel.addEventListener("change", syncControls);
    bgSel.addEventListener("change", syncControls);

    const row = el("div", "h3e-writer-row");
    const brief = el("input", "h3e-writer-brief");
    brief.type = "text";
    brief.placeholder = "optional -- extra context, action, or dialogue beyond the clip";
    row.appendChild(brief);

    const go = button("Analyze & write swap",
        "Draft one standalone swap contract (automatically samples 5 clip frames and scans reference plates).",
        () => run());
    row.appendChild(go);
    body.appendChild(row);

    const status = el("div", "h3e-note h3e-writer-status");
    status.style.display = "none";
    body.appendChild(status);

    const draft = el("div", "h3e-writer-draft");
    draft.style.display = "none";
    const draftList = el("div", "h3e-writer-draft-list");
    draft.appendChild(draftList);
    const draftBtns = el("div", "h3e-writer-row");
    const acceptBtn = button("Accept to SWAP",
        "Commit this six-field contract to swap_script and swap_refs. "
        + "SCRIPT (your chain) and REFERENCES stay untouched.",
        () => acceptDraft());
    const discardBtn = button("Discard",
        "Throw the draft away.",
        () => discardDraft());
    draftBtns.appendChild(acceptBtn);
    draftBtns.appendChild(discardBtn);
    draft.appendChild(draftBtns);
    body.appendChild(draft);

    // Live view of the active `swap_script` + `swap_refs` on the node, with a
    // one-click Clear button so returning from a swap to a multi-shot chain
    // takes one click and loses nothing.
    const activeBox = el("div", "h3e-writer-draft");
    activeBox.style.display = "none";
    const activeHead = el("div", "h3e-writer-row");
    const activeMeta = el("span", "h3e-draft-meta", "");
    const clearSwapBtn = button("Clear swap (use SCRIPT chain)",
        "Empty swap_script and swap_refs so the node renders your SCRIPT chain again.",
        () => clearActiveSwap());
    activeHead.appendChild(activeMeta);
    activeHead.appendChild(clearSwapBtn);
    activeBox.appendChild(activeHead);
    const activeText = el("textarea", "h3e-json");
    activeText.rows = 8;
    activeText.placeholder = "Active six-field swap contract (swap_script)";
    activeText.addEventListener("change", () => {
        if (wSwapScript) commit(node, wSwapScript, activeText.value);
        syncActiveBox();
        onWritten?.(null, {
            swap_script: activeText.value,
            swap_refs: String(wSwapRefs?.value || ""),
        });
    });
    activeBox.appendChild(activeText);
    body.appendChild(activeBox);

    let busy = false;
    let pending = null;

    function say(text, kind) {
        status.style.display = text ? "" : "none";
        status.className = "h3e-note h3e-writer-status"
            + (kind === "error" ? " h3e-note-error"
                : kind === "hint" ? " h3e-note-hint" : "");
        status.textContent = text || "";
    }

    function setBusy(on) {
        busy = on;
        go.disabled = acceptBtn.disabled = on;
    }

    function syncActiveBox() {
        const curScript = String(wSwapScript?.value || "").trim();
        const curRefs = String(wSwapRefs?.value || "").trim();
        badge.textContent = curScript ? "ON" : "";
        if (!curScript) {
            activeBox.style.display = "none";
            return;
        }
        activeBox.style.display = "";
        if (document.activeElement !== activeText) {
            activeText.value = curScript;
        }
        const platesLabel = curRefs === "[]"
            ? "(none -- keep_person)"
            : (curRefs ? curRefs.split(",").map((t) => "@" + t.trim()).join(" ")
                : "(register default)");
        activeMeta.textContent = `ACTIVE SWAP \u00b7 plates: ${platesLabel} \u00b7 overrides SCRIPT while set`;
    }

    function clearActiveSwap() {
        if (wSwapScript) commit(node, wSwapScript, "");
        if (wSwapRefs) commit(node, wSwapRefs, "");
        onWritten?.(null, { swap_script: "", swap_refs: "" });
        syncActiveBox();
        say("Cleared swap_script. The node will render SCRIPT again.", "hint");
    }

    function oneShot(shotJson) {
        let obj;
        try {
            obj = JSON.parse(shotJson);
        } catch (err) {
            return null;
        }
        const shots = obj?.shots || obj?.shot_plan?.shots;
        if (!Array.isArray(shots) || shots.length !== 1) return null;
        return JSON.stringify({ shots: [shots[0]] }, null, 2);
    }

    function deriveSwapWidgets(oneJson, explicitScript, explicitRefs) {
        let shot = {};
        try { shot = JSON.parse(oneJson).shots[0] || {}; } catch (err) { /* */ }
        const scriptText = String(explicitScript || shot.beat || "").trim();
        let refsText = "";
        if (explicitRefs !== undefined && explicitRefs !== null && String(explicitRefs) !== "") {
            refsText = String(explicitRefs).trim();
        } else if (Array.isArray(shot.refs)) {
            const cleaned = shot.refs
                .map((t) => String(t || "").replace(/^@/, "").trim())
                .filter(Boolean);
            refsText = cleaned.length ? cleaned.join(", ") : "[]";
        }
        return { shot, scriptText, refsText };
    }

    function showDraft(shotJson, videoDesc, explicitScript, explicitRefs) {
        const one = oneShot(shotJson);
        if (!one) {
            say("SWAP writes one hop. This draft had "
                + "a different number of shots and was not kept.", "error");
            return;
        }
        const { shot, scriptText, refsText } = deriveSwapWidgets(
            one, explicitScript, explicitRefs,
        );
        pending = {
            shot: one,
            swapScript: scriptText,
            swapRefs: refsText,
            videoDesc: videoDesc || "",
        };
        draftList.textContent = "";
        // Show the FULL six-field contract before Accept so the user can verify
        // every header and subject definition before committing it.
        draftList.appendChild(el("div", "h3e-draft-beat",
            scriptText || shot.beat || "(empty contract)"));
        const dirs = Object.entries(shot.directives || {})
            .map(([k, v]) => `${k}=${v}`);
        if (refsText === "[]") {
            dirs.push("plates (none)");
        } else if (refsText) {
            dirs.push("plates " + refsText.split(",").map((t) => "@" + t.trim()).join(" "));
        }
        if (dirs.length) {
            draftList.appendChild(el("div", "h3e-draft-meta", dirs.join(" \u00b7 ")));
        }
        if (pending.videoDesc) {
            draftList.appendChild(el("div", "h3e-draft-meta",
                "clip: " + pending.videoDesc));
        }
        draft.style.display = "";
    }

    function discardDraft() {
        pending = null;
        draft.style.display = "none";
        draftList.textContent = "";
    }

    function acceptDraft() {
        if (!pending) return;
        const { shot, swapScript, swapRefs, videoDesc } = pending;
        const one = oneShot(shot);
        if (!one || !swapScript) {
            say("Accept refused: SWAP writes exactly one valid six-field contract.", "error");
            return;
        }
        if (wSwapScript) commit(node, wSwapScript, swapScript);
        if (wSwapRefs) commit(node, wSwapRefs, swapRefs);
        discardDraft();
        onWritten?.(one, {
            swap_script: swapScript,
            swap_refs: swapRefs,
            reference_video_desc: videoDesc || "",
        });
        syncActiveBox();
        say("Accepted to SWAP (1 hop). SCRIPT and REFERENCES are untouched; "
            + "press Clear swap whenever you want to return to your chain.", "hint");
    }

    async function run() {
        if (busy) return;
        const video = String(wVideo?.value || "");
        if (!video) { say("Pick a reference clip first.", "error"); return; }
        const needsIdentity = modeSel.value !== "keep_person";
        const rows = railRows();
        const activeTags = needsIdentity
            ? (selectedTags.length
                ? selectedTags.slice()
                : (identSel.value ? [String(identSel.value).replace(/^@/, "")] : []))
            : [];
        const identities = activeTags
            .map((tag) => rows.find((r) => String(r.tag || "").replace(/^@/, "") === tag))
            .filter(Boolean)
            .map((r) => ({
                tag: String(r.tag).replace(/^@/, ""),
                file: String(r.file || "").trim(),
            }));
        if (needsIdentity && !identities.length) {
            say("Pick at least one identity picture from the rail first.", "error");
            return;
        }

        setBusy(true);
        say(identities.length > 1
            ? `Writing ${identities.length}-person swap contract (L\u2192R)\u2026`
            : "Writing one-hop swap contract\u2026", "hint");
        try {
            const rawWard = String(wardInput.value || "").trim();
            const isWardTag = rawWard.startsWith("@");
            const r = await fetch(SWAP_PLAN_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    brief: brief.value,
                    duration: String(widgetByName(node, "duration")?.value || ""),
                    video,
                    video_start_s: Number(wStart?.value) || 0,
                    video_end_s: Number(wEnd?.value) || 0,
                    identity: identities[0] || {},
                    identities,
                    rail_tags: rows.map(
                        (rowItem) => String(rowItem.tag || "").replace(/^@/, "")),
                    rail_rows: rows.map((rowItem) => ({
                        tag: String(rowItem.tag || "").replace(/^@/, ""),
                        file: String(rowItem.file || "").trim(),
                    })),
                    mode: modeSel.value,
                    background: bgSel.value,
                    background_tag: bgTagSel.value || "",
                    wardrobe_tag: isWardTag ? rawWard.replace(/^@/, "") : "",
                    wardrobe_text: isWardTag ? "" : rawWard,
                    ...(extras?.fields?.() || {}),
                    pins: String(pinsInput.value || "").trim(),
                }),
            });
            const j = await r.json();
            if (j.shot_plan) {
                showDraft(j.shot_plan, j.video_desc || "", j.swap_script, j.swap_refs);
            }
            if (!j.ok) {
                const errs = (j.errors || []).map((e) => `\u2022 ${e}`).join("\n");
                say(errs || j.error || "SWAP failed", "error");
                return;
            }
            const warn = (j.warnings || []).map((w) => `\u2022 ${w}`).join("\n");
            say("Drafted six-field swap contract in " + (j.attempts || "?")
                + " attempt(s). Review the full script below and press Accept to SWAP."
                + (warn ? "\n\n" + warn : ""),
                "hint");
        } catch (e) {
            say(String(e), "error");
        } finally {
            setBusy(false);
        }
    }

    function render() {
        fillIdentity();
        pick.render?.();
        syncActiveBox();
    }

    fillIdentity();
    syncActiveBox();
    return { root, render, destroy() { pick.destroy?.(); } };
}
