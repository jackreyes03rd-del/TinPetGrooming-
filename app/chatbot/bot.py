from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests

from config import CONFIG

                           
BREED_KNOWLEDGE_PATH = Path(__file__).parent / "breed_knowledge.json"
BREED_DATA: dict[str, Any] = {}

try:
    with open(BREED_KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
        breed_json = json.load(f)
                                                    
        for breed in breed_json.get("breeds", []):
            breed_name = breed["name"].lower()
            BREED_DATA[breed_name] = breed
                         
            for alias in breed.get("aliases", []):
                BREED_DATA[alias.lower()] = breed
except Exception as e:
    print(f"Warning: Could not load breed knowledge base: {e}")

SERVICE_CATALOG: dict[str, str] = {
    "Bath & Blow Dry": "Best for routine cleaning, odor control, and light coat maintenance without a haircut.",
    "Full Groom": "Best for pets that need a bath, haircut, nail trim, and an overall reset in one visit.",
    "Breed Styling": "Best for owners who want a breed-specific finish or a more polished haircut.",
    "Nail Trim": "Best when nails are the main concern and the pet does not need a full bath.",
    "De-shedding": "Best for double-coated or heavy-shedding pets that need undercoat removal.",
    "Sanitary Trim": "Best for quick hygiene cleanup around sensitive areas between full grooms.",
}

BOOKING_PREP_TIPS = [
    "Bring or upload updated vaccination records before the visit.",
    "Tell the groomer about allergies, medications, skin issues, anxiety, or bite history.",
    "Avoid a heavy meal right before drop-off and allow a short bathroom break before arrival.",
    "If the coat is matted or the pet recently had medical treatment, mention it at check-in.",
]

ROLE_GUIDANCE = {
    "public": "Speak to prospective clients in a welcoming, practical way.",
    "owner": "Speak to pet owners and focus on clear next steps before or after appointments.",
    "staff": "Speak to grooming staff and emphasize safety, escalation, and handling notes.",
    "admin": "Speak to admins and include operational context when booking workflow is relevant.",
}

ADD_ON_GUIDANCE = (
    "Popular add-ons depend on the pet's needs: ear cleaning helps pets prone to wax buildup, teeth cleaning is useful for mild odor and routine care, paw balm helps dry paw pads, tick and flea wash is useful when parasites are suspected, and a blueberry facial works well for pets with tear staining or dirty facial fur."
)

RULES: list[dict[str, Any]] = [
    {
        "topic": "grooming_schedule",
        "keywords": ["how often", "bathe", "bath", "groom", "schedule", "frequency", "how many times"],
        "answer": (
            "Most dogs benefit from grooming every 4–8 weeks depending on breed and coat type. "
            "Short-coated breeds like Beagles can go 6–8 weeks; long-coated breeds like Shih Tzus and Maltese "
            "do better every 3–4 weeks. Cats rarely need baths but benefit from brushing 1–2 times a week. "
            "Rabbits should never be bathed — spot cleaning only."
        ),
    },
    {
        "topic": "breed_tips_shih_tzu",
        "keywords": ["shih tzu", "shihtzu"],
        "answer": (
            "Shih Tzus have a double coat that grows continuously and needs grooming every 3–4 weeks. "
            "Popular styles include the teddy bear trim, puppy cut, and top knot. "
            "Daily brushing prevents matting, and tear stain cleaning keeps the face area healthy."
        ),
    },
    {
        "topic": "breed_tips_poodle",
        "keywords": ["poodle", "poodles"],
        "answer": (
            "Poodles have curly coats that don't shed but tangle quickly — grooming every 4–6 weeks is ideal. "
            "Common cuts include the puppy clip, continental clip, and modern cut. "
            "Regular ear hair removal prevents infections since debris collects inside the ear canal."
        ),
    },
    {
        "topic": "breed_tips_husky",
        "keywords": ["husky", "huskies", "double coat", "siberian"],
        "answer": (
            "Never shave a Husky's double coat — it regulates both heat and cold and protects against sunburn. "
            "De-shedding treatments help during heavy blow-coat seasons (spring and fall). "
            "Bathing every 6–8 weeks with a de-shedding shampoo and thorough blow-out keeps the coat healthy."
        ),
    },
    {
        "topic": "breed_tips_persian",
        "keywords": ["persian", "persian cat", "flat face", "brachycephalic cat"],
        "answer": (
            "Persian cats need daily brushing to prevent tangles in their long, silky coat. "
            "A lion cut or sanitary trim every 6–8 weeks comforts them in warm climates. "
            "Clean eye discharge regularly since flat-faced cats produce more tear staining."
        ),
    },
    {
        "topic": "cat_hates_bath",
        "keywords": ["cat", "hates", "scared", "afraid", "terrified", "wet", "water"],
        "answer": (
            "Most cats dislike baths because they're not hardwired for it. Tips that help: "
            "Use lukewarm water and a gentle sprayer rather than a running faucet; "
            "apply a calming spray with lavender or chamomile 20 minutes before; "
            "keep the session short — under 10 minutes; reward immediately with treats. "
            "Dry shampoo is a good option for cats who are truly water-averse."
        ),
    },
    {
        "topic": "anxious_dog",
        "keywords": ["anxious", "anxious dog", "nervous", "aggressive", "fear", "biting", "snapping"],
        "answer": (
            "For anxious dogs, keep the environment calm: low noise, gentle touch, slow movements. "
            "Take breaks every 15–20 minutes to let the dog decompress. "
            "Never restrain an aggressive dog without a muzzle if there is a biting risk. "
            "Ask the owner if the dog is on any calming supplements or medication before beginning. "
            "Short sessions with positive rewards work better than pushing through all at once."
        ),
    },
    {
        "topic": "skin_health",
        "keywords": ["scratch", "itch", "itchy", "skin", "rash", "redness", "irritation", "hot spot"],
        "answer": (
            "Persistent itching may indicate allergies (food or environmental), parasites, dry skin, or a fungal/bacterial infection. "
            "Use a hypoallergenic oatmeal shampoo and avoid fragranced products. "
            "Red hot spots, odor, hair loss, or broken skin are signs to refer the owner to a veterinarian before proceeding."
        ),
    },
    {
        "topic": "flea_tick",
        "keywords": ["flea", "tick", "parasite", "bug", "lice"],
        "answer": (
            "A tick-and-flea wash with an anti-parasitic shampoo is highly recommended if you notice signs of infestation. "
            "After bathing, use a flea comb through the coat. "
            "Recommend the owner use a monthly topical or oral flea preventive. "
            "Check the ears, armpits, and between toes — ticks love these areas."
        ),
    },
    {
        "topic": "ear_cleaning",
        "keywords": ["ear", "ears", "ear cleaning", "ear infection", "smell", "discharge"],
        "answer": (
            "Clean ears with a vet-approved ear cleaning solution and cotton balls — never use cotton swabs inside the ear canal. "
            "Signs of infection include redness, dark discharge, strong odor, or head shaking — refer to a vet. "
            "Floppy-eared breeds like Cocker Spaniels and Basset Hounds need more frequent ear checks."
        ),
    },
    {
        "topic": "nail_trim",
        "keywords": ["nail", "nails", "claw", "claws", "trim nails", "cut nails"],
        "answer": (
            "Nails should be trimmed every 3–4 weeks for most dogs. The quick (blood vessel inside the nail) "
            "is visible in light-colored nails as a pink line — stop before it. "
            "For dark nails, trim in small increments and look for a gray dot at the center cross-section. "
            "Keep styptic powder nearby in case of accidental bleeding."
        ),
    },
    {
        "topic": "matted_fur",
        "keywords": ["mat", "matted", "knot", "tangle", "dreadlock"],
        "answer": (
            "Never wet a severely matted coat — water tightens mats further. "
            "Use a dematting tool or detangling spray and work from the tip of the mat inward. "
            "For severe matting close to the skin, shaving may be the only humane option. "
            "Warn the owner beforehand to set expectations. After shaving, the coat typically regrows in 2–4 months."
        ),
    },
    {
        "topic": "puppy_first_groom",
        "keywords": ["puppy", "first groom", "first visit", "first time", "baby dog"],
        "answer": (
            "A puppy's first groom is an introduction — keep it positive and brief (15–20 min). "
            "Prioritize nail trims, light brushing, and handling paws and ears. "
            "Avoid loud dryers — a cage dryer at low heat or towel drying is less stressful. "
            "Puppies can start visits as soon as they've had their core vaccinations (usually 10–12 weeks)."
        ),
    },
    {
        "topic": "vaccination",
        "keywords": ["vaccine", "vaccination", "rabies", "record", "certificate"],
        "answer": (
            "Tin Pet Grooming recommends keeping vaccination records updated — especially Rabies and DHPP for dogs, "
            "and FVRCP for cats. Upload your pet's vaccination file to their profile in the app. "
            "If records are missing, the groomer may ask for proof before starting the session."
        ),
    },
    {
        "topic": "faq_walkins",
        "keywords": ["walk in", "walk-in", "same day", "no appointment", "drop in"],
        "answer": (
            "Walk-ins are welcome when same-day slots are available. "
            "Check the live booking calendar for open slots, or call the shop. "
            "Scheduled bookings are always prioritized, so walk-in availability changes throughout the day."
        ),
    },
    {
        "topic": "faq_cancel",
        "keywords": ["cancel", "reschedule", "change appointment", "move booking"],
        "answer": (
            "You can cancel or request to reschedule from the 'Booking History' section of your dashboard. "
            "Cancelling at least 24 hours in advance is appreciated so the slot can be released for other clients."
        ),
    },
    {
        "topic": "faq_pricing",
        "keywords": ["price", "cost", "how much", "fee", "rate", "charge"],
        "answer": (
            "Current service rates at Tin Pet Grooming:\n"
            "• Bath & Blow Dry — ₱450 (60 min)\n"
            "• Full Groom — ₱850 (90 min)\n"
            "• Breed Styling — ₱1,100 (120 min)\n"
            "• Nail Trim — ₱180 (30 min)\n"
            "• De-shedding — ₱520 (60 min)\n"
            "• Sanitary Trim — ₱300 (45 min)\n"
            "Add-ons (teeth cleaning, ear cleaning, paw balm, cologne) are available at checkout."
        ),
    },
    {
        "topic": "faq_sms",
        "keywords": ["sms", "text", "reminder", "notification", "confirmation"],
        "answer": (
            "SMS confirmations are sent automatically when you book. "
            "A reminder is also sent 24 hours before your appointment. "
            "Make sure your mobile number is correct in your profile to receive messages."
        ),
    },
    {
        "topic": "dental_care",
        "keywords": ["teeth", "dental", "brush teeth", "tooth", "bad breath", "tartar"],
        "answer": (
            "Daily or every-other-day tooth brushing with a pet-safe toothpaste prevents tartar buildup. "
            "Never use human toothpaste — fluoride is toxic to pets. "
            "Teeth cleaning add-ons during grooming help — but for heavy tartar, a vet dental cleaning under anesthesia is recommended annually."
        ),
    },
    {
        "topic": "shedding",
        "keywords": ["shed", "shedding", "hair loss", "hair everywhere", "loose fur", "excessive fur"],
        "answer": (
            "All dogs shed — some more than others. De-shedding treatments with specialized shampoos and high-velocity drying "
            "can remove up to 80% of loose undercoat in one session. "
            "Regular brushing at home (2–3x per week) and omega-3 supplements support coat health and reduce shedding."
        ),
    },
    {
        "topic": "senior_pet",
        "keywords": ["old dog", "old cat", "senior", "elderly pet", "aging"],
        "answer": (
            "Senior pets (7+ years) need extra care during grooming. "
            "Keep sessions shorter and warmer; joints may be sore so limit time standing on the table. "
            "Watch for unusual lumps or skin changes and inform the owner promptly. "
            "Gentle handling and non-slip surfaces prevent falls."
        ),
    },
    {
        "topic": "post_groom_care",
        "keywords": ["after groom", "after bath", "post grooming", "home care", "at home"],
        "answer": (
            "After grooming: wait 24 hours before letting pets play in dirt or rain so the coat stays fresh. "
            "Brush every 2–3 days to prevent matting between sessions. "
            "Check paws for redness after nail trims. Keep the ear canals dry after ear cleaning."
        ),
    },
    {
        "topic": "shampoo_types",
        "keywords": ["shampoo", "shampoos", "soap", "wash", "bathing product", "what shampoo"],
        "answer": (
            "Common pet shampoos include: Hypoallergenic/Oatmeal (for sensitive skin, allergies, itching), "
            "Medicated (for fungal/bacterial infections, prescribed by vet), Whitening (for white coats to remove stains), "
            "Deodorizing (for strong odors), Flea & Tick (anti-parasitic), De-shedding (to loosen undercoat), "
            "and Puppy/Kitten formulas (extra gentle for young pets). Never use human shampoo — the pH is wrong for pets."
        ),
    },
    {
        "topic": "dog_breeds_small",
        "keywords": ["chihuahua", "pomeranian", "yorkie", "yorkshire terrier", "maltese", "toy poodle", "miniature poodle"],
        "answer": (
            "Small breeds like Chihuahuas, Pomeranians, Yorkies, and Maltese need grooming every 4–6 weeks. "
            "Yorkies and Maltese have continuously growing hair that mats easily — daily brushing helps. "
            "Pomeranians have thick double coats and shed heavily twice a year. "
            "Chihuahuas are low-maintenance but benefit from nail trims every 3–4 weeks."
        ),
    },
    {
        "topic": "dog_breeds_medium",
        "keywords": ["beagle", "bulldog", "cocker spaniel", "corgi", "boston terrier", "shiba inu", "basset hound"],
        "answer": (
            "Medium breeds vary in coat care: Beagles and Bulldogs have short coats and need bathing every 6–8 weeks. "
            "Cocker Spaniels need grooming every 4–6 weeks with special attention to ear cleaning. "
            "Corgis shed heavily year-round — de-shedding treatments help. "
            "Basset Hounds have loose skin and floppy ears — clean face folds and ears weekly to prevent infections."
        ),
    },
    {
        "topic": "dog_breeds_large",
        "keywords": ["golden retriever", "labrador", "german shepherd", "rottweiler", "doberman", "great dane"],
        "answer": (
            "Large breeds: Golden Retrievers and Labradors shed heavily and benefit from de-shedding every 6–8 weeks. "
            "German Shepherds have double coats — never shave them. "
            "Rottweilers and Dobermans have short coats but need nail trims and bathing every 6–8 weeks. "
            "Great Danes are low-maintenance but need regular ear cleaning and nail care."
        ),
    },
    {
        "topic": "cat_breeds",
        "keywords": ["siamese", "maine coon", "ragdoll", "british shorthair", "sphynx", "bengal"],
        "answer": (
            "Cat breed care: Persian and Maine Coons need daily brushing due to long coats. "
            "Ragdolls have silky fur that tangles less but still need brushing 2–3x weekly. "
            "British Shorthairs and Bengals are low-maintenance with weekly brushing. "
            "Sphynx cats are hairless but need weekly baths to remove skin oils."
        ),
    },
    {
        "topic": "rabbit_care",
        "keywords": ["rabbit", "bunny", "rabbits", "holland lop", "flemish giant"],
        "answer": (
            "Rabbits should NEVER be bathed — they can go into shock from stress and water. "
            "Spot-clean dirty areas with a damp cloth only. Brush weekly to remove loose fur and prevent hairballs. "
            "Trim nails every 4–6 weeks. Rabbits groom themselves like cats."
        ),
    },
    {
        "topic": "guinea_pig",
        "keywords": ["guinea pig", "cavy", "guinea pigs"],
        "answer": (
            "Guinea pigs rarely need baths unless very dirty — spot-clean with a damp cloth. "
            "Long-haired breeds (like Peruvian guinea pigs) need daily brushing. "
            "Trim nails every 3–4 weeks. Keep the cage clean to prevent skin issues and odor."
        ),
    },
    {
        "topic": "hamster_gerbil",
        "keywords": ["hamster", "gerbil", "dwarf hamster", "syrian hamster"],
        "answer": (
            "Hamsters and gerbils should NEVER be bathed with water — they clean themselves with sand baths. "
            "Provide a small container of chinchilla sand for them to roll in. "
            "Clean the cage weekly and trim nails if they grow too long."
        ),
    },
    {
        "topic": "allergy_symptoms",
        "keywords": ["allergy", "allergies", "allergic", "reaction", "hives", "swelling"],
        "answer": (
            "Pet allergy symptoms include: excessive scratching, red or inflamed skin, ear infections, paw licking, "
            "hair loss, vomiting, diarrhea, or watery eyes. Common causes are food ingredients (chicken, beef, grains), "
            "environmental allergens (pollen, dust, mold), or contact allergens (shampoos, detergents). "
            "Use hypoallergenic shampoo and consult a vet for diagnosis and treatment."
        ),
    },
    {
        "topic": "food_allergies",
        "keywords": ["food allergy", "food allergies", "grain free", "chicken allergy", "beef allergy"],
        "answer": (
            "Common food allergens for pets: chicken, beef, dairy, eggs, wheat, soy, and corn. "
            "Symptoms include itchy skin, ear infections, digestive upset, and paw licking. "
            "A vet may recommend an elimination diet to identify the trigger. "
            "Grain-free and limited-ingredient diets help some pets with sensitivities."
        ),
    },
    {
        "topic": "skin_infections",
        "keywords": ["fungal infection", "yeast infection", "bacterial infection", "ringworm", "mange"],
        "answer": (
            "Common skin infections: Yeast infections cause greasy skin and odor, often in skin folds and ears. "
            "Ringworm is a fungal infection with circular bald patches — highly contagious. "
            "Bacterial infections appear as red bumps, pus, or hot spots. "
            "Mange is caused by mites and causes intense itching and hair loss. All require veterinary diagnosis and treatment."
        ),
    },
    {
        "topic": "dry_skin",
        "keywords": ["dry skin", "flaky skin", "dandruff", "scaly skin"],
        "answer": (
            "Dry skin causes include low humidity, over-bathing, poor diet, or allergies. "
            "Use a moisturizing oatmeal shampoo and avoid bathing more than once every 4 weeks unless needed. "
            "Add omega-3 supplements (fish oil) to the diet. "
            "Use a humidifier at home during dry seasons. Persistent dryness may indicate an underlying health issue."
        ),
    },
    {
        "topic": "hot_spots",
        "keywords": ["hot spot", "hot spots", "acute moist dermatitis", "lick granuloma"],
        "answer": (
            "Hot spots are red, moist, painful skin lesions caused by excessive licking, scratching, or moisture. "
            "Common triggers: allergies, flea bites, ear infections, or boredom. "
            "Clean the area gently, keep it dry, and prevent licking with a cone collar. "
            "Veterinary treatment may include antibiotics or topical medications."
        ),
    },
    {
        "topic": "eye_care",
        "keywords": ["tear stain", "eye discharge", "watery eyes", "eye gunk", "eye infection"],
        "answer": (
            "Tear stains (brown streaks under eyes) are common in light-colored breeds and flat-faced pets. "
            "Clean daily with a tear stain wipe or diluted saline solution. "
            "Discharge can indicate allergies, blocked tear ducts, or infection. "
            "Yellow or green discharge with redness requires a vet visit — may be conjunctivitis."
        ),
    },
    {
        "topic": "grooming_tools",
        "keywords": ["brush", "comb", "slicker brush", "undercoat rake", "dematting tool", "grooming tool"],
        "answer": (
            "Essential grooming tools: Slicker brush (removes tangles, works for most coat types), "
            "Undercoat rake (for double-coated breeds like Huskies), Pin brush (for long silky coats), "
            "Dematting tool (cuts through stubborn mats), Flea comb (fine-toothed for parasite detection), "
            "and Nail clippers (guillotine or scissor-style). Choose tools based on your pet's coat type."
        ),
    },
    {
        "topic": "paw_care",
        "keywords": ["paw", "paws", "paw pad", "cracked paw", "dry paw", "paw balm"],
        "answer": (
            "Paw care tips: Check paws weekly for cuts, cracks, or foreign objects between toes. "
            "Trim fur between paw pads to prevent matting and ice buildup. "
            "Use paw balm for dry or cracked pads, especially in hot or cold weather. "
            "Avoid walking on hot pavement or salted roads. Wipe paws after outdoor walks."
        ),
    },
    {
        "topic": "anal_glands",
        "keywords": ["anal gland", "anal glands", "scooting", "dragging butt", "gland expression"],
        "answer": (
            "Anal glands are scent glands near the anus that can become impacted or infected. "
            "Signs of problems: scooting on the floor, excessive licking near the tail, foul odor, or swelling. "
            "Some pets need manual expression every 4–8 weeks — groomers or vets can do this. "
            "High-fiber diets help naturally express glands during bowel movements."
        ),
    },
    {
        "topic": "winter_care",
        "keywords": ["winter", "cold weather", "snow", "ice", "cold", "sweater"],
        "answer": (
            "Winter pet care: Small, short-haired, or senior pets may need sweaters or coats outdoors. "
            "Wipe paws after walks to remove ice-melt chemicals. Use paw balm to prevent cracking. "
            "Never shave double-coated breeds in winter — their coat insulates them. "
            "Provide extra bedding and keep pets indoors during extreme cold."
        ),
    },
    {
        "topic": "summer_care",
        "keywords": ["summer", "hot weather", "heat", "overheating", "heatstroke", "hot"],
        "answer": (
            "Summer pet care: Never leave pets in cars — temperatures can be deadly within minutes. "
            "Provide shade and fresh water. Walk during cooler hours (early morning or evening). "
            "Avoid hot pavement — it can burn paw pads. Watch for heatstroke signs: excessive panting, drooling, "
            "lethargy, vomiting. Never shave double-coated breeds — their coat protects from heat and sunburn."
        ),
    },
    {
        "topic": "pet_insurance",
        "keywords": ["insurance", "pet insurance", "medical cost", "vet bills"],
        "answer": (
            "Pet insurance helps cover unexpected vet costs for accidents, illnesses, or chronic conditions. "
            "Plans vary — some cover wellness visits, others only emergencies. "
            "Common providers in the Philippines include PetCare and other international platforms. "
            "Enroll early (before age 8) for better coverage and lower premiums."
        ),
    },
    {
        "topic": "obesity",
        "keywords": ["overweight", "obese", "obesity", "fat pet", "weight loss", "diet"],
        "answer": (
            "Pet obesity leads to diabetes, joint problems, and heart disease. "
            "Signs: difficulty breathing, lethargy, inability to feel ribs, no visible waist. "
            "Weight loss tips: measure food portions, limit treats, increase exercise gradually, "
            "feed a high-protein low-carb diet, and consult a vet for a safe weight loss plan."
        ),
    },
    {
        "topic": "parasites",
        "keywords": ["worm", "worms", "heartworm", "roundworm", "tapeworm", "hookworm", "deworming"],
        "answer": (
            "Common parasites: Heartworms (transmitted by mosquitoes, preventable with monthly medication), "
            "Roundworms (cause pot-bellied appearance, visible in stool), Tapeworms (look like rice grains in stool), "
            "Hookworms (cause anemia and bloody stool). Regular deworming every 3–6 months is recommended. "
            "Consult a vet for diagnosis and treatment."
        ),
    },
    {
        "topic": "behavior_training",
        "keywords": ["training", "behavior", "obedience", "sit", "stay", "come", "potty training"],
        "answer": (
            "Basic training tips: Use positive reinforcement (treats, praise) rather than punishment. "
            "Be consistent with commands and schedules. Start with basics: sit, stay, come. "
            "Potty training requires a regular schedule and immediate outdoor access after meals. "
            "Crate training helps with house training and provides a safe space. Patience is key."
        ),
    },
    {
        "topic": "barking_meowing",
        "keywords": ["barking", "excessive barking", "meowing", "vocal", "noisy", "loud"],
        "answer": (
            "Excessive barking/meowing causes: boredom, anxiety, attention-seeking, hunger, or medical issues. "
            "Solutions: increase exercise and mental stimulation, establish routines, ignore attention-seeking behavior, "
            "provide puzzle toys, and rule out pain or illness with a vet visit. "
            "Training and consistency reduce unwanted vocalizations over time."
        ),
    },
    {
        "topic": "separation_anxiety",
        "keywords": ["separation anxiety", "alone", "destructive", "crying when alone", "home alone"],
        "answer": (
            "Separation anxiety signs: destructive behavior, excessive barking/howling, urinating indoors, or pacing. "
            "Solutions: gradual desensitization (leave for short periods and increase slowly), create a safe space (crate or room), "
            "leave calming music or toys, avoid emotional goodbyes, and consider calming supplements or medication in severe cases."
        ),
    },
    {
        "topic": "spay_neuter",
        "keywords": ["spay", "neuter", "sterilize", "castrate", "fix", "desex"],
        "answer": (
            "Spaying (females) and neutering (males) prevent unwanted litters and reduce health risks (uterine infections, testicular cancer). "
            "Benefits: calmer behavior, reduced roaming, less marking, and longer lifespan. "
            "Recommended age: 6–9 months for most pets. Recovery takes 10–14 days — keep the pet calm and the incision clean."
        ),
    },
    {
        "topic": "pregnancy_birth",
        "keywords": ["pregnant", "pregnancy", "puppies", "kittens", "giving birth", "whelping", "queening"],
        "answer": (
            "Pet pregnancy lasts about 63 days in dogs and cats. Signs: enlarged abdomen, increased appetite, nesting behavior. "
            "Provide a quiet whelping box 1–2 weeks before due date. Feed high-quality food and consult a vet for prenatal care. "
            "Most pets give birth naturally, but have a vet's contact ready for emergencies. Avoid unnecessary handling of newborns."
        ),
    },
    {
        "topic": "senior_health",
        "keywords": ["arthritis", "joint pain", "stiff", "limping", "mobility", "old age"],
        "answer": (
            "Senior pet health issues include arthritis, kidney disease, dental disease, and vision/hearing loss. "
            "Arthritis signs: stiffness, limping, difficulty jumping, reluctance to move. "
            "Management: joint supplements (glucosamine), pain medication, weight control, gentle exercise, "
            "orthopedic beds, and ramps/steps for furniture. Regular vet checkups catch issues early."
        ),
    },
    {
        "topic": "emergency_signs",
        "keywords": ["emergency", "urgent", "vet now", "poisoning", "choking", "seizure", "collapsed"],
        "answer": (
            "Emergency warning signs requiring immediate vet care: difficulty breathing, choking, seizures, "
            "collapse or inability to stand, severe bleeding, vomiting/diarrhea with blood, bloated abdomen, "
            "suspected poisoning, trauma from accident, heatstroke, or sudden loss of consciousness. "
            "Call ahead to the emergency vet and transport the pet safely."
        ),
    },
    {
        "topic": "toxic_foods",
        "keywords": ["toxic", "poison", "chocolate", "grapes", "onion", "garlic", "xylitol", "dangerous food"],
        "answer": (
            "Toxic foods for pets: Chocolate, grapes/raisins, onions, garlic, xylitol (artificial sweetener), "
            "macadamia nuts, avocado, alcohol, caffeine, raw dough, and cooked bones (splinter risk). "
            "Signs of poisoning: vomiting, diarrhea, lethargy, tremors, seizures. "
            "Contact a vet or poison control immediately if ingestion is suspected."
        ),
    },
    {
        "topic": "microchipping",
        "keywords": ["microchip", "microchipping", "chip", "lost pet", "identification"],
        "answer": (
            "Microchipping is a permanent ID method — a rice-sized chip is injected under the skin between the shoulder blades. "
            "If a pet is lost and found, vets or shelters scan the chip to retrieve owner contact info. "
            "Cost is affordable (usually ₱500–₱1,500) and lasts a lifetime. Remember to register and update your contact details."
        ),
    },
    {
        "topic": "pet_travel",
        "keywords": ["travel", "airplane", "car ride", "crate", "carrier", "flying with pet"],
        "answer": (
            "Pet travel tips: Use an airline-approved carrier for flights. Acclimate your pet to the crate weeks before travel. "
            "For car rides, secure pets in a crate or harness. Never leave pets in hot cars. "
            "Bring water, food, medications, and vaccination records. Some airlines require health certificates. "
            "Consider calming supplements for anxious travelers."
        ),
    },
    {
        "topic": "pet_adoption",
        "keywords": ["adopt", "adoption", "rescue", "shelter", "rehome"],
        "answer": (
            "Adoption tips: Visit local shelters or rescue organizations. Ask about the pet's history, temperament, and health. "
            "Prepare your home with food, water bowls, bedding, toys, and a safe space. "
            "Schedule a vet checkup within the first week. Be patient — adjustment takes time. "
            "Adoption fees usually include vaccinations and spaying/neutering."
        ),
    },
]

def detect_topic(question: str) -> str:
    matches = _matched_rules(question, limit=1)
    if matches:
        return str(matches[0]["topic"])

    lowered = _normalize_text(question)
    if any(phrase in lowered for phrase in {"before my appointment", "before the appointment", "appointment tomorrow", "drop off"}):
        return "appointment_prep"
    if any(phrase in lowered for phrase in {"what service", "which service", "recommend a service", "choose a service", "best service"}):
        return "service_recommendation"
    if any(word in lowered for word in {"book", "booking", "slot", "appointment", "schedule"}):
        return "booking_help"
    if any(w in lowered for w in {"cat", "dog", "pet", "fur", "coat", "groomer"}):
        return "general_pet_care"
    return "general_faq"

def _rule_response(question: str) -> str | None:
    matches = _matched_rules(question, limit=1)
    return str(matches[0]["answer"]) if matches else None

def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())

