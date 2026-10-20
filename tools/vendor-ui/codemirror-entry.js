import { basicSetup, EditorView } from "codemirror";
import { EditorState } from "@codemirror/state";
import { StreamLanguage } from "@codemirror/language";
import { openSearchPanel } from "@codemirror/search";
import { json } from "@codemirror/lang-json";
import { yaml } from "@codemirror/lang-yaml";
import { oneDark } from "@codemirror/theme-one-dark";

const dotenv = StreamLanguage.define({
  startState() {
    return { afterEquals: false };
  },
  token(stream, state) {
    if (stream.sol()) state.afterEquals = false;
    if (stream.eatSpace()) return null;

    if (!state.afterEquals && stream.peek() === "#") {
      stream.skipToEnd();
      return "comment";
    }

    if (!state.afterEquals && stream.match(/[A-Za-z_][A-Za-z0-9_]*/)) {
      return "variableName.definition";
    }

    if (!state.afterEquals && stream.eat("=")) {
      state.afterEquals = true;
      return "operator";
    }

    if (state.afterEquals) {
      const quote = stream.peek();
      if (quote === '"' || quote === "'") {
        stream.next();
        let escaped = false;
        while (!stream.eol()) {
          const ch = stream.next();
          if (escaped) {
            escaped = false;
          } else if (ch === "\\" && quote === '"') {
            escaped = true;
          } else if (ch === quote) {
            break;
          }
        }
        return "string";
      }
      stream.skipToEnd();
      return "string";
    }

    stream.next();
    return "invalid";
  },
  languageData: {
    commentTokens: { line: "#" },
  },
});

function languageExtension(language) {
  if (language === "json") return json();
  if (language === "yaml" || language === "yml") return yaml();
  if (language === "env" || language === "dotenv") return dotenv;
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
      ".cm-search": { backgroundColor: "#0f172a", color: "#e2e8f0", borderTop: "1px solid #334155" },
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

export function openSearch(view) {
  if (!view) return false;
  return openSearchPanel(view);
}

export function focus(view) {
  view?.focus?.();
}

export function destroy(view) {
  view?.destroy?.();
}
