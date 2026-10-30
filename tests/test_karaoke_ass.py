"""
test_karaoke_ass.py - Automated unit tests for Karaoke / Animated Word Subtitles (.ass) generator and API.
"""

import re

import pytest
from karaoke_ass import (
    _ends_sentence,
    _flatten_caption_words,
    _forced_break_after_first,
    _forced_break_after_question,
    _group_phrases,
    _split_overlong_posters,
    _kinetic_base_size,
    _kinetic_event_anchor,
    _kinetic_max_width,
    _kinetic_lines,
    _kinetic_scales,
    _recess_base_em,
    _recess_layout,
    _recess_pill_box,
    _recess_pill_events,
    _recess_strips,
    escape_ass_text,
    format_ass_time,
    generate_karaoke_ass,
    is_accent_word,
    is_punch_word,
)
from caption_styles import resolve_style


def test_format_ass_time():
    assert format_ass_time(0.0) == "0:00:00.00"
    assert format_ass_time(1.234) == "0:00:01.23"
    assert format_ass_time(65.789) == "0:01:05.79"
    assert format_ass_time(3661.05) == "1:01:01.05"
    assert format_ass_time(-5.0) == "0:00:00.00"


def test_escape_ass_text():
    assert escape_ass_text("Hello {World}") == "Hello (World)"
    assert escape_ass_text("Simple text") == "Simple text"


def test_generate_karaoke_ass_basic():
    sample_cards = [
        {
            "start": 1.0,
            "end": 3.5,
            "original_text": "à¤¨à¤®à¤¸à¥à¤¤à¥‡ à¤¦à¥‹à¤¸à¥à¤¤à¥‹à¤‚",
            "hinglish_text": "Namaste dosto",
            "words": [
                {"start": 1.0, "end": 2.0, "word": "à¤¨à¤®à¤¸à¥à¤¤à¥‡", "hinglish": "Namaste"},
                {"start": 2.1, "end": 3.2, "word": "à¤¦à¥‹à¤¸à¥à¤¤à¥‹à¤‚", "hinglish": "dosto"}
            ]
        }
    ]

    ass = generate_karaoke_ass(sample_cards, script_title="Test Reel")
    assert "[Script Info]" in ass
    assert "[V4+ Styles]" in ass
    assert "[Events]" in ass
    assert "Style: HormoziYellow" in ass
    assert "Dialogue: 0,0:00:01.00,0:00:03.50,HormoziYellow" in ass
    assert r"{\k100}Namaste " in ass
    assert r"{\k10}{\k110}dosto" in ass


def test_ass_karaoke_tracks_absolute_word_starts():
    """A silence inside a card must be emitted, not folded into the next word."""
    import re

    cards = [
        {
            "start": 1.0,
            "end": 5.0,
            "original_text": "a b c",
            "hinglish_text": "a b c",
            "words": [
                {"start": 1.0, "end": 1.5, "word": "a", "hinglish": "a"},
                {"start": 2.0, "end": 2.5, "word": "b", "hinglish": "b"},
                {"start": 4.0, "end": 4.5, "word": "c", "hinglish": "c"},
            ],
        }
    ]
    ass = generate_karaoke_ass(cards)
    line = next(l for l in ass.splitlines() if l.startswith("Dialogue:"))

    # Replay the \k chain exactly as libass does: a tag advances the clock, and
    # a word starts wherever the clock is when its tag appears.
    elapsed = 1.0
    starts = []
    for tag, text in re.findall(r"\{\\k(\d+)\}([^\\{}]*)", line):
        if text.strip():
            starts.append(round(elapsed, 2))
        elapsed += int(tag) / 100.0

    assert starts == [1.0, 2.0, 4.0], line


def test_format_ass_time_carries_centiseconds():
    assert format_ass_time(12.999) == "0:00:13.00"
    assert format_ass_time(59.995) == "0:01:00.00"
    assert format_ass_time(3599.999) == "1:00:00.00"


def test_generate_karaoke_ass_fallback_without_words():
    sample_cards = [
        {
            "start": 0.5,
            "end": 2.0,
            "original_text": "à¤¬à¤¿à¤¨à¤¾ à¤¶à¤¬à¥à¤¦ à¤Ÿà¥‹à¤•à¤¨",
            "hinglish_text": "Bina shabd token",
            "words": []
        }
    ]

    ass = generate_karaoke_ass(sample_cards)
    assert r"Dialogue: 0,0:00:00.50,0:00:02.00,HormoziYellow,,0,0,0,,{\fad(80,0)}Bina shabd token" in ass


