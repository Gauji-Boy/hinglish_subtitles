/*
 * Honey Punch poster grouping.
 *
 * Step 2 of the reference match: one held poster per sentence instead of one
 * block per Whisper card. The preview must group exactly like karaoke_ass.py,
 * so these assertions mirror tests/test_karaoke_ass.py.
 *
 * Run with: node tests/js/poster_grouping_test.js
 */

const { loadApp } = require("./dom_stub.js");

const STYLE = {
  id: "honeypunch",
  name: "123 Honey Punch",
  font: "Arial",
  font_size: 128,
  bold: true,
  uppercase: false,
  base_color: "#FFFFFF",
  highlight_color: "#F6C83E",
  outline_color: "#000000",
  back_color: "#00000080",
  outline_width: 10,
  shadow: 3,
  box: false,
  margin_v: 0,
  alignment: 5,
  animation: "none",
  motion: "word-pop",
  active_scale: 150,
  accent_scale: 150,
  accent_size_scale: 100,
  anchor_y: 22,
  max_width: 55,
  phrase_gap_ms: 650,
  pop_ms: 0,
  settle_ms: 0,
  accent_mode: "content",
  kinetic_layout: "alternate",
  kinetic_grouping: "poster",
  max_words_per_phrase: 10,
};

let failures = 0;

function check(label, actual, expected) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) {
    failures += 1;
    console.log(`FAIL  ${label}`);
    console.log(`        expected: ${e}`);
    console.log(`        actual:   ${a}`);
  } else {
    console.log(`ok    ${label}`);
  }
}

// One sentence split over ASR cards, spoken with short gaps only. A token in
// `pauseAfter` is followed by a 0.3 s breath, the same gate the Python
// renderer applies before punctuation may end a poster.
function cardsFor(sentence, perCard = 3, pauseAfter = null, cardGap = 0.12) {
  const tokens = String(sentence).split(/\s+/);
  const cards = [];
  let cursor = 0.0;
  for (let i = 0; i < tokens.length; i += perCard) {
    const chunk = tokens.slice(i, i + perCard);
    const words = chunk.map((text) => {
      const word = { start: cursor, end: cursor + 0.3, hinglish: text };
      cursor += 0.45;
      if (pauseAfter && text === pauseAfter) cursor += 0.3;
      return word;
    });
    cards.push({
      start: words[0].start,
      end: words[words.length - 1].end,
      hinglish_text: chunk.join(" "),
      original_text: chunk.join(" "),
      words,
    });
    cursor += cardGap;
  }
  return cards;
}

function harness(segments, { portrait = false } = {}) {
  const t = loadApp();
  t.setSegments(segments);
  t.setStyle({ ...STYLE });
  t.setMode("hinglish");
  t.setActiveIndex(null);
  if (portrait) {
    t.getPlayer().getBoundingClientRect = () => ({
      width: 456, height: 810, top: 0, left: 0, right: 456, bottom: 810, x: 0, y: 0
    });
  }
  return t;
}

const phraseSizes = (words) => {
  const sizes = [];
  words.forEach((word) => {
    sizes[word.phrase] = (sizes[word.phrase] || 0) + 1;
  });
  return sizes;
};

// Case 1: one sentence, six ASR cards, no punctuation until the end.
{
  console.log("\ncase: sentence holds across ASR cards");
  const t = harness(cardsFor(
    "jab log shaam ko kaam se aate the to mumbai mein traffic jump karta tha aaj"
  ));
  const sizes = phraseSizes(t.flattenKineticWords());
  check("16 words become two posters", sizes.length, 2);
  check("the split is balanced", Math.max(...sizes) - Math.min(...sizes) <= 2, true);
  check("no poster exceeds the cap", sizes.every((n) => n <= 10), true);
  check("first poster starts at phrase 0", t.flattenKineticWords()[0].phrase, 0);
}

