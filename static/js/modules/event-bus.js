export class EventBus {
  constructor() { this.target = new EventTarget(); }
  on(name, handler, options) {
    this.target.addEventListener(name, handler, options);
    return () => this.target.removeEventListener(name, handler, options);
  }
  emit(name, detail = {}) {
    this.target.dispatchEvent(new CustomEvent(name, { detail }));
  }
}