def _cards():
    return [
        {
            "start": 0.0,
            "end": 2.0,
            "original_text": "à¤¨à¤®à¤¸à¥à¤¤à¥‡ à¤¦à¥‹à¤¸à¥à¤¤à¥‹à¤‚",
            "hinglish_text": "Namaste dosto",
            "words": [
                {"start": 0.0, "end": 1.0, "word": "à¤¨à¤®à¤¸à¥à¤¤à¥‡", "hinglish": "Namaste"},
                {"start": 1.0, "end": 2.0, "word": "à¤¦à¥‹à¤¸à¥à¤¤à¥‹à¤‚", "hinglish": "dosto"},
            ],
        }
    ]


def _style_fields(ass):
    line = next(l for l in ass.splitlines() if l.startswith("Style: "))
    return line.split(": ", 1)[1].split(",")


def test_style_preset_changes_header_and_colours():
    ass = generate_karaoke_ass(_cards(), style="vox", aspect="16:9")
    fields = _style_fields(ass)
    assert "PlayResX: 1920" in ass
    assert "PlayResY: 1080" in ass
    assert fields[1] == "Segoe UI"
    assert fields[3] == "&H00F8BD38"   # Primary = spoken highlight
    assert fields[4] == "&H00FFFFFF"   # Secondary = upcoming base
    assert 40 <= int(fields[2]) <= 60


def test_default_preset_uses_highlight_primary_and_base_secondary():
    ass = generate_karaoke_ass(_cards(), style="hormozi")
    fields = _style_fields(ass)
    assert fields[0] == "HormoziYellow"
    assert fields[3] == "&H0000C7FF"
    assert fields[4] == "&H00FFFFFF"
    assert fields[7] == "-1"


def test_uppercase_is_applied_only_for_uppercase_presets():
    assert "NAMASTE" in generate_karaoke_ass(_cards(), style="hormozi")
    assert "Namaste" in generate_karaoke_ass(_cards(), style="vox")
    assert "Namaste" in generate_karaoke_ass(_cards())


def test_box_preset_uses_border_style_three():
    ass = generate_karaoke_ass(_cards(), style="blackout")
    fields = _style_fields(ass)
    assert fields[15] == "3"
    assert fields[17] == "0"


def test_square_aspect_scales_geometry():
    ass = generate_karaoke_ass(_cards(), style="hormozi", aspect="1:1")
    fields = _style_fields(ass)
    assert "PlayResX: 1080" in ass
    assert "PlayResY: 1080" in ass
    assert int(fields[2]) == int(round(68 * 0.82))
    assert fields[21] == str(int(round(240 * 0.46)))


def test_fade_animation_and_blank_style():
    faded = generate_karaoke_ass(_cards(), style="hormozi")
    assert r"{\fad(80,0)}" in faded
    blank = generate_karaoke_ass(_cards(), style="blank")
    assert r"\fad" not in blank


def test_no_invalid_or_state_corrupting_tags():
    ass = generate_karaoke_ass(_cards(), style="hormozi")
    assert r"\fshy" not in ass
    assert r"\r" not in ass


def test_legacy_style_keywords_still_work():
    ass = generate_karaoke_ass(
        _cards(),
        font_name="Arial",
        font_size=50,
        primary_color="&H00FFFFFF",
        secondary_color="&H0000C7FF",
        outline_width=2,
    )
    fields = _style_fields(ass)
    assert fields[1] == "Arial"
    assert fields[2] == "50"
    assert fields[3] == "&H0000C7FF"
    assert fields[4] == "&H00FFFFFF"
    assert fields[16] == "2"


def test_server_export_ass_endpoint():
    from fastapi.testclient import TestClient
    from server import app

    client = TestClient(app)
    payload = {
        "title": "API Test Karaoke",
        "segments": [
            {
                "start": 0.0,
                "end": 2.5,
                "hinglish_text": "Quick test caption",
                "words": [
                    {"start": 0.0, "end": 0.8, "hinglish": "Quick"},
                    {"start": 0.9, "end": 1.5, "hinglish": "test"},
                    {"start": 1.6, "end": 2.3, "hinglish": "caption"}
                ]
            }
        ]
    }

    res = client.post("/api/export/ass", json=payload)
    assert res.status_code == 200
    assert "text/x-ssa" in res.headers["content-type"]
    assert "attachment; filename=\"karaoke_subtitles.ass\"" in res.headers["content-disposition"]
    body = res.text
    assert "[Script Info]" in body
    assert r"{\k80}Quick" in body

