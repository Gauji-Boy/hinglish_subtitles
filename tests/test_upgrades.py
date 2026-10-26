"""
tests/test_upgrades.py - Comprehensive test suite for Hinglish subtitle generator upgrades.
Tests:
  1. Loanword recovery with real CMUdict & wordfreq (marketing, campaign, Hindi protection)
  2. Variant unification (clustering Latin variants, cross-script brand snapping)
  3. Case normalization (mid-sentence common words vs proper nouns)
  4. Prompt vs hotwords logic (window 1 vs window 2 isolation)
  5. Semantic chunker timing constraints (no cards over 2.8s)
"""
import pytest
import re
from typing import List

import cmudict
import wordfreq

from hinglish_upgrades import (
    load_cmudict_lexicon,
    hindi_protect_list,
    LoanwordRecoverer,
    build_prompt,
    unify_variants,
    normalize_case,
    semantic_chunk,
    pad_display_times,
    words_to_cards,
    sanitize_words,
    _word_edit_dist,
    _latin_skeleton,
    deva_to_phones,
    _skeleton,
    _HINDI_INFLECTION,
)
from transliteration import convert_to_hinglish, COMMON_LOANWORDS


# =============================================================================
# 1. LOANWORD RECOVERY TESTS
# =============================================================================
class TestLoanwordRecovery:
    @pytest.fixture(scope="class")
    def recoverer(self):
        lex = load_cmudict_lexicon(min_zipf=3.6)
        prot = hindi_protect_list(n=10000)
        cur = set(COMMON_LOANWORDS)
        return LoanwordRecoverer(lex, protected=prot, curated=cur)

    def test_recovers_marketing_and_campaign(self, recoverer):
        # मार्केटिंग -> marketing
        res_m = recoverer.recover("मार्केटिंग")
        assert res_m == "marketing", f"Expected 'marketing', got {res_m}"

        # कैंपेन -> campaign
        res_c = recoverer.recover("कैंपेन")
        assert res_c == "campaign", f"Expected 'campaign', got {res_c}"

    def test_protects_hindi_words_from_false_recovery(self, recoverer):
        # कम must remain Hindi (never turn into English 'come')
        assert recoverer.recover("कम") is None

        # दूपते / डूबते has Hindi inflection -> must not match English
        assert recoverer.recover("दूपते") is None
        assert recoverer.recover("डूबते") is None

        # जलेगा has Hindi inflection -ेगा -> must not match English
        assert recoverer.recover("जलेगा") is None
        assert recoverer.recover("चलेगा") is None

        # फिरसे has postposition inflection -से -> must not match English 'fierce'
        assert recoverer.recover("फिरसे") is None

    def test_false_positive_guard_hindi_words_stay_hindi(self, recoverer):
        # Native Hindi words must NEVER be recovered as English loanwords
        hindi_words = ["तितली", "कर्वा", "ताला", "तालाब", "तौलिया", "बात", "काम", "घर", "जादा", "बाभाप"]
        for w in hindi_words:
            assert recoverer.recover(w) is None, f"Expected {w} to remain Hindi, but got {recoverer.recover(w)}"

    def test_merges_split_loanwords(self, recoverer):
        # Heal 'रेवे' + 'न्यू' -> 'revenue'
        words = [
            {"start": 1.0, "end": 1.4, "text": "रेवे"},
            {"start": 1.45, "end": 1.8, "text": "न्यू"}
        ]
        healed = recoverer.merge_split_words(words)
        assert len(healed) == 1
        assert healed[0]["text"] == "revenue"

    def test_never_merges_real_hindi_words(self, recoverer):
        # Measured on real audio: the merge path ignored `protected` and rewrote
        # ordinary Hindi bigrams into unrelated English words. Each of these pairs
        # was actually observed in a 54 s clip.
        pairs = [
            ("है", "देखो", "headache"),
            ("अगर", "आप", "grape"),
            ("कपड़े", "से", "cooperation"),
            ("का", "लोगो", "colleague"),
            ("के", "डाल", "cattle"),
            ("में", "भी", "maybe"),
        ]
        for a, b, wrong in pairs:
            words = [
                {"start": 0.0, "end": 0.4, "text": a},
                {"start": 0.45, "end": 0.9, "text": b},
            ]
            healed = recoverer.merge_split_words(words)
            assert [x["text"] for x in healed] == [a, b], f"{a}+{b} must not become {wrong}"

        # And the full pass must leave the sentence alone.
        sentence = [{"start": i * 0.5, "end": i * 0.5 + 0.4, "text": t}
                    for i, t in enumerate(["है", "देखो", "अगर", "आप", "कपड़े", "से"])]
        assert [w["text"] for w in recoverer.apply(sentence)] == [w["text"] for w in sentence]

    def test_nukta_is_not_an_english_signal(self, recoverer):
        # ज़/फ़ are ordinary Hindi consonants, but they used to count as an English
        # spelling signal -- which skipped `protected` and allowed the lenient
        # distance, so ज़रूर became 'server' and ज़्यादा became 'shadow'.
        # An empty protected set isolates the signal decision: only the signal can
        # stop these words now.
        bare = LoanwordRecoverer(recoverer.lex, protected=set(), curated=set())
        for deva in ("ज़रूर", "ज़्यादा", "चीज़", "चीज़े", "इज़त", "फ़र्क", "ज़िंदगी"):
            assert bare.recover(deva) is None, f"{deva} is Hindi and must not become English"

    def test_english_shaped_spellings_still_recover(self, recoverer):
        # ॉ and -िंग really are English-shaped. कॉलिटी and टॉपलेट sit between the
        # old 0.34 threshold and the current 0.20, so they also pin the limit:
        # lowering it to 0.15 would silently lose both.
        bare = LoanwordRecoverer(recoverer.lex, protected=set(), curated=set())
        expected = {
            "कॉंटेंट": "content",
            "कॉलिटी": "quality",
            "टॉपलेट": "tablet",
            "बॉस": "boss",
            "नॉस्टाइल्जिया": "nostalgia",
            "फिल्मिंग": "filming",
        }
        for deva, want in expected.items():
            assert bare.recover(deva) == want, f"{deva} should recover as {want!r}"


