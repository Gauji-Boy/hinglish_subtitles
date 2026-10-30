/* ==========================================================================
   APP.JS - CLIENT CONTROLLER FOR HINGLISH SUBTITLE GENERATOR
   Connects UI to FastAPI backend, manages drag-and-drop, drawer, and search.
   ========================================================================== */

let currentFile = null;
let currentResults = null;
let currentSegments = [];
let activeSegmentIndex = null;
let editorSearchQuery = "";
let editorDirty = false;
let editorStyleSaveTimer = null;

const initialConfig = window.__INITIAL_CONFIG__ || {};
let selectedLanguage = initialConfig.selected_language || localStorage.getItem("selectedLanguage") || "mixed";
let selectedDevice = initialConfig.selected_device || localStorage.getItem("selectedDevice") || "auto";
let selectedModel = initialConfig.selected_model || localStorage.getItem("selectedModel") || "large-v3-turbo";
let selectedPacing = initialConfig.selected_pacing || localStorage.getItem("selectedPacing") || "short";
const storedDiarization = localStorage.getItem("isDiarizationEnabled");
let isDiarizationEnabled = storedDiarization === null
  ? (initialConfig.enable_diarization ?? false)
  : storedDiarization === "true";
let activeCaptionStyle = initialConfig.caption_style || null;
let captionStyles = [];
let captionFonts = [];
let defaultCaptionStyleId = "hormozi";
let stylePreviewTimer = null;
let stylePreviewUrl = null;

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
const stylePresetGrid = document.getElementById("stylePresetGrid");
const styleSample = document.getElementById("styleSample");
const styleSampleText = document.getElementById("styleSampleText");
const styleEditBtn = document.getElementById("styleEditBtn");
const styleResetBtn = document.getElementById("styleResetBtn");
const styleExportBtn = document.getElementById("styleExportBtn");
const styleImportBtn = document.getElementById("styleImportBtn");
const styleImportFile = document.getElementById("styleImportFile");
const styleEditor = document.getElementById("styleEditor");
const editorStylePresetGrid = document.getElementById("editorStylePresetGrid");
const editorStyleFont = document.getElementById("editorStyleFont");
const editorStyleFontSize = document.getElementById("editorStyleFontSize");
const editorStyleBaseColor = document.getElementById("editorStyleBaseColor");
const editorStyleHighlightColor = document.getElementById("editorStyleHighlightColor");
const editorStyleOutline = document.getElementById("editorStyleOutline");
const editorStyleMargin = document.getElementById("editorStyleMargin");
const editorStyleMarginValue = document.getElementById("editorStyleMarginValue");
const editorStyleUppercase = document.getElementById("editorStyleUppercase");
const editorStyleBox = document.getElementById("editorStyleBox");
const editorStyleResetBtn = document.getElementById("editorStyleResetBtn");
const editorStyleExportBtn = document.getElementById("editorStyleExportBtn");
const editorStyleImportBtn = document.getElementById("editorStyleImportBtn");
const editorStyleImportFile = document.getElementById("editorStyleImportFile");
const editorStyleStatus = document.getElementById("editorStyleStatus");
const stylePreviewBtn = document.getElementById("stylePreviewBtn");
const stylePreviewVideo = document.getElementById("stylePreviewVideo");
const stylePreviewStatus = document.getElementById("stylePreviewStatus");
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
const mainColRuntime = document.getElementById("mainColRuntime");
const mainColStyle = document.getElementById("mainColStyle");
const mainLowerDeck = document.getElementById("mainLowerDeck");
const mainHwGroup = document.getElementById("mainHwGroup");
const mainPacingGroup = document.getElementById("mainPacingGroup");
const mainDiarizeGroup = document.getElementById("mainDiarizeGroup");
const mainModelGroup = document.getElementById("mainModelGroup");
const mainStyleGroup = document.getElementById("mainStyleGroup");
const mainStylePresetGrid = document.getElementById("mainStylePresetGrid");
const mainStyleSample = document.getElementById("mainStyleSample");
const mainStyleSampleText = document.getElementById("mainStyleSampleText");
const mainModelPills = document.getElementById("mainModelPills");
const mainDevicePills = document.getElementById("mainDevicePills");
const mainPacingPills = document.getElementById("mainPacingPills");
const mainDiarizePills = document.getElementById("mainDiarizePills");
const mainModelStatusText = document.getElementById("mainModelStatusText");
const mainPreDownloadModelBtn = document.getElementById("mainPreDownloadModelBtn");

const pinModelSwitch = document.getElementById("pinModelSwitch");
const pinHwSwitch = document.getElementById("pinHwSwitch");
const pinPacingSwitch = document.getElementById("pinPacingSwitch");
const pinStyleSwitch = document.getElementById("pinStyleSwitch");
const pinDiarizeSwitch = document.getElementById("pinDiarizeSwitch");

let pinnedModules = {
  model: false,
  hw: false,
  pacing: false,
  diarize: false
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
const captionSync = document.getElementById("captionSync");
const captionSyncValue = document.getElementById("captionSyncValue");
const captionSyncEarlier = document.getElementById("captionSyncEarlier");
const captionSyncLater = document.getElementById("captionSyncLater");
const captionOverlay = document.getElementById("captionOverlay");
const captionText = document.getElementById("captionText");
const captionPill = document.getElementById("captionPill");
const safeZoneMask = document.getElementById("safeZoneMask");
const safeZoneBtn = document.getElementById("safeZoneBtn");
const safeZoneWarning = document.getElementById("safeZoneWarning");
let captionMode = "hinglish";

// Keep these in sync with karaoke_ass.py. They decide which words become gold.
const KINETIC_ACCENT_WORDS = new Set(
  "hey hi hello yo wow yes yeah no nah okay ok oh ah arrey arey oye by".split(/\s+/)
);
const KINETIC_STOPWORDS = new Set(
  `a an the and or but if then so to of in on at by for with from as is are was were be been
  being am do does did have has had i you he she it we they me him her us them my your his its
  our their this that these those there here what which who whom whose when where why how not
  no yes just very too also about into over under again once all any both each few more most
  other some such only own same than now up down out off every each another many much more most
  few several plenty enough really quite rather almost less least lot lots bunch it's i'm you're
  we're they're don't doesn't didn't can't won't isn't aren't wasn't weren't i've you've we've
  they've i'll you'll he'll she'll we'll they'll i'd you'd he'd she'd we'd they'd that's there's
  let's lets ne ko ka ki ke hai hain tha thi the aur par se me mein ek yeh ye wo vo kya nahi nahin
  bhi toh hi na ha ho hua hui hue kar karta karti karte kiya raha rahi rahe gaya gayi gaye liye liya
  diya di de dena lena le lo chalo aao ja jaao sakta sakti sakte chahiye hoga hogi honge mera meri
  mere tera teri tere uska uski uske inka inki inke hamara hamari hamare unka unki unke yahan wahan
  ab phir fir kal aaj roz sab sabse kuch koi kuchh bas sirf bahut zyada kam accha acha`.split(/\s+/)
);
let kineticRenderKey = "";
let kineticStyleKey = "";
let kineticPillKey = "";
let kineticPillTop = null;
let kineticMeasureCtx = null;
let kineticWarningKey = "";

// --------------------------------------------------------------------------
// Caption placement
//
// One POSITION slider drives every style. Kinetic styles store a top anchor
// (`anchor_y`, % of the frame); classic styles store `margin_v` (px above the
// bottom of the PlayRes frame). Both are the same number in disguise, so the
// slider converts through the aspect profile the burn uses.
// --------------------------------------------------------------------------
const STYLE_ASPECT_PROFILES = {
  "9:16": { play_res_y: 1920, margin_scale: 1.0 },
  "16:9": { play_res_y: 1080, margin_scale: 0.375 },
  "1:1": { play_res_y: 1080, margin_scale: 0.46 }
};
// Mirrors the `margin_v` clamp in caption_styles.resolve_style.
const STYLE_MAX_MARGIN = 1600;

function styleIsKinetic(style) {
  return Boolean(style && style.motion === "word-pop");
}

function clampPercent(value, fallback = 50) {
  const num = Number(value);
  if (!Number.isFinite(num)) return fallback;
  return Math.max(0, Math.min(100, num));
}

function styleAspectProfile() {
  return STYLE_ASPECT_PROFILES[detectAspect()] || STYLE_ASPECT_PROFILES["9:16"];
}

// The slider range is the range the burn can actually draw. Classic styles are
// bottom-anchored, so the top of their travel stops where `margin_v` runs out.
function stylePositionRange(style) {
  if (styleIsKinetic(style)) return { min: 0, max: 100 };
  const profile = styleAspectProfile();
  const min = 100 - (STYLE_MAX_MARGIN * profile.margin_scale * 100) / profile.play_res_y;
  return { min: Math.min(100, Math.max(0, Math.round(min * 10) / 10)), max: 100 };
}

function stylePositionValue(style) {
  if (!style) return 88;
  if (styleIsKinetic(style)) return clampPercent(style.anchor_y, 50);
  const profile = styleAspectProfile();
  return clampPercent(
    100 - (Number(style.margin_v || 0) * profile.margin_scale * 100) / profile.play_res_y,
    88
  );
}

// Returns only the fields the active style actually reads, so switching between
// a kinetic and a classic style never leaves the other anchor stale.
function stylePositionPatch(style, percent) {
  const range = stylePositionRange(style);
  const value = Math.min(range.max, Math.max(range.min, Number(percent)));
  if (!Number.isFinite(value)) return {};
  if (styleIsKinetic(style)) return { anchor_y: Math.round(value) };
  const profile = styleAspectProfile();
  return {
    margin_v: Math.min(
      STYLE_MAX_MARGIN,
      Math.round(((100 - value) / 100) * profile.play_res_y / profile.margin_scale)
    )
  };
}

function updateStylePositionReadout() {
  if (!editorStyleMargin || !editorStyleMarginValue) return;
  const value = Number(editorStyleMargin.value);
  const text = Number.isFinite(value) ? `${Math.round(value * 10) / 10}%` : "0%";
  if (editorStyleMarginValue.textContent !== text) editorStyleMarginValue.textContent = text;
  document.querySelectorAll(".position-chip").forEach(chip => {
    const chipVal = Number(chip.dataset.pos);
    chip.classList.toggle("is-active", Math.abs(chipVal - value) < 1.0);
  });
}

// The video's own box inside the stage. The stage also holds the control bar
// and the audio banner, so a percentage of the stage is not the frame the burn
// draws into. Everything anchored to the caption uses this rect.
function videoFrameRect() {
  if (!videoStage || !videoPlayer) return null;
  const stageRect = videoStage.getBoundingClientRect();
  const videoRect = videoPlayer.getBoundingClientRect();
  if (!stageRect.width || !stageRect.height || !videoRect.width || !videoRect.height) return null;
  // Absolutely positioned children are laid out against the padding box, so
  // drop the stage's border before converting to overlay coordinates.
  const borderLeft = videoStage.clientLeft || 0;
  const borderTop = videoStage.clientTop || 0;
  return {
    left: videoRect.left - stageRect.left - borderLeft,
    top: videoRect.top - stageRect.top - borderTop,
    width: videoRect.width,
    height: videoRect.height,
    stageWidth: videoStage.clientWidth || stageRect.width,
    stageHeight: videoStage.clientHeight || stageRect.height
  };
}

// The overlay spans the video picture, not the stage. A portrait clip can be
// narrower than the control bar, and the burn lays text out inside the frame.
// When the picture already fills the stage width, clear the inline pins so the
// stylesheet's per-orientation insets still apply.
function applyCaptionFrameBox(insetPx = 0) {
  if (!captionOverlay) return;
  const frame = videoFrameRect();
  if (!frame) return;
  const leftGap = Math.round(frame.left);
  const rightGap = Math.round(Math.max(0, frame.stageWidth - frame.left - frame.width));
  if (leftGap <= 1 && rightGap <= 1) {
    captionOverlay.style.left = "";
    captionOverlay.style.right = "";
    return;
  }
  captionOverlay.style.left = `${leftGap + insetPx}px`;
  captionOverlay.style.right = `${rightGap + insetPx}px`;
}

// Classic styles are bottom-anchored: the burn puts the block `margin_v *
// margin_scale` px above the bottom of the PlayRes frame. The overlay is
// positioned against the stage, which also holds the control bar, so the gap
// below the video has to be added to the frame's own inset.
function applyClassicBottom(style) {
  if (!captionOverlay || !style || typeof style.margin_v !== "number") return;
  const profile = styleAspectProfile();
  const frame = videoFrameRect();
  if (!frame) {
    captionOverlay.style.bottom = `${Math.max(40, Math.min(140, Math.round(style.margin_v * 0.28)))}px`;
    return;
  }
  const frameInset = frame.height * style.margin_v * profile.margin_scale / profile.play_res_y;
  const belowFrame = Math.max(0, frame.stageHeight - frame.top - frame.height);
  captionOverlay.style.bottom = `${Math.round(belowFrame + frameInset)}px`;
  // 10 px of breathing room inside the picture, as the stylesheet had.
  applyCaptionFrameBox(10);
}

// Kinetic styles anchor the top of the block, in frame pixels for the live
// preview so the burn's `anchor_y` is what the user sees.
function applyKineticTop(state, style) {
  if (!captionOverlay || !style) return;
  const percent = kineticAnchorPercent(state, style);
  const frame = videoFrameRect();
  captionOverlay.style.top = frame
    ? `${(frame.top + frame.height * percent / 100).toFixed(1)}px`
    : `${percent}%`;
}

// Re-derive the placement after a layout change (resize, fullscreen, rotate)
// without rebuilding the caption DOM.
function refreshCaptionTop() {
  if (activeCaptionStyle && captionOverlay) {
    applyCaptionFrameBox(styleIsKinetic(activeCaptionStyle) ? 0 : 10);
    if (styleIsKinetic(activeCaptionStyle)) {
      if (!activeCaptionStyle.pill) {
        applyKineticTop(kineticStateAt(videoPlayer ? videoPlayer.currentTime : 0), activeCaptionStyle);
      }
    } else if (captionOverlay.classList.contains("visible")) {
      applyClassicBottom(activeCaptionStyle);
    }
  }
  syncSafeZoneMask();
}

// Caption playback clock. Every style is driven from the same frame loop so a
// card is painted on the frame its start time passes, not on the video's
// `timeupdate` tick (which only fires ~4x/s and can be a quarter second late).
let captionRaf = null;
let captionFrameHandle = null;
let captionLoopOn = false;
let captionRenderKey = "";
let captionOffsetMs = 0;
let captionBaseSegments = null;

// Recess geometry. The ASS renderer emits a libass-calibrated em; the browser
// needs the real one. libass lays Arial Black out at 0.652x its Pillow advance,
// so matching the line width (and therefore the wrapping and the 82% fill)
// means scaling the emitted em by the same ratio.
const RECESS_LIVE_EM = 0.652;
// Pill padding/radius are authored in the reference type em, which is the
// emitted em scaled by 0.775 (see karaoke_ass._RECESS_PILL_EM_RATIO).
const RECESS_PILL_EM_RATIO = 0.775;
const RECESS_CAP_RATIO = 0.52;
const RECESS_PILL_PAD_X = 0.16;
const RECESS_PILL_PAD_Y = 0.32;
// Arial Black's cap centre sits 0.035 em below the middle of a line-height:1
// box (ascent 1.10, descent 0.31, cap 0.72). Both the block and the pill are
// positioned from it, so the caps land on the video's midline like \an5.
const RECESS_PILL_Y_NUDGE = 0.035;
// Row pitch: the ASS line pitch is 0.915 em, which is one 1 em box plus this.
const RECESS_ROW_GAP = 0.29;

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

const subtitleEditor = document.getElementById("subtitleEditor");
const editorResizer = document.getElementById("editorResizer");
const editorCollapseBtn = document.getElementById("editorCollapseBtn");
const editorExpandBtn = document.getElementById("editorExpandBtn");
const editorRailCount = document.getElementById("editorRailCount");
const editorSegmentCount = document.getElementById("editorSegmentCount");
const editorTabCount = document.getElementById("editorTabCount");
const editorSegmentsTab = document.getElementById("editorSegmentsTab");
const editorStyleTab = document.getElementById("editorStyleTab");
const editorSegmentsPanel = document.getElementById("editorSegmentsPanel");
const editorStylePanel = document.getElementById("editorStylePanel");
const editorSearchInput = document.getElementById("editorSearchInput");
const editorMatchCount = document.getElementById("editorMatchCount");
const editorSegmentList = document.getElementById("editorSegmentList");
const editorSegmentTitle = document.getElementById("editorSegmentTitle");
const editorSegmentTime = document.getElementById("editorSegmentTime");
const editorCaptionInput = document.getElementById("editorCaptionInput");
const editorOriginalText = document.getElementById("editorOriginalText");
const editorStartInput = document.getElementById("editorStartInput");
const editorEndInput = document.getElementById("editorEndInput");
const editorSpeakerInput = document.getElementById("editorSpeakerInput");
const editorSpeakerOptions = document.getElementById("editorSpeakerOptions");
const editorSaveBtn = document.getElementById("editorSaveBtn");
const editorSeekBtn = document.getElementById("editorSeekBtn");
const editorRevertBtn = document.getElementById("editorRevertBtn");

const studioBreadcrumbBar = document.getElementById("studioBreadcrumbBar");
const studioFileChip = document.getElementById("studioFileChip");
const studioModeChip = document.getElementById("studioModeChip");
const studioMetaText = document.getElementById("studioMetaText");
const studioToggleConfigBtn = document.getElementById("studioToggleConfigBtn");

const floatingDownloadBar = document.getElementById("floatingDownloadBar");
const floatingMatchPill = document.getElementById("floatingMatchPill");
const floatingMatchCountText = document.getElementById("floatingMatchCountText");
const floatingCopyAllBtn = document.getElementById("floatingCopyAllBtn");
const floatingCopyAllText = document.getElementById("floatingCopyAllText");
const downloadHinglishBtn = document.getElementById("downloadHinglishBtn");
const downloadAssBtn = document.getElementById("downloadAssBtn");
const burnVideoBtn = document.getElementById("burnVideoBtn");
const overlayVideoBtn = document.getElementById("overlayVideoBtn");
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
  loadCaptionStyles();

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
const mainDiarizeOffBtn = document.getElementById("mainDiarizeOffBtn");
const mainDiarizeOnBtn = document.getElementById("mainDiarizeOnBtn");

function updateDiarizationUI() {
  [
    [diarizeOffBtn, diarizeOnBtn],
    [mainDiarizeOffBtn, mainDiarizeOnBtn]
  ].forEach(([off, on]) => {
    if (!off || !on) return;
    off.classList.toggle("active", !isDiarizationEnabled);
    on.classList.toggle("active", isDiarizationEnabled);
    off.setAttribute("aria-pressed", String(!isDiarizationEnabled));
    on.setAttribute("aria-pressed", String(isDiarizationEnabled));
  });
}

function setDiarization(enabled) {
  isDiarizationEnabled = enabled;
  localStorage.setItem("isDiarizationEnabled", String(enabled));
  updateDiarizationUI();
}

[
  [diarizeOffBtn, false],
  [diarizeOnBtn, true],
  [mainDiarizeOffBtn, false],
  [mainDiarizeOnBtn, true]
].forEach(([button, value]) => {
  if (button) button.addEventListener("click", () => setDiarization(value));
});

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

async function loadCaptionStyles() {
  try {
    const res = await fetch("/api/caption-styles");
    if (!res.ok) return;
    const data = await res.json();
    captionStyles = (data.presets || []).slice();
    defaultCaptionStyleId = data.default || defaultCaptionStyleId;
    captionFonts = data.fonts || [];
    populateStyleFonts();
    if (data.custom && data.custom.id === "custom" && !captionStyles.some(s => s.id === "custom")) {
      captionStyles.push(data.custom);
    }
    // Migrate a saved pre-kinetic Honey Punch selection to the new animated preset.
    if (activeCaptionStyle && activeCaptionStyle.id) {
      const preset = captionStyles.find(s => s.id === activeCaptionStyle.id);
      if (preset && preset.motion === "word-pop" && !activeCaptionStyle.motion) {
        activeCaptionStyle = { ...preset };
      }
    }
    if (!activeCaptionStyle) {
      activeCaptionStyle = captionStyles.find(s => s.id === defaultCaptionStyleId) || captionStyles[0] || null;
    }
    renderCaptionPresets();
    syncStyleEditor();
  } catch (err) {
    console.warn("Could not load caption styles:", err);
  }
}

function populateStyleFonts() {
  if (!editorStyleFont) return;
  editorStyleFont.textContent = "";
  captionFonts.forEach(font => {
    const option = document.createElement("option");
    option.value = font;
    option.textContent = font;
    editorStyleFont.appendChild(option);
  });
}

const STYLE_SHORT_NAMES = {
  hormozi: "Hormozi",
  vox: "Vox",
  cyber: "Cyber",
  blackout: "Blackout",
  editorial: "Editorial",
  buzz: "Buzz",
  medusa: "Medusa",
  cartwheel: "Cartwheel",
  heat: "Heat",
  neon: "Neon",
  magazine: "Magazine",
  techwave: "Techwave",
  minima: "Minima",
  blank: "Blank"
};

function compactStyleName(style) {
  if (style.id === "custom") {
    return style.name && style.name !== "Custom" ? style.name.slice(0, 14) : "Custom";
  }
  return STYLE_SHORT_NAMES[style.id] || style.name;
}

function renderCaptionPresets() {
  renderPresetGrid(stylePresetGrid, false);
  renderPresetGrid(editorStylePresetGrid, false);
  applyCaptionSample();
}

function renderPresetGrid(grid, compact) {
  if (!grid) return;
  grid.textContent = "";
  captionStyles.forEach(style => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = compact ? "style-mini-pill" : "style-preset-btn";
    btn.dataset.styleId = style.id;
    const isActive = !!(activeCaptionStyle && style.id === activeCaptionStyle.id);
    if (isActive) btn.classList.add("active");
    btn.setAttribute("aria-pressed", String(isActive));
    btn.title = style.name;

    const swatch = document.createElement("span");
    swatch.className = compact ? "style-mini-dot" : "style-preset-swatch";
    swatch.style.background = style.box
      ? `linear-gradient(135deg, ${style.back_color} 0 52%, ${style.highlight_color} 52% 100%)`
      : style.highlight_color;

    const name = document.createElement("span");
    name.className = compact ? "style-mini-name" : "style-preset-name";
    name.textContent = compact ? compactStyleName(style) : style.name;

    btn.append(swatch, name);
    btn.addEventListener("click", () => selectCaptionStyle(style));
    grid.appendChild(btn);
  });
}

