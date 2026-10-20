/* ==========================================================================
   APP.JS - CLIENT CONTROLLER FOR HINGLISH SUBTITLE GENERATOR
   Connects UI to FastAPI backend, manages drag-and-drop, drawer, and search.
   ========================================================================== */

let currentFile = null;
let currentResults = null;
let currentSegments = [];
let activeSegmentIndex = null;

const initialConfig = window.__INITIAL_CONFIG__ || {};
let selectedLanguage = initialConfig.selected_language || localStorage.getItem("selectedLanguage") || "mixed";
let selectedDevice = initialConfig.selected_device || localStorage.getItem("selectedDevice") || "auto";
let selectedModel = initialConfig.selected_model || localStorage.getItem("selectedModel") || "medium";
let selectedPacing = initialConfig.selected_pacing || localStorage.getItem("selectedPacing") || "short";
let isDiarizationEnabled = initialConfig.enable_diarization ?? (localStorage.getItem("isDiarizationEnabled") === "true");

if (selectedLanguage === "hi-en" && !["small", "medium", "large-v3"].includes(selectedModel)) {
  selectedModel = (selectedModel === "large-v3-turbo") ? "large-v3" : "medium";
}

// DOM Elements
const themeSelect = document.getElementById("themeSelect");
const themeModeToggleBtn = document.getElementById("themeModeToggleBtn");
const themeModeIcon = document.getElementById("themeModeIcon");
const themeModeText = document.getElementById("themeModeText");
const hwBadge = document.getElementById("hwBadge");
const deviceMetaPill = document.getElementById("deviceMetaPill");
const modelMetaPill = document.getElementById("modelMetaPill");

const languageRibbon = document.getElementById("languageRibbon");
const devicePills = document.getElementById("devicePills");
const pacingPills = document.getElementById("pacingPills");
const modelPills = document.getElementById("modelPills");
const modelStatusText = document.getElementById("modelStatusText");
const preDownloadModelBtn = document.getElementById("preDownloadModelBtn");
const launchModeSelect = document.getElementById("launchModeSelect");
let modelsStatusMap = {};

// Main Dynamic Pinned Controls & Switches
const mainDynamicControlsWrap = document.getElementById("mainDynamicControlsWrap");
const mainDynamicControlsCard = document.getElementById("mainDynamicControlsCard");
const mainColLeft = document.getElementById("mainColLeft");
const mainColRight = document.getElementById("mainColRight");
const mainHwGroup = document.getElementById("mainHwGroup");
const mainPacingGroup = document.getElementById("mainPacingGroup");
const mainModelGroup = document.getElementById("mainModelGroup");
const mainModelPills = document.getElementById("mainModelPills");
const mainDevicePills = document.getElementById("mainDevicePills");
const mainPacingPills = document.getElementById("mainPacingPills");
const mainModelStatusText = document.getElementById("mainModelStatusText");
const mainPreDownloadModelBtn = document.getElementById("mainPreDownloadModelBtn");

const pinModelSwitch = document.getElementById("pinModelSwitch");
const pinHwSwitch = document.getElementById("pinHwSwitch");
const pinPacingSwitch = document.getElementById("pinPacingSwitch");

let pinnedModules = {
  model: false,
  hw: false,
  pacing: false
};

const dropzone = document.getElementById("dropzone");
const videoFileInput = document.getElementById("videoFileInput");
const filePreview = document.getElementById("filePreview");
const fileNameLabel = document.getElementById("fileNameLabel");
const fileMetaLabel = document.getElementById("fileMetaLabel");
const removeFileBtn = document.getElementById("removeFileBtn");
const videoPlayer = document.getElementById("videoPlayer");
const videoStage = document.getElementById("videoStage");
const audioTrackBanner = document.getElementById("audioTrackBanner");
const captionToggleGroup = document.getElementById("captionToggleGroup");
const captionOverlay = document.getElementById("captionOverlay");
const captionText = document.getElementById("captionText");
let captionMode = "hinglish";

const generateBtn = document.getElementById("generateBtn");
const progressPanel = document.getElementById("progressPanel");
const progressStatusText = document.getElementById("progressStatusText");
const progressPctText = document.getElementById("progressPctText");
const progressBarFill = document.getElementById("progressBarFill");

const resultsSection = document.getElementById("resultsSection");
const subtitleSearchInput = document.getElementById("subtitleSearchInput");
const segmentCountLabel = document.getElementById("segmentCountLabel");
const speedMetaLabel = document.getElementById("speedMetaLabel");
const subtitleGrid = document.getElementById("subtitleGrid");
const toggleGridBtn = document.getElementById("toggleGridBtn");
const gridToggleIcon = document.getElementById("gridToggleIcon");
const gridToggleText = document.getElementById("gridToggleText");
const segmentsCollapsedCard = document.getElementById("segmentsCollapsedCard");
const collapsedCountText = document.getElementById("collapsedCountText");
const expandSegmentsBannerBtn = document.getElementById("expandSegmentsBannerBtn");
let isSegmentsCollapsed = false;

const openSettingsBtn = document.getElementById("openSettingsBtn");
const settingsDrawer = document.getElementById("settingsDrawer");
const settingsDrawerOverlay = document.getElementById("settingsDrawerOverlay");
const settingsDrawerCloseBtn = document.getElementById("settingsDrawerCloseBtn");
const saveAndCloseSettingsBtn = document.getElementById("saveAndCloseSettingsBtn");
const settingsHwBadge = document.getElementById("settingsHwBadge");

const drawerOverlay = document.getElementById("drawerOverlay");
const drawer = document.getElementById("drawer");
const drawerCloseBtn = document.getElementById("drawerCloseBtn");
const drawerIndexTitle = document.getElementById("drawerIndexTitle");
const drawerTimeRange = document.getElementById("drawerTimeRange");
const drawerOrigText = document.getElementById("drawerOrigText");
const drawerHinglishInput = document.getElementById("drawerHinglishInput");
const drawerSaveBtn = document.getElementById("drawerSaveBtn");
const drawerCopyBtn = document.getElementById("drawerCopyBtn");
const drawerPlayAudioBtn = document.getElementById("drawerPlayAudioBtn");

const floatingDownloadBar = document.getElementById("floatingDownloadBar");
const floatingMatchPill = document.getElementById("floatingMatchPill");
const floatingMatchCountText = document.getElementById("floatingMatchCountText");
const floatingCopyAllBtn = document.getElementById("floatingCopyAllBtn");
const floatingCopyAllText = document.getElementById("floatingCopyAllText");
const downloadHinglishBtn = document.getElementById("downloadHinglishBtn");
const downloadAssBtn = document.getElementById("downloadAssBtn");
const burnVideoBtn = document.getElementById("burnVideoBtn");
const downloadOrigBtn = document.getElementById("downloadOrigBtn");
const downloadTxtBtn = document.getElementById("downloadTxtBtn");

// Workbench Empty State Elements (Pattern B)
const workbenchEmptyState = document.getElementById("workbenchEmptyState");
const workbenchGrid = document.getElementById("workbenchGrid");
const workbenchRestoreBar = document.getElementById("workbenchRestoreBar");
const workbenchImporterCard = document.getElementById("workbenchImporterCard");
const workbenchRecentsCard = document.getElementById("workbenchRecentsCard");
const hideImporterBtn = document.getElementById("hideImporterBtn");
const hideRecentsBtn = document.getElementById("hideRecentsBtn");
const restoreImporterBtn = document.getElementById("restoreImporterBtn");
const restoreRecentsBtn = document.getElementById("restoreRecentsBtn");
const urlImportInput = document.getElementById("urlImportInput");
const urlFetchBtn = document.getElementById("urlFetchBtn");
const urlFetchText = document.getElementById("urlFetchText");
const urlImportStatus = document.getElementById("urlImportStatus");
const importerModeVideo = document.getElementById("importerModeVideo");
const importerModeAudio = document.getElementById("importerModeAudio");
const importerQualitySelect = document.getElementById("importerQualitySelect");
const recentsListContainer = document.getElementById("recentsListContainer");
const sampleTrafficBtn = document.getElementById("sampleTrafficBtn");
const sampleGeniusBtn = document.getElementById("sampleGeniusBtn");

function formatShortGpuName(rawName) {
  if (!rawName) return "CUDA fp16";
  const rtxMatch = rawName.match(/(RTX\s*\d{4}[A-Za-z]*|GTX\s*\d{4}[A-Za-z]*|T4|A100|H100)/i);
  if (rtxMatch) return `${rtxMatch[0]} (CUDA fp16)`;
  const cleaned = rawName.replace(/NVIDIA\s+/i, "").replace(/Laptop\s+GPU/i, "").replace(/,\s*\d+\s*MiB/i, "").trim();
  return `${cleaned.slice(0, 18)} (CUDA fp16)`;
}

function updateGenerateButtonState(enabled, message) {
  if (!generateBtn) return;
  generateBtn.disabled = !enabled;
  if (enabled) {
    generateBtn.classList.remove("is-standby");
  } else {
    generateBtn.classList.add("is-standby");
  }
  const actionStatusChip = document.getElementById("actionStatusChip");
  const actionStatusText = document.getElementById("actionStatusText");
  if (actionStatusChip && actionStatusText) {
    if (enabled) {
      actionStatusChip.classList.add("ready");
      actionStatusText.textContent = message || "File staged & ready for GPU transcription";
    } else {
      actionStatusChip.classList.remove("ready");
      actionStatusText.textContent = message || "Drop a video or audio file above to begin";
    }
  }
}

// --------------------------------------------------------------------------
// 1. Initialization & Hardware Fetch
// --------------------------------------------------------------------------
async function initApp() {
  // Theme check
  const savedTheme = localStorage.getItem("theme") || "industrial-hybrid";
  applyTheme(savedTheme, false);

  // Synchronize UI immediately with initial / saved preferences before network calls
  applyLanguageSelection(selectedLanguage, false);
  applyModelSelection(selectedModel, false);
  applyDeviceSelection(selectedDevice, false);
  applyPacingSelection(selectedPacing, false);

  try {
    const res = await fetch("/api/hardware");
    const data = await res.json();
    if (data.cuda_available) {
      hwBadge.textContent = `⚡ ${formatShortGpuName(data.device_name)}`;
      hwBadge.title = `${data.device_name} (CUDA Float16) - Click to open Settings`;
      hwBadge.className = "badge gpu";
      if (settingsHwBadge) settingsHwBadge.textContent = `${formatShortGpuName(data.device_name)} ACTIVE`;
      if (deviceMetaPill) deviceMetaPill.textContent = `⚡ Hardware: ${formatShortGpuName(data.device_name)}`;
    } else {
      hwBadge.textContent = "💻 CPU (INT8)";
      hwBadge.title = "Standard CPU Mode (Int8) - Click to open Settings";
      hwBadge.className = "badge";
      if (settingsHwBadge) settingsHwBadge.textContent = "CPU MODE";
      if (deviceMetaPill) deviceMetaPill.textContent = "⚡ Hardware: Standard CPU (Int8)";
    }
  } catch (err) {
    hwBadge.textContent = "STANDBY";
    if (settingsHwBadge) settingsHwBadge.textContent = "STANDBY";
  }

  updateGenerateButtonState(false);
  initWorkbenchEmptyState();
  initPinSwitches();

  await fetchModelStatuses();
  await fetchLaunchConfig();
}


async function fetchModelStatuses() {
  try {
    const res = await fetch("/api/models");
    if (res.ok) {
      modelsStatusMap = await res.json();
      updateModelStatusUI();
    }
  } catch (err) {
    console.error("Could not fetch model statuses:", err);
  }
}

