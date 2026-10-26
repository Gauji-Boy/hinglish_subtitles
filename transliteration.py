"""
transliteration.py - Universal Hindi & Urdu (Hindustani) to Conversational Hinglish Engine.
Converts both Devanagari (Hindi) and Perso-Arabic (Urdu) scripts into natural,
readable Latin-script Hinglish, while leaving English words and numbers untouched.
"""

import re
import unicodedata
from aksharamukha import transliterate

# Common tech, social media and loanwords that Whisper often writes in Devanagari
COMMON_LOANWORDS = {
    'वीडियो': 'video',
    'विड़ियो': 'video',
    'विडियो': 'video',
    'चैनल': 'channel',
    'सब्सक्राइब': 'subscribe',
    'सबस्क्राइब': 'subscribe',
    'लाइक': 'like',
    'शेयर': 'share',
    'कमेंट': 'comment',
    'कमेंट्स': 'comments',
    'लिंक': 'link',
    'ऐप': 'app',
    'एप्लीकेशन': 'application',
    'वेबसाइट': 'website',
    'कंप्यूटर': 'computer',
    'इंटरनेट': 'internet',
    'मोबाइल': 'mobile',
    'मूवी': 'movie',
    'मुवी': 'movie',
    'स्क्रीन': 'screen',
    'क्लिक': 'click',
    'डाउनलोड': 'download',
    'अपलोड': 'upload',
    'फॉलो': 'follow',
    'बटन': 'button',
    'सॉफ्टवेयर': 'software',
    'कोड': 'code',
    'कोडिंग': 'coding',
    'प्रोग्राम': 'program',
    'प्रोजेक्ट': 'project',
    'ट्यूटोरियल': 'tutorial',
    'ऑनलाइन': 'online',
    'ऑफलाइन': 'offline',
    'यूट्यूब': 'YouTube',
    'गूगल': 'Google',
    'फेसबुक': 'Facebook',
    'इंस्टाग्राम': 'Instagram',
    'ट्विटर': 'Twitter',
    'व्हाट्सएप': 'WhatsApp',
    'हाय': 'Hi',
    'हेलो': 'Hello',
    'ओके': 'Okay',
    'थैंक्यू': 'Thank you',
    'थैंक्स': 'Thanks',
    'प्लीज': 'Please',
    'वेलकम': 'Welcome',
    'बाय': 'Bye',
    'वेट': 'wait',
    'सेकंड': 'second',
    'मिनट': 'minute',
    'टाइम': 'time',
    'पोस्ट': 'post',
    'मैसेज': 'message',
    'कृपया': 'kripya',
    'नीचे': 'neeche',
    'ऊपर': 'upar',
    'आसान': 'aasan',
    'ट्रैफिक': 'traffic',
    'त्रैफिक': 'traffic',
    'जाम': 'jam',
    'रेवेन्यू': 'revenue',
    'रेवेन्वू': 'revenue',
    'रेवेनु': 'revenue',
    'मंथली': 'monthly',
    'मन्सली': 'monthly',
    'पैकेज': 'package',
    'पैकेजिंग': 'packaging',
    'पैकेजिन': 'packaging',
    'वाडापाव': 'Vada Pav',
    'वडापाव': 'Vada Pav',
    'वाटर': 'water',
    'बोटल': 'bottle',
    'टिश्यू': 'tissue',
    'तीसु': 'tissue',
    'तीसू': 'tissue',
    'तीसुपेपर': 'tissue paper',
    'हाइजीन': 'hygiene',
    'हाईजीन': 'hygiene',
    'हाईजी': 'hygiene',
    'टैलेंट': 'talent',
    'तालेंट': 'talent',
    'एग्जीक्यूशन': 'execution',
    'एकजिकॉषन': 'execution',
    'प्रॉब्लम': 'problem',
    'प्रोब्लम': 'problem',
    'स्मार्टली': 'smartly',
    'स्मार्ट': 'smart',
    'मुमभाई': 'Mumbai',
    'मुंबई': 'Mumbai',
    'परेशानी': 'pareshani',
    'पडेशानी': 'pareshani',
    'लाख': 'lakh',
    'प्लस': 'plus',
    'पलस': 'plus',
}

