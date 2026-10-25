/*
 * Caption sync regression test.
 *
 * Bug: after the first couple of seconds the on-video caption freezes on one
 * segment for the rest of the video.
 *
 * The test drives the playhead across three non-overlapping segments and asserts
 * that the overlay shows the segment under the playhead. Run with:
 *   node tests/js/caption_sync_test.js
 */

const { loadApp } = require("./dom_stub.js");

const STYLE = {
  id: "neon",
  name: "Neon",
  font: "Segoe UI",
  font_size: 64,
  bold: true,
  uppercase: false,
  base_color: "#FFFFFF",
  highlight_color: "#F08AB5",
  outline_color: "#000000",
  back_color: "#00000080",
  outline_width: 0,
  shadow: 4,
  box: false,
  margin_v: 220,
  alignment: 2,
  animation: "fade",
  motion: "none",
};

const SEGMENTS = [
  { index: 1, start: 0.0, end: 2.0, hinglish_text: "pehla caption", original_text: "first caption" },
  { index: 2, start: 2.5, end: 4.5, hinglish_text: "doosra caption", original_text: "second caption" },
  { index: 3, start: 5.0, end: 7.0, hinglish_text: "teesra caption", original_text: "third caption" },
];

let failures = 0;

function check(label, actual, expected) {
  if (actual !== expected) {
    failures += 1;
    console.log(`FAIL  ${label}`);
    console.log(`        expected: ${JSON.stringify(expected)}`);
    console.log(`        actual:   ${JSON.stringify(actual)}`);
  } else {
    console.log(`ok    ${label}`);
  }
}

function makeHarness({ activeIndex }) {
  const t = loadApp();
  t.setSegments(SEGMENTS.map((s) => ({ ...s })));
  t.setStyle({ ...STYLE });
  t.setMode("hinglish");
  t.setActiveIndex(activeIndex);
  return t;
}

function captionAt(t, seconds) {
  t.getPlayer().currentTime = seconds;
  t.updateVideoCaption();
  return t.getCaptionText().textContent.trim();
}

// Case 1: nothing selected in the editor (fresh transcription, no card clicked).
{
  console.log("\ncase: no editor selection");
  const t = makeHarness({ activeIndex: null });
  check("t=1.0s shows segment 1", captionAt(t, 1.0), "pehla caption");
  check("t=3.0s shows segment 2", captionAt(t, 3.0), "doosra caption");
  check("t=6.0s shows segment 3", captionAt(t, 6.0), "teesra caption");
}

// Case 2: the first card is selected after transcription (what the app does on load).
{
  console.log("\ncase: first card selected in editor");
  const t = makeHarness({ activeIndex: 1 });
  check("t=1.0s shows segment 1", captionAt(t, 1.0), "pehla caption");
  check("t=3.0s shows segment 2", captionAt(t, 3.0), "doosra caption");
  check("t=6.0s shows segment 3", captionAt(t, 6.0), "teesra caption");
}

// Case 3: playhead in a gap between segments must hide the overlay, not freeze it.
{
  console.log("\ncase: playhead in a gap");
  const t = makeHarness({ activeIndex: 1 });
  captionAt(t, 1.0);
  t.getPlayer().currentTime = 2.2;
  t.updateVideoCaption();
  const stillVisible = t.getOverlay().classList.contains("visible");
  check("gap hides the overlay", stillVisible, false);
}

console.log(
  failures === 0
    ? "\nAll caption sync checks passed."
    : `\n${failures} caption sync check(s) failed.`
);
process.exit(failures === 0 ? 0 : 1);