def _keyword_in_text(keyword: str, text: str) -> bool:
    escaped = re.escape(keyword.strip().lower())
    if " " in keyword.strip():
        return escaped in text
    return re.search(rf"\b{escaped}\b", text) is not None

def _matched_rules(question: str, limit: int = 3) -> list[dict[str, Any]]:
    lowered = _normalize_text(question)
    scored_rules: list[tuple[int, dict[str, Any]]] = []
    for rule in RULES:
        score = sum(max(1, len(str(keyword).split())) for keyword in rule["keywords"] if _keyword_in_text(str(keyword), lowered))
        if score > 0:
            scored_rules.append((score, rule))
    scored_rules.sort(key=lambda item: item[0], reverse=True)
    return [rule for _, rule in scored_rules[:limit]]

def _recent_history(history: list[dict[str, str]] | None, limit: int = 6) -> list[dict[str, str]]:
    if not history:
        return []
    allowed_roles = {"assistant", "user"}
    return [message for message in history[-limit:] if message.get("role") in allowed_roles and message.get("content")]

def _context_for_question(question: str, audience: str, history: list[dict[str, str]] | None = None) -> str:
    parts = [
        "Tin Pet Grooming is a pet grooming shop in Calumpang, General Santos City, Philippines.",
        "Core services: " + "; ".join(f"{name}: {description}" for name, description in SERVICE_CATALOG.items()),
    ]

    matched_rules = _matched_rules(question)
    if matched_rules:
        parts.append(
            "Relevant pet-care knowledge: "
            + " ".join(str(rule["answer"]) for rule in matched_rules)
        )

    if detect_topic(question) == "appointment_prep":
        parts.append("Pre-appointment guidance: " + " ".join(BOOKING_PREP_TIPS))

    recent_messages = _recent_history(history)
    if recent_messages:
        transcript = " | ".join(f"{message['role']}: {message['content']}" for message in recent_messages)
        parts.append("Recent conversation: " + transcript)

    parts.append(ROLE_GUIDANCE.get(audience, ROLE_GUIDANCE["public"]))
    return "\n".join(parts)

