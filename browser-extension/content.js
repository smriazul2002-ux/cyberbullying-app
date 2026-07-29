const API_URL = "http://127.0.0.1:8000/predict";
const MIN_TEXT_LENGTH = 8;
const MAX_TEXT_LENGTH = 400;
const processed = new WeakSet();

function isCandidateElement(el) {
  if (!el || processed.has(el)) return false;
  if (["SCRIPT", "STYLE", "NOSCRIPT", "svg", "path", "IFRAME"].includes(el.tagName)) return false;
  const text = el.innerText?.trim();
  if (!text) return false;
  if (text.length < MIN_TEXT_LENGTH || text.length > MAX_TEXT_LENGTH) return false;
  const hasBlockChildren = Array.from(el.children).some(
    (child) => window.getComputedStyle(child).display === "block"
  );
  if (hasBlockChildren) return false;
  return true;
}

async function checkText(text) {
  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    console.warn("Cyberbullying Detector: could not reach local API. Is api.py running?", e);
    return null;
  }
}

function flagElement(el, result) {
  el.classList.add("cbd-flagged");
  el.title = `⚠️ Flagged as cyberbullying (${Math.round(result.confidence * 100)}% confidence)`;
  const badge = document.createElement("span");
  badge.className = "cbd-badge";
  badge.innerText = `⚠️ ${Math.round(result.confidence * 100)}%`;
  el.prepend(badge);
}

async function scanNode(root) {
  const candidates = root.querySelectorAll("span, div, p");
  for (const el of candidates) {
    if (!isCandidateElement(el)) continue;
    processed.add(el);
    const text = el.innerText.trim();
    const result = await checkText(text);
    if (result && result.prediction === "Cyberbullying") {
      flagElement(el, result);
    }
  }
}

scanNode(document.body);

const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    for (const node of mutation.addedNodes) {
      if (node.nodeType === 1) {
        scanNode(node);
      }
    }
  }
});

observer.observe(document.body, { childList: true, subtree: true });
