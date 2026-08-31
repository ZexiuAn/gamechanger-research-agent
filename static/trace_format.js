/**
 * 将原始 Agent 日志收成可读摘要卡片，避免搜索结果/长 URL 刷屏。
 */

function truncateText(text, maxLen) {
  const s = String(text || "").replace(/\s+/g, " ").trim();
  if (s.length <= maxLen) return s;
  return s.slice(0, maxLen - 1) + "…";
}

function shortUrl(url) {
  try {
    const u = new URL(url);
    const path = u.pathname.length > 24 ? u.pathname.slice(0, 24) + "…" : u.pathname;
    return u.hostname + (path === "/" ? "" : path);
  } catch (e) {
    return truncateText(url, 48);
  }
}

function cleanNoise(text) {
  return String(text || "")
    .replace(/播报/g, "")
    .replace(/暂停/g, "")
    .replace(/\u0007/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function parseSearchResults(raw) {
  const text = cleanNoise(raw);
  const hits = [];
  const blocks = text.split(/\n(?=\d+\.\s)/);
  for (const block of blocks) {
    const titleMatch = block.match(/^\d+\.\s+(.+)/m);
    if (!titleMatch) continue;
    const title = titleMatch[1].trim();
    const urlMatch = block.match(/URL:\s*(\S+)/);
    const descMatch = block.match(/Description:\s*([^\n]+)/);
    let desc = descMatch ? descMatch[1].trim() : "";
    if (desc === title || desc.startsWith(title.slice(0, 12))) {
      desc = truncateText(desc, 80);
    } else {
      desc = truncateText(desc, 100);
    }
    // 过滤百度推荐词垃圾条
    if (/大家还在搜|百度图片|正在思考/.test(title)) continue;
    hits.push({
      title: truncateText(title, 72),
      url: urlMatch ? urlMatch[1] : "",
      desc,
    });
    if (hits.length >= 5) break;
  }
  const q = (text.match(/Search results for '([^']+)'/) || [])[1] || "";
  return { query: q, hits };
}

function makeStepCard(kind, summaryHtml, rawText) {
  const wrap = document.createElement("div");
  wrap.className = `step-card step-${kind}`;
  const head = document.createElement("div");
  head.className = "step-card-head";
  const labels = {
    think: "Reasoning",
    tool: "Tool Call",
    search: "Search Summary",
    act: "Tool Result",
    step: "Step",
    log: "Log",
  };
  head.textContent = labels[kind] || "Progress";
  wrap.appendChild(head);

  const body = document.createElement("div");
  body.className = "step-card-body";
  body.innerHTML = summaryHtml;
  wrap.appendChild(body);

  if (rawText && rawText.length > 120) {
    const details = document.createElement("details");
    details.className = "step-raw";
    const summary = document.createElement("summary");
    summary.textContent = "View raw output";
    const pre = document.createElement("pre");
    pre.textContent = cleanNoise(rawText).slice(0, 6000);
    details.appendChild(summary);
    details.appendChild(pre);
    wrap.appendChild(details);
  }
  return wrap;
}

function renderSearchSummaryCard(raw) {
  const { query, hits } = parseSearchResults(raw);
  if (!hits.length) {
    return makeStepCard(
      "search",
      `<p>${truncateText(cleanNoise(raw), 220)}</p>`,
      raw
    );
  }
  const qLine = query
    ? `<div class="search-query">查询：${escapeHtml(query)}</div>`
    : "";
  const items = hits
    .map(
      (h, i) => `
      <li>
        <div class="hit-title">${i + 1}. ${escapeHtml(h.title)}</div>
        ${
          h.url
            ? `<a class="hit-url" href="${escapeAttr(h.url)}" target="_blank" rel="noopener">${escapeHtml(
                shortUrl(h.url)
              )}</a>`
            : ""
        }
        ${h.desc ? `<div class="hit-desc">${escapeHtml(h.desc)}</div>` : ""}
      </li>`
    )
    .join("");
  return makeStepCard(
    "search",
    `${qLine}<ol class="search-hits">${items}</ol>`,
    raw
  );
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, "&#39;");
}

function buildTraceStep(raw, type) {
  const text = String(raw || "");
  const cleaned = cleanNoise(text);

  if (
    /Search results for/i.test(cleaned) ||
    (cleaned.includes("URL:") && /\d+\.\s+/.test(cleaned) && cleaned.includes("Description:"))
  ) {
    return renderSearchSummaryCard(cleaned);
  }

  if (/thoughts:/i.test(cleaned)) {
    const thought = cleaned.replace(/^[\s\S]*?thoughts:\s*/i, "").trim();
    return makeStepCard(
      "think",
      `<p>${escapeHtml(truncateText(thought, 320))}</p>`,
      thought.length > 320 ? cleaned : null
    );
  }

  if (/selected\s+\d+\s+tools/i.test(cleaned) || /Tools being prepared/i.test(cleaned)) {
    const tools = cleaned.match(/\[([^\]]+)\]/);
    const msg = tools
      ? `Preparing tools: ${tools[1]}`
      : truncateText(cleaned.replace(/^[✨🛠️🧰🔧🎯📝🏁]+\s*/u, ""), 160);
    return makeStepCard("tool", `<p>${escapeHtml(msg)}</p>`, null);
  }

  if (/Activating tool/i.test(cleaned)) {
    const name = (cleaned.match(/'([^']+)'/) || [])[1] || "tool";
    return makeStepCard("tool", `<p>Activating <code>${escapeHtml(name)}</code></p>`, null);
  }

  if (/Tool arguments/i.test(cleaned)) {
    return makeStepCard(
      "tool",
      `<p>Args: ${escapeHtml(truncateText(cleaned.replace(/^[\s\S]*Tool arguments:\s*/i, ""), 180))}</p>`,
      cleaned
    );
  }

  if (/completed its mission/i.test(cleaned) || type === "act") {
    if (/web_search/i.test(cleaned) && /Search results for/i.test(cleaned)) {
      return renderSearchSummaryCard(cleaned);
    }
    if (/File created successfully|has been edited|Here's the result of running/i.test(cleaned)) {
      const path = (cleaned.match(/\/[^\s]+workspace\/[^\s]+/) || cleaned.match(/workspace\/[\w./-]+/) || [])[0];
      return makeStepCard(
        "act",
        `<p>Deliverable updated${path ? `: <code>${escapeHtml(path)}</code>` : ""}</p>`,
        cleaned
      );
    }
    return makeStepCard(
      "act",
      `<p>${escapeHtml(truncateText(cleaned, 220))}</p>`,
      cleaned.length > 220 ? cleaned : null
    );
  }

  if (/Executing step/i.test(cleaned) || type === "log") {
    const step = (cleaned.match(/Executing step[^\n]*/i) || [truncateText(cleaned, 80)])[0];
    return makeStepCard("step", `<p>${escapeHtml(step)}</p>`, null);
  }

  if (/Attempting search/i.test(cleaned)) {
    return makeStepCard("tool", `<p>${escapeHtml(truncateText(cleaned, 120))}</p>`, null);
  }

  return makeStepCard(
    "log",
    `<p>${escapeHtml(truncateText(cleaned, 200))}</p>`,
    cleaned.length > 200 ? cleaned : null
  );
}

window.buildTraceStep = buildTraceStep;