# Hindustani words of Perso-Arabic origin that are pronounced with /f/ but written
# with फ (not फ़) in Devanagari, because ASR and everyday writing drop the nukta.
# फ spells two sounds -- native /pʰ/ (phir, phool, phal) and borrowed /f/ (saaf,
# kaafi, taraf) -- and the script does not separate them, so the Hinglish spelling
# has to come from a word list. This list holds the /f/ words; native /pʰ/ words are
# deliberately absent and keep their 'ph'. English /f/ loanwords (फोन, फिल्म) are a
# different class: they belong in COMMON_LOANWORDS and come out as English.
F_WORDS = {
    'साफ': 'saaf',
    'माफ': 'maaf',
    'माफी': 'maafi',
    'इंसाफ': 'insaaf',
    'काफी': 'kaafi',
    'काफि': 'kaafi',
    'तरफ': 'taraf',
    'तरफ़': 'taraf',
    'सिर्फ': 'sirf',
    'फायदा': 'fayda',
    'फाइदा': 'fayda',
    'फाइडा': 'fayda',
    'फायदे': 'fayde',
    'फुर्सत': 'fursat',
    'फौज': 'fauj',
    'फौरन': 'fauran',
    'सफर': 'safar',
}

# व is /ʋ/, and Hinglish splits it by etymology: 'w' in native words (wala, wapas,
# wo, sawaal) and 'v' in the English loans that keep their spelling (video, viral,
# device). Devanagari writes both with व, so -- exactly like /f/ above -- the split
# cannot be derived from the spelling and needs a word list. These are the native
# words that occur in speech; everything else is left to the general rules.
W_WORDS = {
    'वो': 'wo',
    'वही': 'wahi',
    'वहीं': 'wahin',
    'वहाँ': 'wahaan',
    'वहां': 'wahaan',
    'वाला': 'wala',
    'वाली': 'wali',
    'वाले': 'wale',
    'वालों': 'walon',
    'वापस': 'wapas',
    'वजह': 'wajah',
    'वक्त': 'waqt',
    'वरना': 'warna',
    'वादा': 'wada',
    'वाह': 'waah',
    'सवाल': 'sawaal',
    'वगेरा': 'wagera',
    'वगरा': 'wagera',
    'वागरा': 'wagera',
    'वागरे': 'wagere',
}