function selectCaptionStyle(style, { persist = true } = {}) {
  activeCaptionStyle = { ...style };
  renderCaptionPresets();
  syncStyleEditor();
  applyCaptionStyleToVideo();
  updateVideoCaption(true);
  if (persist) saveCaptionStyle(activeCaptionStyle);
}

async function saveCaptionStyle(style) {
  try {
    const fd = new FormData();
    fd.append("caption_style", JSON.stringify(style));
    const res = await fetch("/api/config/preferences", { method: "POST", body: fd });
    if (!res.ok) {
      setEditorStyleStatus("SAVE FAILED", true);
      return false;
    }
    const data = await res.json();
    if (data.preferences && data.preferences.caption_style) {
      activeCaptionStyle = data.preferences.caption_style;
      if (activeCaptionStyle.id === "custom") {
        const idx = captionStyles.findIndex(s => s.id === "custom");
        if (idx >= 0) captionStyles[idx] = activeCaptionStyle;
        else captionStyles.push(activeCaptionStyle);
      }
    }
    renderCaptionPresets();
    syncStyleEditor();
    setEditorStyleStatus("SAVED");
    if (typeof scheduleStylePreview === "function") scheduleStylePreview();
    return true;
  } catch (err) {
    setEditorStyleStatus("SAVE FAILED", true);
    console.warn("Could not save caption style:", err);
    return false;
  }
}

function applyCaptionSample() {
  if (styleSample && styleSampleText) paintCaptionSample(styleSample, styleSampleText, 0.4, 42);
  if (mainStyleSample && mainStyleSampleText) paintCaptionSample(mainStyleSample, mainStyleSampleText, 0.28, 26);
  applyCaptionStyleToVideo();
  updateVideoCaption(true);
}

function kineticWordKey(text) {
  const raw = String(text || "")
    .trim()
    .replace(/^[^\p{L}\p{N}_']+|[^\p{L}\p{N}_']+$/gu, "");
  return raw.toLowerCase().replace(/\u2019/g, "'");
}

function kineticIsAccent(text, mode = "content") {
  if (mode === "all") return true;
  if (mode === "none") return false;
  const raw = String(text || "")
    .trim()
    .replace(/^[^\p{L}\p{N}_']+|[^\p{L}\p{N}_']+$/gu, "");
  const key = kineticWordKey(raw);
  if (!key) return false;
  if (KINETIC_ACCENT_WORDS.has(key)) return true;
  if (KINETIC_STOPWORDS.has(key)) return false;
  return key.length >= 4 || /^[A-Z]/.test(raw);
}

function kineticIsPunch(text, mode = "content") {
  if (mode === "none" || !kineticIsAccent(text, mode)) return false;
  const raw = String(text || "")
    .trim()
    .replace(/^[^\p{L}\p{N}_']+|[^\p{L}\p{N}_']+$/gu, "");
  const key = kineticWordKey(raw);
  if (!key || KINETIC_STOPWORDS.has(key)) return false;
  if (KINETIC_ACCENT_WORDS.has(key) || /^[A-Z]/.test(raw)) return true;
  return key.length >= 5;
}

function kineticIsTitlePhrase(words) {
  return Boolean(
    words && words.length >= 2 &&
    words[0].key === "the" &&
    /^[A-Z]/.test(String(words[1].rawText || "").trim())
  );
}

const KINETIC_SENTENCE_END = /[.?!\u0964]$/;
// Mirrors karaoke_ass._KINETIC_SENTENCE_PAUSE_SEC: a full stop ends a poster
// only when the speaker pauses, or when the ASR card ends on it. Continuous
// delivery mid-card keeps the block together.
const KINETIC_SENTENCE_PAUSE_SEC = 0.2;

