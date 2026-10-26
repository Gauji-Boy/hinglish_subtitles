/*
 * Minimal DOM stub + app.js loader for caption-sync tests.
 *
 * app.js is a classic browser script: it reads localStorage at load, grabs a few
 * dozen elements by id, and wires listeners. This harness provides just enough of
 * a DOM for it to load, then exposes the caption state so a test can drive the
 * playhead and assert what the overlay actually shows.
 *
 * No dependencies. Run with: node tests/js/caption_sync_test.js
 */

const fs = require("fs");
const path = require("path");
const vm = require("vm");

class TextNode {
  constructor(text) {
    this.nodeType = 3;
    this._text = String(text);
  }
  get textContent() { return this._text; }
  set textContent(v) { this._text = String(v); }
}

class Fragment {
  constructor() {
    this.nodeType = 11;
    this.childNodes = [];
  }
  appendChild(child) { this.childNodes.push(child); return child; }
  get textContent() {
    return this.childNodes.map((c) => c.textContent).join("");
  }
}

class El {
  constructor(id = "") {
    this.id = id;
    this.nodeType = 1;
    // Browsers expose custom properties through setProperty/getPropertyValue;
    // plain assignments stay readable as style.fontSize etc.
    const custom = new Map();
    const methods = {
      setProperty: (name, value) => custom.set(String(name), String(value)),
      getPropertyValue: (name) => (custom.has(String(name)) ? custom.get(String(name)) : ""),
      removeProperty: (name) => {
        const key = String(name);
        const previous = custom.has(key) ? custom.get(key) : "";
        custom.delete(key);
        return previous;
      },
    };
    this.style = new Proxy(custom, {
      get(target, prop) {
        if (typeof prop === "string" && Object.prototype.hasOwnProperty.call(methods, prop)) {
          return methods[prop];
        }
        return target.has(prop) ? target.get(prop) : "";
      },
      set(target, prop, value) {
        target.set(prop, String(value));
        return true;
      },
      has(target, prop) {
        return (typeof prop === "string" && prop in methods) || target.has(prop);
      },
    });
    this.dataset = {};
    this.childNodes = [];
    this.parentElement = null;
    this.offsetParent = null;
    this.offsetLeft = 0;
    this.offsetTop = 0;
    this.offsetWidth = 0;
    this.offsetHeight = 0;
    this.clientTop = 0;
    this.clientLeft = 0;
    this.clientWidth = 860;
    this.clientHeight = 480;
    this.value = "";
    this.checked = false;
    this.disabled = false;
    this.innerHTML = "";
    this._text = "";
    this._listeners = {};
    const classes = new Set();
    this.classList = {
      add: (...names) => names.forEach((n) => classes.add(n)),
      remove: (...names) => names.forEach((n) => classes.delete(n)),
      toggle: (name, force) => {
        const on = force === undefined ? !classes.has(name) : Boolean(force);
        if (on) classes.add(name); else classes.delete(name);
        return on;
      },
      contains: (name) => classes.has(name),
      _set: classes,
    };
    // app.js assigns className directly, so keep it in step with classList the
    // way a real element does (querySelector(".foo") matches className tokens).
    Object.defineProperty(this, "className", {
      get: () => [...classes].join(" "),
      set: (value) => {
        classes.clear();
        String(value || "")
          .split(/\s+/)
          .filter(Boolean)
          .forEach((name) => classes.add(name));
      },
    });
    this.className = "";
  }

  get textContent() {
    if (this.childNodes.length) {
      return this.childNodes.map((c) => c.textContent).join("");
    }
    return this._text;
  }
  set textContent(v) {
    this._text = String(v);
    this.childNodes = [];
  }

