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
    연한 점선 영역의 문구를 직접 수정할 수 있습니다. 글자색과 서식은 선택 즉시 저장되며, 문구 내용 수정은 '수정 내용 적용'을 누르세요.
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
  position: fixed;
  right: 18px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
  width: 118px;
  margin: 0;
  padding: 9px;
  border: 1px solid #d8dde3;
  border-radius: 10px;
  background: rgba(255,255,255,0.98);
  box-shadow: 0 4px 18px rgba(0,0,0,0.14);
}
.ngc-editor-title {
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 2px 0;
  text-align: center;
  white-space: nowrap;
}
.ngc-editor-toolbar button {
  width: 100%;
  min-height: 30px;
  padding: 4px 8px;
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
  width: 100%;
  height: 1px;
  background: #d8dde3;
  margin: 1px 0;
}
.ngc-spacer { display: none; }
.ngc-status {
  color: #6b7280;
  font-size: 10px;
  line-height: 1.35;
  text-align: center;
  white-space: normal;
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
@media (max-width: 1150px) {
  .ngc-editor-toolbar {
    position: sticky;
    top: 8px;
    right: auto;
    transform: none;
    flex-direction: row;
    align-items: center;
    width: calc(100% - 24px);
    max-width: 980px;
    margin: 0 auto 8px auto;
  }
  .ngc-editor-toolbar button {
    width: auto;
  }
  .ngc-editor-title {
    margin: 0 4px 0 0;
  }
  .ngc-divider {
    width: 1px;
    height: 22px;
    margin: 0 2px;
  }
  .ngc-spacer {
    display: block;
    flex: 1;
  }
  .ngc-status {
    max-width: 210px;
  }
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

  const getEditorSelection = () => {
    if (
      parentElement
      && typeof parentElement.getSelection === "function"
    ) {
      const shadowSelection = parentElement.getSelection();
      if (shadowSelection) return shadowSelection;
    }

    const ownerDocument = parentElement.ownerDocument || document;
    if (
      ownerDocument
      && typeof ownerDocument.getSelection === "function"
    ) {
      const documentSelection = ownerDocument.getSelection();
      if (documentSelection) return documentSelection;
    }

    return window.getSelection();
  };

  const collectContent = () => {
    const content = {};
    editables.forEach((editable) => {
      const key = editable.getAttribute("data-edit-key");
      if (key) content[key] = editable.innerHTML;
    });
    return content;
  };

  const commitContent = (message) => {
    setStateValue("content", collectContent());
    dirty = false;
    applyButton.classList.remove("ngc-dirty");
    if (status) {
      status.textContent = message || "수정 내용이 적용되었습니다.";
    }
  };

  const rememberSelection = () => {
    const selection = getEditorSelection();
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
    const selection = getEditorSelection();
    if (!selection) return false;
    selection.removeAllRanges();
    selection.addRange(savedRange);
    return true;
  };

  const selectedTextSlices = (range, editable) => {
    const slices = [];
    const walker = document.createTreeWalker(
      editable,
      NodeFilter.SHOW_TEXT
    );

    let node = walker.nextNode();
    while (node) {
      if (range.intersectsNode(node)) {
        const start = (
          node === range.startContainer
            ? range.startOffset
            : 0
        );
        const end = (
          node === range.endContainer
            ? range.endOffset
            : node.textContent.length
        );

        if (end > start) {
          slices.push({ node, start, end });
        }
      }
      node = walker.nextNode();
    }
    return slices;
  };

  const applyInlineStyle = (styleName, styleValue) => {
    if (!restoreSelection()) return;

    const selection = getEditorSelection();
    if (!selection || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    const editable = editableForRange(range);
    if (!editable || range.collapsed) {
      if (status) status.textContent = "먼저 바꿀 글자를 드래그해서 선택하세요.";
      return;
    }

    const slices = selectedTextSlices(range, editable);
    if (!slices.length) return;

    const wrappers = [];

    for (let i = slices.length - 1; i >= 0; i -= 1) {
      const { node, start, end } = slices[i];

      if (!node.parentNode) continue;

      if (end < node.textContent.length) {
        node.splitText(end);
      }
      const selectedNode = (
        start > 0
          ? node.splitText(start)
          : node
      );

      const span = document.createElement("span");
      span.style[styleName] = styleValue;
      selectedNode.parentNode.insertBefore(span, selectedNode);
      span.appendChild(selectedNode);
      wrappers.unshift(span);
    }

    if (wrappers.length) {
      const caretRange = document.createRange();
      caretRange.setStartAfter(
        wrappers[wrappers.length - 1]
      );
      caretRange.collapse(true);
      selection.removeAllRanges();
      selection.addRange(caretRange);
      savedRange = null;
    }

    markDirty();
    commitContent("서식이 바로 적용되었습니다.");
  };

  const runCommand = (command) => {
    if (command === "bold") {
      applyInlineStyle("fontWeight", "700");
      return;
    }
    if (command === "italic") {
      applyInlineStyle("fontStyle", "italic");
      return;
    }
    if (command === "underline") {
      applyInlineStyle("textDecoration", "underline");
      return;
    }

    if (!restoreSelection()) return;
    document.execCommand(command, false, null);
    rememberSelection();
    markDirty();
    commitContent("서식이 바로 적용되었습니다.");
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
    button.onclick = () => applyInlineStyle(
      "color",
      button.getAttribute("data-color")
    );
  });

  applyButton.onmousedown = (event) => event.preventDefault();
  applyButton.onclick = () => {
    commitContent("수정 내용이 적용되었습니다.");
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