# Common Hindi conversational word mappings to produce natural social-media Hinglish
# instead of formal Sanskritized Roman spellings
HINDI_CONVERSATIONAL_MAP = {
    'hama': 'hum',
    'ham': 'hum',
    'hamaara': 'hamara',
    'hamaare': 'hamare',
    'hamaari': 'hamari',
    'isa': 'is',
    'usa': 'us',
    'kisa': 'kis',
    'jisa': 'jis',
    'eka': 'ek',
    'aja': 'aaj',
    'aura': 'aur',
    'kama': 'kaam',
    'nama': 'naam',
    'loga': 'log',
    'bahuta': 'bahut',
    'yaha': 'yeh',
    'yah': 'yeh',
    'vaha': 'woh',
    'vah': 'woh',
    'kucha': 'kuch',
    'kuchh': 'kuch',
    'saba': 'sab',
    'apana': 'apna',
    'apani': 'apni',
    'apane': 'apne',
    'karega': 'karega',
    'karemge': 'karenge',
    'karenge': 'karenge',
    'karem': 'karen',
    'karen': 'karen',
    'haim': 'hain',
    'hai': 'hai',
    'mem': 'mein',
    'men': 'mein',
    'nahim': 'nahin',
    'nahin': 'nahin',
    'karana': 'karna',
    'karane': 'karne',
    'karani': 'karni',
    'dekhana': 'dekhna',
    'dekhane': 'dekhne',
    'sikhana': 'seekhna',
    'sikhane': 'seekhne',
    'seekhana': 'seekhna',
    'seekhanaa': 'seekhna',
    'kyomki': 'kyunki',
    'kyonki': 'kyunki',
    'kaise': 'kaise',
    'vaise': 'waise',
    'jaise': 'jaise',
    'kab': 'kab',
    'tab': 'tab',
    'jab': 'jab',
    'aapa': 'aap',
    'aap': 'aap',
    'tumhaara': 'tumhara',
    'tumhaare': 'tumhare',
    'tumhaari': 'tumhari',
    'mera': 'mera',
    'mere': 'mere',
    'meri': 'meri',
    'teraa': 'tera',
    'tere': 'tere',
    'teri': 'teri',
    'bhai': 'bhai',
    'dosta': 'dost',
    'dost': 'dost',
    'dostom': 'doston',
    'doston': 'doston',
    'samajha': 'samajh',
    'samajhana': 'samajhna',
    'sakata': 'sakta',
    'sakate': 'sakte',
    'sakati': 'sakti',
    'raha': 'raha',
    'rahe': 'rahe',
    'rahi': 'rahi',
    'tha': 'tha',
    'the': 'the',
    'thi': 'thi',
    'hota': 'hota',
    'hote': 'hote',
    'hoti': 'hoti',
    'hoga': 'hoga',
    'hoge': 'hoge',
    'hogi': 'hogi',
    'lekin': 'lekin',
    'magar': 'magar',
    'par': 'par',
    'sirf': 'sirf',
    'sirfa': 'sirf',
    'krpaya': 'kripya',
    'krpayaa': 'kripya',
    'diyaa': 'diya',
    'gayaa': 'gaya',
    'kiyaa': 'kiya',
    'liyaa': 'liya',
    'mumbaee': 'mumbai',
    'mumabhaaee': 'Mumbai',
    'traiphika': 'traffic',
    'traiphik': 'traffic',
    'tumhaaree': 'tumhare',
    'lie': 'liye',
    'usee': 'usi',
    'bandene': 'bande ne',
    'padeshaanee': 'pareshani',
    'minad': 'minute',
    'phuj': 'phans',
    'bhoog': 'bhookh',
    'laagee': 'lagi',
    'chaahee': 'chahiye',
    'saam': 'shaam',
    'vaadaapaav': 'Vada Pav',
    'vaadaa': 'Vada',
    'paav': 'Pav',
    'vaatar': 'water',
    'botal': 'bottle',
    'teesupepar': 'tissue paper',
    'paikejin': 'packaging',
    'paikej': 'package',
    'haaeejee': 'hygiene',
    'taalemt': 'talent',
    'ekajikoshan': 'execution',
    'agjikoshan': 'execution',
    'surpiyaa': 'rupaye',
    'bestaagaa': 'bechta tha',
    'besataagaa': 'bechta tha',
    'surv': 'shuru',
    'mahanat': 'mehnat',
    'ramg': 'rang',
    'laayaa': 'laya',
    'palas': 'plus',
    'probalam': 'problem',
    'problam': 'problem',
    'sulb': 'solve',
    'indyaa': 'India',
    'kamee': 'kami',
    'naheen': 'nahin',
    'mansalee': 'monthly',
    'mamtree': 'monthly',
    'revenvoo': 'revenue',
}

# Perso-Arabic / Urdu character transliteration map
URDU_CHAR_MAP = {
    'ا': 'a', 'آ': 'aa', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ٹ': 't', 'ث': 's',
    'ج': 'j', 'چ': 'ch', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ڈ': 'd', 'ذ': 'z',
    'ر': 'r', 'ڑ': 'r', 'ز': 'z', 'ژ': 'zh', 'س': 's', 'ش': 'sh', 'ص': 's',
    'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'q',
    'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm', 'ن': 'n', 'ں': 'n', 'و': 'o',
    'ہ': 'h', 'ۂ': 'h', 'ۃ': 'h', 'ھ': 'h', 'ء': '', 'ی': 'i', 'ے': 'e',
    'ئ': 'i', 'ؤ': 'o', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5'
}