def _kinetic_cards():
    def word(start, end, text):
        return {"start": start, "end": end, "hinglish": text, "word": text}

    return [
        {
            "start": 0.0,
            "end": 4.0,
            "hinglish_text": "Hey did you hear about the bakery in Willow Creek",
            "words": [
                word(0.10, 0.55, "Hey,"),
                word(0.90, 1.15, "did"),
                word(1.15, 1.40, "you"),
                word(1.40, 1.80, "hear"),
                word(1.80, 2.10, "about"),
                word(2.10, 2.35, "the"),
                word(2.35, 2.85, "bakery"),
                word(2.85, 3.10, "in"),
                word(3.10, 3.65, "Willow"),
                word(3.65, 4.05, "Creek,"),
            ],
        },
        {
            "start": 4.65,
            "end": 6.9,
            "hinglish_text": "The Sweet Spot? It's run by Emma",
            "words": [
                word(4.70, 4.95, "The"),
                word(4.95, 5.25, "Sweet"),
                word(5.25, 5.55, "Spot?"),
                word(5.55, 5.85, "It's"),
                word(5.85, 6.10, "run"),
                word(6.10, 6.30, "by"),
                word(6.30, 6.90, "Emma"),
            ],
        },
    ]


def test_kinetic_accent_and_punch_detection_and_title_phrase():
    assert is_accent_word("Hey,") is True
    assert is_accent_word("hear") is True
    assert is_accent_word("bakery") is True
    assert is_accent_word("Willow") is True
    assert is_accent_word("run") is False
    assert is_accent_word("did") is False

    assert is_punch_word("Hey,") is True
    assert is_punch_word("hear") is False
    assert is_punch_word("bakery") is True
    assert is_punch_word("Willow") is True
    assert is_punch_word("run") is False

    words = _flatten_caption_words(_kinetic_cards(), use_hinglish=True, use_upper=False)
    phrases = _group_phrases(words, 0.65)
    assert len(phrases) == 2
    assert [w["text"] for w in phrases[0]][:4] == ["Hey,", "did", "you", "hear"]
    assert [w["text"] for w in phrases[1]][:3] == ["The", "Sweet", "Spot?"]
    assert phrases[1][0]["accent"] is True   # title-case The
    assert phrases[1][0]["punch"] is True    # title-case The is oversized
    assert phrases[0][3]["accent"] is True   # "hear" is gold
    assert phrases[0][3]["punch"] is False   # but not oversized
    assert phrases[0][5]["accent"] is False  # plain "the"
    assert phrases[0][6]["punch"] is True    # bakery
    assert _forced_break_after_first(phrases[0]) is True
    assert _forced_break_after_first(phrases[1]) is False
    assert _forced_break_after_question(phrases[1]) is True
    assert _forced_break_after_question(phrases[0]) is False


def _recess_reference_cards():
    def word(start, end, text):
        return {"start": start, "end": end, "hinglish": text, "word": text}

    return [
        {
            "start": 0.0,
            "end": 4.0,
            "hinglish_text": "Hey, did you hear about the bakery in Willow Creek,",
            "words": [
                word(0.10, 0.55, "Hey,"),
                word(0.90, 1.15, "did"),
                word(1.15, 1.40, "you"),
                word(1.40, 1.80, "hear"),
                word(1.80, 2.10, "about"),
                word(2.10, 2.35, "the"),
                word(2.35, 2.85, "bakery"),
                word(2.85, 3.10, "in"),
                word(3.10, 3.65, "Willow"),
                word(3.65, 4.05, "Creek,"),
            ],
        },
        {
            "start": 4.65,
            "end": 7.4,
            "hinglish_text": "The Sweet Spot? It's run by Emma ?",
            "words": [
                word(4.70, 4.95, "The"),
                word(4.95, 5.25, "Sweet"),
                word(5.25, 5.55, "Spot?"),
                word(5.55, 5.85, "It's"),
                word(5.85, 6.10, "run"),
                word(6.10, 6.30, "by"),
                word(6.30, 6.90, "Emma"),
                word(6.95, 7.15, "?"),
            ],
        },
    ]