def _service_recommendation(question: str) -> str | None:
    lowered = _normalize_text(question)

    if "mat" in lowered or "matted" in lowered:
        return (
            "If the coat is matted, Full Groom is usually the best starting point because it gives the groomer enough time "
            "to assess whether dematting is safe or whether a shorter reset trim is the kinder option."
        )
    if any(word in lowered for word in {"shed", "shedding", "husky", "double coat", "undercoat"}):
        return "For heavy loose coat or double-coated breeds, De-shedding is usually the best fit."
    if any(word in lowered for word in {"bath", "dirty", "odor", "smell"}):
        return "If the main goal is cleaning without a haircut, Bath & Blow Dry is the best fit."
    if any(word in lowered for word in {"nail", "claw"}):
        return "If nails are the only concern, Nail Trim is enough without booking a full grooming slot."
    if any(word in lowered for word in {"hygiene", "sanitary", "private area"}):
        return "If the need is focused hygiene cleanup, Sanitary Trim is the right service."
    if any(word in lowered for word in {"style", "haircut", "poodle", "shih tzu", "persian"}):
        return "If you want a haircut or breed-specific finish, Full Groom or Breed Styling is the right place to start."
    return None

def _addons_response(question: str) -> str | None:
    lowered = _normalize_text(question)
    if any(phrase in lowered for phrase in {"add-on", "add on", "addon", "add-ons", "extras", "extra service"}):
        return ADD_ON_GUIDANCE + " If you tell me your pet's coat condition or skin concern, I can narrow down which add-on fits best."
    return None

