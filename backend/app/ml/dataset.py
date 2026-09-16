"""Synthetic but realistic grievance corpus generator (English + Hinglish mix).

Used to (1) train the category classifier and (2) seed historical resolved cases
that power the retrieval-based resolution recommender.
"""
import random

from app.knowledge import WARDS

LANDMARKS = ["near the bus stop", "opposite the municipal school", "behind the vegetable market",
             "near Ganesh temple", "next to the city hospital", "in lane no. 4", "near the railway crossing",
             "outside the society gate", "near the primary school", "at the main chowk", "near the park",
             "beside the petrol pump", "in our colony", "on the main road", "near the water tank"]
DURATIONS = ["for 2 days", "for the last 3 days", "since one week", "for 10 days", "since last month",
             "for 5 days", "since yesterday", "for more than 2 weeks", "since Monday", ""]
OPENERS = ["", "Respected sir, ", "Dear team, ", "Hello, ", "Sir/Madam, ", "This is to bring to your notice that ",
           "Please help. ", "I want to complain that ", "Kindly look into this: "]
CLOSERS = ["", " Please take action.", " Kindly resolve urgently.", " Nobody is responding to our calls.",
           " We are really frustrated.", " Children are facing a lot of problems.", " Please do the needful.",
           " Complaint already given twice but still ignored.", " Elderly people are suffering.",
           " This is very dangerous.", " Thank you."]

T = {
    "Water Supply": [
        "Taps are dry {loc} {dur}, buying water cans",
        "Tap water is smelly and unfit to drink {loc}",
        "Borewell and municipal water both stopped {loc} {dur}",
        "No water supply {loc} {dur}", "Water is coming very low pressure {loc} {dur}",
        "Drinking water pipeline is leaking {loc} and lot of water is wasted",
        "Dirty and contaminated water is coming from taps {loc} {dur}",
        "Pani nahi aa raha {loc} {dur}", "Water tanker has not come {dur} to our society {loc}",
        "Muddy yellow water in municipal supply {loc}, people getting sick",
        "Main water pipe burst {loc}, road is flooded with water",
        "Water supply timing is irregular {loc}, comes at 3 am only",
        "Water meter is broken and bill is wrong, supply stopped {loc}",
    ],
    "Roads & Potholes": [
        "Deep hole on the service road {loc}, vehicles skidding",
        "Tar washed away from the road {loc} after rain",
        "Crater on the highway stretch {loc} {dur}",
        "Huge potholes on the road {loc} causing accidents", "Road is completely damaged {loc} {dur}",
        "Big pothole {loc}, two wheeler riders fell down yesterday",
        "Road digging work left incomplete {loc} {dur}", "Speed breaker is broken and unmarked {loc}",
        "Sadak pe bahut gadde hai {loc}", "Newly made road already broken {loc}, poor quality work",
        "Footpath tiles are broken {loc}, senior citizens are falling",
        "Road cave-in {loc} after rain, very dangerous for vehicles",
        "Uneven road surface and gravel spread {loc} {dur}",
    ],
    "Electricity": [
        "Whole building without power {loc} {dur}, inverter dead",
        "Loud blast in transformer {loc} and smoke coming",
        "No electricity {loc} {dur}", "Frequent power cuts {loc} every evening",
        "Transformer sparking {loc}, risk of fire", "Live wire fallen on the road {loc}, very dangerous",
        "Bijli nahi hai {loc} {dur}", "Voltage fluctuation damaged our appliances {loc}",
        "Electric pole is tilted and about to fall {loc}", "Meter burnt and power cut {loc} {dur}",
        "Hanging electric cables touching the tree {loc}, sparks during rain",
        "Power outage for 12 hours {loc}, patients on oxygen concentrators struggling",
    ],
    "Garbage & Sanitation": [
        "Rubbish heap not picked up {loc}, rats and flies everywhere",
        "Sweepers have not cleaned the street {loc} {dur}",
        "Waste bins not emptied {loc}, bad odour",
        "Garbage not collected {loc} {dur}", "Huge garbage dump {loc} and it is stinking",
        "Kachra gadi nahi aayi {dur} {loc}", "Dustbin overflowing {loc}, stray dogs spreading waste",
        "People burning garbage {loc}, smoke causing breathing problems",
        "Public toilet is very dirty and without water {loc}", "Dead animal lying on the road {loc} {dur}",
        "Construction debris dumped on the roadside {loc}", "Garbage collection vehicle skips our lane {loc}",
        "Plastic waste piled up near the drain {loc} {dur}",
    ],
    "Drainage & Sewage": [
        "Drainage is blocked and overflowing {loc} {dur}", "Sewage water on the road {loc}, foul smell",
        "Open manhole {loc}, someone may fall in", "Gutter overflow {loc} {dur}, entering homes",
        "Sewage mixing with drinking water line {loc}", "Storm water drain choked {loc}, water logging after rain",
        "Manhole cover broken {loc} {dur}", "Nala saaf nahi hua {loc}, mosquitoes breeding",
        "Chamber overflowing in front of houses {loc}", "Waterlogging in basement due to blocked drains {loc}",
    ],
    "Street Lights": [
        "Pitch dark on the street at night {loc}, lamps dead",
        "Pole light off {loc} {dur}",
        "Street lights not working {loc} {dur}", "Entire lane is dark at night {loc}, feels unsafe",
        "Street light pole damaged {loc}", "Street lights remain on during the day {loc}, wasting electricity",
        "Batti band hai {loc} {dur}", "Flickering street light {loc} {dur}",
        "No lights on the stretch {loc}, women afraid to walk at night",
        "Several street lamps fused {loc}", "Street light timer faulty {loc}",
    ],
    "Public Health": [
        "High fever and platelet count dropping in many neighbours {loc}",
        "Many dengue cases {loc}, please do fogging", "Mosquito menace {loc} {dur}, fever cases increasing",
        "Food poisoning after eating at a stall {loc}", "Stray dog bite cases rising {loc}",
        "Stagnant water breeding mosquitoes {loc}, malaria spreading",
        "Many people vomiting and diarrhea {loc} after drinking water", "Unhygienic meat shop {loc} {dur}",
        "Primary health centre has no doctor {loc} {dur}", "Cholera outbreak suspected {loc}, need medical camp",
        "Fever cases among children {loc}, need health survey",
    ],
    "Public Transport": [
        "Bus number 42 does not stop at our stop {loc}", "Bus frequency very low {loc}, waiting 1 hour",
        "Bus conductor misbehaved with passengers", "Bus stop shelter is broken {loc}",
        "Buses are overcrowded in the morning {loc}", "Driver was driving rashly on the route {loc}",
        "No bus service to our area {loc} {dur}", "Bus display board not working {loc}",
    ],
    "Encroachment": [
        "Hawkers have encroached the footpath {loc}", "Illegal construction on public land {loc}",
        "Shop owners placed goods on the road {loc}, traffic jam", "Illegal parking on the footpath {loc} {dur}",
        "Unauthorised shed built on the drain {loc}", "Road side encroachment {loc} blocking ambulance way",
        "Illegal hoardings and banners {loc}", "Someone has occupied the open space of the park {loc}",
    ],
    "Safety & Law": [
        "Chain snatching incidents {loc} {dur}", "Anti-social elements drinking in public {loc} at night",
        "Women harassment near the college {loc}", "Theft of vehicles {loc} {dur}",
        "Eve teasing at the bus stop {loc}, girls feel unsafe", "Robbery attempt last night {loc}",
        "Drug peddling suspected {loc}", "Street fights happening every night {loc}",
        "Stalking of school girls {loc}, need police patrolling",
    ],
    "Tree & Parks": [
        "Tree collapsed on parked cars {loc} during the storm",
        "Slide and swings rusted in the garden {loc}",
        "Big tree fallen on the road {loc} after rain", "Dangerous dry tree may fall {loc}",
        "Park swings broken {loc}, children getting hurt", "Garden not maintained {loc} {dur}",
        "Tree branches touching electric wires {loc}", "Park lights not working and gate broken {loc}",
        "Illegal tree cutting {loc}", "Open gym equipment damaged in park {loc}",
    ],
}