// Mirrors karaoke_ass._ends_sentence: a trailing quote or bracket after the
// full stop still closes the sentence.
function kineticEndsSentence(text) {
  const stripped = String(text || "")
    .trim()
    .replace(/["'\u201d\u2019)\]}»]+$/u, "")
    .trim();
  return KINETIC_SENTENCE_END.test(stripped);
}

// Mirrors karaoke_ass._kinetic_lines: greedy wrap plus the reference's forced
// breaks. Returns how many words each rendered line holds, so a poster can be
// split on exactly the line boundary the burn will draw.
function kineticLineWordCounts(words, baseSize, maxWidth, style, scaleOf) {
  const counts = [];
  let count = 0;
  let width = 0;
  words.forEach((word, index) => {
    const size = baseSize * scaleOf(word);
    let advance = kineticAdvance(word.text, size, style.font, style.bold);
    if (advance > maxWidth && maxWidth > 0) advance = maxWidth;
    const space = count ? kineticAdvance(" ", size, style.font, style.bold) : 0;
    if (count && width + space + advance > maxWidth) {
      counts.push(count);
      count = 0;
      width = advance;
    } else {
      width += space + advance;
    }
    count += 1;
    const next = words[index + 1];
    const endsQuestion = /\?$/.test(String(word.text || "").trim());
    const breakBeforeThe =
      Boolean(next) && word.key === "about" && next.key === "the" && index < words.length - 2;
    const breakAfterFirst =
      index === 0 && words.length > 1 && KINETIC_ACCENT_WORDS.has(word.key);
    if (next && (breakAfterFirst || breakBeforeThe || (endsQuestion && index < words.length - 1))) {
      counts.push(count);
      count = 0;
      width = 0;
    }
  });
  if (count) counts.push(count);
  return counts;
}

// The live clock asks for this every frame, and building it classifies every
// word twice with Unicode-property regexes. Cached against the inputs that can
// change it; `captureCaptionBase()` clears it because the editor mutates cards
// in place without swapping the array.
let kineticWordsCache = { segments: null, key: "", words: [] };

function flattenKineticWords() {
  if (!currentSegments || !currentSegments.length) return [];
  const accentMode = (activeCaptionStyle && activeCaptionStyle.accent_mode) || "content";
  const gap = Math.max(0.1, Number(activeCaptionStyle && activeCaptionStyle.phrase_gap_ms || 650) / 1000);
  const rect = videoPlayer ? videoPlayer.getBoundingClientRect() : { width: 456, height: 600 };
  const isPortrait = (rect.height || 600) > (rect.width || 456) * 1.15;
  const grouping = (activeCaptionStyle && activeCaptionStyle.kinetic_grouping) || "flow";
  const posterGrouping = grouping === "poster";
  const configuredMax = Number(activeCaptionStyle && activeCaptionStyle.max_words_per_phrase);
  // Posters are capped by the rendered line count, not by the ASR card rhythm.
  // Keep in step with karaoke_ass._KINETIC_POSTER_MAX_WORDS.
  const maxWords = Math.min(
    (Number.isFinite(configuredMax) && configuredMax > 0) ? configuredMax : 10,
    posterGrouping ? (isPortrait ? 8 : 12) : (isPortrait ? 4 : 20)
  );
  const punchGrouping = grouping === "punch";
  const cacheKey = [captionMode, accentMode, gap, maxWords, grouping, isPortrait].join("|");
  if (kineticWordsCache.segments === currentSegments && kineticWordsCache.key === cacheKey) {
    return kineticWordsCache.words;
  }

  const words = [];
  currentSegments.forEach(segment => {
    const list = Array.isArray(segment.words) ? segment.words : [];
    const cardStart = Number(segment.start) || 0;
    const cardEnd = Number(segment.end) || cardStart + 2;
    list.forEach(word => {
      const rawText = captionMode === "original"
        ? (word.word || word.text || "")
        : (word.hinglish || word.word || word.text || "");
      const text = String(rawText || "").trim();
      if (!text) return;
      const rawStart = Number(word.start);
      const rawEnd = Number(word.end);
      const start = Number.isFinite(rawStart) ? rawStart : cardStart;
      let end = Number.isFinite(rawEnd) ? rawEnd : start + 0.3;
      if (end < start) end = start + 0.3;
      words.push({
        text,
        rawText: text,
        key: kineticWordKey(text),
        accent: kineticIsAccent(text, accentMode),
        punch: kineticIsPunch(text, accentMode),
        start,
        end,
        cardStart,
        cardEnd,
        order: words.length,
        phrase: 0,
        nextStart: end
      });
    });
  });
  words.sort((a, b) => (a.start - b.start) || (a.order - b.order));
  const groups = [];
  let current = [];
  words.forEach((word, index) => {
    if (index > 0) {
      const previous = words[index - 1];
      const wordGap = word.start - previous.end;
      // A poster ignores card boundaries: an ASR card break is not a pause.
      const isTimeGap = posterGrouping
        ? wordGap > gap
        : (wordGap > gap || (word.cardStart - previous.cardEnd) > gap);
      const isMaxWords = current.length >= maxWords;
      // Recess isolates every punch word into its own card and keeps each run
      // of connective words together (see karaoke_ass._group_phrases).
      const isPunchBreak = punchGrouping && Boolean(previous.punch || word.punch);
      const isSentenceEnd =
        posterGrouping &&
        kineticEndsSentence(previous.text) &&
        (wordGap >= KINETIC_SENTENCE_PAUSE_SEC || word.cardStart !== previous.cardStart);
      // A poster's word cap is applied per sentence below, not per card, so a
      // long poster splits evenly instead of leaving a one-word tail.
      if (isPunchBreak || isTimeGap || (isMaxWords && !posterGrouping) || isSentenceEnd) {
        groups.push(current);
        current = [];
      }
    }
    current.push(word);
  });
  if (current.length) groups.push(current);

  // Mirror karaoke_ass._split_overlong_posters: a poster that wraps past the
  // line budget is cut on its own line boundary, so the preview and the burn
  // agree on where one block ends and the next begins.
  if (posterGrouping) {
    const style = activeCaptionStyle || {};
    const punchScale = Number(style.accent_scale || 150) / 100;
    const accentSizeScale = Number(style.accent_size_scale || 100) / 100;
    const scaleOf = word => (word.punch ? punchScale : (word.accent ? accentSizeScale : 1));
    const baseSize = kineticBaseSize(style);
    const lineWidth = Math.max(
      80,
      ((rect.width || 456) * kineticMaxWidthPercent(null, style)) / 100
    );
    const maxLines = isPortrait ? 5 : 4;
    const split = [];
    groups.forEach(group => {
      let pending = group;
      while (pending.length) {
        const counts = kineticLineWordCounts(pending, baseSize, lineWidth, style, scaleOf);
        const fitsWords = maxWords <= 0 || pending.length <= maxWords;
        const fitsLines = counts.length <= maxLines;
        if (fitsWords && fitsLines) {
          split.push(pending);
          break;
        }
        // Two limits: the word cap and the rendered line budget. Cuts are
        // tried at every word boundary and the one closest to an even split
        // wins, so a 14-word run reads 7 + 7 rather than 8 + 6 or 8 + 1.
        const blocks = Math.max(
          1,
          Math.ceil(counts.length / maxLines),
          Math.ceil(pending.length / Math.max(1, maxWords))
        );
        const target = pending.length / blocks;
        let best = null;
        for (let keep = 1; keep < pending.length; keep += 1) {
          if (maxWords > 0 && keep > maxWords) break;
          if (maxLines > 0) {
            const head = pending.slice(0, keep);
            const headLines = kineticLineWordCounts(head, baseSize, lineWidth, style, scaleOf);
            if (headLines.length > maxLines) continue;
          }
          const score = Math.abs(keep - target);
          if (!best || score < best.score || (score === best.score && keep < best.keep)) {
            best = { score, keep };
          }
        }
        if (!best) {
          split.push(pending);
          break;
        }
        split.push(pending.slice(0, best.keep));
        pending = pending.slice(best.keep);
      }
    });
    groups.length = 0;
    split.forEach(group => groups.push(group));
  }

  groups.forEach((group, index) => group.forEach(word => { word.phrase = index; }));
  words.forEach((word, index) => {
    const next = words[index + 1];
    word.nextStart = next && next.phrase === word.phrase ? next.start : word.end;
  });
  // "The Sweet Spot?" is a gold/punch title; plain "the bakery" stays white.
  words.forEach((word, index) => {
    const next = words[index + 1];
    if (word.key === "the" && next && next.phrase === word.phrase && /^[A-Z]/.test(next.rawText)) {
      word.accent = true;
      word.punch = true;
    }
  });
  kineticWordsCache = { segments: currentSegments, key: cacheKey, words };
  return words;
}

function kineticBaseSize(style) {
  const rect = videoPlayer ? videoPlayer.getBoundingClientRect() : { width: 456, height: 600 };
  const height = rect.height || (videoPlayer && videoPlayer.clientHeight) || 600;
  const width = rect.width || (videoPlayer && videoPlayer.clientWidth) || 456;
  const isPortrait = height > width * 1.15;
  if (style && style.pill) {
    // Mirror karaoke_ass._recess_base_em: the emitted em is the style size
    // scaled by kinetic_size_scale, shrunk on portrait canvases, then
    // converted from libass units to a CSS font-size.
    const portrait = isPortrait ? 0.70 * 0.55 : 1;
    const em = Number(style.font_size || 136) * height * portrait / 1600;
    return Math.max(12, Math.min(320, em * Number(style.kinetic_size_scale || 1) * RECESS_LIVE_EM));
  }
  const portraitFactor = isPortrait ? 0.65 : (height > width * 0.9 ? 0.90 : 1);
  return Math.max(16, Math.min(140, Number(style.font_size || 128) * height * portraitFactor / 1600));
}

function kineticMaxWidthPercent(state, style) {
  const rect = videoPlayer ? videoPlayer.getBoundingClientRect() : { width: 456, height: 600 };
  const isPortrait = (rect.height || 600) > (rect.width || 456) * 1.15;
  let percent = Number(style.max_width || 54);
  if (style && style.pill) {
    // Same rule as karaoke_ass._kinetic_max_width.
    return isPortrait ? Math.min(92, percent + 18) : percent;
  }
  // Browser flex metrics run ~4% wider than Pillow's ASS measurement at this
  // weight. Tighten the live landscape box so phrase 1 breaks after "about"
  // instead of pulling "the" onto line 2.
  if (isPortrait) percent = Math.min(92, percent + 26);
  else percent = Math.max(35, percent - 4);
  if (state && state.phraseTitle) percent = Math.min(92, percent + 10);
  return percent;
}

function kineticStateAt(seconds) {
  const words = flattenKineticWords();
  if (!words.length) return null;
  let activeIndex = -1;
  for (let i = 0; i < words.length; i += 1) {
    if (words[i].start <= seconds + 1e-6) activeIndex = i;
    else break;
  }
  if (activeIndex < 0) return null;
  const phraseId = words[activeIndex].phrase;
  const phraseWords = words.filter(word => word.phrase === phraseId);
  if (!phraseWords.length) return null;
  const phraseStart = words.indexOf(phraseWords[0]);
  const last = phraseWords[phraseWords.length - 1];
  const nextPhrase = words.find(word => word.phrase > phraseId);
  const naturalEnd = Math.max(last.end, last.start + 0.35);
  const displayEnd = nextPhrase
    ? Math.min(nextPhrase.start, naturalEnd + 1.30)
    : naturalEnd + 0.30;
  if (seconds > displayEnd) return null;
  return {
    words,
    activeIndex,
    phraseId,
    phraseWords,
    phraseStart,
    phraseTitle: kineticIsTitlePhrase(phraseWords),
    displayEnd
  };
}

function kineticStyleSignature(style) {
  return [
    style.font, style.font_size, style.accent_scale, style.accent_size_scale,
    style.active_scale,
    style.pop_ms, style.settle_ms, style.phrase_gap_ms, style.anchor_y,
    style.max_width, style.kinetic_layout, style.accent_mode,
    style.max_words_per_phrase, style.kinetic_size_scale, style.kinetic_grouping,
    style.pill, style.pill_gradient_start, style.pill_gradient_end,
    style.pill_pad_x, style.pill_pad_y, style.pill_radius, style.pill_alpha,
    style.pill_fade_ms, style.pill_slide_ms, style.reveal_fade_ms,
    style.reveal_spring_ms, style.reveal_spring_scale, captionMode
  ].join("|");
}

function kineticAnchorPercent(state, style) {
  // ASS and the browser distribute the first line's leading differently;
  // nudge the live overlay down 1.5% so the glyph tops line up.
  let percent = Number(style.anchor_y ?? 20) + 1.5;
  // The reference's two-line title sits slightly higher than the normal
  // four-line block. Keep the style anchor as the normal position.
  if (state && state.phraseTitle) percent -= 4.5;
  // No 6..80 window: the slider must reach the same pixel the burn's \pos does.
  return Math.max(0, Math.min(100, percent));
}

function recessCentreTop(em, style, state) {
  // The overlay's containing block also holds the audio banner, so 50% is not
  // the video's centre. Anchor to the style's own anchor_y inside the video
  // box, minus the cap lift - the burn puts the \an5 centre at that percentage.
  if (!style || !captionOverlay) return null;
  const frame = videoFrameRect();
  if (!frame) return null;
  let percent = Number(style.anchor_y ?? 50);
  if (state && state.phraseTitle) percent -= 4.5; // _KINETIC_TITLE_ANCHOR_OFFSET
  const centre = frame.top + frame.height * percent / 100;
  return centre - RECESS_PILL_Y_NUDGE * em;
}

function ensureKineticOverlay(style, state = null) {
  if (!captionOverlay || !captionText) return;
  const captionBox = document.getElementById("captionBox");
  const pill = Boolean(style && style.pill);
  captionOverlay.classList.add("kinetic");
  captionText.classList.add("kinetic");
  captionOverlay.classList.toggle("recess", pill);
  captionText.classList.toggle("recess", pill);
  // Kinetic layouts centre inside the video frame; a classic style may have
  // pinned inline left/right to a narrower box.
  applyCaptionFrameBox(0);
  if (pill) {
    // The Recess CSS centres the block; an inline top/transform would win.
    captionOverlay.style.bottom = "auto";
    const em = kineticBaseSize(style);
    const top = recessCentreTop(em, style, state);
    captionOverlay.style.top = top === null ? "50%" : `${top.toFixed(1)}px`;
    captionText.style.setProperty("--recess-row", `${RECESS_ROW_GAP * em}px`);
    if (captionPill) {
      captionPill.style.backgroundImage =
        `linear-gradient(180deg, ${style.pill_gradient_start || "#D2E860"}, ${style.pill_gradient_end || "#A793FF"})`;
    }
  } else {
    applyKineticTop(state, style);
    captionOverlay.style.bottom = "auto";
    captionText.style.removeProperty("--recess-row");
    if (captionPill) captionPill.style.opacity = "0";
  }
  captionText.style.fontFamily = `"${style.font}", sans-serif`;
  captionText.style.fontWeight = style.bold ? "900" : "700";
  captionText.style.textTransform = style.uppercase ? "uppercase" : "none";
  captionText.style.color = style.base_color || "#FFFFFF";
  captionText.style.lineHeight = pill ? "1" : "1.2";
  if (captionBox) {
    captionBox.style.background = "transparent";
    captionBox.style.border = "none";
    captionBox.style.boxShadow = "none";
    captionBox.style.padding = "0";
    captionBox.style.maxWidth = "100%";
    captionBox.style.width = "100%";
  }
}

function hideRecessPill() {
  if (captionPill) captionPill.style.opacity = "0";
  kineticPillKey = "";
  kineticPillTop = null;
}

function kineticMeasureFont(size, font, bold) {
  if (!kineticMeasureCtx) {
    const canvas = document.createElement("canvas");
    kineticMeasureCtx = canvas.getContext("2d");
  }
  if (!kineticMeasureCtx) return null;
  kineticMeasureCtx.font = `${bold ? 900 : 700} ${Math.max(1, size)}px "${font}", sans-serif`;
  return kineticMeasureCtx;
}

function kineticInkMetrics(text, size, font, bold) {
  const ctx = kineticMeasureFont(size, font, bold);
  if (!ctx) return { left: 0, right: 0, width: Math.max(1, size) };
  const metrics = ctx.measureText(String(text || ""));
  const left = Number(metrics.actualBoundingBoxLeft) || 0;
  const right = Number(metrics.actualBoundingBoxRight) || metrics.width || 0;
  return { left, right, width: Math.max(1, left + right) };
}

// Advance width, i.e. what karaoke_ass._measure_kinetic_text measures for
// line wrapping. Ink bounds are narrower, which would let the overlay keep a
// word that the burn shrinks.
function kineticAdvance(text, size, font, bold) {
  const ctx = kineticMeasureFont(size, font, bold);
  if (!ctx) return Math.max(1, size) * String(text || "").length;
  return ctx.measureText(String(text || "")).width || 0;
}

function kineticOffsetWithin(element, ancestor) {
  // Layout coordinates: offsetLeft/offsetTop ignore the reveal transform, which
  // would otherwise move the pill while a word springs.
  let x = 0;
  let y = 0;
  let node = element;
  while (node && node !== ancestor) {
    x += node.offsetLeft || 0;
    y += node.offsetTop || 0;
    node = node.offsetParent;
  }
  return { x, y };
}

function placeRecessPill(style, state, activeLocal, baseSize) {
  if (!captionPill || !captionText || !captionOverlay) return;
  const span = captionText.querySelectorAll(".kinetic-word")[activeLocal];
  const word = state.phraseWords[activeLocal];
  if (!span || !word) {
    hideRecessPill();
    return;
  }

  const spot = kineticOffsetWithin(span, captionOverlay);
  const punchScale = Number(style.accent_scale || 150) / 100;
  const accentScale = Number(style.accent_size_scale || 100) / 100;
  const wordSize = baseSize * (word.punch ? punchScale : (word.accent ? accentScale : 1));
  const rawLabel = String(span.textContent || "");
  const label = style.uppercase ? rawLabel.toUpperCase() : rawLabel;
  const ink = kineticInkMetrics(label, wordSize, style.font, style.bold);

  // Padding is authored in the emitted em (libass units), so the live overlay
  // has to undo the CSS conversion before applying it.
  const typeEm = baseSize / RECESS_LIVE_EM;
  const padX = RECESS_PILL_PAD_X * RECESS_PILL_EM_RATIO * typeEm;
  const padY = RECESS_PILL_PAD_Y * RECESS_PILL_EM_RATIO * typeEm;
  const radius = Number(style.pill_radius ?? 0.26) * RECESS_PILL_EM_RATIO * typeEm;
  const width = ink.width + padX * 2;
  const height = wordSize * (RECESS_CAP_RATIO / RECESS_LIVE_EM) + padY * 2;
  // The glyph's ink centre, not the advance box, is what the reference hugs.
  const centreX = spot.x + (ink.right - ink.left) / 2;
  const centreY = spot.y + (span.offsetHeight || wordSize) / 2 + wordSize * RECESS_PILL_Y_NUDGE;

  const left = centreX - width / 2;
  const top = centreY - height / 2;

  const key = `${state.phraseId}:${activeLocal}`;
  const moved = key !== kineticPillKey;
  const sameLine = moved && kineticPillTop !== null && Math.abs(spot.y - kineticPillTop) <= 2;
  const fadeMs = Math.max(0, Number(style.pill_fade_ms ?? 65));
  const slideMs = Math.max(0, Number(style.pill_slide_ms ?? 130));
  const alpha = Math.max(0, Math.min(1, Number(style.pill_alpha ?? 1)));

  captionPill.style.left = `${left}px`;
  captionPill.style.top = `${top}px`;
  captionPill.style.width = `${width}px`;
  captionPill.style.height = `${height}px`;
  captionPill.style.borderRadius = `${radius}px`;

  if (moved) {
    if (sameLine && slideMs > 0) {
      // Same line: slide the pill from the previous word to the new one.
      captionPill.style.transition =
        `left ${slideMs}ms cubic-bezier(0.16, 1, 0.3, 1), ` +
        `top ${slideMs}ms cubic-bezier(0.16, 1, 0.3, 1), ` +
        `width ${slideMs}ms cubic-bezier(0.16, 1, 0.3, 1), ` +
        `height ${slideMs}ms cubic-bezier(0.16, 1, 0.3, 1), ` +
        `opacity ${fadeMs}ms linear`;
    } else {
      // New line: jump without sliding, then fade back in.
      captionPill.style.transition = "none";
      captionPill.style.opacity = "0";
      void captionPill.offsetWidth;
      captionPill.style.transition = `opacity ${fadeMs}ms linear`;
    }
    kineticPillKey = key;
    kineticPillTop = spot.y;
  }
  captionPill.style.opacity = String(alpha);
}

function hideKineticCaption() {
  if (captionOverlay) captionOverlay.classList.remove("visible");
  hideRecessPill();
  kineticRenderKey = "";
  kineticWarningKey = "";
  if (safeZoneWarning) safeZoneWarning.hidden = true;
}

function updateKineticCaption() {
  if (!captionOverlay || !captionText || !activeCaptionStyle) return;
  if (captionMode === "off" || !currentSegments || !currentSegments.length) {
    hideKineticCaption();
    return;
  }
  if (activeCaptionStyle.motion !== "word-pop") return;

  const seconds = videoPlayer ? videoPlayer.currentTime : 0;
  const state = kineticStateAt(seconds);
  if (!state) {
    hideKineticCaption();
    return;
  }

  const style = activeCaptionStyle;
  ensureKineticOverlay(style, state);
  const signature = kineticStyleSignature(style);
  if (signature !== kineticStyleKey) {
    kineticStyleKey = signature;
    kineticRenderKey = "";
  }

  const baseSize = kineticBaseSize(style);
  const punchScale = Number(style.accent_scale || 150) / 100;
  const accentScale = Number(style.accent_size_scale || 100) / 100;
  const wordScale = word => (word && word.punch ? punchScale : (word && word.accent ? accentScale : 1));
  const widthPercent = kineticMaxWidthPercent(state, style);
  const rect = videoPlayer ? videoPlayer.getBoundingClientRect() : { width: 456, height: 600 };
  const isPortrait = (rect.height || 600) > (rect.width || 456) * 1.15;
  const layout = style.kinetic_layout || "center";
  // `alternate` follows the reference frames: phrase 1 flush right, phrase 2
  // flush left, 7% in from the edge. `right` keeps older custom styles.
  const alternate = layout === "alternate";
  const flushRight = alternate ? Number(state.phraseId || 0) % 2 === 0 : layout === "right";
  const flushLeft = alternate && !flushRight;
  const alignRight = flushRight;
  captionText.style.fontSize = `${baseSize}px`;
  captionText.style.width = `${widthPercent}%`;
  captionText.style.maxWidth = `${widthPercent}%`;
  let marginLeft = "auto";
  let marginRight = "auto";
  if (alternate) {
    // The overlay is inset 10px from the video on each side, so a CSS
    // percentage would measure the wrong box. Compute the frame-accurate
    // 7% margin in pixels instead.
    const frameWidth = rect.width || 456;
    const overlayWidth = captionOverlay.clientWidth || frameWidth;
    const inset = Math.max(0, (frameWidth - overlayWidth) / 2);
    const flush = `${Math.max(0, frameWidth * 0.07 - inset).toFixed(1)}px`;
    if (flushRight) marginRight = flush;
    else marginLeft = flush;
  } else if (alignRight) {
    // karaoke_ass._kinetic_event_anchor puts `right` at 80% of the frame width
    // (a 20% margin), in every aspect. 8% here put the live text on the pool
    // edge while the burn sat 12% further in.
    marginRight = "20%";
  }
  captionText.style.marginLeft = marginLeft;
  captionText.style.marginRight = marginRight;
  captionText.style.justifyContent = alignRight ? "flex-end" : (flushLeft ? "flex-start" : "center");
  captionText.style.textAlign = alignRight ? "right" : (flushLeft ? "left" : "center");

  const activeLocal = state.activeIndex - state.phraseStart;
  const renderKey = `${state.phraseId}:${signature}`;
  if (renderKey !== kineticRenderKey) {
    captionText.textContent = "";
    state.phraseWords.forEach((word, i) => {
      if (!word) return;
      const span = document.createElement("span");
      span.className = "kinetic-word" +
        (word.accent ? " accent" : "") +
        (word.punch ? " punch" : "");
      span.textContent = word.text;
      span.dataset.start = String(word.start);
      span.dataset.end = String(word.end);
      span.dataset.next = String(word.nextStart);
      captionText.appendChild(span);
      const endsQuestion = /\?$/.test(String(word.text || "").trim());
      const nextWord = state.phraseWords[i + 1];
      const beforeTheAfterAbout =
        word.key === "about" && Boolean(nextWord) && nextWord.key === "the";
      if (
        (i === 0 && state.phraseWords.length > 1 && KINETIC_ACCENT_WORDS.has(word.key)) ||
        beforeTheAfterAbout ||
        (endsQuestion && i < state.phraseWords.length - 1)
      ) {
        const lineBreak = document.createElement("span");
        lineBreak.className = "kinetic-break";
        lineBreak.setAttribute("aria-hidden", "true");
        captionText.appendChild(lineBreak);
      }
    });
    kineticRenderKey = renderKey;
  }

  const spans = captionText.querySelectorAll(".kinetic-word");
  spans.forEach((span, index) => {
    const word = state.phraseWords[index];
    if (!word) return;
    const visible = index <= activeLocal;
    span.style.visibility = visible ? "visible" : "hidden";
    let size = baseSize * wordScale(word);
    if (!style.pill && captionText.clientWidth > 0) {
      // Mirror karaoke_ass._kinetic_lines: a word wider than the line box is
      // shrunk to fit instead of running off the frame.
      const advance = kineticAdvance(word.text, size, style.font, style.bold);
      if (advance > captionText.clientWidth) {
        size *= captionText.clientWidth / advance;
      }
    }
    span.style.fontSize = `${size}px`;
    span.style.color = word.accent
      ? (style.highlight_color || "#F5C844")
      : (style.base_color || "#FFFFFF");
    span.classList.toggle("active", index === activeLocal);
    if (visible && span.dataset.revealed !== "1") {
      span.dataset.revealed = "1";
      if (style.pill && typeof span.animate === "function") {
        const spring = Math.max(60, Number(style.reveal_spring_ms || 130));
        const fadeIn = Math.max(60, Number(style.reveal_fade_ms || 65));
        const from = Number(style.reveal_spring_scale || 1.1);
        span.animate(
          [
            { opacity: 0, transform: `scale(${from})` },
            { opacity: 1, transform: "scale(1)" }
          ],
          {
            duration: Math.max(spring, fadeIn),
            easing: "cubic-bezier(0.16, 1, 0.3, 1)"
          }
        );
      }
    }
  });
  if (style.pill) {
    // Punch words are isolated on their own line, so the tallest word sets the
    // block's em for the cap lift and the pill follows the same centre.
    const blockEm = state.phraseWords.reduce(
      (max, word) => Math.max(max, baseSize * wordScale(word)),
      baseSize
    );
    const top = recessCentreTop(blockEm, style, state);
    if (top !== null) captionOverlay.style.top = `${top.toFixed(1)}px`;
    placeRecessPill(style, state, activeLocal, baseSize);
  } else {
    hideRecessPill();
  }
  captionOverlay.classList.add("visible");
  // Measuring the word boxes forces a layout, so only do it when the visible
  // block changes - not on every frame of the caption clock.
  const warningKey = `${state.phraseId}:${activeLocal}`;
  if (warningKey !== kineticWarningKey) {
    kineticWarningKey = warningKey;
    refreshSafeZoneWarning();
  }
}

// One clock for every style. `requestVideoFrameCallback` fires once per
// presented frame (frame-exact, no drift); rAF is the fallback. Both read
// `video.currentTime`, so seeking and 0.5x/2x playback stay correct.
function scheduleCaptionFrame() {
  if (!captionLoopOn || !videoPlayer) return;
  // Idempotent: `captionTick` calls updateVideoCaption() (which may start the
  // loop) and then schedules again. Without this guard a second callback would
  // be queued every frame and the loop would multiply.
  if (captionRaf !== null || captionFrameHandle !== null) return;
  if (typeof videoPlayer.requestVideoFrameCallback === "function") {
    captionFrameHandle = videoPlayer.requestVideoFrameCallback(captionTick);
  } else {
    captionRaf = requestAnimationFrame(captionTick);
  }
}

function captionTick() {
  captionRaf = null;
  captionFrameHandle = null;
  if (!captionLoopOn) return;
  if (!videoPlayer || videoPlayer.paused || videoPlayer.ended || captionMode === "off") {
    stopCaptionLoop();
    updateVideoCaption(true);
    return;
  }
  updateVideoCaption();
  scheduleCaptionFrame();
}

function startCaptionLoop() {
  if (!videoPlayer || captionMode === "off" || videoPlayer.ended) return;
  if (videoPlayer.paused) return;
  if (captionLoopOn) {
    if (captionRaf === null && captionFrameHandle === null) scheduleCaptionFrame();
    return;
  }
  captionLoopOn = true;
  scheduleCaptionFrame();
}

function stopCaptionLoop() {
  captionLoopOn = false;
  if (captionRaf !== null) {
    cancelAnimationFrame(captionRaf);
    captionRaf = null;
  }
  if (captionFrameHandle !== null) {
    if (typeof videoPlayer.cancelVideoFrameCallback === "function") {
      videoPlayer.cancelVideoFrameCallback(captionFrameHandle);
    }
    captionFrameHandle = null;
  }
}

function applyCaptionStyleToVideo() {
  if (!captionText || !activeCaptionStyle) return;
  const s = activeCaptionStyle;
  const captionBox = document.getElementById("captionBox");
  const isKinetic = s.motion === "word-pop";
  captionOverlay.classList.toggle("kinetic", isKinetic);
  captionText.classList.toggle("kinetic", isKinetic);

  captionText.style.fontFamily = `"${s.font}", sans-serif`;
  captionText.style.fontWeight = s.bold ? "900" : "700";

  const previewSize = Math.max(13, Math.min(32, Math.round((s.font_size || 60) * 0.32)));
  captionText.style.fontSize = `${previewSize}px`;
  captionText.style.color = s.base_color || "#FFFFFF";
  captionText.style.textTransform = s.uppercase ? "uppercase" : "none";

  if (s.box) {
    if (captionBox) {
      captionBox.style.background = s.back_color ? s.back_color : "rgba(0, 0, 0, 0.88)";
      captionBox.style.border = "1px solid rgba(255, 255, 255, 0.18)";
      captionBox.style.boxShadow = "0 2px 10px rgba(0,0,0,0.5)";
      captionBox.style.borderRadius = "8px";
      captionBox.style.padding = "6px 14px";
    }
    captionText.style.textShadow = "none";
  } else {
    if (captionBox) {
      captionBox.style.background = "transparent";
      captionBox.style.border = "none";
      captionBox.style.boxShadow = "none";
      captionBox.style.padding = "4px 8px";
    }
    const outlinePx = Math.max(0, Math.min(6, Math.round((s.outline_width || 0) / 1.5)));
    const shadowPx = Math.max(0, Math.min(8, Math.round(s.shadow || 0)));
    const oc = s.outline_color || "#000000";
    const shadows = [];
    // ASS draws a hard `Shadow` offset in BackColour behind the glyphs, with the
    // outline on top of it. CSS paints the first shadow at the bottom of the
    // stack, so the drop shadow has to come first and must not be blurred: a
    // blurred shadow at preview size smears over the outline and reads as dirt.
    if (shadowPx > 0) {
      const drop = Math.max(1, Math.round(shadowPx * 0.5));
      shadows.push(`${drop}px ${drop}px 0 ${s.back_color || "#00000080"}`);
    }
    if (outlinePx > 0) {
      shadows.push(
        `-${outlinePx}px -${outlinePx}px 0 ${oc}`,
        `${outlinePx}px -${outlinePx}px 0 ${oc}`,
        `-${outlinePx}px ${outlinePx}px 0 ${oc}`,
        `${outlinePx}px ${outlinePx}px 0 ${oc}`
      );
    }
    captionText.style.textShadow = shadows.length ? shadows.join(", ") : "none";
  }

  if (isKinetic) {
    ensureKineticOverlay(s);
    captionText.style.fontSize = `${kineticBaseSize(s)}px`;
    captionText.style.textTransform = s.uppercase ? "uppercase" : "none";
    kineticStyleKey = "";
    kineticRenderKey = "";
    kineticWarningKey = "";
    if (currentSegments && currentSegments.length && captionMode !== "off") {
      updateKineticCaption();
      if (!videoPlayer.paused && !videoPlayer.ended) startCaptionLoop();
    } else {
      hideKineticCaption();
    }
    return;
  }

  captionOverlay.classList.remove("kinetic");
  captionOverlay.classList.remove("recess");
  captionText.classList.remove("kinetic");
  captionText.classList.remove("recess");
  hideRecessPill();
  // Classic fade. The old 150 ms fade sat on top of the playback-clock delay,
  // so text was only half-readable ~75 ms after the card was already late.
  const fadeMs = Math.max(0, Math.min(300, Number(s.reveal_fade_ms ?? 80)));
  captionOverlay.style.setProperty("--caption-fade", `${fadeMs}ms`);
  captionText.style.removeProperty("--recess-row");
  captionOverlay.style.top = "";
  captionText.style.width = "";
  captionText.style.maxWidth = "";
  captionText.style.marginLeft = "";
  captionText.style.marginRight = "";
  captionText.style.justifyContent = "";
  captionText.style.textAlign = "";
  if (captionBox) {
    captionBox.style.width = "";
    captionBox.style.maxWidth = "";
  }

  applyClassicBottom(s);

  applyCaptionWordColors(videoPlayer ? videoPlayer.currentTime : 0);
}

function renderCaptionText(segment, text, currentTime) {
  if (!captionText || !activeCaptionStyle) return;
  const words = Array.isArray(segment.words) ? segment.words : [];
  const tokens = text.trim().split(/\s+/).filter(Boolean);
  if (!words.length || words.length !== tokens.length) {
    captionText.textContent = text.trim();
    return;
  }

  // Match the .ASS \k behaviour: spoken words keep the highlight colour, upcoming words use the base colour.
  const base = activeCaptionStyle.base_color || "#FFFFFF";
  const highlight = activeCaptionStyle.highlight_color || base;
  captionText.textContent = "";
  const fragment = document.createDocumentFragment();

  tokens.forEach((token, index) => {
    const word = words[index] || {};
    const rawStart = word.start;
    const start = Number(rawStart);
    const hasStart = rawStart !== null && rawStart !== undefined && rawStart !== "" && Number.isFinite(start);
    const span = document.createElement("span");
    span.className = "caption-word";
    span.textContent = token;
    if (hasStart) span.dataset.start = String(start);
    span.style.color = hasStart && currentTime >= start ? highlight : base;
    fragment.appendChild(span);
    if (index < tokens.length - 1) fragment.appendChild(document.createTextNode(" "));
  });

  captionText.appendChild(fragment);
}

function applyCaptionWordColors(currentTime) {
  if (!captionText || !activeCaptionStyle) return;
  const base = activeCaptionStyle.base_color || "#FFFFFF";
  const highlight = activeCaptionStyle.highlight_color || base;
  captionText.querySelectorAll(".caption-word").forEach(span => {
    const start = Number.parseFloat(span.dataset.start);
    const spoken = span.dataset.start !== "" && Number.isFinite(start) && currentTime >= start;
    span.style.color = spoken ? highlight : base;
  });
}

function paintCaptionSample(container, textElement, scale, maxSize) {
  if (!container || !textElement || !activeCaptionStyle) return;
  const s = activeCaptionStyle;
  const box = !!s.box;

  container.style.background = box ? s.back_color : "#111827";
  textElement.textContent = "";
  textElement.style.fontFamily = `"${s.font}", sans-serif`;
  textElement.style.fontWeight = s.bold ? "800" : "400";
  textElement.style.fontSize = `${Math.max(12, Math.min(maxSize, Math.round((s.font_size || 60) * scale)))}px`;
  textElement.style.color = s.base_color;
  const outlinePx = Math.max(1, Math.min(6, Math.round((s.outline_width || 3) / 2)));
  textElement.style.textShadow = box ? "none" : `${outlinePx}px ${outlinePx}px 0 ${s.outline_color}`;

  const base = document.createElement("span");
  base.textContent = s.uppercase ? "CAPTION " : "Caption ";
  const highlight = document.createElement("span");
  highlight.textContent = s.uppercase ? "STYLE" : "style";
  highlight.style.color = s.highlight_color;
  textElement.append(base, highlight);
}

function hex6(value) {
  const text = String(value || "");
  return /^#[0-9a-fA-F]{6}/.test(text) ? text.slice(0, 7) : "#FFFFFF";
}

function syncStyleEditor() {
  if (!activeCaptionStyle) return;
  const s = activeCaptionStyle;

  if (editorStyleFont) {
    editorStyleFont.value = s.font;
    editorStyleFontSize.value = s.font_size;
    editorStyleBaseColor.value = hex6(s.base_color);
    editorStyleHighlightColor.value = hex6(s.highlight_color);
    editorStyleOutline.value = s.outline_width;
    const range = stylePositionRange(s);
    editorStyleMargin.min = String(range.min);
    editorStyleMargin.max = String(range.max);
    editorStyleMargin.value = String(stylePositionValue(s));
    updateStylePositionReadout();
    editorStyleUppercase.checked = !!s.uppercase;
    editorStyleBox.checked = !!s.box;
  }
}

function setEditorStyleStatus(message, isError = false) {
  if (!editorStyleStatus) return;
  editorStyleStatus.textContent = message;
  editorStyleStatus.style.color = isError ? "var(--pink)" : "var(--green)";
}

function readEditorStyleEditor(positionChanged = false) {
  const base = activeCaptionStyle || captionStyles[0] || {};
  const draft = {
    ...base,
    id: "custom",
    name: "Custom",
    font: editorStyleFont.value,
    font_size: Number(editorStyleFontSize.value) || 60,
    uppercase: editorStyleUppercase.checked,
    base_color: editorStyleBaseColor.value,
    highlight_color: editorStyleHighlightColor.value,
    outline_width: Number(editorStyleOutline.value),
    box: editorStyleBox.checked
  };
  // Only the slider rewrites the anchor. Touching font or outline must not
  // round-trip the position through the slider and shift a preset by a pixel.
  if (!positionChanged) return draft;
  return Object.assign(draft, stylePositionPatch(draft, Number(editorStyleMargin.value)));
}

function queueEditorStyleSave(event) {
  if (!editorStyleFont || !activeCaptionStyle) return;
  const fromPosition = Boolean(event && event.target === editorStyleMargin);
  const draft = readEditorStyleEditor(fromPosition);
  activeCaptionStyle = draft;
  if (fromPosition) updateStylePositionReadout();
  const idx = captionStyles.findIndex(s => s.id === "custom");
  if (idx >= 0) captionStyles[idx] = draft;
  else captionStyles.push(draft);
  markActiveStyle();
  applyCaptionSample();
  setEditorStyleStatus("SAVING...");
  clearTimeout(editorStyleSaveTimer);
  editorStyleSaveTimer = setTimeout(() => saveCaptionStyle(draft), 400);
}

function markActiveStyle() {
  [stylePresetGrid, editorStylePresetGrid].forEach(grid => {
    if (!grid) return;
    const activeId = activeCaptionStyle && activeCaptionStyle.id;
    grid.querySelectorAll("[data-style-id]").forEach(btn => {
      const isActive = btn.dataset.styleId === activeId;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-pressed", String(isActive));
    });
  });
}

function detectAspect() {
  if (videoPlayer && videoPlayer.videoWidth && videoPlayer.videoHeight) {
    const ratio = videoPlayer.videoWidth / videoPlayer.videoHeight;
    if (ratio > 1.2) return "16:9";
    if (ratio < 0.85) return "9:16";
    return "1:1";
  }
  return selectedPacing === "long" ? "16:9" : "9:16";
}

async function requestStylePreview() {
  if (!activeCaptionStyle || !stylePreviewBtn) return;
  stylePreviewBtn.disabled = true;
  stylePreviewBtn.textContent = "RENDERING...";
  if (stylePreviewStatus) stylePreviewStatus.textContent = "Rendering with libass...";

  try {
    const res = await fetch("/api/preview-style", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ style: activeCaptionStyle, aspect: detectAspect() })
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `HTTP ${res.status}`);
    }
    const blob = await res.blob();
    if (stylePreviewUrl) URL.revokeObjectURL(stylePreviewUrl);
    stylePreviewUrl = URL.createObjectURL(blob);
    if (stylePreviewVideo) {
      stylePreviewVideo.src = stylePreviewUrl;
      stylePreviewVideo.hidden = false;
      stylePreviewVideo.play().catch(() => {});
    }
    if (stylePreviewStatus) stylePreviewStatus.textContent = "RENDERED BY LIBASS — this is the burned look.";
  } catch (err) {
    if (stylePreviewStatus) stylePreviewStatus.textContent = "Preview failed. Check the FFmpeg log.";
    console.warn("Could not render style preview:", err);
  } finally {
    stylePreviewBtn.disabled = false;
    stylePreviewBtn.textContent = "VERIFY RENDER";
  }
}

