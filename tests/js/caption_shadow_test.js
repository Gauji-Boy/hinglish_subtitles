/*
 * Caption outline + shadow regression test.
 *
 * Two user-visible bugs are pinned here:
 *
 * 1. The live overlay built its outline out of four offset copies of the glyph
 *    (`text-shadow: -4px -4px 0, ...`). A copied glyph is painted behind the
 *    real one, so at 13-32 px preview size the copies show through every
 *    counter ("O", "P", "B", "R", "A") and the text reads as a black blob.
 *    The outline must be a real stroke: `-webkit-text-stroke` with
 *    `paint-order: stroke fill`, so the fill stays clean.
 *
 * 2. The OUTLINE slider was mapped with `round(outline_width / 1.5)` and then
 *    clamped to 6 px, so every value from 9 to 30 produced the same preview:
 *    most of the slider did nothing. The stroke must scale with the same
 *    em ratio the ASS frame uses (previewSize / font_size), so every step of
 *    the slider changes the overlay.
 *
 * Run with: node tests/js/caption_shadow_test.js
 */

const { loadApp } = require("./dom_stub.js");

const BASE = {
  name: "Test",
  font: "Arial Black",
  font_size: 72,
  bold: true,
  uppercase: true,
  base_color: "#FFFFFF",
  highlight_color: "#FFC700",
  outline_color: "#000000",
  back_color: "#00000080",
  outline_width: 6,
  shadow: 4,
  box: false,
  margin_v: 220,
  alignment: 2,
  animation: "fade",
  motion: "none",
};

let failures = 0;

function check(label, ok, detail) {
  if (!ok) {
    failures += 1;
    console.log(`FAIL  ${label}`);
    if (detail !== undefined) console.log(`        ${detail}`);
  } else {
    console.log(`ok    ${label}`);
  }
}

function round2(value) {
  return Math.round(value * 100) / 100;
}

function previewSize(style) {
  return Math.max(13, Math.min(32, Math.round((style.font_size || 60) * 0.32)));
}

function expected(style) {
  const size = previewSize(style);
  const scale = size / Math.max(1, style.font_size || 60);
  return {
    size,
    stroke: round2(2 * Math.max(0, style.outline_width || 0) * scale),
    shadow: round2(Math.max(0, style.shadow || 0) * scale),
  };
}

function strokeWidth(value) {
  const match = /^(-?\d+(?:\.\d+)?)px/.exec(String(value || "").trim());
  return match ? Number.parseFloat(match[1]) : NaN;
}

function overlay(overrides) {
  const t = loadApp();
  t.setStyle({ ...BASE, ...overrides });
  t.setMode("hinglish");
  t.applyCaptionStyleToVideo();
  const text = t.getCaptionText();
  return {
    t,
    text,
    stroke: text.style.getPropertyValue("-webkit-text-stroke"),
    paintOrder: text.style.getPropertyValue("paint-order"),
    shadow: text.style.textShadow || "",
  };
}

function layers(value) {
  return String(value || "")
    .split(/,(?![^(]*\))/)
    .map((layer) => layer.trim())
    .filter(Boolean);
}

// Case 1: outline + shadow, the style the user reported (Techwave).
{
  console.log("\ncase: outline and shadow");
  const o = overlay({});
  const want = expected({ ...BASE });
  check("has a stroke", o.stroke !== "", o.stroke);
  check("stroke is 2x the visible outline (centred stroke)", strokeWidth(o.stroke) === want.stroke, o.stroke);
  check("stroke uses outline_color", o.stroke.includes("#000000"), o.stroke);
  check("stroke is painted behind the fill", o.paintOrder === "stroke fill", o.paintOrder);
  check("shadow is one hard layer", layers(o.shadow).length === 1, o.shadow);
  check("shadow offset scales with the ASS em", o.shadow === `${want.shadow}px ${want.shadow}px 0 #00000080`, o.shadow);
  check("shadow uses back_color", o.shadow.includes("#00000080"), o.shadow);
}