function updateModelStatusUI() {
  const modelInfo = modelsStatusMap[selectedModel];
  if (!modelInfo) return;

  // Update pills with checkmark if cached (both drawer and main window)
  [modelPills, mainModelPills].forEach(container => {
    if (!container) return;
    container.querySelectorAll(".pill").forEach(p => {
      const m = p.dataset.model;
      const info = modelsStatusMap[m];
      if (info && info.cached) {
        if (!p.textContent.includes("✓")) {
          p.textContent = p.textContent.replace(" ✓", "") + " ✓";
        }
      }
    });
  });

  if (selectedLanguage === "hi-en" && selectedModel === "large-v3-turbo") {
    const turboNotice = `<span style="color: var(--yellow); font-weight: 800;">⚡ AUTO-ROUTED TO LARGE-V3</span>: Large-v3-Turbo is distilled for transcription only. The translation pipeline automatically uses full <b>Large-V3 (Studio)</b> for English translation.`;
    if (modelStatusText) modelStatusText.innerHTML = turboNotice;
    if (mainModelStatusText) mainModelStatusText.innerHTML = turboNotice;
    if (preDownloadModelBtn) preDownloadModelBtn.style.display = "none";
    if (mainPreDownloadModelBtn) mainPreDownloadModelBtn.style.display = "none";
    return;
  }

  const cachedHtml = `<span style="color: var(--green); font-weight: 800;">✓ CACHED ON DISK</span>: <b>${selectedModel.toUpperCase()}</b> (${modelInfo.size}) is downloaded and ready for immediate offline inference.`;
  const notCachedHtml = `<span style="color: var(--yellow); font-weight: 800;">📥 NOT DOWNLOADED YET</span>: <b>${selectedModel.toUpperCase()}</b> (${modelInfo.size}) will auto-download on first use.`;
  const btnLabel = `⚡ PRE-DOWNLOAD ${selectedModel.toUpperCase()} (${modelInfo.size})`;

  if (modelInfo.cached) {
    if (modelStatusText) modelStatusText.innerHTML = cachedHtml;
    if (mainModelStatusText) mainModelStatusText.innerHTML = cachedHtml;
    if (preDownloadModelBtn) preDownloadModelBtn.style.display = "none";
    if (mainPreDownloadModelBtn) mainPreDownloadModelBtn.style.display = "none";
  } else {
    if (modelStatusText) modelStatusText.innerHTML = notCachedHtml;
    if (mainModelStatusText) mainModelStatusText.innerHTML = notCachedHtml;
    if (preDownloadModelBtn) {
      preDownloadModelBtn.style.display = "inline-flex";
      preDownloadModelBtn.textContent = btnLabel;
      preDownloadModelBtn.disabled = false;
    }
    if (mainPreDownloadModelBtn) {
      mainPreDownloadModelBtn.style.display = "inline-flex";
      mainPreDownloadModelBtn.textContent = btnLabel;
      mainPreDownloadModelBtn.disabled = false;
    }
  }
}

// Speaker Diarization Switch
const diarizeOffBtn = document.getElementById("diarizeOffBtn");
const diarizeOnBtn = document.getElementById("diarizeOnBtn");

function updateDiarizationUI() {
  if (diarizeOffBtn && diarizeOnBtn) {
    if (isDiarizationEnabled) {
      diarizeOffBtn.classList.remove("active");
      diarizeOnBtn.classList.add("active");
    } else {
      diarizeOffBtn.classList.add("active");
      diarizeOnBtn.classList.remove("active");
    }
  }
}

if (diarizeOffBtn) {
  diarizeOffBtn.addEventListener("click", () => {
    isDiarizationEnabled = false;
    localStorage.setItem("isDiarizationEnabled", "false");
    updateDiarizationUI();
  });
}
if (diarizeOnBtn) {
  diarizeOnBtn.addEventListener("click", () => {
    isDiarizationEnabled = true;
    localStorage.setItem("isDiarizationEnabled", "true");
    updateDiarizationUI();
  });
}
updateDiarizationUI();

// Pre-download Model Handler
if (preDownloadModelBtn) {
  preDownloadModelBtn.addEventListener("click", async () => {
    preDownloadModelBtn.disabled = true;
    preDownloadModelBtn.textContent = `⏳ DOWNLOADING ${selectedModel.toUpperCase()}... PLEASE WAIT`;
    if (mainPreDownloadModelBtn) {
      mainPreDownloadModelBtn.disabled = true;
      mainPreDownloadModelBtn.textContent = `⏳ DOWNLOADING ${selectedModel.toUpperCase()}... PLEASE WAIT`;
    }
    const downloadingHtml = `<span style="color: var(--yellow); font-weight: 800;">⏳ DOWNLOADING FROM HUGGINGFACE</span>: Fetching <b>${selectedModel.toUpperCase()}</b> weights... This only happens once.`;
    if (modelStatusText) modelStatusText.innerHTML = downloadingHtml;
    if (mainModelStatusText) mainModelStatusText.innerHTML = downloadingHtml;

    const formData = new FormData();
    formData.append("model_size", selectedModel);

    try {
      const res = await fetch("/api/download_model", {
        method: "POST",
        body: formData
      });
      if (!res.ok) throw new Error("Download failed");

      if (modelsStatusMap[selectedModel]) {
        modelsStatusMap[selectedModel].cached = true;
      }
      updateModelStatusUI();
      alert(`Model [${selectedModel.toUpperCase()}] successfully downloaded and cached!`);
    } catch (err) {
      alert(`Error downloading model: ${err.message}`);
      preDownloadModelBtn.disabled = false;
      preDownloadModelBtn.textContent = `RETRY DOWNLOAD`;
      if (mainPreDownloadModelBtn) {
        mainPreDownloadModelBtn.disabled = false;
        mainPreDownloadModelBtn.textContent = `RETRY DOWNLOAD`;
      }
    }
  });
}

if (mainPreDownloadModelBtn) {
  mainPreDownloadModelBtn.addEventListener("click", () => {
    if (preDownloadModelBtn) preDownloadModelBtn.click();
  });
}

document.addEventListener("DOMContentLoaded", initApp);

const SUN_SVG = `<svg class="sun-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;

const MOON_SVG = `<svg class="moon-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;

function updateThemeModeUI(theme) {
  const isLight = (theme === "minimalist-light");
  if (themeModeIcon) {
    themeModeIcon.innerHTML = isLight ? SUN_SVG : MOON_SVG;
  }
  if (themeModeText) {
    themeModeText.textContent = isLight ? "LIGHT" : "DARK";
  }
  if (themeModeToggleBtn) {
    const title = isLight ? "Switch to Dark Mode" : "Switch to Light Mode";
    themeModeToggleBtn.title = title;
    themeModeToggleBtn.setAttribute("aria-label", title);
  }
}

function applyTheme(newTheme, persist = true) {
  document.documentElement.dataset.theme = newTheme;
  if (persist) {
    localStorage.setItem("theme", newTheme);
  }
  if (newTheme === "minimalist-light") {
    updateThemeModeUI("minimalist-light");
    const preferredDark = localStorage.getItem("preferredDarkTheme") || "industrial-hybrid";
    if (themeSelect) themeSelect.value = preferredDark;
  } else {
    localStorage.setItem("preferredDarkTheme", newTheme);
    if (themeSelect) themeSelect.value = newTheme;
    updateThemeModeUI(newTheme);
  }
}

if (themeSelect) {
  themeSelect.addEventListener("change", (e) => {
    applyTheme(e.target.value, true);
  });
}

if (themeModeToggleBtn) {
  themeModeToggleBtn.addEventListener("click", () => {
    const currentTheme = document.documentElement.dataset.theme || "industrial-hybrid";
    if (currentTheme === "minimalist-light") {
      const preferredDark = localStorage.getItem("preferredDarkTheme") || "industrial-hybrid";
      applyTheme(preferredDark, true);
    } else {
      localStorage.setItem("preferredDarkTheme", currentTheme);
      applyTheme("minimalist-light", true);
    }
  });
}

// --------------------------------------------------------------------------
// Launch Mode Configuration (Silent / No Terminal Window vs Console Window)
// --------------------------------------------------------------------------
async function fetchLaunchConfig() {
  try {
    const res = await fetch("/api/config/launch_mode");
    if (res.ok) {
      const data = await res.json();
      updateLaunchModeUI(Boolean(data.silent_launch));
    }
  } catch (err) {
    console.warn("Could not fetch launch mode config:", err);
  }
}

function updateLaunchModeUI(isSilent) {
  if (launchModeSelect) {
    launchModeSelect.value = isSilent ? "silent" : "console";
  }
}

async function saveLaunchMode(isSilent) {
  updateLaunchModeUI(isSilent);
  try {
    const formData = new FormData();
    formData.append("silent_launch", isSilent);
    await fetch("/api/config/launch_mode", {
      method: "POST",
      body: formData
    });
  } catch (err) {
    console.error("Failed to save launch mode config:", err);
  }
}

if (launchModeSelect) {
  launchModeSelect.addEventListener("change", (e) => {
    saveLaunchMode(e.target.value === "silent");
  });
}

// --------------------------------------------------------------------------
// 2. Control Selectors & Persistence (Pills & Ribbon)
// --------------------------------------------------------------------------
function applyModelSelection(model, persist = true) {
  if (!model) return;
  selectedModel = model;
  if (persist) {
    try { localStorage.setItem("selectedModel", model); } catch (_) {}
    saveBackendPreference("selected_model", model);
  }
  [modelPills, mainModelPills].forEach(container => {
    if (!container) return;
    const targetPill = container.querySelector(`[data-model="${model}"]`);
    if (targetPill) {
      container.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
      targetPill.classList.add("active");
      if (container === modelPills) {
        const cleanName = targetPill.textContent.replace("✓", "").trim();
        if (modelMetaPill) modelMetaPill.textContent = `🤖 ${cleanName}`;
      }
    }
  });
  const hintHelper = document.getElementById("hintHelperText");
  const isAcousticOnly = ["indic-conformer", "sravaani-1.0", "sensevoice-small"].includes(model);
  if (hintHelper) {
    if (isAcousticOnly) {
      hintHelper.innerHTML = `<span style="color: var(--yellow); font-weight: bold;">⚠️ NOTE:</span> Caption and brand hints are not supported by acoustic engines (<strong>${model}</strong>). Hints will be ignored during transcription.`;
    } else {
      hintHelper.innerHTML = `Feeds into Whisper hotwords & brand snapping so brand names and niche jargon are never misheard.`;
    }
  }
  updateModelStatusUI();
}