def _appointment_prep_response() -> str:
    return (
        "Before the appointment, make sure vaccination records are uploaded or ready to show, and let the groomer know about any "
        "allergies, medications, skin issues, anxiety, or bite history. Give your pet a short bathroom break before arrival, avoid a heavy meal right before drop-off, and mention any matting or recent medical treatment at check-in."
    )

def _combine_rule_answers(matches: list[dict[str, Any]], limit: int = 2) -> str:
    seen: set[str] = set()
    sentences: list[str] = []
    for rule in matches[:limit]:
        for sentence in re.split(r"(?<=[.!?])\s+", str(rule["answer"])):
            cleaned = sentence.strip()
            key = cleaned.lower()
            if not cleaned or key in seen:
                continue
            seen.add(key)
            sentences.append(cleaned)
    return " ".join(sentences[:5])

def _huggingface_response(question: str, audience: str = "public", history: list[dict[str, str]] | None = None) -> str | None:
    if not CONFIG.huggingface_api_token:
        return None
    headers = {
        "Authorization": f"Bearer {CONFIG.huggingface_api_token}",
        "Content-Type": "application/json",
    }
    context = _context_for_question(question, audience, history)
    prompt = (
        "You are an assistant for a pet grooming shop in General Santos City, Philippines. "
        "Answer pet grooming, care, and booking questions clearly and briefly using the provided context. "
        f"Context: {context}\nQuestion: {question}"
    )
    try:
        resp = requests.post(
            "https://api-inference.huggingface.co/models/google/flan-t5-base",
            headers=headers,
            json={"inputs": prompt},
            timeout=12,
        )
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, list) and payload:
            text = payload[0].get("generated_text", "").strip()
            return text or None
    except Exception:
        return None
    return None

