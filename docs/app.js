const REGISTRY = window.WMR_REGISTRY;
const VERSION = REGISTRY.version;
const STORAGE_KEY = "web-measurement-report-v0.1";
const IS_MAC = /Mac|iPhone|iPad|iPod/.test(navigator.platform);
const MULTI_SELECT_KEY = IS_MAC ? "Cmd (⌘)" : "Ctrl";

const defaultReport = {
  version: VERSION,
  metadata: { title: "" },
  factors: {}
};

let report = loadReport();
let activeExport = "latex";
let tableMode = "compact";
let missingOnly = false;

const elements = {
  sectionNav: document.querySelector("#sectionNav"),
  factorForm: document.querySelector("#factorForm"),
  previewBody: document.querySelector("#previewTable tbody"),
  reportTitle: document.querySelector("#reportTitle"),
  reportedMetric: document.querySelector("#reportedMetric"),
  recommendedMetric: document.querySelector("#recommendedMetric"),
  naMetric: document.querySelector("#naMetric"),
  exportOutput: document.querySelector("#exportOutput")
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function groups() {
  return REGISTRY.groups;
}

function allFactors() {
  return groups().flatMap((group) => group.factors.map((factor) => ({
    ...factor,
    groupId: group.id,
    groupTitle: group.title
  })));
}

function factorById(factorId) {
  return allFactors().find((factor) => factor.id === factorId);
}

function itemById(itemId) {
  return allFactors().flatMap((factor) => factor.items).find((item) => item.id === itemId);
}

function factorGroups(factor) {
  const groups = [];

  const used = new Set();
  if (factor.itemGroups?.length) {
    for (const g of factor.itemGroups) {
      groups.push(g);
      for (const id of g.items || []) {
        used.add(id);
      }
    }
  }
  for (const item of factor.items || []) {
    if (used.has(item.id)) continue;
    groups.push({
      id: item.id,
      label: item.label,
      items: [item.id]
    });
  }
  return groups;
}

function emptyRowState() {
  return {
    status: "not_reported",
    note: "",
    fields: {},
    autoNa: false
  };
}

function newEntry(factor) {
  const groupsState = {};
  factorGroups(factor).forEach((group) => {
    groupsState[group.id] = emptyRowState();
  });
  return { groups: groupsState };
}

function normalizeFieldValue(input) {
  if (input && typeof input === "object" && !Array.isArray(input) && "value" in input) {
    return input.value ?? "";
  }
  return input ?? "";
}

function normalizeRowState(input) {
  if (!input) return emptyRowState();
  return {
    status: input.status || "not_reported",
    note: input.note || "",
    fields: { ...(input.fields || {}) },
    autoNa: Boolean(input.autoNa)
  };
}

function normalizeFactorState(factor, state = {}) {
  const normalized = {
    entries: Array.isArray(state.entries) ? state.entries.map((entry) => normalizeEntry(factor, entry)) : []
  };

  const minEntries = factor.repeatable ? (factor.minEntries || 0) : 1;
  while (normalized.entries.length < minEntries) {
    normalized.entries.push(newEntry(factor));
  }

  if (!factor.repeatable && normalized.entries.length > 1) {
    normalized.entries = normalized.entries.slice(0, 1);
  }

  return normalized;
}

function normalizeEntry(factor, entry = {}) {
  const normalized = newEntry(factor);
  factorGroups(factor).forEach((group) => {
    const row = normalized.groups[group.id];
    const sourceRow = entry.groups?.[group.id] || entry[group.id] || {};
    row.status = sourceRow.status || entry.status || row.status;
    row.note = sourceRow.note || entry.note || row.note;

    group.items.forEach((itemId) => {
      const value = sourceRow.fields?.[itemId] ?? entry.fields?.[itemId] ?? entry.items?.[itemId] ?? entry.values?.[itemId];
      row.fields[itemId] = normalizeFieldValue(value);
    });
  });
  return normalized;
}

function loadReport() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return clone(defaultReport);

  try {
    return normalizeReport(JSON.parse(stored));
  } catch {
    return clone(defaultReport);
  }
}

function normalizeReport(input) {
  const base = {
    ...clone(defaultReport),
    ...input,
    metadata: { ...clone(defaultReport).metadata, ...(input.metadata || {}) },
    factors: input.factors || {}
  };

  if (base.metadata.authors || base.metadata.id || base.metadata.scope) {
    base.metadata = { title: base.metadata.title || "" };
  }

  const normalized = clone(defaultReport);
  normalized.metadata = base.metadata;
  normalized.factors = {};

  allFactors().forEach((factor) => {
    normalized.factors[factor.id] = normalizeFactorState(factor, base.factors[factor.id]);
  });

  return normalized;
}

function saveReport() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(report));
}