# High-frequency Hindustani / Urdu words dictionary for 100% natural conversational spelling
URDU_WORD_MAP = {
    'تمہارے': 'tumhare', 'تمہاری': 'tumhari', 'تمہارا': 'tumhara',
    'لیے': 'liye', 'لئے': 'liye', 'ٹریفک': 'traffic', 'بڑی': 'badi', 'بڑا': 'bada', 'بڑے': 'bade',
    'شانی': 'shaani', 'شاندار': 'shandar', 'ہے': 'hai', 'ہیں': 'hain', 'جب': 'jab', 'لوگ': 'log',
    'شام': 'shaam', 'کو': 'ko', 'کام': 'kaam', 'سے': 'se', 'آتے': 'aate', 'آتی': 'aati', 'آتا': 'aata',
    'تھے': 'the', 'تھی': 'thi', 'تھا': 'tha', 'تو': 'to', 'ممبئی': 'mumbai', 'میں': 'mein',
    'بیس': 'bees', 'پینتالیس': 'paintalis', 'منٹ': 'minute',
    'تک': 'tak', 'جام': 'jam', 'پھنس': 'phans', 'فتح': 'phans', 'جاتا': 'jata', 'جاتے': 'jaate',
    'یہ': 'yeh', 'وہ': 'woh', 'اس': 'is', 'ان': 'un', 'بندے': 'bande', 'بندہ': 'banda',
    'نے': 'ne', 'پھر': 'phir', 'اور': 'aur', 'کا': 'ka', 'کے': 'ke', 'کی': 'ki',
    'ایک': 'ek', 'کر': 'kar', 'رہا': 'raha', 'رہے': 'rahe', 'رہی': 'rahi', 'نہیں': 'nahin',
    'بہت': 'bahut', 'ویڈیو': 'video', 'چینل': 'channel', 'سبسکرائب': 'subscribe',
    'لائک': 'like', 'شیئر': 'share', 'کمنٹ': 'comment', 'راک': 'rock', 'پلس': 'plus',
    'ریستوں': 'restore', 'ہم': 'hum', 'ہمارا': 'hamara', 'ہمارے': 'hamare', 'ہماری': 'hamari',
    'آپ': 'aap', 'کیوں': 'kyun', 'کیونکہ': 'kyunki', 'کیسے': 'kaise', 'ایسے': 'aise', 'ویسے': 'waise',
    'بات': 'baat', 'کرنا': 'karna', 'کرنے': 'karne', 'دیکھنا': 'dekhna', 'دیکھنے': 'dekhne',
}


# ---------------------------------------------------------------------------
# Token cache
#
# `transliterate.process` (aksharamukha) dominates the conversion: a 400-word
# reel calls it once per word and spoken Hinglish repeats a small vocabulary
# ("hai", "to", "mein", "ka", "ki", ...). Cache the finished Latin form per
# token. The cache is bounded and cleared wholesale when it fills: the working
# set for one clip is a few hundred entries, so an LRU would add bookkeeping for
# no measurable benefit.
# ---------------------------------------------------------------------------
_TOKEN_CACHE: dict = {}
_TOKEN_CACHE_MAX = 8192


def _remember_token(token: str, value: str) -> None:
    if len(_TOKEN_CACHE) >= _TOKEN_CACHE_MAX:
        _TOKEN_CACHE.clear()
    _TOKEN_CACHE[token] = value


def _transliterate_hindi_word(word: str) -> str:
    cached = _TOKEN_CACHE.get(word)
    if cached is not None:
        return cached
    value = _transliterate_hindi_word_uncached(word)
    _remember_token(word, value)
    return value


def _transliterate_urdu_word(word: str) -> str:
    cached = _TOKEN_CACHE.get(word)
    if cached is not None:
        return cached
    value = _transliterate_urdu_word_uncached(word)
    _remember_token(word, value)
    return value


# Devanagari flaps ड़/ढ़ are /ɽ/ /ɽʱ/, which Hinglish writes as d / dh:
# kapde, thoda, ladka, karod, padhna. ISO renders them ṛ / ṛh, and the NFKD
# strip then turns ṛ into a plain r -- that is where 'kapare', 'karor',
# 'larakee' and 'parhanaa' came from. Mapping them to the plain retroflex
# stop first lets the existing transliteration produce d / dh.
# They arrive both precomposed (U+095C/095D) and as stop + nukta, and ASR
# output uses the decomposed form.
_FLAP_REPLACEMENTS = (
    ("\u0921\u093c", "\u0921"),
    ("\u0922\u093c", "\u0922"),
    ("\u095c", "\u0921"),
    ("\u095d", "\u0922"),
)