function scheduleStylePreview() {
  if (!stylePreviewVideo || stylePreviewVideo.hidden) return;
  clearTimeout(stylePreviewTimer);
  stylePreviewTimer = setTimeout(requestStylePreview, 600);
}

if (stylePreviewBtn) {
  stylePreviewBtn.addEventListener("click", requestStylePreview);
}

if (styleEditBtn && styleEditor) {
  styleEditBtn.addEventListener("click", () => {
    if (styleEditor.hasAttribute("hidden")) {
      styleEditor.removeAttribute("hidden");
      styleEditBtn.textContent = "CLOSE EDITOR";
      syncStyleEditor();
    } else {
      styleEditor.setAttribute("hidden", "");
      styleEditBtn.textContent = "EDIT STYLE";
    }
  });
}

if (styleResetBtn) {
  styleResetBtn.addEventListener("click", () => {
    const preset = captionStyles.find(s => s.id === defaultCaptionStyleId) || captionStyles[0];
    if (preset) {
      selectCaptionStyle(preset);
      syncStyleEditor();
    }
  });
}

if (styleExportBtn) {
  styleExportBtn.addEventListener("click", () => {
    if (!activeCaptionStyle) return;
    const blob = new Blob([JSON.stringify(activeCaptionStyle, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "caption-style.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}

if (styleImportBtn && styleImportFile) {
  styleImportBtn.addEventListener("click", () => styleImportFile.click());
  styleImportFile.addEventListener("change", async () => {
    const file = styleImportFile.files && styleImportFile.files[0];
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text());
      selectCaptionStyle({ ...parsed, id: "custom", name: parsed.name || "Custom" });
      if (styleEditor) {
        styleEditor.removeAttribute("hidden");
        if (styleEditBtn) styleEditBtn.textContent = "CLOSE EDITOR";
      }
    } catch (err) {
      alert("Invalid style JSON: " + err.message);
    } finally {
      styleImportFile.value = "";
    }
  });
}

[editorStyleFont, editorStyleFontSize, editorStyleBaseColor, editorStyleHighlightColor, editorStyleOutline, editorStyleMargin, editorStyleUppercase, editorStyleBox].forEach(el => {
  if (!el) return;
  el.addEventListener("input", queueEditorStyleSave);
  el.addEventListener("change", queueEditorStyleSave);
});

if (editorStyleResetBtn) {
  editorStyleResetBtn.addEventListener("click", () => {
    const preset = captionStyles.find(s => s.id === defaultCaptionStyleId) || captionStyles[0];
    if (preset) {
      selectCaptionStyle(preset);
      setEditorStyleStatus("RESET TO DEFAULT");
    }
  });
}

if (editorStyleExportBtn) {
  editorStyleExportBtn.addEventListener("click", () => {
    if (!activeCaptionStyle) return;
    const blob = new Blob([JSON.stringify(activeCaptionStyle, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `caption_style_${activeCaptionStyle.id || "custom"}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setEditorStyleStatus("EXPORTED");
  });
}

if (editorStyleImportBtn && editorStyleImportFile) {
  editorStyleImportBtn.addEventListener("click", () => editorStyleImportFile.click());
  editorStyleImportFile.addEventListener("change", async () => {
    const file = editorStyleImportFile.files && editorStyleImportFile.files[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      selectCaptionStyle({ ...parsed, id: "custom", name: parsed.name || "Custom" }, { persist: false });
      const saved = await saveCaptionStyle(activeCaptionStyle);
      setEditorStyleStatus(saved ? "IMPORTED" : "SAVE FAILED", !saved);
    } catch (err) {
      alert("Invalid style JSON: " + err.message);
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

function syncPinSwitch(button, isOn) {
  if (!button) return;
  button.classList.toggle("on", isOn);
  button.setAttribute("aria-pressed", String(isOn));
  const txt = button.querySelector(".pin-text");
  if (txt) txt.textContent = isOn ? "PINNED" : "PIN TO MAIN";
}

function updateDynamicControlsLayout() {
  if (!mainDynamicControlsWrap || !mainDynamicControlsCard) return;

  // Topic Hints is permanently on the main window (Left Column)
  mainDynamicControlsWrap.style.display = "block";
  if (mainColLeft) mainColLeft.style.display = "flex";

  const hasHw = !!pinnedModules.hw;
  const hasPacing = !!pinnedModules.pacing;
  const hasDiarize = !!pinnedModules.diarize;
  const hasModel = !!pinnedModules.model;

  // Update Switches UI in Settings Drawer
  syncPinSwitch(pinModelSwitch, hasModel);
  syncPinSwitch(pinHwSwitch, hasHw);
  syncPinSwitch(pinPacingSwitch, hasPacing);
  syncPinSwitch(pinDiarizeSwitch, hasDiarize);

  // Left Column items
  if (mainHwGroup) mainHwGroup.style.display = hasHw ? "flex" : "none";
  if (mainPacingGroup) mainPacingGroup.style.display = hasPacing ? "flex" : "none";
  if (mainDiarizeGroup) mainDiarizeGroup.style.display = hasDiarize ? "flex" : "none";

  const mainTopicHintGroup = document.getElementById("mainTopicHintGroup");
  if (mainTopicHintGroup) {
    const hasAnyLeftPinned = hasHw || hasPacing || hasDiarize;
    mainTopicHintGroup.style.marginTop = hasAnyLeftPinned ? "auto" : "0px";
    mainTopicHintGroup.style.paddingTop = hasAnyLeftPinned ? "14px" : "0px";
  }

  // Right Column (Model Switcher)
  if (mainColRight) mainColRight.style.display = hasModel ? "flex" : "none";
  if (mainModelGroup) mainModelGroup.style.display = hasModel ? "flex" : "none";

  // Grid columns: 1 column if model is unpinned, 2 columns if model is pinned
  if (hasModel) {
    mainDynamicControlsCard.classList.remove("cols-1");
    mainDynamicControlsCard.classList.add("cols-2");
  } else {
    mainDynamicControlsCard.classList.remove("cols-2");
    mainDynamicControlsCard.classList.add("cols-1");
  }
}

function initPinSwitches() {
  loadPinnedControls();
  updateDynamicControlsLayout();

  [
    [pinModelSwitch, "model"],
    [pinHwSwitch, "hw"],
    [pinPacingSwitch, "pacing"],
    [pinDiarizeSwitch, "diarize"]
  ].forEach(([button, key]) => {
    if (!button) return;
    button.addEventListener("click", () => {
      pinnedModules[key] = !pinnedModules[key];
      savePinnedControls();
      updateDynamicControlsLayout();
    });
  });
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
    safeZoneOn = false;
    syncSafeZoneMask();
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
    safeZoneOn = true;
  } else if (w === h) {
    videoPlayer.classList.add("video-square");
    safeZoneOn = false;
  } else {
    videoPlayer.classList.add("video-landscape");
    safeZoneOn = false;
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
  refreshCaptionTop();
  syncSafeZoneMask();
  // The slider range depends on the aspect the burn will use, so a new clip
  // can widen or narrow it. Re-read it while the editor may be open.
  syncStyleEditor();
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

// Binary search: segments are sorted and non-overlapping. Much cheaper than a
// linear scan once a long video has thousands of cards.
function activeCardIndexAt(seconds) {
  const segs = currentSegments;
  if (!segs || segs.length === 0) return -1;
  let lo = 0;
  let hi = segs.length - 1;
  let best = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (segs[mid].start <= seconds) {
      best = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  if (best < 0) return -1;
  return seconds <= segs[best].end ? best : -1;
}

function hideCaptionOverlay() {
  if (captionRenderKey === "hidden") return;
  captionRenderKey = "hidden";
  captionOverlay.classList.remove("visible");
  if (safeZoneWarning) safeZoneWarning.hidden = true;
}

// --------------------------------------------------------------------------
// 9:16 safe zones (TikTok / Reels / Shorts)
//
// Approximate platform chrome as a share of the frame: the top tab bar, the
// bottom profile / caption / sound rail, and the right like-comment-share rail.
// These are constants, not measurements, so they are drawn with their names on.
// --------------------------------------------------------------------------
const SAFE_ZONE_PRESETS = {
  universal: { name: "Universal", top: 11.5, bottom: 23.5, right: 15.2 },
  reels:     { name: "Instagram Reels", top: 11.5, bottom: 23.4, right: 11.1 },
  shorts:    { name: "YouTube Shorts", top: 6.3, bottom: 15.6, right: 4.4 },
  off:       { name: "Off", top: 0, bottom: 0, right: 0 }
};
const SAFE_ZONE_TOP = 11.5;
const SAFE_ZONE_BOTTOM = 23.5;
const SAFE_ZONE_RIGHT = 15.2;
let currentSafeZonePreset = "universal";
let safeZoneOn = true;

function activeSafeZonePreset() {
  return SAFE_ZONE_PRESETS[currentSafeZonePreset] || SAFE_ZONE_PRESETS.universal;
}

// Pure geometry so the rules can be tested without a layout engine. `block`
// and `frame` are stage-relative boxes; only the overlap decides a hit.
function safeZoneCollisions(block, frame) {
  if (!block || !frame || currentSafeZonePreset === "off") return [];
  const width = frame.right - frame.left;
  const height = frame.bottom - frame.top;
  if (!(width > 0) || !(height > 0)) return [];
  const preset = activeSafeZonePreset();
  const hits = [];
  const topEdge = frame.top + height * preset.top / 100;
  const bottomEdge = frame.bottom - height * preset.bottom / 100;
  const rightEdge = frame.right - width * preset.right / 100;
  if (block.top < topEdge && block.bottom > frame.top) hits.push("top bar");
  if (block.bottom > bottomEdge && block.top < frame.bottom) hits.push("bottom rail");
  // The action rail runs between the top bar and the bottom rail, so a
  // caption in the top-right corner is not also under the like buttons.
  if (
    block.right > rightEdge &&
    block.left < frame.right &&
    block.bottom > topEdge &&
    block.top < bottomEdge
  ) {
    hits.push("action rail");
  }
  return hits;
}

// The painted words, not the overlay / text box: a centred phrase leaves most
// of its box empty, and a box-sized warning would fire on every frame.
function captionBlockBox() {
  if (!captionOverlay || !videoStage || !captionOverlay.classList.contains("visible")) return null;
  const stageRect = videoStage.getBoundingClientRect();
  const borderLeft = videoStage.clientLeft || 0;
  const borderTop = videoStage.clientTop || 0;
  let left = Infinity;
  let top = Infinity;
  let right = -Infinity;
  let bottom = -Infinity;
  const words = captionText ? captionText.querySelectorAll(".kinetic-word") : [];
  words.forEach(word => {
    // Hidden words still occupy a box; the guide is about painted ink.
    if (word.style && word.style.visibility === "hidden") return;
    const r = word.getBoundingClientRect();
    if (!r.width || !r.height) return;
    left = Math.min(left, r.left);
    top = Math.min(top, r.top);
    right = Math.max(right, r.right);
    bottom = Math.max(bottom, r.bottom);
  });
  if (!Number.isFinite(left)) {
    const el = captionText || document.getElementById("captionBox");
    if (!el) return null;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return null;
    left = r.left;
    top = r.top;
    right = r.right;
    bottom = r.bottom;
  }
  return {
    left: left - stageRect.left - borderLeft,
    top: top - stageRect.top - borderTop,
    right: right - stageRect.left - borderLeft,
    bottom: bottom - stageRect.top - borderTop
  };
}

function safeZoneFrameBox() {
  const frame = videoFrameRect();
  if (!frame) return null;
  return {
    left: frame.left,
    top: frame.top,
    right: frame.left + frame.width,
    bottom: frame.top + frame.height
  };
}

function refreshSafeZoneWarning() {
  if (!safeZoneWarning) return;
  if (!safeZoneOn) {
    safeZoneWarning.hidden = true;
    return;
  }
  const hits = safeZoneCollisions(captionBlockBox(), safeZoneFrameBox());
  if (!hits.length) {
    safeZoneWarning.hidden = true;
    return;
  }
  const text = `CAPTION IN ${hits.join(" + ").toUpperCase()}`;
  if (safeZoneWarning.textContent !== text) safeZoneWarning.textContent = text;
  safeZoneWarning.hidden = false;
}

function syncSafeZoneMask() {
  const stageSafePill = document.getElementById("stageSafePill");
  const portrait = Boolean(videoPlayer && videoPlayer.classList.contains("video-portrait"));
  if (stageSafePill) {
    stageSafePill.style.display = portrait ? "flex" : "none";
  }
  document.querySelectorAll(".stage-safe-chip").forEach(chip => {
    const active = chip.dataset.preset === currentSafeZonePreset;
    chip.classList.toggle("is-active", active);
    chip.setAttribute("aria-pressed", String(active));
  });
  if (!safeZoneMask) return;
  const frame = portrait ? videoFrameRect() : null;
  const isOff = (currentSafeZonePreset === "off" || !safeZoneOn);
  if (safeZoneBtn) {
    safeZoneBtn.disabled = !portrait;
    safeZoneBtn.classList.toggle("is-active", !isOff && portrait);
    safeZoneBtn.setAttribute("aria-pressed", String(!isOff && portrait));
  }
  if (isOff || !frame) {
    safeZoneMask.classList.remove("visible");
    if (safeZoneWarning) safeZoneWarning.hidden = true;
    return;
  }
  const preset = activeSafeZonePreset();
  // A 4.4% rail is too narrow for "ACTION RAIL" set horizontally: the label
  // spills over the picture. Set it vertically so it stays inside its band.
  safeZoneMask.classList.toggle("is-narrow", preset.right < 8);
  const topBand = document.getElementById("safeZoneTop");
  const bottomBand = document.getElementById("safeZoneBottom");
  const rightBand = document.getElementById("safeZoneRight");
  if (topBand) topBand.style.height = `${preset.top}%`;
  if (bottomBand) bottomBand.style.height = `${preset.bottom}%`;
  if (rightBand) {
    rightBand.style.top = `${preset.top}%`;
    rightBand.style.bottom = `${preset.bottom}%`;
    rightBand.style.width = `${preset.right}%`;
  }
  safeZoneMask.style.left = `${frame.left}px`;
  safeZoneMask.style.top = `${frame.top}px`;
  safeZoneMask.style.width = `${frame.width}px`;
  safeZoneMask.style.height = `${frame.height}px`;
  safeZoneMask.classList.add("visible");
  refreshSafeZoneWarning();
}

// `force` re-renders even when the playhead is still inside the same card: used
// by seek/style/mode changes, not by the frame loop.
function updateVideoCaption(force) {
  if (!captionOverlay || !captionText) return;

  if (captionMode === "off" || !currentSegments || currentSegments.length === 0) {
    hideCaptionOverlay();
    stopCaptionLoop();
    return;
  }

  if (activeCaptionStyle && activeCaptionStyle.motion === "word-pop") {
    captionRenderKey = "";
    updateKineticCaption();
    startCaptionLoop();
    return;
  }

  const curTime = videoPlayer.currentTime;
  const idx = activeCardIndexAt(curTime);
  if (idx < 0) {
    hideCaptionOverlay();
    return;
  }
  const activeSeg = currentSegments[idx];
  const text = captionMode === "original" ? (activeSeg.original_text || "") : (activeSeg.hinglish_text || "");
  if (!text.trim()) {
    hideCaptionOverlay();
    return;
  }

  // Only rebuild the card's DOM when the card itself changes. Every other frame
  // just recolours the existing spans, which is what keeps a 60 Hz tick cheap.
  const cardKey = `${idx}|${captionMode}|${activeSeg.start}|${text.length}`;
  if (force || cardKey !== captionRenderKey) {
    renderCaptionText(activeSeg, text, curTime);
    applyCaptionStyleToVideo();
    captionOverlay.classList.add("visible");
    captionRenderKey = cardKey;
    refreshSafeZoneWarning();
  } else {
    applyCaptionWordColors(curTime);
  }
}

videoPlayer.addEventListener("timeupdate", () => updateVideoCaption());
videoPlayer.addEventListener("seeked", () => updateVideoCaption(true));
videoPlayer.addEventListener("seeking", () => updateVideoCaption(true));
videoPlayer.addEventListener("ratechange", () => updateVideoCaption(true));

// --------------------------------------------------------------------------
// Per-clip sync nudge
//
// One number, applied once to the card timeline, so the live preview, the
// .ASS export, the .SRT rebuild and the burn can never drift apart. ±500 ms
// in 20 ms steps is enough to fix a clip without creating new problems.
// --------------------------------------------------------------------------
const CAPTION_OFFSET_STEP = 20;
const CAPTION_OFFSET_LIMIT = 500;

function roundCaptionTime(value) {
  return Math.round(Number(value || 0) * 1000) / 1000;
}

// Move one card and its words by `delta` seconds, never past 0.
function shiftSegmentTimes(seg, delta) {
  const start = Math.max(0, Number(seg.start || 0) + delta);
  const end = Math.max(start + 0.05, Number(seg.end || start) + delta);
  const words = (seg.words || []).map((word) => {
    const ws = Math.max(0, Number(word.start ?? start) + delta);
    const we = Math.max(ws + 0.02, Number(word.end ?? ws) + delta);
    return { ...word, start: roundCaptionTime(ws), end: roundCaptionTime(we) };
  });
  return {
    ...seg,
    start: roundCaptionTime(start),
    end: roundCaptionTime(end),
    start_str: srtTimestamp(start),
    end_str: srtTimestamp(end),
    words,
  };
}

function renderCaptionSyncLabel() {
  if (!captionSyncValue) return;
  const sign = captionOffsetMs > 0 ? "+" : (captionOffsetMs < 0 ? "−" : "");
  captionSyncValue.textContent = `${sign}${Math.abs(captionOffsetMs)} ms`;
  captionSyncValue.classList.toggle("active", captionOffsetMs !== 0);
}

// The editor edits the shifted timeline, so re-derive the unshifted source of
// truth before the next nudge, otherwise a nudge would undo the edit.
function captureCaptionBase() {
  // The editor mutates cards in place, so identity alone would keep a stale
  // kinetic word list.
  kineticWordsCache.segments = null;
  if (!captionBaseSegments) return;
  const delta = -captionOffsetMs / 1000;
  captionBaseSegments = currentSegments.map((seg) => shiftSegmentTimes(seg, delta));
}

function setCaptionOffset(ms, { persist = false } = {}) {
  const stepped = Math.round(Number(ms || 0) / CAPTION_OFFSET_STEP) * CAPTION_OFFSET_STEP;
  captionOffsetMs = Math.max(-CAPTION_OFFSET_LIMIT, Math.min(CAPTION_OFFSET_LIMIT, stepped));

  if (captionBaseSegments) {
    const delta = captionOffsetMs / 1000;
    currentSegments = captionBaseSegments.map((seg) => shiftSegmentTimes(seg, delta));
  }

  captionRenderKey = "";
  renderCaptionSyncLabel();
  updateVideoCaption(true);
  if (currentSegments.length) renderEditorList();
  if (persist) {
    try {
      localStorage.setItem("hinglish.captionOffsetMs", String(captionOffsetMs));
    } catch (err) { /* private mode: keep the value for this session only */ }
  }
}

function nudgeCaptionOffset(deltaMs) {
  setCaptionOffset(captionOffsetMs + deltaMs, { persist: true });
}

if (captionSyncEarlier) captionSyncEarlier.addEventListener("click", () => nudgeCaptionOffset(-CAPTION_OFFSET_STEP));
if (captionSyncLater) captionSyncLater.addEventListener("click", () => nudgeCaptionOffset(CAPTION_OFFSET_STEP));

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
  closeSubtitleEditor();
  if (editorSearchInput) editorSearchInput.value = "";
  editorSearchQuery = "";
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
  if (captionSync) {
    captionSync.style.display = "none";
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
  startCaptionLoop();
  updateVideoCaption(true);
});

videoPlayer.addEventListener("pause", () => {
  updatePlayPauseBtnState();
  stopCaptionLoop();
  updateVideoCaption(true);
});

videoPlayer.addEventListener("ended", () => {
  updatePlayPauseBtnState();
  stopCaptionLoop();
  updateVideoCaption(true);
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
    // The stage changes size when it becomes the fullscreen element.
    refreshCaptionTop();
  syncSafeZoneMask();
  });
}

document.querySelectorAll(".position-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    if (!editorStyleMargin || !activeCaptionStyle) return;
    const target = Number(chip.dataset.pos);
    if (!Number.isFinite(target)) return;
    const range = stylePositionRange(activeCaptionStyle);
    const clamped = Math.max(range.min, Math.min(range.max, target));
    editorStyleMargin.value = String(clamped);
    editorStyleMargin.dispatchEvent(new Event("input", { bubbles: true }));
  });
});

document.querySelectorAll(".stage-safe-chip").forEach(chip => {
  chip.addEventListener("click", (e) => {
    e.stopPropagation();
    const preset = chip.dataset.preset;
    if (preset && SAFE_ZONE_PRESETS[preset]) {
      currentSafeZonePreset = preset;
      safeZoneOn = (preset !== "off");
      syncSafeZoneMask();
    }
  });
});

if (safeZoneBtn) {
  safeZoneBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    safeZoneOn = !safeZoneOn;
    syncSafeZoneMask();
  });
}

// The picture box changes on window resize, fullscreen, and when the editor
// panel is dragged wider. A window listener misses that last one, so observe
// the stage itself; fall back to the window event where the API is absent.
if (videoStage && typeof ResizeObserver !== "undefined") {
  new ResizeObserver(refreshCaptionTop).observe(videoStage);
} else if (typeof window !== "undefined" && window.addEventListener) {
  window.addEventListener("resize", refreshCaptionTop);
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
    // Keep an untouched copy of the timeline so the sync nudge can be applied
    // (and undone) without re-transcribing.
    captionBaseSegments = (data.segments || []).map((seg) => ({
      ...seg,
      words: (seg.words || []).map((word) => ({ ...word })),
    }));
    let savedOffset = 0;
    try {
      savedOffset = Number(localStorage.getItem("hinglish.captionOffsetMs") || 0) || 0;
    } catch (err) { savedOffset = 0; }
    setCaptionOffset(savedOffset);

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
  if (captionSync) {
    captionSync.style.display = currentSegments.length > 0 ? "flex" : "none";
    renderCaptionSyncLabel();
  }
  updateDownloadButtonsLabels();
  updateVideoCaption(true);

  setSegmentsCollapsed(false);
  if (floatingSearchInput) floatingSearchInput.value = "";
  updateFloatingMatchPill(currentSegments.length, currentSegments.length, false);
  renderCards(currentSegments);
  updateStudioBreadcrumb();
  openSubtitleEditor();
}

function updateStudioBreadcrumb() {
  if (!studioBreadcrumbBar) return;
  if (studioFileChip) {
    studioFileChip.textContent = `🎬 ${currentFile ? currentFile.name : "video.mp4"}`;
  }
  if (studioModeChip) {
    const langLabelMap = {
      "mixed": "Mixed Hinglish",
      "hi": "Pure Hindi",
      "hi-en": "Hindi ➔ English",
      "en": "English",
      "auto": "Auto-Detect"
    };
    studioModeChip.textContent = langLabelMap[selectedLanguage] || "Hinglish";
  }
  if (studioMetaText) {
    const modelLabel = (selectedModel || "medium").toUpperCase();
    studioMetaText.textContent = `${modelLabel} • ${currentSegments ? currentSegments.length : 0} Segments`;
  }
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

    // Select the segment in the left editor (except copy button)
    card.addEventListener("click", (e) => {
      if (e.target.closest(".copy-btn")) return;
      if (subtitleEditor && subtitleEditor.hidden) openSubtitleEditor();
      setEditorCollapsed(false, { persist: true, focus: false });
      selectEditorSegment(seg.index, { seek: true, focus: true });
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

// Global keyboard shortcuts: '/' to focus bottom search, 'Escape' to collapse editor, ',' to open settings
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
    } else if (subtitleEditor && !subtitleEditor.hidden && !subtitleEditor.classList.contains("is-collapsed")) {
      setEditorCollapsed(true);
    }
  }
});

// --------------------------------------------------------------------------
// Studio Settings Slide-over Drawer (Option 1)
// --------------------------------------------------------------------------
function openSettingsDrawer() {
  if (settingsDrawer && settingsDrawerOverlay) {
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
// 7. Collapsible Subtitle Editor (Segments + Global Style)
// --------------------------------------------------------------------------
function srtTimestamp(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  const totalMs = Math.round(safe * 1000);
  const ms = totalMs % 1000;
  const totalSecs = Math.floor(totalMs / 1000);
  const secs = totalSecs % 60;
  const totalMins = Math.floor(totalSecs / 60);
  const mins = totalMins % 60;
  const hrs = Math.floor(totalMins / 60);
  const pad = (value, width = 2) => String(value).padStart(width, "0");
  return `${pad(hrs)}:${pad(mins)}:${pad(secs)},${pad(ms, 3)}`;
}

function shortClock(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  const total = Math.floor(safe);
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function editorFilteredSegments() {
  const query = editorSearchQuery.toLowerCase().trim();
  if (!query) return currentSegments;
  return currentSegments.filter(seg =>
    (seg.hinglish_text || "").toLowerCase().includes(query) ||
    (seg.original_text || "").toLowerCase().includes(query) ||
    (seg.speaker || "").toLowerCase().includes(query)
  );
}

function updateEditorDirtyState() {
  if (!editorSaveBtn) return;
  editorSaveBtn.disabled = !editorDirty;
  editorSaveBtn.textContent = editorDirty ? "SAVE CHANGES" : "NO CHANGES";
  if (editorRevertBtn) editorRevertBtn.disabled = !editorDirty;
}

function markEditorDirty() {
  if (!editorDirty) {
    editorDirty = true;
    updateEditorDirtyState();
  }
}

function renderEditorSpeakerOptions() {
  if (!editorSpeakerOptions) return;
  const speakers = [...new Set(currentSegments.map(seg => seg.speaker).filter(Boolean))];
  editorSpeakerOptions.textContent = "";
  speakers.forEach(speaker => {
    const option = document.createElement("option");
    option.value = speaker;
    editorSpeakerOptions.appendChild(option);
  });
}

function renderEditorList() {
  if (!editorSegmentList) return;
  const items = editorFilteredSegments();
  const total = currentSegments.length;
  if (editorMatchCount) editorMatchCount.textContent = `${items.length} / ${total}`;
  if (editorSegmentCount) editorSegmentCount.textContent = String(total);
  if (editorTabCount) editorTabCount.textContent = String(total);
  if (editorRailCount) editorRailCount.textContent = String(total);

  editorSegmentList.textContent = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "editor-segment-empty";
    empty.textContent = total ? "No segments match this search." : "Generate captions to start editing.";
    editorSegmentList.appendChild(empty);
    return;
  }

  items.forEach(seg => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "editor-segment-row";
    row.dataset.segmentId = String(seg.index);
    row.setAttribute("role", "option");
    row.setAttribute("aria-selected", String(seg.index === activeSegmentIndex));

    const speaker = seg.speaker ? `<span class="editor-row-speaker">${escapeHtml(seg.speaker)}</span>` : "";
    row.innerHTML = `
      <span class="editor-row-index">#${seg.index}</span>
      <span class="editor-row-copy">
        <span class="editor-row-text">${escapeHtml(seg.hinglish_text || seg.original_text || "—")}</span>
        <span class="editor-row-meta">${speaker}<span>${escapeHtml(seg.start_str || "")}</span></span>
      </span>
      <span class="editor-row-time">${shortClock(seg.start)}</span>
    `;
    row.addEventListener("click", () => selectEditorSegment(seg.index, { seek: true }));
    editorSegmentList.appendChild(row);
  });
}

function fillEditor(seg) {
  if (!editorCaptionInput) return;
  if (!seg) {
    editorSegmentTitle.textContent = "NO SEGMENT SELECTED";
    editorSegmentTime.textContent = "—";
    editorOriginalText.textContent = "—";
    editorCaptionInput.value = "";
    editorStartInput.value = "";
    editorEndInput.value = "";
    editorSpeakerInput.value = "";
    editorDirty = false;
    updateEditorDirtyState();
    return;
  }

  activeSegmentIndex = seg.index;
  editorSegmentTitle.textContent = `SEGMENT #${seg.index}`;
  editorSegmentTime.textContent = `${seg.start_str} → ${seg.end_str}`;
  editorSegmentTime.style.color = "var(--green)";
  editorOriginalText.textContent = seg.original_text || "—";
  editorCaptionInput.value = seg.hinglish_text || "";
  editorStartInput.value = Number(seg.start || 0).toFixed(2);
  editorEndInput.value = Number(seg.end || 0).toFixed(2);
  editorSpeakerInput.value = seg.speaker || "";
  editorDirty = false;
  updateEditorDirtyState();
}

function selectEditorSegment(index, { seek = false, focus = false } = {}) {
  const seg = currentSegments.find(item => item.index === index);
  if (!seg) return;
  activeSegmentIndex = seg.index;
  fillEditor(seg);
  renderEditorList();

  const activeRow = editorSegmentList && editorSegmentList.querySelector(`[data-segment-id="${seg.index}"]`);
  if (activeRow) activeRow.scrollIntoView({ block: "nearest" });

  if (seek && videoPlayer && videoPlayer.src) {
    videoPlayer.currentTime = seg.start;
    updateVideoCaption();
  }
  if (focus && editorCaptionInput) editorCaptionInput.focus();
}

function refreshResultsAfterEditorChange() {
  captureCaptionBase();
  handleSubtitleSearch(floatingSearchInput ? floatingSearchInput.value : "");
  updateVideoCaption(true);
}

function saveEditorSegment() {
  if (activeSegmentIndex === null) return;
  const seg = currentSegments.find(item => item.index === activeSegmentIndex);
  if (!seg) return;

  const start = Number(editorStartInput.value);
  const end = Number(editorEndInput.value);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
    editorSegmentTime.textContent = "CHECK TIMING — END MUST BE AFTER START";
    editorSegmentTime.style.color = "var(--pink)";
    return;
  }

  const previousSpeaker = seg.speaker || "";
  const nextSpeaker = editorSpeakerInput.value.trim();
  let nextText = editorCaptionInput.value.trim();
  let nextOriginal = seg.original_text || "";
  const previousPrefix = previousSpeaker ? `[${previousSpeaker}]: ` : "";

  if (previousSpeaker !== nextSpeaker) {
    if (previousPrefix && nextText.startsWith(previousPrefix)) nextText = nextText.slice(previousPrefix.length);
    if (previousPrefix && nextOriginal.startsWith(previousPrefix)) nextOriginal = nextOriginal.slice(previousPrefix.length);
    if (nextSpeaker) {
      if (nextText && !nextText.startsWith(`[${nextSpeaker}]:`)) nextText = `[${nextSpeaker}]: ${nextText}`;
      if (nextOriginal && !nextOriginal.startsWith(`[${nextSpeaker}]:`)) nextOriginal = `[${nextSpeaker}]: ${nextOriginal}`;
    }
  }

  seg.hinglish_text = nextText;
  seg.original_text = nextOriginal;
  seg.start = start;
  seg.end = end;
  seg.start_str = srtTimestamp(start);
  seg.end_str = srtTimestamp(end);
  if (nextSpeaker) seg.speaker = nextSpeaker;
  else delete seg.speaker;

  editorDirty = false;
  updateEditorDirtyState();
  renderEditorSpeakerOptions();
  refreshResultsAfterEditorChange();
  fillEditor(seg);
  renderEditorList();
  editorSaveBtn.textContent = "SAVED!";
  setTimeout(updateEditorDirtyState, 900);
}

function openSubtitleEditor() {
  if (!subtitleEditor) return;
  subtitleEditor.hidden = false;
  if (editorResizer) editorResizer.hidden = window.innerWidth <= 900;
  document.body.classList.add("editor-open");

  let collapsed = false;
  try {
    const stored = localStorage.getItem("subtitle_editor_collapsed");
    if (stored !== null) {
      collapsed = stored === "true";
    } else if (window.innerWidth <= 900) {
      collapsed = true;
    }
  } catch (_) {}
  setEditorCollapsed(collapsed, { persist: false, focus: false });

  // Restore saved width
  try {
    const savedW = localStorage.getItem("subtitle_editor_width");
    if (savedW && Number(savedW) >= 320 && Number(savedW) <= 800) {
      document.documentElement.style.setProperty("--editor-width", `${savedW}px`);
      if (editorResizer && !collapsed) editorResizer.style.left = `${savedW}px`;
    }
  } catch (_) {}

  renderEditorSpeakerOptions();
  renderEditorList();

  if (currentSegments.length) {
    const keepActive = currentSegments.some(seg => seg.index === activeSegmentIndex);
    selectEditorSegment(keepActive ? activeSegmentIndex : currentSegments[0].index, { seek: false });
  } else {
    fillEditor(null);
    renderEditorList();
  }
}

function closeSubtitleEditor() {
  if (!subtitleEditor) return;
  subtitleEditor.hidden = true;
  if (editorResizer) editorResizer.hidden = true;
  document.body.classList.remove("editor-open", "editor-collapsed", "setup-expanded");
  if (studioToggleConfigBtn) studioToggleConfigBtn.textContent = "⚙️ SETUP / RE-RUN";
  activeSegmentIndex = null;
  editorDirty = false;
  fillEditor(null);
}

function setEditorCollapsed(collapsed, { persist = true, focus = true } = {}) {
  if (!subtitleEditor || subtitleEditor.hidden) return;
  const isCollapsed = !!collapsed;
  const keepScrollY = window.scrollY;
  subtitleEditor.classList.toggle("is-collapsed", isCollapsed);
  document.body.classList.toggle("editor-collapsed", isCollapsed);
  if (editorResizer) {
    editorResizer.style.display = isCollapsed ? "none" : "block";
    if (!isCollapsed) {
      const curW = parseInt(getComputedStyle(document.documentElement).getPropertyValue("--editor-width")) || 420;
      editorResizer.style.left = `${curW}px`;
    }
  }
  if (editorCollapseBtn) editorCollapseBtn.setAttribute("aria-expanded", String(!isCollapsed));
  if (editorExpandBtn) editorExpandBtn.setAttribute("aria-expanded", String(!isCollapsed));
  if (persist) {
    try { localStorage.setItem("subtitle_editor_collapsed", String(isCollapsed)); } catch (_) {}
  }
  if (focus) {
    const target = isCollapsed ? editorExpandBtn : editorCollapseBtn;
    if (target) target.focus({ preventScroll: true });
  }
  // A column-width change can trigger scroll anchoring; keep the editor in place.
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (Math.abs(window.scrollY - keepScrollY) > 1) window.scrollTo(0, keepScrollY);
    });
  });
}

function activateEditorTab(name, focusTab = false) {
  const tabs = [editorSegmentsTab, editorStyleTab].filter(Boolean);
  tabs.forEach(tab => {
    const selected = tab.dataset.editorTab === name;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    if (selected && focusTab) tab.focus();
  });
  if (editorSegmentsPanel) editorSegmentsPanel.hidden = name !== "segments";
  if (editorStylePanel) editorStylePanel.hidden = name !== "style";
  if (name === "style") {
    syncStyleEditor();
    applyCaptionSample();
  }
}

if (editorCollapseBtn) editorCollapseBtn.addEventListener("click", () => setEditorCollapsed(true));
if (editorExpandBtn) editorExpandBtn.addEventListener("click", () => setEditorCollapsed(false));

// If a desktop window is narrowed past the mobile breakpoint, do not leave the
// full-width editor overlay covering the page. Do not persist this automatic
// collapse, so the user's desktop preference remains intact.
let lastViewportWasMobile = window.innerWidth <= 900;
window.addEventListener("resize", () => {
  const isMobile = window.innerWidth <= 900;
  if (
    isMobile &&
    !lastViewportWasMobile &&
    document.body.classList.contains("editor-open") &&
    !document.body.classList.contains("editor-collapsed")
  ) {
    setEditorCollapsed(true, { persist: false, focus: false });
  }
  lastViewportWasMobile = isMobile;
});

// Subtitle Editor Drag Resizer
if (editorResizer) {
  let isResizingEditor = false;

  editorResizer.addEventListener("mousedown", (e) => {
    isResizingEditor = true;
    editorResizer.classList.add("is-dragging");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  });

  window.addEventListener("mousemove", (e) => {
    if (!isResizingEditor) return;
    const minW = 320;
    const maxW = Math.min(800, window.innerWidth - 300);
    const newW = Math.max(minW, Math.min(maxW, e.clientX));
    document.documentElement.style.setProperty("--editor-width", `${newW}px`);
    editorResizer.style.left = `${newW}px`;
  });

  window.addEventListener("mouseup", () => {
    if (isResizingEditor) {
      isResizingEditor = false;
      editorResizer.classList.remove("is-dragging");
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      const finalW = parseInt(getComputedStyle(document.documentElement).getPropertyValue("--editor-width")) || 420;
      try { localStorage.setItem("subtitle_editor_width", String(finalW)); } catch (_) {}
    }
  });
}

if (studioToggleConfigBtn) {
  studioToggleConfigBtn.addEventListener("click", () => {
    document.body.classList.toggle("setup-expanded");
    const isExp = document.body.classList.contains("setup-expanded");
    studioToggleConfigBtn.textContent = isExp ? "✕ HIDE SETUP" : "⚙️ SETUP / RE-RUN";
  });
}

[editorSegmentsTab, editorStyleTab].forEach(tab => {
  if (!tab) return;
  tab.addEventListener("click", () => activateEditorTab(tab.dataset.editorTab));
});

if (subtitleEditor) {
  subtitleEditor.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      saveEditorSegment();
    } else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      setEditorCollapsed(true);
    }
  });
}

