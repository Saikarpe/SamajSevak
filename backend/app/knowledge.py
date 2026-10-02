"""Domain knowledge: categories, departments, SLAs, severity weights, resolution playbooks, wards."""

CATEGORIES = {
    "Water Supply": {
        "department": "Water Supply Department",
        "sla_hours": 48,
        "severity": 0.70,
        "playbook": [
            "Dispatch junior engineer to inspect supply line and valve at the reported location",
            "Check pumping station schedule and pressure logs for the ward",
            "Arrange temporary water tanker if supply is disrupted for more than 24 hours",
            "Repair/replace leaking pipeline segment and flush the line",
            "Collect water sample for quality test if contamination is reported",
        ],
    },
    "Roads & Potholes": {
        "department": "Public Works Department (Roads)",
        "sla_hours": 120,
        "severity": 0.55,
        "playbook": [
            "Barricade and mark the hazard area to prevent accidents",
            "Assign road maintenance crew for cold-mix pothole patching",
            "Verify whether road is under defect-liability period of a contractor",
            "Schedule permanent resurfacing in next maintenance cycle",
            "Upload before/after geo-tagged photos for closure",
        ],
    },
    "Electricity": {
        "department": "Electricity Board",
        "sla_hours": 24,
        "severity": 0.75,
        "playbook": [
            "Alert the local substation/lineman for fault inspection",
            "Isolate the section if exposed or fallen wires are reported",
            "Check transformer load and replace blown fuse/DO",
            "Restore supply and verify voltage levels with consumers",
            "Log outage cause for preventive maintenance analysis",
        ],
    },
    "Garbage & Sanitation": {
        "department": "Solid Waste Management",
        "sla_hours": 24,
        "severity": 0.50,
        "playbook": [
            "Dispatch garbage collection vehicle to clear the spot",
            "Sanitize the area with disinfectant/bleaching powder",
            "Check door-to-door collection route adherence for the ward",
            "Install signage / CCTV at chronic dumping black-spots",
            "Impose penalty on repeat violators as per bye-laws",
        ],
    },
    "Drainage & Sewage": {
        "department": "Drainage Department",
        "sla_hours": 36,
        "severity": 0.70,
        "playbook": [
            "Send suction/jetting machine to clear the blocked chamber",
            "Inspect manhole covers and replace broken ones immediately",
            "Check for sewage mixing with drinking water line",
            "Carry out fogging/spraying to prevent vector breeding",
            "Plan desilting of the storm water drain before monsoon",
        ],
    },
    "Street Lights": {
        "department": "Electrical Maintenance (Street Lighting)",
        "sla_hours": 72,
        "severity": 0.40,
        "playbook": [
            "Assign street-light maintenance team to the pole location",
            "Replace faulty LED fixture / fuse / timer switch",
            "Check feeder pillar and cable continuity",
            "Prioritise dark stretches near schools, bus stops and women-safety zones",
        ],
    },
    "Public Health": {
        "department": "Health Department",
        "sla_hours": 24,
        "severity": 0.85,
        "playbook": [
            "Send ward health inspector for field verification",
            "Conduct fogging and larvicide spraying for mosquito control",
            "Organise door-to-door fever survey in the affected area",
            "Coordinate with nearest PHC/hospital for medical camp",
            "Inspect food establishments if food poisoning is reported",
        ],
    },
    "Public Transport": {
        "department": "City Transport Corporation",
        "sla_hours": 96,
        "severity": 0.35,
        "playbook": [
            "Share complaint with depot manager of the reported route",
            "Review GPS logs for frequency / skipped stops",
            "Initiate disciplinary process for staff misconduct if verified",
            "Repair bus stop shelter / display boards",
        ],
    },
    "Encroachment": {
        "department": "Anti-Encroachment Cell",
        "sla_hours": 168,
        "severity": 0.35,
        "playbook": [
            "Verify land records and permitted usage of the site",
            "Issue notice to the encroacher with compliance timeline",
            "Plan removal drive with police support if notice is ignored",
            "Restore footpath/public space after removal",
        ],
    },
    "Safety & Law": {
        "department": "Police & Public Safety Cell",
        "sla_hours": 12,
        "severity": 0.90,
        "playbook": [
            "Forward to nearest police station beat officer immediately",
            "Increase night patrolling in the reported area",
            "Check CCTV coverage and install cameras at blind spots",
            "Coordinate with street lighting team for dark stretches",
        ],
    },
    "Tree & Parks": {
        "department": "Garden & Tree Authority",
        "sla_hours": 72,
        "severity": 0.45,
        "playbook": [
            "Inspect the tree / park for hazard assessment",
            "Remove fallen or dangerous branches with cutting crew",
            "Repair park equipment, fencing and lighting",
            "Schedule pruning ahead of monsoon season",
        ],
    },
}

