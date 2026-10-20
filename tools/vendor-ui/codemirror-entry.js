import { basicSetup, EditorView } from "codemirror";
import { EditorState } from "@codemirror/state";
import { json } from "@codemirror/lang-json";
import { yaml } from "@codemirror/lang-yaml";
import { oneDark } from "@codemirror/theme-one-dark";

function languageExtension(language) {
  if (language === "json") return json();
  if (language === "yaml" || language === "yml") return yaml();
  return [];
}

export function createEditor({ parent, doc = "", language = "text", onChange = null } = {}) {
  if (!parent) throw new Error("CodeMirror parent is required");
  const extensions = [
    basicSetup,
    oneDark,
    languageExtension(language),
    EditorView.lineWrapping,
    EditorView.theme({
      "&": { height: "100%", backgroundColor: "#020617" },
      ".cm-scroller": { overflow: "auto", fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" },
      ".cm-content": { minHeight: "340px", fontSize: "12.5px", lineHeight: "1.6" },
      ".cm-gutters": { backgroundColor: "#020617", borderRight: "1px solid #1e293b" },
    }),
  ];
  if (typeof onChange === "function") {
    extensions.push(EditorView.updateListener.of((update) => {
      if (update.docChanged) onChange(update.state.doc.toString());
    }));
  }
  const state = EditorState.create({ doc: String(doc ?? ""), extensions });
  return new EditorView({ state, parent });
}

export function setValue(view, value) {
  if (!view?.state) return;
  const next = String(value ?? "");
  if (view.state.doc.toString() === next) return;
  view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: next } });
}

export function getValue(view) {
  return view?.state?.doc?.toString?.() ?? "";
}

export function focus(view) {
  view?.focus?.();
}

export function destroy(view) {
  view?.destroy?.();
}
