from __future__ import annotations

from typing import Any

import streamlit as st


_EDITOR_HTML = """
<div class="ngc-editor-shell">
  <div class="ngc-editor-toolbar">
    <span class="ngc-editor-title">결과지 직접 편집</span>
    <button type="button" data-cmd="bold" title="굵게"><strong>B</strong></button>
    <button type="button" data-cmd="italic" title="기울임"><em>I</em></button>
    <button type="button" data-cmd="underline" title="밑줄"><u>U</u></button>
    <span class="ngc-divider"></span>
    <button type="button" data-color="#D7191C" class="ngc-color ngc-red" title="빨간색">빨강</button>
    <button type="button" data-color="#2679D9" class="ngc-color ngc-blue" title="파란색">파랑</button>
    <button type="button" data-color="#111111" class="ngc-color ngc-black" title="검정색">검정</button>
    <button type="button" data-cmd="removeFormat" title="서식 지우기">서식 지우기</button>
    <span class="ngc-spacer"></span>
    <span class="ngc-status" aria-live="polite">수정 가능 영역을 클릭해 편집하세요.</span>
    <button type="button" id="ngc-apply" class="ngc-apply">수정 내용 적용</button>
  </div>
  <div class="ngc-editor-help">
    연한 점선 영역의 문구를 직접 수정할 수 있습니다. 수정이 끝나면 상단의 '수정 내용 적용'을 누르세요.
  </div>
  <div id="ngc-report-root"></div>
</div>
"""

_EDITOR_CSS = """
.ngc-editor-shell {
  width: 100%;
  background: #f4f6f8;
  padding: 12px 0 20px 0;
  font-family: "Noto Sans CJK KR", "Noto Sans KR", "Malgun Gothic", sans-serif;
}
.ngc-editor-toolbar {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 6px;
  width: min(100%, 980px);
  margin: 0 auto 8px auto;
  padding: 8px 10px;
  border: 1px solid #d8dde3;
  border-radius: 8px;
  background: rgba(255,255,255,0.98);
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.ngc-editor-title {
  font-size: 13px;
  font-weight: 700;
  margin-right: 4px;
  white-space: nowrap;
}
.ngc-editor-toolbar button {
  min-height: 30px;
  padding: 4px 9px;
  border: 1px solid #cfd5dc;
  border-radius: 5px;
  background: #fff;
  color: #111;
  font-size: 12px;
  cursor: pointer;
}
.ngc-editor-toolbar button:hover {
  background: #f0f4f8;
}
.ngc-editor-toolbar .ngc-red { color: #D7191C; }
.ngc-editor-toolbar .ngc-blue { color: #2679D9; }
.ngc-editor-toolbar .ngc-black { color: #111111; }
.ngc-divider {
  width: 1px;
  height: 22px;
  background: #d8dde3;
  margin: 0 2px;
}
.ngc-spacer { flex: 1; }
.ngc-status {
  color: #6b7280;
  font-size: 11px;
  white-space: nowrap;
}
.ngc-apply {
  border-color: #1f5f9f !important;
  background: #1f5f9f !important;
  color: #fff !important;
  font-weight: 700;
  white-space: nowrap;
}
.ngc-apply.ngc-dirty {
  background: #0f4f8f !important;
  box-shadow: 0 0 0 2px rgba(31,95,159,0.15);
}
.ngc-editor-help {
  width: min(100%, 980px);
  margin: 0 auto 10px auto;
  color: #5f6873;
  font-size: 12px;
}
#ngc-report-root {
  overflow-x: auto;
  padding: 0 12px 12px 12px;
}
#ngc-report-root .ngc-report-host {
  width: max-content;
  margin: 0 auto;
  font-family: "Noto Sans CJK KR", "Noto Sans KR", "Malgun Gothic", sans-serif;
}
#ngc-report-root .page {
  margin: 0 auto 18px auto;
  box-shadow: 0 2px 14px rgba(0,0,0,0.13);
}
#ngc-report-root [data-edit-key][contenteditable="true"] {
  outline: 1.5px dashed #8fb9df;
  outline-offset: 2px;
  cursor: text;
  background: rgba(234,246,255,0.24);
  transition: outline-color 120ms ease, background 120ms ease;
}
#ngc-report-root [data-edit-key][contenteditable="true"]:hover {
  outline-color: #4d91ca;
  background: rgba(234,246,255,0.42);
}
#ngc-report-root [data-edit-key][contenteditable="true"]:focus {
  outline: 2px solid #2f7db8;
  background: rgba(234,246,255,0.34);
}
"""