function updateDownloadButtonsLabels() {
  const isEnglish = (selectedLanguage === "hi-en" || selectedLanguage === "en");
  if (downloadHinglishBtn) {
    downloadHinglishBtn.textContent = isEnglish ? "📥 DOWNLOAD ENGLISH SRT" : "📥 DOWNLOAD HINGLISH SRT";
  }
  if (floatingCopyAllBtn) {
    floatingCopyAllBtn.title = isEnglish ? "Copy all English subtitles to clipboard" : "Copy all Hinglish subtitles to clipboard";
  }
  if (captionToggleGroup) {
    const hinglishPill = captionToggleGroup.querySelector('.btn-caption-pill[data-mode="hinglish"]');
    if (hinglishPill) {
      hinglishPill.textContent = isEnglish ? "ENGLISH" : "HINGLISH";
    }
  }
  if (generateBtn) {
    const svgIcon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`;
    const btnLabel = selectedLanguage === "hi-en" ? "TRANSLATE TO ENGLISH" : (selectedLanguage === "en" ? "GENERATE ENGLISH SUBTITLES" : "GENERATE HINGLISH SUBTITLES");
    generateBtn.innerHTML = `${svgIcon} ${btnLabel}`;
  }
}

const ENGLISH_TRANSLATION_MODELS = ["small", "medium", "large-v3"];
const ENGLISH_ASR_MODELS = ["small", "medium", "large-v3-turbo", "large-v3", "sensevoice-small"];

function updateModelVisibilityForLanguage() {
  const isHiEn = (selectedLanguage === "hi-en");
  const isEn = (selectedLanguage === "en");

  [modelPills, mainModelPills].forEach(container => {
    if (!container) return;
    container.querySelectorAll(".pill").forEach(p => {
      const m = p.dataset.model;
      let shouldHide = false;
      if (isHiEn) {
        shouldHide = !ENGLISH_TRANSLATION_MODELS.includes(m);
      } else if (isEn) {
        shouldHide = !ENGLISH_ASR_MODELS.includes(m);
      }
      p.style.display = shouldHide ? "none" : "";
    });
  });

  const descElements = document.querySelectorAll(".settings-card-desc");
  if (descElements && descElements.length > 0) {
    if (isHiEn) {
      descElements[0].textContent = "Showing models with native translation support (Small, Medium, Large-V3). Incompatible models are hidden.";
    } else {
      descElements[0].textContent = "Select Whisper model weights. Turbo and Medium are recommended for RTX 4050.";
    }
  }

  // If the currently selected model is hidden in this language mode, auto-switch to a supported model
  if (isHiEn && !ENGLISH_TRANSLATION_MODELS.includes(selectedModel)) {
    const fallback = (selectedModel === "large-v3-turbo") ? "large-v3" : "medium";
    applyModelSelection(fallback, true);
  } else if (isEn && !ENGLISH_ASR_MODELS.includes(selectedModel)) {
    applyModelSelection("medium", true);
  }
}

function applyLanguageSelection(lang, persist = true) {
  if (!lang) return;
  selectedLanguage = lang;
  if (persist) {
    try { localStorage.setItem("selectedLanguage", lang); } catch (_) {}
    saveBackendPreference("selected_language", lang);
  }
  if (languageRibbon) {
    const targetTile = languageRibbon.querySelector(`[data-lang="${lang}"]`);
    if (targetTile) {
      languageRibbon.querySelectorAll(".tile").forEach(t => t.classList.remove("active"));
      targetTile.classList.add("active");
    }
  }
  updateModelVisibilityForLanguage();
  updateDownloadButtonsLabels();
  updateModelStatusUI();
}

function applyDeviceSelection(dev, persist = true) {
  if (!dev) return;
  selectedDevice = dev;
  if (persist) {
    try { localStorage.setItem("selectedDevice", dev); } catch (_) {}
    saveBackendPreference("selected_device", dev);
  }
  [devicePills, mainDevicePills].forEach(container => {
    if (!container) return;
    const targetPill = container.querySelector(`[data-device="${dev}"]`);
    if (targetPill) {
      container.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
      targetPill.classList.add("active");
    }
  });
}

function applyPacingSelection(pacing, persist = true) {
  if (!pacing) return;
  selectedPacing = pacing;
  if (persist) {
    try { localStorage.setItem("selectedPacing", pacing); } catch (_) {}
    saveBackendPreference("selected_pacing", pacing);
  }
  [pacingPills, mainPacingPills].forEach(container => {
    if (!container) return;
    const targetPill = container.querySelector(`[data-pacing="${pacing}"]`);
    if (targetPill) {
      container.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
      targetPill.classList.add("active");
    }
  });
}

async function saveBackendPreference(key, value) {
  if (key === "selected_language") selectedLanguage = value;
  if (key === "selected_model") selectedModel = value;
  if (key === "selected_device") selectedDevice = value;
  if (key === "selected_pacing") selectedPacing = value;

  try {
    const fd = new FormData();
    fd.append("selected_language", selectedLanguage);
    fd.append("selected_model", selectedModel);
    fd.append("selected_device", selectedDevice);
    fd.append("selected_pacing", selectedPacing);
    await fetch("/api/config/preferences", { method: "POST", body: fd });
  } catch (err) {
    console.warn("Could not save preference to backend:", err);
  }
}

// Dynamic Pinned Controls (Settings Drawer -> Main Window)
function loadPinnedControls() {
  try {
    const saved = localStorage.getItem("pinned_controls");
    if (saved) {
      const parsed = JSON.parse(saved);
      pinnedModules = { ...pinnedModules, ...parsed };
    }
  } catch (err) {
    console.warn("Could not load pinned controls state:", err);
  }
}

function savePinnedControls() {
  try {
    localStorage.setItem("pinned_controls", JSON.stringify(pinnedModules));
  } catch (err) {
    console.warn("Could not save pinned controls state:", err);
  }
}

function updateDynamicControlsLayout() {
  if (!mainDynamicControlsWrap || !mainDynamicControlsCard) return;

  // Topic Hints is permanently on the main window (Left Column)
  mainDynamicControlsWrap.style.display = "block";
  if (mainColLeft) mainColLeft.style.display = "flex";

  const hasHw = !!pinnedModules.hw;
  const hasPacing = !!pinnedModules.pacing;
  const hasModel = !!pinnedModules.model;

  // Update Switches UI in Settings Drawer
  if (pinModelSwitch) {
    pinModelSwitch.classList.toggle("on", hasModel);
    const txt = pinModelSwitch.querySelector(".pin-text");
    if (txt) txt.textContent = hasModel ? "PINNED" : "PIN TO MAIN";
  }
  if (pinHwSwitch) {
    pinHwSwitch.classList.toggle("on", hasHw);
    const txt = pinHwSwitch.querySelector(".pin-text");
    if (txt) txt.textContent = hasHw ? "PINNED" : "PIN TO MAIN";
  }
  if (pinPacingSwitch) {
    pinPacingSwitch.classList.toggle("on", hasPacing);
    const txt = pinPacingSwitch.querySelector(".pin-text");
    if (txt) txt.textContent = hasPacing ? "PINNED" : "PIN TO MAIN";
  }

  // Left Column elements
  if (mainHwGroup) {
    mainHwGroup.style.display = hasHw ? "flex" : "none";
  }
  if (mainPacingGroup) {
    mainPacingGroup.style.display = hasPacing ? "flex" : "none";
    mainPacingGroup.style.marginTop = (!hasHw && hasPacing) ? "0px" : "18px";
  }

  const mainTopicHintGroup = document.getElementById("mainTopicHintGroup");
  if (mainTopicHintGroup) {
    if (hasHw || hasPacing) {
      mainTopicHintGroup.style.marginTop = "auto";
      mainTopicHintGroup.style.paddingTop = "14px";
    } else {
      mainTopicHintGroup.style.marginTop = "0px";
      mainTopicHintGroup.style.paddingTop = "0px";
    }
  }

  // Right Column (ASR Model Switcher)
  if (mainColRight) {
    mainColRight.style.display = hasModel ? "flex" : "none";
  }
  if (mainModelGroup) {
    mainModelGroup.style.display = hasModel ? "flex" : "none";
  }

  // Dynamic Grid: 2 columns if Model Switcher is pinned, 1 column if unpinned
  if (hasModel) {
    mainDynamicControlsCard.className = "controls-card cols-2";
  } else {
    mainDynamicControlsCard.className = "controls-card cols-1";
  }
}

function initPinSwitches() {
  loadPinnedControls();
  updateDynamicControlsLayout();

  if (pinModelSwitch) {
    pinModelSwitch.addEventListener("click", () => {
      pinnedModules.model = !pinnedModules.model;
      savePinnedControls();
      updateDynamicControlsLayout();
    });
  }
  if (pinHwSwitch) {
    pinHwSwitch.addEventListener("click", () => {
      pinnedModules.hw = !pinnedModules.hw;
      savePinnedControls();
      updateDynamicControlsLayout();
    });
  }
  if (pinPacingSwitch) {
    pinPacingSwitch.addEventListener("click", () => {
      pinnedModules.pacing = !pinnedModules.pacing;
      savePinnedControls();
      updateDynamicControlsLayout();
    });
  }
}

// Drawer Pill Event Listeners
languageRibbon.addEventListener("click", (e) => {
  const tile = e.target.closest(".tile");
  if (!tile) return;
  applyLanguageSelection(tile.dataset.lang, true);
});

devicePills.addEventListener("click", (e) => {
  const pill = e.target.closest(".pill");
  if (!pill) return;
  applyDeviceSelection(pill.dataset.device, true);
});

if (pacingPills) {
  pacingPills.addEventListener("click", (e) => {
    const pill = e.target.closest(".pill");
    if (!pill) return;
    applyPacingSelection(pill.dataset.pacing || "short", true);
  });
}

modelPills.addEventListener("click", (e) => {
  const pill = e.target.closest(".pill");
  if (!pill) return;
  applyModelSelection(pill.dataset.model, true);
});

// Main Window Pinned Pill Event Listeners
if (mainDevicePills) {
  mainDevicePills.addEventListener("click", (e) => {
    const pill = e.target.closest(".pill");
    if (!pill) return;
    applyDeviceSelection(pill.dataset.device, true);
  });
}

if (mainPacingPills) {
  mainPacingPills.addEventListener("click", (e) => {
    const pill = e.target.closest(".pill");
    if (!pill) return;
    applyPacingSelection(pill.dataset.pacing || "short", true);
  });
}

if (mainModelPills) {
  mainModelPills.addEventListener("click", (e) => {
    const pill = e.target.closest(".pill");
    if (!pill) return;
    applyModelSelection(pill.dataset.model, true);
  });
}


// --------------------------------------------------------------------------
// 3. Drag and Drop Video Handling
// --------------------------------------------------------------------------
["dragenter", "dragover"].forEach(event => {
  dropzone.addEventListener(event, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach(event => {
  dropzone.addEventListener(event, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove("dragover");
  });
});

dropzone.addEventListener("drop", (e) => {
  const files = e.dataTransfer.files;
  if (files && files.length > 0) {
    handleSelectedFile(files[0]);
  }
});

videoFileInput.addEventListener("change", (e) => {
  if (e.target.files && e.target.files.length > 0) {
    handleSelectedFile(e.target.files[0]);
  }
});

function updateVideoOrientation() {
  const ext = currentFile ? currentFile.name.split('.').pop().toLowerCase() : "";
  const isAudio = (currentFile && currentFile.type.startsWith("audio/")) ||
                  ["mp3", "wav", "m4a", "aac", "flac", "ogg", "opus", "wma"].includes(ext);

  const w = videoPlayer.videoWidth;
  const h = videoPlayer.videoHeight;

  if (isAudio || !w || !h) {
    videoPlayer.classList.remove("video-portrait", "video-landscape", "video-square");
    videoPlayer.classList.add("media-audio");
    videoPlayer.style.aspectRatio = "";
    if (videoStage) videoStage.classList.add("is-audio");
    if (audioTrackBanner) audioTrackBanner.style.display = "flex";

    if (currentFile) {
      const sizeMB = (currentFile.size / (1024 * 1024)).toFixed(2);
      const dur = (videoPlayer.duration && !isNaN(videoPlayer.duration))
        ? ` • ${Math.round(videoPlayer.duration)}s`
        : "";
      fileMetaLabel.textContent = `${sizeMB} MB • Audio Track (${ext.toUpperCase() || "AUDIO"})${dur}`;
    }
    return;
  }

  // Video track detected
  if (audioTrackBanner) audioTrackBanner.style.display = "none";
  if (videoStage) videoStage.classList.remove("is-audio");
  videoPlayer.classList.remove("media-audio");

  videoPlayer.style.aspectRatio = `${w} / ${h}`;
  videoPlayer.classList.remove("video-portrait", "video-landscape", "video-square");

  if (h > w) {
    videoPlayer.classList.add("video-portrait");
  } else if (w === h) {
    videoPlayer.classList.add("video-square");
  } else {
    videoPlayer.classList.add("video-landscape");
  }

  // Format label update
  let formatName = "Landscape";
  const ratio = w / h;
  if (h > w) {
    if (ratio >= 0.54 && ratio <= 0.60) {
      formatName = "Vertical Reel (9:16)";
    } else if (ratio >= 0.75 && ratio <= 0.85) {
      formatName = "Portrait (4:5)";
    } else {
      formatName = `Vertical (${w}×${h})`;
    }
  } else if (w === h) {
    formatName = "Square (1:1)";
  } else {
    if (ratio >= 1.70 && ratio <= 1.82) {
      formatName = "Widescreen (16:9)";
    } else {
      formatName = `Landscape (${w}×${h})`;
    }
  }

  if (currentFile) {
    const sizeMB = (currentFile.size / (1024 * 1024)).toFixed(2);
    fileMetaLabel.textContent = `${sizeMB} MB • ${w}×${h} • ${formatName}`;
  }
}

videoPlayer.addEventListener("loadedmetadata", updateVideoOrientation);

function handleSelectedFile(file) {
  currentFile = file;
  fileNameLabel.textContent = file.name;

  const ext = file.name.split('.').pop().toLowerCase();
  const isAudio = file.type.startsWith("audio/") ||
                  ["mp3", "wav", "m4a", "aac", "flac", "ogg", "opus", "wma"].includes(ext);

  const typeDesc = isAudio ? `Audio Track (${ext.toUpperCase()})` : (file.type || "Video");
  fileMetaLabel.textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB • ${typeDesc}`;

  // Show file preview
  filePreview.style.display = "block";
  dropzone.style.display = "none";
  if (workbenchEmptyState) workbenchEmptyState.style.display = "none";
  updateGenerateButtonState(true, `${file.name} staged & verified`);

  // Reset classes and previous aspect ratio
  videoPlayer.className = "";
  videoPlayer.style.aspectRatio = "";

  if (isAudio) {
    videoPlayer.classList.add("media-audio");
    if (videoStage) videoStage.classList.add("is-audio");
    if (audioTrackBanner) audioTrackBanner.style.display = "flex";
    setTimeout(() => { if (typeof renderAudioVisualizer === "function") renderAudioVisualizer(); }, 60);
  } else {
    if (videoStage) videoStage.classList.remove("is-audio");
    if (audioTrackBanner) audioTrackBanner.style.display = "none";
  }

  // Local object URL for HTML5 player
  const videoUrl = URL.createObjectURL(file);
  videoPlayer.src = videoUrl;
  videoPlayer.style.display = "block";

  if (videoPlayer.readyState >= 1) {
    updateVideoOrientation();
  }
}

// --------------------------------------------------------------------------
// On-Video Subtitle Sync Engine (Option 1: Social Media Reel Overlay)
// --------------------------------------------------------------------------
function updateVideoCaption() {
  if (!captionOverlay || !captionText) return;

  if (captionMode === "off" || !currentSegments || currentSegments.length === 0) {
    captionOverlay.classList.remove("visible");
    return;
  }

  const curTime = videoPlayer.currentTime;
  const activeSeg = currentSegments.find(s => curTime >= s.start && curTime <= s.end);

  if (activeSeg) {
    const text = captionMode === "original" ? (activeSeg.original_text || "") : (activeSeg.hinglish_text || "");
    if (text.trim()) {
      captionText.textContent = text.trim();
      captionOverlay.classList.add("visible");
    } else {
      captionOverlay.classList.remove("visible");
    }
  } else {
    captionOverlay.classList.remove("visible");
  }
}

videoPlayer.addEventListener("timeupdate", updateVideoCaption);
videoPlayer.addEventListener("seeked", updateVideoCaption);

if (captionToggleGroup) {
  captionToggleGroup.querySelectorAll(".btn-caption-pill").forEach(btn => {
    btn.addEventListener("click", () => {
      captionToggleGroup.querySelectorAll(".btn-caption-pill").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      captionMode = btn.dataset.mode || "hinglish";
      updateVideoCaption();
    });
  });
}

removeFileBtn.addEventListener("click", () => {
  currentFile = null;
  videoFileInput.value = "";
  filePreview.style.display = "none";
  dropzone.style.display = "block";
  if (workbenchEmptyState) {
    workbenchEmptyState.style.display = "block";
    if (typeof renderRecentTranscriptions === "function") renderRecentTranscriptions();
  }
  updateGenerateButtonState(false, "Drop a video or audio file above to begin");
  videoPlayer.pause();
  videoPlayer.removeAttribute("src");
  videoPlayer.load();
  videoPlayer.style.display = "none";
  videoPlayer.className = "";
  videoPlayer.style.aspectRatio = "";
  if (videoStage) {
    videoStage.classList.remove("is-audio");
  }
  if (audioTrackBanner) {
    audioTrackBanner.style.display = "none";
  }
  fileMetaLabel.textContent = "0.00 MB";
  if (captionToggleGroup) {
    captionToggleGroup.style.display = "none";
  }
  if (captionOverlay) {
    captionOverlay.classList.remove("visible");
  }
  if (captionText) {
    captionText.textContent = "";
  }
  if (playerCurrentTime) playerCurrentTime.textContent = "00:00";
  if (playerDuration) playerDuration.textContent = "00:00";
  if (playerScrubber) {
    playerScrubber.value = 0;
    updateScrubberTrack(0);
  }
  updatePlayPauseBtnState();
  if (typeof renderAudioVisualizer === "function") renderAudioVisualizer();
});

// --------------------------------------------------------------------------
// Custom Neo-Brutalist Media Player Controls & Web Audio Visualizer
// --------------------------------------------------------------------------
const customMediaControls = document.getElementById("customMediaControls");
const playerPlayBtn = document.getElementById("playerPlayBtn");
const playerCurrentTime = document.getElementById("playerCurrentTime");
const playerDuration = document.getElementById("playerDuration");
const playerScrubber = document.getElementById("playerScrubber");
const playerVolumeBtn = document.getElementById("playerVolumeBtn");
const playerVolumeSlider = document.getElementById("playerVolumeSlider");
const playerFullscreenBtn = document.getElementById("playerFullscreenBtn");
const audioVisualizerCanvas = document.getElementById("audioVisualizerCanvas");

function formatPlayerTime(seconds) {
  if (isNaN(seconds) || seconds === Infinity || seconds < 0) return "00:00";
  const totalSecs = Math.floor(seconds);
  const hrs = Math.floor(totalSecs / 3600);
  const mins = Math.floor((totalSecs % 3600) / 60);
  const secs = totalSecs % 60;
  const pad = n => String(n).padStart(2, "0");
  if (hrs > 0) {
    return `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
  }
  return `${pad(mins)}:${pad(secs)}`;
}

let isScrubbing = false;

function updateScrubberTrack(val) {
  if (!playerScrubber) return;
  const pct = Math.max(0, Math.min(100, Number(val) || 0));
  playerScrubber.style.background = `linear-gradient(to right, var(--yellow) 0%, var(--yellow) ${pct}%, #191c24 ${pct}%, #191c24 100%)`;
}

function updatePlayPauseBtnState() {
  if (!playerPlayBtn) return;
  const playIcon = playerPlayBtn.querySelector(".icon-play");
  const pauseIcon = playerPlayBtn.querySelector(".icon-pause");
  if (!videoPlayer.paused && !videoPlayer.ended) {
    if (playIcon) playIcon.style.display = "none";
    if (pauseIcon) pauseIcon.style.display = "block";
  } else {
    if (playIcon) playIcon.style.display = "block";
    if (pauseIcon) pauseIcon.style.display = "none";
  }
}

if (playerPlayBtn) {
  playerPlayBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!videoPlayer.src) return;
    if (videoPlayer.paused) {
      videoPlayer.play();
    } else {
      videoPlayer.pause();
    }
  });
}

