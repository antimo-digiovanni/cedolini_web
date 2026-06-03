const state = {
  headers: [],
  selectedBatchId: null,
  canOperate: false,
  currentJob: null,
  currentSummary: null,
};

let importCheckToken = 0;

const catalogFileInput = document.getElementById("catalog-file");
const catalogSheetNameInput = document.getElementById("catalog-sheet-name");
const catalogHeaderRowInput = document.getElementById("catalog-header-row");
const catalogForm = document.getElementById("catalog-form");
const catalogMessageBox = document.getElementById("catalog-message-box");
const catalogConflicts = document.getElementById("catalog-conflicts");
const catalogTable = document.getElementById("catalog-table");
const fileInput = document.getElementById("excel-file");
const sheetNameInput = document.getElementById("sheet-name");
const headerRowInput = document.getElementById("header-row");
const previewForm = document.getElementById("preview-form");
const importForm = document.getElementById("import-form");
const previewTable = document.getElementById("preview-table");
const importMessageBox = document.getElementById("import-message-box");
const importSkippedRows = document.getElementById("import-skipped-rows");
const palletColumn = document.getElementById("pallet-column");
const incomingColumn = document.getElementById("incoming-column");
const outgoingColumn = document.getElementById("outgoing-column");
const productColumn = document.getElementById("product-column");
const productCodeColumn = document.getElementById("product-code-column");
const reasonColumn = document.getElementById("reason-column");
const productionLotColumn = document.getElementById("production-lot-column");
const zunColumn = document.getElementById("zun-column");
const stats = document.getElementById("stats");
const itemsBody = document.getElementById("items-body");
const completedEditForm = document.getElementById("completed-edit-form");
const completedEditPallet = document.getElementById("completed-edit-pallet");
const completedEditProductCode = document.getElementById("completed-edit-product-code");
const completedEditPalletLabel = document.getElementById("completed-edit-pallet-label");
const completedEditOperator = document.getElementById("completed-edit-operator");
const completedEditIncoming = document.getElementById("completed-edit-incoming");
const completedEditOutgoing = document.getElementById("completed-edit-outgoing");
const completedEditZun = document.getElementById("completed-edit-zun");
const completedEditCancel = document.getElementById("completed-edit-cancel");
const completedEditMessage = document.getElementById("completed-edit-message");
const importStatus = document.getElementById("import-status");
const messageBox = document.getElementById("message-box");
const incomingForm = document.getElementById("incoming-form");
const incomingScan = document.getElementById("incoming-scan");
const operatorName = document.getElementById("operator-name");
const operatorBatchAlert = document.getElementById("operator-batch-alert");
const outgoingForm = document.getElementById("outgoing-form");
const outgoingScan = document.getElementById("outgoing-scan");
const outgoingProductCode = document.getElementById("outgoing-product-code");
const outgoingZun = document.getElementById("outgoing-zun");
const activePallets = document.getElementById("active-pallets");
const refreshDashboardButton = document.getElementById("refresh-dashboard");
const catalogItemsTitle = document.getElementById("catalog-items-title");
const itemsTableShell = document.getElementById("items-table-shell");
const jobCard = document.getElementById("job-card");
const jobProduct = document.getElementById("job-product");
const jobProductCode = document.getElementById("job-product-code");
const jobPallet = document.getElementById("job-pallet");
const jobReason = document.getElementById("job-reason");
const jobState = document.getElementById("job-state");
const waitingFicheButton = document.getElementById("waiting-fiche-button");
const openOutgoingButton = document.getElementById("open-outgoing-button");
const outgoingPanel = document.getElementById("outgoing-panel");
const waitingHint = document.getElementById("waiting-hint");
const batchName = document.getElementById("batch-name");
const batchMeta = document.getElementById("batch-meta");
const batchSelector = document.getElementById("batch-selector");
const batchViewNote = document.getElementById("batch-view-note");
const finishBatchButton = document.getElementById("finish-batch-button");
const deleteBatchButton = document.getElementById("delete-batch-button");
const wipeAllButton = document.getElementById("wipe-all-button");
const reportLink = document.getElementById("report-link");
const catalogSection = document.getElementById("catalog-section");
const importSection = document.getElementById("import-section");
const operatorSection = document.getElementById("operator-section");
const workspaceCatalogTab = document.getElementById("workspace-catalog-tab");
const workspaceImportTab = document.getElementById("workspace-import-tab");
const workspaceOperatorTab = document.getElementById("workspace-operator-tab");
const signatureModal = document.getElementById("signature-modal");
const signatureModalDetails = document.getElementById("signature-modal-details");
const signatureOperatorInput = document.getElementById("signature-operator-input");
const signatureCancelButton = document.getElementById("signature-cancel-button");
const signatureConfirmButton = document.getElementById("signature-confirm-button");
const APP_BASE_PATH = String(window.APP_BASE_PATH || "").replace(/\/$/, "");

let signatureResolver = null;

function appUrl(path) {
  const normalizedPath = String(path || "").startsWith("/") ? String(path || "") : `/${String(path || "")}`;
  return `${APP_BASE_PATH}${normalizedPath}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setWorkspace(mode) {
  const catalogMode = mode === "catalog";
  const importMode = mode === "import";
  const operatorMode = mode === "operator";
  catalogSection.classList.toggle("hidden", !catalogMode);
  importSection.classList.toggle("hidden", !importMode);
  operatorSection.classList.toggle("hidden", !operatorMode);
  workspaceCatalogTab.classList.toggle("active", catalogMode);
  workspaceImportTab.classList.toggle("active", importMode);
  workspaceOperatorTab.classList.toggle("active", operatorMode);
  catalogItemsTitle.textContent = catalogMode ? "Anagrafica importata" : "Situazione pallet";
  catalogTable.classList.toggle("hidden", !catalogMode);
  itemsTableShell.classList.toggle("hidden", catalogMode);
}

function showMessage(text, tone = "muted") {
  messageBox.className = `message-box ${tone}`;
  messageBox.textContent = text;
}

function showCompletedEditMessage(text, tone = "muted") {
  completedEditMessage.className = `message-box ${tone}`;
  completedEditMessage.textContent = text;
}

function showImportMessage(text, tone = "muted") {
  importMessageBox.className = `message-box ${tone}`;
  importMessageBox.textContent = text;
}

function showCatalogMessage(text, tone = "muted") {
  catalogMessageBox.className = `message-box ${tone}`;
  catalogMessageBox.textContent = text;
}

function renderOperatorBatchAlert(summary, item = state.currentJob) {
  const batchId = Number(item?.batch_id || summary?.batch_id || 0);
  const batchLabel = summary?.last_filename || (batchId ? `Lotto ${batchId}` : "");
  if (!batchId || !batchLabel) {
    operatorBatchAlert.classList.add("hidden");
    operatorBatchAlert.textContent = "";
    return;
  }

  operatorBatchAlert.className = "message-box error";
  operatorBatchAlert.textContent = `Stai lavorando il lotto ${batchLabel}.`;
}

function clearCatalogConflicts() {
  catalogConflicts.classList.add("hidden");
  catalogConflicts.innerHTML = "";
}

function renderCatalogTable(rows) {
  catalogTable.classList.remove("hidden");
  if (!rows?.length) {
    catalogTable.innerHTML = `
      <div class="preview-caption">Anagrafica vuota</div>
      <div class="message-box muted">Nessun codice prodotto presente in anagrafica.</div>
    `;
    return;
  }

  catalogTable.innerHTML = `
    <div class="preview-caption">Codici presenti in anagrafica: ${rows.length}</div>
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Codice prodotto</th>
            <th>Prodotto</th>
            <th>Ultima sincronizzazione</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              <td>${escapeHtml(row.product_code)}</td>
              <td>${escapeHtml(row.product_name)}</td>
              <td>${escapeHtml(row.synced_at || "-")}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function loadCatalogTable() {
  const response = await fetch(appUrl("/api/product-catalog?limit=500"));
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Impossibile caricare l'anagrafica importata.");
  }
  renderCatalogTable(payload.rows || []);
}