// Case 2: punctuation only ends a poster when the speaker pauses there.
{
  console.log("\ncase: punctuation needs a pause");
  // One card, continuous delivery: no gap for the question mark to end on.
  const t = harness(cardsFor("The Sweet Spot? It's run by Emma", 7));
  check(
    "a continuous question mark holds the poster",
    phraseSizes(t.flattenKineticWords()),
    [7]
  );

  // A 0.3 s breath after "Spot?" is what ends the poster (mirrors
  // karaoke_ass._KINETIC_SENTENCE_PAUSE_SEC).
  const paused = harness(cardsFor("The Sweet Spot? It's run by Emma", 7, "Spot?"));
  check(
    "a pause after the question mark splits",
    phraseSizes(paused.flattenKineticWords()),
    [3, 4]
  );

  const comma = harness(cardsFor("Creek, the bakery in Willow Creek"));
  check(
    "a comma does not split",
    phraseSizes(comma.flattenKineticWords()),
    [6]
  );

  // No pause, but the ASR card ends on the question mark: the segmentation
  // confirms the sentence, so it splits there too (cardGap=0 keeps the word
  // gap below the pause gate, so only the card rule can fire).
  const cardEnd = harness(cardsFor("The Sweet Spot? It's run by Emma", 3, null, 0));
  check(
    "a card ending on the stop splits",
    phraseSizes(cardEnd.flattenKineticWords()),
    [3, 4]
  );
}

// Case 3: the word cap follows the aspect.
{
  console.log("\ncase: word cap per aspect");
  const run = "ko se me to na hi ki jo bhi ab wo bhi na bhi";
  const landscape = phraseSizes(harness(cardsFor(run)).flattenKineticWords());
  check("landscape splits the run", landscape.length > 1, true);
  check("landscape caps at 10", landscape.every((n) => n <= 10), true);
  check(
    "landscape balances the split",
    Math.max(...landscape) - Math.min(...landscape) <= 2,
    true
  );

  const portrait = phraseSizes(
    harness(cardsFor(run), { portrait: true }).flattenKineticWords()
  );
  check("portrait caps at 8", portrait.every((n) => n <= 8), true);
  check(
    "portrait balances the split",
    Math.max(...portrait) - Math.min(...portrait) <= 2,
    true
  );
}

// Case 4: a punch-dense poster is cut on its own line boundary.
{
  console.log("\ncase: line budget");
  const dense = harness(cardsFor("ek achchhe se packaging karake 20 rupayaa manifesto thaa german"));
  const words = dense.flattenKineticWords();
  check("all words survive the split", words.length, 10);
  const lines = dense.posterLineCounts();
  check("landscape posters stay within 4 lines", lines.every((n) => n <= 4), true);

  const portrait = harness(
    cardsFor("ek achchhe se packaging karake 20 rupayaa manifesto thaa german"),
    { portrait: true }
  );
  portrait.flattenKineticWords();
  check(
    "portrait posters stay within 5 lines",
    portrait.posterLineCounts().every((n) => n <= 5),
    true
  );
}

// Case 5: wall parity is a global poster index, not a per-card one.
{
  console.log("\ncase: global wall parity");
  const t = harness(cardsFor("The Sweet Spot? It's run by Emma and they love the bakery in Willow Creek,"));
  const sizes = phraseSizes(t.flattenKineticWords());
  // Posters: The/Sweet/Spot? | It's run by Emma and they | love the bakery in ...
  check("three posters", sizes.length, 3);
  const words = t.flattenKineticWords();
  check("poster 1 is right", words.find((w) => w.phrase === 0).phrase % 2, 0);
  check("poster 2 is left", words.find((w) => w.phrase === 1).phrase % 2, 1);
  check("poster 3 is right", words.find((w) => w.phrase === 2).phrase % 2, 0);
}

if (failures) {
  console.log(`\n${failures} failure(s)`);
  process.exit(1);
}
console.log("\nall poster grouping checks passed");