if (editorSearchInput) {
  editorSearchInput.addEventListener("input", () => {
    editorSearchQuery = editorSearchInput.value;
    renderEditorList();
  });
}

if (editorSegmentList) {
  editorSegmentList.addEventListener("keydown", (event) => {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    const rows = Array.from(editorSegmentList.querySelectorAll(".editor-segment-row"));
    if (!rows.length) return;
    event.preventDefault();
    const currentIndex = rows.findIndex(row => Number(row.dataset.segmentId) === activeSegmentIndex);
    let nextIndex = currentIndex;
    if (event.key === "ArrowDown") nextIndex = Math.min(rows.length - 1, currentIndex + 1);
    if (event.key === "ArrowUp") nextIndex = Math.max(0, currentIndex - 1);
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = rows.length - 1;
    const next = rows[nextIndex];
    if (next) selectEditorSegment(Number(next.dataset.segmentId), { seek: true, focus: false });
  });
}

[editorCaptionInput, editorStartInput, editorEndInput, editorSpeakerInput].forEach(input => {
  if (!input) return;
  input.addEventListener("input", markEditorDirty);
  input.addEventListener("change", markEditorDirty);
});

if (editorSaveBtn) editorSaveBtn.addEventListener("click", saveEditorSegment);
if (editorRevertBtn) {
  editorRevertBtn.addEventListener("click", () => {
    const seg = currentSegments.find(item => item.index === activeSegmentIndex);
    if (seg) fillEditor(seg);
  });
}
if (editorSeekBtn) {
  editorSeekBtn.addEventListener("click", () => {
    const seg = currentSegments.find(item => item.index === activeSegmentIndex);
    if (!seg || !videoPlayer || !videoPlayer.src) return;
    videoPlayer.currentTime = seg.start;
    const playPromise = videoPlayer.play();
    if (playPromise && typeof playPromise.catch === "function") playPromise.catch(() => {});
  });
}