async function refreshWorkspaceData(options = {}) {
  await fetchDashboard(options);
  await loadCatalogTable();
}

function renderCatalogConflicts(conflicts) {
  if (!conflicts?.length) {
    clearCatalogConflicts();
    return;
  }

  catalogConflicts.classList.remove("hidden");
  catalogConflicts.innerHTML = `
    <div class="section-head compact-head">
      <h3>Conflitti anagrafica da risolvere</h3>
      <span class="badge warning">${conflicts.length} righe</span>
    </div>
    <div class="table-wrap">
      <table class="data-table issue-table">
        <thead>
          <tr>
            <th>Codice nuovo</th>
            <th>Prodotto nuovo</th>
            <th>Gia' censito</th>
            <th>Messaggio</th>
            <th>Azioni</th>
          </tr>
        </thead>
        <tbody>
          ${conflicts.map((row, index) => `
            <tr class="issue-row" data-index="${index}" data-current-product-code="${escapeHtml(row.current_product_code || "")}" data-current-product-name="${escapeHtml(row.current_product_name || "")}">
              <td><input type="text" class="catalog-conflict-code" value="${escapeHtml(row.product_code)}" /></td>
              <td><input type="text" class="catalog-conflict-name" value="${escapeHtml(row.product_name)}" /></td>
              <td>
                <div><strong>${escapeHtml(row.current_product_code || "-")}</strong></div>
                <div>${escapeHtml(row.current_product_name || "-")}</div>
              </td>
              <td>${escapeHtml(row.message || "Conflitto anagrafica")}</td>
              <td>
                <div class="table-actions">
                  <button type="button" class="secondary table-action-button catalog-resolve-button">Salva modifica</button>
                  <button type="button" class="table-action-button catalog-force-button">Forza registrazione</button>
                </div>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function resolveCatalogConflict(row, { force }) {
  const response = await fetch(appUrl("/api/product-catalog/resolve"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      current_product_code: row.current_product_code || "",
      current_product_name: row.current_product_name || "",
      product_code: row.product_code,
      product_name: row.product_name,
      force,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Impossibile aggiornare il conflitto anagrafica.");
  }
  return payload;
}

function closeSignatureModal(result = null) {
  signatureModal.classList.add("hidden");
  signatureModal.setAttribute("aria-hidden", "true");
  signatureOperatorInput.value = "";
  if (signatureResolver) {
    const resolver = signatureResolver;
    signatureResolver = null;
    resolver(result);
  }
}

function requestProductCodeSignature(currentOperator, expectedProductCode, outgoingProductCodeValue) {
  signatureModalDetails.textContent = [
    `Codice atteso da Excel: ${expectedProductCode}`,
    `Codice digitato dall'operatore: ${outgoingProductCodeValue}`,
    "",
    `Per firmare l'eccezione inserisci il nome operatore: ${currentOperator}`,
  ].join("\n");
  signatureOperatorInput.value = "";
  signatureModal.classList.remove("hidden");
  signatureModal.setAttribute("aria-hidden", "false");
  queueMicrotask(() => signatureOperatorInput.focus());
  return new Promise((resolve) => {
    signatureResolver = resolve;
  });
}

function clearImportSkippedRows() {
  importSkippedRows.innerHTML = "";
  importSkippedRows.classList.add("hidden");
}

function renderImportSkippedRows(rows, options = {}) {
  const {
    editable = false,
    title = editable ? "Righe da correggere prima dell'import" : "Righe scartate dall'import",
  } = options;

  if (!rows?.length) {
    clearImportSkippedRows();
    return;
  }

  const body = rows
    .map(
      (row) => `
        <tr class="issue-row${editable ? " issue-row-editable" : ""}" data-row-number="${escapeHtml(row.row_number || "")}">
          <td>${escapeHtml(row.row_number || "-")}</td>
          <td>${row.fiche || "-"}</td>
          <td>${row.pallet || "-"}</td>
          <td class="cell-product">${row.product_name || "-"}</td>
          <td>${row.zun_quantity || "-"}</td>
          <td class="cell-reason issue-reason-cell">${editable
            ? `<input type="text" class="issue-reason-input" value="${escapeHtml(row.reason || "")}" placeholder="Inserisci motivo riconfezionamento" autocomplete="off" />`
            : escapeHtml(row.expected_product_name || "-")}</td>
          <td>${editable
            ? `<label class="issue-discard-toggle"><input type="checkbox" class="issue-discard-checkbox" /> <span>Scarta</span></label>`
            : row.catalog_missing && row.product_code && row.product_name && row.product_name !== "prodotto non indicato"
              ? `<div class="table-actions"><button type="button" class="secondary table-action-button add-catalog-button" data-product-code="${escapeHtml(row.product_code)}" data-product-name="${escapeHtml(row.product_name)}">Aggiungi in anagrafica</button></div>`
              : "-"}</td>
        </tr>`
    )
    .join("");

  importSkippedRows.classList.remove("hidden");
  importSkippedRows.innerHTML = `
    <div class="preview-caption">${title}</div>
    <div class="table-shell">
      <table class="preview-grid">
        <thead>
          <tr>
            <th>Riga Excel</th>
            <th>Fiche</th>
            <th>Pallet</th>
            <th>Prodotto</th>
            <th>ZUN</th>
            <th>${editable ? "Motivo da usare" : "Prodotto anagrafica"}</th>
            <th>Azione</th>
          </tr>
        </thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

function syncIssueRowState(rowElement) {
  if (!rowElement) {
    return;
  }

  const discardCheckbox = rowElement.querySelector(".issue-discard-checkbox");
  const reasonInput = rowElement.querySelector(".issue-reason-input");
  if (!discardCheckbox || !reasonInput) {
    return;
  }

  const discarded = discardCheckbox.checked;
  reasonInput.disabled = discarded;
  rowElement.classList.toggle("issue-row-discarded", discarded);
}

function collectImportRowActions() {
  const actions = {};
  importSkippedRows.querySelectorAll("tr[data-row-number]").forEach((rowElement) => {
    const rowNumber = rowElement.dataset.rowNumber;
    const discardCheckbox = rowElement.querySelector(".issue-discard-checkbox");
    const reasonInput = rowElement.querySelector(".issue-reason-input");
    if (!rowNumber || !discardCheckbox || !reasonInput) {
      return;
    }

    const discard = discardCheckbox.checked;
    const reason = reasonInput.value.trim();
    if (!discard && !reason) {
      return;
    }

    actions[rowNumber] = { discard, reason };
  });
  return actions;
}

async function addProductToCatalog(productCode, productName) {
  const response = await fetch(appUrl("/api/product-catalog"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_code: productCode, product_name: productName }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Impossibile aggiornare l'anagrafica prodotti.");
  }
  return payload;
}

function getPendingImportRows() {
  return [...importSkippedRows.querySelectorAll("tr[data-row-number]")].filter((rowElement) => {
    const discardCheckbox = rowElement.querySelector(".issue-discard-checkbox");
    const reasonInput = rowElement.querySelector(".issue-reason-input");
    if (!discardCheckbox || !reasonInput) {
      return false;
    }
    return !discardCheckbox.checked && !reasonInput.value.trim();
  });
}

function buildImportFormData(includeRowActions = false) {
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("sheet_name", sheetNameInput.value.trim());
  formData.append("header_row", headerRowInput.value || "1");
  formData.append("pallet_column", palletColumn.value);
  formData.append("incoming_column", incomingColumn.value);
  formData.append("outgoing_column", outgoingColumn.value);
  formData.append("product_column", productColumn.value);
  formData.append("product_code_column", productCodeColumn.value);
  formData.append("reason_column", reasonColumn.value);
  formData.append("production_lot_column", productionLotColumn.value);
  formData.append("zun_column", zunColumn.value);
  if (includeRowActions) {
    formData.append("row_actions", JSON.stringify(collectImportRowActions()));
  }
  return formData;
}

async function submitCatalogImport(event) {
  event.preventDefault();
  if (!catalogFileInput.files.length) {
    showCatalogMessage("Seleziona un file anagrafica prima di continuare.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", catalogFileInput.files[0]);
  formData.append("sheet_name", catalogSheetNameInput.value.trim());
  formData.append("header_row", catalogHeaderRowInput.value || "1");
  const response = await fetch(appUrl("/api/product-catalog/import"), { method: "POST", body: formData });
  const payload = await response.json();
  if (!response.ok) {
    clearCatalogConflicts();
    showCatalogMessage(payload.detail || "Errore durante l'aggiornamento anagrafica.", "error");
    return;
  }

  renderCatalogConflicts(payload.conflicts || []);
  await loadCatalogTable();
  showCatalogMessage(payload.message || "Anagrafica aggiornata.", payload.conflicts?.length ? "warning" : "success");
}

async function inspectImportRows() {
  if (!fileInput.files.length || importForm.classList.contains("hidden") || !reasonColumn.value) {
    clearImportSkippedRows();
    return;
  }

  const currentToken = ++importCheckToken;
  const response = await fetch(appUrl("/api/import/check"), { method: "POST", body: buildImportFormData() });
  const payload = await response.json();
  if (currentToken !== importCheckToken) {
    return;
  }

  if (!response.ok) {
    if (payload.detail && typeof payload.detail === "object" && payload.detail.mismatch_rows?.length) {
      renderImportSkippedRows(payload.detail.mismatch_rows, {
        editable: false,
        title: "Righe con prodotto non coerente con l'anagrafica",
      });
      showImportMessage(payload.detail.message || "Errore durante il controllo righe.", "error");
      return;
    }
    clearImportSkippedRows();
    showImportMessage(payload.detail?.message || payload.detail || "Errore durante il controllo righe.", "error");
    return;
  }

  if (payload.issues?.length) {
    renderImportSkippedRows(payload.issues, { editable: true });
    showImportMessage(payload.message, "warning");
    return;
  }

  clearImportSkippedRows();
  showImportMessage(payload.message, "success");
}

function formatDateTime(value) {
  if (!value || value === "-") {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function getOperatorName() {
  return operatorName.value.trim();
}

function requireOperatorName() {
  const value = getOperatorName();
  if (!value) {
    showMessage("Inserisci il nome dell'operatore.", "error");
    operatorName.focus();
    return null;
  }
  return value;
}

function getOperatorLabel(item) {
  const labels = [];
  if (item.incoming_operator) {
    labels.push(`Entrata: ${item.incoming_operator}`);
  }
  if (item.waiting_operator) {
    labels.push(`Attesa: ${item.waiting_operator}`);
  }
  if (item.outgoing_operator) {
    labels.push(`Uscita: ${item.outgoing_operator}`);
  }
  return labels.length ? labels.join(" | ") : "-";
}

function fillSelect(select, headers) {
  const optionalLabels = {
    "pallet-column": "Usa la fiche entrata come pallet",
    "outgoing-column": "Registra la fiche uscita in fase finale",
    "product-column": "Nessuna colonna prodotto",
    "product-code-column": "Nessuna colonna codice prodotto",
    "zun-column": "Nessuna colonna ZUN",
  };
  const options = headers
    .filter((header) => header)
    .map((header) => `<option value="${header}">${header}</option>`);

  if (optionalLabels[select.id]) {
    options.unshift(`<option value="">${optionalLabels[select.id]}</option>`);
  }
  select.innerHTML = options.join("");
}

function guessColumns() {
  const lowerHeaders = state.headers.map((header) => header.toLowerCase());
  const choose = (terms) => {
    const index = lowerHeaders.findIndex((header) => terms.some((term) => header.includes(term)));
    return index >= 0 ? state.headers[index] : "";
  };
  const chooseReason = () => {
    const explicitMotivoIndex = lowerHeaders.findIndex(
      (header) => header.startsWith("motivo") || header.includes("motivo ") || header.includes("motivo_")
    );
    if (explicitMotivoIndex >= 0) {
      return state.headers[explicitMotivoIndex];
    }

    const riconfezionamentoIndex = lowerHeaders.findIndex(
      (header) => header.includes("riconfezionamento") && !header.includes("costo")
    );
    if (riconfezionamentoIndex >= 0) {
      return state.headers[riconfezionamentoIndex];
    }

    return choose(["nota"]);
  };

  palletColumn.value = choose(["pallet", "udc", "bancale"]) || choose(["codice prodotto", "cod prodotto", "codice", "code", "sku", "articolo"]);
  incomingColumn.value = choose(["n° fiche", "n fiche", "fiche", "entrata", "ingresso"]) || state.headers[0] || "";
  outgoingColumn.value = choose(["uscita", "out", "nuova", "new"]);
  productColumn.value = choose(["prodotto", "nome"]);
  productCodeColumn.value = choose(["codice prodotto", "cod prodotto", "codice", "code", "sku", "articolo"]);
  reasonColumn.value = chooseReason();
  productionLotColumn.value = choose(["lotto di produzione", "lotto produzione", "lotto", "batch", "production lot"]);
  zunColumn.value = choose(["q.ta", "qta", "zun", "basi"]);
}

function renderPreview(preview) {
  if (!preview.length) {
    previewTable.innerHTML = "<p class='muted-text'>Nessuna riga disponibile per l'anteprima.</p>";
    return;
  }
  const columns = Object.keys(preview[0]).filter((column) => !column.startsWith("__"));
  const head = columns.map((column) => `<th>${column}</th>`).join("");
  const body = preview
    .map((row) => `<tr>${columns.map((column) => `<td>${row[column] || ""}</td>`).join("")}</tr>`)
    .join("");

  previewTable.innerHTML = `
    <div class="preview-caption">Prime ${preview.length} righe del lotto</div>
    <div class="preview-hint">Scorri orizzontalmente per vedere tutte le colonne del file Excel.</div>
    <div class="table-shell preview-shell">
      <table class="preview-grid excel-preview-grid">
        <thead><tr>${head}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

function renderStats(summary) {
  stats.innerHTML = [
    { label: "Registrati", value: summary.registered ?? 0 },
    { label: "In lavorazione", value: summary.in_progress ?? 0 },
    { label: "Attesa fiches", value: summary.waiting_fiche ?? 0 },
    { label: "Completati", value: summary.completed ?? 0 },
    { label: "Totale", value: summary.total_items ?? 0 },
  ]
    .map((item) => `<article class="stat-pill"><span>${item.label}</span><strong>${item.value}</strong></article>`)
    .join("");

  importStatus.textContent = summary.last_filename ? `${summary.last_filename} importato` : "Nessun lotto importato";
}

function renderBatchSelector(batches, selectedBatchId, activeBatchId) {
  const options = ["<option value=''>Lotto corrente</option>"];
  batches.forEach((batch) => {
    const isActive = Number(batch.id) === Number(activeBatchId);
    const statusLabel = batch.completed_at ? "chiuso" : "aperto";
    const importedAt = formatDateTime(batch.imported_at);
    const label = `${batch.filename || `Lotto ${batch.id}`} | ${importedAt} | ${statusLabel}${isActive ? " | attivo" : ""}`;
    options.push(`<option value="${batch.id}">${escapeHtml(label)}</option>`);
  });
  batchSelector.innerHTML = options.join("");
  batchSelector.value = selectedBatchId && Number(selectedBatchId) !== Number(activeBatchId) ? String(selectedBatchId) : "";
}

function renderBatchInfo(summary, activeBatchId = summary.batch_id, canOperate = Boolean(summary.batch_id && !summary.completed_at)) {
  batchName.textContent = summary.last_filename || "Nessun lotto caricato";
  const importedAt = formatDateTime(summary.last_imported_at);
  const completedAt = summary.completed_at ? formatDateTime(summary.completed_at) : "Lotto aperto";
  batchMeta.textContent = `Importato: ${importedAt} | Chiusura: ${completedAt}`;
  const hasBatch = Boolean(summary.batch_id);
  finishBatchButton.disabled = !hasBatch || !canOperate;
  deleteBatchButton.disabled = !hasBatch || !canOperate;
  workspaceOperatorTab.disabled = false;
  batchViewNote.classList.toggle("hidden", hasBatch && !summary.completed_at);
  batchViewNote.textContent = !hasBatch
    ? ""
    : summary.completed_at
      ? "Questo lotto e chiuso: puoi consultarlo ma non lavorarlo."
      : Number(summary.batch_id) === Number(activeBatchId)
        ? ""
        : "Stai consultando un lotto aperto diverso da quello piu' recente. La scansione sposta automaticamente il flusso sul lotto del pallet.";
  if (summary.report_path) {
    const reportName = summary.report_path.split(/[\\/]/).pop();
    reportLink.href = appUrl(`/api/reports/${reportName}`);
    reportLink.textContent = "Apri report Excel";
    reportLink.classList.remove("hidden");
  } else {
    reportLink.classList.add("hidden");
    reportLink.removeAttribute("href");
  }
}

function renderItems(items) {
  itemsBody.innerHTML = items
    .map(
      (item) => {
        const rowClass = item.state === "completed"
          ? "pallet-row pallet-row-completed"
          : item.state === "waiting_fiche"
            ? "pallet-row pallet-row-waiting-fiche"
            : "pallet-row pallet-row-default";
        const productCodeChangeNote = Number.parseInt(item.product_code_changed || 0, 10)
          ? `Postilla: cambio codice prodotto autorizzato${item.product_code_change_operator ? ` da ${escapeHtml(item.product_code_change_operator)}` : ""}.`
          : "-";
        return `
        <tr class="${rowClass}">
          <td data-label="Codice prodotto">${escapeHtml(item.product_code || "-")}</td>
          <td data-label="Fiche entrata">${item.incoming_fiche}</td>
          <td data-label="Fiche uscita">${item.outgoing_fiche || "-"}</td>
          <td class="cell-product" data-label="Prodotto">${item.product_name || "-"}</td>
          <td data-label="Lotto produzione">${escapeHtml(item.production_lot || "-")}</td>
          <td class="cell-reason" data-label="Postilla cambio codice">${productCodeChangeNote === "-" ? "-" : `<span class="table-note warning-note">${productCodeChangeNote}</span>`}</td>
          <td data-label="ZUN">${item.zun_quantity ?? 0}</td>
          <td class="cell-reason" data-label="Motivo">${item.repackaging_reason || "-"}</td>
          <td data-label="Operatore">${getOperatorLabel(item)}</td>
          <td data-label="Stato"><span class="state ${item.state}">${item.state}</span></td>
          <td data-label="Entrata">${formatDateTime(item.scanned_incoming_at)}</td>
          <td data-label="Uscita">${formatDateTime(item.scanned_outgoing_at)}</td>
          <td data-label="Azioni">
            <div class="table-actions">
              <button type="button" class="secondary table-action-button edit-completed-button" data-pallet-code="${escapeHtml(item.pallet_code)}">Modifica</button>
              ${state.canOperate
                ? `<button type="button" class="secondary danger-button table-action-button reset-pallet-button" data-pallet-code="${escapeHtml(item.pallet_code)}">Reset</button>`
                : ""}
            </div>
          </td>
        </tr>`
      })
    .join("");
}

function resetCompletedEditForm() {
  completedEditForm.classList.add("hidden");
  completedEditPallet.value = "";
  completedEditProductCode.value = "";
  completedEditPalletLabel.value = "";
  completedEditOperator.value = "";
  completedEditIncoming.value = "";
  completedEditOutgoing.value = "";
  completedEditZun.value = "";
  state.currentJob = null;
  showCompletedEditMessage("Seleziona un pallet dalla tabella per modificare numero pallet, fiches e ZUN.", "muted");
}

async function openCompletedEdit(palletCode) {
  const params = new URLSearchParams();
  if (state.selectedBatchId) {
    params.set("batch_id", String(state.selectedBatchId));
  }
  const response = await fetch(appUrl(`/api/items/${encodeURIComponent(palletCode)}${params.toString() ? `?${params.toString()}` : ""}`));
  const payload = await response.json();
  if (!response.ok) {
    showMessage(payload.detail || "Impossibile caricare il pallet.", "error");
    return;
  }

  completedEditForm.classList.remove("hidden");
  completedEditPallet.value = payload.item.pallet_code || "";
  completedEditProductCode.value = payload.item.product_code || "";
  completedEditPalletLabel.value = payload.item.pallet_code || "";
  completedEditOperator.value = getOperatorName();
  completedEditIncoming.value = payload.item.incoming_fiche || "";
  completedEditOutgoing.value = payload.item.outgoing_fiche || "";
  completedEditZun.value = String(payload.item.zun_quantity ?? "");
  showCompletedEditMessage("Puoi modificare anche solo il numero pallet. Operatore facoltativo.", "warning");
  completedEditPalletLabel.focus();
}

async function submitCompletedEdit(event) {
  event.preventDefault();
  const palletCode = completedEditPallet.value.trim();
  const newPalletCode = completedEditPalletLabel.value.trim();
  const operator = completedEditOperator.value.trim();
  const incomingCode = completedEditIncoming.value.trim();
  const outgoingCode = completedEditOutgoing.value.trim();
  const productCode = completedEditProductCode.value.trim();
  const outgoingZunValue = Number.parseInt(completedEditZun.value, 10);

  if (!palletCode) {
    showCompletedEditMessage("Seleziona prima un pallet dalla tabella.", "error");
    return;
  }
  if (!newPalletCode) {
    showCompletedEditMessage("Inserisci il numero pallet aggiornato.", "error");
    completedEditPalletLabel.focus();
    return;
  }
  if (!incomingCode) {
    showCompletedEditMessage("Inserisci la fiche di entrata aggiornata.", "error");
    completedEditIncoming.focus();
    return;
  }
  if (!Number.isInteger(outgoingZunValue) || outgoingZunValue <= 0) {
    showCompletedEditMessage("Inserisci uno ZUN finale valido.", "error");
    completedEditZun.focus();
    return;
  }

  const response = await fetch(appUrl(`/api/items/${encodeURIComponent(palletCode)}/completed`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pallet_code: newPalletCode,
      incoming_code: incomingCode,
      outgoing_code: outgoingCode,
      outgoing_zun: outgoingZunValue,
      product_code: productCode,
      operator_name: operator,
      batch_id: state.selectedBatchId,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    showCompletedEditMessage(payload.detail?.message || "Impossibile aggiornare il pallet.", "error");
    return;
  }

  showCompletedEditMessage(payload.message, "success");
  showMessage(payload.message, "success");
  await fetchDashboard({ batchId: state.selectedBatchId });
  await openCompletedEdit(palletCode);
}

async function resetPalletRow(palletCode) {
  if (!window.confirm(`Confermi il reset del pallet ${palletCode}? Tornera' come appena importato.`)) {
    return;
  }

  const response = await fetch(appUrl(`/api/items/${encodeURIComponent(palletCode)}/reset`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ batch_id: state.selectedBatchId }),
  });
  const payload = await response.json();
  if (!response.ok) {
    showMessage(payload.detail?.message || "Impossibile resettare il pallet.", "error");
    return;
  }

  if (completedEditPallet.value === palletCode) {
    resetCompletedEditForm();
  }
  showMessage(payload.message, "success");
  await fetchDashboard({ batchId: state.selectedBatchId });
}

function renderActivePallets(pallets) {
  const options = pallets.length
    ? pallets
      .map((item) => `<option value="${item.pallet_code}">${item.pallet_code}${item.product_code ? ` | codice ${item.product_code}` : ""} - ${item.state === "waiting_fiche" ? "attesa fiches" : "in lavorazione"}</option>`)
      .join("")
    : "<option value=''>Nessuna pedana aperta</option>";
  activePallets.innerHTML = options;
}

function setOutgoingMode(enabled) {
  outgoingPanel.classList.toggle("hidden", !enabled);
  waitingHint.classList.toggle("hidden", enabled);
  if (enabled) {
    if (!outgoingZun.value) {
      outgoingZun.value = "1";
    }
    outgoingScan.focus();
  } else {
    outgoingScan.value = "";
    outgoingProductCode.value = "";
  }
}

function renderCurrentJob(item) {
  state.currentJob = item || null;
  if (!item) {
    jobCard.classList.add("hidden");
    jobProductCode.textContent = "";
    jobProductCode.classList.add("hidden");
    renderOperatorBatchAlert(state.currentSummary, null);
    setOutgoingMode(false);
    return;
  }

  jobCard.classList.remove("hidden");
  jobProduct.textContent = `Pallet di ${item.product_name || "prodotto non indicato"}`;
  jobProductCode.textContent = item.product_code || "CODICE EXCEL ASSENTE";
  jobProductCode.classList.remove("hidden");
  jobPallet.textContent = `Fiche entrata ${item.incoming_fiche} - pedana ${item.pallet_code} - ZUN ${item.zun_quantity ?? 0}`;
  jobReason.textContent = item.repackaging_reason
    ? `Bisogna ${item.repackaging_reason}`
    : "Motivo di riconfezionamento non presente nel lotto.";
  const stateText = item.state === "waiting_fiche"
    ? "Stato: in attesa di fiches"
    : item.state === "completed"
      ? "Stato: completato"
      : "Stato: in lavorazione";
  const incomingAt = formatDateTime(item.scanned_incoming_at);
  const outgoingAt = formatDateTime(item.scanned_outgoing_at);
  const operatorText = getOperatorLabel(item);
  jobState.textContent = `${stateText} | Operatore: ${operatorText} | Entrata: ${incomingAt}${outgoingAt !== "-" ? ` | Uscita: ${outgoingAt}` : ""}`;
  outgoingZun.value = String(item.zun_quantity ?? "");
  renderOperatorBatchAlert(state.currentSummary, item);
  setOutgoingMode(false);
}

function revealOperatorFlow() {
  setWorkspace("operator");
  if (operatorSection) {
    operatorSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  if (!getOperatorName()) {
    operatorName.focus();
    return;
  }

  incomingScan.focus();
}

async function loadCurrentJob(palletCode, batchIdOverride = state.selectedBatchId) {
  if (!palletCode) {
    renderCurrentJob(null);
    return;
  }

  const params = new URLSearchParams();
  if (batchIdOverride) {
    params.set("batch_id", String(batchIdOverride));
  }
  const response = await fetch(appUrl(`/api/items/${encodeURIComponent(palletCode)}${params.toString() ? `?${params.toString()}` : ""}`));
  const payload = await response.json();
  if (!response.ok) {
    showMessage(payload.detail || "Impossibile caricare la pedana.", "error");
    return;
  }
  renderCurrentJob(payload.item);
}

async function fetchDashboard(options = {}) {
  const { revealOperator = false, batchId = state.selectedBatchId, focusPalletCode = "" } = options;
  const params = new URLSearchParams();
  if (batchId) {
    params.set("batch_id", String(batchId));
  }
  const response = await fetch(appUrl(`/api/dashboard${params.toString() ? `?${params.toString()}` : ""}`));
  const payload = await response.json();
  state.selectedBatchId = payload.selected_batch_id || null;
  state.canOperate = Boolean(payload.can_operate);
  state.currentSummary = payload.summary || null;
  renderStats(payload.summary);
  renderBatchSelector(payload.batches || [], payload.selected_batch_id, payload.current_batch?.id || null);
  renderBatchInfo(payload.summary, payload.current_batch?.id || null, payload.can_operate);
  renderItems(payload.items);
  if (!payload.summary?.batch_id) {
    resetCompletedEditForm();
  }
  renderActivePallets(payload.active_pallets);
  if (focusPalletCode) {
    const matchingActivePallet = payload.active_pallets.find((item) => item.pallet_code === focusPalletCode);
    if (matchingActivePallet) {
      activePallets.value = matchingActivePallet.pallet_code;
    }
    await loadCurrentJob(focusPalletCode, payload.selected_batch_id || null);
  } else if (payload.active_pallets.length) {
    activePallets.value = payload.active_pallets[0].pallet_code;
    await loadCurrentJob(payload.active_pallets[0].pallet_code, payload.selected_batch_id || null);
  } else {
    renderCurrentJob(null);
  }

  if (revealOperator && payload.summary?.batch_id) {
    revealOperatorFlow();
  } else if (!payload.summary?.batch_id) {
    setWorkspace("catalog");
  }
}

async function submitPreview(event) {
  event.preventDefault();
  if (!fileInput.files.length) {
    showImportMessage("Seleziona un file Excel prima di continuare.", "error");
    return;
  }

  const response = await fetch(appUrl("/api/preview"), { method: "POST", body: buildImportFormData() });
  const payload = await response.json();
  if (!response.ok) {
    clearImportSkippedRows();
    showImportMessage(payload.detail || "Errore durante l'anteprima del file.", "error");
    return;
  }

  state.headers = payload.headers;
  setWorkspace("import");
  clearImportSkippedRows();
  sheetNameInput.value = payload.resolved_sheet_name || sheetNameInput.value;
  headerRowInput.value = payload.resolved_header_row || headerRowInput.value || "1";
  [palletColumn, incomingColumn, outgoingColumn, productColumn, productCodeColumn, reasonColumn, productionLotColumn, zunColumn].forEach((select) => {
    fillSelect(select, payload.headers);
  });
  guessColumns();
  renderPreview(payload.preview);
  importForm.classList.remove("hidden");
  showImportMessage(
    `Anteprima pronta: ${payload.row_count} righe rilevate nel lotto. Foglio ${payload.resolved_sheet_name}, intestazioni riga ${payload.resolved_header_row}.`,
    "success"
  );
  await inspectImportRows();
}

async function submitImport(event) {
  event.preventDefault();
  if (!fileInput.files.length) {
    showImportMessage("Seleziona un file Excel prima dell'import.", "error");
    return;
  }
  if (!reasonColumn.value) {
    showImportMessage("Seleziona la colonna del motivo riconfezionamento prima dell'import.", "error");
    reasonColumn.focus();
    return;
  }
  if (!productionLotColumn.value) {
    showImportMessage("Seleziona la colonna del lotto di produzione prima dell'import.", "error");
    productionLotColumn.focus();
    return;
  }

  const pendingRows = getPendingImportRows();
  if (pendingRows.length) {
    showImportMessage("Completa il motivo oppure marca come scartate tutte le righe evidenziate prima dell'import.", "warning");
    pendingRows[0].querySelector(".issue-reason-input")?.focus();
    return;
  }

  const response = await fetch(appUrl("/api/import"), { method: "POST", body: buildImportFormData(true) });
  const payload = await response.json();
  if (!response.ok) {
    if (payload.detail && typeof payload.detail === "object") {
      if (payload.detail.mismatch_rows?.length) {
        renderImportSkippedRows(payload.detail.mismatch_rows, {
          editable: false,
          title: "Righe con prodotto non coerente con l'anagrafica",
        });
      } else {
        renderImportSkippedRows(payload.detail.skipped_rows || [], { editable: true });
      }
      showImportMessage(payload.detail.message || "Errore durante l'import del lotto.", "error");
    } else {
      clearImportSkippedRows();
      showImportMessage(payload.detail || "Errore durante l'import del lotto.", "error");
    }
    return;
  }

  clearImportSkippedRows();
  showImportMessage(payload.message, "success");
  state.selectedBatchId = null;
  await refreshWorkspaceData({ revealOperator: true });
}

async function deleteBatch() {
  const batchLabel = batchName.textContent?.trim();
  if (!batchLabel || batchLabel === "Nessun lotto caricato") {
    showMessage("Nessun lotto da cancellare.", "error");
    return;
  }

  if (!window.confirm(`Confermi la cancellazione del lotto ${batchLabel}?`)) {
    return;
  }

  const response = await fetch(appUrl("/api/batches/current"), { method: "DELETE" });
  const payload = await response.json();
  if (!response.ok) {
    showMessage(payload.detail || "Impossibile cancellare il lotto.", "error");
    return;
  }

  fileInput.value = "";
  previewTable.innerHTML = "";
  importForm.classList.add("hidden");
  state.headers = [];
  clearImportSkippedRows();
  resetCompletedEditForm();
  showImportMessage(payload.message, "success");
  renderStats(payload.summary);
  renderBatchInfo(payload.summary);
  renderItems(payload.items);
  renderActivePallets(payload.active_pallets);
  renderCurrentJob(null);
  state.selectedBatchId = null;
  setWorkspace("import");
}

async function wipeAllData() {
  const password = window.prompt("Inserisci la password amministratore per cancellare tutti i backup e tutti i lotti importati.");
  if (password === null) {
    return;
  }

  if (!window.confirm("Confermi la cancellazione totale di tutti i backup e di tutti i lotti importati? L'operazione e' irreversibile.")) {
    return;
  }

  const response = await fetch(appUrl("/api/admin/wipe-all"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  const payload = await response.json();
  if (!response.ok) {
    showMessage(payload.detail || "Impossibile cancellare tutti i dati.", "error");
    return;
  }

  fileInput.value = "";
  previewTable.innerHTML = "";
  importForm.classList.add("hidden");
  state.headers = [];
  state.selectedBatchId = null;
  clearImportSkippedRows();
  resetCompletedEditForm();
  showImportMessage(payload.message, "success");
  showMessage(payload.message, "success");
  renderStats(payload.summary);
  renderBatchSelector(payload.batches || [], null, null);
  renderBatchInfo(payload.summary);
  renderItems(payload.items || []);
  renderActivePallets(payload.active_pallets || []);
  renderCurrentJob(null);
  setWorkspace("import");
}

async function submitIncoming(event) {
  event.preventDefault();
  const currentOperator = requireOperatorName();
  if (!currentOperator) {
    return;
  }
  const code = incomingScan.value.trim();
  if (!code) {
    showMessage("Inserisci una scansione di entrata.", "error");
    return;
  }

  const response = await fetch(appUrl("/api/scan/incoming"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, operator_name: currentOperator, batch_id: state.selectedBatchId }),
  });
  const payload = await response.json();
  if (!response.ok) {
    showMessage(payload.detail?.message || "Entrata non valida.", "error");
    return;
  }

  incomingScan.value = "";
  showMessage(payload.message, "success");
  await fetchDashboard({
    batchId: payload.item?.batch_id || null,
    revealOperator: true,
    focusPalletCode: payload.item?.incoming_fiche || payload.item?.pallet_code || "",
  });
}

async function submitWaitingFiche() {
  const currentOperator = requireOperatorName();
  if (!currentOperator) {
    return;
  }
  const palletCode = activePallets.value;
  if (!palletCode) {
    showMessage("Seleziona una pedana aperta.", "error");
    return;
  }

  const response = await fetch(appUrl("/api/scan/waiting-fiche"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pallet_code: palletCode, operator_name: currentOperator, batch_id: state.currentJob?.batch_id || state.selectedBatchId }),
  });
  const payload = await response.json();
  if (!response.ok) {
    showMessage(payload.detail?.message || "Operazione non valida.", "error");
    return;
  }

  showMessage(payload.message, "success");
  await fetchDashboard({
    batchId: payload.item?.batch_id || state.currentJob?.batch_id || state.selectedBatchId,
    revealOperator: true,
    focusPalletCode: payload.item?.incoming_fiche || payload.item?.pallet_code || palletCode,
  });
}

async function submitOutgoing(event) {
  event.preventDefault();
  const currentOperator = requireOperatorName();
  if (!currentOperator) {
    return;
  }
  const palletCode = activePallets.value;
  const outgoingCode = outgoingScan.value.trim();
  const outgoingProductCodeValue = outgoingProductCode.value.trim();
  const outgoingZunValue = Number.parseInt(outgoingZun.value, 10);
  if (!palletCode || !outgoingCode) {
    showMessage("Seleziona una pedana e inserisci la nuova fiche.", "error");
    return;
  }
  if (!outgoingProductCodeValue) {
    showMessage("Inserisci il codice prodotto riportato sulla nuova fiche.", "error");
    outgoingProductCode.focus();
    return;
  }
  if (!Number.isInteger(outgoingZunValue) || outgoingZunValue <= 0) {
    showMessage("Inserisci lo ZUN finale da registrare alla chiusura del pallet.", "error");
    outgoingZun.focus();
    return;
  }

  let allowProductCodeChange = false;
  const expectedProductCode = (state.currentJob?.product_code || "").trim();
  if (expectedProductCode && outgoingProductCodeValue !== expectedProductCode) {
    const confirmChange = window.confirm(
      [
        "ATTENZIONE: il codice prodotto della nuova fiche non coincide con quello atteso.",
        "",
        `Codice atteso da Excel: ${expectedProductCode}`,
        `Codice digitato dall'operatore: ${outgoingProductCodeValue}`,
        "",
        "Premi OK solo se la rilavorazione riguarda davvero un cambio codice prodotto.",
        "Premi Annulla se il codice e' sbagliato e devi correggerlo.",
      ].join("\n")
    );
    if (!confirmChange) {
      showMessage("Codice prodotto non coerente. Contatta il responsabile e non finalizzare l'operazione.", "error");
      outgoingProductCode.focus();
      return;
    }

    const confirmSignature = window.confirm(
      [
        "Stai autorizzando un cambio codice prodotto.",
        "",
        "Premi OK per firmare l'eccezione inserendo il tuo nome operatore.",
        "Premi Annulla per bloccare la chiusura.",
      ].join("\n")
    );
    if (!confirmSignature) {
      showMessage("Cambio codice non firmato. Operazione annullata.", "warning");
      outgoingProductCode.focus();
      return;
    }

    const signature = await requestProductCodeSignature(
      currentOperator,
      expectedProductCode,
      outgoingProductCodeValue,
    );
    if (signature === null) {
      showMessage("Firma operatore annullata. Operazione bloccata.", "warning");
      outgoingProductCode.focus();
      return;
    }
    if (signature.trim().toLowerCase() !== currentOperator.trim().toLowerCase()) {
      showMessage("Firma non valida: inserisci esattamente il tuo nome operatore per autorizzare il cambio codice.", "error");
      outgoingProductCode.focus();
      return;
    }

    allowProductCodeChange = true;
  }

  const response = await fetch(appUrl("/api/scan/outgoing"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pallet_code: palletCode,
      outgoing_code: outgoingCode,
      outgoing_zun: outgoingZunValue,
      outgoing_product_code: outgoingProductCodeValue,
      operator_name: currentOperator,
      allow_product_code_change: allowProductCodeChange,
      batch_id: state.currentJob?.batch_id || state.selectedBatchId,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    if (payload.detail?.error_code === "missing_expected_product_code") {
      showMessage(payload.detail?.message || "Codice prodotto Excel mancante per questo pallet.", "error");
      return;
    }
    if (payload.detail?.error_code === "product_code_mismatch") {
      showMessage(payload.detail?.message || "Codice prodotto non coerente.", "warning");
      outgoingProductCode.focus();
      return;
    }
    showMessage(payload.detail?.message || "Uscita non valida.", "error");
    return;
  }

  outgoingScan.value = "";
  outgoingProductCode.value = "";
  outgoingZun.value = "";
  incomingScan.focus();
  showMessage(payload.message, "success");
  await fetchDashboard({
    batchId: payload.item?.batch_id || state.currentJob?.batch_id || state.selectedBatchId,
    revealOperator: true,
    focusPalletCode: payload.item?.incoming_fiche || payload.item?.pallet_code || palletCode,
  });
}

async function finishBatch() {
  const response = await fetch(appUrl("/api/batches/current/finish"), { method: "POST" });
  const payload = await response.json();
  if (!response.ok) {
    showMessage(payload.detail || "Impossibile chiudere il lotto.", "error");
    return;
  }

  showMessage(payload.message, "success");
  if (payload.report_url) {
    const reportUrl = appUrl(payload.report_url);
    reportLink.href = reportUrl;
    reportLink.textContent = "Apri report Excel";
    reportLink.classList.remove("hidden");
    window.open(reportUrl, "_blank", "noopener");
  }
  await fetchDashboard();
}

catalogForm.addEventListener("submit", submitCatalogImport);
previewForm.addEventListener("submit", submitPreview);
importForm.addEventListener("submit", submitImport);
incomingForm.addEventListener("submit", submitIncoming);
outgoingForm.addEventListener("submit", submitOutgoing);
refreshDashboardButton.addEventListener("click", () => {
  refreshWorkspaceData({ batchId: state.selectedBatchId }).catch(() => showMessage("Impossibile aggiornare lo stato iniziale.", "error"));
});
waitingFicheButton.addEventListener("click", submitWaitingFiche);
openOutgoingButton.addEventListener("click", async () => {
  const selectedPallet = activePallets.value;
  if (selectedPallet && state.currentJob?.pallet_code !== selectedPallet) {
    await loadCurrentJob(selectedPallet);
  }
  if (!state.currentJob || state.currentJob.state === "completed" || state.currentJob.state === "waiting_fiche") {
    showMessage("Seleziona un pallet in lavorazione prima di inserire la nuova fiche.", "warning");
    return;
  }
  setOutgoingMode(true);
});
workspaceImportTab.addEventListener("click", () => setWorkspace("import"));
workspaceCatalogTab.addEventListener("click", () => setWorkspace("catalog"));
workspaceOperatorTab.addEventListener("click", () => setWorkspace("operator"));
batchSelector.addEventListener("change", (event) => {
  const selected = event.target.value ? Number(event.target.value) : null;
  state.selectedBatchId = Number.isInteger(selected) ? selected : null;
  fetchDashboard({ batchId: state.selectedBatchId, revealOperator: !operatorSection.classList.contains("hidden") }).catch(() => showMessage("Impossibile caricare il lotto selezionato.", "error"));
});
activePallets.addEventListener("change", (event) => {
  loadCurrentJob(event.target.value).catch(() => showMessage("Impossibile caricare il dettaglio pedana.", "error"));
});
itemsBody.addEventListener("click", (event) => {
  const editButton = event.target.closest(".edit-completed-button");
  if (editButton) {
    openCompletedEdit(editButton.dataset.palletCode).catch(() => showCompletedEditMessage("Impossibile aprire la modifica del pallet completato.", "error"));
    return;
  }

  const resetButton = event.target.closest(".reset-pallet-button");
  if (!resetButton) {
    return;
  }
  resetPalletRow(resetButton.dataset.palletCode).catch(() => showMessage("Impossibile resettare il pallet.", "error"));
});
finishBatchButton.addEventListener("click", finishBatch);
deleteBatchButton.addEventListener("click", deleteBatch);
wipeAllButton.addEventListener("click", () => {
  wipeAllData().catch(() => showMessage("Impossibile cancellare tutti i dati.", "error"));
});
signatureCancelButton.addEventListener("click", () => closeSignatureModal(null));
signatureConfirmButton.addEventListener("click", () => closeSignatureModal(signatureOperatorInput.value.trim()));
signatureOperatorInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    closeSignatureModal(signatureOperatorInput.value.trim());
  }
  if (event.key === "Escape") {
    event.preventDefault();
    closeSignatureModal(null);
  }
});
completedEditForm.addEventListener("submit", submitCompletedEdit);
completedEditCancel.addEventListener("click", resetCompletedEditForm);
importSkippedRows.addEventListener("change", (event) => {
  const rowElement = event.target.closest("tr[data-row-number]");
  syncIssueRowState(rowElement);
});
importSkippedRows.addEventListener("click", (event) => {
  const addCatalogButton = event.target.closest(".add-catalog-button");
  if (!addCatalogButton) {
    return;
  }

  const productCode = addCatalogButton.dataset.productCode || "";
  const productName = addCatalogButton.dataset.productName || "";
  addCatalogButton.disabled = true;
  addProductToCatalog(productCode, productName)
    .then(async (payload) => {
      showImportMessage(payload.message || "Anagrafica prodotti aggiornata.", "success");
      await inspectImportRows();
    })
    .catch((error) => {
      showImportMessage(error.message || "Impossibile aggiornare l'anagrafica prodotti.", "error");
    })
    .finally(() => {
      addCatalogButton.disabled = false;
    });
});
catalogConflicts.addEventListener("click", (event) => {
  const actionButton = event.target.closest(".catalog-resolve-button, .catalog-force-button");
  if (!actionButton) {
    return;
  }

  const rowElement = actionButton.closest("tr[data-index]");
  const codeInput = rowElement?.querySelector(".catalog-conflict-code");
  const nameInput = rowElement?.querySelector(".catalog-conflict-name");
  if (!rowElement || !codeInput || !nameInput) {
    return;
  }

  const force = actionButton.classList.contains("catalog-force-button");
  const payload = {
    current_product_code: rowElement.dataset.currentProductCode || "",
    current_product_name: rowElement.dataset.currentProductName || "",
    product_code: codeInput.value.trim(),
    product_name: nameInput.value.trim(),
  };

  actionButton.disabled = true;
  resolveCatalogConflict(payload, { force })
    .then((result) => {
      rowElement.remove();
      if (!catalogConflicts.querySelector("tbody tr")) {
        clearCatalogConflicts();
      }
      return loadCatalogTable().then(() => result);
    })
    .then((result) => {
      showCatalogMessage(result.message || "Conflitto anagrafica risolto.", force ? "warning" : "success");
    })
    .catch((error) => {
      showCatalogMessage(error.message || "Impossibile risolvere il conflitto anagrafica.", "error");
    })
    .finally(() => {
      actionButton.disabled = false;
    });
});
fileInput.addEventListener("change", () => {
  sheetNameInput.value = "";
  headerRowInput.value = "1";
  clearImportSkippedRows();
  showImportMessage("File selezionato. Genera una nuova anteprima per leggere il foglio corretto.", "muted");
});
[palletColumn, incomingColumn, outgoingColumn, productColumn, productCodeColumn, reasonColumn, productionLotColumn, zunColumn].forEach((field) => {
  field.addEventListener("change", () => {
    inspectImportRows().catch(() => showImportMessage("Impossibile aggiornare il controllo righe.", "error"));
  });
});

setWorkspace("catalog");
resetCompletedEditForm();
refreshWorkspaceData({ revealOperator: true }).catch(() => {
  showCatalogMessage("Impossibile caricare l'anagrafica importata.", "error");
  showMessage("Impossibile caricare lo stato iniziale.", "error");
});