# =============================================================================
# 2. VARIANT UNIFICATION TESTS
# =============================================================================
class TestUnrenderableTokens:
    def test_a_lone_replacement_character_never_reaches_a_card(self):
        # Whisper emitted exactly this in a real clip: a 0.1 s token at 0.917
        # probability sitting between two real words.
        words = [
            {"start": 0.0, "end": 0.5, "text": "सकता"},
            {"start": 0.5, "end": 0.6, "text": "\ufffd"},
            {"start": 0.6, "end": 1.0, "text": "गाड़ी"},
        ]
        kept = sanitize_words(words)
        assert [w["text"] for w in kept] == ["सकता", "गाड़ी"]

        cards = words_to_cards(words, lambda s: s, pacing="short")
        joined = " ".join(c["original_text"] + c["hinglish_text"] for c in cards)
        assert "\ufffd" not in joined

    def test_invisible_marks_are_stripped_but_the_word_survives(self):
        words = [{"start": 0.0, "end": 1.0, "text": "गा\u200dड़ी"}]
        kept = sanitize_words(words)
        assert [w["text"] for w in kept] == ["गाड़ी"]

    def test_visible_punctuation_is_not_touched(self):
        words = [
            {"start": 0.0, "end": 1.0, "text": "&"},
            {"start": 1.0, "end": 2.0, "text": "H&M,"},
            {"start": 2.0, "end": 3.0, "text": "19"},
        ]
        assert [w["text"] for w in sanitize_words(words)] == ["&", "H&M,", "19"]


class TestVariantUnification:
    def test_latin_variant_clustering(self):
        words = [
            {"start": 0.0, "end": 1.0, "text": "Detol"},
            {"start": 2.0, "end": 3.0, "text": "DTOL"},
            {"start": 4.0, "end": 5.0, "text": "Detol"},
        ]
        unified = unify_variants(words)
        texts = [w["text"] for w in unified]
        assert texts == ["Detol", "Detol", "Detol"]

    def test_cross_script_brand_snapping(self):
        # Devanagari tokens ڈیٹाल / डेटॉल should snap to the established Latin brand Detol
        words = [
            {"start": 0.0, "end": 1.0, "text": "Detol"},
            {"start": 5.0, "end": 6.0, "text": "डेटॉल"},
            {"start": 10.0, "end": 11.0, "text": "डेतॉल"},
            {"start": 15.0, "end": 16.0, "text": "दिटाल"},
        ]
        unified = unify_variants(words)
        texts = [w["text"] for w in unified]
        assert texts == ["Detol", "Detol", "Detol", "Detol"]

    def test_false_positive_guard_on_short_and_hindi_words(self):
        # Hindi words like जलन must NEVER snap to Sablon
        words = [
            {"start": 0.0, "end": 1.0, "text": "Sablon"},
            {"start": 2.0, "end": 3.0, "text": "जलन"},
            {"start": 4.0, "end": 5.0, "text": "to"},
            {"start": 6.0, "end": 7.0, "text": "do"},
        ]
        unified = unify_variants(words)
        texts = [w["text"] for w in unified]
        assert texts[0] == "Sablon"
        assert texts[1] == "जलन"  # Unchanged!
        assert texts[2] == "to"    # Never merged with 'do'!
        assert texts[3] == "do"

    def test_false_positive_guard_titali_taala_etc(self):
        # तितली, ताला, तालाब, तौलिया must not snap to Detol or any canonical token
        words = [
            {"start": 0.0, "end": 1.0, "text": "Detol"},
            {"start": 2.0, "end": 3.0, "text": "तितली"},
            {"start": 4.0, "end": 5.0, "text": "ताला"},
            {"start": 6.0, "end": 7.0, "text": "तालाब"},
            {"start": 8.0, "end": 9.0, "text": "तौलिया"},
        ]
        unified = unify_variants(words)
        texts = [w["text"] for w in unified]
        assert texts[0] == "Detol"
        assert texts[1] == "तितली"
        assert texts[2] == "ताला"
        assert texts[3] == "तालाब"
        assert texts[4] == "तौलिया"



# =============================================================================
# 3. CASE NORMALIZATION TESTS
# =============================================================================
class TestCaseNormalization:
    def test_lowercases_mid_sentence_common_words(self):
        words = [
            {"start": 0.0, "end": 1.0, "text": "dekho"},
            {"start": 1.0, "end": 2.0, "text": "India"},
            {"start": 2.0, "end": 3.0, "text": "mein"},
            {"start": 3.0, "end": 4.0, "text": "Talent"},
            {"start": 4.0, "end": 5.0, "text": "ki"},
            {"start": 5.0, "end": 6.0, "text": "kami"},
            {"start": 6.0, "end": 7.0, "text": "hai,"},
            {"start": 7.0, "end": 8.0, "text": "Execution"},
            {"start": 8.0, "end": 9.0, "text": "ki"}
        ]
        normalized = normalize_case(words)
        texts = [w["text"] for w in normalized]
        assert texts[1] == "India"       # Proper noun preserved
        assert texts[3] == "talent"      # Mid-sentence common word lowercased
        assert texts[7] == "execution"   # Mid-sentence common word lowercased

    def test_preserves_sentence_starters_and_proper_nouns(self):
        words = [
            {"start": 0.0, "end": 1.0, "text": "monthly"},
            {"start": 1.0, "end": 2.0, "text": "revenue."},
            {"start": 2.0, "end": 3.0, "text": "mumbai"},
            {"start": 3.0, "end": 4.0, "text": "mein"},
            {"start": 4.0, "end": 5.0, "text": "Dettol"}
        ]
        normalized = normalize_case(words)
        texts = [w["text"] for w in normalized]
        assert texts[0] == "Monthly"     # Sentence start capitalized
        assert texts[2] == "Mumbai"      # Capitalized after sentence end
        assert texts[4] == "Dettol"      # Brand preserved

    def test_lowercases_mid_sentence_marketing_campaign_monthly_revenue(self):
        # Words with high Hindi frequency (loanwords like Marketing, Campaign, Revenue, Monthly)
        # must still be lowercased mid-sentence
        words = [
            {"start": 0.0, "end": 1.0, "text": "dekho"},
            {"start": 1.0, "end": 2.0, "text": "Marketing"},
            {"start": 2.0, "end": 3.0, "text": "aur"},
            {"start": 3.0, "end": 4.0, "text": "Campaign"},
            {"start": 4.0, "end": 5.0, "text": "ka"},
            {"start": 5.0, "end": 6.0, "text": "Monthly"},
            {"start": 6.0, "end": 7.0, "text": "Revenue"}
        ]
        normalized = normalize_case(words)
        texts = [w["text"] for w in normalized]
        assert texts[1] == "marketing"
        assert texts[3] == "campaign"
        assert texts[5] == "monthly"
        assert texts[6] == "revenue"


