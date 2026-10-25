/*
 * Caption clock + render-cost regression test.
 *
 * Bug: non-kinetic styles were driven only by the video's `timeupdate` event,
 * which fires ~4x a second, so a card could paint up to 250 ms after its start.
 * The overlay is now driven by a frame loop (requestVideoFrameCallback, rAF
 * fallback) and only rebuilds the card's spans when the card changes.
 *
 * This test drives the loop one frame at a time and asserts:
 *   1. a frame alone is enough to move the overlay to the next card
 *   2. repeated frames inside one card do NOT rebuild the DOM
 *   3. word colours still advance frame by frame
 *   4. a gap hides the overlay
 *   5. pausing stops the loop
 *
 * Run with: node tests/js/caption_clock_test.js
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
  {
    index: 1,
    start: 0.0,
    end: 2.0,
    hinglish_text: "ek do teen",
    original_text: "one two three",
    words: [
      { start: 0.05, end: 0.5, word: "ek", hinglish: "ek" },
      { start: 0.7, end: 1.0, word: "do", hinglish: "do" },
      { start: 1.2, end: 1.5, word: "teen", hinglish: "teen" },
    ],
  },
  {
    index: 2,
    start: 2.5,
    end: 4.5,
    hinglish_text: "chaar paanch",
    original_text: "four five",
    words: [
      { start: 2.55, end: 3.0, word: "chaar", hinglish: "chaar" },
      { start: 3.1, end: 3.6, word: "paanch", hinglish: "paanch" },
    ],
  },
];

let failures = 0;

function check(label, actual, expected) {
  const ok = actual === expected;
  if (!ok) {
    failures += 1;
    console.log(`FAIL  ${label}`);
    console.log(`        expected: ${JSON.stringify(expected)}`);
    console.log(`        actual:   ${JSON.stringify(actual)}`);
  } else {
    console.log(`ok    ${label}`);
  }
}

function makeHarness() {
  const t = loadApp();
  t.setSegments(SEGMENTS.map((s) => ({ ...s, words: s.words.map((w) => ({ ...w })) })));
  t.setStyle({ ...STYLE });
  t.setMode("hinglish");
  const player = t.getPlayer();
  player.paused = false;
  player.ended = false;
  return { t, player };
}

// 1 + 2 + 3: one frame per playhead move, no timeupdate event anywhere.
{
  console.log("\ncase: frame loop drives the overlay");
  const { t, player } = makeHarness();
  t.startCaptionLoop();
  check("loop is running after start", t.isCaptionLoopRunning(), true);

  player.currentTime = 0.9;
  check("a frame is scheduled", player.emitFrame(), true);
  check("card 1 painted on the first frame", t.getCaptionText().textContent.trim(), "ek do teen");
  check("overlay visible", t.getOverlay().classList.contains("visible"), true);
  check("exactly one frame in flight", player.pendingFrames(), 1);

  const spansBefore = t.getCaptionText().childNodes.filter((n) => n.nodeType === 1);
  check("one span per word", spansBefore.length, 3);
  const firstSpan = spansBefore[0];

  player.currentTime = 1.3;
  player.emitFrame();
  check("still one frame in flight after a tick", player.pendingFrames(), 1);
  const spansAfter = t.getCaptionText().childNodes.filter((n) => n.nodeType === 1);
  check("same card -> no DOM rebuild", spansAfter[0] === firstSpan, true);
  check("spoken word takes the highlight colour", spansAfter[1].style.color, STYLE.highlight_color);
  check("spoken word 3 takes the highlight colour", spansAfter[2].style.color, STYLE.highlight_color);

  player.currentTime = 2.8;
  player.emitFrame();
  check("next card painted without a timeupdate", t.getCaptionText().textContent.trim(), "chaar paanch");

  player.currentTime = 2.2;
  player.emitFrame();
  check("gap hides the overlay", t.getOverlay().classList.contains("visible"), false);

  player.paused = true;
  player.currentTime = 3.2;
  player.emitFrame();
  check("pause stops the loop", t.isCaptionLoopRunning(), false);
  check("paused frame still paints the right card", t.getCaptionText().textContent.trim(), "chaar paanch");
}

// 4: forcing a repaint (style/mode change) rebuilds even inside the same card.
{
  console.log("\ncase: forced repaint");
  const { t, player } = makeHarness();
  player.currentTime = 0.9;
  t.updateVideoCaption(true);
  const before = t.getCaptionText().childNodes.filter((n) => n.nodeType === 1)[2];
  t.setStyle({ ...STYLE, base_color: "#00FF00" });
  t.updateVideoCaption(true);
  const after = t.getCaptionText().childNodes.filter((n) => n.nodeType === 1)[2];
  check("force rebuilds the card", after !== before, true);
  check("new base colour applied to unspoken word", after.style.color, "#00FF00");
}

// 5: the sync nudge shifts the whole timeline once, and clamps.
{
  console.log("\ncase: sync nudge");
  const { t } = makeHarness();
  t.setBaseSegments(SEGMENTS);

  t.setCaptionOffset(100);
  const shifted = t.getSegments();
  check("card start moved +100 ms", shifted[0].start, 0.1);
  check("card end moved +100 ms", shifted[0].end, 2.1);
  check("first word moved +100 ms", shifted[0].words[0].start, 0.15);
  check("SRT string rebuilt", shifted[0].start_str, "00:00:00,100");

  t.setCaptionOffset(60);
  check("offset snaps to 20 ms steps", t.getCaptionOffsetMs(), 60);

  t.setCaptionOffset(-5000);
  check("offset clamps at -500", t.getCaptionOffsetMs(), -500);
  check("card start never goes negative", t.getSegments()[0].start, 0);

  t.setCaptionOffset(0);
  check("zero restores the original timeline", t.getSegments()[0].start, 0);
  check("zero restores the original word time", t.getSegments()[0].words[0].start, 0.05);
}

// 6: the kinetic word list is built once, not once per frame.
{
  console.log("\ncase: kinetic word cache");
  const { t } = makeHarness();
  t.setStyle({ ...STYLE, motion: "word-pop", accent_mode: "content" });

  const first = t.flattenKineticWords();
  check("words are flattened", first.length, 5);
  check("second call reuses the array", t.flattenKineticWords(), first);

  // The editor edits in place; only captureCaptionBase() marks it dirty.
  t.getSegments()[0].hinglish_text = "ek do teen chaar";
  t.captureCaptionBase();
  const rebuilt = t.flattenKineticWords();
  check("editor edit rebuilds", rebuilt !== first, true);

  t.setMode("original");
  check("caption mode change rebuilds", t.flattenKineticWords() !== rebuilt, true);
  t.setMode("hinglish");
  t.setStyle({ ...STYLE, motion: "word-pop", accent_mode: "all" });
  check("accent mode change rebuilds", t.flattenKineticWords() !== rebuilt, true);

  // Fresh arrays per load must not collide on identity.
  t.setSegments(SEGMENTS.map((s) => ({ ...s, words: s.words.map((w) => ({ ...w })) })));
  check("new segment array rebuilds", t.flattenKineticWords() !== rebuilt, true);
}

console.log(
  failures === 0
    ? "\nAll caption clock checks passed."
    : `\n${failures} caption clock check(s) failed.`
);
process.exit(failures === 0 ? 0 : 1);
