/*
 * Recess live-overlay geometry test.
 *
 * The ASS side of the preset is pinned by tests/test_karaoke_ass.py. This drives
 * the live overlay under the DOM stub and checks that it publishes the same
 * geometry: the row pitch, the cap lift, and the pill box for a normal and a
 * punch word.
 *
 * The stub reports an 860x480 player, so the base em is 56.93 px - the same
 * 1080p calibration scaled by 480/1080.
 *
 * Run with:
 *   node tests/js/recess_overlay_test.js <resolved-recess-style.json>
 */

const fs = require("fs");
const { loadApp } = require("./dom_stub.js");

const stylePath = process.argv[2];
if (!stylePath) {
  console.log("usage: node tests/js/recess_overlay_test.js <style.json>");
  process.exit(2);
}
const STYLE = JSON.parse(fs.readFileSync(stylePath, "utf8"));

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

function near(label, actual, expected, tolerance) {
  if (!Number.isFinite(actual) || Math.abs(actual - expected) > tolerance) {
    failures += 1;
    console.log(`FAIL  ${label}`);
    console.log(`        expected: ${expected} +/- ${tolerance}`);
    console.log(`        actual:   ${actual}`);
  } else {
    console.log(`ok    ${label}`);
  }
}

const SEGMENTS = [
  {
    start: 2.2,
    end: 2.8,
    hinglish_text: "bakery",
    words: [{ start: 2.3, end: 2.65, hinglish: "bakery" }],
  },
  {
    start: 2.95,
    end: 3.4,
    hinglish_text: "in",
    words: [{ start: 3.05, end: 3.3, hinglish: "in" }],
  },
];

function harness(style = STYLE) {
  const t = loadApp();
  t.setSegments(SEGMENTS.map((s) => ({ ...s, words: s.words.map((w) => ({ ...w })) })));
  t.setStyle({ ...style });
  t.setMode("hinglish");
  // The overlay centres itself on the player, so give it a containing block.
  t.getOverlay().offsetParent = t.getPlayer();
  return t;
}

function show(t, seconds) {
  t.getPlayer().currentTime = seconds;
  t.updateVideoCaption();
}

function overlayTop(t) {
  const top = t.getOverlay().style.top;
  return Number.parseFloat(top);
}

// --- Punch word: "bakery" is oversized, "in" is not ------------------------
{
  console.log("\ncase: pill geometry for a punch word");
  const t = harness();
  show(t, 2.5);
  const text = t.getCaptionText();
  const em = Number.parseFloat(text.style.fontSize);
  const spans = text.querySelectorAll(".kinetic-word");
  check("one word is rendered", spans.length, 1);
  check("bakery is a punch word", spans[0].classList.contains("punch"), true);
  near("base em at 480p", em, 56.9, 0.1);

  const punchEm = Number.parseFloat(spans[0].style.fontSize);
  near("punch em follows accent_scale", punchEm / em, STYLE.accent_scale / 100, 0.01);

  // The row pitch is the ASS 0.915 em line pitch minus the 1 em word box.
  near(
    "row gap is published to CSS",
    Number.parseFloat(text.style.getPropertyValue("--recess-row")),
    0.29 * em,
    0.05
  );

  // The block is lifted so Arial Black's cap centre lands on the video midline
  // (480 / 2 in the stub), matching the ASS \an5 anchor.
  near("block is centred with the cap lift", overlayTop(t), 240 - 0.035 * punchEm, 0.2);

  // The stub has no layout engine, so give the word a line-height: 1 box and
  // place the pill again.
  spans[0].offsetHeight = punchEm;
  show(t, 2.5);

  const pill = t.document.getElementById("captionPill");
  const width = Number.parseFloat(pill.style.width);
  const height = Number.parseFloat(pill.style.height);
  const radius = Number.parseFloat(pill.style.borderRadius);
  const top = Number.parseFloat(pill.style.top);

  // Padding and radius are authored in the reference em, so they scale with the
  // base em and not with the (larger) punch word.
  near("pill radius scales with the base em", radius / em, 0.309, 0.01);
  // Height = word cap box (0.52 / 0.652 of the word em) + two vertical pads.
  // Pads are authored in the reference em, so a punch word keeps the base pads.
  const padY = (STYLE.pill_pad_y * 0.775 * em) / 0.652;
  near("pill height follows the cap ratio", height, punchEm * (0.52 / 0.652) + 2 * padY, 0.2);
  check("pill is wider than the word ink", width > punchEm * 2, true);
  // Arial Black's cap centre is 0.035 em below the middle of the 1 em line box,
  // so the pill centre lands 0.535 em below the row top - the ASS cap centre.
  near("pill centre sits on the cap centre", top + height / 2, punchEm * 0.535, 0.2);
  check("pill is fully opaque at rest", pill.style.opacity, String(STYLE.pill_alpha));
  check(
    "pill uses the preset gradient",
    pill.style.backgroundImage.includes(STYLE.pill_gradient_start) &&
      pill.style.backgroundImage.includes(STYLE.pill_gradient_end),
    true
  );
}