function ensureFactorState(factorId) {
  const factor = factorById(factorId);
  if (!factor) return null;

  if (!report.factors[factorId]) {
    report.factors[factorId] = normalizeFactorState(factor, {});
  }

  const state = report.factors[factorId];
  const minEntries = factor.repeatable ? (factor.minEntries || 0) : 1;

  while (state.entries.length < minEntries) {
    state.entries.push(newEntry(factor));
  }

  if (!factor.repeatable && state.entries.length > 1) {
    state.entries = state.entries.slice(0, 1);
  }

  return state;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeLatex(value) {
  return String(value || "")
    .replaceAll("\\", "\\textbackslash{}")
    .replaceAll("&", "\\&")
    .replaceAll("%", "\\%")
    .replaceAll("$", "\\$")
    .replaceAll("#", "\\#")
    .replaceAll("_", "\\_")
    .replaceAll("{", "\\{")
    .replaceAll("}", "\\}")
    .replaceAll("--", "-{}-")
    .replaceAll("~", "\\textasciitilde{}")
    .replaceAll("^", "\\textasciicircum{}")
    .replace(/\n+/g, " ");
}

function selectedMultiValues(select) {
  return Array.from(select.selectedOptions).map((option) => option.value);
}

function hasValue(value) {
  return Array.isArray(value) ? value.length > 0 : String(value || "").trim().length > 0;
}

function itemEnabled(item) {
  return !item.dependsOn || isDependencyMet(item);
}

function isDependencyMet(definition) {
  if (!definition.dependsOn) return true;

  const dependency = definition.dependsOn;
  const values = itemState(dependency.itemId);
  const metValue = values.some((value) => {
    const v = value.value;
    const flat = Array.isArray(v) ? v : [v];
    return flat.some((x) => dependency.values.includes(x));
  });
  const notAllNA = values.some((value) => value.status !== "not_applicable");
  return metValue && notAllNA;
}

function dependencyReason(definition) {
  if (!definition.dependsOn) return "";
  return `Not applicable because ${definition.dependsOn.itemId} is not one of: ${definition.dependsOn.values.join(", ")}.`;
}

function buildItemToFactorIndex(registry) {
  const index = {};

  for (const group of registry.groups) {
    for (const factor of group.factors) {
      const factorId = factor.id;

      const collect = (items = []) => {
        for (const item of items) {
          index[item.id] = factorId;
        }
      };

      if (factor.items) collect(factor.items);

      if (factor.itemGroups) {
        for (const ig of factor.itemGroups) {
          collect(ig.items.map(id => ({ id })));
        }
      }
    }
  }

  return index;
}
const itemToFactor = buildItemToFactorIndex(window.WMR_REGISTRY);

function itemState(itemId) {
  const factorId = itemToFactor[itemId];
  if (!factorId) return [];

  const factorBlock = report.factors?.[factorId];
  if (!factorBlock?.entries) return [];

  const results = [];

  for (const entry of factorBlock.entries) {
    const groups = entry.groups || {};

    for (const group of Object.values(groups)) {
      const fields = group.fields || {};

      if (itemId in fields) {
        results.push({
          value: fields[itemId],
          status: group.status,
          note: group.note,
          autoNa: group.autoNa
        });
      }
    }
  }

  return results;
}

function groupEnabled(group) {
  factor = factorById(group.id.slice(0, group.id.lastIndexOf("-")));
  return isDependencyMet(factor);
}

function groupState(factorId, entryIndex, groupId) {
  return ensureFactorState(factorId)?.entries[entryIndex]?.groups[groupId];
}

function renderNav() {
  elements.sectionNav.innerHTML = `<div class="nav-group-label">Input</div>` + groups()
    .map((group, index) => `<button type="button" data-section="${group.id}" class="${index === 0 ? "active" : ""}">
      <strong>${escapeHtml(group.id)} · ${escapeHtml(group.title)}</strong>
      <span>${group.factors.length}</span>
    </button>`)
    .join("") + `<div class="nav-group-label">Output</div>
    <button type="button" data-section="summaryExport">
      <strong>Summary & export</strong>
      <span>↧</span>
    </button>`;

  elements.sectionNav.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.section === "summaryExport"
        ? document.querySelector("#summaryExport")
        : document.querySelector(`#group-${button.dataset.section}`);
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
      elements.sectionNav.querySelectorAll("button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    });
  });
}

function renderMetadata() {
  elements.reportTitle.value = report.metadata.title;
}