def _flatten_flaps(word: str) -> str:
    for flap, stop in _FLAP_REPLACEMENTS:
        word = word.replace(flap, stop)
    return word


# Anusvara (ं) and candrabindu (ँ) before a consonant are written 'n' in Hinglish,
# except before a labial, where the nasal assimilates to 'm':
#   ज़िंदगी zindagi, अंदाज andaz, इंसान insaan, पसंद pasand, रंग rang
#   अंबानी Ambani, संभव sambhav, कंपनी company
# The ISO transliteration renders both marks as 'm' and the old final-only cleanup
# only fixed the last letter, so every medial one leaked: zimdagi, amdaaj, ramgeen.
# Substituting the nasal *consonant* the mark stands for, before transliterating,
# keeps the rule in one place and leaves a genuine म (कमरा, नमक) untouched.
_NASAL_MARKS = ("\u0901", "\u0902")
_LABIAL_CONSONANTS = "पफबभमव"


def _assimilate_nasals(word: str) -> str:
    """Spell a medial anusvara/candrabindu as the nasal consonant it sounds like."""
    out = []
    for i, ch in enumerate(word):
        if ch in _NASAL_MARKS and i + 1 < len(word):
            out.append("\u092e\u094d" if word[i + 1] in _LABIAL_CONSONANTS else "\u0928\u094d")
        else:
            out.append(ch)
    return "".join(out)

_CONSONANTS = "bcdfghjklmnpqrstvwxyz"
_VOWELS = "aeiou"

# Two- and three-letter spellings of a single Hindi consonant. Needed to know
# whether the syllable before a schwa is open: 'cha' in चला is one consonant
# plus a vowel, so dropping its schwa gives the illegal onset 'chl'.
_CONSONANT_UNITS = ("chh", "ch", "sh", "kh", "gh", "jh", "th", "dh", "ph",
                    "bh", "rh", "lh")


def _unit_length_before(word: str, index: int) -> int:
    """Length of the consonant spelling ending just before `index`."""
    for unit in _CONSONANT_UNITS:
        if word[max(0, index - len(unit)):index] == unit:
            return len(unit)
    return 1


def _naturalise_hinglish(ascii_str: str) -> str:
    """Apply the reductions Hindi speakers actually make when writing Hinglish.

    The ISO transliteration is a faithful *spelling*, so it keeps every inherent
    vowel and every long final vowel. Nobody writes that: भाषा-style spelling
    gave 'aapako', 'usake', 'isane', 'bolatee', 'karanaa', 'honaa'. Speech drops
    the medial schwa and shortens the final vowel, and romanised Hinglish follows
    speech: aapko, uske, isne, bolti, karna, hona.

    Kept deliberately conservative: exactly one medial schwa (the rightmost), only
    when the syllable before it is open, and never before a glide, because
    'banaya' must not become 'banya' and 'chala' must not become 'chla'.
    """
    # च्छ is written 'chh' in Hinglish, not the 'ch' + 'chh' the letter map emits.
    ascii_str = ascii_str.replace("chchh", "chh")

    # किजिए -> kijiye (इए is written iye, not ie).
    ascii_str = re.sub(r"ie$", "iye", ascii_str)

    # Drop the rightmost medial schwa.
    for i in range(len(ascii_str) - 3, 1, -1):
        if (ascii_str[i] == "a"
                and ascii_str[i - 1] in _CONSONANTS
                and ascii_str[i + 1] in _CONSONANTS and ascii_str[i + 1] != "y"
                and ascii_str[i + 2] in _VOWELS
                and i - _unit_length_before(ascii_str, i) - 1 >= 0
                and ascii_str[i - _unit_length_before(ascii_str, i) - 1] in _VOWELS):
            ascii_str = ascii_str[:i] + ascii_str[i + 1:]
            break

    # Colloquial finals: kaa -> ka, bolatee -> bolti, too -> tu. A single letter
    # is left alone: आ on its own stays 'aa'.
    if len(ascii_str) > 1:
        ascii_str = re.sub(r"aa$", "a", ascii_str)
        ascii_str = re.sub(r"ee$", "i", ascii_str)
        ascii_str = re.sub(r"oo$", "u", ascii_str)
        # बनाया: 'aaya' is written 'aya' -- but only after a consonant. Word-initial
        # आया is 'aaya', and the plain rule was turning it into 'aya'.
        ascii_str = re.sub(r"(?<=[bcdfghjklmnpqrstvwxyz])aay([aeiou])", r"ay\1", ascii_str)
    return ascii_str