def test_recess_punch_grouping_matches_the_reference_card_sequence():
    words = _flatten_caption_words(
        _recess_reference_cards(), use_hinglish=True, use_upper=True
    )
    # Uppercase is a display transform; it must not promote "hear" to punch.
    hear = next(w for w in words if w["raw_text"] == "hear")
    assert hear["punch"] is False

    phrases = _group_phrases(words, 0.45, max_words=10, grouping="punch")

    def card(phrase):
        return " ".join(str(w["text"]).strip(",.!") for w in phrase)

    assert [card(p) for p in phrases] == [
        "HEY",
        "DID YOU HEAR ABOUT THE",
        "BAKERY",
        "IN",
        "WILLOW",
        "CREEK",
        "THE",
        "SWEET",
        "SPOT?",
        "IT'S RUN BY",
        "EMMA",
        "?",
    ]


def test_flow_grouping_is_unchanged_by_punch_mode():
    words = _flatten_caption_words(
        _recess_reference_cards(), use_hinglish=True, use_upper=True
    )
    default = _group_phrases(words, 0.65)
    explicit = _group_phrases(words, 0.65, grouping="flow")
    default_cards = [[w["text"] for w in phrase] for phrase in default]
    flow_cards = [[w["text"] for w in phrase] for phrase in explicit]
    assert default_cards == flow_cards


def _sentence_cards(sentence, step=0.30, gap=0.15, card_size=None, begin=0.0):
    """One sentence as ASR cards, with an audible gap between the cards."""
    tokens = sentence.split()
    cards = []
    cursor = begin
    size = card_size or max(1, len(tokens))
    for start in range(0, len(tokens), size):
        chunk = tokens[start:start + size]
        words = []
        for token in chunk:
            words.append({"start": cursor, "end": cursor + step, "hinglish": token})
            cursor += step + gap
        cards.append({
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "hinglish_text": " ".join(chunk),
            "words": words,
        })
        cursor += 0.12  # ASR cards overlap the next card start slightly
    return cards


def test_poster_grouping_holds_one_sentence_across_its_asr_cards():
    sentence = "jab log shaam ko kaam se aate the to mumbai mein traffic jump karta tha aaj"
    cards = _sentence_cards(sentence, card_size=3)
    words = _flatten_caption_words(cards, use_hinglish=True, use_upper=False)

    posters = _group_phrases(words, 0.65, grouping="poster")
    # No punctuation and no pause, so the sentence stays one run until the
    # splitter balances it (see _split_overlong_posters).
    assert len(posters) == 1
    assert len(posters[0]) == 16

    # The same words in per-card flow stay fragmented, which is the defect.
    flow = _group_phrases(words, 0.65, max_words=4, grouping="flow")
    assert len(flow) == 4


def test_poster_holds_a_question_without_a_pause():
    # Reference frame 108120: "The Sweet Spot? It's run by Emma," is one block.
    # The speaker runs straight through the question mark, so punctuation alone
    # does not end the poster.
    cards = _sentence_cards("The Sweet Spot? It's run by Emma", card_size=4)
    words = _flatten_caption_words(cards, use_hinglish=True, use_upper=False)
    posters = _group_phrases(words, 0.65, max_words=10, grouping="poster")
    assert [[w["text"] for w in p] for p in posters] == [
        ["The", "Sweet", "Spot?", "It's", "run", "by", "Emma"],
    ]

    # The same sentence with a 300 ms breath after "Spot?" does split.
    for word in words:
        if word["start"] > words[2]["end"]:
            word["start"] += 0.3
            word["end"] += 0.3
    posters = _group_phrases(words, 0.65, max_words=10, grouping="poster")
    assert [[w["text"] for w in p] for p in posters] == [
        ["The", "Sweet", "Spot?"],
        ["It's", "run", "by", "Emma"],
    ]

    # No pause, but the ASR card ends on the question mark: the segmentation
    # confirms the sentence, so it splits there too.
    cards = _sentence_cards("The Sweet Spot? It's run by Emma", gap=0.05, card_size=3)
    words = _flatten_caption_words(cards, use_hinglish=True, use_upper=False)
    posters = _group_phrases(words, 0.65, max_words=10, grouping="poster")
    assert [[w["text"] for w in p] for p in posters] == [
        ["The", "Sweet", "Spot?"],
        ["It's", "run", "by", "Emma"],
    ]

    # A comma is not a sentence end; a danda and a closing quote are.
    assert _ends_sentence("Creek,") is False
    assert _ends_sentence("Spot?") is True
    assert _ends_sentence("baat\u0964") is True
    assert _ends_sentence("\u201cStop!\u201d") is True
    assert _ends_sentence("plain") is False


