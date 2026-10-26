"""Tests for the Hinglish naturalisation layer (Step 2).

The ISO transliteration is a correct *spelling* of Hindi, which is not how anyone
writes Hinglish: it keeps the medial schwa and the long final vowel, so आपको comes
out 'aapako' and होना 'honaa'. These tests pin the reductions that make the output
read like speech, and just as importantly pin the cases they must NOT touch --
'chala' must not lose its vowel, 'banaya' must not lose its glide.
"""
import pytest

from transliteration import convert_to_hinglish, _transliterate_hindi_word_uncached as word_to_hinglish


class TestMedialSchwa:
    """Hindi drops the inherent vowel before the final syllable."""

    @pytest.mark.parametrize("deva,expected", [
        ("आपको", "aapko"),
        ("हमको", "hamko"),
        ("उसके", "uske"),
        ("इसके", "iske"),
        ("इसने", "isne"),
        ("उसने", "usne"),
        ("हमने", "hamne"),
        ("अपना", "apna"),
        ("अपनी", "apni"),
        ("करना", "karna"),
        ("करके", "karke"),
        ("करती", "karti"),
        ("करते", "karte"),
        ("बोलती", "bolti"),
        ("बोलता", "bolta"),
        ("मिलता", "milta"),
        ("देखते", "dekhte"),
        ("लगता", "lagta"),
        ("पहले", "pahle"),
        ("दूसरा", "doosra"),
        ("मतलब", "matlab"),
        ("समझना", "samajhna"),
        ("बोलना", "bolna"),
        ("पिछले", "pichhle"),
        ("कमरे", "kamre"),
        ("सबसे", "sabse"),
        ("आसपास", "aaspaas"),
        ("खरीदने", "khareedne"),
        ("डालने", "daalne"),
    ])
    def test_drops_the_schwa(self, deva, expected):
        assert word_to_hinglish(deva) == expected

    @pytest.mark.parametrize("deva,expected", [
        # 'cha' is an open syllable: dropping its vowel gives the illegal onset
        # 'chl', so चला must stay 'chala', not become 'chla'.
        ("चला", "chala"),
        ("चली", "chali"),
        ("कमल", "kamal"),
        # A glide is not a vowel to elide: बनाया is 'banaya', never 'banya'.
        ("बनाया", "banaya"),
        ("दिखाया", "dikhaya"),
        # व in the deleted position is a real consonant, so it may go: काशवी.
        ("काशवी", "kaashvi"),
    ])
    def test_keeps_vowels_it_must_not_drop(self, deva, expected):
        assert word_to_hinglish(deva) == expected

    def test_long_vowel_is_not_a_schwa(self):
        # बहाना has a long आ, so nothing is deleted: bahaana, not bahna.
        assert word_to_hinglish("बहाना") == "bahaana"
        # बहना has a short inherent vowel and does delete: bahna.
        assert word_to_hinglish("बहना") == "bahna"


class TestColloquialFinals:
    @pytest.mark.parametrize("deva,expected", [
        ("का", "ka"),
        ("होना", "hona"),
        ("रहा", "raha"),
        ("बना", "bana"),
        ("क्या", "kya"),
        ("जाता", "jaata"),
        ("दिया", "diya"),
        ("की", "ki"),
        ("ही", "hi"),
        ("जी", "ji"),
        ("कभी", "kabhi"),
        ("तू", "tu"),
        ("भाई", "bhaai"),
        ("आज", "aaj"),
        ("काम", "kaam"),
        ("बात", "baat"),
    ])
    def test_shortens_the_final_vowel(self, deva, expected):
        assert word_to_hinglish(deva) == expected

    def test_single_letter_word_keeps_its_length(self):
        # आ on its own is the long vowel, not a shortened final.
        assert word_to_hinglish("आ") == "aa"

    @pytest.mark.parametrize("deva,expected", [
        ("बनाया", "banaya"),
        ("दिखाया", "dikhaya"),
        ("बताया", "bataya"),
        ("खाया", "khaya"),
        # Word-initial आ is the long vowel on its own: आया is 'aaya', not 'aya'.
        ("आया", "aaya"),
        ("आये", "aaye"),
    ])
    def test_aay_shrinks_only_after_a_consonant(self, deva, expected):
        assert word_to_hinglish(deva) == expected

    def test_bata_is_not_baat(self):
        # Regression: the curated map had bata -> baat, which collided with the
        # verb बता once the schwa rules started producing 'bata'.
        assert word_to_hinglish("बता") == "bata"
        assert word_to_hinglish("बात") == "baat"