def _openai_response(question: str, audience: str = "public", history: list[dict[str, str]] | None = None) -> str | None:
    if not CONFIG.openai_api_key:
        return None
    headers = {
        "Authorization": f"Bearer {CONFIG.openai_api_key}",
        "Content-Type": "application/json",
    }
    context = _context_for_question(question, audience, history)
    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant for Tin Pet Grooming, a pet grooming shop in "
                    "Calumpang, General Santos City, Philippines. Answer questions about pet "
                    "grooming, care, and bookings. Keep answers practical and concise. "
                    + ROLE_GUIDANCE.get(audience, ROLE_GUIDANCE["public"])
                ),
            },
            *(_recent_history(history)),
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{question}"},
        ],
        "temperature": 0.4,
        "max_tokens": 200,
    }
    try:
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=12)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

def fallback_response(question: str) -> str:
    topic = detect_topic(question)
    if topic == "appointment_prep":
        return _appointment_prep_response()
    if topic == "general_pet_care":
        return (
            "That depends on your pet's breed, age, and health condition. "
            "A safe next step is to describe the concern to the groomer before the session — "
            "or consult a vet if it sounds medical. I can also help with specific breed information if you tell me your pet's breed!"
        )
    
                                                                  
    lowered = _normalize_text(question)
    if any(word in lowered for word in ["breed", "dog", "cat", "pet type"]):
        supported_count = len([b for b in BREED_DATA.values() if b.get("name")])
        return (
            f"I don't have detailed info on that breed yet, but I know about {supported_count}+ common breeds including "
            "Japanese Spitz, Shih Tzu, Poodle, Golden Retriever, Labrador, Husky, Persian Cat, Maine Coon, and many more! "
            "You can ask me about grooming, health, or care for these breeds. "
            "For general questions, I can help with grooming schedules, coat care, pricing, and booking."
        )
    
    return (
        "I can help with grooming schedules, coat care, breed-specific tips (30+ breeds!), pricing, and booking questions. "
        "For medical concerns, please consult a veterinarian before the grooming session."
    )