function renderForm() {
  syncDependencies();
  elements.factorForm.innerHTML = groups().map(renderGroup).join("");

  elements.factorForm.querySelectorAll("[data-group-field]").forEach((input) => {
    input.addEventListener("input", handleGroupInput);
    input.addEventListener("change", handleGroupInput);
  });

  elements.factorForm.querySelectorAll("[data-group-note]").forEach((input) => {
    input.addEventListener("input", handleGroupInput);
    input.addEventListener("change", handleGroupInput);
  });

  elements.factorForm.querySelectorAll("[data-group-status]").forEach((input) => {
    input.addEventListener("input", handleGroupInput);
    input.addEventListener("change", handleGroupInput);
  });

  elements.factorForm.querySelectorAll("[data-add-entry]").forEach((button) => {
    button.addEventListener("click", () => {
      const factor = factorById(button.dataset.addEntry);
      const state = ensureFactorState(button.dataset.addEntry);
      if (!factor || !state) return;
      state.entries.push(newEntry(factor));
      saveAndRender(true);
    });
  });

  elements.factorForm.querySelectorAll("[data-remove-entry]").forEach((button) => {
    button.addEventListener("click", () => {
      const factor = factorById(button.dataset.removeEntry);
      const state = ensureFactorState(button.dataset.removeEntry);
      if (!factor || !state) return;
      state.entries.splice(Number(button.dataset.entryIndex), 1);
      saveAndRender(true);
    });
  });

  applyMissingFilter();
}

function renderGroup(group) {
  return `<section class="category-block" id="group-${group.id}">
    <div class="category-title">
      <h4>${escapeHtml(group.id)} · ${escapeHtml(group.title)}</h4>
      <span>${group.factors.length} factors</span>
    </div>
    ${group.factors.map((factor) => renderFactor(factor, group)).join("")}
  </section>`;
}

function renderFactor(factor, category) {
  const state = ensureFactorState(factor.id);
  const entriesHtml = state.entries.map((entry, index) => renderEntry(factor, entry, index)).join("");
  const canAdd = factor.repeatable && (!factor.maxEntries || state.entries.length < factor.maxEntries);

  return `<article class="factor-card${factor.repeatable ? " repeatable-factor" : ""}" data-factor-card="${factor.id}" data-group="${category.id}">
    <div class="factor-head">
      <span class="factor-id">${escapeHtml(factor.id)}</span>
      <div>
        <div class="factor-title">${escapeHtml(factor.label)}</div>
        <div class="factor-help">${escapeHtml(factor.help || "")}</div>
      </div>
    </div>
    ${entriesHtml}
    ${canAdd ? `<button type="button" class="ghost-button add-entry" data-add-entry="${factor.id}">Add entry</button>` : ""}
  </article>`;
}

function renderEntry(factor, entry, entryIndex, enabled) {
  const groupsHtml = factorGroups(factor).map((group) => renderGroupRow(factor, entry, entryIndex, group, enabled)).join("");
  const removable = factor.repeatable && ensureFactorState(factor.id).entries.length > (factor.minEntries || 0);

  return `<section class="repeat-entry">
    ${factor.repeatable ? `<div class="repeat-entry-head">
      <div>
        <strong>${escapeHtml(factor.id)}-${entryIndex + 1}</strong>
        <span>${escapeHtml(factor.label)}</span>
      </div>
      ${removable ? `<button class="ghost-button remove-entry" data-remove-entry="${factor.id}" data-entry-index="${entryIndex}" type="button">Remove</button>` : ""}
    </div>` : ""}
    ${groupsHtml}
  </section>`;
}

function renderGroupRow(factor, entry, entryIndex, group) {
  const row = entry.groups[group.id];
  const item = itemById(group.id);
  const disabledReason = !groupEnabled(group)
    ? dependencyReason(factorById(group.id.slice(0, group.id.lastIndexOf("-"))))
    : (!itemEnabled(item) ? dependencyReason(item) : "");
  const rowEnabled = groupEnabled(group) && itemEnabled(item);
  const statusDisabled = !rowEnabled;

  const fields = group.items.map((itemId) => {
    const item = itemById(itemId);
    if (!item) return "";
    const itemActive = isDependencyMet(item) && rowEnabled;
    const value = row.fields[itemId] ?? "";

    return `<div class="field-block">
      <strong>${escapeHtml(item.label)}</strong>
      ${item.help ? `<em>${escapeHtml(item.help)}</em>` : ""}
      ${renderInput(item, value, {
        disabled: !itemActive,
        data: `data-group-field data-factor-id="${factor.id}" data-entry-index="${entryIndex}" data-group-id="${group.id}" data-item-id="${itemId}" data-field="value"`
      })}
      ${renderOptionNote(item, value)}
    </div>`;
  }).join("");

  return `<section class="item-row" data-group-row="${factor.id}-${group.id}-${entryIndex}" ${disabledReason ? `title="${escapeHtml(disabledReason)}"` : ""}>
    <div class="item-meta">
      <span class="item-id">${escapeHtml(group.id)}</span>
      <strong>${escapeHtml(group.label)}</strong>
      ${disabledReason ? `<div class="dependency-note">${escapeHtml(disabledReason)}</div>` : ""}
    </div>
    <div class="item-controls">
      ${renderStatusControl(row.status, statusDisabled, `data-group-status data-factor-id="${factor.id}" data-entry-index="${entryIndex}" data-group-id="${group.id}" data-field="status"`)}
      ${fields}
      <label class="note-field">
        Note
        <textarea data-group-note data-factor-id="${factor.id}" data-entry-index="${entryIndex}" data-group-id="${group.id}" data-item-id="${item.id}" data-field="note" ${statusDisabled ? "disabled" : ""}>${escapeHtml(row.note)}</textarea>
      </label>
    </div>
  </section>`;
}