# =============================================================================
# 3b. TRANSLITERATION TOKEN CACHE
# =============================================================================
class TestTransliterationCache:
    @pytest.fixture(autouse=True)
    def _clean_cache(self):
        import transliteration
        transliteration._TOKEN_CACHE.clear()
        yield
        transliteration._TOKEN_CACHE.clear()

    def test_cached_output_matches_uncached(self):
        import transliteration

        tokens = ["आज", "कैसे", "है", "मार्केटिंग", "फिर", "बहुत", "अच्छा"]
        for token in tokens:
            fresh = transliteration._transliterate_hindi_word_uncached(token)
            assert transliteration._transliterate_hindi_word(token) == fresh
            # Second call must come from the cache and match the first.
            assert transliteration._transliterate_hindi_word(token) == fresh

    def test_convert_is_idempotent_across_calls(self):
        text = "आज का दिन बहुत अच्छा है, फिर मिलेंगे!"
        first = convert_to_hinglish(text)
        second = convert_to_hinglish(text)
        assert first == second
        assert re.search(r"[\u0900-\u097F]", first) is None

    def test_a_danda_does_not_corrupt_the_final_word(self):
        # The danda is fed to Aksharamukha as part of the token, so the anusvara
        # rules anchored at the end of the word never match: "हैं।" became
        # "haim." and "लोग।" became "loga.". Every Hindi card ends on a danda,
        # so this hit most sentences.
        assert convert_to_hinglish("हैं।") == "hain."
        assert convert_to_hinglish("हूं।") == "hoon."
        assert convert_to_hinglish("लोग।") == "log."

        # Mid-sentence dandas convert too, and the final word stays clean.
        phrase = convert_to_hinglish("बात। क्या है।")
        assert "\u0964" not in phrase
        assert phrase.startswith("baat. ")
        assert phrase.endswith("hai."), phrase

        # A comma already took the correct path; the danda must agree with it.
        assert convert_to_hinglish("हैं।") == convert_to_hinglish("हैं,").replace(",", ".")

    def test_urdu_tokens_are_cached_too(self):
        import transliteration

        token = "کیسے"
        fresh = transliteration._transliterate_urdu_word_uncached(token)
        assert transliteration._transliterate_urdu_word(token) == fresh
        assert transliteration._transliterate_urdu_word(token) == fresh
        assert token in transliteration._TOKEN_CACHE

    def test_cache_stays_bounded_and_correct_after_clear(self):
        import transliteration

        token = "आज"
        expected = transliteration._transliterate_hindi_word_uncached(token)
        transliteration._TOKEN_CACHE.clear()
        for i in range(transliteration._TOKEN_CACHE_MAX + 5):
            transliteration._TOKEN_CACHE[f"filler{i}"] = "x"
        assert transliteration._transliterate_hindi_word(token) == expected
        assert len(transliteration._TOKEN_CACHE) < 10


# =============================================================================
# 4. PROMPTING & HOTWORDS TESTS
# =============================================================================
class TestPrompting:
    def test_domain_neutral_initial_prompt(self):
        prompt, hot = build_prompt(topic_hint="", extra_keywords=())
        assert "नमस्ते" in prompt
        assert "video" in prompt
        # Domain terms from test reels must NEVER be in initial prompt
        assert "dettol" not in prompt.lower()
        assert "savlon" not in prompt.lower()
        assert "vada" not in prompt.lower()
        assert hot == ""

    def test_caption_hint_routes_to_hotwords(self):
        prompt, hot = build_prompt(topic_hint="Check out this #Dettol vs #Savlon ad", extra_keywords=())
        assert "Dettol" in hot
        assert "Savlon" in hot
        # initial_prompt remains domain-neutral
        assert "dettol" not in prompt.lower()


# =============================================================================
# 5. SEMANTIC CHUNKER CONSTRAINTS
# =============================================================================
class TestSemanticChunker:
    def test_card_duration_ceiling(self):
        # Generate dummy stream of 50 words with realistic 0.3s duration each
        words = []
        t = 0.0
        for i in range(50):
            words.append({"start": round(t, 2), "end": round(t + 0.3, 2), "text": f"word{i}"})
            t += 0.35

        cards = pad_display_times(semantic_chunk(words, max_dur=2.8, pacing="short"), pacing="short")
        for c in cards:
            dur = c["end"] - c["start"]
            assert dur <= 2.81, f"Card duration exceeded 2.8s ceiling: {dur:.2f}s ({c})"
            assert dur >= 0.99, f"Card duration under min duration: {dur:.2f}s ({c})"

    def test_long_form_pacing_constraints(self):
        # 50 words in long-form mode should form longer cards (up to 5.0s, >= 2.0s)
        words = []
        t = 0.0
        for i in range(50):
            words.append({"start": round(t, 2), "end": round(t + 0.3, 2), "text": f"word{i}"})
            t += 0.35

        cards = pad_display_times(semantic_chunk(words, pacing="long"), pacing="long")
        # Fewer total cards than short-form
        short_cards = pad_display_times(semantic_chunk(words, pacing="short"), pacing="short")
        assert len(cards) < len(short_cards), f"Expected fewer cards in long-form ({len(cards)}) than short-form ({len(short_cards)})"
        for c in cards:
            dur = c["end"] - c["start"]
            assert dur <= 5.05, f"Long-form card exceeded 5.0s ceiling: {dur:.2f}s"
            assert dur >= 1.95, f"Long-form card under 2.0s min: {dur:.2f}s"

    def test_pad_display_times_clamps_stretched_cards(self):
        # Even if Whisper or audio pause produced a card spanning 12s, pad_display_times must clamp to max_dur
        stretched = [
            {"start": 10.0, "end": 22.0, "text": "stuck word"},
            {"start": 25.0, "end": 26.0, "text": "next word"}
        ]
        padded = pad_display_times(stretched, max_dur=2.8, pacing="short")
        assert padded[0]["end"] <= 12.8, f"Stretched card duration not clamped: {padded[0]}"
        assert padded[0]["end"] < padded[1]["start"], "Overlapped subsequent card"



