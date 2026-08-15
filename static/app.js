/**
 * Bulk Email Sender Pro - Frontend Application Engine
 */

document.addEventListener("DOMContentLoaded", () => {
  // ==========================================================================
  // STATE STORE
  // ==========================================================================
  const state = {
    config: {},
    files: { templates: [], csv_files: [], attachments: [] },
    currentTemplateFile: "compose.md",
    templateContent: "",
    currentCsvFile: "data.csv",
    csvHeaders: [],
    csvRows: [], // [{ index, data: {}, is_sent: bool, sent_record: {} }]
    currentRowIndex: 0,
    selectedAttachments: [],
    historyRecords: [],
    theme: localStorage.getItem("automailer_theme") || "dark"
  };

  // ==========================================================================
  // DOM ELEMENT SELECTORS
  // ==========================================================================
  const els = {
    // Navigation
    tabs: document.querySelectorAll(".nav-tab"),
    tabContents: document.querySelectorAll(".tab-content"),
    themeToggleBtn: document.getElementById("btn-theme-toggle"),
    badgeCsvRows: document.getElementById("badge-csv-rows"),
    badgeAttachmentsCount: document.getElementById("badge-attachments-count"),
    dotSendStatus: document.getElementById("dot-send-status"),
    smtpPill: document.getElementById("smtp-status-pill"),

    // Template Tab
    selectTemplateFile: document.getElementById("select-template-file"),
    templateFileExt: document.getElementById("template-file-ext"),
    templateCodeEditor: document.getElementById("template-code-editor"),
    templateFormatBadge: document.getElementById("template-format-badge"),
    liveSubjectPreview: document.getElementById("live-subject-preview"),
    liveRenderedPreview: document.getElementById("live-rendered-preview"),
    templateVarChips: document.getElementById("template-var-chips"),
    btnSaveTemplate: document.getElementById("btn-save-template"),
    btnNewTemplate: document.getElementById("btn-new-template"),

    // CSV Tab
    selectCsvFile: document.getElementById("select-csv-file"),
    csvTableHead: document.getElementById("csv-table-head"),
    csvTableBody: document.getElementById("csv-table-body"),
    statTotalRows: document.getElementById("stat-total-rows"),
    statSentRows: document.getElementById("stat-sent-rows"),
    statPendingRows: document.getElementById("stat-pending-rows"),
    csvSearchInput: document.getElementById("csv-search-input"),
    btnAddRow: document.getElementById("btn-add-row"),
    btnAddColumn: document.getElementById("btn-add-column"),
    btnSaveCsv: document.getElementById("btn-save-csv"),

    // Attachments Tab
    attachmentsTabFileInput: document.getElementById("attachments-tab-file-input"),
    attachmentsTabDropzone: document.getElementById("attachments-tab-dropzone"),
    attachmentsTabTbody: document.getElementById("attachments-tab-tbody"),
    btnRefreshAttachmentsTab: document.getElementById("btn-refresh-attachments-tab"),

    // Preview Tab
    btnPrevRow: document.getElementById("btn-prev-row"),
    btnNextRow: document.getElementById("btn-next-row"),
    currentRowDisplay: document.getElementById("current-row-display"),
    totalRowsDisplay: document.getElementById("total-rows-display"),
    selectRowJump: document.getElementById("select-row-jump"),
    currentRowStatusBadge: document.getElementById("current-row-status-badge"),
    duplicateWarningBanner: document.getElementById("duplicate-warning-banner"),
    duplicateWarningText: document.getElementById("duplicate-warning-text"),
    checkForceResend: document.getElementById("check-force-resend"),
    previewSenderMeta: document.getElementById("preview-sender-meta"),
    previewRecipientMeta: document.getElementById("preview-recipient-meta"),
    previewSubjectMeta: document.getElementById("preview-subject-meta"),
    previewBodyRendered: document.getElementById("preview-body-rendered"),
    previewAttachmentsList: document.getElementById("preview-attachments-list"),
    attachmentsDropZone: document.getElementById("attachments-drop-zone"),
    attachmentFileInput: document.getElementById("attachment-file-input"),
    attachmentsSelectedCount: document.getElementById("attachments-selected-count"),
    previewRowKeyvalues: document.getElementById("preview-row-keyvalues"),
    btnSendSingleRow: document.getElementById("btn-send-single-row"),
    sendResponseBox: document.getElementById("send-response-box"),
    btnOpenBatchModal: document.getElementById("btn-open-batch-modal"),

    // History Tab
    historyTableBody: document.getElementById("history-table-body"),
    btnRefreshHistory: document.getElementById("btn-refresh-history"),
    btnClearHistory: document.getElementById("btn-clear-history"),

    // Settings Tab
    inputDisplayName: document.getElementById("input-display-name"),
    inputSenderEmail: document.getElementById("input-sender-email"),
    inputPassword: document.getElementById("input-password"),
    btnTogglePwd: document.getElementById("btn-toggle-pwd"),
    inputSmtpHost: document.getElementById("input-smtp-host"),
    inputSmtpPort: document.getElementById("input-smtp-port"),
    inputDefaultSubject: document.getElementById("input-default-subject"),
    inputMailCompose: document.getElementById("input-mail-compose"),
    btnTestSmtp: document.getElementById("btn-test-smtp"),
    btnSaveSettings: document.getElementById("btn-save-settings"),
    smtpTestResultCard: document.getElementById("smtp-test-result-card"),
    smtpTestResultContent: document.getElementById("smtp-test-result-content"),

    // Batch Modal
    batchModal: document.getElementById("batch-modal"),
    btnCloseBatchModal: document.getElementById("btn-close-batch-modal"),
    btnCancelBatch: document.getElementById("btn-cancel-batch"),
    btnStartBatch: document.getElementById("btn-start-batch"),
    batchTargetCsvBadge: document.getElementById("batch-target-csv-badge"),
    inputBatchDelay: document.getElementById("input-batch-delay"),
    checkBatchForceAll: document.getElementById("check-batch-force-all"),
    batchProgressFill: document.getElementById("batch-progress-fill"),
    batchProgressStatusText: document.getElementById("batch-progress-status-text"),
    batchProgressPercent: document.getElementById("batch-progress-percent"),
    batchStatSent: document.getElementById("batch-stat-sent"),
    batchStatSkipped: document.getElementById("batch-stat-skipped"),
    batchStatFailed: document.getElementById("batch-stat-failed"),
    batchStatTotal: document.getElementById("batch-stat-total"),
    batchConsoleLog: document.getElementById("batch-console-log"),

    // Toast
    toastContainer: document.getElementById("toast-container")
  };

  // ==========================================================================
  // INITIALIZATION
  // ==========================================================================
  function init() {
    applyTheme(state.theme);
    setupEventListeners();
    refreshAllData();
  }

  async function refreshAllData() {
    await loadConfig();
    await loadFileList();
    await loadTemplate(state.currentTemplateFile);
    await loadCsv(state.currentCsvFile);
    await loadHistory();
    renderIcons();
  }

  function renderIcons() {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  // ==========================================================================
  // THEME MANAGEMENT
  // ==========================================================================
  function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("automailer_theme", theme);
    renderIcons();
  }

  // ==========================================================================
  // TOAST NOTIFICATIONS
  // ==========================================================================
  function showToast(message, type = "info", duration = 3500) {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let iconName = "info";
    if (type === "success") iconName = "check-circle";
    if (type === "error") iconName = "alert-circle";
    if (type === "warning") iconName = "alert-triangle";

    toast.innerHTML = `<i data-lucide="${iconName}"></i> <span>${message}</span>`;
    els.toastContainer.appendChild(toast);
    renderIcons();

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(40px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // ==========================================================================
  // API CALLS & DATA LOADERS
  // ==========================================================================

  // 1. Config (.env)
  async function loadConfig() {
    try {
      const res = await fetch("/api/config");
      const data = await res.json();
      state.config = data;

      // Populate Settings form
      els.inputDisplayName.value = data.display_name || "";
      els.inputSenderEmail.value = data.sender_email || "";
      els.inputPassword.value = data.password || "";
      els.inputSmtpHost.value = data.smtp_host || "smtp.gmail.com";
      els.inputSmtpPort.value = data.smtp_port || "587";
      els.inputDefaultSubject.value = data.subject || "";
      els.inputMailCompose.value = data.mail_compose || "compose.md";

      if (data.mail_compose) {
        state.currentTemplateFile = data.mail_compose;
      }
    } catch (err) {
      showToast("Failed to load .env settings", "error");
    }
  }

  async function saveConfig() {
    const payload = {
      display_name: els.inputDisplayName.value.trim(),
      sender_email: els.inputSenderEmail.value.trim(),
      password: els.inputPassword.value.trim(),
      smtp_host: els.inputSmtpHost.value.trim(),
      smtp_port: els.inputSmtpPort.value.trim(),
      subject: els.inputDefaultSubject.value.trim(),
      mail_compose: els.inputMailCompose.value.trim()
    };

    try {
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        state.config = data.config;
        showToast("Settings successfully saved to .env", "success");
        updatePreviewMeta();
      }
    } catch (err) {
      showToast("Error saving settings", "error");
    }
  }

  async function testSmtpConnection() {
    els.btnTestSmtp.disabled = true;
    els.btnTestSmtp.innerHTML = `<i data-lucide="loader" class="spin"></i> Testing Connection...`;
    renderIcons();

    const payload = {
      display_name: els.inputDisplayName.value.trim(),
      sender_email: els.inputSenderEmail.value.trim(),
      password: els.inputPassword.value.trim(),
      smtp_host: els.inputSmtpHost.value.trim(),
      smtp_port: els.inputSmtpPort.value.trim()
    };

    try {
      const res = await fetch("/api/config/test-smtp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await res.json();

      els.smtpTestResultCard.style.display = "block";
      if (result.success) {
        els.smtpTestResultCard.className = "card test-result-card alert-warning";
        els.smtpTestResultCard.style.borderLeftColor = "var(--success)";
        els.smtpTestResultContent.innerHTML = `<strong class="text-success"><i data-lucide="check-circle"></i> Connection Verified:</strong> ${result.message}`;
        showToast("SMTP Connection Successful!", "success");
      } else {
        els.smtpTestResultCard.className = "card test-result-card alert-warning";
        els.smtpTestResultCard.style.borderLeftColor = "var(--danger)";
        els.smtpTestResultContent.innerHTML = `<strong class="text-danger"><i data-lucide="alert-triangle"></i> Test Failed:</strong> ${result.message}`;
        showToast("SMTP Authentication Failed", "error");
      }
    } catch (err) {
      showToast("Error connecting to server", "error");
    } finally {
      els.btnTestSmtp.disabled = false;
      els.btnTestSmtp.innerHTML = `<i data-lucide="activity"></i> Test SMTP Connection`;
      renderIcons();
    }
  }

  // 2. File List
  async function loadFileList() {
    try {
      const res = await fetch("/api/files");
      const data = await res.json();
      state.files = data;

      // Populate Template File Select
      els.selectTemplateFile.innerHTML = "";
      data.templates.forEach(file => {
        const opt = document.createElement("option");
        opt.value = file;
        opt.textContent = file;
        if (file === state.currentTemplateFile) opt.selected = true;
        els.selectTemplateFile.appendChild(opt);
      });

      // Populate CSV File Select
      els.selectCsvFile.innerHTML = "";
      data.csv_files.forEach(file => {
        const opt = document.createElement("option");
        opt.value = file;
        opt.textContent = file;
        if (file === state.currentCsvFile) opt.selected = true;
        els.selectCsvFile.appendChild(opt);
      });

      // Render Attachments list in Preview tab
      renderAttachmentsList(data.attachments);
    } catch (err) {
      console.error("Error loading file list:", err);
    }
  }

  function renderAttachmentsList(attachments) {
    const list = attachments || [];
    if (els.badgeAttachmentsCount) {
      els.badgeAttachmentsCount.textContent = list.length;
    }

    // 1. Render Preview Sidebar List
    if (els.previewAttachmentsList) {
      if (list.length === 0) {
        els.previewAttachmentsList.innerHTML = `<p class="text-muted text-sm">No files attached yet. Drag & drop files above or click "Add Files".</p>`;
      } else {
        els.previewAttachmentsList.innerHTML = "";
        const currentlySelected = new Set(state.selectedAttachments.length > 0 ? state.selectedAttachments : list.map(a => a.path));

        list.forEach(att => {
          const item = document.createElement("div");
          item.className = "attachment-item";
          const sizeKb = (att.size / 1024).toFixed(1);
          const isChecked = currentlySelected.has(att.path);

          item.innerHTML = `
            <div class="attachment-left">
              <input type="checkbox" class="att-checkbox" value="${att.path}" ${isChecked ? 'checked' : ''}>
              <i data-lucide="file-text" style="width:14px; height:14px; color:var(--accent);"></i>
              <span class="attachment-name" title="${att.name}">${att.name}</span>
              <span class="attachment-size">(${sizeKb} KB)</span>
            </div>
            <button class="btn-delete-att" title="Delete attachment" data-delete-name="${att.name}">
              <i data-lucide="trash-2"></i>
            </button>
          `;
          els.previewAttachmentsList.appendChild(item);
        });
      }
    }

    // 2. Render Dedicated Attachments Tab Table
    if (els.attachmentsTabTbody) {
      if (list.length === 0) {
        els.attachmentsTabTbody.innerHTML = `<tr><td colspan="5" class="text-muted text-center" style="padding: 2rem;">No attachments uploaded yet. Drag & drop files in the box above.</td></tr>`;
      } else {
        els.attachmentsTabTbody.innerHTML = "";
        const currentlySelected = new Set(state.selectedAttachments.length > 0 ? state.selectedAttachments : list.map(a => a.path));

        list.forEach(att => {
          const tr = document.createElement("tr");
          const sizeKb = (att.size / 1024).toFixed(1);
          const isChecked = currentlySelected.has(att.path);

          tr.innerHTML = `
            <td style="text-align: center;">
              <input type="checkbox" class="att-checkbox-tab" value="${att.path}" ${isChecked ? 'checked' : ''} style="width:16px; height:16px; cursor:pointer;">
            </td>
            <td>
              <div style="display:flex; align-items:center; gap:0.5rem;">
                <i data-lucide="paperclip" style="color:var(--primary); width:16px; height:16px;"></i>
                <strong>${att.name}</strong>
              </div>
            </td>
            <td class="font-mono text-muted">${sizeKb} KB</td>
            <td class="font-mono text-muted text-sm" style="max-width:250px; overflow:hidden; text-overflow:ellipsis;">ATTACH/${att.name}</td>
            <td style="text-align: center;">
              <button class="btn btn-danger btn-sm btn-delete-att" data-delete-name="${att.name}" title="Delete file">
                <i data-lucide="trash-2"></i> Delete
              </button>
            </td>
          `;
          els.attachmentsTabTbody.appendChild(tr);
        });
      }
    }

    updateSelectedAttachmentsState();

    // Checkbox listeners (both sidebar & tab table)
    document.querySelectorAll(".att-checkbox, .att-checkbox-tab").forEach(cb => {
      cb.addEventListener("change", (e) => {
        const val = e.target.value;
        const checked = e.target.checked;
        // Sync both checkboxes
        document.querySelectorAll(`input[value="${CSS.escape(val)}"]`).forEach(input => input.checked = checked);
        updateSelectedAttachmentsState();
      });
    });

    // Delete listeners
    document.querySelectorAll(".btn-delete-att").forEach(btn => {
      btn.addEventListener("click", () => {
        const name = btn.dataset.deleteName;
        deleteAttachmentFile(name);
      });
    });

    renderIcons();
  }

  function updateSelectedAttachmentsState() {
    const checked = Array.from(document.querySelectorAll(".att-checkbox:checked, .att-checkbox-tab:checked")).map(el => el.value);
    state.selectedAttachments = Array.from(new Set(checked));
    if (els.attachmentsSelectedCount) {
      els.attachmentsSelectedCount.textContent = state.selectedAttachments.length;
    }
  }

  async function uploadFiles(files) {
    if (!files || files.length === 0) return;
    showToast(`Uploading ${files.length} file(s)...`, "info");

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch("/api/attachments/upload", {
          method: "POST",
          body: formData
        });
        const data = await res.json();
        if (data.success) {
          showToast(`Uploaded ${file.name}`, "success");
        } else {
          showToast(`Failed to upload ${file.name}: ${data.error}`, "error");
        }
      } catch (err) {
        showToast(`Error uploading ${file.name}`, "error");
      }
    }

    await loadFileList();
  }

  async function deleteAttachmentFile(filename) {
    if (!confirm(`Delete attachment '${filename}'?`)) return;

    try {
      const res = await fetch("/api/attachments/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: filename })
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Deleted ${filename}`, "info");
        await loadFileList();
      } else {
        showToast(`Failed to delete ${filename}`, "error");
      }
    } catch (err) {
      showToast("Error deleting attachment", "error");
    }
  }

  // 3. Template Management
  async function loadTemplate(filename) {
    try {
      state.currentTemplateFile = filename;
      const res = await fetch(`/api/template?file=${encodeURIComponent(filename)}`);
      const data = await res.json();
      state.templateContent = data.content || "";
      els.templateCodeEditor.value = state.templateContent;

      const isHtml = filename.endsWith(".html");
      els.templateFileExt.textContent = isHtml ? "HTML" : "Markdown";
      els.templateFormatBadge.textContent = isHtml ? "HTML Mode" : "Markdown Mode";

      updateLiveTemplateRender();
      updatePreviewMeta();
    } catch (err) {
      showToast(`Failed to load template ${filename}`, "error");
    }
  }

  async function saveTemplate() {
    const filename = state.currentTemplateFile;
    const content = els.templateCodeEditor.value;
    try {
      const res = await fetch("/api/template", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file: filename, content: content })
      });
      const data = await res.json();
      if (data.success) {
        state.templateContent = content;
        showToast(`Template ${filename} saved!`, "success");
        updateLiveTemplateRender();
        renderPreviewCurrentRow();
      }
    } catch (err) {
      showToast("Error saving template", "error");
    }
  }

  function updateLiveTemplateRender() {
    const raw = els.templateCodeEditor.value || "";
    const isHtml = state.currentTemplateFile.endsWith(".html");

    // Extract subject preview
    const defaultSubject = state.config.subject;
    if (defaultSubject && defaultSubject.trim()) {
      els.liveSubjectPreview.textContent = `Subject: ${defaultSubject}`;
    } else {
      const firstLine = raw.split("\n")[0] || "No Subject";
      els.liveSubjectPreview.textContent = `Subject: ${firstLine}`;
    }

    // Render body
    if (isHtml) {
      els.liveRenderedPreview.innerHTML = raw;
    } else {
      const bodyText = (!defaultSubject && raw.includes("\n")) 
        ? raw.substring(raw.indexOf("\n") + 1).trim()
        : raw;
      els.liveRenderedPreview.innerHTML = marked.parse(bodyText);
    }
  }

  function renderVariableChips() {
    els.templateVarChips.innerHTML = "";
    if (state.csvHeaders.length === 0) {
      els.templateVarChips.innerHTML = `<span class="text-muted text-sm">No CSV columns detected</span>`;
      return;
    }

    state.csvHeaders.forEach(col => {
      const chip = document.createElement("button");
      chip.className = "var-chip";
      chip.textContent = `$${col}`;
      chip.title = `Click to insert $${col} at cursor`;
      chip.addEventListener("click", () => insertVariableAtCursor(`$${col}`));
      els.templateVarChips.appendChild(chip);
    });
  }

  function insertVariableAtCursor(text) {
    const textarea = els.templateCodeEditor;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const val = textarea.value;

    textarea.value = val.substring(0, start) + text + val.substring(end);
    textarea.focus();
    textarea.selectionStart = textarea.selectionEnd = start + text.length;
    updateLiveTemplateRender();
    showToast(`Inserted ${text}`, "info", 1500);
  }

  // 4. CSV Management
  async function loadCsv(filename) {
    try {
      state.currentCsvFile = filename;
      const res = await fetch(`/api/csv?file=${encodeURIComponent(filename)}`);
      const data = await res.json();

      state.csvHeaders = data.headers || [];
      state.csvRows = data.rows || [];
      state.currentRowIndex = 0;

      // Update counters
      els.badgeCsvRows.textContent = state.csvRows.length;
      els.statTotalRows.textContent = state.csvRows.length;
      els.batchTargetCsvBadge.textContent = filename;

      renderVariableChips();
      renderCsvTable();
      updateCsvStats();
      populateRowJumpDropdown();
      renderPreviewCurrentRow();
    } catch (err) {
      showToast(`Failed to load CSV file ${filename}`, "error");
    }
  }

  function updateCsvStats() {
    const total = state.csvRows.length;
    const sent = state.csvRows.filter(r => r.is_sent).length;
    const pending = total - sent;

    els.statTotalRows.textContent = total;
    els.statSentRows.textContent = sent;
    els.statPendingRows.textContent = pending;

    // Navbar indicator
    if (pending === 0 && total > 0) {
      els.dotSendStatus.style.background = "var(--success)";
      els.dotSendStatus.title = "All emails sent!";
    } else {
      els.dotSendStatus.style.background = "var(--warning)";
      els.dotSendStatus.title = `${pending} emails pending`;
    }
  }

  function renderCsvTable(filterQuery = "") {
    els.csvTableHead.innerHTML = "";
    els.csvTableBody.innerHTML = "";

    if (state.csvHeaders.length === 0) return;

    // 1. Build Header Row
    const trHead = document.createElement("tr");
    trHead.innerHTML = `
      <th style="width: 50px;">#</th>
      <th style="width: 100px;">Status</th>
    `;
    state.csvHeaders.forEach(header => {
      const th = document.createElement("th");
      th.textContent = header;
      if (header.toUpperCase() === "EMAIL") {
        th.style.color = "var(--accent)";
      }
      trHead.appendChild(th);
    });
    trHead.innerHTML += `<th style="width: 60px; text-align: center;">Actions</th>`;
    els.csvTableHead.appendChild(trHead);

    // 2. Build Body Rows
    const q = filterQuery.toLowerCase().trim();
    state.csvRows.forEach((rowObj, index) => {
      const rowData = rowObj.data;
      
      // Filter logic
      if (q) {
        const matches = Object.values(rowData).some(val => String(val).toLowerCase().includes(q));
        if (!matches) return;
      }

      const tr = document.createElement("tr");
      tr.dataset.rowIndex = index;

      // Status Badge
      let statusBadgeHtml = `<span class="badge badge-pending"><i data-lucide="clock"></i> Pending</span>`;
      if (rowObj.is_sent) {
        statusBadgeHtml = `<span class="badge badge-success" title="Sent at ${rowObj.sent_record?.timestamp || ''}"><i data-lucide="check"></i> Sent</span>`;
      }

      tr.innerHTML = `
        <td class="font-mono text-muted">${index + 1}</td>
        <td>${statusBadgeHtml}</td>
      `;

      // Editable Data Cells
      state.csvHeaders.forEach(header => {
        const td = document.createElement("td");
        td.className = "editable-cell";
        td.contentEditable = "true";
        td.textContent = rowData[header] || "";
        td.dataset.header = header;
        td.dataset.rowIndex = index;

        td.addEventListener("blur", (e) => {
          const newVal = e.target.textContent.trim();
          state.csvRows[index].data[header] = newVal;
          if (index === state.currentRowIndex) {
            renderPreviewCurrentRow();
          }
        });

        tr.appendChild(td);
      });

      // Actions Column (Delete row)
      const tdAction = document.createElement("td");
      tdAction.style.textAlign = "center";
      tdAction.innerHTML = `
        <button class="table-btn-delete" title="Delete Row" data-delete-index="${index}">
          <i data-lucide="trash-2"></i>
        </button>
      `;
      tr.appendChild(tdAction);

      els.csvTableBody.appendChild(tr);
    });

    // Delete event listeners
    document.querySelectorAll(".table-btn-delete").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const idx = parseInt(btn.dataset.deleteIndex, 10);
        deleteCsvRow(idx);
      });
    });

    renderIcons();
  }

  function addCsvRow() {
    const newRowData = {};
    state.csvHeaders.forEach(h => {
      newRowData[h] = h.toUpperCase() === "EMAIL" ? "recipient@example.com" : "";
    });
    state.csvRows.push({
      index: state.csvRows.length,
      data: newRowData,
      is_sent: false,
      sent_record: null
    });
    renderCsvTable();
    updateCsvStats();
    populateRowJumpDropdown();
    showToast("Added new row at the bottom", "info");
  }

  function addCsvColumn() {
    const colName = prompt("Enter new column name (e.g. COMPANY, DUE_DATE):");
    if (!colName || !colName.trim()) return;
    const cleanCol = colName.trim().toUpperCase().replace(/\s+/g, "_");
    if (state.csvHeaders.includes(cleanCol)) {
      showToast(`Column ${cleanCol} already exists!`, "warning");
      return;
    }
    state.csvHeaders.push(cleanCol);
    state.csvRows.forEach(r => {
      r.data[cleanCol] = "";
    });
    renderVariableChips();
    renderCsvTable();
    showToast(`Added column $${cleanCol}`, "success");
  }

  function deleteCsvRow(index) {
    if (!confirm(`Delete row #${index + 1}?`)) return;
    state.csvRows.splice(index, 1);
    // Re-index
    state.csvRows.forEach((r, idx) => r.index = idx);
    if (state.currentRowIndex >= state.csvRows.length) {
      state.currentRowIndex = Math.max(0, state.csvRows.length - 1);
    }
    renderCsvTable();
    updateCsvStats();
    populateRowJumpDropdown();
    renderPreviewCurrentRow();
    showToast(`Deleted row #${index + 1}`, "info");
  }

  async function saveCsv() {
    const payload = {
      file: state.currentCsvFile,
      headers: state.csvHeaders,
      rows: state.csvRows
    };

    try {
      const res = await fetch("/api/csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        showToast(data.message, "success");
      }
    } catch (err) {
      showToast("Error saving CSV file", "error");
    }
  }

  // 5. Preview & Single Send Center
  function populateRowJumpDropdown() {
    els.selectRowJump.innerHTML = "";
    state.csvRows.forEach((r, idx) => {
      const opt = document.createElement("option");
      opt.value = idx;
      const email = r.data.EMAIL || r.data.email || `Row ${idx + 1}`;
      const name = r.data.NAME || r.data.name || "";
      opt.textContent = `#${idx + 1}: ${name ? name + ' - ' : ''}${email}`;
      if (idx === state.currentRowIndex) opt.selected = true;
      els.selectRowJump.appendChild(opt);
    });
  }

  function updatePreviewMeta() {
    const sender = state.config.sender_email || "your@email.com";
    const name = state.config.display_name || "";
    els.previewSenderMeta.textContent = name ? `${name} <${sender}>` : sender;
  }

  async function renderPreviewCurrentRow() {
    if (state.csvRows.length === 0) {
      els.currentRowDisplay.textContent = "0";
      els.totalRowsDisplay.textContent = "0";
      els.previewRecipientMeta.textContent = "No data loaded";
      els.previewSubjectMeta.textContent = "No data loaded";
      els.previewBodyRendered.innerHTML = `<p class="text-muted">No CSV records found. Please load or add rows in the CSV tab.</p>`;
      els.duplicateWarningBanner.style.display = "none";
      els.btnSendSingleRow.disabled = true;
      return;
    }

    const rowObj = state.csvRows[state.currentRowIndex];
    if (!rowObj) return;

    els.currentRowDisplay.textContent = state.currentRowIndex + 1;
    els.totalRowsDisplay.textContent = state.csvRows.length;
    els.selectRowJump.value = state.currentRowIndex;

    const rowData = rowObj.data;
    const isHtml = state.currentTemplateFile.endsWith(".html");

    // 1. Fetch Rendered Preview
    try {
      const res = await fetch("/api/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template: els.templateCodeEditor.value || state.templateContent,
          row: rowData,
          subject: state.config.subject,
          is_html: isHtml
        })
      });
      const preview = await res.json();

      els.previewRecipientMeta.textContent = preview.recipient || "(No EMAIL specified)";
      els.previewSubjectMeta.textContent = preview.subject || "(No Subject)";
      els.previewBodyRendered.innerHTML = preview.body_html || marked.parse(preview.body_text || "");
    } catch (err) {
      console.error("Preview render error:", err);
    }

    // 2. Duplicate Check & Sent Status Banner
    if (rowObj.is_sent) {
      const sentTime = rowObj.sent_record?.timestamp || "Unknown";
      els.currentRowStatusBadge.innerHTML = `<span class="badge badge-success"><i data-lucide="check"></i> Sent on ${sentTime}</span>`;
      
      els.duplicateWarningBanner.style.display = "flex";
      els.duplicateWarningText.innerHTML = `This recipient (<code>${rowData.EMAIL || ''}</code>) was already emailed on <strong>${sentTime}</strong>. To prevent accidental duplicates, resending is locked unless you check <em>Allow Force Resend</em> below.`;
      
      els.checkForceResend.checked = false;
      els.btnSendSingleRow.disabled = true;
      els.btnSendSingleRow.className = "btn btn-secondary btn-lg w-full";
      els.btnSendSingleRow.innerHTML = `<i data-lucide="shield-alert"></i> Already Sent (Locked)`;
    } else {
      els.currentRowStatusBadge.innerHTML = `<span class="badge badge-pending"><i data-lucide="clock"></i> Pending (Not sent yet)</span>`;
      els.duplicateWarningBanner.style.display = "none";
      els.btnSendSingleRow.disabled = false;
      els.btnSendSingleRow.className = "btn btn-primary btn-lg w-full";
      els.btnSendSingleRow.innerHTML = `<i data-lucide="mail"></i> Send This Email`;
    }

    // 3. Render Row Keyvalues list
    els.previewRowKeyvalues.innerHTML = "";
    Object.entries(rowData).forEach(([k, v]) => {
      const div = document.createElement("div");
      div.className = "kv-item";
      div.innerHTML = `<span class="kv-key">$${k}</span><span class="kv-val">${v || '<em class="text-muted">empty</em>'}</span>`;
      els.previewRowKeyvalues.appendChild(div);
    });

    els.sendResponseBox.style.display = "none";
    renderIcons();
  }

  // Single Row Send Action
  async function sendCurrentRowEmail() {
    const rowObj = state.csvRows[state.currentRowIndex];
    if (!rowObj) return;

    const isForce = els.checkForceResend.checked;
    if (rowObj.is_sent && !isForce) {
      showToast("Email already sent for this row! Check 'Allow Force Resend' to override.", "warning");
      return;
    }

    const email = rowObj.data.EMAIL || rowObj.data.email;
    if (!confirm(`Are you sure you want to send email to ${email}?`)) return;

    els.btnSendSingleRow.disabled = true;
    els.btnSendSingleRow.innerHTML = `<i data-lucide="loader" class="spin"></i> Sending email...`;
    renderIcons();

    const payload = {
      row: rowObj.data,
      template: els.templateCodeEditor.value || state.templateContent,
      row_index: state.currentRowIndex,
      csv_filename: state.currentCsvFile,
      force_send: isForce,
      is_html: state.currentTemplateFile.endsWith(".html"),
      attachments: state.selectedAttachments
    };

    try {
      const res = await fetch("/api/send/single", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await res.json();

      els.sendResponseBox.style.display = "block";
      if (result.success) {
        els.sendResponseBox.className = "send-response-card alert-warning";
        els.sendResponseBox.style.borderLeftColor = "var(--success)";
        els.sendResponseBox.innerHTML = `<strong class="text-success"><i data-lucide="check-circle"></i> Success:</strong> ${result.message}`;
        showToast(`Email sent to ${email}!`, "success");

        // Mark as sent in state
        rowObj.is_sent = true;
        rowObj.sent_record = result.record;
        updateCsvStats();
        renderCsvTable();
        renderPreviewCurrentRow();
        loadHistory();
      } else {
        els.sendResponseBox.className = "send-response-card alert-warning";
        els.sendResponseBox.style.borderLeftColor = "var(--danger)";
        els.sendResponseBox.innerHTML = `<strong class="text-danger"><i data-lucide="alert-triangle"></i> Failed:</strong> ${result.error || result.message}`;
        showToast(`Send failed: ${result.error || result.message}`, "error");
      }
    } catch (err) {
      showToast("Network error while sending email", "error");
    } finally {
      renderIcons();
    }
  }

  // 6. Batch Send Campaign
  let batchEventSource = null;

  function openBatchModal() {
    const total = state.csvRows.length;
    const sent = state.csvRows.filter(r => r.is_sent).length;
    const pending = total - sent;

    els.batchStatTotal.textContent = total;
    els.batchStatSent.textContent = sent;
    els.batchStatSkipped.textContent = 0;
    els.batchStatFailed.textContent = 0;
    els.batchProgressFill.style.width = "0%";
    els.batchProgressPercent.textContent = "0%";
    els.batchProgressStatusText.textContent = `${pending} pending emails ready to send`;
    els.batchConsoleLog.innerHTML = `<div class="console-line text-muted">[System] Ready. Target CSV: ${state.currentCsvFile} (${pending} pending).</div>`;

    els.btnStartBatch.disabled = false;
    els.btnStartBatch.innerHTML = `<i data-lucide="play"></i> Start Campaign`;
    els.batchModal.style.display = "flex";
    renderIcons();
  }

  function startBatchCampaign() {
    const isForceAll = els.checkBatchForceAll.checked;
    const delaySec = parseFloat(els.inputBatchDelay.value) || 1.5;

    els.btnStartBatch.disabled = true;
    els.btnStartBatch.innerHTML = `<i data-lucide="loader" class="spin"></i> Running Campaign...`;
    renderIcons();

    const payload = {
      template: els.templateCodeEditor.value || state.templateContent,
      rows: state.csvRows,
      csv_filename: state.currentCsvFile,
      force_all: isForceAll,
      is_html: state.currentTemplateFile.endsWith(".html"),
      attachments: state.selectedAttachments,
      delay_seconds: delaySec
    };

    fetch("/api/send/batch-stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(response => {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      function readChunk() {
        reader.read().then(({ done, value }) => {
          if (done) {
            els.btnStartBatch.disabled = false;
            els.btnStartBatch.innerHTML = `<i data-lucide="check"></i> Completed`;
            renderIcons();
            refreshAllData();
            return;
          }

          const text = decoder.decode(value);
          const lines = text.split("\n\n");
          lines.forEach(line => {
            if (line.startsWith("data: ")) {
              try {
                const event = JSON.parse(line.substring(6));
                handleBatchEvent(event);
              } catch (e) {}
            }
          });

          readChunk();
        });
      }

      readChunk();
    }).catch(err => {
      showToast("Batch transmission failed", "error");
      els.btnStartBatch.disabled = false;
      els.btnStartBatch.innerHTML = `<i data-lucide="play"></i> Start Campaign`;
      renderIcons();
    });
  }

  function handleBatchEvent(event) {
    if (event.type === "start") {
      logConsole(`[System] Campaign started for ${event.total} recipients...`);
    } else if (event.type === "progress") {
      const pct = Math.round((event.current / event.total) * 100);
      els.batchProgressFill.style.width = `${pct}%`;
      els.batchProgressPercent.textContent = `${pct}%`;
      els.batchProgressStatusText.textContent = `Processing row ${event.current} of ${event.total}...`;

      if (event.status === "sent") {
        const count = parseInt(els.batchStatSent.textContent, 10) + 1;
        els.batchStatSent.textContent = count;
        logConsole(`[${event.current}/${event.total}] ✅ Sent to ${event.email}`, "success");
        // Update local state
        const targetRow = state.csvRows.find(r => r.index === event.index);
        if (targetRow) {
          targetRow.is_sent = true;
          targetRow.sent_record = event.record;
        }
      } else if (event.status === "skipped") {
        const count = parseInt(els.batchStatSkipped.textContent, 10) + 1;
        els.batchStatSkipped.textContent = count;
        logConsole(`[${event.current}/${event.total}] ⏭️ Skipped ${event.email} (Already sent)`, "warning");
      } else if (event.status === "failed") {
        const count = parseInt(els.batchStatFailed.textContent, 10) + 1;
        els.batchStatFailed.textContent = count;
        logConsole(`[${event.current}/${event.total}] ❌ Failed ${event.email}: ${event.error}`, "error");
      }
    } else if (event.type === "complete") {
      els.batchProgressFill.style.width = "100%";
      els.batchProgressPercent.textContent = "100%";
      els.batchProgressStatusText.textContent = `Campaign Complete! Sent: ${event.sent}, Skipped: ${event.skipped}, Failed: ${event.failed}`;
      logConsole(`[System] 🏁 Campaign finished! Sent: ${event.sent} | Skipped: ${event.skipped} | Failed: ${event.failed}`, "success");
      updateCsvStats();
      renderCsvTable();
      renderPreviewCurrentRow();
      loadHistory();
      showToast("Batch campaign completed!", "success");
    }
  }

  function logConsole(msg, type = "") {
    const line = document.createElement("div");
    line.className = `console-line ${type}`;
    line.textContent = msg;
    els.batchConsoleLog.appendChild(line);
    els.batchConsoleLog.scrollTop = els.batchConsoleLog.scrollHeight;
  }

  // 7. History & Audit Log
  async function loadHistory() {
    try {
      const res = await fetch("/api/history");
      const data = await res.json();
      state.historyRecords = data.records || [];
      renderHistoryTable();
    } catch (err) {
      console.error("Error loading history:", err);
    }
  }

  function renderHistoryTable() {
    els.historyTableBody.innerHTML = "";
    if (state.historyRecords.length === 0) {
      els.historyTableBody.innerHTML = `<tr><td colspan="7" class="text-muted text-center" style="padding: 2rem;">No delivery history recorded yet.</td></tr>`;
      return;
    }

    state.historyRecords.forEach(rec => {
      const tr = document.createElement("tr");
      const isSuccess = rec.status === "sent";
      const statusBadge = isSuccess
        ? `<span class="badge badge-success"><i data-lucide="check"></i> Sent</span>`
        : `<span class="badge badge-danger"><i data-lucide="alert-circle"></i> Failed</span>`;

      tr.innerHTML = `
        <td class="font-mono text-muted text-sm">${rec.timestamp.replace("T", " ")}</td>
        <td class="font-mono text-highlight">${rec.email}</td>
        <td><strong>${rec.subject || '(No Subject)'}</strong></td>
        <td class="text-muted">${rec.csv_filename || 'data.csv'}</td>
        <td class="text-center font-mono">${(rec.row_index ?? 0) + 1}</td>
        <td>${statusBadge}</td>
        <td class="text-sm ${isSuccess ? 'text-muted' : 'text-danger'}">${rec.error || 'Delivered successfully'}</td>
      `;
      els.historyTableBody.appendChild(tr);
    });

    renderIcons();
  }

  async function resetTrackingHistory() {
    if (!confirm(`Are you sure you want to clear tracking history for ${state.currentCsvFile}? This will allow previously sent emails to be sent again.`)) return;

    try {
      const res = await fetch("/api/history/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ csv_file: state.currentCsvFile })
      });
      const data = await res.json();
      showToast(data.message, "info");
      await loadCsv(state.currentCsvFile);
      await loadHistory();
    } catch (err) {
      showToast("Error resetting tracking", "error");
    }
  }

  // ==========================================================================
  // EVENT LISTENERS SETUP
  // ==========================================================================
  function setupEventListeners() {
    // 1. Tab Navigation
    els.tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        const targetId = tab.dataset.tab;
        els.tabs.forEach(t => t.classList.remove("active"));
        els.tabContents.forEach(c => c.classList.remove("active"));

        tab.classList.add("active");
        const targetContent = document.getElementById(targetId);
        if (targetContent) targetContent.classList.add("active");

        renderIcons();

        // Refresh views on tab focus
        if (targetId === "tab-preview") {
          renderPreviewCurrentRow();
        } else if (targetId === "tab-history") {
          loadHistory();
        }
      });
    });

    // 2. Theme Toggle
    els.themeToggleBtn.addEventListener("click", () => {
      applyTheme(state.theme === "dark" ? "light" : "dark");
    });

    // 3. Template Events
    els.templateCodeEditor.addEventListener("input", () => {
      updateLiveTemplateRender();
    });

    els.selectTemplateFile.addEventListener("change", (e) => {
      loadTemplate(e.target.value);
    });

    els.btnSaveTemplate.addEventListener("click", saveTemplate);

    els.btnNewTemplate.addEventListener("click", () => {
      const name = prompt("Enter new template filename (e.g. welcome.md, newsletter.html):");
      if (!name || !name.trim()) return;
      state.currentTemplateFile = name.trim();
      state.templateContent = `# Email Subject\n\nHello $NAME,\n\nWrite your email body here.`;
      els.templateCodeEditor.value = state.templateContent;
      saveTemplate().then(() => loadFileList());
    });

    // 4. CSV Events
    els.selectCsvFile.addEventListener("change", (e) => {
      loadCsv(e.target.value);
    });

    els.btnAddRow.addEventListener("click", addCsvRow);
    els.btnAddColumn.addEventListener("click", addCsvColumn);
    els.btnSaveCsv.addEventListener("click", saveCsv);

    els.csvSearchInput.addEventListener("input", (e) => {
      renderCsvTable(e.target.value);
    });

    // 5. Preview & Send Events
    els.btnPrevRow.addEventListener("click", () => {
      if (state.currentRowIndex > 0) {
        state.currentRowIndex--;
        renderPreviewCurrentRow();
      }
    });

    els.btnNextRow.addEventListener("click", () => {
      if (state.currentRowIndex < state.csvRows.length - 1) {
        state.currentRowIndex++;
        renderPreviewCurrentRow();
      }
    });

    els.selectRowJump.addEventListener("change", (e) => {
      state.currentRowIndex = parseInt(e.target.value, 10);
      renderPreviewCurrentRow();
    });

    els.checkForceResend.addEventListener("change", (e) => {
      if (e.target.checked) {
        els.btnSendSingleRow.disabled = false;
        els.btnSendSingleRow.className = "btn btn-danger btn-lg w-full";
        els.btnSendSingleRow.innerHTML = `<i data-lucide="alert-triangle"></i> Force Send Again`;
      } else {
        els.btnSendSingleRow.disabled = true;
        els.btnSendSingleRow.className = "btn btn-secondary btn-lg w-full";
        els.btnSendSingleRow.innerHTML = `<i data-lucide="shield-alert"></i> Already Sent (Locked)`;
      }
      renderIcons();
    });

    els.btnSendSingleRow.addEventListener("click", sendCurrentRowEmail);

    // 6. Batch Modal Events
    els.btnOpenBatchModal.addEventListener("click", openBatchModal);
    els.btnCloseBatchModal.addEventListener("click", () => els.batchModal.style.display = "none");
    els.btnCancelBatch.addEventListener("click", () => els.batchModal.style.display = "none");
    els.btnStartBatch.addEventListener("click", startBatchCampaign);

    // 7. History Events
    els.btnRefreshHistory.addEventListener("click", loadHistory);
    els.btnClearHistory.addEventListener("click", resetTrackingHistory);

    // 8. Settings Events
    els.btnTogglePwd.addEventListener("click", () => {
      const type = els.inputPassword.getAttribute("type") === "password" ? "text" : "password";
      els.inputPassword.setAttribute("type", type);
    });

    els.btnTestSmtp.addEventListener("click", testSmtpConnection);
    els.btnSaveSettings.addEventListener("click", saveConfig);

    // 9. Attachment Events (Preview Tab & Attachments Tab)
    [els.attachmentFileInput, els.attachmentsTabFileInput].forEach(input => {
      if (input) {
        input.addEventListener("change", (e) => {
          uploadFiles(e.target.files);
          input.value = "";
        });
      }
    });

    if (els.btnRefreshAttachmentsTab) {
      els.btnRefreshAttachmentsTab.addEventListener("click", () => loadFileList());
    }

    [els.attachmentsDropZone, els.attachmentsTabDropzone].forEach(dropzone => {
      if (dropzone) {
        ["dragenter", "dragover"].forEach(evt => {
          dropzone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add("dragover");
          });
        });

        ["dragleave", "drop"].forEach(evt => {
          dropzone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove("dragover");
          });
        });

        dropzone.addEventListener("drop", (e) => {
          const dt = e.dataTransfer;
          if (dt && dt.files && dt.files.length > 0) {
            uploadFiles(dt.files);
          }
        });
      }
    });
  }

  // Run initialization
  init();
});