def test_poster_grouping_splits_on_a_real_pause_and_ignores_punch_words():
    cards = _sentence_cards("Ek achchhe packaging kiya", card_size=4)
    # 900 ms of silence before "kiya".
    cards[0]["words"][2]["end"] = cards[0]["words"][2]["start"] + 0.2
    cards[0]["words"][3]["start"] += 0.9
    cards[0]["words"][3]["end"] += 0.9
    cards[0]["end"] = cards[0]["words"][3]["end"]
    words = _flatten_caption_words(cards, use_hinglish=True, use_upper=False)
    posters = _group_phrases(words, 0.65, max_words=10, grouping="poster")
    assert [[w["text"] for w in p] for p in posters] == [
        ["Ek", "achchhe", "packaging"],
        ["kiya"],
    ]

    # Punch words never break a poster (unlike the Recess rhythm): the punch
    # word stays inside the run when there is no pause and no sentence end.
    assert any(w["punch"] for w in words[:3])
    together = _group_phrases(words[:3], 0.65, max_words=10, grouping="poster")
    assert len(together) == 1


def test_poster_alternation_uses_one_global_wall_index():
    ass = generate_karaoke_ass(_kinetic_cards(), style="honeypunch", aspect="16:9")
    events = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    order = []
    for event in events:
        x = re.search(r"\\pos\((\d+),", event).group(1)
        if not order or order[-1] != x:
            order.append(x)
    # Poster 1 is right and poster 2 is left: poster 2 starts in a new ASR card,
    # and the card boundary does not reset the wall parity. A reset would put it
    # back at 1786.
    assert order == ["1786", "134"]


def test_poster_word_cap_follows_the_aspect():
    # Short connective words keep the line budget out of the way, so the word
    # cap is the only thing ending the poster.
    long_run = "ko se me to na hi ki jo bhi ab wo bhi na bhi"
    cards = _sentence_cards(long_run, card_size=len(long_run.split()))
    words = _flatten_caption_words(cards, use_hinglish=True, use_upper=False)
    grouped = _group_phrases(words, 0.65, grouping="poster")
    resolved = resolve_style("honeypunch")
    for aspect, cap, budget in (("9:16", 8, 5), ("16:9", 10, 4)):
        res_x, res_y = (1080, 1920) if aspect == "9:16" else (1920, 1080)
        posters = _split_overlong_posters(
            grouped, resolved, res_x, res_y,
            _kinetic_base_size(res_y, int(resolved["font_size"]), res_x),
            cap, budget,
        )
        sizes = [len(p) for p in posters]
        assert sizes, aspect
        assert max(sizes) <= cap, f"{aspect}: {sizes}"
        assert max(sizes) - min(sizes) <= 2, f"{aspect}: {sizes}"


def test_poster_line_budget_keeps_the_block_inside_the_frame():
    # This is the punch-dense run that used to render six lines at 16:9 and clip
    # its last line on the frame edge.
    dense = "ek achchhe se packaging karake 20 rupayaa manifesto thaa german"
    cards = _sentence_cards(dense, card_size=10)
    for aspect, budget in (("9:16", 5), ("16:9", 4)):
        ass = generate_karaoke_ass(cards, style="honeypunch", aspect=aspect)
        events = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
        assert events
        for event in events:
            text = event.split(",,", 1)[-1]
            assert text.count(r"\N") + 1 <= budget, f"{aspect}: {text}"

    # The reference poster is exactly four lines, so the budget leaves it alone.
    ass = generate_karaoke_ass(_kinetic_cards(), style="honeypunch", aspect="16:9")
    first = next(l for l in ass.splitlines() if l.startswith("Dialogue:"))
    text = first.split(",,", 1)[-1]
    assert text.count(r"\fs") == 10
    assert text.count(r"\N") + 1 == 4




def test_kinetic_ass_prelays_the_phrase_and_alternates_its_anchors():
    ass = generate_karaoke_ass(_kinetic_cards(), style="honeypunch", aspect="16:9")
    assert "PlayResX: 1920" in ass
    assert "PlayResY: 1080" in ass
    assert "Style: HoneyPunchKinetic,Arial" in ass
    assert r"\k" not in ass
    assert r"\an9" in ass       # odd phrases flush right, 7% in
    assert r"\an7" in ass       # even phrases flush left, 7% in
    assert r"\pos(1786,238)" in ass  # right block at 22%
    assert r"\pos(134,189)" in ass   # title phrase flush left at 17.5%
    assert r"\N" in ass         # real wrapped lines
    assert r"Hey,\N" in ass     # opening interjection sits alone
    assert r"about\N" in ass    # semantic break before "the bakery"
    assert r"\c&H3EC8F6&" in ass  # gold accent words (#F6C83E)
    assert r"\c&HFFFFFF&" in ass  # white connective words
    assert ",90.5,100," in ass  # libass width compensation
    assert r"\fs114" in ass     # connective size, libass-calibrated
    assert r"\fs171" in ass     # 150% punch size, libass-calibrated
    assert r"\alpha&HFF&" in ass  # future words reserve width but stay hidden
    assert r"\alpha&H00&" in ass
    assert ass.count("Dialogue:") > 60


