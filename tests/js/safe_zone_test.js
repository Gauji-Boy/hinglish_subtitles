/*
 * Caption placement + 9:16 safe-zone regression test.
 *
 * Two defects this locks down:
 *   1. The editor's POSITION slider only wrote `margin_v`, so the kinetic
 *      styles (Honey Punch / Recess) ignored it and stayed at `anchor_y` forever.
 *      One slider now speaks both vocabularies.
 *   2. The live preview positioned the caption against the whole stage (video +
 *      control bar) with a clamped 0.28 factor, while the burn used the frame's
 *      `margin_v`. The live numbers below are derived from the video box.
 *
 * Run with: node tests/js/safe_zone_test.js
 */

const { loadApp } = require("./dom_stub.js");

let failures = 0;

function check(name, actual, expected) {
  const ok = actual === expected;
  console.log(`${ok ? "ok  " : "FAIL"}  ${name}`);
  if (!ok) {
    console.log(`        expected: ${JSON.stringify(expected)}`);
    console.log(`        actual:   ${JSON.stringify(actual)}`);
    failures += 1;
  }
}

function near(name, actual, expected, tolerance = 0.51) {
  const ok = Math.abs(Number(actual) - expected) <= tolerance;
  console.log(`${ok ? "ok  " : "FAIL"}  ${name}`);
  if (!ok) {
    console.log(`        expected: ${expected} +/- ${tolerance}`);
    console.log(`        actual:   ${actual}`);
    failures += 1;
  }
}

const t = loadApp();
const player = t.getPlayer();

// --- One slider, two vocabularies -----------------------------------------
console.log("\ncase: kinetic styles move with anchor_y");
const kinetic = { motion: "word-pop", anchor_y: 40, margin_v: 0, pill: false };
check("kinetic detection", t.styleIsKinetic(kinetic), true);
check("slider reads the top anchor", t.stylePositionValue(kinetic), 40);
check(
  "patch writes only anchor_y",
  JSON.stringify(t.stylePositionPatch(kinetic, 62)),
  JSON.stringify({ anchor_y: 62 })
);
check("anchor clamps high", t.stylePositionPatch(kinetic, 140).anchor_y, 100);
check("anchor clamps low", t.stylePositionPatch(kinetic, -20).anchor_y, 0);

console.log("\ncase: classic styles convert margin_v through the 9:16 frame");
const classic = { motion: "none", margin_v: 220 };
check("classic detection", t.styleIsKinetic(classic), false);
near("220 px reads as 88.5% from the top", t.stylePositionValue(classic), 100 - 220 / 19.2, 0.01);
check("patch writes margin_v", t.stylePositionPatch(classic, 100 - 220 / 19.2).margin_v, 220);
check(
  "patch never leaks an anchor into a classic style",
  Object.prototype.hasOwnProperty.call(t.stylePositionPatch(classic, 70), "anchor_y"),
  false
);
const range = t.stylePositionRange(classic);
near("range stops where margin_v runs out", range.min, 16.7, 0.05);
check("range reaches the bottom edge", range.max, 100);

console.log("\ncase: every preset margin round-trips");
[140, 170, 180, 200, 220, 240].forEach((margin) => {
  const value = t.stylePositionValue({ motion: "none", margin_v: margin });
  const back = t.stylePositionPatch({ motion: "none", margin_v: margin }, value).margin_v;
  near(`margin_v ${margin} round-trips`, back, margin, 1);
});

console.log("\ncase: landscape uses the burn's 0.375 margin scale");
player.videoWidth = 1920;
player.videoHeight = 1080;
const landscapeRange = t.stylePositionRange(classic);
near("16:9 range starts at the clamp", landscapeRange.min, 44.4, 0.05);
const landscapeMargin = t.stylePositionPatch(classic, 70).margin_v;
check("70% of a 1080 frame", landscapeMargin, Math.round((30 / 100) * 1080 / 0.375));
near(
  "16:9 margin reads back as the same percentage",
  t.stylePositionValue({ motion: "none", margin_v: landscapeMargin }),
  70,
  0.01
);