def _smart_local_response(question: str) -> str | None:
    topic = detect_topic(question)
    matched_rules = _matched_rules(question)
    answer_parts: list[str] = []

    addons_tip = _addons_response(question)
    if addons_tip:
        answer_parts.append(addons_tip)

    if topic == "appointment_prep":
        answer_parts.append(_appointment_prep_response())

    if matched_rules:
        answer_parts.append(_combine_rule_answers(matched_rules))

    service_tip = _service_recommendation(question)
    if service_tip:
        answer_parts.append(service_tip)

    if answer_parts:
        return " ".join(part for part in answer_parts if part).strip()
    return None

def _detect_breed(question: str) -> dict[str, Any] | None:
    lowered = _normalize_text(question)
    
                                                                                    
    sorted_breeds = sorted(BREED_DATA.keys(), key=len, reverse=True)
    
    for breed_key in sorted_breeds:
                                                        
        escaped = re.escape(breed_key)
        if re.search(rf"\b{escaped}\b", lowered):
            return BREED_DATA[breed_key]
    
    return None

def _detect_breed_intent(question: str) -> str:
    lowered = _normalize_text(question)
    
                                
    if any(keyword in lowered for keyword in ["groom", "grooming", "coat", "brush", "brushing", "haircut", "trim", "bath", "fur", "hair"]):
        return "grooming"
    
    if any(keyword in lowered for keyword in ["health", "disease", "illness", "sick", "problem", "issue", "condition", "medical", "prone"]):
        return "health"
    
    if any(keyword in lowered for keyword in ["first time", "first-time", "beginner", "new owner", "good for me", "easy", "difficult", "recommend"]):
        return "first_time_owner"
    
    if any(keyword in lowered for keyword in ["what is", "tell me about", "describe", "information", "what are", "about the"]):
        return "description"
    
                                    
    return "general"