def test_kinetic_scales_are_three_tiers_when_the_style_asks_for_one():
    words = [{"accent": False, "punch": False}, {"accent": True, "punch": False},
             {"accent": True, "punch": True}]
    assert _kinetic_scales(words, {"accent_scale": 150}) == [1.0, 1.0, 1.5]
    assert _kinetic_scales(words, {"accent_scale": 150, "accent_size_scale": 130}) == [1.0, 1.3, 1.5]


def test_kinetic_lines_shrink_a_word_wider_than_the_line_box():
    # A 12-character punch word cannot be wrapped, so on 9:16 it used to run
    # off the frame. It should be scaled down to the box instead.
    words = [{"text": "parheshaanee"}, {"text": "hai"}]
    measure = lambda text, size, font: len(text) * size * 0.5
    lines = _kinetic_lines(words, [1.5, 1.0], 100, 400, "Arial", measure=measure)
    first = lines[0][0]
    assert first[3] == 0
    assert first[1] < 1.5
    assert len("parheshaanee") * first[2] * 0.5 <= 400 + 1e-6


def test_kinetic_ass_falls_back_when_no_timed_words():
    cards = [{"start": 0.5, "end": 2.0, "hinglish_text": "Bina shabd token", "words": []}]
    ass = generate_karaoke_ass(cards, style="honeypunch")
    assert "HoneyPunchKinetic" in ass
    assert "Bina shabd token" in ass
    assert r"\k" not in ass

def test_kinetic_anchor_reaches_every_slider_position():
    # The editor's POSITION slider writes `anchor_y` directly. These are the
    # pixel values the burn must emit for 40% and 90% of a 9:16 frame; the old
    # live overlay clamped at 80% and disagreed with both.
    resolved = {"max_width": 54, "kinetic_layout": "center", "anchor_y": 40}
    alignment, _, y = _kinetic_event_anchor(0, resolved, 1080, 1920)
    assert alignment == 8
    assert y == 1920 * 0.40
    high = _kinetic_event_anchor(0, {**resolved, "anchor_y": 90}, 1080, 1920)
    assert high[2] == 1728.0


def test_kinetic_portrait_scaling_matches_live_overlay_rules():
    # 16:9 keeps the reference 8% cap height and 54% line box.
    assert _kinetic_base_size(1080, 128, 1920) == 86
    assert _kinetic_max_width(1920, 1080, 54) == 1036.8
    assert _kinetic_event_anchor(0, {"max_width": 54, "kinetic_layout": "right", "anchor_y": 20}, 1920, 1080) == (9, 1536.0, 216.0)

    # 9:16 shrinks the base and widens the line box so punch phrases still wrap like words, not letters.
    assert _kinetic_base_size(1920, 128, 1080) == 108
    assert _kinetic_max_width(1080, 1920, 54) == 777.6
    assert _kinetic_event_anchor(1, {"max_width": 54, "kinetic_layout": "right", "anchor_y": 20}, 1080, 1920) == (9, 864.0, 384.0)

    # `alternate` flips the anchoring edge phrase by phrase, 7% in from it.
    alternating = {"max_width": 54, "kinetic_layout": "alternate", "anchor_y": 20}
    assert _kinetic_event_anchor(0, alternating, 1920, 1080) == (9, 1785.6, 216.0)
    assert _kinetic_event_anchor(1, alternating, 1920, 1080) == (7, 134.4, 216.0)

def test_kinetic_accent_mode_all_and_none_are_honoured():
    cards = [{"start": 0.0, "end": 2.0, "words": [
        {"start": 0.1, "end": 0.4, "hinglish": "Make"},
        {"start": 0.5, "end": 0.8, "hinglish": "every"},
        {"start": 0.9, "end": 1.2, "hinglish": "word"},
    ]}]
    all_words = _flatten_caption_words(cards, True, False, "all")
    none_words = _flatten_caption_words(cards, True, False, "none")
    assert all(word["accent"] for word in all_words)
    assert not any(word["accent"] for word in none_words)