console.log("\ncase: square video uses the 0.46 margin scale");
player.videoWidth = 1080;
player.videoHeight = 1080;
const squareRange = t.stylePositionRange(classic);
near("1:1 range starts at the clamp", squareRange.min, 31.9, 0.05);
const squareMargin = t.stylePositionPatch(classic, 70).margin_v;
check("70% of a 1080 square", squareMargin, Math.round((30 / 100) * 1080 / 0.46));
near(
  "1:1 margin reads back as the same percentage",
  t.stylePositionValue({ motion: "none", margin_v: squareMargin }),
  70,
  0.05
);
player.videoWidth = 0;
player.videoHeight = 0;

// --- Live geometry ---------------------------------------------------------
console.log("\ncase: live placement measures the video, not the stage");
t.setStyle({ ...classic, id: "custom" });
t.applyClassicBottom(classic);
// The stub's video/stage box is 860x480, so 220 * 1.0 / 1920 * 480 = 55.
check("classic bottom follows margin_v", t.getOverlay().style.bottom, "55px");
t.applyKineticTop(null, { anchor_y: 40 });
// anchor_y + the 1.5% glyph nudge = 41.5% of 480 = 199.2 px.
check("kinetic top follows anchor_y", t.getOverlay().style.top, "199.2px");

// --- Safe-zone collisions (calibrated 2026 specs: 11.5% top, 23.5% bottom, 15.2% right) -
console.log("\ncase: safe-zone collisions");
check("SAFE_ZONE_TOP is calibrated to 11.5%", t.SAFE_ZONE_TOP, 11.5);
check("SAFE_ZONE_BOTTOM is calibrated to 23.5%", t.SAFE_ZONE_BOTTOM, 23.5);
check("SAFE_ZONE_RIGHT is calibrated to 15.2%", t.SAFE_ZONE_RIGHT, 15.2);
const frame = { left: 0, top: 0, right: 540, bottom: 960 };
check(
  "a centred block is clear",
  JSON.stringify(t.safeZoneCollisions({ left: 150, top: 450, right: 390, bottom: 510 }, frame)),
  "[]"
);
check(
  "the top 11.5% is flagged",
  JSON.stringify(t.safeZoneCollisions({ left: 150, top: 20, right: 390, bottom: 80 }, frame)),
  '["top bar"]'
);
check(
  "the bottom 23.5% is flagged",
  JSON.stringify(t.safeZoneCollisions({ left: 150, top: 800, right: 390, bottom: 860 }, frame)),
  '["bottom rail"]'
);
check(
  "the right 15.2% is flagged",
  JSON.stringify(t.safeZoneCollisions({ left: 430, top: 450, right: 520, bottom: 510 }, frame)),
  '["action rail"]'
);
check(
  "a block straddling the rail edge hits both",
  JSON.stringify(t.safeZoneCollisions({ left: 430, top: 700, right: 520, bottom: 760 }, frame)),
  '["bottom rail","action rail"]'
);
check(
  "a bottom-right block is only under the bottom rail",
  JSON.stringify(t.safeZoneCollisions({ left: 430, top: 830, right: 520, bottom: 900 }, frame)),
  '["bottom rail"]'
);
check(
  "a top-right block is only under the top bar",
  JSON.stringify(t.safeZoneCollisions({ left: 430, top: 20, right: 520, bottom: 80 }, frame)),
  '["top bar"]'
);
check("no frame means no collisions", t.safeZoneCollisions({}, null).length, 0);

// --- Guide chrome ----------------------------------------------------------
console.log("\ncase: the 9:16 guide only appears on portrait video");
const btn = t.document.getElementById("safeZoneBtn");
const mask = t.document.getElementById("safeZoneMask");
const warning = t.document.getElementById("safeZoneWarning");
player.classList.remove("video-portrait");
t.setSafeZoneOn(true);
t.syncSafeZoneMask();
check("button disabled on landscape", btn.disabled, true);
check("mask hidden on landscape", mask.classList.contains("visible"), false);

player.classList.add("video-portrait");
t.syncSafeZoneMask();
check("button enabled on portrait", btn.disabled, false);
check("mask follows the frame", mask.style.width, "860px");
check("mask follows the frame height", mask.style.height, "480px");
check("mask visible while toggled on", mask.classList.contains("visible"), true);

t.setSafeZoneOn(false);
t.refreshSafeZoneWarning();
check("warning hidden while the guide is off", warning.hidden, true);

console.log(
  failures === 0
    ? "\nAll caption placement and safe-zone checks passed."
    : `\n${failures} check(s) failed.`
);
process.exit(failures === 0 ? 0 : 1);
