const DEMO_PROMPTS = {
  research: `Please draft a structured competitor & tech research briefing (R&D demo task).
Topic: AI assistant capabilities in sports analytics & team management platforms (e.g. Hudl, MaxPreps, GameChanger).
Requirements:
1) Use research_kb to inspect benchmark competitors and template;
2) web_search and fetch_url on 1 key article;
3) Synthesize 5-8 key findings and a summary comparison matrix;
4) Save to workspace/research_brief_sports_ai.md with citations;
5) Conclude with terminate.`,
  docs: `Please perform an internal task memo digestion demo.
1) Use research_kb template=docs to align structure;
2) Read workspace/internal_memo_rd_tasks.txt;
3) Digest and group action items by priority into workspace/task_digest_rd.md;
4) Conclude with terminate.`,
};

async function fillDemoPrompt(promptId) {
  if (DEMO_PROMPTS[promptId]) {
    document.getElementById("messageInput").value = DEMO_PROMPTS[promptId];
    document.getElementById("messageInput").focus();
    return;
  }
  try {
    const res = await fetch("/api/demo-tasks");
    const data = await res.json();
    const hit = (data.tasks || []).find((t) => t.id === promptId);
    if (hit) {
      document.getElementById("messageInput").value = hit.prompt;
      document.getElementById("messageInput").focus();
    }
  } catch (e) {
    console.error(e);
  }
}

window.fillDemoPrompt = fillDemoPrompt;

async function refreshModelStatus() {
  const el = document.getElementById("modelStatus");
  if (!el) return;
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.ok) {
      el.textContent = `${data.provider} · ${data.model}`;
      el.classList.add("is-ok");
      el.classList.remove("is-bad");
    } else {
      el.textContent = data.message || "Model Not Connected";
      el.classList.add("is-bad");
      el.classList.remove("is-ok");
    }
  } catch (e) {
    el.textContent = "Service Offline";
    el.classList.add("is-bad");
    el.classList.remove("is-ok");
  }
}

async function refreshCapabilities() {
  const list = document.getElementById("capabilityList");
  if (!list) return;
  try {
    const res = await fetch("/api/capabilities");
    const data = await res.json();
    const features = data.features || [];
    if (!features.length) {
      list.innerHTML = '<li class="is-muted">No capability info</li>';
      return;
    }
    list.innerHTML = features
      .map((f) => {
        const cls = f.on ? "is-on" : "is-off";
        const mark = f.on ? "" : " (Disabled)";
        return `<li class="${cls}">${f.label}${mark}</li>`;
      })
      .join("");
  } catch (e) {
    list.innerHTML = '<li class="is-muted">Failed to load capabilities</li>';
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-prompt-id]").forEach((el) => {
    el.addEventListener("click", () => {
      fillDemoPrompt(el.getAttribute("data-prompt-id"));
    });
  });
  refreshModelStatus();
  refreshCapabilities();
});