// --------------------------------------------------------------------------
// 8. Subtitle Downloads & Desktop Native File Export
// --------------------------------------------------------------------------
function rebuildSrt(isHinglish = true) {
  if (!currentSegments || currentSegments.length === 0) return "";
  return currentSegments.map(seg => {
    const text = isHinglish ? seg.hinglish_text : seg.original_text;
    return `${seg.index}\n${srtTimestamp(seg.start)} --> ${srtTimestamp(seg.end)}\n${text || ""}\n`;
  }).join("\n");
}

function showDownloadFeedback(btn, message, isSuccess = true) {
  const metaText = document.getElementById("downloadMetaText");
  if (metaText) {
    metaText.textContent = message;
    metaText.style.color = isSuccess ? "var(--green)" : "var(--pink)";
    setTimeout(() => {
      metaText.textContent = "";
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
    
    // Always regenerate: the precomputed blob was created with the default style.

    try {
      const origText = downloadAssBtn.textContent;
      downloadAssBtn.textContent = "⏳ GENERATING ASS...";
      const res = await fetch("/api/export/ass", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments: currentSegments || [],
          title: title,
          style: activeCaptionStyle,
          aspect: detectAspect()
        })
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

      // 1. Prepare ASS or SRT payload (always regenerate with the active style)
      let subPayload = "";
      let subFormat = "ass";

      const assRes = await fetch("/api/export/ass", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments: currentSegments || [],
          title: `${baseName} - Subtitles`,
          style: activeCaptionStyle,
          aspect: detectAspect()
        })
      });
      if (assRes.ok) {
        subPayload = await assRes.text();
      } else {
        subPayload = rebuildSrt(true);
        subFormat = "srt";
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

if (overlayVideoBtn) {
  overlayVideoBtn.addEventListener("click", async () => {
    if (!currentFile) {
      alert("Please upload or load a video file first to render an overlay.");
      return;
    }
    const isAudio = currentFile.type.startsWith("audio/") || /\.(mp3|wav|m4a|aac|flac|ogg)$/i.test(currentFile.name);
    if (isAudio) {
      alert("The alpha overlay needs the source video: its size, frame rate and duration define the canvas.");
      return;
    }

    const baseName = currentFile.name.replace(/\.[^/.]+$/, "");
    const origBtnText = overlayVideoBtn.innerHTML;

    try {
      overlayVideoBtn.disabled = true;
      overlayVideoBtn.innerHTML = `<span>⏳</span> RENDERING ALPHA...`;

      const assRes = await fetch("/api/export/ass", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments: currentSegments || [],
          title: `${baseName} - Overlay`,
          style: activeCaptionStyle,
          aspect: detectAspect()
        })
      });
      if (!assRes.ok) {
        throw new Error("Could not generate the ASS overlay source");
      }

      const formData = new FormData();
      formData.append("video", currentFile);
      formData.append("subtitles", await assRes.text());

      const overlayRes = await fetch("/api/export/overlay-video", {
        method: "POST",
        body: formData
      });

      if (!overlayRes.ok) {
        const errJson = await overlayRes.json().catch(() => ({}));
        throw new Error(errJson.detail || "Alpha overlay render failed on server");
      }

      const blob = await overlayRes.blob();
      const overlayUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = overlayUrl;
      a.download = `${baseName}_overlay.mov`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(overlayUrl), 60000);

      overlayVideoBtn.innerHTML = `<span>✓</span> OVERLAY READY!`;
      setTimeout(() => { overlayVideoBtn.innerHTML = origBtnText; overlayVideoBtn.disabled = false; }, 3500);

    } catch (err) {
      console.error("Alpha overlay error:", err);
      alert("Alpha overlay error: " + err.message);
      overlayVideoBtn.innerHTML = origBtnText;
      overlayVideoBtn.disabled = false;
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
      const editorOpen = subtitleEditor && !subtitleEditor.hidden && !subtitleEditor.classList.contains("is-collapsed");
      const settingsOpen = settingsDrawer && settingsDrawer.classList.contains("open");
      if (!editorOpen && !settingsOpen) {
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

