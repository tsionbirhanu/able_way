"""Telegram and SMS texts in Afaan Oromo (om).

Merged into STRINGS by strings.py. Any text not listed here falls back to English (see t()).
Machine-assisted translations: have a native speaker check them before relying on them.
"""

MORE = {
    "dont_know": {"om": "Hin beeku, nama gaafadhaa."},
    "sources": {"om": "Maddoota"},
    "sms_help": {"om": "Gaaffii ergaa, ykn: JOBS, SUB <jecha>, UNSUB, LANG AM/EN/OM, AI ON/OFF, FORGET, HELP."},
    "sms_lang_set": {"om": "Afaan Oromootti jijjiirameera."},
    "sms_lang_usage": {"om": "LANG AM, LANG EN ykn LANG OM ergaa."},
    "sms_dont_know": {"om": "Hin beeku, nama gaafadhaa. Barsiisaan keessan ykn gargaarsi ALX isin gargaaruu danda'a."},
    "tg_start": {"om": "Akkam! Ani gargaaraa koorsii ALX ti. Waa'ee koorsii keessanii Afaan Oromootiin na gaafadhaa.\nWaan ani gochuu danda'u ilaaluuf /help ergaa."},
    "tg_help": {"om": "Gaaffii barreessaa, ykn ergaa sagalee ergaa; fuula koorsii irraa nan deebisa.\n\nGaaffilee saffisaa (Menu jalattis ni argamu):\n/deadline - guyyaa galchuu hojii manaa\n/late - imaammata yeroo darbee galchuu\n/resubmit - irra deebi'ee galchuu nan danda'aa?\n/quizzes - waa'ee qormaata madaallii\n/course - koorsiin kun waa'ee maaliiti?\n/future - egeree hojii VA\n\n/lang - afaan filadhu (am, en, om)\n/voice on - deebii hunda sagaleenis argadhu (/voice off dhaabuuf)\n/privacy - tajaajila AI fi sagalee eeyyamuu ykn dhiisuu\n/forget - waan chat kana irratti qabame hunda haqi\n/jobs - hojiiwwan haaraa\n/subscribe <jecha> - beeksisa hojii argadhu\n/unsubscribe - beeksisa hojii dhaabi\n/accommodation - gaaffii deeggarsa af-gaaffii\n/human - nama waliin dubbadhu (/end xumuruuf)\n/cancel - waan hojjechaa jirtu dhaabi"},
    "tg_lang_prompt": {"om": "Afaan filadhaa: /lang am Amaaraa, /lang en Ingliizii, /lang om Oromoo."},
    "tg_lang_set": {"om": "Afaan Oromootti jijjiirameera."},
    "tg_offer_human": {"om": "Nama waliin dubbachuuf /human ergaa."},
    "tg_human_started": {"om": "Amma tarree barsiisaa waliin walqunnamtaniittu. Ergaa keessan barreessaa, namni as isiniif deebisa. Gara gargaaraatti deebi'uuf /end ergaa."},
    "tg_human_not_open": {"om": "Amma nama waliin haasawa irra hin jirtan, kanaaf ana Mimii waliin dubbachaa jirtu. Gaaffii na gaafadhaa, ykn nama argachuuf /human ergaa."},
    "tg_human_ended": {"om": "Haasawni nama waliin xumurameera. Gargaaraa irra deebi'anii gaafachuu ni dandeessu."},
    "tg_tutor_prefix": {"om": "Barsiisaa"},
    "tg_cancelled": {"om": "Haqameera."},
    "tg_nothing_to_cancel": {"om": "Wanti haqamu hin jiru."},
    "tg_text_only": {"om": "Mee barreeffama ykn ergaa sagalee ergaa."},
    "tg_voice_heard": {"om": "🎤 Kanan dhaga'e: {text}"},
    "tg_voice_empty": {"om": "Ergaa sagalee sana keessatti jecha tokkollee dhaga'uu hin dandeenye. Irra deebi'aa yaalaa, ykn gaaffii keessan barreessaa."},
    "tg_voice_failed": {"om": "Amma ergaa sagalee dhaggeeffachuu hin danda'u. Mee gaaffii keessan barreessaa."},
    "tg_consent_ask": {"om": "Osoon hin deebisin: deebii barreessuu fi ergaa sagalee dhaga'uu fi dubbachuuf, gaaffii ykn ergaa sagalee keessan gara tajaajila AI Google'tti nan erga. Maqaan fi lakkoofsi bilbila keessanii hin ergamu.\n\nNi eeyyamtuu? Yoo hin eeyyamne, barreeffama koorsii sarvarii kana irra jiru qofaan nan deebisa, sagaleen hin hojjetu. Yeroo kamiyyuu /privacy tiin jijjiiruu ni dandeessu."},
    "tg_consent_yes_button": {"om": "✅ Eeyyami"},
    "tg_consent_no_button": {"om": "Interneetii malee qofa"},
    "tg_consent_yes": {"om": "Galatoomaa. Deebiin AI fi sagaleen banameera. Jijjiiruuf /privacy ergaa."},
    "tg_consent_no": {"om": "Hubadheera. Wanti tokkollee gara alaatti hin ergamu: barreeffama koorsii qofaan nan deebisa, sagaleen hin hojjetu. Jijjiiruuf /privacy ergaa."},
    "tg_consent_status_yes": {"om": "Amma: deebiin AI fi sagaleen eeyyamamaniiru."},
    "tg_consent_status_no": {"om": "Amma: interneetii malee qofa, wanti alatti ergamu hin jiru."},
    "tg_voice_needs_consent": {"om": "Sagaleen tajaajila toora interneetii barbaada, chat kanaaf immoo dhaamsameera. Gaaffii keessan barreessaa, ykn eeyyamuuf /privacy ergaa."},
    "tg_listen_button": {"om": "🔊 Dhaggeeffadhu"},
    "tg_voice_unavailable": {"om": "Amma dubbachuu hin danda'u. Deebiin barreeffama olii keessa jira."},
    "tg_voice_on": {"om": "Deebiin sagalee banameera: deebii hunda barreeffamaa fi ergaa sagaleetiin nan erga. Dhaabuuf /voice off ergaa."},
    "tg_voice_off": {"om": "Deebiin sagalee dhaamseera. Dhaga'uuf deebii kamiyyuu jalatti 🔊 tuqaa, ykn /voice on ergaa."},
    "tg_forgotten": {"om": "Xumurameera: wanti bootiin kun waa'ee chat kanaa qabate hundi haqameera. Irra deebi'uuf /start ergaa."},
    "jobs_header": {"om": "Hojiiwwan gargaaraa virchuwaalii haaraa:"},
    "jobs_none": {"om": "Amma hojiin hin jiru."},
}