class TestRetroflexFlap:
    """ड़/ढ़ are /ɽ/, written d/dh in Hinglish."""

    @pytest.mark.parametrize("deva,expected", [
        ("कपड़े", "kapde"),
        ("करोड़", "karod"),
        ("थोड़ा", "thoda"),
        ("थोड़े", "thode"),
        ("लड़का", "ladka"),
        ("लड़की", "ladki"),
        ("बड़ा", "bada"),
        ("बड़ी", "badi"),
        ("पढ़ना", "padhna"),
        ("पढ़ती", "padhti"),
        ("बढ़ती", "badhti"),
        ("पड़ेगा", "padega"),
        ("वड़ापाव", "vadaapaav"),
    ])
    def test_flap_becomes_d(self, deva, expected):
        assert word_to_hinglish(deva) == expected

    def test_handles_both_encodings(self):
        # U+095C precomposed vs U+0921 U+093C; ASR emits the decomposed form.
        assert word_to_hinglish("\u0915\u092a\u095c\u0947") == "kapde"
        assert word_to_hinglish("\u0915\u092a\u0921\u093c\u0947") == "kapde"


class TestAspiration:
    @pytest.mark.parametrize("deva,expected", [
        ("पिछले", "pichhle"),
        ("पीछे", "peechhe"),
        ("अच्छा", "achha"),
        ("अच्छे", "achhe"),
        ("छोटे", "chhote"),
        ("पूछा", "poochha"),
        ("कुछ", "kuch"),
    ])
    def test_no_triple_h(self, deva, expected):
        # The letter map used to run 'ch'->'chh' then 'c'->'ch' over its own
        # output, producing 'pichhhale'.
        assert word_to_hinglish(deva) == expected
        assert "hhh" not in word_to_hinglish(deva)


class TestSpellingFixes:
    @pytest.mark.parametrize("deva,expected", [
        ("किजिए", "kijiye"),
        ("चलिए", "chaliye"),
        ("उसमें", "usmein"),
        ("इसमें", "ismein"),
        ("जिसमें", "jismein"),
        ("में", "mein"),
        ("हैं", "hain"),
        ("हूं", "hoon"),
    ])
    def test_targeted_fixes(self, deva, expected):
        assert word_to_hinglish(deva) == expected


class TestLoanwords:
    @pytest.mark.parametrize("deva,expected", [
        ("मूवी", "movie"),
        ("मुवी", "movie"),
        ("वीडियो", "video"),
        ("मोबाइल", "mobile"),
    ])
    def test_known_loanwords_stay_english(self, deva, expected):
        assert word_to_hinglish(deva) == expected


class TestAnusvara:
    """Anusvara/candrabindu before a consonant is 'n' -- 'm' only before a labial."""

    @pytest.mark.parametrize("deva,expected", [
        # The old final-only cleanup wrote ISO's 'm' straight through mid-word:
        # zimdagi, amdaaj, imsaan, ramgeen.
        ("ज़िंदगी", "zindagi"),
        ("अंदाज", "andaaj"),
        ("इंसान", "insaan"),
        ("संगीत", "sangeet"),
        ("रंग", "rang"),
        ("रंगीन", "rangeen"),
        ("जंगल", "jangal"),
        ("मंदिर", "mandir"),
        ("बंद", "band"),
        ("पसंद", "pasand"),
        ("हिंदी", "hindi"),
        ("गंदा", "ganda"),
        ("कंधा", "kandha"),
        ("अंत", "ant"),
        ("अंतर", "antar"),
        ("संसार", "sansaar"),
        ("इंतजार", "intajaar"),
        ("घंटे", "ghante"),
        ("पंजाब", "panjaab"),
        ("इंच", "inch"),
    ])
    def test_medial_anusvara_becomes_n(self, deva, expected):
        assert word_to_hinglish(deva) == expected

    @pytest.mark.parametrize("deva,expected", [
        # Before a labial the nasal is /m/: Ambani, sambhav, company.
        ("अंबानी", "ambaani"),
        ("संभव", "sambhav"),
        ("कंपनी", "kampani"),
        ("संपर्क", "sampark"),
    ])
    def test_anusvara_before_a_labial_stays_m(self, deva, expected):
        assert word_to_hinglish(deva) == expected

    def test_candrabindu_is_a_nasal_too(self):
        # पहुँच has a candrabindu (not an anusvara) and must still lose the 'm'.
        assert word_to_hinglish("पहुँच") == "pahunch"

    def test_a_real_ma_is_never_touched(self):
        # कमरा and नमक spell म with a real letter: the rule must not see them.
        assert word_to_hinglish("कमरा") == "kamra"
        assert word_to_hinglish("नमक") == "namak"