def test_kinetic_wrap_measures_with_pillow_not_a_character_estimate():
    # Line wrapping decides what the burn looks like: `_kinetic_lines` greedily
    # packs words until the measured width reaches the line box. Without Pillow
    # `_measure_kinetic_text` falls back to `len(text) * size * 0.58`, which is
    # wider than the real face, so the same 24-word poster packed 5 words in 5
    # lines on a fresh `pip install .` (CI) instead of 8 words. Pillow was never
    # declared as a dependency even though karaoke_ass.py claims it is, so the
    # burn changed with the machine. Pin both the runtime import and the
    # declared dependency.
    import karaoke_ass
    from pathlib import Path

    assert karaoke_ass.ImageFont is not None, (
        "Pillow is missing, so kinetic wrapping fell back to the character estimate"
    )

    root = Path(__file__).resolve().parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    declared = pyproject.split("dependencies = [", 1)[1].split("]", 1)[0]
    assert "pillow" in declared.lower(), declared


def test_kinetic_long_utterance_splits_into_compact_portrait_posters():
    # Continuous 24-word speech without silence pauses becomes held posters, not
    # per-card flashes. Portrait posters are capped at 8 words and, because they
    # are punch-dense, at 5 rendered lines so the block stays clear of the frame
    # edge (5 lines end at ~61% of a 1920px-tall frame).
    sentence = "tumhare liye traffic parheshaanee hai, percy se ye abandon 2 laag plus monthly revenue kar rahaa hai, aaeeye seekhte hain teen simple steps me."
    words = sentence.split()
    card = {
        "start": 0.0,
        "end": 6.0,
        "hinglish_text": sentence,
        "words": [{"start": i * 0.25, "end": (i + 1) * 0.25, "hinglish": w} for i, w in enumerate(words)],
    }
    ass = generate_karaoke_ass([card], style="honeypunch", aspect="9:16")
    lines = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
    assert len(lines) > 50

    assert r"\an9" in ass
    assert r"\an7" in ass
    positions = set(re.findall(r"\\pos\((\d+),", ass))
    # 9:16 frame: right block at 93%, left block at 7%.
    assert positions == {"1004", "76"}, positions

    first = lines[0].split(",,", 1)[-1]
    # 24 words at the 8-word portrait cap: three posters, 8 / 8 / 8.
    assert first.count(r"\fs") == 8, first

    for line in lines:
        text_part = line.split(",,", 1)[-1]
        line_count = text_part.count(r"\N") + 1
        assert line_count <= 5, f"Too many stacked lines ({line_count}) in event: {text_part}"


# --- Recess preset: gradient pill + centred kinetic type -------------------


def _recess_ass(cards=None, aspect="16:9", **overrides):
    return generate_karaoke_ass(
        cards if cards is not None else _recess_reference_cards(),
        style="recess",
        aspect=aspect,
        **overrides,
    )


def _dialogue(ass, layer):
    prefix = f"Dialogue: {layer},"
    return [line for line in ass.splitlines() if line.startswith(prefix)]


def _pos(line):
    match = re.search(r"\\pos\((-?\d+),(-?\d+)\)", line)
    assert match, line
    return int(match.group(1)), int(match.group(2))


def test_recess_ass_separates_text_and_pill_layers():
    ass = _recess_ass()
    text = _dialogue(ass, 1)
    pills = _dialogue(ass, 0)

    assert text and pills
    # Pill drawings live on layer 0 so they sit behind the type; text on 1.
    assert all(",RecessPill," in line for line in pills)
    assert all(",RecessKinetic," in line for line in text)
    assert all(r"\p1" in line for line in pills)
    assert not any(r"\p1" in line for line in text)
    # A pill is several bands, so it must outnumber its words.
    assert len(pills) > len(text)


def test_recess_ass_centres_every_word_on_an5():
    ass = _recess_ass()
    text = _dialogue(ass, 1)

    assert r"\an5" in ass
    assert r"\an9" not in ass
    assert r"\N" not in ass  # words are placed, not concatenated into lines
    for line in text:
        assert r"\an5\pos(" in line
        y = _pos(line)[1]
        # Every word is anchored around the vertical middle of the canvas.
        assert 300 <= y <= 700

    # Single-word cards land on the exact horizontal centre.
    bakery = next(line for line in text if line.rstrip().endswith("BAKERY"))
    assert _pos(bakery) == (960, 530)


