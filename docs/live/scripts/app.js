// Demo stand-in for ComfyUI's app.js: records what the node registers.
const rec = (window.__appStub ||= { extensions: [] });
export const app = {
  registerExtension(ext) { rec.extensions.push(ext); return ext; },
  graph: {
    _nodes: [], links: {},
    setDirtyCanvas() {}, getNodeById(id) { return this._nodes.find((n) => n.id == id) || null; },
    getNodesByType() { return []; }, serialize() { return { nodes: [] }; }, add(n) { this._nodes.push(n); },
  },
  canvas: { setDirty() {}, draw() {}, ds: { scale: 1, offset: [0, 0] }, canvas: document.createElement("canvas") },
  extensionManager: {
    registerSidebarTab() {}, setting: { get() { return undefined; }, set() {} },
    toast: { add(t) { window.__demoToast?.(t?.detail || t?.summary || ""); } },
  },
  ui: { settings: { getSettingValue() { return undefined; }, setSettingValue() {} } },
  async queuePrompt() { window.__demoToast?.("Queue needs ComfyUI running: this page is a demo of the editor."); },
  async graphToPrompt() { return { output: {}, workflow: {} }; },
};
export default app;