# Escalation ladder of an unresolved issue: (stage, who holds it, how long before the next stage,
# as a fraction of the category's SLA above). Complaint and Warning both stay with the concerned
# department; only the strikes go upward.
# This is the prototype's own accountability workflow, not a verified legal or government procedure,
# and the durations are placeholders: change them here, or set SAMAJSEVAK_STAGE_HOURS="72,48,72,120"
# (Complaint, Warning, Strike 1, Strike 2 in hours) to use fixed periods for every category.
DEPARTMENT_LEVEL = "Concerned department"
ESCALATION_STAGES = [
    ("Complaint", DEPARTMENT_LEVEL, 1.0),
    ("Warning", DEPARTMENT_LEVEL, 0.5),
    ("Strike 1", "Higher authority of the concerned department", 0.5),
    ("Strike 2", "Deputy Collector", 0.5),
    ("Strike 3", "Final escalation body: IAS officers and opposition party leaders", None),
]

# Pune-like wards with approximate coordinates (for hotspot map)
WARDS = {
    "Kothrud": (18.5074, 73.8077),
    "Hadapsar": (18.5089, 73.9260),
    "Shivajinagar": (18.5308, 73.8475),
    "Aundh": (18.5580, 73.8075),
    "Baner": (18.5590, 73.7868),
    "Kharadi": (18.5515, 73.9348),
    "Wakad": (18.5987, 73.7650),
    "Yerawada": (18.5529, 73.8797),
    "Katraj": (18.4575, 73.8677),
    "Hinjewadi": (18.5913, 73.7389),
    "Viman Nagar": (18.5679, 73.9143),
    "Swargate": (18.5018, 73.8636),
}

# Urgency keywords with weights -> used for explainable priority
URGENCY_TERMS = {
    "accident": 0.9, "died": 1.0, "death": 1.0, "dead": 0.9, "injured": 0.9, "injury": 0.8,
    "electrocution": 1.0, "shock": 0.8, "fire": 1.0, "sparking": 0.9, "live wire": 1.0,
    "fallen wire": 0.9, "collapse": 0.9, "flood": 0.8, "flooding": 0.8, "emergency": 0.9,
    "urgent": 0.6, "immediately": 0.5, "dangerous": 0.7, "danger": 0.7, "hazard": 0.6,
    "dengue": 0.9, "malaria": 0.8, "cholera": 1.0, "outbreak": 0.9, "fever": 0.6,
    "contaminated": 0.8, "dirty water": 0.7, "vomiting": 0.8, "diarrhea": 0.8, "food poisoning": 0.9,
    "harassment": 0.9, "theft": 0.7, "robbery": 0.9, "unsafe": 0.7, "stalking": 0.9, "chain snatching": 0.8,
    "open manhole": 0.9, "overflowing": 0.5, "no water": 0.6, "no electricity": 0.6, "power cut": 0.5,
    "fallen tree": 0.7, "blocked road": 0.5, "live electric wire": 1.0, "hanging low": 0.6,
    "breathing problem": 0.7, "smoke": 0.6, "admitted": 0.8, "ambulance": 0.8, "fell inside": 0.9, "got stuck": 0.6,
    "cave-in": 0.8, "about to fall": 0.8, "about to collapse": 0.9,
}
VULNERABLE_TERMS = {
    "children": 0.6, "child": 0.6, "school": 0.5, "kids": 0.6, "elderly": 0.6, "senior citizen": 0.6,
    "old age": 0.5, "pregnant": 0.7, "hospital": 0.7, "patients": 0.6, "women": 0.5, "disabled": 0.6,
}

NEGATIVE_WORDS = set("""
angry frustrated terrible worst horrible pathetic useless disgusting fed up irresponsible
negligence ignored careless shameful unbearable suffering helpless disappointed annoyed
nobody nothing never again still waiting stinking smelly foul broken damaged pathetic
corrupt bribe lazy fail failed failure poor bad awful miserable scared afraid worried
""".split())
POSITIVE_WORDS = set("""
thanks thank please kindly appreciate good great resolved helpful quick grateful request
""".split())
INTENSIFIERS = {"very", "extremely", "totally", "completely", "really", "so", "too", "highly",
                "bahut", "bahot", "ekdum", "khup", "बहुत", "खूप", "फार", "अत्यंत", "अतिशय"}

