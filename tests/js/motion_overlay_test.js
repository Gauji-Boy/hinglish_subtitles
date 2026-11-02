/*
 * Motion-mode overlay parity test.
 *
 * karaoke_ass.py and the live overlay must agree on what a mode means, or the
 * preview shows one thing and the burn shows another. `reveal` is one flat
 * tier, `punch` scales whichever word is being spoken, and `word-pop` keeps
 * reading the per-word flags the shipped presets carry.
 *
 * Run with: node tests/js/motion_overlay_test.js
 */

const { loadApp } = require("./dom_stub.js");

const SEGMENTS = [
  {
    start: 0.0,
    end: 2.4,
    hinglish_text: "ek do teen chaar",
    words: [
      { start: 0.0, end: 0.6, hinglish: "ek" },
      { start: 0.6, end: 1.2, hinglish: "do" },
      { start: 1.2, end: 1.8, hinglish: "teen" },
      { start: 1.8, end: 2.4, hinglish: "chaar" },
    ],
  },
];

const STYLE = {
  id: "probe",
  name: "Probe",
  font: "Impact",
  font_size: 68,
  bold: true,
  uppercase: true,
  base_color: "#FFFFFF",
  highlight_color: "#FFC700",
  outline_color: "#000000",
  outline_width: 5,
  shadow: 0,
  box: false,
  margin_v: 240,
  alignment: 2,
  animation: "fade",
  active_scale: 150,
  accent_scale: 180,
  accent_size_scale: 100,
  motion: "reveal",
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

function show(style, seconds) {
  const t = loadApp();
  t.setSegments(SEGMENTS.map((s) => ({ ...s, words: s.words.map((w) => ({ ...w })) })));
  t.setStyle({ ...style });
  t.setMode("hinglish");
  t.getOverlay().offsetParent = t.getPlayer();
  t.getPlayer().currentTime = seconds;
  t.updateVideoCaption();
  return t;
}

function sizes(t) {
  return Array.from(t.getCaptionText().querySelectorAll(".kinetic-word")).map((span) =>
    Number.parseFloat(span.style.fontSize)
  );
}

// --- reveal: no word is ever bigger than another ---------------------------
{
  console.log("\ncase: reveal is one flat tier");
  const px = sizes(show(STYLE, 0.2));
  check("four words rendered", px.length === 4, px);
  check("every word is the same size", new Set(px).size === 1, px);
}

// --- punch: the spoken word is the only big one ----------------------------
{
  console.log("\ncase: punch scales the spoken word");
  const px = sizes(show({ ...STYLE, motion: "punch" }, 0.2));
  check("four words rendered", px.length === 4, px);
  check("the first word is bigger", px[0] > px[1], px);
  check("the rest are equal", px[1] === px[2] && px[2] === px[3], px);
  check(
    "the ratio is active_scale",
    Math.abs(px[0] / px[1] - 1.5) < 0.01,
    px[0] / px[1]
  );

  const later = sizes(show({ ...STYLE, motion: "punch" }, 1.5));
  check("the big word moves with the clock", later[2] > later[0], later);
}

// --- word-pop: flags still drive it, not the clock -------------------------
{
  console.log("\ncase: word-pop still reads the word flags");
  const segments = SEGMENTS.map((s) => ({ ...s, words: s.words.map((w) => ({ ...w })) }));
  segments[0].words[3].punch = true;
  const t = loadApp();
  t.setSegments(segments);
  t.setStyle({ ...STYLE, motion: "word-pop" });
  t.setMode("hinglish");
  t.getOverlay().offsetParent = t.getPlayer();
  t.getPlayer().currentTime = 0.2;
  t.updateVideoCaption();
  const px = sizes(t);
  check("the flagged word is bigger", px[3] > px[0], px);
  check("the active word is not", px[0] === px[1], px);
}

// --- bubble: a pill follows the spoken word, without the style asking ------
{
  console.log("\ncase: bubble draws its own pill");
  const t = show({ ...STYLE, motion: "bubble", pill: false, accent_scale: 100 }, 0.2);
  const pill = t.document.getElementById("captionPill");
  check("the pill element is visible", !pill.hidden, pill.hidden);
  check(
    "the pill has a width",
    Number.parseFloat(pill.style.width) > 0,
    pill.style.width
  );
  const px = sizes(t);
  check("bubble type stays flat", new Set(px).size === 1, px);
  // Switching motion must not resize the type: bubble draws at the same em as
  // the other kinetic modes.
  const revealEm = Number.parseFloat(
    show({ ...STYLE, motion: "reveal" }, 0.2).getCaptionText().style.fontSize
  );
  check(
    "bubble draws at the reveal em",
    Math.abs(px[0] - revealEm) < 0.01,
    `${px[0]} vs ${revealEm}`
  );
  // The pill must follow the face's cap height, not Recess's Arial Black
  // ratio (0.52/0.652). The stub reports a 0.72 cap.
  const em = Number.parseFloat(t.getCaptionText().style.fontSize);
  const padY = 0.32 * 0.775 * em / 0.652;
  const expectedHeight = 0.72 * em + 2 * padY;
  const height = Number.parseFloat(pill.style.height);
  check(
    "the pill covers the face's cap height",
    Math.abs(height - expectedHeight) < em * 0.02,
    `${height} vs ${expectedHeight}`
  );
}

console.log(
  failures === 0
    ? "\nAll motion overlay checks passed."
    : `\n${failures} motion overlay check(s) failed.`
);
process.exit(failures === 0 ? 0 : 1);