// Case 2: shadow with no outline (Buzz / Heat / Neon).
{
  console.log("\ncase: shadow without outline");
  const o = overlay({ outline_width: 0 });
  const want = expected({ ...BASE, outline_width: 0 });
  check("no stroke", strokeWidth(o.stroke) === 0, o.stroke);
  check("single hard shadow", layers(o.shadow).length === 1, o.shadow);
  check("shadow offset", o.shadow === `${want.shadow}px ${want.shadow}px 0 #00000080`, o.shadow);
}

// Case 3: no shadow, outline only.
{
  console.log("\ncase: outline only");
  const o = overlay({ shadow: 0 });
  const want = expected({ ...BASE, shadow: 0 });
  check("stroke present", strokeWidth(o.stroke) === want.stroke, o.stroke);
  check("no text shadow", o.shadow === "none", o.shadow);
}

// Case 4: neither outline nor shadow.
{
  console.log("\ncase: neither outline nor shadow");
  const o = overlay({ shadow: 0, outline_width: 0 });
  check("no stroke", strokeWidth(o.stroke) === 0, o.stroke);
  check("no text shadow", o.shadow === "none", o.shadow);
}

// Case 5: box styles draw no outline or shadow; the box carries the backdrop.
{
  console.log("\ncase: box style");
  const o = overlay({ box: true, shadow: 4, outline_width: 18 });
  check("no stroke", strokeWidth(o.stroke) === 0, o.stroke);
  check("no text shadow", o.shadow === "none", o.shadow);
}

// Case 6: the OUTLINE slider must move the overlay across its whole range.
// The old /1.5 + clamp(6) mapping froze at 9, so 9..30 looked identical.
{
  console.log("\ncase: outline slider reaches the overlay");
  const t = loadApp();
  t.setStyle({ ...BASE, outline_width: 0 });
  t.setMode("hinglish");
  t.syncStyleEditor();
  const editor = t.getEditor();
  const widths = [];
  for (const value of [0, 9, 18, 30]) {
    editor.outline.value = String(value);
    editor.outline.dispatch("input");
    widths.push(strokeWidth(t.getCaptionText().style.getPropertyValue("-webkit-text-stroke")));
  }
  check("0 outline means no stroke", widths[0] === 0, widths.join(", "));
  check("slider keeps changing past 9", widths[1] < widths[2] && widths[2] < widths[3], widths.join(", "));
  const want = [0, 9, 18, 30].map((value) =>
    expected({ ...BASE, outline_width: value }).stroke
  );
  check("each step matches the em scale", widths.join(",") === want.join(","), `${widths.join(", ")} vs ${want.join(", ")}`);
}

// Case 7: the SHADOW slider must exist and move the drop shadow. The style
// schema always had `shadow`, but the editor exposed no control for it, so the
// only "shadow" the user could drag was OUTLINE.
{
  console.log("\ncase: shadow slider reaches the overlay");
  const t = loadApp();
  t.setStyle({ ...BASE });
  t.setMode("hinglish");
  t.syncStyleEditor();
  const editor = t.getEditor();
  check("editor has a shadow control", !!editor.shadow, editor.shadow);
  if (editor.shadow) {
    editor.shadow.value = "0";
    editor.shadow.dispatch("input");
    check("0 removes the drop shadow", (t.getCaptionText().style.textShadow || "") === "none", t.getCaptionText().style.textShadow);
    editor.shadow.value = "12";
    editor.shadow.dispatch("input");
    const want = expected({ ...BASE, shadow: 12 }).shadow;
    check(
      "12 reaches the overlay at the ASS em",
      t.getCaptionText().style.textShadow === `${want}px ${want}px 0 #00000080`,
      t.getCaptionText().style.textShadow
    );
  }
}

console.log(
  failures === 0
    ? "\nAll caption shadow checks passed."
    : `\n${failures} caption shadow check(s) failed.`
);
process.exit(failures === 0 ? 0 : 1);
