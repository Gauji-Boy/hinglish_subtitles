/*
 * Caption shadow regression test.
 *
 * Bug: the live overlay drew its drop shadow with a blur ellipse
 * (`4px 4px 8px rgba(0,0,0,0.75)`) painted on top of the outline. At the 13-32 px
 * preview size that blur read as a grey smear over the glyph edge, while the ASS
 * burn used a hard `Shadow=4` in BackColour. Preview and burn disagreed, and the
 * preview looked dirty.
 *
 * The overlay must now mirror ASS: a hard, un-blurred drop shadow in back_color,
 * painted *first* so the outline covers it.
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

function shadowFor(overrides) {
  const t = loadApp();
  t.setStyle({ ...BASE, ...overrides });
  t.setMode("hinglish");
  t.applyCaptionStyleToVideo();
  return t.getCaptionText().style.textShadow || "";
}

// Every layer is "<x> <y> <blur> <color>"; a blurred layer has a non-zero blur.
function blurredLayers(value) {
  return value
    .split(/,(?![^(]*\))/)
    .map((layer) => layer.trim())
    .filter(Boolean)
    .filter((layer) => {
      const parts = layer.split(/\s+/);
      return Number.parseFloat(parts[2] || "0") !== 0;
    });
}

// Case 1: outline + shadow, the style the user reported (Techwave).
{
  console.log("\ncase: outline and shadow");
  const value = shadowFor({});
  check("not empty", value !== "none", value);
  check("no blurred layer", blurredLayers(value).length === 0, value);
  check("uses back_color on the drop shadow", value.includes("#00000080"), value);
  check("no rgba(0,0,0,0.75) smear", !value.includes("0.75"), value);

  const layers = value.split(/,(?![^(]*\))/).map((l) => l.trim());
  check("drop shadow painted first (so the outline covers it)", layers[0].includes("#00000080"), layers[0]);
  check("four outline corners follow", layers.length === 5, value);
  check("outline layers use outline_color", layers.slice(1).every((l) => l.includes("#000000")), value);
  // ASS shadow 4 at preview scale: half of it, never 0, never a blur radius.
  check("drop offset is a hard pixel offset", /^2px 2px 0 /.test(layers[0]), layers[0]);
}

// Case 2: shadow with no outline (Buzz / Heat / Neon) — one hard offset shadow.
{
  console.log("\ncase: shadow without outline");
  const value = shadowFor({ outline_width: 0, outline_color: "#000000" });
  check("single layer", value.split(/,(?![^(]*\))/).length === 1, value);
  check("no blur", blurredLayers(value).length === 0, value);
  check("back_color", value.includes("#00000080"), value);
}

// Case 3: no shadow, outline only — must not invent a drop shadow.
{
  console.log("\ncase: outline only");
  const value = shadowFor({ shadow: 0 });
  check("four layers", value.split(/,(?![^(]*\))/).length === 4, value);
  check("no drop shadow", !value.includes("#00000080"), value);
  check("no blur", blurredLayers(value).length === 0, value);
}

// Case 4: neither — the text must fall back to the stylesheet shadow, not "none".
{
  console.log("\ncase: neither outline nor shadow");
  const value = shadowFor({ shadow: 0, outline_width: 0 });
  check("no inline shadow", value === "none", value);
}

// Case 5: box styles draw no text shadow at all; the box carries the backdrop.
{
  console.log("\ncase: box style");
  const value = shadowFor({ box: true, shadow: 4, outline_width: 18 });
  check("no inline text shadow on a box style", value === "none", value);
}

console.log(
  failures === 0
    ? "\nAll caption shadow checks passed."
    : `\n${failures} caption shadow check(s) failed.`
);
process.exit(failures === 0 ? 0 : 1);
