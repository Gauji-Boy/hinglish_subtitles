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

const { loadApp, El } = require("./dom_stub.js");

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

// Case 4: the MOTION row shows the motion the style already carries.
{
  console.log("\ncase: motion row syncs from the style");
  const t = loadApp();
  t.setStyle({ ...BASE, motion: "none" });
  t.setMode("hinglish");
  t.syncStyleEditor();
  check("karaoke is the pickable name for `none`", t.motionRow().dataset.activeMotion === "karaoke", t.motionRow().dataset.activeMotion);

  t.setStyle({ ...BASE, motion: "reveal" });
  t.syncStyleEditor();
  check("reveal marks itself", t.motionRow().dataset.activeMotion === "reveal", t.motionRow().dataset.activeMotion);

  // Honey Punch and Recess ship `word-pop`; it is not a pickable motion, so no
  // chip may claim to be active.
  t.setStyle({ ...BASE, motion: "word-pop" });
  t.syncStyleEditor();
  check("word-pop marks no chip", t.motionRow().dataset.activeMotion === "", t.motionRow().dataset.activeMotion);
}

// Case 5: picking a motion writes the schema's own name for it.
{
  console.log("\ncase: picking a motion writes the schema value");
  const t = loadApp();
  t.setStyle({ ...BASE, motion: "none" });
  t.setMode("hinglish");
  t.syncStyleEditor();
  t.applyStyleMotion("bubble");
  check("bubble", t.getStyle().motion === "bubble", t.getStyle().motion);
  t.applyStyleMotion("punch");
  check("punch", t.getStyle().motion === "punch", t.getStyle().motion);
  t.applyStyleMotion("static");
  check("static", t.getStyle().motion === "static", t.getStyle().motion);
  t.applyStyleMotion("karaoke");
  check("karaoke writes `none`", t.getStyle().motion === "none", t.getStyle().motion);
}

// Case 6: leaving bubble takes the pill with it.
{
  console.log("\ncase: switching away from bubble drops the pill");
  const t = loadApp();
  t.setStyle({ ...BASE, motion: "bubble", pill: true });
  t.setMode("hinglish");
  t.syncStyleEditor();
  t.applyCaptionStyleToVideo();
  const pill = t.document.getElementById("captionPill");
  check("bubble shows the pill", t.getOverlay().classList.contains("recess"));

  t.applyStyleMotion("reveal");
  t.applyCaptionStyleToVideo();
  check("reveal hides it", !t.getOverlay().classList.contains("recess"));
  check("the pill is transparent", String(pill.style.opacity) === "0", pill.style.opacity);
}

// Case 7: the picker lists every style and shows its real burned frame.
{
  console.log("\ncase: the picker previews each style");
  const t = loadApp();
  t.setStyles([
    { ...BASE, id: "one", name: "One", font: "Impact", highlight_color: "#FFC700", motion: "karaoke" },
    { ...BASE, id: "two", name: "Two", font: "Georgia", highlight_color: "#38BDF8", motion: "word-pop" },
  ]);
  t.setStyle({ ...BASE, id: "one", name: "One", font: "Impact", highlight_color: "#FFC700", motion: "karaoke" });
  t.renderStylePicker();
  const p = t.picker();
  const rows = p.list.childNodes;
  check("one row per style", rows.length === 2, rows.length);
  const title1 = rows[0].querySelector(".style-picker-title");
  const stage1 = rows[0].querySelector(".style-picker-stage");
  const stage2 = rows[1].querySelector(".style-picker-stage");
  check("the title sits above the preview", rows[0].childNodes[0] === title1);
  check("the preview follows the title", rows[0].childNodes[1] === stage1);
  const frame1 = stage1.querySelector(".style-picker-frame");
  const frame2 = stage2.querySelector(".style-picker-frame");
  check("each row shows a rendered frame", !!frame1 && !!frame2, [!!frame1, !!frame2]);
  check("the frame is a PNG preview", /format=png/.test(frame1.src) && /format=png/.test(frame2.src), [frame1.src, frame2.src]);
  check("the frame comes from the preset", /style_id=one/.test(frame1.src) && /style_id=two/.test(frame2.src), [frame1.src, frame2.src]);
  const motion1 = stage1.querySelector(".style-picker-motion");
  check("a motion clip is ready on hover", /format=mp4/.test(motion1.dataset.src), motion1.dataset.src);
  check("frames stay full-frame, no crop flags", !/focus=1/.test(frame1.src) && !/focus=1/.test(frame2.src));
  const clip = stage1.querySelector(".style-picker-motion");
  check("a video starts with no frame", !clip.classList.contains("has-frame"));
  clip.dispatch("loadeddata");
  check("a loaded video may cover the PNG", clip.classList.contains("has-frame"));
  clip.dispatch("error");
  check("a failed video falls back to the PNG", !clip.classList.contains("has-frame"));
  check("no CSS word chips remain", stage1.querySelectorAll(".style-picker-word").length === 0, stage1.childNodes.length);
}

