const TARGET = new EventTarget();

export function on(type, listener, options) {
  TARGET.addEventListener(type, listener, options);
  return () => TARGET.removeEventListener(type, listener, options);
}

export function emit(type, detail = {}) {
  TARGET.dispatchEvent(new CustomEvent(type, { detail }));
  document.dispatchEvent(new CustomEvent(`devconsole:${type}`, { detail }));
}

export const events = Object.freeze({ on, emit });