class TestFAndW:
    """/f/ and /v~w/ are two Hinglish spellings of one Devanagari letter each."""

    @pytest.mark.parametrize("deva,expected", [
        ("साफ", "saaf"),
        ("माफ", "maaf"),
        ("माफी", "maafi"),
        ("इंसाफ", "insaaf"),
        ("काफी", "kaafi"),
        ("तरफ", "taraf"),
        ("सिर्फ", "sirf"),
        ("फायदा", "fayda"),
        ("फुर्सत", "fursat"),
        ("फौज", "fauj"),
        ("सफर", "safar"),
    ])
    def test_f_words_are_spelled_with_f(self, deva, expected):
        assert word_to_hinglish(deva) == expected

    @pytest.mark.parametrize("deva,expected", [
        # Native /pʰ/ keeps 'ph'; these must not be swept up by the f rule.
        ("फिर", "phir"),
        ("फूल", "phool"),
        ("फल", "phal"),
        ("फंस", "phans"),
        ("फटाफट", "phataaphat"),
        ("सफल", "saphal"),
    ])
    def test_native_ph_is_not_converted_to_f(self, deva, expected):
        assert word_to_hinglish(deva) == expected

    @pytest.mark.parametrize("deva,expected", [
        ("वाला", "wala"),
        ("वाली", "wali"),
        ("वाले", "wale"),
        ("वालों", "walon"),
        ("वापस", "wapas"),
        ("वो", "wo"),
        ("वही", "wahi"),
        ("वहीं", "wahin"),
        ("वहाँ", "wahaan"),
        ("वजह", "wajah"),
        ("वक्त", "waqt"),
        ("वरना", "warna"),
        ("सवाल", "sawaal"),
        ("वगेरा", "wagera"),
    ])
    def test_native_va_is_spelled_with_w(self, deva, expected):
        assert word_to_hinglish(deva) == expected

    @pytest.mark.parametrize("deva,expected", [
        # English loans keep 'v': the w list must not leak into them.
        ("वीडियो", "video"),
        ("विचार", "vichaar"),
        ("विदेश", "videsh"),
        ("व्यक्ति", "vyakti"),
        ("वीर", "veer"),
    ])
    def test_loan_v_is_not_converted_to_w(self, deva, expected):
        assert word_to_hinglish(deva) == expected


class TestEnglishFLoans:
    """English /f/ words written in Devanagari come out as English, not 'ph'."""

    @pytest.mark.parametrize("deva,expected", [
        ("फोन", "phone"),
        ("फेमस", "famous"),
        ("फुल", "full"),
        ("फील", "feel"),
        ("लाइफ", "life"),
        ("फाइल", "file"),
        ("आफ", "off"),
        ("फैमिली", "family"),
        ("फाइनल", "final"),
    ])
    def test_loanwords_take_their_english_spelling(self, deva, expected):
        assert word_to_hinglish(deva) == expected

    def test_long_oo_is_the_flower_not_the_adjective(self):
        # फूल (long ū) is the Hindi flower; फुल (short u) is English 'full'.
        assert word_to_hinglish("फूल") == "phool"
        assert word_to_hinglish("फुल") == "full"


class TestNasalFinal:
    def test_men_is_mein_only_when_the_source_ends_in_a_nasal(self):
        # में and its compounds carry the anusvara.
        assert word_to_hinglish("उसमें") == "usmein"
        assert word_to_hinglish("में") == "mein"
        # रमेन ends in a real न: it is 'ramen', never 'ramein'.
        assert word_to_hinglish("रमेन") == "ramen"
        assert word_to_hinglish("अमेन") == "amen"



class TestSentenceLevel:
    def test_what_the_user_reads(self):
        # The exact caption that used to read 'white cooperation tight band'.
        out = convert_to_hinglish("इसने अपना Levi's को white कपड़े से tight band दिया।")
        assert "kapde" in out
        assert "apna" in out
        assert "isne" in out
        assert "diya" in out
        assert "cooperation" not in out

    def test_no_rule_empties_a_word(self):
        for deva in ("आ", "का", "है", "और", "में", "था", "हो", "न"):
            assert word_to_hinglish(deva), f"{deva!r} produced an empty string"