# =============================================================================
# 6. AUDIO MEDIA EXTRACTION & SUPPORT TESTS
# =============================================================================
class TestAudioSupport:
    def test_extract_audio_from_wav(self):
        import numpy as np
        from hinglish_engine import extract_audio_numpy
        import os
        wav_path = "jalegaa_chalegaa_span.wav"
        if os.path.exists(wav_path):
            audio = extract_audio_numpy(wav_path)
            assert len(audio) > 0
            assert audio.dtype == np.float32


# =============================================================================
# 7. CUSTOM MEDIA CONTROLS & VISUALIZER TESTS
# =============================================================================
class TestCustomPlayerControlsAndUI:
    def test_index_html_has_custom_player_and_canvas(self):
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()

        # videoPlayer should not have browser default controls
        assert '<video id="videoPlayer" playsinline>' in html or '<video id="videoPlayer" playsinline></video>' in html
        assert '<video id="videoPlayer" controls' not in html

        # Custom Neo-Brutalist media controls dock elements
        assert 'id="customMediaControls"' in html
        assert 'id="playerPlayBtn"' in html
        assert 'id="playerScrubber"' in html
        assert 'id="playerCurrentTime"' in html
        assert 'id="playerDuration"' in html
        assert 'id="playerVolumeBtn"' in html
        assert 'id="playerFullscreenBtn"' in html

        # Audio visualizer canvas
        assert 'id="audioVisualizerCanvas"' in html

    def test_components_css_glyph_shadows_and_player(self):
        with open("static/components.css", "r", encoding="utf-8") as f:
            css = f.read()

        # Glyph shadow is pure white in dark theme, pure black in light theme
        assert "box-shadow: 3px 3px 0 #ffffff;" in css
        assert '[data-theme="minimalist-light"] .glyph' in css
        assert "box-shadow: 3px 3px 0 #000000;" in css

        # Active tile border and shadow coordinate with var(--c)
        assert "border-color: var(--c" in css
        assert "box-shadow: 4px 4px 0 var(--c" in css

        # Custom media controls dock styling
        assert ".custom-media-controls" in css
        assert ".player-btn" in css
        assert ".player-scrubber" in css
        assert ".audio-visualizer-canvas" in css

        # Mechanical scrollbar in tokens.css
        with open("static/tokens.css", "r", encoding="utf-8") as f_tok:
            tok_css = f_tok.read()
        assert "scrollbar-width: thin" in tok_css
        assert "::-webkit-scrollbar" in tok_css
        assert "::-webkit-scrollbar-thumb" in tok_css


    def test_segments_dropdown_and_launchers(self):
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="segmentsDropdown"' not in html
        assert 'id="toggleGridBtn"' in html
        assert 'id="segmentsCollapsedCard"' in html

        with open("static/components.css", "r", encoding="utf-8") as f:
            css = f.read()
        assert ".segments-dropdown" in css
        assert ".btn-toggle-grid" in css
        assert ".segments-collapsed-card" in css

        import os
        assert os.path.exists("HinglishSubtitles.exe")
        assert os.path.exists("run_app_no_terminal.vbs")
        assert os.path.exists("stop_app.bat")
        assert os.path.exists("launch_config.json")
        with open("run_app.bat", "r", encoding="utf-8") as f:
            bat = f.read()
        assert "silent_mode" in bat
        assert "run_app_no_terminal.vbs" in bat

        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="toggleConsoleBtn"' in html
        assert 'id="terminalDock"' in html
        assert 'id="terminalLaunchPills"' not in html

    def test_models_d_drive_and_base_removal(self):
        from hinglish_engine import MODEL_SPECS, get_models_status
        import json
        # 1. Base and Tiny models must not be present in MODEL_SPECS
        assert "base" not in MODEL_SPECS
        assert "tiny" not in MODEL_SPECS
        assert "large-v3-turbo" in MODEL_SPECS
        assert "indic-conformer" in MODEL_SPECS
        assert "sravaani-1.0" in MODEL_SPECS
        assert "sensevoice-small" in MODEL_SPECS
        assert "small" in MODEL_SPECS

        # 2. Base and Tiny models must not be in index.html; new models must be present
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        assert 'data-model="base"' not in html
        assert 'data-model="tiny"' not in html
        assert 'data-model="large-v3-turbo"' in html
        assert 'data-model="indic-conformer"' in html
        assert 'data-model="sravaani-1.0"' in html
        assert 'data-model="sensevoice-small"' in html

        # 3. Model status works and sees cached models from D:
        status = get_models_status()
        assert "base" not in status
        assert "tiny" not in status
        assert "large-v3-turbo" in status
        assert status["large-v3-turbo"]["cached"] is True
        assert status["indic-conformer"]["cached"] is True
        assert status["sravaani-1.0"]["cached"] is True
        assert status["sensevoice-small"]["cached"] is True

    def test_preferences_persistence(self):
        from fastapi.testclient import TestClient
        from server import app
        import json
        import os

        # Save previous config to restore after test
        orig_cfg = None
        if os.path.exists("launch_config.json"):
            try:
                with open("launch_config.json", "r", encoding="utf-8") as f:
                    orig_cfg = f.read()
            except Exception:
                pass

        try:
            client = TestClient(app)
            # 1. Post preference updates with Hindi to English (hi-en) and large-v3
            res = client.post("/api/config/preferences", data={
                "selected_model": "large-v3",
                "selected_language": "hi-en",
                "selected_pacing": "long",
                "selected_device": "cuda"
            })
            assert res.status_code == 200

            # 2. Get preferences
            get_res = client.get("/api/config/preferences")
            assert get_res.status_code == 200
            data = get_res.json()
            assert data["selected_model"] == "large-v3"
            assert data["selected_language"] == "hi-en"
            assert data["selected_pacing"] == "long"
            assert data["selected_device"] == "cuda"

            # 3. Check launch_config.json contains saved model & language
            with open("launch_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            assert cfg.get("selected_model") == "large-v3"
            assert cfg.get("selected_language") == "hi-en"

            # 4. Check that GET / serves HTML with synchronous config injection & active tiles/pills
            root_res = client.get("/")
            assert root_res.status_code == 200
            html = root_res.text
            assert "window.__INITIAL_CONFIG__" in html
            assert '"selected_language": "hi-en"' in html
            assert '"selected_model": "large-v3"' in html
            # Active language tile is hi-en
            assert 'class="tile active" data-lang="hi-en"' in html
            # Non-translation models are hidden in hi-en mode
            assert 'data-model="large-v3-turbo" style="display: none;"' in html
            assert 'data-model="indic-conformer" style="display: none;"' in html
            # Active model pill is large-v3
            assert 'class="pill active" data-model="large-v3"' in html
            # Active pacing pill is long
            assert 'class="pill active" data-pacing="long"' in html
            assert root_res.headers.get("cache-control") == "no-cache, no-store, must-revalidate, max-age=0"
        finally:
            if orig_cfg is not None:
                with open("launch_config.json", "w", encoding="utf-8") as f:
                    f.write(orig_cfg)

    def test_cors_restricted_to_local_origins(self):
        from server import app
        from starlette.testclient import TestClient
        client = TestClient(app)

        # 1. Localhost and 127.0.0.1 origins are permitted
        r_local1 = client.get("/api/hardware", headers={"Origin": "http://127.0.0.1:8501"})
        assert r_local1.headers.get("access-control-allow-origin") == "http://127.0.0.1:8501"

        r_local2 = client.get("/api/hardware", headers={"Origin": "http://localhost:8502"})
        assert r_local2.headers.get("access-control-allow-origin") == "http://localhost:8502"

        # 2. Arbitrary external origins are denied
        r_evil = client.get("/api/hardware", headers={"Origin": "http://evil.com"})
        assert "access-control-allow-origin" not in r_evil.headers

    def test_sleek_bento_theme_configuration(self):
        # Verify index.html has option
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        assert '<option value="sleek-bento">' in html

        # Verify tokens.css has tokens
        with open("static/tokens.css", "r", encoding="utf-8") as f:
            tokens = f.read()
        assert '[data-theme="sleek-bento"]' in tokens
        assert "#bef264" in tokens  # Neon lime accent
        assert "#fb923c" in tokens  # Solar orange accent
        assert "--border-radius-pill: 9999px" in tokens

        # Verify components.css has scoped overrides
        with open("static/components.css", "r", encoding="utf-8") as f:
            components = f.read()
        assert '[data-theme="sleek-bento"] .btn-primary' in components
        assert '[data-theme="sleek-bento"] .tile' in components
        assert '[data-theme="sleek-bento"] .pill' in components

    def test_micro_polished_cta_and_layout(self):
        with open("static/components.css", "r", encoding="utf-8") as f:
            css = f.read()

        # Primary button must NOT turn white on hover
        assert ".btn-primary:hover {\n  background: #ffffff;" not in css
        assert ".btn-primary:hover:not(:disabled)" in css
        assert ".btn-primary:disabled" in css
        assert ".action-status-chip" in css
        assert "user-select: none" in css
        assert "user-select: text !important" in css

        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="actionStatusChip"' in html
        assert 'class="control-group topic-hint-group"' in html
        assert '<svg class="brand-logo"' in html
        assert '<img src="/static/logo.svg"' not in html
        assert 'href="favicon.ico"' in html

        with open("static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "function formatShortGpuName" in js
        assert "function updateGenerateButtonState" in js

        with open("server.py", "r", encoding="utf-8") as f:
            srv = f.read()
        assert "SetCurrentProcessExplicitAppUserModelID" in srv
        assert "icon=icon_path" in srv
        assert "text_select=False" in srv

        import os
        assert os.path.exists("static/favicon.ico")
        assert os.path.exists("static/logo.svg")
        assert os.path.exists("app_icon.ico")

    def test_dark_light_theme_toggle_option1(self):
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="themeModeToggleBtn"' in html
        assert 'class="theme-mode-btn"' in html
        assert 'id="themeModeIcon"' in html
        assert 'id="themeModeText"' in html
        assert '<option value="minimalist-light">' not in html
        assert 'html[data-theme="minimalist-light"]' in html

        with open("static/tokens.css", "r", encoding="utf-8") as f:
            tokens = f.read()
        assert '[data-theme="minimalist-light"]' in tokens
        assert "--bg: #f5f4ef" in tokens
        assert "--text: #1c1917" in tokens
        assert "--border-color: #d6d3cb" in tokens

        with open("static/components.css", "r", encoding="utf-8") as f:
            css = f.read()
        assert ".theme-mode-btn" in css
        assert '[data-theme="minimalist-light"] .theme-mode-btn' in css
        assert '[data-theme="sleek-bento"] .theme-mode-btn' in css
        assert '[data-theme="minimalist-light"] .ribbon' in css
        assert '[data-theme="minimalist-light"] .meta-pill' in css
        assert '[data-theme="minimalist-light"] .topic-hint-input' in css
        assert '[data-theme="minimalist-light"] .model-status-bar' in css
        assert '[data-theme="minimalist-light"] .action-status-chip' in css
        assert '[data-theme="minimalist-light"] .hero h1 mark' in css
        assert '.tile.active {\n  border-color: var(--c, var(--yellow));\n  background: var(--tile-hover-bg);\n  color: #ffffff;\n  box-shadow: 4px 4px 0 var(--c, var(--yellow));' in css
        assert '[data-theme="minimalist-light"] .tile.active {\n  background: #ffffff;\n  border-color: var(--c, var(--yellow));\n  color: var(--text);\n  box-shadow: 4px 4px 0 var(--c, var(--yellow));' in css

        with open("static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "themeModeToggleBtn" in js
        assert "preferredDarkTheme" in js
        assert "applyTheme" in js
        assert "updateThemeModeUI" in js
        assert "minimalist-light" in js

    def test_subtitle_download_api_and_desktop_bridge(self, tmp_path):
        from server import app, DesktopAPI
        from starlette.testclient import TestClient
        client = TestClient(app)

        # 1. Test POST /api/download/file for SRT
        srt_data = {
            "filename": "test_video_hinglish.srt",
            "content": "1\n00:00:00,000 --> 00:00:02,000\nYeh ek test hai\n"
        }
        res_srt = client.post("/api/download/file", json=srt_data)
        assert res_srt.status_code == 200
        assert 'attachment; filename="test_video_hinglish.srt"' in res_srt.headers.get("content-disposition", "")
        assert "application/x-subrip" in res_srt.headers.get("content-type", "")
        assert res_srt.text == srt_data["content"]

        # 2. Test POST /api/download/file for TXT
        txt_data = {
            "filename": "test_video_hinglish.txt",
            "content": "Yeh ek test hai"
        }
        res_txt = client.post("/api/download/file", json=txt_data)
        assert res_txt.status_code == 200
        assert 'attachment; filename="test_video_hinglish.txt"' in res_txt.headers.get("content-disposition", "")
        assert "text/plain" in res_txt.headers.get("content-type", "")
        assert res_txt.text == txt_data["content"]

        # 3. Test DesktopAPI class mock
        api = DesktopAPI()
        # No window yet
        assert api.save_subtitle_file("test.srt", "content")["success"] is False

        target_file = tmp_path / "mock_subtitles.srt"
        class MockWindow:
            def create_file_dialog(self, **kwargs):
                return (str(target_file),)

        api.set_window(MockWindow())
        result = api.save_subtitle_file("mock_subtitles.srt", "1\n00:00:00,000 --> 00:00:01,000\nHello")
        assert result["success"] is True
        assert result["path"] == str(target_file)
        assert target_file.read_text(encoding="utf-8") == "1\n00:00:00,000 --> 00:00:01,000\nHello"

        # 4. Verify static/app.js has multi-strategy export logic
        with open("static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "save_subtitle_file" in js
        assert "/api/download/file" in js
        assert "showDownloadFeedback" in js
        assert "rebuildSrt" in js

        # 5. Verify static/index.html floatingDownloadBar elevated z-index & search integration
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="floatingDownloadBar"' in html
        assert "z-index: 95" in html
        assert 'id="floatingSearchInput"' in html
        assert 'id="downloadHinglishBtn"' in html
        assert 'id="downloadOrigBtn"' in html
        assert 'id="downloadTxtBtn"' in html
        assert 'class="theme-segmented-cluster"' in html

        # 6. Verify static/app.js handles synchronized search & compact GPU title
        assert "floatingSearchInput" in js
        assert "handleSubtitleSearch" in js





# =============================================================================
# 8. PACING MODE PROPERTY TESTS
# =============================================================================
class TestPacingModeProperties:
    def test_pacing_mode_random_properties(self):
        import random
        random.seed(1337)
        vocab = ["aur", "yeh", "video", "bahut", "achha", "hai", "isliye", "hum", "sab", "dekh", "rahe", "the", "marketing", "campaign"]

        for pacing in ["short", "long"]:
            max_dur = 2.8 if pacing == "short" else 5.0
            max_chars = 42 if pacing == "short" else 76

            for trial in range(30):
                n_words = random.randint(5, 30)
                words = []
                t = 0.0
                for _ in range(n_words):
                    dur = random.uniform(0.15, 0.8)
                    gap = random.uniform(0.0, 0.4)
                    t += gap
                    words.append({"start": round(t, 2), "end": round(t + dur, 2), "text": random.choice(vocab)})
                    t += dur

                cards = semantic_chunk(words, pacing=pacing)
                padded = pad_display_times(cards, pacing=pacing)

                # 1. No card exceeds max speech duration unless a single word does
                for c in cards:
                    span = c["end"] - c["start"]
                    n_w = len(c["text"].split())
                    if n_w > 1:
                        assert span <= max_dur * 1.6 + 1e-4, f"Card span {span} exceeded allowable speech span ({c})"

                # 2. Displayed time never overlaps the next card
                for i in range(len(padded) - 1):
                    assert padded[i]["end"] <= padded[i + 1]["start"] + 1e-4, (
                        f"Overlap detected: card {i} end {padded[i]['end']} > card {i+1} start {padded[i+1]['start']}"
                    )

                # 3. Char limits respected where words allow
                for c in cards:
                    text_len = len(c["text"])
                    # If card has multiple words, it should respect max_chars constraint
                    if len(c["text"].split()) > 1:
                        # Allow slight tolerance if words themselves are long
                        assert text_len <= max_chars + 15, f"Card text '{c['text']}' ({text_len} chars) exceeded limit {max_chars}"

    def test_floating_download_bar_option_a(self):
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="floatingMatchPill"' in html
        assert 'id="floatingMatchCountText"' in html
        assert 'id="floatingCopyAllBtn"' in html
        assert 'id="floatingCopyAllText"' in html

        with open("static/components.css", "r", encoding="utf-8") as f:
            css = f.read()
        assert ".live-match-pill" in css
        assert ".live-match-pill.is-active-match" in css
        assert "#floatingCopyAllBtn" in css

        with open("static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "function updateFloatingMatchPill" in js
        assert "floatingCopyAllBtn" in js
        assert "navigator.clipboard.writeText" in js

    def test_workbench_empty_state_dom_and_css(self):
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="workbenchEmptyState"' in html
        assert 'id="workbenchGrid"' in html
        assert 'id="workbenchImporterCard"' in html
        assert 'id="workbenchRecentsCard"' in html
        assert 'id="hideImporterBtn"' not in html
        assert 'id="hideRecentsBtn"' not in html
        assert 'id="urlImportInput"' in html
        assert 'id="urlFetchBtn"' in html
        assert 'id="sampleTrafficBtn"' in html
        assert 'id="sampleGeniusBtn"' in html

        with open("static/components.css", "r", encoding="utf-8") as f:
            css = f.read()
        assert ".workbench-empty-state" in css
        assert ".workbench-grid" in css
        assert ".btn-card-hide" in css
        assert ".url-import-input" in css
        assert ".sample-chip-btn" in css

        with open("static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "function initWorkbenchEmptyState" in js
        assert "function initUrlImporter" in js
        assert "function renderRecentTranscriptions" in js
        assert "function initSampleLoaders" in js

    def test_api_import_url_validation(self):
        from server import app
        from starlette.testclient import TestClient
        client = TestClient(app)

        # 1. Empty URL returns 400
        r_empty = client.post("/api/import-url", json={"url": ""})
        assert r_empty.status_code == 400

        # 2. Non-http URL returns 400
        r_invalid = client.post("/api/import-url", json={"url": "ftp://bad-url.com/video"})
        assert r_invalid.status_code == 400

        # 3. Sample files exist and are servable
        import os
        assert os.path.exists("static/samples/traffic.mp4")
        assert os.path.exists("static/samples/genius_ad.mp4")
        assert os.path.getsize("static/samples/traffic.mp4") > 1_000_000
        assert os.path.getsize("static/samples/genius_ad.mp4") > 1_000_000

    def test_url_importer_quality_and_format_options(self):
        """Tests UrlImportRequest model, MIME serving, and Option 1 frontend controls."""
        from server import UrlImportRequest, app
        from starlette.testclient import TestClient

        # 1. Model defaults and custom values
        req_default = UrlImportRequest(url="https://youtube.com/watch?v=123")
        assert req_default.media_type == "video"
        assert req_default.quality == "720p"

        req_audio = UrlImportRequest(url="https://youtube.com/watch?v=123", media_type="audio", quality="64k")
        assert req_audio.media_type == "audio"
        assert req_audio.quality == "64k"

        # 2. HTML elements for Option 1 exist
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        assert 'id="importerModeVideo"' in html
        assert 'id="importerModeAudio"' in html
        assert 'id="importerQualitySelect"' in html
        assert 'class="importer-controls-row"' in html

        # 3. JS implements Option 1 mode switcher and dynamic quality options
        with open("static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "importerModeVideo" in js
        assert "importerModeAudio" in js
        assert "importerQualitySelect" in js
        assert "renderQualityOptions" in js
        assert "setImporterMode" in js
        assert "media_type: mode" in js

    def test_hindi_to_english_translation_mode(self):
        """Verifies Hindi to English 5th ribbon tile and Whisper task=translate pipeline."""
        from hinglish_upgrades import transcribe_words
        import inspect

        # 1. transcribe_words supports task parameter
        sig = inspect.signature(transcribe_words)
        assert "task" in sig.parameters
        assert sig.parameters["task"].default == "transcribe"

        # 2. HTML contains 5th tile with data-lang="hi-en"
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        assert 'data-lang="hi-en"' in html
        assert "Hindi ➔ English" in html
        assert "--orange" in html

        # 3. CSS ribbon has 5-column grid
        with open("static/components.css", "r", encoding="utf-8") as f:
            css = f.read()
        assert "grid-template-columns: repeat(5, 1fr)" in css

        # 4. JS handles hi-en mode in cards and downloads
        with open("static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert 'selectedLanguage === "hi-en"' in js
        assert "TRANSLATED ENGLISH" in js
        assert "DOWNLOAD ENGLISH SRT" in js

    def test_settings_slide_over_drawer(self):
        """Verifies Option 1 Slide-Over Settings Drawer architecture."""
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()

        # 1. Top nav button exists with shortcut indicator
        assert 'id="openSettingsBtn"' in html
        assert 'class="settings-nav-btn"' in html
        assert 'SETTINGS' in html
        assert 'settings-kbd-hint' in html

        # 2. Main flow has permanent Topic Hints and dynamic controls
        assert 'id="mainDynamicControlsWrap"' in html
        assert 'id="mainDynamicControlsCard"' in html
        assert 'id="mainTopicHintGroup"' in html
        assert 'id="topicHintInput"' in html
        assert 'id="mainModelPills"' in html
        assert 'id="mainDevicePills"' in html
        assert 'id="mainPacingPills"' in html
        assert 'id="mainDiarizeGroup"' in html
        assert 'id="mainColLeft"' in html
        assert 'id="mainColRight"' in html

        # 3. Dedicated slide-over drawer and overlay exist
        assert 'id="settingsDrawer"' in html
        assert 'id="settingsDrawerOverlay"' in html
        assert 'id="settingsDrawerCloseBtn"' in html
        assert 'id="saveAndCloseSettingsBtn"' in html

        # 4. Core controls, Pin Switches, and Workbench Visibility toggles are in drawer
        drawer_slice = html[html.find('id="settingsDrawer"'):html.find('id="floatingDownloadBar"')]
        assert 'id="modelPills"' in drawer_slice
        assert 'id="devicePills"' in drawer_slice
        assert 'id="pacingPills"' in drawer_slice
        assert 'id="topicHintInput"' not in drawer_slice  # Permanently in main window
        assert 'id="preDownloadModelBtn"' in drawer_slice
        assert 'id="pinModelSwitch"' in drawer_slice
        assert 'id="pinHwSwitch"' in drawer_slice
        assert 'id="pinPacingSwitch"' in drawer_slice
        assert 'id="pinDiarizeSwitch"' in drawer_slice
        assert 'id="settingsShowImporterBtn"' in drawer_slice
        assert 'id="settingsHideImporterBtn"' in drawer_slice
        assert 'id="settingsShowRecentsBtn"' in drawer_slice
        assert 'id="settingsHideRecentsBtn"' in drawer_slice

        # 5. CSS defines drawer, card, button, pin-switch, and dynamic column styles
        with open("static/components.css", "r", encoding="utf-8") as f:
            css = f.read()
        assert ".settings-drawer" in css
        assert ".settings-nav-btn" in css
        assert ".settings-card" in css
        assert ".pin-switch" in css

        # 6. JS wires drawer toggle, keyboard shortcuts, dynamic pin layout, and workbench visibility
        with open("static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "openSettingsDrawer" in js
        assert "closeSettingsDrawer" in js
        assert "toggleSettingsDrawer" in js
        assert "openSettingsBtn" in js
        assert 'e.key === ","' in js
        assert "initPinSwitches" in js
        assert "updateDynamicControlsLayout" in js
        assert "pinnedModules" in js
        assert "mainDiarizeOnBtn" in js
        assert "setDiarization" in js
        assert "paintCaptionSample" in js
        assert "settingsShowImporterBtn" in js
        assert "settingsHideImporterBtn" in js

    def test_collapsible_left_subtitle_editor(self):
        """Verifies the production left editor replaces the old right inspector."""
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()

        assert 'id="workspaceShell"' in html
        assert 'id="subtitleEditor"' in html
        assert 'id="subtitleEditor" aria-label="Subtitle editor" hidden' in html
        assert 'id="editorSegmentsTab"' in html
        assert 'id="editorStyleTab"' in html
        assert 'id="editorSegmentsPanel"' in html
        assert 'id="editorStylePanel"' in html
        assert 'id="editorSegmentList"' in html
        assert 'id="editorCaptionInput"' in html
        assert 'id="editorStartInput"' in html
        assert 'id="editorEndInput"' in html
        assert 'id="editorSpeakerInput"' in html
        assert 'id="editorSaveBtn"' in html
        assert 'id="editorRevertBtn"' in html
        assert 'id="editorSeekBtn"' in html
        assert 'id="editorSearchInput"' in html
        assert 'id="editorCollapseBtn"' in html
        assert 'id="editorExpandBtn"' in html
        assert 'id="editorStylePresetGrid"' in html
        assert 'id="editorStyleFont"' in html
        assert 'id="editorStyleFontSize"' in html
        assert 'id="editorStyleBaseColor"' in html
        assert 'id="editorStyleHighlightColor"' in html
        assert 'id="editorStyleOutline"' in html
        assert 'id="editorStyleMargin"' in html
        assert 'id="editorStyleUppercase"' in html
        assert 'id="editorStyleBox"' in html
        assert 'id="editorStyleResetBtn"' in html

        # The old right inspector is retired in favour of the left editor.
        assert 'id="drawerOverlay"' not in html
        assert 'id="drawerHinglishInput"' not in html
        assert 'id="drawerSaveBtn"' not in html

        with open("static/components.css", "r", encoding="utf-8") as f:
            css = f.read()
        assert ".workspace-shell" in css
        assert ".subtitle-editor" in css
        assert ".subtitle-editor.is-collapsed" in css
        assert ".editor-segment-row" in css
        assert ".editor-inspector" in css
        assert ".editor-style-panel" in css
        assert ".subtitle-editor-rail" in css
        assert "body.editor-open .workspace-shell" in css
        assert "body.editor-open.editor-collapsed .workspace-shell" in css
        assert "@media (max-width: 1100px)" in css

        with open("static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "openSubtitleEditor" in js
        assert "closeSubtitleEditor" in js
        assert "setEditorCollapsed" in js
        assert "renderEditorList" in js
        assert "selectEditorSegment" in js
        assert "saveEditorSegment" in js
        assert "srtTimestamp" in js
        assert "queueEditorStyleSave" in js
        assert "editorStylePresetGrid" in js
        assert "subtitle_editor_collapsed" in js
        assert 'document.body.classList.add("editor-open")' in js
        assert "openSubtitleEditor();" in js
        assert "openDrawer(seg)" not in js


# =============================================================================
# 10. HINDI TO ENGLISH DEDICATED TRANSLATION ENGINE TESTS
# =============================================================================
class TestHindiToEnglishEngine:
    def test_translation_engine_structure_and_prompt(self):
        import hindi_to_english_engine
        assert hasattr(hindi_to_english_engine, "generate_english_subtitles")
        assert hasattr(hindi_to_english_engine, "ENGLISH_SUBTITLE_PROMPT")
        prompt = hindi_to_english_engine.ENGLISH_SUBTITLE_PROMPT
        # Prompt must be English, never Devanagari Hindi
        assert "English" in prompt
        assert "नमस्ते" not in prompt
        assert "video" not in prompt

    def test_server_routes_hi_en_to_dedicated_engine(self):
        with open("server.py", "r", encoding="utf-8") as f:
            code = f.read()
        assert 'if language == "hi-en":' in code
        assert 'from hindi_to_english_engine import generate_english_subtitles' in code

    def test_translation_engine_auto_routes_turbo_to_large_v3(self):
        # Verify code logic routes large-v3-turbo to full large-v3 for translation
        with open("hindi_to_english_engine.py", "r", encoding="utf-8") as f:
            code = f.read()
        assert 'if model_size == "large-v3-turbo":' in code
        assert 'active_model_size = "large-v3"' in code

    def test_model_visibility_filtering_logic(self):
        # Verify JS hides models incompatible with English translation
        with open("static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "ENGLISH_TRANSLATION_MODELS" in js
        assert "updateModelVisibilityForLanguage" in js
        assert 'ENGLISH_TRANSLATION_MODELS = ["small", "medium", "large-v3"]' in js

        # Verify server.py initial HTML hides incompatible models when hi-en is active
        with open("server.py", "r", encoding="utf-8") as f:
            py = f.read()
        assert 'sel_lang == "hi-en"' in py
        assert 'm_name not in ("small", "medium", "large-v3")' in py













