/**
 * Shared ComfyUI subgraph runner for Studio Image Forge, YuE2 Song Forge, and Swap Keyframe Painter.
 */

import { api } from "../../../scripts/api.js";

export const IMAGE_MP_STOPS = [
    ["0", "MP: Auto"],
    ["0.5", "0.5 MP (Fast)"],
    ["1", "1 MP"],
    ["1.5", "1.5 MP"],
    ["2", "2 MP"],
    ["3", "3 MP"],
    ["4", "4 MP"],
    ["6", "6 MP"],
    ["8", "8 MP"],
    ["12", "12 MP"],
];

const _ASPECT_BASE = {
    qwen: { "16:9": [1344, 768], "9:16": [768, 1344], "1:1": [1024, 1024], "4:3": [1152, 896], "3:4": [896, 1152] },
    moss: { "16:9": [1344, 768], "9:16": [768, 1344], "1:1": [1024, 1024], "4:3": [1184, 896], "3:4": [896, 1184] },
    h3_4mp: { "16:9": [2720, 1536], "9:16": [1536, 2720], "1:1": [2048, 2048], "4:3": [2368, 1760], "3:4": [1760, 2368] },
};

export function previewImageDims(profile, aspect, megapixels) {
    const family = String(profile?.family || "qwen");
    const step = family === "moss" ? 16 : 32;
    const explicitMp = Number(megapixels || 0) || 0;
    const defaultMp = Number(profile?.default_mp || 0) || 0;
    const useMp = explicitMp > 0 ? explicitMp : defaultMp;
    const asp = String(aspect || "16:9").split(" ")[0].trim().toLowerCase();
    if (!asp || asp === "match") {
        if (useMp > 0) {
            return { width: 0, height: 0, mp: useMp, label: `Match Ref · ${useMp} MP` };
        }
        const autoMp = family === "h3_4mp" ? 4.0 : 1.0;
        return {
            width: 0,
            height: 0,
            mp: autoMp,
            label: family === "h3_4mp" ? "Match Ref (~4 MP)" : "Match Ref (Native)",
        };
    }
    const table = _ASPECT_BASE[family] || _ASPECT_BASE.qwen;
    const pair = table[asp] || table["16:9"];
    let w = pair[0];
    let h = pair[1];
    if (useMp > 0 && w > 0 && h > 0) {
        const scale = Math.sqrt((useMp * 1_000_000.0) / (w * h));
        w = Math.max(step, Math.round((w * scale) / step) * step);
        h = Math.max(step, Math.round((h * scale) / step) * step);
    }
    const actualMp = (w * h) / 1_000_000.0;
    return { width: w, height: h, mp: actualMp, label: `${w}×${h} (${actualMp.toFixed(1)} MP)` };
}

export function viewUrl(rec) {
    if (!rec || !rec.filename) return "";
    const p = new URLSearchParams({
        filename: String(rec.filename),
        type: String(rec.type || "output"),
    });
    if (rec.subfolder) p.set("subfolder", String(rec.subfolder));
    return `/view?${p.toString()}`;
}

export async function unloadWriterForGpu({ auto = false } = {}) {
    try {
        await fetch("/h3_ref_chain/llm/unload", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ auto: Boolean(auto) }),
        });
    } catch (_) {
        /* ignore if LLM server is already stopped */
    }
}

function formatPromptErrors(j) {
    if (!j || typeof j !== "object") return "ComfyUI rejected the graph.";
    const parts = [];
    if (j.error?.message) parts.push(String(j.error.message));
    const nodeErrs = j.node_errors;
    if (nodeErrs && typeof nodeErrs === "object") {
        for (const [nid, info] of Object.entries(nodeErrs)) {
            const errs = Array.isArray(info?.errors) ? info.errors : [];
            for (const err of errs) {
                parts.push(`Node ${nid} (${info.class_type || "?"}): ${err.message || err.details || "invalid"}`);
            }
        }
    }
    return parts.join("; ") || JSON.stringify(j).slice(0, 220);
}