videoPlayer.addEventListener("play", () => {
  updatePlayPauseBtnState();
  startVisualizerAnimation();
});

videoPlayer.addEventListener("pause", () => {
  updatePlayPauseBtnState();
});

videoPlayer.addEventListener("ended", () => {
  updatePlayPauseBtnState();
});

videoPlayer.addEventListener("loadedmetadata", () => {
  if (playerDuration) {
    playerDuration.textContent = formatPlayerTime(videoPlayer.duration);
  }
  if (playerCurrentTime) {
    playerCurrentTime.textContent = formatPlayerTime(videoPlayer.currentTime);
  }
  if (playerScrubber) {
    playerScrubber.value = 0;
    updateScrubberTrack(0);
  }
});

videoPlayer.addEventListener("timeupdate", () => {
  if (!isScrubbing && playerCurrentTime) {
    playerCurrentTime.textContent = formatPlayerTime(videoPlayer.currentTime);
    if (videoPlayer.duration && videoPlayer.duration > 0) {
      const pct = (videoPlayer.currentTime / videoPlayer.duration) * 100;
      if (playerScrubber) {
        playerScrubber.value = pct;
        updateScrubberTrack(pct);
      }
    }
  }
});

if (playerScrubber) {
  playerScrubber.addEventListener("input", (e) => {
    isScrubbing = true;
    const pct = parseFloat(e.target.value);
    updateScrubberTrack(pct);
    if (videoPlayer.duration && playerCurrentTime) {
      playerCurrentTime.textContent = formatPlayerTime((pct / 100) * videoPlayer.duration);
    }
  });

  playerScrubber.addEventListener("change", (e) => {
    const pct = parseFloat(e.target.value);
    if (videoPlayer.duration) {
      videoPlayer.currentTime = (pct / 100) * videoPlayer.duration;
    }
    isScrubbing = false;
  });
}

function updateVolumeUI() {
  if (!playerVolumeBtn || !playerVolumeSlider) return;
  const isMuted = videoPlayer.muted || videoPlayer.volume === 0;
  const iconVol = playerVolumeBtn.querySelector(".icon-volume");
  const iconMuted = playerVolumeBtn.querySelector(".icon-muted");
  if (iconVol) iconVol.style.display = isMuted ? "none" : "block";
  if (iconMuted) iconMuted.style.display = isMuted ? "block" : "none";
  playerVolumeSlider.value = isMuted ? 0 : videoPlayer.volume;
}

if (playerVolumeBtn) {
  playerVolumeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    videoPlayer.muted = !videoPlayer.muted;
    updateVolumeUI();
  });
}

if (playerVolumeSlider) {
  playerVolumeSlider.addEventListener("input", (e) => {
    const vol = parseFloat(e.target.value);
    videoPlayer.volume = vol;
    videoPlayer.muted = (vol === 0);
    updateVolumeUI();
  });
}

videoPlayer.addEventListener("volumechange", updateVolumeUI);

if (playerFullscreenBtn && videoStage) {
  playerFullscreenBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!document.fullscreenElement) {
      if (videoStage.requestFullscreen) {
        videoStage.requestFullscreen();
      } else if (videoStage.webkitRequestFullscreen) {
        videoStage.webkitRequestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      }
    }
  });

  document.addEventListener("fullscreenchange", () => {
    const enterIcon = playerFullscreenBtn.querySelector(".icon-fs-enter");
    const exitIcon = playerFullscreenBtn.querySelector(".icon-fs-exit");
    const isFs = (document.fullscreenElement === videoStage);
    if (enterIcon) enterIcon.style.display = isFs ? "none" : "block";
    if (exitIcon) exitIcon.style.display = isFs ? "block" : "none";
  });
}

if (videoStage) {
  videoStage.addEventListener("click", (e) => {
    if (e.target.closest(".custom-media-controls") || e.target.closest(".video-caption-overlay")) {
      return;
    }
    if (!videoPlayer.src) return;
    if (videoPlayer.paused) {
      videoPlayer.play();
    } else {
      videoPlayer.pause();
    }
  });
}

// --------------------------------------------------------------------------
// Real-Time Stepped Digital Sound Wave Equalizer (Web Audio API + Procedural Fallback)
// --------------------------------------------------------------------------
let audioCtx = null;
let audioAnalyser = null;
let audioSourceNode = null;
let visualizerAnimId = null;

function initAudioAnalyser() {
  if (audioCtx) return;
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    audioCtx = new AudioContextClass();
    audioAnalyser = audioCtx.createAnalyser();
    audioAnalyser.fftSize = 128;
    audioAnalyser.smoothingTimeConstant = 0.8;
    audioSourceNode = audioCtx.createMediaElementSource(videoPlayer);
    audioSourceNode.connect(audioAnalyser);
    audioAnalyser.connect(audioCtx.destination);
  } catch (err) {
    console.warn("Web Audio API binding note (using adaptive waveform):", err);
  }
}

