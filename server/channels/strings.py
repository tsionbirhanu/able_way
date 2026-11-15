"""All learner-facing text for the channels and handoff pages, in English and Amharic.

One file on purpose: translators only need to look here.
Use t(lang, key, **values). Unknown languages fall back to English.
NOTE: the Amharic was written by a non-native speaker; please have a native speaker review it.
"""

LANGS = {"en": "English", "am": "አማርኛ"}
DEFAULT_LANG = "en"


def norm_lang(lang) -> str:
    lang = (lang or "").strip().lower()
    if lang in ("am", "amh", "amharic", "አማርኛ"):
        return "am"
    if lang in ("en", "eng", "english", "እንግሊዝኛ"):
        return "en"
    return DEFAULT_LANG


STRINGS = {
    # ---- shared ----
    "dont_know": {
        "en": "I don't know, ask a person.",
        "am": "አላውቅም፣ እባክዎ ሰው ይጠይቁ።",
    },
    "sources": {"en": "Sources", "am": "ምንጮች"},
    "language": {"en": "Language", "am": "ቋንቋ"},
    "send": {"en": "Send", "am": "ላክ"},
    "empty_question": {"en": "Please type a question first.", "am": "እባክዎ መጀመሪያ ጥያቄ ይጻፉ።"},
    "skip_to_content": {"en": "Skip to content", "am": "ወደ ዋናው ይዘት ዝለል"},
    # ---- /lite ----
    "lite_title": {"en": "Ask the assistant (lite)", "am": "ረዳቱን ይጠይቁ (ቀላል ገጽ)"},
    "lite_intro": {
        "en": "A small page for slow connections. Type your question and press Ask.",
        "am": "ለዝቅተኛ ኢንተርኔት የተዘጋጀ ቀላል ገጽ። ጥያቄዎን ይጻፉና «ጠይቅ» ይጫኑ።",
    },
    "lite_question": {"en": "Your question", "am": "ጥያቄዎ"},
    "lite_ask": {"en": "Ask", "am": "ጠይቅ"},
    "lite_you_asked": {"en": "You asked", "am": "የጠየቁት"},
    "lite_answer": {"en": "Answer", "am": "መልስ"},
    "lite_talk_to_person": {"en": "Talk to a person", "am": "ከሰው ጋር ይነጋገሩ"},
    "lite_accommodation_link": {
        "en": "Request interview support",
        "am": "የቃለ መጠይቅ ድጋፍ ይጠይቁ",
    },
    # ---- SMS ----
    "sms_help": {
        "en": "Send a question, or: JOBS, SUB <word>, UNSUB, LANG AM/EN, AI ON/OFF, FORGET, HELP.",
        "am": "ጥያቄ ይላኩ፣ ወይም፦ JOBS፣ SUB <ቃል>፣ UNSUB፣ LANG AM/EN፣ AI ON/OFF፣ FORGET፣ HELP።",
    },
    "sms_lang_set": {"en": "Language set to English.", "am": "ቋንቋ ወደ አማርኛ ተቀይሯል።"},
    "sms_lang_usage": {"en": "Send LANG AM or LANG EN.", "am": "LANG AM ወይም LANG EN ይላኩ።"},
    "sms_sub_usage": {
        "en": "Send SUB and a word, for example: SUB calendar",
        "am": "SUB እና አንድ ቃል ይላኩ፣ ለምሳሌ፦ SUB calendar",
    },
    "sms_dont_know": {
        "en": "I don't know, ask a person. Your tutor or the ALX help desk can help.",
        "am": "አላውቅም፣ እባክዎ ሰው ይጠይቁ። አስተማሪዎ ወይም የALX እገዛ ማዕከል ሊረዱዎት ይችላሉ።",
    },
    # ---- jobs + alerts ----
    "jobs_header": {"en": "Newest virtual assistant jobs:", "am": "አዳዲስ የቨርቹዋል ረዳት ስራዎች፦"},
    "jobs_none": {"en": "No jobs right now.", "am": "አሁን ምንም ስራ የለም።"},
    "job_deadline": {"en": "Deadline", "am": "የማመልከቻ ማብቂያ"},
    "job_remote": {"en": "Remote", "am": "ከርቀት"},
    "job_skills": {"en": "Skills", "am": "ክህሎቶች"},
    "job_alert_prefix": {"en": "New job", "am": "አዲስ ስራ"},
    "subscribed": {
        "en": "Subscribed to job alerts for \"{keyword}\".",
        "am": "ለ«{keyword}» የስራ ማሳወቂያ ተመዝግበዋል።",
    },
    "subscribed_all": {
        "en": "Subscribed to alerts for all new jobs.",
        "am": "ለሁሉም አዳዲስ ስራዎች ማሳወቂያ ተመዝግበዋል።",
    },
    "unsubscribed": {
        "en": "You will get no more job alerts.",
        "am": "ከእንግዲህ የስራ ማሳወቂያ አይደርስዎትም።",
    },
    "not_subscribed": {
        "en": "You have no job alerts to remove.",
        "am": "የሚሰረዝ የስራ ማሳወቂያ የለዎትም።",
    },
    # ---- Telegram ----
    "tg_start": {
        "en": "Hello! I am the ALX course assistant. Ask me a question about your course in English or Amharic.\nSend /help to see what I can do.",
        "am": "ሰላም! እኔ የALX የትምህርት ረዳት ነኝ። ስለ ትምህርትዎ በአማርኛ ወይም በእንግሊዝኛ ይጠይቁኝ።\nምን ማድረግ እንደምችል ለማየት /help ይላኩ።",
    },
    "tg_help": {
        "en": (
            "Type a question, or send a voice message, and I will answer from the course pages.\n\n"
            "/lang - choose Amharic or English\n"
            "/voice on - get every answer as a voice message too (/voice off to stop)\n"
            "/privacy - choose whether AI and voice services may be used\n"
            "/forget - delete everything kept about this chat\n"
            "/jobs - newest virtual assistant jobs\n"
            "/subscribe <word> - get job alerts (for example /subscribe calendar)\n"
            "/unsubscribe - stop job alerts\n"
            "/accommodation - ask for support in an interview\n"
            "/human - talk to a person (/end to finish)\n"
            "/cancel - stop what you are doing"
        ),
        "am": (
            "ማንኛውንም ጥያቄ ይጻፉ ወይም የድምፅ መልእክት ይላኩ፤ ከትምህርቱ ገጾች እመልሳለሁ።\n\n"
            "/lang - አማርኛ ወይም እንግሊዝኛ ይምረጡ\n"
            "/voice on - እያንዳንዱን መልስ በድምፅም ያግኙ (ለማቆም /voice off)\n"
            "/privacy - የAIና የድምፅ አገልግሎቶች ይፈቀዱ እንደሆነ ይምረጡ\n"
            "/forget - ስለዚህ ውይይት የተያዘውን ሁሉ ይሰርዙ\n"
            "/jobs - አዳዲስ የቨርቹዋል ረዳት ስራዎች\n"
            "/subscribe <ቃል> - የስራ ማሳወቂያ ያግኙ (ለምሳሌ /subscribe calendar)\n"
            "/unsubscribe - የስራ ማሳወቂያ ያቁሙ\n"
            "/accommodation - ለቃለ መጠይቅ ድጋፍ ይጠይቁ\n"
            "/human - ከሰው ጋር ይነጋገሩ (ለመጨረስ /end)\n"
            "/cancel - እየሰሩ ያሉትን ያቁሙ"
        ),
    },
    "tg_lang_prompt": {
        "en": "Choose a language: /lang am for Amharic, /lang en for English.",
        "am": "ቋንቋ ይምረጡ፦ ለአማርኛ /lang am፣ ለእንግሊዝኛ /lang en።",
    },
    "tg_lang_set": {"en": "Language set to English.", "am": "ቋንቋ ወደ አማርኛ ተቀይሯል።"},
    "tg_offer_human": {
        "en": "Send /human to talk to a person.",
        "am": "ከሰው ጋር ለመነጋገር /human ይላኩ።",
    },
    "tg_human_started": {
        "en": "You are now connected to the tutor queue. Write your message and a person will reply here. Send /end to go back to the assistant.",
        "am": "አሁን ከአስተማሪዎች ጋር ተገናኝተዋል። መልእክትዎን ይጻፉ፤ ሰው እዚሁ ይመልስልዎታል። ወደ ረዳቱ ለመመለስ /end ይላኩ።",
    },
    "tg_human_ended": {
        "en": "The chat with a person has ended. You can ask the assistant again.",
        "am": "ከሰው ጋር የነበረው ውይይት ተጠናቋል። ረዳቱን እንደገና መጠየቅ ይችላሉ።",
    },
    "tg_tutor_prefix": {"en": "Tutor", "am": "አስተማሪ"},
    "tg_cancelled": {"en": "Cancelled.", "am": "ተሰርዟል።"},
    "tg_nothing_to_cancel": {"en": "Nothing to cancel.", "am": "የሚሰረዝ ነገር የለም።"},
    "tg_text_only": {
        "en": "Please send a text or a voice message.",
        "am": "እባክዎ የጽሑፍ ወይም የድምፅ መልእክት ይላኩ።",
    },
    # ---- voice messages ----
    "tg_voice_heard": {"en": "🎤 I heard: {text}", "am": "🎤 የሰማሁት፦ {text}"},
    "tg_voice_empty": {
        "en": "I could not hear any words in that voice message. Please try again, or type your question.",
        "am": "በድምፅ መልእክቱ ውስጥ ቃላት መስማት አልቻልኩም። እባክዎ እንደገና ይሞክሩ ወይም ጥያቄዎን ይጻፉ።",
    },
    "tg_voice_failed": {
        "en": "I cannot listen to voice messages right now. Please type your question.",
        "am": "አሁን የድምፅ መልእክት ማዳመጥ አልችልም። እባክዎ ጥያቄዎን ይጻፉ።",
    },
    # ---- consent: nothing leaves the server until the learner agrees ----
    "tg_consent_ask": {
        "en": (
            "Before I answer: to write answers and to hear and speak voice messages, I send your "
            "question or voice message to Google's AI services. Your name and phone number are not sent.\n\n"
            "Allow this? If not, I answer with text from the course on this server only, and voice is off. "
            "You can change it any time with /privacy."
        ),
        "am": (
            "ከመመለሴ በፊት፦ መልስ ለመጻፍና የድምፅ መልእክት ለመስማትና ለመናገር ጥያቄዎን ወይም የድምፅ መልእክትዎን "
            "ወደ Google የAI አገልግሎቶች እልካለሁ። ስምዎና ስልክ ቁጥርዎ አይላኩም።\n\n"
            "ይፈቅዳሉ? ካልፈቀዱ በዚህ ሰርቨር ላይ ካለው የኮርስ ጽሑፍ ብቻ እመልሳለሁ፤ ድምፅ አይሰራም። "
            "በማንኛውም ጊዜ በ /privacy መቀየር ይችላሉ።"
        ),
    },
    "tg_consent_yes_button": {"en": "✅ Allow", "am": "✅ እፈቅዳለሁ"},
    "tg_consent_no_button": {"en": "Offline only", "am": "ያለ ኢንተርኔት ብቻ"},
    "tg_consent_yes": {
        "en": "Thank you. AI answers and voice are on. Send /privacy to change this.",
        "am": "እናመሰግናለን። የAI መልሶችና ድምፅ በርተዋል። ለመቀየር /privacy ይላኩ።",
    },
    "tg_consent_no": {
        "en": "Understood. Nothing is sent outside: I answer from the course text only, and voice is off. Send /privacy to change this.",
        "am": "ተረድቻለሁ። ምንም ወደ ውጭ አይላክም፦ ከኮርሱ ጽሑፍ ብቻ እመልሳለሁ፤ ድምፅ አይሰራም። ለመቀየር /privacy ይላኩ።",
    },
    "tg_consent_status_yes": {"en": "Now: AI answers and voice are allowed.", "am": "አሁን፦ የAI መልሶችና ድምፅ ተፈቅደዋል።"},
    "tg_consent_status_no": {"en": "Now: offline only, nothing is sent outside.", "am": "አሁን፦ ያለ ኢንተርኔት ብቻ፤ ምንም ወደ ውጭ አይላክም።"},
    "tg_voice_needs_consent": {
        "en": "Voice needs the online services, which are off for this chat. Type your question, or send /privacy to allow them.",
        "am": "ድምፅ የኢንተርኔት አገልግሎቶችን ይፈልጋል፤ ለዚህ ውይይት ጠፍተዋል። ጥያቄዎን ይጻፉ፣ ወይም ለመፍቀድ /privacy ይላኩ።",
    },
    "sms_consent_info": {
        "en": "Mimi: answers now come from the course text only. Reply AI ON for AI answers (your question goes to Google), AI OFF to stop.",
        "am": "ሚሚ፦ መልሶች ከኮርሱ ጽሑፍ ብቻ ናቸው። ለAI መልስ AI ON ይላኩ (ጥያቄዎ ወደ Google ይሄዳል)፤ ለማቆም AI OFF።",
    },
    "sms_consent_on": {
        "en": "AI answers on. Your questions go to Google's AI to write the answer. Reply AI OFF to stop.",
        "am": "የAI መልስ በርቷል። ጥያቄዎ መልስ ለመጻፍ ወደ Google AI ይሄዳል። ለማቆም AI OFF ይላኩ።",
    },
    "sms_consent_off": {
        "en": "AI answers off. Answers come from the course text only; nothing is sent outside.",
        "am": "የAI መልስ ጠፍቷል። መልሶች ከኮርሱ ጽሑፍ ብቻ ናቸው፤ ምንም ወደ ውጭ አይላክም።",
    },
    "lite_cloud_label": {
        "en": "Use AI to write the answer (your question is sent to Google's AI; leave unticked to keep it on this server)",
        "am": "መልሱን በAI ይጻፍ (ጥያቄዎ ወደ Google AI ይላካል፤ በዚህ ሰርቨር ብቻ እንዲቆይ ምልክት አያድርጉ)",
    },
    "tg_forgotten": {
        "en": "Done: everything this bot kept about this chat is deleted (language, voice and privacy choices, job alerts, and the link to any help chat). Send /start to begin again.",
        "am": "ተጠናቋል፦ ይህ ቦት ስለዚህ ውይይት የያዘው ሁሉ ተሰርዟል (ቋንቋ፣ የድምፅና የግላዊነት ምርጫዎች፣ የስራ ማሳወቂያዎች እና ከእርዳታ ውይይት ጋር ያለው ግንኙነት)። እንደገና ለመጀመር /start ይላኩ።",
    },
    "sms_forgotten": {
        "en": "Deleted: your language, AI choice, job alerts and messages kept for this number.",
        "am": "ተሰርዟል፦ ለዚህ ቁጥር የተያዙት ቋንቋ፣ የAI ምርጫ፣ የስራ ማሳወቂያዎችና መልእክቶች።",
    },
    "tg_listen_button": {"en": "🔊 Listen", "am": "🔊 ያዳምጡ"},
    "tg_listen_expired": {
        "en": "That answer is no longer available to play. Please ask again.",
        "am": "ያ መልስ ለማዳመጥ አይገኝም። እባክዎ እንደገና ይጠይቁ።",
    },
    "tg_voice_unavailable": {
        "en": "I cannot speak right now. The answer is in the text above.",
        "am": "አሁን መናገር አልችልም። መልሱ ከላይ በጽሑፍ አለ።",
    },
    "tg_voice_on": {
        "en": "Voice answers are on: I will send every answer as text and as a voice message. Send /voice off to stop.",
        "am": "የድምፅ መልስ በርቷል፦ እያንዳንዱን መልስ በጽሑፍና በድምፅ እልካለሁ። ለማቆም /voice off ይላኩ።",
    },
    "tg_voice_off": {
        "en": "Voice answers are off. Press 🔊 Listen under any answer to hear it, or send /voice on.",
        "am": "የድምፅ መልስ ጠፍቷል። ማንኛውንም መልስ ለመስማት ከሱ በታች ያለውን 🔊 ያዳምጡ ይጫኑ፣ ወይም /voice on ይላኩ።",
    },
    "tg_voice_too_long": {
        "en": "That voice message is too long. Please keep it under two minutes.",
        "am": "የድምፅ መልእክቱ በጣም ረጅም ነው። እባክዎ ከሁለት ደቂቃ በታች ያድርጉት።",
    },
    # ---- accommodation ----
    "acc_title": {"en": "Interview support request", "am": "የቃለ መጠይቅ ድጋፍ መጠየቂያ"},
    "acc_intro": {
        "en": "Tell us what you need to do your best in an interview, for example a sign language interpreter, extra time, or written questions.",
        "am": "በቃለ መጠይቅ ላይ የተሻለ ለመስራት የሚያስፈልግዎትን ይንገሩን፤ ለምሳሌ የምልክት ቋንቋ አስተርጓሚ፣ ተጨማሪ ጊዜ ወይም በጽሑፍ የቀረቡ ጥያቄዎች።",
    },
    "acc_privacy": {
        "en": "Private: only the support team sees this. Teachers do not see it and it is not used for statistics.",
        "am": "ሚስጥራዊ፦ ይህንን የሚያየው የድጋፍ ቡድኑ ብቻ ነው። አስተማሪዎች አያዩትም፤ ለስታቲስቲክስም አይውልም።",
    },
    "acc_job": {"en": "Which job or interview is this for?", "am": "ይህ ለየትኛው ስራ ወይም ቃለ መጠይቅ ነው?"},
    "acc_job_other": {"en": "Other (write it below)", "am": "ሌላ (ከታች ይጻፉ)"},
    "acc_job_text": {"en": "Other job or interview", "am": "ሌላ ስራ ወይም ቃለ መጠይቅ"},
    "acc_support": {"en": "What support do you need?", "am": "ምን ዓይነት ድጋፍ ያስፈልግዎታል?"},
    "acc_contact": {
        "en": "How should we contact you? (phone, email or Telegram)",
        "am": "እንዴት እናግኝዎት? (ስልክ፣ ኢሜይል ወይም ቴሌግራም)",
    },
    "acc_submit": {"en": "Send request", "am": "ጥያቄውን ላክ"},
    "acc_missing": {
        "en": "Please fill in all three answers.",
        "am": "እባክዎ ሦስቱንም መልሶች ይሙሉ።",
    },
    "acc_thanks": {
        "en": "Thank you. Your request was received. The support team will contact you.",
        "am": "እናመሰግናለን። ጥያቄዎ ደርሶናል። የድጋፍ ቡድኑ ያገኝዎታል።",
    },
    "acc_another": {"en": "Send another request", "am": "ሌላ ጥያቄ ይላኩ"},
    "acc_tg_step1": {
        "en": "Interview support request (private, step 1 of 3).\nWhich job or interview is this for? Send /cancel to stop.",
        "am": "የቃለ መጠይቅ ድጋፍ መጠየቂያ (ሚስጥራዊ፣ ደረጃ 1 ከ3)።\nይህ ለየትኛው ስራ ወይም ቃለ መጠይቅ ነው? ለማቆም /cancel ይላኩ።",
    },
    "acc_tg_step2": {
        "en": "Step 2 of 3. What support do you need?",
        "am": "ደረጃ 2 ከ3። ምን ዓይነት ድጋፍ ያስፈልግዎታል?",
    },
    "acc_tg_step3": {
        "en": "Step 3 of 3. How should we contact you? (phone, email or Telegram)",
        "am": "ደረጃ 3 ከ3። እንዴት እናግኝዎት? (ስልክ፣ ኢሜይል ወይም ቴሌግራም)",
    },
    # ---- handoff (learner chat page) ----
    "chat_title": {"en": "Talk to a person", "am": "ከሰው ጋር ይነጋገሩ"},
    "chat_intro": {
        "en": "A tutor will join this chat. You can start writing now.",
        "am": "አስተማሪ ወደዚህ ውይይት ይገባል። አሁኑኑ መጻፍ መጀመር ይችላሉ።",
    },
    "chat_messages": {"en": "Messages", "am": "መልእክቶች"},
    "chat_message_label": {"en": "Your message", "am": "መልእክትዎ"},
    "chat_you": {"en": "You", "am": "እርስዎ"},
    "chat_tutor": {"en": "Tutor", "am": "አስተማሪ"},
    "chat_connecting": {"en": "Connecting…", "am": "በመገናኘት ላይ…"},
    "chat_connected_waiting": {
        "en": "Connected. Waiting for a tutor.",
        "am": "ተገናኝቷል። አስተማሪ በመጠበቅ ላይ።",
    },
    "chat_tutor_here": {"en": "A tutor is here.", "am": "አስተማሪ ገብቷል።"},
    "chat_disconnected": {
        "en": "Connection lost. Trying again…",
        "am": "ግንኙነቱ ተቋርጧል። እንደገና በመሞከር ላይ…",
    },
    "chat_closed": {"en": "This chat is closed.", "am": "ይህ ውይይት ተዘግቷል።"},
    "chat_not_found": {"en": "This chat does not exist.", "am": "ይህ ውይይት የለም።"},
    "chat_needs_js": {
        "en": "Live chat needs JavaScript. Without it, use the lite page.",
        "am": "ቀጥታ ውይይት JavaScript ያስፈልገዋል። ያለ እሱ ቀላሉን ገጽ ይጠቀሙ።",
    },
    "share_start": {"en": "Share my screen", "am": "ስክሪኔን አጋራ"},
    "share_explain": {
        "en": "Only you can start screen sharing. The tutor can look but cannot control anything.",
        "am": "ስክሪን ማጋራትን መጀመር የሚችሉት እርስዎ ብቻ ነዎት። አስተማሪው ማየት ብቻ እንጂ ምንም መቆጣጠር አይችልም።",
    },
    "share_banner": {"en": "You are sharing your screen", "am": "ስክሪንዎን እያጋሩ ነው"},
    "share_stop": {"en": "Stop", "am": "አቁም"},
    "share_stopped": {"en": "Screen sharing stopped.", "am": "ስክሪን ማጋራት ቆሟል።"},
    "share_failed": {
        "en": "Screen sharing could not start.",
        "am": "ስክሪን ማጋራት መጀመር አልተቻለም።",
    },
    "share_unsupported": {
        "en": "This browser cannot share the screen.",
        "am": "ይህ ብራውዘር ስክሪን ማጋራት አይችልም።",
    },
    "handoff_start_title": {"en": "Talk to a person", "am": "ከሰው ጋር ይነጋገሩ"},
    "handoff_start_button": {"en": "Start a chat with a tutor", "am": "ከአስተማሪ ጋር ውይይት ጀምር"},
}


def t(lang: str, key: str, **values) -> str:
    entry = STRINGS[key]
    text = entry.get(norm_lang(lang)) or entry["en"]
    return text.format(**values) if values else text


def format_citations(citations, lang: str) -> str:
    """Plain-text citations for chat channels: 'Sources: page - heading; ...'."""
    if not citations:
        return ""
    parts = []
    for c in citations:
        page, heading = (c.get("page") or "").strip(), (c.get("heading") or "").strip()
        parts.append(" - ".join(p for p in (page, heading) if p))
    return t(lang, "sources") + ": " + "; ".join(p for p in parts if p)