/**
 * Unload writer VRAM, compile a graph via `/h3_ref_chain/mv/build_graph`, queue it on ComfyUI,
 * stream live progress, and resolve with the output media metadata from `/history/{prompt_id}`.
 */
export async function runForgeGraph(buildBody, { onStatus, onProgress } = {}) {
    onStatus?.("Freeing writer VRAM & compiling graph...");
    await unloadWriterForGpu({ auto: true });

    const buildRes = await fetch("/h3_ref_chain/mv/build_graph", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildBody || {}),
    });
    const buildJson = await buildRes.json();
    if (!buildRes.ok || !buildJson?.ok || !buildJson?.prompt) {
        throw new Error(buildJson?.error || `Failed to build graph (HTTP ${buildRes.status})`);
    }

    onStatus?.("Queueing on ComfyUI...");
    const payload = { prompt: buildJson.prompt };
    if (api.clientId) payload.client_id = api.clientId;

    const qRes = await api.fetchApi("/prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const qJson = await qRes.json();
    if (!qRes.ok || qJson?.error || (qJson?.node_errors && Object.keys(qJson.node_errors).length)) {
        throw new Error(formatPromptErrors(qJson));
    }
    const promptId = String(qJson?.prompt_id || "");
    if (!promptId) throw new Error("ComfyUI did not return a prompt_id.");

    let wsErr = null;
    let done = false;
    const onProg = (e) => {
        const d = e?.detail || {};
        if (d.prompt_id && d.prompt_id !== promptId) return;
        const val = Number(d.value || 0);
        const max = Math.max(1, Number(d.max || 1));
        onProgress?.(val, max);
    };
    const onErr = (e) => {
        const d = e?.detail || {};
        if (d.prompt_id && d.prompt_id !== promptId) return;
        wsErr = new Error(d.exception_message || "ComfyUI execution failed.");
    };
    const onExecuted = (e) => {
        const d = e?.detail || {};
        if (d.prompt_id === promptId && String(d.node) === String(buildJson.output_node)) {
            done = true;
        }
    };

    api.addEventListener("progress", onProg);
    api.addEventListener("execution_error", onErr);
    api.addEventListener("executed", onExecuted);

    try {
        const deadline = Date.now() + 20 * 60 * 1000;
        while (Date.now() < deadline) {
            if (wsErr) throw wsErr;
            try {
                const hRes = await api.fetchApi(`/history/${encodeURIComponent(promptId)}`);
                if (hRes.ok) {
                    const hist = await hRes.json();
                    const entry = hist?.[promptId];
                    if (entry) {
                        const statusStr = String(entry.status?.status_str || "");
                        if (statusStr === "error") {
                            throw new Error("ComfyUI reported execution error.");
                        }
                        const nodeOut = entry.outputs?.[String(buildJson.output_node)];
                        if (nodeOut && (nodeOut.images?.length || nodeOut.audio?.length)) {
                            const items = nodeOut.images || nodeOut.audio || [];
                            return {
                                ok: true,
                                prompt_id: promptId,
                                output_kind: buildJson.output_kind,
                                file: items[0],
                                files: items,
                                meta: buildJson,
                            };
                        }
                        if (buildJson.output_kind === "refmod" && (entry.status?.completed || done)) {
                            return {
                                ok: true,
                                prompt_id: promptId,
                                output_kind: "refmod",
                                refmod_name: buildJson.refmod_name || "",
                                file: null,
                                files: [],
                                meta: buildJson,
                            };
                        }
                        if (entry.status?.completed && done) {
                            throw new Error("Graph completed with no media output.");
                        }
                    }
                }
            } catch (pollErr) {
                if (pollErr === wsErr || String(pollErr?.message || "").includes("ComfyUI")) {
                    throw pollErr;
                }
            }
            await new Promise((r) => setTimeout(r, 600));
        }
        throw new Error("Timed out waiting for ComfyUI output.");
    } finally {
        api.removeEventListener("progress", onProg);
        api.removeEventListener("execution_error", onErr);
        api.removeEventListener("executed", onExecuted);
    }
}