function startVisualizerAnimation() {
  if (!audioVisualizerCanvas) return;
  if (!audioCtx) {
    initAudioAnalyser();
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  if (!visualizerAnimId) {
    renderAudioVisualizer();
  }
}

function renderAudioVisualizer() {
  if (!audioVisualizerCanvas) return;
  const ctx = audioVisualizerCanvas.getContext("2d");
  if (!ctx) return;

  const w = audioVisualizerCanvas.width;
  const h = audioVisualizerCanvas.height;
  ctx.clearRect(0, 0, w, h);

  const numCols = 32;
  const colWidth = 11;
  const colGap = 5;
  const totalWidth = numCols * colWidth + (numCols - 1) * colGap;
  const startX = Math.floor((w - totalWidth) / 2);

  const numBlocks = 9;
  const blockHeight = 5;
  const blockGap = 2;
  const totalBlockH = numBlocks * blockHeight + (numBlocks - 1) * blockGap;
  const startY = Math.floor((h - totalBlockH) / 2);

  let freqData = null;
  if (audioAnalyser && !videoPlayer.paused) {
    freqData = new Uint8Array(audioAnalyser.frequencyBinCount);
    audioAnalyser.getByteFrequencyData(freqData);
  }

  const isPlaying = !videoPlayer.paused && !videoPlayer.ended && videoPlayer.currentTime > 0;
  const now = performance.now() * 0.003;

  for (let c = 0; c < numCols; c++) {
    let amplitude = 0.12; // Resting baseline
    if (isPlaying) {
      if (freqData && freqData.length > 0) {
        const binIndex = Math.floor((c / numCols) * (freqData.length * 0.7));
        amplitude = freqData[binIndex] / 255;
      } else {
        const wave1 = Math.sin(now * 3.2 + c * 0.28);
        const wave2 = Math.cos(now * 5.4 - c * 0.45);
        const wave3 = Math.sin(now * 1.8 + c * 0.15);
        amplitude = Math.max(0.1, (wave1 * 0.35 + wave2 * 0.25 + wave3 * 0.2 + 0.45));
      }
    }

    const activeBlocks = Math.min(numBlocks, Math.max(1, Math.round(amplitude * numBlocks)));
    const x = startX + c * (colWidth + colGap);

    for (let b = 0; b < numBlocks; b++) {
      const y = startY + (numBlocks - 1 - b) * (blockHeight + blockGap);
      const isActive = b < activeBlocks;

      if (isActive) {
        if (b < 4) {
          ctx.fillStyle = "#facc15"; // Neon yellow register
        } else if (b < 7) {
          ctx.fillStyle = "#38bdf8"; // Cyan mid register
        } else {
          ctx.fillStyle = "#4ade80"; // Emerald green peak register
        }
      } else {
        ctx.fillStyle = "rgba(255, 255, 255, 0.07)"; // Unlit segment matrix
      }

      ctx.fillRect(x, y, colWidth, blockHeight);
    }
  }

  if (isPlaying) {
    visualizerAnimId = requestAnimationFrame(renderAudioVisualizer);
  } else {
    visualizerAnimId = null;
  }
}

// --------------------------------------------------------------------------
// 4. Transcription & Progress Trigger
// --------------------------------------------------------------------------
generateBtn.addEventListener("click", async () => {
  if (!currentFile) return;

  generateBtn.disabled = true;
  generateBtn.classList.add("is-standby");
  const actionStatusChip = document.getElementById("actionStatusChip");
  const actionStatusText = document.getElementById("actionStatusText");
  if (actionStatusChip && actionStatusText) {
    actionStatusChip.classList.remove("ready");
    actionStatusText.textContent = "Processing audio with AI models...";
  }
  progressPanel.style.display = "block";
  resultsSection.style.display = "none";
  floatingDownloadBar.style.display = "none";
  if (workbenchEmptyState) workbenchEmptyState.style.display = "none";

  const isCached = modelsStatusMap[selectedModel] && modelsStatusMap[selectedModel].cached;
  progressBarFill.style.width = "15%";
  progressPctText.textContent = "15%";
  
  if (!isCached) {
    const sz = modelsStatusMap[selectedModel]?.size || "";
    progressStatusText.textContent = `📥 Downloading Whisper [${selectedModel.toUpperCase()}] weights (${sz}) from HuggingFace... First-time setup, please wait.`;
  } else {
    progressStatusText.textContent = "Uploading video & extracting audio...";
  }

  const topicHintEl = document.getElementById("topicHintInput");
  const topicHint = topicHintEl ? topicHintEl.value.trim() : "";

  const formData = new FormData();
  formData.append("video", currentFile);
  formData.append("language", selectedLanguage);
  formData.append("model_size", selectedModel);
  formData.append("device", selectedDevice);
  formData.append("topic_hint", topicHint);
  formData.append("pacing", selectedPacing);
  formData.append("enable_diarization", isDiarizationEnabled);

  // Smooth progression with live elapsed ticker (essential for longer audio files)
  let elapsedSec = 0;
  let progressInterval = setInterval(() => {
    elapsedSec++;
    let currentPct = parseInt(progressPctText.textContent) || 15;
    if (currentPct < 92) {
      currentPct = Math.min(92, currentPct + (currentPct < 60 ? 5 : (currentPct < 85 ? 2 : 1)));
      progressBarFill.style.width = `${currentPct}%`;
      progressPctText.textContent = `${currentPct}%`;
    }

    if (!isCached && elapsedSec < 12) {
      progressStatusText.textContent = `📥 Downloading Whisper [${selectedModel.toUpperCase()}] weights from HuggingFace...`;
    } else {
      const devName = selectedDevice.toUpperCase() === "AUTO" ? "GPU (CUDA)" : selectedDevice.toUpperCase();
      progressStatusText.textContent = `⚡ Neural transcription running on ${devName} (${elapsedSec}s elapsed)...`;
    }
  }, 1000);

  try {
    const res = await fetch("/api/transcribe", {
      method: "POST",
      body: formData
    });

    clearInterval(progressInterval);

    if (modelsStatusMap[selectedModel]) {
      modelsStatusMap[selectedModel].cached = true;
      updateModelStatusUI();
    }

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Transcription failed");
    }

    const data = await res.json();
    currentResults = data;
    currentSegments = data.segments || [];

    // Complete Progress Bar
    progressBarFill.style.width = "100%";
    progressPctText.textContent = "100%";
    progressStatusText.textContent = `Complete in ${data.elapsed_time.toFixed(1)}s (${data.speed_factor.toFixed(1)}x real-time)!`;

    setTimeout(() => {
      progressPanel.style.display = "none";
      displayResults(data);
    }, 600);

  } catch (err) {
    clearInterval(progressInterval);
    progressStatusText.textContent = `Error: ${err.message}`;
    progressBarFill.style.backgroundColor = "var(--pink)";
    updateGenerateButtonState(true, "Transcription failed. Click to retry.");
  }
});

// --------------------------------------------------------------------------
// 5. Render Results & Card Grid
// --------------------------------------------------------------------------
function displayResults(data) {
  window.__LAST_RESULT__ = data;
  resultsSection.style.display = "block";
  floatingDownloadBar.style.display = "flex";
  if (workbenchEmptyState) workbenchEmptyState.style.display = "none";
  if (typeof saveRecentTranscription === "function") {
    saveRecentTranscription({
      name: currentFile ? currentFile.name : "Subtitles",
      segments: currentSegments ? currentSegments.length : 0,
      timestamp: Date.now(),
      duration: videoPlayer && videoPlayer.duration ? videoPlayer.duration : 0
    });
  }
  updateGenerateButtonState(true, `Transcription complete (${currentSegments.length} segments). Ready to re-generate.`);

  segmentCountLabel.textContent = `Showing ${currentSegments.length} subtitle segments`;
  speedMetaLabel.textContent = `⚡ Speed: ${data.speed_factor.toFixed(1)}x real-time on ${data.active_device.toUpperCase()} (${data.active_compute})`;

  if (captionToggleGroup && currentSegments.length > 0) {
    captionToggleGroup.style.display = "flex";
  }
  updateDownloadButtonsLabels();
  updateVideoCaption();

  setSegmentsCollapsed(false);
  if (floatingSearchInput) floatingSearchInput.value = "";
  updateFloatingMatchPill(currentSegments.length, currentSegments.length, false);
  renderCards(currentSegments);
}

function renderCards(segments) {
  subtitleGrid.innerHTML = "";

  if (!segments || segments.length === 0) {
    subtitleGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--muted); font-family: var(--font-mono);">No subtitle segments found matching your search.</div>`;
    return;
  }

  segments.forEach((seg, idx) => {
    const card = document.createElement("div");
    card.className = "card";
    card.style.setProperty("--c", "var(--cyan)");

    const speakerBadge = seg.speaker ? `<span class="settings-card-badge" style="background: rgba(56, 189, 248, 0.15); color: var(--cyan); border-color: rgba(56, 189, 248, 0.3); font-size: 10px; margin-left: 8px;">👤 ${escapeHtml(seg.speaker)}</span>` : "";

    card.innerHTML = `
      <div>
        <div class="card-head">
          <div>
            <span class="card-idx">#${seg.index}</span>
            ${speakerBadge}
          </div>
          <span class="card-time">${seg.start_str} ➔ ${seg.end_str}</span>
        </div>
        <div class="card-orig-box">${escapeHtml(seg.original_text || "")}</div>
        <div class="card-hinglish-box">
          <b>${selectedLanguage === "hi-en" ? "TRANSLATED ENGLISH" : "HINGLISH"}</b>
          <span>${escapeHtml(seg.hinglish_text || "")}</span>
        </div>
      </div>
      <div class="card-foot">
        <span class="lang-tag">Click to inspect / edit</span>
        <button class="copy-btn" data-copy="${escapeHtml(seg.hinglish_text)}">COPY</button>
      </div>
    `;

    // Open drawer on card click (except copy button)
    card.addEventListener("click", (e) => {
      if (e.target.closest(".copy-btn")) return;
      openDrawer(seg);
    });

    const copyBtn = card.querySelector(".copy-btn");
    copyBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      navigator.clipboard.writeText(seg.hinglish_text);
      copyBtn.textContent = "COPIED!";
      copyBtn.classList.add("done");
      setTimeout(() => {
        copyBtn.textContent = "COPY";
        copyBtn.classList.remove("done");
      }, 1500);
    });

    subtitleGrid.appendChild(card);
  });
}

// --------------------------------------------------------------------------
// 6. Subtitle Segments Collapse / Expand Toggle Engine
// --------------------------------------------------------------------------
function setSegmentsCollapsed(collapsed) {
  isSegmentsCollapsed = collapsed;
  if (isSegmentsCollapsed) {
    if (subtitleGrid) subtitleGrid.style.display = "none";
    if (segmentsCollapsedCard) {
      segmentsCollapsedCard.style.display = "flex";
      if (collapsedCountText && currentSegments) {
        collapsedCountText.textContent = `${currentSegments.length} subtitle segments are hidden`;
      }
    }
    if (gridToggleIcon) gridToggleIcon.textContent = "▶";
    if (gridToggleText) gridToggleText.textContent = "SHOW CARDS";
  } else {
    if (subtitleGrid) subtitleGrid.style.display = "grid";
    if (segmentsCollapsedCard) segmentsCollapsedCard.style.display = "none";
    if (gridToggleIcon) gridToggleIcon.textContent = "▼";
    if (gridToggleText) gridToggleText.textContent = "HIDE CARDS";
  }
}

if (toggleGridBtn) {
  toggleGridBtn.addEventListener("click", () => {
    setSegmentsCollapsed(!isSegmentsCollapsed);
  });
}

if (expandSegmentsBannerBtn) {
  expandSegmentsBannerBtn.addEventListener("click", () => {
    setSegmentsCollapsed(false);
  });
}