// --- Normal word: same em, no punch scaling -------------------------------
{
  console.log("\ncase: normal word keeps the base em");
  const t = harness();
  show(t, 3.2);
  const text = t.getCaptionText();
  const em = Number.parseFloat(text.style.fontSize);
  const spans = text.querySelectorAll(".kinetic-word");
  check("in is not a punch word", spans[0].classList.contains("punch"), false);
  near("normal word uses the base em", Number.parseFloat(spans[0].style.fontSize), em, 0.01);

  const pill = t.document.getElementById("captionPill");
  spans[0].offsetHeight = em;
  show(t, 3.2);
  const height = Number.parseFloat(pill.style.height);
  const padY = (STYLE.pill_pad_y * 0.775 * em) / 0.652;
  near("normal pill height", height, em * (0.52 / 0.652) + 2 * padY, 0.2);
  near("normal pill is centred on the cap", Number.parseFloat(pill.style.top) + height / 2, em * 0.535, 0.2);
}

// --- Word change inside a card slides the pill instead of jumping ----------
{
  console.log("\ncase: pill tracks the active word");
  const t = harness();
  const card = {
    start: 1.0,
    end: 2.2,
    hinglish_text: "in about",
    words: [
      { start: 1.05, end: 1.35, hinglish: "in" },
      { start: 1.45, end: 1.8, hinglish: "about" },
    ],
  };
  t.setSegments([card]);
  show(t, 1.1);
  const text = t.getCaptionText();
  const spans = text.querySelectorAll(".kinetic-word");
  // The stub has no layout engine, so hand-place the two words.
  spans[0].offsetLeft = 0;
  spans[0].offsetWidth = 60;
  spans[1].offsetLeft = 200;
  spans[1].offsetWidth = 150;

  const pill = t.document.getElementById("captionPill");
  const firstLeft = Number.parseFloat(pill.style.left);
  const firstWidth = Number.parseFloat(pill.style.width);
  show(t, 1.5);
  const secondLeft = Number.parseFloat(pill.style.left);
  const secondWidth = Number.parseFloat(pill.style.width);
  check("pill moved to the second word", secondLeft > firstLeft + 100, true);
  check("pill width follows the word", secondWidth > firstWidth, true);
  check(
    "same-line moves are animated",
    pill.style.transition.includes("left") && pill.style.transition.includes(`${STYLE.pill_slide_ms}ms`),
    true
  );
}

// --- Honey Punch keeps the plain overlay ----------------------------------
{
  console.log("\ncase: honey punch is untouched");
  const honey = {
    ...STYLE,
    id: "honeypunch",
    pill: false,
    kinetic_layout: "right",
    anchor_y: 20,
    max_width: 54,
    font_size: 128,
    kinetic_size_scale: 1,
    kinetic_grouping: "flow",
  };
  const t = harness(honey);
  show(t, 2.5);
  const overlay = t.getOverlay();
  const text = t.getCaptionText();
  const pill = t.document.getElementById("captionPill");
  check("no recess class on the overlay", overlay.classList.contains("recess"), false);
  check("no recess class on the text", text.classList.contains("recess"), false);
  check("pill stays hidden", pill.style.opacity, "0");
  check("no row gap variable", text.style.getPropertyValue("--recess-row"), "");
  check("word margins are untouched", text.querySelectorAll(".kinetic-word")[0].style.marginBottom, "");
  // The live anchor is resolved inside the video's own box now (the stage also
  // holds the control bar), so it is emitted in pixels, not a stage percentage.
  const videoHeightPx = t.document.getElementById("videoPlayer").getBoundingClientRect().height;
  check(
    "overlay keeps the anchor position",
    overlay.style.top,
    `${((honey.anchor_y + 1.5) * videoHeightPx / 100).toFixed(1)}px`
  );
}

// --- The POSITION slider moves a centred Recess block ---------------------
{
  console.log("\ncase: recess follows anchor_y");
  const t = harness({ ...STYLE, anchor_y: 40 });
  show(t, 2.5);
  const text = t.getCaptionText();
  const punchEm = Number.parseFloat(text.querySelectorAll(".kinetic-word")[0].style.fontSize);
  // 40% of the stub's 480 px frame, minus the cap lift. Recess centres the
  // block with translateY(-50%), so its top is the anchor.
  near("a 40% anchor moves the centred block", overlayTop(t), 0.40 * 480 - 0.035 * punchEm, 0.2);
}

console.log(
  failures === 0
    ? "\nAll Recess overlay checks passed."
    : `\n${failures} Recess overlay check(s) failed.`
);
process.exit(failures === 0 ? 0 : 1);