# ---------------- Hindi / Marathi (Devanagari) and Hinglish lexicon ----------------
# Surface form -> the English key it stands for in URGENCY_TERMS / VULNERABLE_TERMS, so the
# priority score and its explanation stay in one vocabulary whatever the complaint language.
# Devanagari forms match as word prefixes (inflections: मुले/मुलांना, शाळा/शाळेजवळ).
WARD_NAMES_DEVANAGARI = {
    "Kothrud": "कोथरूड", "Hadapsar": "हडपसर", "Shivajinagar": "शिवाजीनगर", "Aundh": "औंध", "Baner": "बाणेर",
    "Kharadi": "खराडी", "Wakad": "वाकड", "Yerawada": "येरवडा", "Katraj": "कात्रज", "Hinjewadi": "हिंजवडी",
    "Viman Nagar": "विमान नगर", "Swargate": "स्वारगेट",
}
WARD_ALIASES = {**{v: k for k, v in WARD_NAMES_DEVANAGARI.items()},
                "कोथरुड": "Kothrud", "हिंजेवाडी": "Hinjewadi", "विमाननगर": "Viman Nagar", "येरवडे": "Yerawada"}

URGENCY_ALIASES = {
    # Hindi
    "दुर्घटना": "accident", "हादसा": "accident", "हादसे": "accident", "मौत": "death", "मृत्यु": "death", "मर गया": "died",
    "मर गई": "died", "घायल": "injured", "चोट": "injury", "करंट": "shock", "आग": "fire", "चिंगारी": "sparking",
    "चिंगारियां": "sparking", "तार टूट": "fallen wire", "तार गिर": "fallen wire", "बाढ़": "flood", "इमरजेंसी": "emergency",
    "आपातकाल": "emergency", "तुरंत": "immediately", "तत्काल": "immediately", "खतरनाक": "dangerous", "खतरा": "danger",
    "खतरे": "danger", "डेंगू": "dengue", "मलेरिया": "malaria", "हैजा": "cholera", "बुखार": "fever", "दूषित": "contaminated",
    "गंदा पानी": "dirty water", "गंदे पानी": "dirty water", "उल्टी": "vomiting", "उलटी": "vomiting", "दस्त हो": "diarrhea", "दस्त लग": "diarrhea",
    "छेड़छाड़": "harassment", "छेड़ते": "harassment", "चोरी": "theft", "लूट": "robbery", "डकैती": "robbery",
    "असुरक्षित": "unsafe", "मैनहोल खुला": "open manhole", "खुला मैनहोल": "open manhole", "ओवरफ्लो": "overflowing",
    "पानी नहीं": "no water", "बिजली नहीं": "no electricity", "लाइट नहीं": "no electricity", "पेड़ गिर": "fallen tree",
    "रास्ता बंद": "blocked road", "धुआं": "smoke", "धुएं": "smoke", "भर्ती": "admitted", "एम्बुलेंस": "ambulance",
    "गिरने वाला": "about to fall", "फूड पॉइजनिंग": "food poisoning", "चेन स्नैचिंग": "chain snatching",
    # Marathi
    "अपघात": "accident", "मृत्यू": "death", "जखमी": "injured", "दुखापत": "injury", "शॉक": "shock", "ठिणग्या": "sparking",
    "ठिणगी": "sparking", "तार तुट": "fallen wire", "तार पडल": "fallen wire", "पूर": "flood", "आणीबाणी": "emergency",
    "ताबडतोब": "immediately", "तातडीने": "immediately", "धोकादायक": "dangerous", "धोका": "danger", "डेंग्यू": "dengue",
    "कॉलरा": "cholera", "ताप": "fever", "तापाचे": "fever", "दूषित पाणी": "contaminated", "घाण पाणी": "dirty water",
    "उलट्या": "vomiting", "जुलाब": "diarrhea", "छेडछाड": "harassment", "छेड काढ": "harassment", "दरोडा": "robbery",
    "उघडे मॅनहोल": "open manhole", "मॅनहोल उघडे": "open manhole", "ओव्हरफ्लो": "overflowing", "पाणी येत नाही": "no water",
    "पाणी नाही": "no water", "पाणी आलेले नाही": "no water", "वीज नाही": "no electricity", "लाईट नाही": "no electricity",
    "झाड पडल": "fallen tree", "रस्ता बंद": "blocked road", "धूर": "smoke", "धुरामुळे": "smoke", "दाखल": "admitted",
    "रुग्णवाहिका": "ambulance", "पडण्याच्या स्थितीत": "about to fall", "विषबाधा": "food poisoning",
    "सोनसाखळी": "chain snatching",
    # Hinglish (Roman script)
    "durghatna": "accident", "hadsa": "accident", "maut": "death", "ghayal": "injured", "current lag": "shock",
    "aag lag": "fire", "chingari": "sparking", "taar toot": "fallen wire", "taar gir": "fallen wire",
    "turant": "immediately", "jaldi": "immediately", "khatarnak": "dangerous", "khatra": "danger", "bukhar": "fever",
    "ganda paani": "dirty water", "ganda pani": "dirty water", "ulti": "vomiting", "dast": "diarrhea",
    "chhed chhad": "harassment", "chori": "theft", "paani nahi": "no water", "pani nahi": "no water",
    "bijli nahi": "no electricity", "light nahi": "no electricity", "ped gir": "fallen tree", "dhuan": "smoke",
    "girne wala": "about to fall", "dhakkan gayab": "open manhole", "dhakkan nahi": "open manhole",
}
VULNERABLE_ALIASES = {
    "बच्चे": "children", "बच्चों": "children", "बच्चा": "child", "स्कूल": "school", "विद्यालय": "school",
    "बुजुर्ग": "elderly", "वृद्ध": "elderly", "गर्भवती": "pregnant", "अस्पताल": "hospital", "हॉस्पिटल": "hospital",
    "मरीज": "patients", "महिला": "women", "औरत": "women", "लड़कियों": "women", "विकलांग": "disabled",
    "दिव्यांग": "disabled",
    "मुले": "children", "मुलं": "children", "मुलां": "children", "मुलाला": "child", "शाळा": "school", "शाळे": "school",
    "ज्येष्ठ": "elderly", "गरोदर": "pregnant", "रुग्णालय": "hospital", "दवाखान": "hospital", "रुग्ण": "patients",
    "स्त्रिया": "women", "मुलीं": "women", "अपंग": "disabled",
    "bachche": "children", "bachcho": "children", "bachchon": "children", "bujurg": "elderly", "buzurg": "elderly",
    "aspatal": "hospital", "mareez": "patients", "mahila": "women", "mahilaon": "women", "ladkiyon": "women",
}

