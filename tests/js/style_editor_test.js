/*
 * Style editor regression test.
 *
 * The panel used to be one flat "CUSTOM STYLE" block of nine controls, so the
 * outline colour that the ASS burn and the live overlay both read had no
 * control at all: you could set its width but not its colour. The panel is now
 * grouped TYPE / PAINT / LAYOUT, and PAINT owns every colour the burn uses.
 *
 * Run with: node tests/js/style_editor_test.js
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

// Case 1: the editor shows the outline colour the style already carries.
{
  console.log("\ncase: outline colour syncs into the panel");
  const t = loadApp();
  t.setStyle({ ...BASE, outline_color: "#221144" });
  t.setMode("hinglish");
  t.syncStyleEditor();
  const editor = t.getEditor();
  check("PAINT has an outline colour control", !!editor.outlineColor, editor.outlineColor);
  check(
    "it shows the active style's outline colour",
    editor.outlineColor && editor.outlineColor.value.toLowerCase() === "#221144",
    editor.outlineColor && editor.outlineColor.value
  );
}

// Case 2: changing it repaints the live overlay, not just the draft.
{
  console.log("\ncase: outline colour reaches the overlay");
  const t = loadApp();
  t.setStyle({ ...BASE });
  t.setMode("hinglish");
  t.syncStyleEditor();
  const editor = t.getEditor();
  editor.outlineColor.value = "#ff0000";
  editor.outlineColor.dispatch("input");
  const stroke = t.getCaptionText().style.getPropertyValue("-webkit-text-stroke");
  check("stroke uses the new colour", /#ff0000/i.test(stroke), stroke);
  check(
    "the style draft keeps it",
    String(t.getStyle().outline_color).toLowerCase() === "#ff0000",
    t.getStyle().outline_color
  );
}

// Case 3: the regroup must not drop the controls that already worked.
{
  console.log("\ncase: existing paint controls still round-trip");
  const t = loadApp();
  t.setStyle({ ...BASE, outline_width: 11, shadow: 7 });
  t.setMode("hinglish");
  t.syncStyleEditor();
  const editor = t.getEditor();
  check("outline width", String(editor.outline.value) === "11", editor.outline.value);
  check("shadow", String(editor.shadow.value) === "7", editor.shadow.value);
  editor.outline.value = "20";
  editor.outline.dispatch("input");
  check("outline width saves", t.getStyle().outline_width === 20, t.getStyle().outline_width);
}

console.log(
  failures === 0
    ? "\nAll style editor checks passed."
    : `\n${failures} style editor check(s) failed.`
);
process.exit(failures === 0 ? 0 : 1);