// --------------------------------------------------------------------------
// 7. Subtitle Search (Floating Bottom Dock)
// --------------------------------------------------------------------------
const floatingSearchInput = document.getElementById("floatingSearchInput");

function updateFloatingMatchPill(matchCount, totalCount, isFiltering) {
  if (!floatingMatchPill || !floatingMatchCountText) return;
  if (!totalCount) {
    floatingMatchCountText.textContent = "0 SEGMENTS";
    floatingMatchPill.className = "live-match-pill";
    return;
  }
  if (!isFiltering) {
    floatingMatchCountText.textContent = `${totalCount} / ${totalCount} SEGMENTS`;
    floatingMatchPill.className = "live-match-pill";
  } else if (matchCount === 0) {
    floatingMatchCountText.textContent = `0 / ${totalCount} MATCHES`;
    floatingMatchPill.className = "live-match-pill is-zero-match";
  } else {
    floatingMatchCountText.textContent = `🎯 ${matchCount} / ${totalCount} MATCHES`;
    floatingMatchPill.className = "live-match-pill is-active-match";
  }
}

function handleSubtitleSearch(query) {
  const q = (query || "").toLowerCase().trim();
  if (isSegmentsCollapsed && q) {
    setSegmentsCollapsed(false);
  }

  if (!currentSegments || currentSegments.length === 0) {
    updateFloatingMatchPill(0, 0, false);
    return;
  }

  if (!q) {
    renderCards(currentSegments);
    if (segmentCountLabel) segmentCountLabel.textContent = `Showing ${currentSegments.length} subtitle segments`;
    updateFloatingMatchPill(currentSegments.length, currentSegments.length, false);
    return;
  }

  const filtered = currentSegments.filter(seg => 
    (seg.hinglish_text && seg.hinglish_text.toLowerCase().includes(q)) ||
    (seg.original_text && seg.original_text.toLowerCase().includes(q))
  );

  if (segmentCountLabel) segmentCountLabel.textContent = `Showing ${filtered.length} of ${currentSegments.length} segments`;
  updateFloatingMatchPill(filtered.length, currentSegments.length, true);
  renderCards(filtered);
}

if (floatingSearchInput) {
  floatingSearchInput.addEventListener("input", (e) => {
    handleSubtitleSearch(e.target.value);
  });
}

// Global keyboard shortcuts: '/' to focus bottom search, 'Escape' to close drawer, ',' to open settings
document.addEventListener("keydown", (e) => {
  const activeTag = (document.activeElement.tagName || "").toLowerCase();
  const isInputActive = activeTag === "input" || activeTag === "textarea";

  if (e.key === "/" && document.activeElement !== floatingSearchInput) {
    if (isInputActive) {
      return;
    }
    e.preventDefault();
    if (floatingSearchInput) {
      floatingSearchInput.focus();
      floatingSearchInput.select();
    }
  } else if (e.key === "," && !isInputActive) {
    e.preventDefault();
    toggleSettingsDrawer();
  } else if (e.key === "Escape") {
    if (settingsDrawer && settingsDrawer.classList.contains("open")) {
      closeSettingsDrawer();
    } else if (drawer && drawer.classList.contains("open")) {
      closeDrawer();
    }
  }
});

// --------------------------------------------------------------------------
// Studio Settings Slide-over Drawer (Option 1)
// --------------------------------------------------------------------------
function openSettingsDrawer() {
  if (settingsDrawer && settingsDrawerOverlay) {
    if (drawer && drawer.classList.contains("open")) {
      closeDrawer();
    }
    settingsDrawerOverlay.classList.add("open");
    settingsDrawer.classList.add("open");
    if (settingsHwBadge && hwBadge) {
      settingsHwBadge.textContent = hwBadge.textContent;
    }
  }
}

function closeSettingsDrawer() {
  if (settingsDrawer && settingsDrawerOverlay) {
    settingsDrawerOverlay.classList.remove("open");
    settingsDrawer.classList.remove("open");
  }
}

function toggleSettingsDrawer() {
  if (settingsDrawer && settingsDrawer.classList.contains("open")) {
    closeSettingsDrawer();
  } else {
    openSettingsDrawer();
  }
}

if (openSettingsBtn) {
  openSettingsBtn.addEventListener("click", openSettingsDrawer);
}
if (hwBadge) {
  hwBadge.addEventListener("click", openSettingsDrawer);
}
if (settingsDrawerCloseBtn) {
  settingsDrawerCloseBtn.addEventListener("click", closeSettingsDrawer);
}
if (settingsDrawerOverlay) {
  settingsDrawerOverlay.addEventListener("click", closeSettingsDrawer);
}
if (saveAndCloseSettingsBtn) {
  saveAndCloseSettingsBtn.addEventListener("click", closeSettingsDrawer);
}

// --------------------------------------------------------------------------
// 7. Drawer Inspector & Live Editor
// --------------------------------------------------------------------------
function openDrawer(seg) {
  activeSegmentIndex = seg.index;
  drawerIndexTitle.textContent = `SEGMENT #${seg.index}`;
  drawerTimeRange.textContent = `${seg.start_str} ➔ ${seg.end_str}`;
  drawerOrigText.textContent = seg.original_text || "—";
  drawerHinglishInput.value = seg.hinglish_text || "";

  drawerOverlay.classList.add("open");
  drawer.classList.add("open");
}

function closeDrawer() {
  drawerOverlay.classList.remove("open");
  drawer.classList.remove("open");
  activeSegmentIndex = null;
}

drawerCloseBtn.addEventListener("click", closeDrawer);
drawerOverlay.addEventListener("click", closeDrawer);

drawerSaveBtn.addEventListener("click", () => {
  if (activeSegmentIndex === null) return;
  const newText = drawerHinglishInput.value.trim();
  const seg = currentSegments.find(s => s.index === activeSegmentIndex);
  if (seg) {
    seg.hinglish_text = newText;
    renderCards(currentSegments);
    updateVideoCaption();
    drawerSaveBtn.textContent = "SAVED!";
    setTimeout(() => {
      drawerSaveBtn.textContent = "Save Subtitle Edit";
      closeDrawer();
    }, 600);
  }
});

drawerCopyBtn.addEventListener("click", () => {
  navigator.clipboard.writeText(drawerHinglishInput.value);
  drawerCopyBtn.textContent = "COPIED!";
  setTimeout(() => { drawerCopyBtn.textContent = "COPY TEXT"; }, 1500);
});

drawerPlayAudioBtn.addEventListener("click", () => {
  if (activeSegmentIndex === null || !videoPlayer.src) return;
  const seg = currentSegments.find(s => s.index === activeSegmentIndex);
  if (seg) {
    videoPlayer.currentTime = seg.start;
    videoPlayer.play();
  }
});

// --------------------------------------------------------------------------
// 8. Subtitle Downloads & Desktop Native File Export
// --------------------------------------------------------------------------
function rebuildSrt(isHinglish = true) {
  if (!currentSegments || currentSegments.length === 0) return "";
  return currentSegments.map(seg => {
    const text = isHinglish ? seg.hinglish_text : seg.original_text;
    return `${seg.index}\n${seg.start_str} --> ${seg.end_str}\n${text || ""}\n`;
  }).join("\n");
}

function showDownloadFeedback(btn, message, isSuccess = true) {
  const metaText = document.getElementById("downloadMetaText");
  if (metaText) {
    metaText.textContent = message;
    metaText.style.color = isSuccess ? "var(--green)" : "var(--pink)";
    setTimeout(() => {
      metaText.textContent = "Ready for YouTube, Premiere & DaVinci";
      metaText.style.color = "var(--muted)";
    }, 4500);
  }

  if (btn) {
    const origText = btn.dataset.origText || btn.textContent;
    btn.dataset.origText = origText;
    btn.textContent = isSuccess ? "✓ SAVED!" : "FAILED";
    btn.style.filter = isSuccess ? "brightness(1.15)" : "none";
    setTimeout(() => {
      btn.textContent = origText;
      btn.style.filter = "";
    }, 2500);
  }
}

async function triggerDownload(filename, content, btn) {
  if (!content || !content.trim()) {
    showDownloadFeedback(btn, "No subtitle content available to export yet", false);
    return;
  }

  // Strategy 1: Native Windows OS Save Dialog via pywebview desktop bridge
  if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.save_subtitle_file === "function") {
    try {
      const res = await window.pywebview.api.save_subtitle_file(filename, content);
      if (res && res.success) {
        showDownloadFeedback(btn, `✓ Exported to ${res.path}`, true);
        return;
      } else if (res && res.cancelled) {
        // User clicked Cancel in Windows dialog; clean return
        return;
      }
    } catch (err) {
      console.warn("pywebview desktop save error, falling back to server download:", err);
    }
  }

  // Strategy 2: Server Download Endpoint (Standard HTTP Content-Disposition)
  try {
    const response = await fetch("/api/download/file", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, content })
    });
    if (response.ok) {
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      showDownloadFeedback(btn, `✓ Downloaded ${filename}`, true);
      return;
    }
  } catch (err) {
    console.warn("Server download fetch error, falling back to client blob:", err);
  }

  // Strategy 3: Client-Side Blob Fallback (delayed revocation prevents WebView2 abort)
  try {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    showDownloadFeedback(btn, `✓ Downloaded ${filename}`, true);
  } catch (err) {
    showDownloadFeedback(btn, `Download failed: ${err.message}`, false);
  }
}

downloadHinglishBtn.addEventListener("click", () => {
  const srtContent = rebuildSrt(true);
  const baseName = currentFile ? currentFile.name.replace(/\.[^/.]+$/, "") : "subtitles";
  const suffix = selectedLanguage === "hi-en" ? "english" : "hinglish";
  triggerDownload(`${baseName}_${suffix}.srt`, srtContent, downloadHinglishBtn);
});

if (downloadAssBtn) {
  downloadAssBtn.addEventListener("click", async () => {
    const baseName = currentFile ? currentFile.name.replace(/\.[^/.]+$/, "") : "subtitles";
    const title = `${baseName} - Karaoke`;
    
    // If backend returned pre-calculated ass_karaoke and no manual edits were made, use it
    if (window.__LAST_RESULT__ && window.__LAST_RESULT__.ass_karaoke && !hasManualEdits()) {
      triggerDownload(`${baseName}_karaoke.ass`, window.__LAST_RESULT__.ass_karaoke, downloadAssBtn);
      return;
    }

    // Otherwise fetch fresh ASS from server with current edited segments
    try {
      const origText = downloadAssBtn.textContent;
      downloadAssBtn.textContent = "⏳ GENERATING ASS...";
      const res = await fetch("/api/export/ass", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ segments: currentSegments || [], title: title })
      });
      if (res.ok) {
        const assText = await res.text();
        triggerDownload(`${baseName}_karaoke.ass`, assText, downloadAssBtn);
      } else {
        alert("Failed to export ASS karaoke subtitles.");
      }
    } catch (e) {
      console.error(e);
      alert("Error generating ASS file: " + e.message);
    } finally {
      downloadAssBtn.textContent = "🎤 KARAOKE (.ASS)";
    }
  });
}

function hasManualEdits() {
  return false;
}