def test_recess_ass_spring_preserves_the_condensed_style():
    ass = _recess_ass()
    text = _dialogue(ass, 1)

    # The style condenses Arial Black to 90.5%; \fscx is absolute in libass, so
    # the spring has to start and finish in that space instead of 100/110.
    assert r"\t(0,130,\fscx90.5\fscy100)" in ass
    assert r"\fscx99.5\fscy110" in ass
    assert r"\fscx110\fscy110" not in ass
    for line in text:
        assert r"\t(0,130," in line


def test_recess_ass_pill_gradient_and_opacity_match_the_measured_reference():
    ass = _recess_ass()
    pills = _dialogue(ass, 0)

    # #D2E860 -> #A793FF is emitted BGR-ordered.
    assert r"\c&H60E8D2&" in ass
    assert r"\c&HFF93A7&" in ass
    # 0.58 opacity in inverted ASS alpha space.
    assert r"\alpha&H6B&" in ass
    assert r"\alpha&HFF&" not in ass
    for line in pills:
        assert r"\p1" in line and r"\p0" in line
        assert r"\c&H" in line


def test_recess_ass_pill_bands_are_contiguous_and_rounded():
    resolved = resolve_style("recess")
    box = _recess_pill_box(
        {"em": 197.0, "x": 960.0, "ink": 1181.0, "y": 535.0},
        resolved,
        197.0 * 0.775,
    )
    x0, y0, width, height, radius = box
    assert width == pytest.approx(1181.0 + 2 * 0.16 * 197.0 * 0.775)
    assert height == pytest.approx(197.0 * 0.52 + 2 * 0.32 * 197.0 * 0.775)
    # The pill is vertically centred on the cap box, not the anchor.
    assert y0 + height / 2.0 == pytest.approx(535.0 + 197.0 * 0.025)

    bands = _recess_strips(x0, y0, width, height, radius)
    assert len(bands) >= 10
    # Bands tile the box with no gaps or overlaps.
    assert bands[0][2] == pytest.approx(y0, abs=0.2)
    assert bands[-1][3] == pytest.approx(y0 + height, abs=0.2)
    for previous, current in zip(bands, bands[1:]):
        assert current[2] == pytest.approx(previous[3])
    # The corner arcs inset the ends and leave the straight middle flush.
    assert bands[0][0] > x0 + 1.0
    assert bands[-1][0] > x0 + 1.0
    middle = next(band for band in bands if band[2] > y0 + radius and band[3] < y0 + height - radius)
    assert middle[0] == pytest.approx(x0)
    assert middle[1] == pytest.approx(x0 + width)


def test_recess_ass_uses_the_reference_line_pitch():
    ass = _recess_ass()
    text = _dialogue(ass, 1)
    positions = [(line.rstrip().split("}")[-1], _pos(line)) for line in text]

    # The "DID YOU HEAR ABOUT / THE" break is the reference's only two-line card.
    words = [word for word, _pos_ in positions]
    start = words.index("DID")
    assert words[start : start + 5] == ["DID", "YOU", "HEAR", "ABOUT", "THE"]
    assert words[start + 5] == "BAKERY"
    first_line_y = positions[start][1][1]
    for word, (x, y) in positions[start + 1 : start + 4]:
        assert y == first_line_y, word
    assert positions[start + 4][1][1] > first_line_y
    # em * 0.915 = 180 px at 1080p, matching the reference cap-to-cap pitch.
    assert positions[start + 4][1][1] - first_line_y == pytest.approx(180, abs=1)
    assert positions[start][1][0] < positions[start + 3][1][0]


def test_recess_ass_stays_small_and_has_no_karaoke_timing():
    ass = _recess_ass()
    assert len(ass.encode("utf-8")) < 1024 * 1024
    assert r"\k" not in ass
    # No outline or shadow in the reference.
    style = next(line for line in ass.splitlines() if line.startswith("Style: RecessKinetic"))
    assert ",1,0,0,5," in style


def test_recess_portrait_centring_stays_on_canvas():
    ass = _recess_ass(aspect="9:16")
    assert "PlayResX: 1080" in ass
    assert "PlayResY: 1920" in ass
    for line in _dialogue(ass, 1):
        x, y = _pos(line)
        assert 0 <= x <= 1080
        assert 0 <= y <= 1920


def test_honey_punch_still_uses_the_plain_kinetic_renderer():
    ass = generate_karaoke_ass(_kinetic_cards(), style="honeypunch", aspect="16:9")
    assert "RecessPill" not in ass
    assert "RecessKinetic" not in ass
    assert r"\an9" in ass
    assert r"\an5" not in ass
    assert not any(r"\p1" in line for line in ass.splitlines())
    assert "HoneyPunchKinetic,,0,0,0,," in ass

