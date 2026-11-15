// Demo stand-in for ComfyUI's api.js. Every request goes to the service worker.
const listeners = {};
export const api = {
  clientId: "demo",
  apiURL(p) { return p; }, fileURL(p) { return p; },
  addEventListener(n, f) { (listeners[n] ||= []).push(f); },
  removeEventListener(n, f) { listeners[n] = (listeners[n] || []).filter((x) => x !== f); },
  dispatchEvent() {},
  async fetchApi(route, opts = {}) { return fetch(route.startsWith("/") ? route : "/" + route, opts); },
};
export default api;