  appendChild(child) {
    // A real DOM expands a DocumentFragment into the parent's children.
    if (child && child.nodeType === 11 && Array.isArray(child.childNodes)) {
      child.childNodes.forEach((node) => {
        if (node && typeof node === "object") node.parentElement = this;
        this.childNodes.push(node);
      });
      child.childNodes = [];
      return child;
    }
    if (child && typeof child === "object") child.parentElement = this;
    this.childNodes.push(child);
    return child;
  }
  removeChild(child) {
    const i = this.childNodes.indexOf(child);
    if (i >= 0) this.childNodes.splice(i, 1);
    return child;
  }
  insertBefore(child) { this.childNodes.unshift(child); return child; }
  descendants() {
    const found = [];
    const walk = (node) => {
      (node.childNodes || []).forEach((child) => {
        if (child && child.nodeType === 1) {
          found.push(child);
          walk(child);
        }
      });
    };
    walk(this);
    return found;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  querySelectorAll(selector) {
    const match = /^\.([\w-]+)$/.exec(String(selector || "").trim());
    if (!match) return [];
    return this.descendants().filter((el) => el.classList.contains(match[1]));
  }
  getContext() {
    // Just enough of a 2D context for canvas text metrics. Glyph widths are a
    // fixed average so the numbers are deterministic.
    const ctx = {
      font: "",
      measureText: (text) => {
        const size = Number((/ (\d+(?:\.\d+)?)px/.exec(ctx.font) || [])[1]) || 16;
        const advance = 0.6 * size * String(text).length;
        return { width: advance, actualBoundingBoxLeft: 0, actualBoundingBoxRight: advance };
      },
    };
    return ctx;
  }
  remove() {}
  setAttribute() {}
  removeAttribute() {}
  getAttribute() { return null; }
  hasAttribute() { return false; }
  addEventListener(type, fn) {
    (this._listeners[type] = this._listeners[type] || []).push(fn);
  }
  removeEventListener() {}
  // requestVideoFrameCallback is only real on <video>; the stub exposes it on
  // every element so tests can drive the caption clock one frame at a time.
  // Pending callbacks are kept in a queue so a test can prove the loop only
  // ever has one frame in flight.
  requestVideoFrameCallback(fn) {
    this._frameCallbacks = this._frameCallbacks || [];
    this._frameCallbackId = (this._frameCallbackId || 0) + 1;
    this._frameCallbacks.push({ id: this._frameCallbackId, fn });
    return this._frameCallbackId;
  }
  cancelVideoFrameCallback(id) {
    this._frameCallbacks = (this._frameCallbacks || []).filter((cb) => cb.id !== id);
  }
  pendingFrames() {
    return (this._frameCallbacks || []).length;
  }
  emitFrame() {
    const queue = this._frameCallbacks || [];
    if (!queue.length) return false;
    const next = queue.shift();
    next.fn(0, {});
    return true;
  }
  dispatch(type, event = {}) {
    (this._listeners[type] || []).forEach((fn) => fn({ target: this, ...event }));
  }
  closest() { return null; }
  contains() { return false; }
  scrollIntoView() {}
  focus() {}
  blur() {}
  click() {}
  play() { return Promise.resolve(); }
  pause() {}
  load() {}
  getBoundingClientRect() {
    return { width: 860, height: 480, top: 0, left: 0, right: 860, bottom: 480, x: 0, y: 0 };
  }
}

function makeDocument() {
  const byId = new Map();
  const doc = {
    nodeType: 9,
    body: new El("body"),
    documentElement: new El("html"),
    head: new El("head"),
    getElementById(id) {
      if (!byId.has(id)) byId.set(id, new El(id));
      return byId.get(id);
    },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement(tag) { return new El(tag); },
    createElementNS(_ns, tag) { return new El(tag); },
    createDocumentFragment() { return new Fragment(); },
    createTextNode(text) { return new TextNode(text); },
    addEventListener() {},
    removeEventListener() {},
  };
  return doc;
}

function loadApp() {
  const document = makeDocument();
  const storage = new Map();
  const localStorage = {
    getItem: (k) => (storage.has(k) ? storage.get(k) : null),
    setItem: (k, v) => storage.set(k, String(v)),
    removeItem: (k) => storage.delete(k),
    clear: () => storage.clear(),
  };

  const sandbox = {
    document,
    localStorage,
    navigator: { userAgent: "node", clipboard: { writeText: () => Promise.resolve() } },
    console,
    setTimeout: () => 0,
    clearTimeout: () => {},
    setInterval: () => 0,
    clearInterval: () => {},
    requestAnimationFrame: () => 0,
    cancelAnimationFrame: () => {},
    fetch: () => new Promise(() => {}),
    EventSource: class { constructor() {} addEventListener() {} close() {} },
    URL: { createObjectURL: () => "blob:stub", revokeObjectURL: () => {} },
    Blob: class {},
    FormData: class { append() {} },
    FileReader: class { readAsText() {} },
    Image: class {},
    Audio: class { play() {} pause() {} },
    performance: { now: () => Date.now() },
    getComputedStyle: () => ({ getPropertyValue: () => "" }),
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    IntersectionObserver: class { observe() {} unobserve() {} disconnect() {} },
    ResizeObserver: class { observe() {} unobserve() {} disconnect() {} },
    MutationObserver: class { observe() {} disconnect() {} },
    alert: () => {},
    confirm: () => false,
    prompt: () => null,
    location: { href: "http://127.0.0.1:8501/", origin: "http://127.0.0.1:8501", reload() {} },
    screen: { width: 1920, height: 1080 },
    devicePixelRatio: 1,
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => true,
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  sandbox.self = sandbox;
  sandbox.window.__INITIAL_CONFIG__ = {};

  const source = fs.readFileSync(
    path.join(__dirname, "..", "..", "static", "app.js"),
    "utf8"
  );

  // The test hooks are appended to the same script body so they share app.js's
  // top-level lexical scope (currentSegments, captionText, etc. are let/const).
  const hooks = `
;globalThis.__captionTest = {
  document,
  setSegments(segments) { currentSegments = segments; },
  setBaseSegments(segments) {
    captionBaseSegments = segments.map((s) => ({ ...s, words: (s.words || []).map((w) => ({ ...w })) }));
  },
  setCaptionOffset(ms) { setCaptionOffset(ms); },
  getCaptionOffsetMs() { return captionOffsetMs; },
  getSegments() { return currentSegments; },
  setActiveIndex(index) { activeSegmentIndex = index; },
  setStyle(style) { activeCaptionStyle = style; },
  setMode(mode) { captionMode = mode; },
  getCaptionText() { return captionText; },
  getOverlay() { return captionOverlay; },
  getPlayer() { return videoPlayer; },
  updateVideoCaption,
  applyCaptionStyleToVideo,
  applyCaptionWordColors,
  flattenKineticWords,
  posterLineCounts() {
    const style = activeCaptionStyle || {};
    const words = flattenKineticWords();
    const byPhrase = new Map();
    words.forEach((word) => {
      if (!byPhrase.has(word.phrase)) byPhrase.set(word.phrase, []);
      byPhrase.get(word.phrase).push(word);
    });
    const baseSize = kineticBaseSize(style);
    const rect = videoPlayer ? videoPlayer.getBoundingClientRect() : { width: 860 };
    const lineWidth = Math.max(
      80,
      ((rect.width || 860) * kineticMaxWidthPercent(null, style)) / 100
    );
    const punchScale = Number(style.accent_scale || 150) / 100;
    const accentScale = Number(style.accent_size_scale || 100) / 100;
    const scaleOf = (word) => (word.punch ? punchScale : (word.accent ? accentScale : 1));
    return [...byPhrase.values()].map(
      (group) => kineticLineWordCounts(group, baseSize, lineWidth, style, scaleOf).length
    );
  },
  captureCaptionBase,
  startCaptionLoop,
  stopCaptionLoop,
  isCaptionLoopRunning() { return captionLoopOn; },
  stylePositionRange,
  stylePositionValue,
  stylePositionPatch,
  styleIsKinetic,
  safeZoneCollisions,
  safeZoneFrameBox,
  captionBlockBox,
  applyClassicBottom,
  applyKineticTop,
  refreshSafeZoneWarning,
  setSafeZoneOn(on) { safeZoneOn = Boolean(on); },
  isSafeZoneOn() { return safeZoneOn; },
  syncSafeZoneMask,
  SAFE_ZONE_TOP,
  SAFE_ZONE_BOTTOM,
  SAFE_ZONE_RIGHT,
};
`;
  const context = vm.createContext(sandbox);
  vm.runInContext(source + hooks, context, { filename: "app.js" });
  return sandbox.__captionTest;
}

module.exports = { loadApp, El, TextNode };