def _transliterate_hindi_word_uncached(word: str) -> str:
    """Converts a single Devanagari word into natural Latin Hinglish."""
    clean_devanagari = word.strip()
    if clean_devanagari in COMMON_LOANWORDS:
        return COMMON_LOANWORDS[clean_devanagari]
    if clean_devanagari in F_WORDS:
        return F_WORDS[clean_devanagari]
    if clean_devanagari in W_WORDS:
        return W_WORDS[clean_devanagari]

    # में and its compounds end in a nasal mark: उसमें -> usmein, not usmen. Only
    # a word that really carries the mark is rewritten -- रमेन is 'ramen', and the
    # old unguarded rule turned every word ending in 'men' into 'mein'.
    ends_with_nasal = bool(re.search(r"[\u0901\u0902]$", clean_devanagari))

    clean_devanagari = _flatten_flaps(clean_devanagari)
    clean_devanagari = _assimilate_nasals(clean_devanagari)

    # Aksharamukha ISO transliteration
    iso = transliterate.process('Devanagari', 'ISO', clean_devanagari)
    
    # In ISO transliteration, Devanagari 'च' is 'c' and 'छ' is 'ch'.
    # In English/Hinglish, 'ch' is used for 'च' and 'chh' for 'छ'.
    # One pass, because the first rule's output ('chh') was being re-matched by
    # the second, which is why पिछले came out as 'pichhhale' with three h's.
    iso = re.sub(r'ch|c', lambda m: 'chh' if m.group() == 'ch' else 'ch', iso)
    
    # Map long vowels and specific letters
    iso = (
        iso.replace('ā', 'aa')
           .replace('ī', 'ee')
           .replace('ū', 'oo')
           .replace('ō', 'o')
           .replace('ē', 'e')
           .replace('ś', 'sh')
           .replace('ṣ', 'sh')
    )
    
    # Strip any remaining diacritics to clean ASCII
    ascii_str = unicodedata.normalize('NFKD', iso).encode('ASCII', 'ignore').decode('utf-8')
    
    # Clean up nasalized endings (anusvara)
    ascii_str = re.sub(r'em$', 'en', ascii_str)
    ascii_str = re.sub(r'aim$', 'ain', ascii_str)
    ascii_str = re.sub(r'om$', 'on', ascii_str)
    ascii_str = re.sub(r'im$', 'in', ascii_str)
    ascii_str = re.sub(r'um$', 'un', ascii_str)
    ascii_str = re.sub(r'm$', 'n', ascii_str)
    
    # Verbs ending in -naa or -na (e.g. seekhanaa -> seekhna, dekhanaa -> dekhna)
    ascii_str = re.sub(r'([bdfghjklmnpqrstvwxyz])a([bdfghjklmnpqrstvwxyz])naa?$', r'\1\2na', ascii_str)
    
    # Trailing schwa deletion for words ending in consonant + single 'a'.
    # 'ha' is NOT exempt: the old exception left कुछ as 'kuchha', साथ as 'saatha'
    # and देख as 'dekha' -- 40 words on four clips. यह/वह are handled by the
    # curated map instead, which is where a judgement call belongs.
    if ascii_str.endswith('a') and len(ascii_str) > 2 and not ascii_str.endswith(('aa', 'ia', 'ya')):
        ascii_str = ascii_str[:-1]

    # Check conversational map (curated first, keyed on the spelling form)
    lower = ascii_str.lower()
    if lower in HINDI_CONVERSATIONAL_MAP:
        return HINDI_CONVERSATIONAL_MAP[lower]

    # A one-letter word is a bare vowel: आ stays 'aa', it is not a shortened final.
    if len(clean_devanagari) > 1:
        ascii_str = _naturalise_hinglish(ascii_str)

    if ends_with_nasal:
        ascii_str = re.sub(r"men$", "mein", ascii_str)

    return ascii_str