_EDITOR_JS = """
export default function(component) {
  const {
    data,
    parentElement,
    setStateValue,
  } = component;

  const root = parentElement.querySelector("#ngc-report-root");
  const toolbar = parentElement.querySelector(".ngc-editor-toolbar");
  const status = parentElement.querySelector(".ngc-status");
  const applyButton = parentElement.querySelector("#ngc-apply");

  if (!root || !toolbar || !applyButton) return;

  const parsed = new DOMParser().parseFromString(
    (data && data.html) || "",
    "text/html"
  );

  root.innerHTML = "";

  parsed.querySelectorAll("style").forEach((sourceStyle) => {
    const style = document.createElement("style");
    style.textContent = sourceStyle.textContent || "";
    root.appendChild(style);
  });

  const host = document.createElement("div");
  host.className = "ngc-report-host";
  host.innerHTML = parsed.body ? parsed.body.innerHTML : "";
  root.appendChild(host);

  const editables = Array.from(
    host.querySelectorAll("[data-edit-key]")
  );

  let savedRange = null;
  let dirty = false;

  const markDirty = () => {
    dirty = true;
    applyButton.classList.add("ngc-dirty");
    if (status) status.textContent = "수정 내용이 아직 적용되지 않았습니다.";
  };

  const editableForRange = (range) => {
    if (!range) return null;
    let node = range.commonAncestorContainer;
    if (node && node.nodeType === Node.TEXT_NODE) {
      node = node.parentElement;
    }
    if (!node || !node.closest) return null;
    const editable = node.closest("[data-edit-key]");
    return editable && host.contains(editable) ? editable : null;
  };

  const rememberSelection = () => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;
    const range = selection.getRangeAt(0);
    if (!editableForRange(range)) return;
    savedRange = range.cloneRange();
  };

  const restoreSelection = () => {
    if (!savedRange) return false;
    const editable = editableForRange(savedRange);
    if (!editable) return false;
    editable.focus();
    const selection = window.getSelection();
    if (!selection) return false;
    selection.removeAllRanges();
    selection.addRange(savedRange);
    return true;
  };

  const runCommand = (command, value = null) => {
    if (!restoreSelection()) return;
    try {
      document.execCommand("styleWithCSS", false, true);
    } catch (e) {
      // Browser may not expose styleWithCSS. The main command still works.
    }
    document.execCommand(command, false, value);
    rememberSelection();
    markDirty();
  };

  editables.forEach((editable) => {
    editable.setAttribute("contenteditable", "true");
    editable.setAttribute("spellcheck", "true");
    editable.oninput = markDirty;
    editable.onmouseup = rememberSelection;
    editable.onkeyup = rememberSelection;
    editable.onfocus = rememberSelection;
    editable.onkeydown = (event) => {
      if (
        (event.ctrlKey || event.metaKey)
        && event.key.toLowerCase() === "s"
      ) {
        event.preventDefault();
        applyButton.click();
      }
    };
  });

  toolbar.querySelectorAll("[data-cmd]").forEach((button) => {
    button.onmousedown = (event) => event.preventDefault();
    button.onclick = () => runCommand(
      button.getAttribute("data-cmd")
    );
  });

  toolbar.querySelectorAll("[data-color]").forEach((button) => {
    button.onmousedown = (event) => event.preventDefault();
    button.onclick = () => runCommand(
      "foreColor",
      button.getAttribute("data-color")
    );
  });

  applyButton.onmousedown = (event) => event.preventDefault();
  applyButton.onclick = () => {
    const content = {};
    editables.forEach((editable) => {
      const key = editable.getAttribute("data-edit-key");
      if (key) content[key] = editable.innerHTML;
    });

    setStateValue("content", content);
    dirty = false;
    applyButton.classList.remove("ngc-dirty");
    if (status) status.textContent = "수정 내용이 적용되었습니다.";
  };

  return () => {
    toolbar.querySelectorAll("button").forEach((button) => {
      button.onclick = null;
      button.onmousedown = null;
    });
    editables.forEach((editable) => {
      editable.oninput = null;
      editable.onmouseup = null;
      editable.onkeyup = null;
      editable.onfocus = null;
      editable.onkeydown = null;
    });
  };
}
"""


_REPORT_EDITOR = st.components.v2.component(
    "ngc_cpet_report_editor",
    html=_EDITOR_HTML,
    css=_EDITOR_CSS,
    js=_EDITOR_JS,
)


def render_report_editor(
    html_text: str,
    initial_content: dict[str, str],
    *,
    key: str,
) -> Any:
    return _REPORT_EDITOR(
        key=key,
        data={"html": html_text},
        default={"content": initial_content},
        on_content_change=lambda: None,
        width="stretch",
        height="content",
    )
