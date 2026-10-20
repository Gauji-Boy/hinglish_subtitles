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
    'bata': 'baat',
    'kama': 'kaam',
    'nama': 'naam',
    'loga': 'log',
    'bahuta': 'bahut',
    'yaha': 'yeh',
    'vaha': 'woh',
    'kucha': 'kuch',
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


def _transliterate_hindi_word(word: str) -> str:
    """Converts a single Devanagari word into natural Latin Hinglish."""
    clean_devanagari = word.strip()
    if clean_devanagari in COMMON_LOANWORDS:
        return COMMON_LOANWORDS[clean_devanagari]

    # Aksharamukha ISO transliteration
    iso = transliterate.process('Devanagari', 'ISO', clean_devanagari)
    
    # In ISO transliteration, Devanagari 'च' is 'c' and 'छ' is 'ch'.
    # In English/Hinglish, 'ch' is used for 'च' and 'chh' for 'छ'.
    iso = re.sub(r'ch', 'chh', iso)
    iso = re.sub(r'(?<!c)c', 'ch', iso)
    
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
    
    # Trailing schwa deletion for words ending in consonant + single 'a'
    if ascii_str.endswith('a') and len(ascii_str) > 2 and not ascii_str.endswith(('aa', 'ia', 'ya', 'ha')):
        ascii_str = ascii_str[:-1]

    # Check conversational map
    lower = ascii_str.lower()
    if lower in HINDI_CONVERSATIONAL_MAP:
        return HINDI_CONVERSATIONAL_MAP[lower]

    return ascii_str


def _transliterate_urdu_word(word: str) -> str:
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