RESOLUTION_NOTES = {
    "Water Supply": ["Leaking valve replaced and line flushed", "Tanker deployed; pump motor repaired",
                     "Pipeline segment of 6 m replaced; water quality test passed", "Supply schedule corrected with pumping station"],
    "Roads & Potholes": ["Pothole filled with cold-mix asphalt", "Contractor directed to repair under defect liability",
                         "Road stretch resurfaced", "Speed breaker repainted and signage installed"],
    "Electricity": ["Blown fuse replaced at transformer", "Fallen line isolated and re-strung",
                    "Transformer load balanced; new DO fitted", "Pole replaced and supply restored"],
    "Garbage & Sanitation": ["Spot cleared and disinfected", "Collection route revised to cover lane",
                             "Black-spot cleared; CCTV and signage installed", "Debris removed; penalty imposed"],
    "Drainage & Sewage": ["Chamber cleared with jetting machine", "New manhole cover installed",
                          "Drain desilted; fogging done", "Cross-connection with water line fixed"],
    "Street Lights": ["LED fixture replaced", "Feeder pillar fuse replaced", "Timer switch repaired",
                      "Cable fault rectified"],
    "Public Health": ["Fogging and larvicide spraying done", "Fever survey conducted; medical camp held",
                      "Food stall inspected and sealed", "Dog sterilisation drive conducted"],
    "Public Transport": ["Route frequency increased", "Staff counselled and warned", "Bus shelter repaired",
                         "GPS audit done; driver penalised"],
    "Encroachment": ["Notice issued; encroachment removed", "Removal drive conducted with police",
                     "Illegal hoardings removed", "Footpath restored"],
    "Safety & Law": ["Night patrolling increased", "CCTV installed at spot", "FIR registered and accused identified",
                     "Beat marshal assigned"],
    "Tree & Parks": ["Fallen tree removed", "Hazardous branches pruned", "Park equipment repaired",
                     "Tree cutting complaint forwarded to Tree Authority; fine imposed"],
}


