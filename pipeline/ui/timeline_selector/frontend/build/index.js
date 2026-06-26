"use strict";
const root = document.getElementById("root");
let args = {};
let selectedColumn = null;
let activeTab = "overview";
let pendingActiveTab = null;
let computeBackend = "mps";
let useWeights = false;
let weightColumn = null;
let targetColumn = null;
let pendingTargetColumn = null;
let yearStart = null;
let yearEnd = null;
function sendMessage(type, data = {}) {
    window.parent.postMessage({ isStreamlitMessage: true, type, ...data }, "*");
}
function setFrameHeight() {
    sendMessage("streamlit:setFrameHeight", { height: document.documentElement.scrollHeight });
}
function publishValue() {
    sendMessage("streamlit:setComponentValue", {
        value: {
            selectedColumn,
            activeTab,
            computeBackend,
            useWeights,
            weightColumn,
            targetColumn,
            yearStart,
            yearEnd,
        },
    });
}
function updateActiveTab(tab) {
    activeTab = tab;
    root.querySelectorAll(".header-tab").forEach((button) => {
        const isActive = button.dataset.tab === activeTab;
        button.classList.toggle("is-active", isActive);
        button.setAttribute("aria-selected", String(isActive));
    });
}
function compactText(value, maxLength = 42) {
    const text = String(value || "").trim();
    if (!text)
        return "Non défini";
    return text.length <= maxLength ? text : `${text.slice(0, maxLength - 1)}…`;
}
function displayColumnName(column) {
    const text = String(column ?? "").trim();
    return text || "Colonne sans nom";
}
function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}
function highlightKeys(item) {
    const keys = item.highlight_keys || item.highlightKeys || [];
    return Array.isArray(keys) ? keys : [];
}
function isItemActive(item) {
    return item.key === activeTab || highlightKeys(item).includes(activeTab);
}
function renderStep(step) {
    const filled = step.filled ? " is-filled" : "";
    const active = isItemActive(step) ? " is-active" : "";
    const stepKey = step.key ? ` data-step-key="${escapeHtml(step.key)}"` : "";
    const value = step.label === "Univarié" && selectedColumn !== null
        ? displayColumnName(selectedColumn)
        : step.label === "Cible" && targetColumn !== null
            ? displayColumnName(targetColumn)
            : step.value;
    const isUnivariate = step.label === "Univarié" && Boolean(args.columns?.length);
    const isTarget = step.label === "Cible" && Boolean(args.targetColumns?.length);
    const isYearRange = step.label === "Années" &&
        args.yearMin !== null &&
        args.yearMin !== undefined &&
        args.yearMax !== null &&
        args.yearMax !== undefined;
    let valueHtml = `<div class="timeline-value">${escapeHtml(compactText(value))}</div>`;
    if (isUnivariate) {
        const options = (args.columns || [])
            .map((column) => {
            const selected = column === selectedColumn ? " selected" : "";
            return `<option value="${escapeHtml(column)}"${selected}>${escapeHtml(displayColumnName(column))}</option>`;
        })
            .join("");
        valueHtml = `<select class="univariate-select column-select" aria-label="Choisir la colonne active">${options}</select>`;
    }
    else if (isTarget) {
        const options = (args.targetColumns || [])
            .map((column) => {
            const selected = column === targetColumn ? " selected" : "";
            const label = column === "Aucune" ? "Aucune" : displayColumnName(column);
            return `<option value="${escapeHtml(column)}"${selected}>${escapeHtml(label)}</option>`;
        })
            .join("");
        valueHtml = `<select class="target-select column-select" aria-label="Choisir la variable cible">${options}</select>`;
    }
    else if (isYearRange) {
        const minimum = Number(args.yearMin);
        const maximum = Number(args.yearMax);
        const start = yearStart ?? minimum;
        const end = yearEnd ?? maximum;
        const disabled = minimum === maximum ? " disabled" : "";
        valueHtml = [
            '<div class="year-range-control">',
            `<div class="year-range-values"><span>${start}</span><span>${end}</span></div>`,
            '<div class="year-range-sliders">',
            `<input class="year-range-input year-range-start" type="range" min="${minimum}" max="${maximum}" value="${start}" aria-label="Année de début"${disabled}>`,
            `<input class="year-range-input year-range-end" type="range" min="${minimum}" max="${maximum}" value="${end}" aria-label="Année de fin"${disabled}>`,
            "</div>",
            "</div>",
        ].join("");
    }
    return [
        `<button class="timeline-step${filled}${active}" type="button"${stepKey}>`,
        '<div class="timeline-dot"></div>',
        '<div class="timeline-content">',
        `<div class="timeline-label">${escapeHtml(step.label)}</div>`,
        valueHtml,
        `<div class="timeline-detail">${escapeHtml(compactText(step.detail, 48))}</div>`,
        "</div>",
        "</button>",
    ].join("");
}
function renderPipelineStage(stage, index, total) {
    const filled = stage.filled ? " is-filled" : "";
    const active = isItemActive(stage) ? " is-active" : "";
    const tone = stage.tone ? ` tone-${escapeHtml(stage.tone)}` : "";
    const redAlert = stage.value === "Red Alert" ? " is-red-alert" : "";
    const disabled = stage.disabled || !stage.key ? " is-disabled" : "";
    const stageKey = stage.key ? ` data-stage-key="${escapeHtml(stage.key)}"` : "";
    const arrow = index < total - 1 ? '<span class="pipeline-arrow" aria-hidden="true">→</span>' : "";
    return [
        '<div class="pipeline-stage-wrap">',
        `<button class="pipeline-stage${filled}${active}${tone}${redAlert}${disabled}" type="button"${stageKey}${stage.disabled || !stage.key ? " disabled" : ""}>`,
        `<div class="pipeline-phase">${escapeHtml(stage.phase || "")}</div>`,
        `<div class="pipeline-label">${escapeHtml(stage.label || "")}</div>`,
        `<div class="pipeline-value">${escapeHtml(compactText(stage.value, 28))}</div>`,
        `<div class="pipeline-detail">${escapeHtml(compactText(stage.detail, 54))}</div>`,
        "</button>",
        arrow,
        "</div>",
    ].join("");
}
function bindEvents() {
    const select = root.querySelector(".univariate-select");
    if (select) {
        select.addEventListener("change", (event) => {
            selectedColumn = event.target.value;
            publishValue();
            render();
        });
    }
    const targetSelect = root.querySelector(".target-select");
    if (targetSelect) {
        targetSelect.addEventListener("change", (event) => {
            targetColumn = event.target.value || "Aucune";
            pendingTargetColumn = targetColumn;
            publishValue();
            render();
        });
    }
    root.querySelectorAll(".header-tab").forEach((button) => {
        button.addEventListener("click", () => {
            const nextTab = button.dataset.tab || "overview";
            if (nextTab === activeTab)
                return;
            pendingActiveTab = nextTab;
            updateActiveTab(nextTab);
            button.blur();
            publishValue();
        });
    });
    root.querySelectorAll(".timeline-step").forEach((button) => {
        button.addEventListener("click", () => {
            const nextTab = button.dataset.stepKey;
            if (!nextTab || nextTab === activeTab)
                return;
            pendingActiveTab = nextTab;
            activeTab = nextTab;
            publishValue();
            render();
        });
    });
    root.querySelectorAll(".pipeline-stage").forEach((button) => {
        button.addEventListener("click", () => {
            const nextTab = button.dataset.stageKey;
            if (!nextTab || nextTab === activeTab)
                return;
            pendingActiveTab = nextTab;
            activeTab = nextTab;
            publishValue();
            render();
        });
    });
    root.querySelectorAll(".backend-option").forEach((button) => {
        button.addEventListener("click", () => {
            computeBackend = button.dataset.backend || "mps";
            publishValue();
            render();
        });
    });
    const weightToggle = root.querySelector(".weight-toggle");
    if (weightToggle) {
        weightToggle.addEventListener("change", (event) => {
            const columns = args.weightColumns || [];
            useWeights = event.target.checked;
            if (useWeights && !weightColumn && columns.length > 0) {
                weightColumn = columns[0];
            }
            if (!useWeights) {
                weightColumn = null;
            }
            publishValue();
            render();
        });
    }
    const weightSelect = root.querySelector(".weight-select");
    if (weightSelect) {
        weightSelect.addEventListener("change", (event) => {
            weightColumn = event.target.value || null;
            useWeights = Boolean(weightColumn);
            publishValue();
            render();
        });
    }
    const yearStartInput = root.querySelector(".year-range-start");
    const yearEndInput = root.querySelector(".year-range-end");
    const updateYearRange = (changed) => {
        if (!yearStartInput || !yearEndInput)
            return;
        let nextStart = Number(yearStartInput.value);
        let nextEnd = Number(yearEndInput.value);
        if (nextStart > nextEnd) {
            if (changed === "start")
                nextEnd = nextStart;
            else
                nextStart = nextEnd;
        }
        yearStart = nextStart;
        yearEnd = nextEnd;
        publishValue();
        render();
    };
    yearStartInput?.addEventListener("change", () => updateYearRange("start"));
    yearEndInput?.addEventListener("change", () => updateYearRange("end"));
}
function render() {
    const steps = args.steps || [];
    const pipelineStages = args.pipelineStages || [];
    const datasetLabel = args.datasetLabel || "Aucun dataset chargé";
    const tabs = args.tabs || [];
    const weightColumns = args.weightColumns || [];
    const weightDisabled = weightColumns.length === 0;
    const weightOptions = weightColumns
        .map((column) => {
        const selected = column === weightColumn ? " selected" : "";
        return `<option value="${escapeHtml(column)}"${selected}>${escapeHtml(column)}</option>`;
    })
        .join("");
    const backendOptions = [
        ["cpu", "CPU"],
        ["mps", "MPS"],
        ["cuda", "CUDA"],
    ]
        .map(([key, label]) => {
        const selected = key === computeBackend ? " is-active" : "";
        return `<button class="backend-option${selected}" type="button" data-backend="${key}">${label}</button>`;
    })
        .join("");
    const tabHtml = tabs
        .map((tab) => {
        const selected = tab.key === activeTab ? " is-active" : "";
        const ariaSelected = tab.key === activeTab ? "true" : "false";
        return `<button class="header-tab${selected}" type="button" role="tab" aria-selected="${ariaSelected}" data-tab="${escapeHtml(tab.key)}">${escapeHtml(tab.label)}</button>`;
    })
        .join("");
    root.innerHTML = [
        '<div class="header-shell">',
        steps.length
            ? [
        '<div class="timeline-shell">',
        '<div class="timeline-title">',
        `<div class="backend-control" aria-label="Backend calcul">${backendOptions}</div>`,
        '<div class="weight-control">',
        '<span>Pondération</span>',
        `<label class="weight-switch"><input class="weight-toggle" type="checkbox"${useWeights ? " checked" : ""}${weightDisabled ? " disabled" : ""}><span></span></label>`,
        `<select class="weight-select" aria-label="Colonne de pondération"${!useWeights || weightDisabled ? " disabled" : ""}>${weightOptions}</select>`,
        "</div>",
        "</div>",
        `<div class="timeline-track">${steps.map(renderStep).join("")}</div>`,
        "</div>",
            ].join("")
            : "",
        pipelineStages.length
            ? `<div class="pipeline-shell"><div class="pipeline-map" aria-label="Pipeline PX8">${pipelineStages.map((stage, index) => renderPipelineStage(stage, index, pipelineStages.length)).join("")}</div></div>`
            : "",
        `<div class="header-tabs">${tabHtml}</div>`,
        "</div>",
    ].join("");
    bindEvents();
    window.requestAnimationFrame(setFrameHeight);
}
window.addEventListener("message", (event) => {
    const message = event.data || {};
    if (message.type !== "streamlit:render")
        return;
    args = message.args || {};
    selectedColumn = args.selectedColumn ?? args.default?.selectedColumn ?? null;
    const serverActiveTab = args.activeTab || "overview";
    if (pendingActiveTab === serverActiveTab) {
        pendingActiveTab = null;
    }
    activeTab = pendingActiveTab || serverActiveTab;
    computeBackend = args.computeBackend || "mps";
    useWeights = Boolean(args.useWeights);
    weightColumn = args.weightColumn || null;
    const serverTargetColumn = args.targetColumn ?? args.default?.targetColumn ?? "Aucune";
    if (pendingTargetColumn === serverTargetColumn) {
        pendingTargetColumn = null;
    }
    const previousTargetColumn = targetColumn;
    targetColumn = pendingTargetColumn || serverTargetColumn;
    yearStart = args.yearStart ?? args.default?.yearStart ?? args.yearMin ?? null;
    yearEnd = args.yearEnd ?? args.default?.yearEnd ?? args.yearMax ?? null;
    render();
    if (pendingTargetColumn === null
        && previousTargetColumn !== null
        && previousTargetColumn !== targetColumn) {
        window.requestAnimationFrame(publishValue);
    }
});
sendMessage("streamlit:componentReady", { apiVersion: 1 });
setFrameHeight();