// Case 8: the trigger shows the style you are on.
{
  console.log("\ncase: the trigger shows the active style");
  const t = loadApp();
  t.setStyle({ ...BASE, id: "hormozi", name: "Neon", font: "Segoe UI", highlight_color: "#F08AB5", motion: "punch" });
  t.syncStylePicker();
  const p = t.picker();
  check("name", p.name.textContent === "Neon", p.name.textContent);
  const frame = p.stage.querySelector(".style-picker-frame");
  check("the trigger shows a rendered frame", !!frame && /format=png/.test(frame.src), frame && frame.src);
  check("the trigger carries edited settings, not a stock preset id",
    /style=/.test(frame.src) && !/style_id=/.test(frame.src), frame.src);
}

// Case 9: choosing a row applies it, updates the trigger and closes the list.
{
  console.log("\ncase: choosing a row applies the style");
  const t = loadApp();
  t.setStyles([
    { ...BASE, id: "one", name: "One" },
    { ...BASE, id: "two", name: "Two" },
  ]);
  t.setStyle({ ...BASE, id: "one", name: "One" });
  t.syncStylePicker();
  t.setStylePickerOpen(true);
  const p = t.picker();
  p.list.childNodes[1].dispatch("click");
  check("the style changed", t.getStyle().id === "two", t.getStyle().id);
  check("the list closed", p.list.hidden === true);
  check("the trigger follows", p.name.textContent === "Two", p.name.textContent);
}

// Case 10: scrolling the page must not close a list anchored to a visible
// control; scrolling the list itself was already ignored by the handler.
{
  console.log("\ncase: page scroll keeps the open list anchored");
  const t = loadApp();
  t.setStyles([{ ...BASE, id: "one", name: "One" }]);
  t.setStylePickerOpen(true);
  const p = t.picker();
  t.closeStylePickerOnScroll({ target: {} });
  check("a document scroll leaves it open", p.list.hidden === false);
  p.trigger.getBoundingClientRect = () => ({ top: -900, bottom: -700, left: 0,
    right: 300, width: 300, height: 200 });
  t.closeStylePickerOnScroll({ target: {} });
  check("it closes once the trigger is off screen", p.list.hidden === true);
}

// Case 11: the canvas switch changes what the renderer is asked for.
{
  console.log("\ncase: the portrait/landscape switch");
  const t = loadApp();
  t.setStyles([{ ...BASE, id: "one", name: "One", motion: "none" }]);
  t.renderStylePicker();
  const p = t.picker();
  const frameBefore = p.list.querySelector(".style-picker-frame");
  check("landscape is the default", /aspect=16%3A9/.test(frameBefore.src), frameBefore.src);
  const portrait = new El("button");
  portrait.dataset.aspect = "9:16";
  p.aspect.appendChild(portrait);
  p.aspect.dispatch("click", { target: portrait });
  const frameAfter = p.list.querySelector(".style-picker-frame");
  check("portrait is requested after the switch", /aspect=9%3A16/.test(frameAfter.src), frameAfter.src);
  check("portrait frames are requested full-frame", !/focus=1/.test(frameAfter.src), frameAfter.src);
}

// Case 12: open, close and Escape.
{
  console.log("\ncase: the list opens and closes");
  const t = loadApp();
  t.setStyles([{ ...BASE, id: "one", name: "One" }]);
  const p = t.picker();
  t.setStylePickerOpen(true);
  check("open", p.list.hidden === false);
  check("trigger marked open", p.trigger.classList.contains("is-open"));
  p.list.dispatch("keydown", { key: "Escape", preventDefault() {} });
  check("Escape closes", p.list.hidden === true);
  p.trigger.dispatch("click");
  check("the trigger opens it", p.list.hidden === false);
  p.trigger.dispatch("click");
  check("and closes it again", p.list.hidden === true);
}

console.log(
  failures === 0
    ? "\nAll style editor checks passed."
    : `\n${failures} style editor check(s) failed.`
);
process.exit(failures === 0 ? 0 : 1);