def _fill(template: str, rng: random.Random, ward: str) -> str:
    loc = rng.choice(LANDMARKS) + (f" in {ward}" if rng.random() < 0.7 else "")
    text = template.format(loc=loc, dur=rng.choice(DURATIONS))
    text = rng.choice(OPENERS) + text.strip() + "." + rng.choice(CLOSERS)
    return " ".join(text.split())


def generate_training(n_per_class: int = 180, seed: int = 7):
    rng = random.Random(seed)
    rows = []
    for cat, temps in T.items():
        for _ in range(n_per_class):
            ward = rng.choice(list(WARDS))
            rows.append((_fill(rng.choice(temps), rng, ward), cat))
    rng.shuffle(rows)
    return rows


def generate_history(n: int = 420, seed: int = 11):
    """Historical grievances with ward, timestamps and resolution info."""
    rng = random.Random(seed)
    cats = list(T)
    weights = [14, 12, 10, 13, 10, 8, 6, 5, 5, 4, 5]
    out = []
    for _ in range(n):
        cat = rng.choices(cats, weights)[0]
        ward = rng.choice(list(WARDS))
        # simulate an emerging hotspot: drainage + health issues in Hadapsar recently
        out.append({"category": cat, "ward": ward,
                    "text": _fill(rng.choice(T[cat]), rng, ward),
                    "resolution": rng.choice(RESOLUTION_NOTES[cat])})
    for text, cat, ward in CRITICAL_SAMPLES:
        out.append({"category": cat, "ward": ward, "text": text, "resolution": rng.choice(RESOLUTION_NOTES[cat]), "recent": True})
    for _ in range(18):
        cat = rng.choice(["Drainage & Sewage", "Public Health"])
        out.append({"category": cat, "ward": "Hadapsar", "text": _fill(rng.choice(T[cat]), rng, "Hadapsar"),
                    "resolution": rng.choice(RESOLUTION_NOTES[cat]), "recent": True})
    return out


CRITICAL_SAMPLES = [
    ("Live electric wire has fallen on the road near the primary school in Kothrud since yesterday. Children walk here daily, this is extremely dangerous!", "Electricity", "Kothrud"),
    ("Open manhole on the main road in Hadapsar without any cover. An elderly man fell inside last night and was injured. Please act immediately.", "Drainage & Sewage", "Hadapsar"),
    ("Dirty contaminated water coming in taps in Hadapsar for 4 days. Many children vomiting and diarrhea cases. Complaint given twice but still ignored.", "Water Supply", "Hadapsar"),
    ("Suspected dengue outbreak in our society in Hadapsar, 9 people admitted to hospital with fever. Urgent fogging needed.", "Public Health", "Hadapsar"),
    ("Transformer sparking and small fire near the vegetable market in Yerawada. Very dangerous, shops around.", "Electricity", "Yerawada"),
    ("Big tree fallen on the road in Aundh after storm blocking the ambulance route to the hospital. Emergency!", "Tree & Parks", "Aundh"),
    ("Chain snatching and harassment of women near the bus stop in Katraj every evening, street is unsafe and dark.", "Safety & Law", "Katraj"),
    ("Road cave-in near the railway crossing in Swargate, two bikers had an accident yesterday. Very dangerous hazard.", "Roads & Potholes", "Swargate"),
    ("Sewage mixing with drinking water line in Hadapsar lane no. 4, people getting fever and diarrhea. Pregnant women and kids at risk.", "Drainage & Sewage", "Hadapsar"),
    ("Electric pole about to collapse near the school in Wakad, live wire hanging low. Kids in danger.", "Electricity", "Wakad"),
    ("No water supply in Kharadi for 6 days, elderly and patients are suffering. Nobody responds, we are totally frustrated!", "Water Supply", "Kharadi"),
    ("Street lights not working for 2 weeks near the college in Viman Nagar, girls are afraid and a stalking incident happened.", "Street Lights", "Viman Nagar"),
    ("Garbage burning every night in Baner near the hospital, smoke causing breathing problems for patients and children.", "Garbage & Sanitation", "Baner"),
    ("Flooding in the underpass in Shivajinagar due to choked storm water drain, a car got stuck. Dangerous.", "Drainage & Sewage", "Shivajinagar"),
    ("Food poisoning — 15 students vomiting after eating at the canteen stall near the school in Hinjewadi.", "Public Health", "Hinjewadi"),
]