def _breed_response(breed_data: dict[str, Any], intent: str) -> str:
    breed_name = breed_data["name"]
    species = breed_data.get("species", "pet").title()
    
    if intent == "grooming":
        return f"**{breed_name} Grooming:**\n{breed_data['grooming']}"
    
    elif intent == "health":
        return f"**{breed_name} Health Concerns:**\n{breed_data['health']}"
    
    elif intent == "first_time_owner":
        good_for_beginner = breed_data.get("good_for_first_time_owner", "maybe")
        if good_for_beginner is True or good_for_beginner == "yes":
            recommendation = f"Yes, {breed_name}s are generally good for first-time owners. {breed_data['description']}"
        elif good_for_beginner is False or good_for_beginner == "no":
            recommendation = f"No, {breed_name}s are typically not recommended for first-time owners. {breed_data['description']} They require experienced handling and training."
        else:
            recommendation = f"Maybe — {breed_name}s can work for first-time owners with proper research and commitment. {breed_data['description']}"
        
        return f"**Is a {breed_name} good for first-time owners?**\n{recommendation}"
    
    elif intent == "description":
        return f"**About the {breed_name}:**\n{breed_data['description']}"
    
    else:           
                                    
        parts = [
            f"**{breed_name} ({species})**",
            f"\n**Description:** {breed_data['description']}",
            f"\n**Grooming:** {breed_data['grooming']}",
            f"\n**Health:** {breed_data['health']}"
        ]
        
        good_for_beginner = breed_data.get("good_for_first_time_owner")
        if good_for_beginner is True:
            parts.append("\n**First-time owner friendly:** Yes ✓")
        elif good_for_beginner is False:
            parts.append("\n**First-time owner friendly:** Not recommended (requires experience)")
        
        return "".join(parts)

def generate_response(
    question: str,
    history: list[dict[str, str]] | None = None,
    audience: str = "public",
) -> tuple[str, str]:
                                                          
    detected_breed = _detect_breed(question)
    if detected_breed:
        intent = _detect_breed_intent(question)
        breed_answer = _breed_response(detected_breed, intent)
        return breed_answer, f"breed_{detected_breed['name'].lower().replace(' ', '_')}"
    
                                     
    topic = detect_topic(question)
    llm_answer = _openai_response(question, audience=audience, history=history) or _huggingface_response(
        question,
        audience=audience,
        history=history,
    )
    if llm_answer:
        return llm_answer, topic
    
                                     
    local_answer = _smart_local_response(question)
    if local_answer:
        return local_answer, topic
    
                                          
    rule_answer = _rule_response(question)
    if rule_answer:
        return rule_answer, topic
    
                                
    return fallback_response(question), topic