function renderStatusControl(status, disabled, dataAttrs) {
  return `<label>
    Status
    <select ${dataAttrs} ${disabled ? "disabled" : ""}>
      ${statusOption("reported", "Reported", status)}
      ${statusOption("not_applicable", "Not applicable", status)}
      ${statusOption("unknown", "Unknown", status)}
      ${statusOption("not_reported", "Not reported", status)}
    </select>
  </label>`;
}

function renderInput(item, value, options = {}) {
  const disabled = options.disabled ? "disabled" : "";
  const data = options.data || "";
  const optionNames = Object.keys(item.options || {});

  if (item.type === "select") {
    return `<select ${data} ${disabled}>
      <option value=""></option>
      ${optionNames.map((option) => `<option value="${escapeHtml(option)}" ${value === option ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}
    </select>`;
  }

  if (item.type === "multi") {
    const values = Array.isArray(value) ? value : String(value || "").split("|").filter(Boolean);
    return `<div class="multi-select-wrapper">
      <select multiple ${data} ${disabled}>
        ${optionNames.map((option) => `<option value="${escapeHtml(option)}" ${values.includes(option) ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}
      </select>
      <span class="multi-select-hint">Hold ${MULTI_SELECT_KEY} to select multiple</span>
    </div>`;
  }

  if (item.type === "textarea") {
    return `<textarea ${data} ${disabled}>${escapeHtml(value)}</textarea>`;
  }

  const inputType = ["number", "date", "url"].includes(item.type) ? item.type : "text";
  return `<input ${data} type="${inputType}" value="${escapeHtml(value)}" ${disabled}>`;
}

function statusOption(value, label, selected) {
  return `<option value="${value}" ${selected === value ? "selected" : ""}>${label}</option>`;
}

function handleGroupInput(event) {
  const { factorId, entryIndex, groupId, itemId, field } = event.target.dataset;
  const state = ensureFactorState(factorId);
  const entry = state?.entries[Number(entryIndex)];
  const row = entry?.groups?.[groupId];
  if (!row) return;

  if (field === "status") {
    row.status = event.target.value;
  } else if (field === "note") {
    row.note = event.target.value;
  } else {
    row.fields[itemId] = event.target.multiple ? selectedMultiValues(event.target) : event.target.value;
    if (row.status === "not_reported" && Object.values(row.fields).some(hasValue)) {
      row.status = "reported";
    }
  }
  const needsRebuild = field === "status" || (field === "value" && event.target.type !== "text" && event.target.type !== "url" && event.target.type !== "number" && event.target.type !== "date");
  saveAndRender(needsRebuild);
}

function syncDependencies() {
  allFactors().forEach((factor) => {
    const state = ensureFactorState(factor.id);
    if (!state) return;

    state.entries.forEach((entry) => {
      factorGroups(factor).forEach((group) => {
        const row = entry.groups[group.id];
        if (!row) return;

        const enabled = groupEnabled(group) && itemEnabled(itemById(group.id));
        if (!enabled) {
          row.status = "not_applicable";
          row.autoNa = true;
        } else if (row.autoNa) {
          row.status = "not_reported";
          row.autoNa = false;
        }
      });
    });
  });
}

function saveAndRender(rebuildForm = false) {
  syncDependencies();
  saveReport();
  if (rebuildForm) renderForm();
  renderPreview();
  renderMetrics();
  renderExport();
  applyMissingFilter();
}

function formatGroupValue(group, row) {
  const values = (group.items || [])
    .map((itemId) => ({
      id: itemId,
      value: normalizeFieldValue(row.fields?.[itemId])
    }))
    .filter((x) => hasValue(x.value));

  if (values.length === 0) return "";

  if (values.length === 1) {
    const v = values[0].value;
    if (group.link) {
        const linkValue = values.find((v) => v.id === group.link)?.value || group.link;
        //return `[${combined}](${linkValue})`;
        return `<a href="${escapeHtml(linkValue)}" target="_blank" rel="noopener noreferrer">${escapeHtml(v)}</a>`
    }
    return v;
  }

  const base = values[0].value;
  const rest = values.slice(1).filter((v) => v.id !== group.link).map((v, i) => {
    const labelPrefix = group.labels?.[i] ?? "";
    const cleaned = labelPrefix
      ? `${labelPrefix}${v.value}`
      : v.value;
    return cleaned;
  });

  const combined = `${base} (${rest.join(", ")})`;
  if (group.link) {
    const linkValue = values.find((v) => v.id === group.link)?.value || group.link;
    //return `[${combined}](${linkValue})`;
    return `<a href="${escapeHtml(linkValue)}" target="_blank" rel="noopener noreferrer">${escapeHtml(combined)}</a>`
  }
  return combined;
}

function tableRows() {
  const rows = [];

  allFactors().forEach((factor) => {
    const state = ensureFactorState(factor.id);
    state.entries.forEach((entry, entryIndex) => {
      factorGroups(factor).forEach((group) => {
        const row = entry.groups[group.id];
        rows.push({
          categoryId: factor.groupId,
          factorId: factor.id,
          point: state.entries.length > 1 ? `${group.label} (${entryIndex + 1})` : group.label,
          status: row.status,
          value: formatGroupValue(group, row),
          note: row.note
        });
      });
    });
  });

  return rows;
}

function compactRows() {
  const rows = [];

  allFactors().forEach((factor) => {
    const state = ensureFactorState(factor.id);
    const groups = factorGroups(factor);

    groups.forEach((group) => {
      const entryCount = state.entries.length;
      const singleEntry = entryCount === 1;

      const mergedValues = [];
      const mergedNotes = [];

      state.entries.forEach((entry) => {
        const row = entry.groups[group.id];

        let value = formatGroupValue(group, row);
        if (!hasValue(value)) {
            value = latexValue(row);
        }
        const note = row?.note || "";

        mergedValues.push(value);
        mergedNotes.push(note);
      });

      rows.push({
        categoryId: factor.groupId,
        factorId: factor.id,
        point: group.label,
        status: state.entries[0]?.groups?.[group.id]?.status,
        value: singleEntry
          ? mergedValues[0]
          : mergedValues.map((v, i) => `${i + 1}. ${v || "-"}`).join(" "),
        note: singleEntry
          ? mergedNotes[0]
          : mergedNotes.map((n, i) => `${i + 1}. ${n || "-"}`).join(" ")
      });
    });
  });

  return rows;
}

function tableModeRows() {
  if (tableMode === "compact") {
    return compactRows();
  }
  return tableRows();
}

function renderPreview() {
  const rows = tableModeRows();
  let lastFactorId = null;
  let lastCategoryId = null;
  const tableRowsHtml = [];

  rows.forEach((row) => {
    if (row.categoryId && row.categoryId !== lastCategoryId) {
      const category = groups().find((group) => group.id === row.categoryId);
      if (category) {
        tableRowsHtml.push(`<tr class="group-header"><td colspan="4"><strong>${escapeHtml(category.title)} (${escapeHtml(category.id)})</strong></td></tr>`);
      }
      lastCategoryId = row.categoryId;
    }

    const showFactor = row.factorId !== lastFactorId;
    lastFactorId = row.factorId;
    tableRowsHtml.push(`<tr>
      <td>${showFactor ? escapeHtml(row.factorId) : ""}</td>
      <td>${escapeHtml(row.point)}</td>
      <td>${displayValue(row)}</td>
      <td><span class="detail-list">${escapeHtml(row.note)}</span></td>
    </tr>`);
  });

  elements.previewBody.innerHTML = tableRowsHtml.join("");
}

function displayValue(row) {
  if (row.status === "not_applicable") return `<span class="status-text status-na">N/A</span>`;
  if (row.status === "unknown") return `<span class="status-text status-missing">Unknown</span>`;
  if (row.status === "not_reported" && !hasValue(row.value)) return `<span class="status-text status-missing">Not reported</span>`;
  const formattedValue = formatValue(row.value) || "Reported";
  if (formattedValue.includes('<a href=')) {
    return formattedValue; // Already contains HTML, don't escape
  }
  return escapeHtml(formattedValue);
}

function formatValue(value) {
  return Array.isArray(value) ? value.join(", ") : String(value || "");
}

function renderMetrics() {
  const rows = tableRows();
  elements.reportedMetric.textContent = rows.filter((row) => row.status === "reported" && hasValue(row.value)).length;
  elements.recommendedMetric.textContent = rows.filter((row) => row.status === "not_reported" && !hasValue(row.value)).length;
  elements.naMetric.textContent = rows.filter((row) => row.status === "not_applicable").length;
}

function renderExport() {
  elements.exportOutput.value = activeExport === "json" ? JSON.stringify(report, null, 2) : toLatex();
}

function toLatex() {
  const rows = tableModeRows();
  let lastFactorId = null;
  let lastCategoryId = null;
  const latexRows = [];

  rows.forEach((row) => {
    if (row.categoryId && row.categoryId !== lastCategoryId) {
      const category = groups().find((group) => group.id === row.categoryId);
      if (category) {
        latexRows.push(`\\midrule`);
        latexRows.push(`\\multicolumn{4}{l}{\\textbf{${escapeLatex(category.title)} (${escapeLatex(category.id)})}} \\\\`);
        latexRows.push(`\\midrule`);
      }
      lastCategoryId = row.categoryId;
    }

    const factorId = row.factorId !== lastFactorId ? escapeLatex(row.factorId) : "";
    lastFactorId = row.factorId;
    const value = latexValue(row);
    // Check if value contains raw LaTeX (marked with __LATEX_RAW__)
    const escapedValue = value.includes('__LATEX_RAW__') 
      ? value.replace(/__LATEX_RAW__/g, '') 
      : escapeLatex(value);
    latexRows.push(`${factorId} & ${escapeLatex(row.point)} & ${escapedValue} & ${escapeLatex(row.note)} \\\\`);
  });

  const title = report.metadata.title ? ` for ${report.metadata.title}` : "";
  return `
% @online{WebMeasurementReportV${VERSION},
%	title = {{WebMeasurementReport} v${VERSION}},
%	url = {https://anonymous.4open.science/w/web-measurements-477B/},
%	author = {Anonymous},
%	urldate = {2026-06-06},
%	date = {2026},
%}
\\begin{table*}[t]
\\centering
\\caption{\\textsc{WebMeasurementReport v${VERSION}\\cite{WebMeasurementReportV${VERSION}}} summary${escapeLatex(title)}.}
\\footnotesize
\\begin{tabular}{p{0.12\\linewidth}p{0.20\\linewidth}p{0.22\\linewidth}p{0.40\\linewidth}}
\\toprule
Factor & Subfactor & Reported value & Notes \\\\
${latexRows.join("\n")}
\\bottomrule
\\end{tabular}
\\end{table*}`;
}

function latexValue(row) {
  if (row.status === "not_applicable") return "N/A";
  if (row.status === "unknown") return "Unknown";
  if (row.status === "not_reported" && !hasValue(row.value)) return "Not reported";

  const value = formatValue(row.value) || "Reported";
  const parts = value.split(/(<a href="[^"]+"[^>]*>[\s\S]*?<\/a>)/g);
  let hasLink = false;
  const converted = parts.map((part) => {
    const linkMatch = part.match(/<a href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/);

    if (linkMatch) {
      hasLink = true;
      const url = linkMatch[1];
      const text = escapeLatex(linkMatch[2]);
      return `\\href{${url}}{${text}}`;
    }
    return escapeLatex(part);
  });

  const result = converted.join("");
  return hasLink
    ? `__LATEX_RAW__${result}__LATEX_RAW__`
    : result;
}

function applyMissingFilter() {
  document.querySelectorAll("[data-factor-card]").forEach((card) => {
    const factor = factorById(card.dataset.factorCard);
    card.classList.toggle("is-hidden", missingOnly && !factorMissingData(factor));
  });
}

function factorMissingData(factor) {
  if (!factor) return false;
  const state = ensureFactorState(factor.id);
  return state.entries.some((entry) =>
    factorGroups(factor).some((group) => {
      const row = entry.groups[group.id];
      return row.status === "not_reported" && !group.items.some((itemId) => hasValue(row.fields[itemId]));
    })
  );
}

function renderOptionNote(item, value) {
  if (!item.options || !hasValue(value)) return "";
  const values = Array.isArray(value) ? value : [value];
  const notes = values.map((option) => item.options[option]).filter(Boolean);
  if (!notes.length) return "";
  return `<div class="option-note">${notes.map(escapeHtml).join(" ")}</div>`;
}

function download(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function loadExample() {
  report = clone(defaultReport);
  report.metadata.title = "Example Dummy Experiment";

  const setRow = (factorId, entryIndex, groupId, values, status = "reported", note = "") => {
    const factor = factorById(factorId);
    const state = ensureFactorState(factorId);
    const entry = state.entries[entryIndex];
    if (!factor || !entry) return;
    const row = entry.groups[groupId];
    if (!row) return;
    row.status = status;
    if (note){
      row.note = note;
    }
    Object.entries(values).forEach(([itemId, value]) => {
      row.fields[itemId] = value;
    });
  };

// ===================== D-Site =====================
  setRow("D-Site", 0, "D-Site-Source", {
    "D-Site-Source": "Tranco",
    "D-Site-SourceId": "334VL",
    "D-Site-Date": "2026-06-01",
    "D-Site-Link": "https://tranco-list.eu/list/334VL/1000000"
  }, "reported", "Default config");

  setRow("D-Site", 0, "D-Site-Count", {
    "D-Site-Count": "5000"
  }, "reported", "");

  setRow("D-Site", 0, "D-Site-Sampling", {
    "D-Site-Sampling": "Top-N ranking"
  }, "reported", "");

  setRow("D-Site", 0, "D-Site-Removed", {
    "D-Site-Removed": ["Unreachable", "TLD filter"]
  }, "reported", "Only .com, no DNS errors");

  setRow("D-Site", 0, "D-Site-CountFinal", {
    "D-Site-CountFinal": "4000"
  }, "reported", "");


  // ===================== D-Page =====================
  setRow("D-Page", 0, "D-Page-Scope", {
    "D-Page-Scope": "Landing page only"
  }, "reported", "");

  setRow("D-Page", 0, "D-Page-Conversion", {
    "D-Page-Conversion": [
      "https://domain/",
      "http://domain/"
    ]
  }, "reported", "");


  // ===================== D-Other =====================
  setRow("D-Other", 0, "D-Other-Description", {}, "not_applicable", "");

  // ===================== B-Type =====================
  setRow("B-Type", 0, "B-Type-Kind", {
    "B-Type-Kind": "Browser-based"
  }, "reported", "");


  // ===================== B-Instr =====================
  setRow("B-Instr", 0, "B-Instr-Tool", {
    "B-Instr-Tool": "Selenium",
    "B-Instr-Version": "4.40"
  }, "reported", "");

  setRow("B-Instr", 0, "B-Instr-Modification", {
    "B-Instr-Modification": ["Injected JavaScript"]
  }, "reported", "Using CDP Page.addScriptToEvaluateOnNewDocument, see Section 4.2");


  // ===================== B-Brow =====================
  setRow("B-Brow", 0, "B-Brow-Browser", {
    "B-Brow-Browser": "Chromium",
    "B-Brow-Version": "148.0.7778.96"
  }, "not_reported", "");


  // ===================== B-UA =====================
  setRow("B-UA", 0, "B-UA-Policy", {
    "B-UA-Policy": "Browser default"
  }, "reported", "");


  // ===================== B-Head =====================
  setRow("B-Head", 0, "B-Head-Mode", {
    "B-Head-Mode": "Headless"
  }, "reported", "--headless=new");


  // ===================== B-Set =====================
  setRow("B-Set", 0, "B-Set-Window", {
    "B-Set-Window": ""
  }, "unknown", "");

  setRow("B-Set", 0, "B-Set-Flags", {
    "B-Set-Flags": "--unsafely-treat-insecure-origin-as-secure"
  }, "reported", "Required to test on localhost");


  // ===================== E-Geo =====================
  setRow("E-Geo", 0, "E-Geo-Location", {
    "E-Geo-Location": ["United States"]
  }, "reported", "");


  // ===================== E-IP =====================
  setRow("E-IP", 0, "E-IP-Type", {
    "E-IP-Type": ["University"]
  }, "reported", "");

  setRow("E-IP", 0, "E-IP-Rotation", {
    "E-IP-Rotation": "Static IP"
  }, "reported", "");


  // ===================== E-Platform =====================
  setRow("E-Platform", 0, "E-Platform-OS", {
    "E-Platform-OS": "Windows"
  }, "reported", "11");


  // ===================== P-State =====================
  setRow("P-State", 0, "P-State-Mode", {
    "P-State-Mode": ["Stateless"]
  }, "reported", "");

  // ===================== P-Time =====================
  setRow("P-Time", 0, "P-Time-LoadEvent", {
    "P-Time-LoadEvent": "DOMContentLoaded"
  }, "reported", "");

  setRow("P-Time", 0, "P-Time-Timeout", {
    "P-Time-Timeout": "30"
  }, "reported", "");

  setRow("P-Time", 0, "P-Time-Dwell", {
    "P-Time-Dwell": "0"
  }, "reported", "");


  // ===================== P-Interact =====================
  setRow("P-Interact", 0, "P-Interact-Strategy", {
    "P-Interact-Strategy": ["None"]
  }, "reported", "");


  // ===================== P-Auth =====================
  setRow("P-Auth", 0, "P-Auth-Use", {
    "P-Auth-Use": "None"
  }, "reported", "");


  // ===================== P-Cookie =====================
  setRow("P-Cookie", 0, "P-Cookie-Policy", {
    "P-Cookie-Policy": "No interaction"
  }, "reported", "");


  // ===================== A-Detect =====================
  setRow("A-Detect", 0, "A-Detect-Method", {
    "A-Detect-Method": "See Sec 4.2"
  }, "reported", "");


  // ===================== A-Clean =====================
  setRow("A-Clean", 0, "A-Clean-PostExclusion", {
    "A-Clean-PostExclusion": ["Outliers"]
  }, "reported", "Sites with more than 1000 messages");


  // ===================== A-Manual =====================
  setRow("A-Manual", 0, "A-Manual-Used", {
    "A-Manual-Used": "Manual validation"
  }, "reported", "Random sample of 100 pages validated. 0 FPs.");


  // ===================== N-Bot =====================
  setRow("N-Bot", 0, "N-Bot-Tested", {
    "N-Bot-Tested": "Not considered"
  }, "reported", "");


  // ===================== N-Time =====================
  setRow("N-Time", 0, "N-Time-Design", {
    "N-Time-Design": "Single crawl"
  }, "reported", "");

  setRow("N-Time", 0, "N-Time-Date1", {
    "N-Time-Date1": "2026-06-01"
  }, "reported", "");

  setRow("N-Time", 0, "N-Time-Date2", {
    "N-Time-Date2": "2026-06-02"
  }, "reported", "");


  // ===================== N-Rand =====================
  setRow("N-Rand", 0, "N-Rand-Tested", {
    "N-Rand-Tested": "Small-scale experiment"
  }, "reported", "Subset of 100 sites measured twice. Results roughly the same.");


  // ===================== G-Limitations =====================
  setRow("G-Limitations", 0, "G-Limitations-Discussed", {
    "G-Limitations-Discussed": "Yes"
  }, "reported", "See Sec 7.1");


  // ===================== G-Ethics =====================
  setRow("G-Ethics", 0, "G-Ethics-Discussed", {
    "G-Ethics-Discussed": "Yes"
  }, "reported", "See Sec 7.2");


  // ===================== G-Open =====================
  setRow("G-Open", 0, "G-Open-Code", {
    "G-Open-Code": "Public"
  }, "reported", "https://code.code");

  setRow("G-Open", 0, "G-Open-Data", {
    "G-Open-Data": "Partially available"
  }, "reported", "Exact list of URLs visited in the code repo. Full dataset is too large.");

  saveAndRender(true);
  renderAll();
}

function bindEvents() {
  elements.reportTitle.addEventListener("input", (event) => {
    report.metadata.title = event.target.value;
    saveAndRender();
  });

  document.querySelector("#compactTable").addEventListener("click", () => {
    tableMode = "compact";
    setTableModeButtons();
    saveAndRender();
  });

  document.querySelector("#fullTable").addEventListener("click", () => {
    tableMode = "full";
    setTableModeButtons();
    saveAndRender();
  });

  document.querySelector("#showAll").addEventListener("click", () => {
    missingOnly = false;
    togglePair("#showAll", "#showMissing");
    applyMissingFilter();
  });

  document.querySelector("#showMissing").addEventListener("click", () => {
    missingOnly = true;
    togglePair("#showMissing", "#showAll");
    applyMissingFilter();
  });

  document.querySelectorAll("[data-export-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      activeExport = button.dataset.exportTab;
      document.querySelectorAll("[data-export-tab]").forEach((item) => item.classList.toggle("active", item === button));
      renderExport();
    });
  });

  document.querySelector("#downloadJson").addEventListener("click", () => {
    const slug = report.metadata.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "web-measurement-report";
    download(`${slug}.json`, JSON.stringify(report, null, 2), "application/json");
  });

  document.querySelector("#copyExport").addEventListener("click", async () => {
    elements.exportOutput.select();
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(elements.exportOutput.value);
    } else {
      document.execCommand("copy");
    }
  });

  document.querySelector("#importJson").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      const parsed = JSON.parse(await file.text());
      if (parsed.version && parsed.version !== VERSION) {
        const proceed = confirm(`Warning: This report is version ${parsed.version}, but the current application is version ${VERSION}. Importing may cause compatibility issues or data loss. Do you want to proceed?`);
        if (!proceed) {
          event.target.value = "";
          return;
        }
      }

      report = normalizeReport(parsed);
      saveAndRender(true);
    } catch {
      alert("The selected file is not a valid WebMeasurementReport JSON file.");
    }

    event.target.value = "";
  });

  document.querySelector("#loadExample").addEventListener("click", loadExample);

  document.querySelector("#resetReport").addEventListener("click", () => {
    if (!confirm("Reset this report?")) return;
    report = clone(defaultReport);
    saveAndRender(true);
    renderAll();
  });
}

function togglePair(activeSelector, inactiveSelector) {
  document.querySelector(activeSelector).classList.add("active");
  document.querySelector(inactiveSelector).classList.remove("active");
}

function setTableModeButtons() {
  document.querySelector("#compactTable").classList.toggle("active", tableMode === "compact");
  document.querySelector("#fullTable").classList.toggle("active", tableMode === "full");
}

function renderAll() {
  renderMetadata();
  renderNav();
  renderForm();
  renderPreview();
  renderMetrics();
  renderExport();
}

bindEvents();
renderAll();