if (burnVideoBtn) {
  burnVideoBtn.addEventListener("click", async () => {
    if (!currentFile) {
      alert("Please upload or load a video file first to burn subtitles.");
      return;
    }
    const isAudio = currentFile.type.startsWith("audio/") || /\.(mp3|wav|m4a|aac|flac|ogg)$/i.test(currentFile.name);
    if (isAudio) {
      alert("Subtitle burn-in requires a video file (MP4, MKV, MOV, etc.). For audio, please download .SRT or .ASS.");
      return;
    }

    const baseName = currentFile.name.replace(/\.[^/.]+$/, "");
    const origBtnText = burnVideoBtn.innerHTML;

    try {
      burnVideoBtn.disabled = true;
      burnVideoBtn.innerHTML = `<span>⏳</span> BURNING WITH FFMPEG...`;

      // 1. Prepare ASS or SRT payload
      let subPayload = "";
      let subFormat = "ass";

      if (window.__LAST_RESULT__ && window.__LAST_RESULT__.ass_karaoke && !hasManualEdits()) {
        subPayload = window.__LAST_RESULT__.ass_karaoke;
      } else {
        // Fetch fresh ASS from server
        const assRes = await fetch("/api/export/ass", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ segments: currentSegments || [], title: `${baseName} - Subtitles` })
        });
        if (assRes.ok) {
          subPayload = await assRes.text();
        } else {
          subPayload = rebuildSrt(true);
          subFormat = "srt";
        }
      }

      // 2. Send video + subtitle to /api/export/burn-video
      const formData = new FormData();
      formData.append("video", currentFile);
      formData.append("subtitles", subPayload);
      formData.append("format_type", subFormat);

      const burnRes = await fetch("/api/export/burn-video", {
        method: "POST",
        body: formData
      });

      if (!burnRes.ok) {
        const errJson = await burnRes.json().catch(() => ({}));
        throw new Error(errJson.detail || "FFmpeg burn failed on server");
      }

      const blob = await burnRes.blob();
      const burnedUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = burnedUrl;
      a.download = `${baseName}_subtitled.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(burnedUrl), 60000);

      burnVideoBtn.innerHTML = `<span>✓</span> BURN COMPLETE!`;
      setTimeout(() => { burnVideoBtn.innerHTML = origBtnText; burnVideoBtn.disabled = false; }, 3500);

    } catch (err) {
      console.error("Burn video error:", err);
      alert("Video burning error: " + err.message);
      burnVideoBtn.innerHTML = origBtnText;
      burnVideoBtn.disabled = false;
    }
  });
}

downloadOrigBtn.addEventListener("click", () => {
  const srtContent = rebuildSrt(false);
  const baseName = currentFile ? currentFile.name.replace(/\.[^/.]+$/, "") : "subtitles";
  triggerDownload(`${baseName}_original.srt`, srtContent, downloadOrigBtn);
});

downloadTxtBtn.addEventListener("click", () => {
  const textContent = currentSegments ? currentSegments.map(s => s.hinglish_text || "").join("\n") : "";
  const baseName = currentFile ? currentFile.name.replace(/\.[^/.]+$/, "") : "subtitles";
  const suffix = selectedLanguage === "hi-en" ? "english" : "hinglish";
  triggerDownload(`${baseName}_${suffix}.txt`, textContent, downloadTxtBtn);
});

if (floatingCopyAllBtn) {
  floatingCopyAllBtn.addEventListener("click", async () => {
    if (!currentSegments || currentSegments.length === 0) return;
    const allText = currentSegments
      .map(s => (s.hinglish_text || s.original_text || "").trim())
      .filter(Boolean)
      .join("\n");
    
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(allText);
      } else {
        const tempArea = document.createElement("textarea");
        tempArea.value = allText;
        tempArea.style.position = "fixed";
        tempArea.style.opacity = "0";
        document.body.appendChild(tempArea);
        tempArea.select();
        document.execCommand("copy");
        document.body.removeChild(tempArea);
      }

      floatingCopyAllBtn.classList.add("copied");
      if (floatingCopyAllText) floatingCopyAllText.textContent = "COPIED! ✅";
      setTimeout(() => {
        floatingCopyAllBtn.classList.remove("copied");
        if (floatingCopyAllText) floatingCopyAllText.textContent = "COPY ALL";
      }, 1800);
    } catch (err) {
      console.error("Clipboard copy failed:", err);
      alert("Unable to copy to clipboard automatically.");
    }
  });
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/* ==========================================================================
   WORKBENCH EMPTY STATE CONTROLLER (PATTERN B: WEB IMPORTER & RECENTS)
   ========================================================================== */

function updateWorkbenchGridLayout() {
  const importerHidden = localStorage.getItem("hide_workbench_importer") === "true";
  const recentsHidden = localStorage.getItem("hide_workbench_recents") === "true";

  if (workbenchImporterCard) {
    workbenchImporterCard.style.display = importerHidden ? "none" : "flex";
  }
  if (workbenchRecentsCard) {
    workbenchRecentsCard.style.display = recentsHidden ? "none" : "flex";
  }

  // Sync Settings Drawer visibility buttons
  const settingsShowImporterBtn = document.getElementById("settingsShowImporterBtn");
  const settingsHideImporterBtn = document.getElementById("settingsHideImporterBtn");
  const settingsShowRecentsBtn = document.getElementById("settingsShowRecentsBtn");
  const settingsHideRecentsBtn = document.getElementById("settingsHideRecentsBtn");

  if (settingsShowImporterBtn && settingsHideImporterBtn) {
    settingsShowImporterBtn.classList.toggle("active", !importerHidden);
    settingsHideImporterBtn.classList.toggle("active", importerHidden);
  }

  if (settingsShowRecentsBtn && settingsHideRecentsBtn) {
    settingsShowRecentsBtn.classList.toggle("active", !recentsHidden);
    settingsHideRecentsBtn.classList.toggle("active", recentsHidden);
  }

  if (workbenchGrid) {
    if (importerHidden && !recentsHidden) {
      workbenchGrid.classList.add("full-width");
      workbenchGrid.style.display = "grid";
    } else if (!importerHidden && recentsHidden) {
      workbenchGrid.classList.add("full-width");
      workbenchGrid.style.display = "grid";
    } else if (importerHidden && recentsHidden) {
      workbenchGrid.style.display = "none";
    } else {
      workbenchGrid.classList.remove("full-width");
      workbenchGrid.style.display = "grid";
    }
  }
}

function initWorkbenchPanelToggles() {
  const settingsShowImporterBtn = document.getElementById("settingsShowImporterBtn");
  const settingsHideImporterBtn = document.getElementById("settingsHideImporterBtn");
  const settingsShowRecentsBtn = document.getElementById("settingsShowRecentsBtn");
  const settingsHideRecentsBtn = document.getElementById("settingsHideRecentsBtn");

  if (settingsShowImporterBtn) {
    settingsShowImporterBtn.addEventListener("click", () => {
      localStorage.removeItem("hide_workbench_importer");
      updateWorkbenchGridLayout();
    });
  }
  if (settingsHideImporterBtn) {
    settingsHideImporterBtn.addEventListener("click", () => {
      localStorage.setItem("hide_workbench_importer", "true");
      updateWorkbenchGridLayout();
    });
  }

  if (settingsShowRecentsBtn) {
    settingsShowRecentsBtn.addEventListener("click", () => {
      localStorage.removeItem("hide_workbench_recents");
      updateWorkbenchGridLayout();
    });
  }
  if (settingsHideRecentsBtn) {
    settingsHideRecentsBtn.addEventListener("click", () => {
      localStorage.setItem("hide_workbench_recents", "true");
      updateWorkbenchGridLayout();
    });
  }

  updateWorkbenchGridLayout();
}

function initUrlImporter() {
  if (!urlFetchBtn || !urlImportInput) return;

  const QUALITY_CONFIGS = {
    video: [
      { val: "best", text: "🌟 Source Best (1080p/Max)" },
      { val: "720p", text: "⚡ 720p (Fast HD)", default: true },
      { val: "480p", text: "⚡ 480p (Lightweight)" }
    ],
    audio: [
      { val: "best", text: "🌟 Source / 320k (High Quality)", default: true },
      { val: "128k", text: "⚡ 128 kbps (Standard)" },
      { val: "64k", text: "⚡ 64 kbps (Speech / Fast)" }
    ]
  };

  let currentMode = "video";
  try {
    currentMode = localStorage.getItem("importer_media_type") || "video";
  } catch (e) {}

  let currentQuality = (currentMode === "audio" ? "best" : "720p");
  try {
    const saved = localStorage.getItem("importer_quality");
    if (saved) currentQuality = saved;
  } catch (e) {}

  function renderQualityOptions(mode, selectedVal) {
    if (!importerQualitySelect) return;
    const opts = QUALITY_CONFIGS[mode] || QUALITY_CONFIGS.video;
    importerQualitySelect.innerHTML = "";

    let matched = false;
    opts.forEach(opt => {
      const el = document.createElement("option");
      el.value = opt.val;
      el.textContent = opt.text;
      if (selectedVal && opt.val === selectedVal) {
        el.selected = true;
        matched = true;
      } else if (!selectedVal && opt.default) {
        el.selected = true;
        matched = true;
      }
      importerQualitySelect.appendChild(el);
    });

    if (!matched && opts[0]) {
      importerQualitySelect.value = opts[0].val;
    }
    currentQuality = importerQualitySelect.value;
  }

  function setImporterMode(mode) {
    currentMode = mode === "audio" ? "audio" : "video";
    try {
      localStorage.setItem("importer_media_type", currentMode);
    } catch (e) {}

    if (importerModeVideo) {
      importerModeVideo.classList.toggle("active", currentMode === "video");
    }
    if (importerModeAudio) {
      importerModeAudio.classList.toggle("active", currentMode === "audio");
    }

    renderQualityOptions(currentMode);
  }

  // Setup tab click listeners
  if (importerModeVideo) {
    importerModeVideo.addEventListener("click", () => setImporterMode("video"));
  }
  if (importerModeAudio) {
    importerModeAudio.addEventListener("click", () => setImporterMode("audio"));
  }
  if (importerQualitySelect) {
    importerQualitySelect.addEventListener("change", (e) => {
      currentQuality = e.target.value;
      try {
        localStorage.setItem("importer_quality", currentQuality);
      } catch (err) {}
    });
  }

  // Initial render
  setImporterMode(currentMode);
  if (currentQuality) {
    renderQualityOptions(currentMode, currentQuality);
  }

  async function handleUrlFetch() {
    const rawUrl = urlImportInput.value.trim();
    if (!rawUrl) {
      showUrlImportStatus("Please paste a valid video or reel URL.", "error");
      urlImportInput.focus();
      return;
    }

    const mode = currentMode;
    const quality = importerQualitySelect ? importerQualitySelect.value : (mode === "audio" ? "best" : "720p");
    const modeDesc = mode === "audio" ? `audio stream (${quality})` : `video stream (${quality})`;

    urlFetchBtn.disabled = true;
    if (urlFetchText) urlFetchText.textContent = "⏳ FETCHING...";
    showUrlImportStatus(`Connecting via yt-dlp to download ${modeDesc}... (Please wait)`, "loading");

    try {
      const res = await fetch("/api/import-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: rawUrl,
          media_type: mode,
          quality: quality
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to download media");
      }

      const mediaTypeLabel = data.media_type === "audio" ? "audio" : "video";
      showUrlImportStatus(`✓ Download complete: "${data.title}" (${data.duration ? Math.round(data.duration) + 's' : ''}). Staging ${mediaTypeLabel}...`, "success");

      // Fetch the downloaded file as a Blob and stage it into the media player
      const mediaRes = await fetch(data.media_url);
      if (!mediaRes.ok) throw new Error("Could not retrieve downloaded media stream");
      const blob = await mediaRes.blob();
      const mimeType = blob.type || (data.media_type === "audio" ? "audio/mp4" : "video/mp4");
      const fallbackName = data.media_type === "audio" ? "imported_audio.m4a" : "imported_reel.mp4";
      const file = new File([blob], data.filename || fallbackName, { type: mimeType });

      handleSelectedFile(file);
      urlImportInput.value = "";
      setTimeout(() => {
        if (urlImportStatus) urlImportStatus.style.display = "none";
      }, 3000);

    } catch (err) {
      console.error("URL Import error:", err);
      showUrlImportStatus(err.message || "Failed to import video link", "error");
    } finally {
      urlFetchBtn.disabled = false;
      if (urlFetchText) urlFetchText.textContent = "⚡ FETCH & STAGE";
    }
  }

  urlFetchBtn.addEventListener("click", handleUrlFetch);
  urlImportInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleUrlFetch();
    }
  });
}

function showUrlImportStatus(msg, type) {
  if (!urlImportStatus) return;
  urlImportStatus.textContent = msg;
  urlImportStatus.className = `url-import-status is-${type}`;
  urlImportStatus.style.display = "block";
}

function saveRecentTranscription(item) {
  try {
    const raw = localStorage.getItem("recent_transcriptions");
    let recents = raw ? JSON.parse(raw) : [];
    // Deduplicate by name
    recents = recents.filter(r => r.name !== item.name);
    recents.unshift(item);
    if (recents.length > 4) recents = recents.slice(0, 4);
    localStorage.setItem("recent_transcriptions", JSON.stringify(recents));
    renderRecentTranscriptions();
  } catch (e) {
    console.warn("Could not save recent transcription:", e);
  }
}

function renderRecentTranscriptions() {
  if (!recentsListContainer) return;
  recentsListContainer.innerHTML = "";

  let recents = [];
  try {
    const raw = localStorage.getItem("recent_transcriptions");
    if (raw) recents = JSON.parse(raw);
  } catch (e) {}

  if (!recents || recents.length === 0) {
    recentsListContainer.innerHTML = `<div class="recents-empty-hint">No past transcriptions recorded yet. Transcribe a file or test a sample below!</div>`;
    return;
  }

  recents.forEach(r => {
    const row = document.createElement("div");
    row.className = "recent-row";

    const mins = Math.floor((r.duration || 0) / 60);
    const secs = Math.floor((r.duration || 0) % 60);
    const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    row.innerHTML = `
      <div style="display: flex; align-items: center; overflow: hidden;">
        <span class="recent-row-name" title="${escapeHtml(r.name)}">🎬 ${escapeHtml(r.name)}</span>
        <span class="recent-row-meta">• ${timeStr} • ${r.segments} segs</span>
      </div>
      <button type="button" class="recent-open-btn" title="View details">PAST JOB ✓</button>
    `;
    recentsListContainer.appendChild(row);
  });
}

function initSampleLoaders() {
  async function loadSample(sampleUrl, filename) {
    const actionStatusChip = document.getElementById("actionStatusChip");
    const actionStatusText = document.getElementById("actionStatusText");
    if (actionStatusChip && actionStatusText) {
      actionStatusChip.classList.remove("ready");
      actionStatusText.textContent = `Loading sample benchmark ${filename}...`;
    }
    try {
      const res = await fetch(sampleUrl);
      if (!res.ok) throw new Error("Sample file not found on server");
      const blob = await res.blob();
      const file = new File([blob], filename, { type: "video/mp4" });
      handleSelectedFile(file);
    } catch (err) {
      console.error("Error loading sample reel:", err);
      alert(`Could not load sample reel: ${err.message}`);
    }
  }

  if (sampleTrafficBtn) {
    sampleTrafficBtn.addEventListener("click", () => {
      loadSample("/static/samples/traffic.mp4", "traffic_reel_benchmark.mp4");
    });
  }

  if (sampleGeniusBtn) {
    sampleGeniusBtn.addEventListener("click", () => {
      loadSample("/static/samples/genius_ad.mp4", "genius_ad_benchmark.mp4");
    });
  }
}

function initWorkbenchEmptyState() {
  initWorkbenchPanelToggles();
  initUrlImporter();
  renderRecentTranscriptions();
  initSampleLoaders();
}

/* ==========================================================================
   IN-APP TERMINAL CONSOLE CONTROLLER (OPTION 1)
   ========================================================================== */

(function initConsoleDock() {
  const toggleConsoleBtn = document.getElementById("toggleConsoleBtn");
  const consoleBadge = document.getElementById("consoleBadge");
  const consoleNavDot = document.getElementById("consoleNavDot");
  const terminalDock = document.getElementById("terminalDock");
  const terminalResizeHandle = document.getElementById("terminalResizeHandle");
  const terminalBody = document.getElementById("terminalBody");
  const terminalIndicator = document.getElementById("terminalIndicator");
  const consoleStatusText = document.getElementById("consoleStatusText");
  const terminalFilterGroup = document.getElementById("terminalFilterGroup");
  const clearConsoleBtn = document.getElementById("clearConsoleBtn");
  const copyConsoleBtn = document.getElementById("copyConsoleBtn");
  const downloadConsoleBtn = document.getElementById("downloadConsoleBtn");
  const closeConsoleBtn = document.getElementById("closeConsoleBtn");

  if (!terminalDock || !terminalBody) return;

  let activeFilter = "all";
  let logEntries = [];
  let unreadErrors = 0;
  let isUserScrolledUp = false;
  let isDragging = false;
  let startY = 0;
  let startHeight = 320;

  // Restore saved dock height and state
  const savedHeight = localStorage.getItem("terminalDockHeight");
  if (savedHeight && parseInt(savedHeight) >= 120 && parseInt(savedHeight) <= (window.innerHeight - 80)) {
    terminalDock.style.height = `${parseInt(savedHeight)}px`;
  }

  function toggleDock(open) {
    const isCollapsed = terminalDock.classList.contains("collapsed");
    const shouldOpen = open !== undefined ? open : isCollapsed;

    if (shouldOpen) {
      terminalDock.classList.remove("collapsed");
      unreadErrors = 0;
      updateBadge();
      scrollToBottom();
    } else {
      terminalDock.classList.add("collapsed");
    }
  }

  if (toggleConsoleBtn) {
    toggleConsoleBtn.addEventListener("click", () => toggleDock());
  }

  if (closeConsoleBtn) {
    closeConsoleBtn.addEventListener("click", () => toggleDock(false));
  }

  // Keyboard shortcut: Ctrl + ` (backtick) or Escape to close if open
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key === "`" || e.code === "Backquote")) {
      e.preventDefault();
      toggleDock();
    } else if (e.key === "Escape" && !terminalDock.classList.contains("collapsed")) {
      // Don't close if drawer is active
      const drawer = document.getElementById("drawer");
      if (!drawer || !drawer.classList.contains("active")) {
        toggleDock(false);
      }
    }
  });

  // Drag-to-resize behavior
  if (terminalResizeHandle) {
    terminalResizeHandle.addEventListener("mousedown", (e) => {
      isDragging = true;
      startY = e.clientY;
      startHeight = terminalDock.offsetHeight;
      terminalResizeHandle.classList.add("active");
      document.body.style.userSelect = "none";
      document.body.style.cursor = "ns-resize";
    });

    window.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      const delta = startY - e.clientY;
      const newHeight = Math.max(120, Math.min(window.innerHeight - 60, startHeight + delta));
      terminalDock.style.height = `${newHeight}px`;
    });

    window.addEventListener("mouseup", () => {
      if (isDragging) {
        isDragging = false;
        terminalResizeHandle.classList.remove("active");
        document.body.style.userSelect = "";
        document.body.style.cursor = "";
        localStorage.setItem("terminalDockHeight", terminalDock.offsetHeight);
      }
    });
  }

  // Smart auto-scroll detection
  terminalBody.addEventListener("scroll", () => {
    const scrollPos = terminalBody.scrollTop + terminalBody.clientHeight;
    const isAtBottom = scrollPos >= terminalBody.scrollHeight - 30;
    isUserScrolledUp = !isAtBottom;
  });

  function scrollToBottom() {
    if (!isUserScrolledUp) {
      terminalBody.scrollTop = terminalBody.scrollHeight;
    }
  }

  function renderLogEntry(entry) {
    logEntries.push(entry);
    updateBadge();

    // Check filter match
    const level = (entry.level || "INFO").toUpperCase();
    let matches = true;
    if (activeFilter === "stage") matches = (level === "STAGE");
    else if (activeFilter === "warn") matches = (level === "WARN");
    else if (activeFilter === "error") matches = (level === "ERROR");

    if (level === "ERROR") {
      consoleNavDot.className = "console-dot error";
      terminalIndicator.style.background = "var(--pink)";
      if (terminalDock.classList.contains("collapsed")) {
        unreadErrors++;
        // Auto-open dock on first unexpected error
        toggleDock(true);
      }
    } else if (level === "WARN" && consoleNavDot.className !== "console-dot error") {
      consoleNavDot.className = "console-dot warn";
    }

    if (!matches) return;

    const line = document.createElement("div");
    line.className = "log-line";
    line.dataset.level = level;
    line.innerHTML = `
      <span class="log-time">${escapeHtml(entry.time || "")}</span>
      <span class="log-level ${level}">[${level}]</span>
      <span class="log-msg ${level}">${escapeHtml(entry.message || "")}</span>
    `;

    terminalBody.appendChild(line);
    scrollToBottom();
  }

  function rebuildVisibleLogs() {
    terminalBody.innerHTML = "";
    for (const entry of logEntries) {
      const level = (entry.level || "INFO").toUpperCase();
      let matches = true;
      if (activeFilter === "stage") matches = (level === "STAGE");
      else if (activeFilter === "warn") matches = (level === "WARN");
      else if (activeFilter === "error") matches = (level === "ERROR");

      if (matches) {
        const line = document.createElement("div");
        line.className = "log-line";
        line.dataset.level = level;
        line.innerHTML = `
          <span class="log-time">${escapeHtml(entry.time || "")}</span>
          <span class="log-level ${level}">[${level}]</span>
          <span class="log-msg ${level}">${escapeHtml(entry.message || "")}</span>
        `;
        terminalBody.appendChild(line);
      }
    }
    scrollToBottom();
  }

  function updateBadge() {
    if (consoleBadge) {
      consoleBadge.textContent = logEntries.length;
    }
  }

  // Filter Buttons
  if (terminalFilterGroup) {
    terminalFilterGroup.addEventListener("click", (e) => {
      const btn = e.target.closest(".terminal-pill");
      if (!btn) return;
      terminalFilterGroup.querySelectorAll(".terminal-pill").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      activeFilter = btn.dataset.filter || "all";
      rebuildVisibleLogs();
    });
  }

  // Actions
  if (clearConsoleBtn) {
    clearConsoleBtn.addEventListener("click", async () => {
      try {
        await fetch("/api/console/clear", { method: "POST" });
        logEntries = [];
        terminalBody.innerHTML = "";
        updateBadge();
      } catch (err) {
        console.error("Clear console failed:", err);
      }
    });
  }

  if (copyConsoleBtn) {
    copyConsoleBtn.addEventListener("click", () => {
      const text = logEntries.map(e => `[${e.time}] [${e.level}] ${e.message}`).join("\n");
      navigator.clipboard.writeText(text).then(() => {
        const oldText = copyConsoleBtn.textContent;
        copyConsoleBtn.textContent = "COPIED!";
        setTimeout(() => { copyConsoleBtn.textContent = oldText; }, 1500);
      });
    });
  }

  if (downloadConsoleBtn) {
    downloadConsoleBtn.addEventListener("click", () => {
      window.location.href = "/api/console/download";
    });
  }

  // Fetch initial history
  fetch("/api/console/history?limit=1000")
    .then(r => r.json())
    .then(data => {
      if (data && data.lines && Array.isArray(data.lines)) {
        for (const item of data.lines) {
          renderLogEntry(item);
        }
      }
      connectSSE();
    })
    .catch(() => {
      connectSSE();
    });

  // Connect SSE live log stream
  function connectSSE() {
    if (consoleStatusText) consoleStatusText.textContent = "CONNECTING...";
    const evtSource = new EventSource("/api/console/stream");

    evtSource.onopen = () => {
      if (consoleStatusText) consoleStatusText.textContent = "LIVE STREAM ACTIVE";
      if (terminalIndicator) terminalIndicator.style.background = "var(--green)";
    };

    evtSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "connected") return;
        renderLogEntry(data);
      } catch (err) {
        // Heartbeat or malformed JSON
      }
    };

    evtSource.onerror = () => {
      if (consoleStatusText) consoleStatusText.textContent = "DISCONNECTED (RETRYING)";
      if (terminalIndicator) terminalIndicator.style.background = "var(--pink)";
    };
  }
})();