def _transliterate_urdu_word_uncached(word: str) -> str:
    """Converts a single Perso-Arabic / Urdu word into natural Latin Hinglish."""
    clean_urdu = word.strip()
    if clean_urdu in URDU_WORD_MAP:
        return URDU_WORD_MAP[clean_urdu]

    # Fallback letter-by-letter mapping
    chars = [URDU_CHAR_MAP.get(c, c) for c in clean_urdu]
    res = ''.join(chars)
    
    # Clean vowel transitions
    res = re.sub(r'oo$', 'o', res)
    res = re.sub(r'ee$', 'i', res)
    return res


# Common colloquial phrase normalizations for reels, business and spoken Hinglish
PHRASE_NORMALIZATION = [
    (r'\b(reve\s*nu|reve\s*noo|revenvoo|levenvoo|devenvoo)\b', 'revenue'),
    (r'\b(do|2)\s*(laa[kp]|laa)\s*(plus|palas)\b', '2 lakh plus'),
    (r'\b(dolaa|dolaap)\s*(plus|palas)\b', '2 lakh plus'),
    (r'\b(amdyaa|indyaa|imdiyaa)\b', 'India'),
    (r'\b(kee)\b', 'ki'),
    (r'\b(bhee)\b', 'bhi'),
    (r'\b(avar daa taaem|ab avar daa taaem)\b', 'over the time'),
    (r'\b(bhee surpiyaa|bees surpiyaa|surpiyaa)\b', 'bees rupaye'),
    (r'\b(vaadaa?\s*paav|vaadaapaav)\b', 'Vada Pav'),
    (r'\b(vaatar\s*botal)\b', 'water bottle'),
    (r'\b(teesoo\s*pepar|teesupepar|tissue\s*pepar)\b', 'tissue paper'),
    (r'\b(pepar)\b', 'paper'),
    (r'\b(phuj\s*jaataa?taa?|phans\s*jaataataa)\b', 'phans jaate the'),
    (r'\b(bhoog\s*laagee\s*tee|buk\s*laagee\s*thee|bhookh\s*lagi\s*tee)\b', 'bhookh lagi thi'),
    (r'\b(chaahee\s*hai\s*taa|chaahee\s*taa|chahiye\s*hai\s*taa)\b', 'chahiye tha'),
    (r'\b(samaathalee|smaathalee)\b', 'smartly'),
    (r'\b(ekajeekoshan|ekajikoshan|agjikoshan)\b', 'execution'),
    (r'\bis\s*taart\b', 'start'),
    (r'\bbeshataagaa\b', 'bechta tha'),
]


def convert_to_hinglish(text: str) -> str:
    """
    Takes any text (Devanagari Hindi, Perso-Arabic Urdu, English, or Code-mixed).
    Converts both Devanagari and Urdu portions into Latin script Hinglish,
    leaving English words, numbers, and symbols untouched.
    """
    if not text:
        return ""

    # The danda (।) and double danda (॥) are sentence marks, but Aksharamukha
    # renders them as a period *inside* the word, which defeats the anusvara
    # rules anchored at the end of the token: "हैं।" came out "haim." and
    # "लोग।" came out "loga." while the same words without the mark were
    # correct. The punctuation below is already split off, so normalise the
    # Devanagari marks to a period first and let that handling do the rest.
    text = text.replace("\u0964", ".").replace("\u0965", ".")

    # Split while preserving delimiters (spaces, punctuation, symbols)
    tokens = re.split(r'(\s+|[.,!?:;\"\'\(\)\[\]{}<>\\/`~@#$%^&*+=_-]+)', text)
    result = []

    for token in tokens:
        # 1. Check if token contains Devanagari characters (\u0900 to \u097F)
        if re.search(r'[\u0900-\u097F]', token):
            result.append(_transliterate_hindi_word(token))
        # 2. Check if token contains Perso-Arabic / Urdu characters (\u0600 to \u06FF)
        elif re.search(r'[\u0600-\u06FF]', token):
            result.append(_transliterate_urdu_word(token))
        else:
            result.append(token)

    output = ''.join(result)

    # Post-process multi-word phrase patterns
    for pattern, replacement in PHRASE_NORMALIZATION:
        output = re.sub(pattern, replacement, output, flags=re.IGNORECASE)

    return output