# Citizen-facing names for replies in the complaint's own language
CATEGORY_NAMES = {
    "hi": {"Water Supply": "जल आपूर्ति", "Roads & Potholes": "सड़क और गड्ढे", "Electricity": "बिजली",
           "Garbage & Sanitation": "कचरा और स्वच्छता", "Drainage & Sewage": "नाली और सीवर", "Street Lights": "स्ट्रीट लाइट",
           "Public Health": "सार्वजनिक स्वास्थ्य", "Public Transport": "सार्वजनिक परिवहन", "Encroachment": "अतिक्रमण",
           "Safety & Law": "सुरक्षा और कानून व्यवस्था", "Tree & Parks": "पेड़ और उद्यान"},
    "mr": {"Water Supply": "पाणीपुरवठा", "Roads & Potholes": "रस्ते आणि खड्डे", "Electricity": "वीज",
           "Garbage & Sanitation": "कचरा आणि स्वच्छता", "Drainage & Sewage": "गटार आणि सांडपाणी", "Street Lights": "पथदिवे",
           "Public Health": "सार्वजनिक आरोग्य", "Public Transport": "सार्वजनिक वाहतूक", "Encroachment": "अतिक्रमण",
           "Safety & Law": "सुरक्षा आणि कायदा-सुव्यवस्था", "Tree & Parks": "झाडे आणि उद्याने"},
}
PRIORITY_NAMES = {"hi": {"Critical": "अति गंभीर", "High": "उच्च", "Medium": "मध्यम", "Low": "सामान्य"},
                  "mr": {"Critical": "अतिगंभीर", "High": "उच्च", "Medium": "मध्यम", "Low": "सामान्य"}}

NEGATIVE_WORDS |= set("pareshan kharab ganda gandagi badbu bekar taklif dikkat laparwahi gussa".split())
POSITIVE_WORDS |= set("dhanyavad shukriya kripya धन्यवाद कृपया आभार".split())
# Devanagari negative stems (prefix match)
NEGATIVE_STEMS = ("परेशान", "खराब", "गंद", "बदबू", "बेकार", "तकलीफ", "दिक्कत", "लापरवाह", "गुस्स", "सुनवाई", "त्रास", "त्रस्त",
                  "घाण", "दुर्गंध", "अस्वच्छ", "निकृष्ट", "दुर्लक्ष", "हैराण", "संताप", "भीती", "डर")
REPEAT_TERMS = ("again", "already", "twice", "still", "ignored", "reminder", "phir se", "dobara", "abhi tak", "kai baar",
                "फिर से", "दोबारा", "अभी तक", "कई बार", "दो बार शिकायत", "सुनवाई नहीं", "पुन्हा", "अजूनही", "अनेक वेळा",
                "दोनदा तक्रार", "दखल घेत नाही")
