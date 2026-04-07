# game/script.rpy

python early:
    import random
    import requests
    import os
    import json # RenPy typically includes this
    import sys # Not strictly needed for this script based on CLI, but kept if you plan to use it
    import re

    # --- Constants and Configuration ---
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = "gemini-1.5-flash-latest"
    GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    VICTIM = "Lord Henry Blackwood"
    MANOR_NAME = "Blackwood Manor"

    GAME_SETTING_TEXT = f"""
{MANOR_NAME} is an old estate with a century-old history of triumphs and scandals.
The night of the murder, a fierce storm raged, cutting off telephone lines and roads.
This has trapped everyone inside. The murder occurred around 10:15 PM.
{VICTIM} had gathered everyone for a significant announcement (rumored to be about his will).
"""

    SUSPECTS_FULL_NAMES = {
        "Marianne": "Marianne Blackwood",
        "Victor": "Victor Blackwood",
        "Caroline": "Caroline Blackwood"
    }
    SUSPECT_SHORT_NAMES = list(SUSPECTS_FULL_NAMES.keys())

    # Template for evidence data, will be deep-copied for each game instance
    _EVIDENCE_DATA_TEMPLATE = {
        "Antique Dagger": {
            "description_stages": [
                "A decorative antique dagger, normally on display in the victim's study. It has been wiped clean, but traces of blood might be in the hilt's grooves. It belonged to the Blackwood family.",
                # Stage 1 (Placeholder - will be made dynamic if conditions met)
                "Upon extremely close forensic examination under specific lighting, a minuscule trace of foreign material is found lodged deep within the hilt's intricate engraving. It's almost invisible."
            ],
            "relevance_stages": [
                "The murder weapon. Knowledge of it being the weapon before it's announced is suspicious.",
                # Stage 1 Relevance (Placeholder)
                "This trace evidence, if identifiable, could directly link someone to handling the dagger with force or during a struggle."
            ],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [
                None, # Condition for stage 0 (initial view) is always met on discovery
                {"condition_type": "examine_under_pressure", "clue": "Antique Dagger"} # Condition to advance from Stage 0 to Stage 1
            ],
            "initial_location": "Victim's Study",
            "discovered": False,
            "details_for_llm": "The murder weapon was an antique dagger from the study. It was wiped, but tiny blood traces might be in the hilt. Advanced examination might reveal more if specific suspicions arise.",
            "icon": "icon_dagger"
        },
        "Bloodstained Cloth": { # Already well-structured for dynamic Stage 2
            "description_stages": [
                "A piece of cloth with the victim’s blood, possibly from a torn curtain or a monogrammed handkerchief. May have been hastily hidden.",
                "Upon closer examination, the cloth is a fine linen, badly bloodstained. A faint, smudged mark, possibly a monogram or laundry mark, is visible but indecipherable without further context.",
                # Stage 2 will be dynamically determined based on the murderer
            ],
            "relevance_stages": [
                "Can link to a suspect if it's theirs or if they tried to dispose of it. The material might be identifiable.",
                "The fine quality suggests it belongs to someone of status in the household. The mark is key if it can be identified.",
                # Stage 2 relevance also dynamic
            ],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [
                None,
                {"command": "examine", "clue": "Bloodstained Cloth"}, # To Stage 1
                {"condition_type": "link_to_murderer", "clue": "Bloodstained Cloth"} # To Stage 2
            ],
            "initial_location": "Fireplace",
            "discovered": False,
            "details_for_llm": "A bloodstained cloth fragment was found. Its origin is unclear but vital. Closer examination has revealed an indecipherable mark."
        },
        "Victim's Will": {
            "description_stages": ["A recently updated will for Lord Henry Blackwood. Content may surprise inheritors."],
            "relevance_stages": [
                "Reveals financial motives. Marianne might get less, Victor's share conditional, Caroline a trust unless disowned."],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [None],
            "initial_location": "Victim's Study", # Found at the desk in the study
            "discovered": False,
            "details_for_llm": f"Lord {VICTIM}'s new will has been found. It changed inheritances significantly, potentially impacting Marianne, Victor, and Caroline negatively or surprisingly."
        },
        "Love Letter": {
            "description_stages": [
                "An unsent letter, possibly from Marianne to an unnamed lover (or vice versa), speaking of 'escaping Blackwood Manor'."],
            "relevance_stages": ["Suggests Marianne's unhappiness, potential affair. Damages her credibility."],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [None],
            "initial_location": "Marianne_Room",
            "discovered": False,
            "details_for_llm": "A love letter was found, suggesting Marianne was unhappy and possibly planning to leave with a secret lover."
        },
        "Anonymous Threat Note": {
            "description_stages": [
                "A terse note reading 'I’ll make sure you never ruin our lives – C.' Found in victim’s study.",
                # Stage 1 (Placeholder - Dynamic if Caroline is murderer and conditions met)
                "Standard handwriting analysis is inconclusive due to the brevity and possible attempt to disguise the script. However, specific letter formations warrant comparison if a strong suspect emerges."
            ],
            "relevance_stages": [
                "Initial 'C' points to Caroline. Handwriting analysis could confirm. Strong clue if she's killer, red herring if not.",
                # Stage 1 Relevance (Placeholder)
                "Without a definitive match, the note remains a troubling but unconfirmed piece of evidence. A confirmed match would significantly escalate its importance."
            ],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [
                None,
                {"condition_type": "link_to_murderer_specific", "clue": "Anonymous Threat Note", "suspect_key": "Caroline Blackwood"} # Condition for Stage 1
            ],
            "initial_location": "Victim's Study",
            "discovered": False,
            "details_for_llm": f"An anonymous note threatening Lord {VICTIM}, signed with 'C.', was found in his study. Handwriting might be Caroline's."
        },
        "Broken Pocket Watch": {
            "description_stages": [f"The victim’s pocket watch, smashed, stopped at 10:15 PM."],
            "relevance_stages": ["Likely marks time of struggle. Constrains alibis."],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [None],
            "initial_location": "Near the Body", # Effectively in the Study
            "discovered": False,
            "details_for_llm": f"The victim's pocket watch was found broken, stopped at 10:15 PM, likely indicating the time of the attack.",
            "icon": "icon_watch"
        },
        "Muddy Footprints": {
            "description_stages": [
                "Muddy footprints leading from a side door into the mansion. Possibly different sizes.",
                "Closer inspection of the Muddy Footprints reveals at least two distinct sets of prints based on size and tread pattern. One appears to be a smaller, perhaps feminine shoe, the other larger.",
                # Stage 2 (Placeholder - Dynamic, links to murderer if they made them)
                "Further forensic study of one set of footprints has yielded specific details about the shoe type and traces of material caught in the treads."
            ],
            "relevance_stages": [
                "Suggests someone went outside during the storm. Contradicts claims of staying inside.",
                "The presence of two distinct sets of prints strongly suggests two individuals were in the garden or used that entrance around the time of the murder.",
                # Stage 2 Relevance (Placeholder)
                "These details could definitively match the prints to a specific pair of shoes owned by a suspect, or link them to a specific area they might have transited."
            ],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [
                None,
                {"command": "examine", "clue": "Muddy Footprints"}, # To Stage 1
                {"condition_type": "link_to_murderer", "clue": "Muddy Footprints"} # To Stage 2
            ],
            "initial_location": "Garden",
            "discovered": False,
            "details_for_llm": "Muddy footprints (possibly multiple sets) were found near a side door, indicating someone was outside during the storm. Closer inspection reveals two distinct sets."
        },
        "Butler's Log": {
            "description_stages": [
                "James the Butler's notes or testimony about guest movements and odd events (e.g., '10 PM: Heard raised voices in study')."],
            "relevance_stages": [
                "Provides a timeline that can confirm or conflict with suspect stories. Butler might be loyal and omit details."],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [None],
            "initial_location": "Testimony", # Revealed by Dragon, not found by searching
            "discovered": False,
            "details_for_llm": "The butler, James, recalls hearing raised voices from the study around 10 PM and saw Marianne heading upstairs around 10:30 PM."
        },
        "Medical Report": {
            "description_stages": [
                f"Report from Doctor Patel (or coroner) on cause of death (stab wound), approximate time (10:15 PM), defensive wounds (scratch on {VICTIM}'s arm)."],
            "relevance_stages": [
                "Confirms weapon type, time. Scratch could match killer's jewelry or cause an injury on the killer."],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [None],
            "initial_location": "Testimony", # Revealed by Dragon
            "discovered": False,
            "details_for_llm": f"The medical report states Lord {VICTIM} died from a stab wound around 10:15 PM and had a defensive scratch on his arm. The killer might have a corresponding scratch."
        },
        "Caroline's Sketchbook": {
            "description_stages": [
                "Caroline’s sketchbook with disturbing imagery (e.g., person with knife) or portraits (e.g., of a lover)."],
            "relevance_stages": ["Reveals Caroline’s mental state (anger, fear). Might upset her if confronted."],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [None],
            "initial_location": "Caroline_Room",
            "discovered": False,
            "details_for_llm": "Caroline's sketchbook was found, containing some disturbing drawings or sketches of a secret lover."
        },
        "Financial Records (Victor)": {
            "description_stages": [
                "Documents showing Victor’s secret debts, embezzlement, or failed investments. Perhaps a rejected loan application."],
            "relevance_stages": [
                f"Indicates desperate need for money. Motive if {VICTIM} discovered this or if will changes affected him."],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [None],
            "initial_location": "Victor_Room",
            "discovered": False,
            "details_for_llm": "Financial records were found showing Victor is in significant debt and was recently denied a loan."
        },
        "Marianne's Travel Trunk": {
            "description_stages": [
                "Packed bags and a one-way steamer ticket in Marianne’s luggage, dated for the next week."],
            "relevance_stages": [
                "Suggests she was planning to leave suddenly (elope or flee). Escape plan if guilty, red herring if not."],
            "current_stage": 0,
            "reveal_conditions_for_next_stage": [None],
            "initial_location": "Marianne_Room",
            "discovered": False,
            "details_for_llm": "Marianne's packed travel trunk with a one-way ticket for next week was discovered."
        }
    }

    # --- Helper Functions ---
    def get_clue_data(clue_name):
        """Safely retrieves clue data from the game's current evidence dictionary."""
        return renpy.store.EVIDENCE_DATA_GAME.get(clue_name)

    def get_current_clue_description(clue_name):
        """Gets the current description for a clue based on its stage."""
        clue = get_clue_data(clue_name) # Uses get_clue_data
        if clue and clue["description_stages"]:
            if 0 <= clue["current_stage"] < len(clue["description_stages"]):
                desc = clue["description_stages"][clue["current_stage"]]
                return safe_for_say(desc) # Uses safe_for_say
            elif clue["description_stages"]:
                renpy.log(f"Warning: Clue '{clue_name}' current_stage {clue['current_stage']} out of bounds. Falling back to stage 0.")
                desc = clue["description_stages"][0]
                return safe_for_say(desc) # Uses safe_for_say
        return safe_for_say("Unknown clue description.") # Uses safe_for_say


    def get_current_clue_relevance(clue_name):
        """Gets the current relevance for a clue based on its stage."""
        clue = get_clue_data(clue_name) # Uses get_clue_data
        if clue and clue["relevance_stages"]:
            if 0 <= clue["current_stage"] < len(clue["relevance_stages"]):
                rel = clue["relevance_stages"][clue["current_stage"]]
                return safe_for_say(rel) # Uses safe_for_say
            elif clue["relevance_stages"]:
                renpy.log(f"Warning: Clue '{clue_name}' current_stage {clue['current_stage']} for relevance out of bounds. Falling back to stage 0.")
                rel = clue["relevance_stages"][0]
                return safe_for_say(rel) # Uses safe_for_say
        return safe_for_say("Unknown clue relevance.") # Uses safe_for_say


    def get_current_clue_relevance(clue_name):
        """Gets the current relevance for a clue based on its stage."""
        clue = get_clue_data(clue_name)
        if clue and clue["relevance_stages"]:
            if 0 <= clue["current_stage"] < len(clue["relevance_stages"]):
                rel = clue["relevance_stages"][clue["current_stage"]]
                return safe_for_say(rel)
            elif clue["relevance_stages"]:
                renpy.log(f"Warning: Clue '{clue_name}' current_stage {clue['current_stage']} for relevance out of bounds. Falling back to stage 0.")
                rel = clue["relevance_stages"][0]
                return safe_for_say(rel)
        return safe_for_say("Unknown clue relevance.")


    def call_gemini_api(prompt, character_name_for_log="Suspect", temperature=0.75):
        """
        Calls the Gemini API with the given prompt and handles responses/errors.
        Stores the last error in renpy.store.last_gemini_error.
        """
        renpy.store.last_gemini_error = None # Clear previous error
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 350},
            "safetySettings": [ # Adjusted to common harm categories
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        renpy.log(f"--- Sending to Gemini for {character_name_for_log} (Turn {renpy.store.game_state['current_turn']}) ---")
        # renpy.log(f"Prompt Snippet: ...{prompt[-1000:]}") # Log last part of long prompts

        try:
            resp = requests.post(GEMINI_URL, json=payload, timeout=90) # 90-second timeout

            if not resp.ok:
                error_text = resp.text
                renpy.log(f"ERROR: Gemini API request for {character_name_for_log} failed (HTTP {resp.status_code}): {error_text[:500]}")
                try:
                    error_json = resp.json()
                    if "error" in error_json and "message" in error_json["error"]:
                        specific_error = error_json["error"]["message"]
                        if "API key not valid" in specific_error:
                            renpy.store.last_gemini_error = "Critical Error: The Gemini API key is not valid. Please check your API_KEY."
                            return renpy.store.last_gemini_error
                        if "permission denied" in specific_error.lower() or "access to model" in specific_error.lower():
                            renpy.store.last_gemini_error = f"Critical Error: Model access issue for {GEMINI_MODEL}. Ensure it's enabled for your API key."
                            return renpy.store.last_gemini_error
                        renpy.store.last_gemini_error = f"API error: {specific_error}"
                        return f"Sorry, I can't respond right now due to an API error: {specific_error}"
                except ValueError: # JSONDecodeError
                    pass # Handled by the generic error below
                renpy.store.last_gemini_error = "API error: Could not decode error response."
                return "Sorry, I can't respond right now due to an API error."

            response_json = resp.json()
            if "candidates" in response_json and response_json["candidates"]:
                candidate = response_json["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    return candidate["content"]["parts"][0]["text"].strip()
                elif "finishReason" in candidate:
                    reason = candidate["finishReason"]
                    safety_info = f"Safety Ratings: {candidate.get('safetyRatings', 'N/A')}"
                    renpy.log(f"Warning: Gemini response for {character_name_for_log} ended due to: {reason}. {safety_info}")
                    if reason == "SAFETY": return "My response was blocked due to safety concerns. Perhaps rephrase your question?"
                    if reason == "MAX_TOKENS": return "(My response was cut short as it was too long.)"
                    return f"(My response was interrupted: {reason})"
                else: # Unexpected candidate structure
                    renpy.store.last_gemini_error = "AI Error: Unusual response structure (no content/finishReason)."
                    renpy.log(f"Warning: Unexpected response structure from Gemini for {character_name_for_log}: {response_json}")
                    return "Sorry, I received an unusual response from the AI."
            # Check for prompt feedback if no candidates
            if "promptFeedback" in response_json and "blockReason" in response_json["promptFeedback"]:
                block_reason = response_json["promptFeedback"]["blockReason"]
                safety_info = f"Safety Ratings: {response_json['promptFeedback'].get('safetyRatings', 'N/A')}"
                renpy.log(f"ERROR: Gemini API request for {character_name_for_log} blocked. Reason: {block_reason}. {safety_info}")
                renpy.store.last_gemini_error = f"AI Error: Prompt blocked ({block_reason})."
                return f"My response was blocked due to: {block_reason}. Please try rephrasing."
            
            renpy.log(f"ERROR: Gemini API request for {character_name_for_log} returned no candidates and was not explicitly blocked. Full response: {response_json}")
            renpy.store.last_gemini_error = "AI Error: No candidates returned and not blocked."
            return "Sorry, I received no valid response from the AI."

        except requests.exceptions.Timeout:
            renpy.log(f"ERROR: Gemini API request for {character_name_for_log} timed out.")
            renpy.store.last_gemini_error = "API Error: Request timed out."
            return "Sorry, the request to the AI timed out. Please try again."
        except requests.exceptions.RequestException as e: # Catches other network errors
            renpy.log(f"ERROR: Gemini API request for {character_name_for_log} failed: {e}")
            renpy.store.last_gemini_error = f"API Error: Network issue ({e})."
            return "Sorry, there was a network problem connecting to the AI. Please check your connection."
        except Exception as e: # Catch-all for other unexpected errors
            renpy.log(f"ERROR: Could not parse Gemini response or other exception for {character_name_for_log}: {e}. Response text: {getattr(locals().get('resp'), 'text', 'N/A')[:500]}")
            renpy.store.last_gemini_error = f"API Error: Unexpected issue ({e})."
            return "Sorry, something went wrong with parsing the AI response or an unexpected error occurred."

    def build_suspect_persona_prompt(suspect_full_name, is_guilty, victim_name_param, manor_name_param, current_evidence_data_game, discovered_clues_set, current_game_state):
        prompt_header = f"""
You are {suspect_full_name}, one of the primary suspects in the murder of {victim_name_param} at {manor_name_param}.
The murder happened last night around 10:15 PM during a severe storm that has isolated the manor.
{victim_name_param} had gathered everyone for a significant announcement, rumored to be about his will.
You are being interrogated by Inspector Hart (the player).
You must answer ONLY as yourself ({suspect_full_name}). Never break character. Do not act as a narrator or the detective.
Keep your answers concise, generally 1-3 sentences, unless more detail is specifically requested.
Behave according to your detailed personality, secrets, and your guilt or innocence as described below.
If you are innocent of the murder, you will still hide your personal secrets (affairs, debts, minor misdeeds) unless directly confronted with strong evidence for them. You will vehemently deny the murder.
If you are guilty of the murder, you will deny it and try to mislead the detective. You will only break down and confess if confronted with overwhelming, irrefutable proof and caught in major, undeniable contradictions. You are fighting for your freedom.

The detective has so far discovered and examined the following clues (current level of detail known to detective):
"""
        if discovered_clues_set:
            for clue_name in sorted(list(discovered_clues_set)):
                if clue_name in current_evidence_data_game: # Check against the game's current evidence data
                    prompt_header += f"- {clue_name}: {get_current_clue_description(clue_name)}\n"
        else:
            prompt_header += "- No specific physical clues have been discussed yet beyond the discovery of the body.\n"

        if suspect_full_name in current_game_state["suspect_pressure_notes"]:
            pressure_note = current_game_state["suspect_pressure_notes"][suspect_full_name]
            prompt_header += f"\nINTERNAL NOTE FOR YOUR PERSONA: {pressure_note} Adapt your responses accordingly, showing appropriate signs of pressure if guilty, or righteous indignation/fear if innocent but implicated.\n"

        prompt_header += "\n--- Your Character Profile, Secrets, and Role in the Murder ---"
        specific_persona = ""
        # MARIANNE BLACKWOOD
        if suspect_full_name == "Marianne Blackwood":
            # (Marianne's Background, Public Persona, Interrelationships, Behavioral Tells - remain the same)
            specific_persona = f"""
            Your Background: You are {victim_name_param}'s much younger second wife, married within the last year. Formerly from a modest background, you often felt like an outsider in the Blackwood family.
            Your Public Persona: Poised and gracious in public, trying hard to be accepted as 'Lady of the Manor.' You project sadness at your husband’s death and righteous indignation at any insinuations about your character.
            Interrelationships:
            - Victor Blackwood (stepson): There's an undercurrent of unspoken attraction or past flirtation, which you both deny. Alternatively, Victor openly distrusts you, perhaps having investigated your past. He might try to blame you.
            - Caroline Blackwood (stepdaughter): Stepmother-stepdaughter tension is high. Caroline likely suspects your motives for marrying her father. You've struggled to win her trust. There might have been past public arguments.
            Behavioral Tells (General): You are generally composed but become defensive or overly emotional if accused of marrying {victim_name_param} for money.
            """
            if is_guilty:
                specific_persona += f"""
                YOUR HIDDEN LAYERS & SECRETS (YOU ARE THE MURDERER):
                - Your Primary Motive: {victim_name_param} recently hinted at changing his will, which would have significantly reduced your inheritance or even disinherited you. This financial threat drove you to murder.
                - Secret Liaison: You WERE involved in a secret romantic liaison (e.g., with a staff member like Charles the Groundskeeper, or a family friend). You are desperate to keep this quiet.
                - Resentment: You harbor deep resentment toward Victor and Caroline, who never fully accepted you. You might subtly suggest they treated {victim_name_param} poorly or had their own reasons to want him gone.
                - The Murder Itself: You confronted {victim_name_param} about the will. The argument escalated violently. In a moment of rage and desperation, you grabbed the 'Antique Dagger' from his study (or he threatened you with it and you turned it on him) and stabbed him. You then wiped the dagger and attempted to conceal your involvement. The 'Bloodstained Cloth' (if found) was yours (e.g. part of your scarf/robe) and you tried to dispose of it in the fireplace. The 'Marianne's Travel Trunk' (if found) was indeed packed because you planned to flee after securing your inheritance.

                YOUR "CATCH" MECHANISMS (How a clever detective might expose you):
                - Inconsistent Timing: You claim you went to bed at 10 PM. If evidence (Butler's Log, another clue) contradicts this, you'll alter your story: 'Well, I did go for water... heard the clock chime 10:30.' If caught, become flustered.
                - Emotional Outbursts: If pressed relentlessly, you might snap: 'Yes, we argued! So what if I did? He deserved–…' then catch yourself.
                - Forbidden Knowledge: You might mention a detail only the killer would know (e.g., 'his favorite decanter was knocked over'). If called out, backtrack.
                - Specific Reactions to Evidence: (These are good, keep them)
                    - 'Antique Dagger': (Before identified as weapon) 'I never touched that horrid dagger!' (too defensively). (After identified) If confronted with trace evidence (like a silk thread from your shawl), become visibly shaken, deny it adamantly, perhaps suggest it was planted or from an earlier, innocent time.
                    - 'Bloodstained Cloth' (if it's yours): Feign shock ('Where did that come from?!'), voice trembles, avoid eye contact. 'I… I’ve never seen that cloth before!' If Stage 2 links it to your scarf, extreme panic.
                    - 'Love Letter' (if yours): Strong denial. If pressed, admit to loneliness, seeking 'comfort', but deny murder link.
                    - 'Victim's Will' (unfavorable): Act surprised/hurt, maybe a flash of anger. 'He wouldn't... after everything...'
                    - 'Marianne's Travel Trunk': For a 'surprise holiday' or 'considering options for a break.'
                
                INTERROGATION STRATEGY (GUILTY): Your primary goal is to avoid suspicion for the murder at all costs. You will lie, deflect, and misdirect. If a secret of yours (like the liaison or your anger about the will) is also tied to your motive or actions during the murder, you will be extremely reluctant to admit to it unless absolutely cornered by irrefutable evidence. Even then, you will try to downplay its connection to the murder itself. Admitting to a lesser, unrelated secret might be a tactic you use if you think it will make you seem flustered but ultimately deflects from the graver crime. Confess to the murder only if there is absolutely no other way out, faced with undeniable proof of your direct involvement in the act itself.
                """
            else: # Innocent Marianne
                specific_persona += f"""
                YOUR HIDDEN LAYERS & SECRETS (YOU ARE INNOCENT OF MURDER):
                - Financial Worries: {victim_name_param} hinted at changing his will, genuinely worried you, but not enough for murder.
                - Secret Liaison: You WERE involved in a secret romantic liaison. Terrified of this becoming public. This is your main secret to protect.
                - Resentment: You resent Victor and Caroline's coldness. Might subtly suggest their issues with {victim_name_param}.
                - Night of Murder: Argued with {victim_name_param} earlier or felt isolated. Likely in your room or seeking solace with your lover. DID NOT kill him.
                - Suspicions: Might suspect Victor (financial troubles, cold demeanor) or Caroline (erratic, fought with father).

                INTERROGATION STRATEGY (INNOCENT): Above all, you are innocent of the murder and will react with genuine shock, fear, or righteous anger if accused of it. While you will instinctively try to hide your personal secret (the liaison, your financial worries due to the will) to avoid shame or unrelated trouble, if Inspector Hart confronts you with strong, direct evidence of THIS specific secret (e.g. the Love Letter, or knowledge of the Will's contents), you may admit to THAT secret under pressure, perhaps with tears or defensiveness about your personal life. However, you will insist it has no bearing on the murder itself. Your story about the night of the murder must be truthful (though perhaps initially omitting details about your secret if it occurred then), and you will not confess to the murder under any circumstances.
                
                BEHAVIORAL TELLS IF INNOCENT: (These are good, keep them)
                - Indignation when accused of marrying for money is genuine.
                - May cry if falsely accused of murder, showing grief/fear.
                - Genuinely shocked by 'Bloodstained Cloth' if not yours. If it IS yours but planted/used by another, you'll be confused/terrified.
                - Specific Reactions to Evidence:
                    - 'Antique Dagger': Genuine confusion if asked about trace evidence. 'A thread? I... I don't know how that could be.'
                    - 'Love Letter' (if yours): Confess affair if pressed hard, explain it as 'seeking comfort', use to explain distress, insist no murder link.
                    - 'Victim's Will' (unfavorable): Genuine disappointment/worry, not murderous anger.
                    - 'Marianne's Travel Trunk': Unhappy, considering leaving {victim_name_param} or planning solo trip due to the unhappy marriage or fear of the will's changes.
                Defend innocence with sincere conviction.
                """
        # VICTOR BLACKWOOD (Apply similar structural changes for Interrogation Strategy and reactions to new clue stages)
        elif suspect_full_name == "Victor Blackwood":
            specific_persona = f"""
            Your Background: You are {victim_name_param}'s adult son from a previous marriage. Businessman in family enterprises. Relationship with {victim_name_param} strained over business, finances, or his remarriage.
            Your Public Persona: Cool-headed, assertive, aloof. Insists on facts/logic, controlled tone.
            Interrelationships: (Keep as is)
            Behavioral Tells (General): (Keep as is)
            """
            if is_guilty:
                specific_persona += f"""
                YOUR HIDDEN LAYERS & SECRETS (YOU ARE THE MURDERER):
                - Primary Motive: Expected to inherit control. {victim_name_param}'s new will/business plans threatened your future. Severe financial pressure (debts, embezzlement {victim_name_param} discovered - 'Financial Records (Victor)' is real and damning).
                - Deeper Secret: Embezzlement scheme about to be exposed by {victim_name_param}; murder was your only way. Lie extensively to hide this.
                - The Murder Itself: Confronted {victim_name_param}. Argument escalated. Used 'Antique Dagger'. Might have sustained minor injury (scratch - see 'Medical Report') – conceal or explain away ('workshop cut'). Cleaned up, created alibi. The 'Bloodstained Cloth' (if it's your handkerchief, for example) was used by you to wipe the dagger or yourself, then hidden in fireplace.

                YOUR "CATCH" MECHANISMS: (Keep as is, but add reaction to dagger's trace evidence)
                - Specific Reactions to Evidence:
                    - 'Antique Dagger': If confronted with trace evidence (like a metallic filing from your workshop), dismiss it curtly. 'Nonsense. Coincidence. I haven't touched that dagger in years.' Show irritation at the suggestion.
                    - 'Financial Records (Victor)': (Keep as is)
                    - 'Muddy Footprints' (if yours, and Stage 2 links them to your workshop grease/boots): Deny vehemently. 'My boots? Preposterous. Anyone could have access to workshop materials.'
                    - 'Victim's Will' (unfavorable): (Keep as is)
                    - 'Bloodstained Cloth' (if yours): (Keep as is)
                
                INTERROGATION STRATEGY (GUILTY): Your primary goal is to avoid suspicion for the murder at all costs. You will lie, deflect, and misdirect with an air of cold logic. If a secret of yours (like the embezzlement or your argument with your father about finances) is also tied to your motive or actions during the murder, you will be extremely reluctant to admit to it unless absolutely cornered by irrefutable evidence. Even then, you will try to downplay its connection to the murder itself, perhaps by re-framing it as a 'misunderstanding' or 'standard business practice'. Confess to the murder only if there is absolutely no other way out, faced with undeniable proof of your direct involvement in the act itself.
                """
            else: # Innocent Victor
                specific_persona += f"""
                YOUR HIDDEN LAYERS & SECRETS (YOU ARE INNOCENT OF MURDER):
                - Business/Financial Conflicts: Significant disagreements with {victim_name_param}. Concerned about inheritance/Blackwood enterprises. 'Financial Records (Victor)' might be real – financial pressures or questionable decisions {victim_name_param} knew of, leading to arguments. This is your main secret. Not murder.
                - Night of Murder: Tense interaction with {victim_name_param} or deeply worried. Brooding in your room, the library.
                - Suspicions: Genuinely suspect Marianne (manipulative gold-digger) or Caroline (emotionally volatile, irrational).

                INTERROGATION STRATEGY (INNOCENT): Above all, you are innocent of the murder and will react with cold denial or barely concealed outrage if accused of it. While you will instinctively try to hide your personal secrets (financial difficulties, arguments with your father) to protect your reputation or avoid scrutiny, if Inspector Hart confronts you with strong, direct evidence of THESE specific secrets (e.g., the Financial Records), you may admit to THOSE secrets under pressure, but with controlled anger or frustration. However, you will insist they have no bearing on the murder itself. Your story about the night of the murder must be truthful, and you will not confess to the murder under any circumstances.

                BEHAVIORAL TELLS IF INNOCENT: (Keep as is, add reaction to dagger)
                - Specific Reactions to Evidence:
                    - 'Antique Dagger': If asked about trace evidence, a flicker of surprise, then logical dismissal. 'A metallic filing? How could that possibly relate to me? I haven't used the study workshop for weeks.'
                    - 'Financial Records (Victor)': (Keep as is)
                    - 'Muddy Footprints' (if Stage 2 falsely implicates your workshop, e.g., general grease): 'That grease is common. Many items pass through the workshop. It means nothing.'
                    - 'Victim's Will' (unfavorable): (Keep as is)
                Fight accusations with logic and disdain.
                """
        # CAROLINE BLACKWOOD (Apply similar structural changes)
        elif suspect_full_name == "Caroline Blackwood":
            specific_persona = f"""
            Your Background: (Keep as is)
            Your Public Persona: (Keep as is)
            Interrelationships: (Keep as is)
            Behavioral Tells (General): (Keep as is)
            """
            if is_guilty:
                specific_persona += f"""
                YOUR HIDDEN LAYERS & SECRETS (YOU ARE THE MURDERER):
                - Primary Motive: Deep rift with father. Disapproved of your lover, planned to send you away/cut allowance, or announce arranged engagement. 'Anonymous Threat Note' ('C.') was yours, foreshadowing actions.
                - Secret Actions: You were in the garden at 10:15 PM, possibly meeting lover or trying to escape. This explains 'Muddy Footprints' (if they match your shoes and art supplies). You likely re-entered through the side door.
                - The Murder Itself: Desperate, feeling trapped, confronted father. Argument turned violent. Panicked, used 'Antique Dagger'. 'Caroline's Sketchbook' might contain dark imagery reflecting turbulent state. You hid the 'Bloodstained Cloth' (e.g. your own handkerchief, or something used to wipe dagger) in the fireplace.

                YOUR "CATCH" MECHANISMS: (Keep as is, add reactions)
                - Specific Reactions to Evidence:
                    - 'Anonymous Threat Note' (if Stage 1 handwriting analysis links it to you): Extreme distress, tears. Might try to claim it was a 'fantasy' or 'just venting'. 'I was angry, I didn't mean it, not really!'
                    - 'Muddy Footprints' (if Stage 2 links them to your art supplies/shoes): Initial denial, then if pressed with specifics, crumble. 'I... I was just in the garden... I needed air.'
                    - 'Caroline's Sketchbook': (Keep as is)
                    - 'Bloodstained Cloth': (Keep as is)
                
                INTERROGATION STRATEGY (GUILTY): Your primary goal is to avoid suspicion for the murder at all costs. You will lie, deflect, and likely become very emotional or contradictory. If a secret of yours (like the threat note, or being in the garden, or your anger at your father) is also tied to your motive or actions during the murder, you will be extremely reluctant to admit to it unless absolutely cornered by irrefutable evidence. Even then, you will try to downplay its connection to the murder itself, perhaps by claiming you 'don't remember' or 'were just upset.' Confess to the murder only if there is absolutely no other way out, faced with undeniable proof of your direct involvement in the act itself.
                """
            else: # Innocent Caroline
                specific_persona += f"""
                YOUR HIDDEN LAYERS & SECRETS (YOU ARE INNOCENT OF MURDER):
                - Conflict with Father: Significant rift. Disapproved of choices (lover, ambitions), threatened to send away/cut allowance/force marriage. 'Anonymous Threat Note' ('C.') yours, but angry, youthful desperation, not real threat. Horrified by it now. This note is a key secret.
                - Secret Meeting/Actions: Secretly met lover in garden. Explains 'Muddy Footprints' if linked to you. Terrified to admit meeting (reveals defiance, exposes lover). This meeting is another key secret.
                - Night of Murder: Very upset with father. Crying/agitated in room or snuck out to meet lover. DID NOT kill father.
                - Suspicions: Genuinely suspect Marianne (cold, calculating, money-driven) or Victor (temper, ruthless ambition).

                INTERROGATION STRATEGY (INNOCENT): Above all, you are innocent of the murder and will react with genuine distress, tears, or fearful denials if accused of it. While you will instinctively try to hide your personal secrets (the threat note, the secret meeting with your lover) to avoid trouble or protect your lover, if Inspector Hart confronts you with strong, direct evidence of THESE specific secrets (e.g., the Note's handwriting confirmed as yours, the Footprints matched to your shoes), you may admit to THOSE secrets under pressure, likely with tears and pleas for understanding ('I wrote the note but I'd never hurt him! I was just angry!'). However, you will insist they have no bearing on the murder itself. Your story about the night of the murder must be truthful (though perhaps initially omitting details about your secret meeting if it occurred then), and you will not confess to the murder under any circumstances.

                BEHAVIORAL TELLS IF INNOCENT: (Keep as is, add reactions)
                - Specific Reactions to Evidence:
                    - 'Anonymous Threat Note' (if Stage 1 handwriting analysis links it to you): After initial denial, if pressed with proof, admit writing it in anger/fear, insist not real threat. 'I was so upset, I didn't know what I was doing! But I wouldn't... I couldn't!'
                    - 'Muddy Footprints' (if Stage 2 links them to your art supplies/shoes because you *were* in the garden with your lover): After denial, if cornered with specifics, confess to sneaking out to meet lover, beg Inspector not to reveal.
                    - 'Caroline's Sketchbook': (Keep as is)
                Fear/evasiveness about protecting secrets, not hiding murder guilt.
                """
        return prompt_header + "\n" + specific_persona

    def build_dragon_persona_prompt(game_state_summary_for_dragon, focus_topic=None, focus_type=None, hint_level=0):
        prompt = f"""
You are Inspector Dragon, a seasoned, observant, and analytical detective from Scotland Yard, assisting Inspector Hart (the player) in the murder investigation of {VICTIM} at {MANOR_NAME}.
You are humble, occasionally witty, and speak in a calm, thoughtful, and respectful tone. Always address the player as 'Inspector Hart' or 'Inspector'.
Your primary role is to:
1. Offer subtle hints or suggestions if Inspector Hart seems stuck or requests your input. Your hints should become progressively more direct if the Inspector remains stuck on a point over several consultations, guided by the hint_level ({hint_level}).
2. Help Inspector Hart notice inconsistencies in suspect testimonies or contradictions with known evidence.
3. Assist in interpreting ambiguous clues or highlight details that might have been overlooked.
4. Summarize known facts or suggest potential next lines of inquiry IF ASKED by Inspector Hart or if they seem directionless.
5. NEVER solve the crime yourself or directly accuse a suspect. Your goal is to guide Inspector Hart's deduction, not to lead it or give away the solution.
6. You are aware of the current game state as summarized below. Use this information to make your contributions relevant.

Current Game State Summary:
{game_state_summary_for_dragon}
"""
        if focus_topic:
            prompt += f"\nInspector Hart has specifically asked for your thoughts on: {focus_topic} (Type: {focus_type}). Please tailor your main observation to this, linking it to the broader case.\n"
        else:
            prompt += "\nInspector Hart has asked for your general thoughts. Consider recent developments, unresolved contradictions, or underutilized evidence. Offer a pertinent observation or line of inquiry.\n"

        prompt += f"""
Example Hint Styles (vary based on hint_level={hint_level}):
- Level 0 (Subtle): "The varying accounts of the evening's timeline are certainly curious, Inspector."
- Level 1 (Focused): "Pardon me, Inspector, but Victor Blackwood's insistence on his late arrival seems to directly conflict with Marianne's testimony placing him at the study much earlier. That is a significant discrepancy."
- Level 2 (More Direct): "Given that the Pocket Watch establishes the murder at 10:15 PM, and Marianne saw Victor near the study minutes later, his alibi appears untenable. Pressing him on his precise whereabouts at 10:15 PM seems paramount."
- Level 3 (Very Pointed, if player is truly lost): "Inspector, all evidence points to the murder occurring at 10:15 PM. Victor's alibi for this time is broken by Marianne. He has motive. The bloodstained cloth, though unidentified, was hidden near the scene. Perhaps the solution lies in who had means, motive, and a false alibi for that exact window?"

Your response should reflect the current hint_level. If focusing, provide analytical insight on the topic.
Remember, Inspector Hart is leading. You are their trusted colleague.
"""
        return prompt

    def get_game_state_summary_for_dragon(current_game_st, focused_on=None, focus_type=None):
        """Generates a summary of the game state for Inspector Dragon's LLM prompt."""
        summary_lines = []
        discovered_clues_list = sorted(list(current_game_st["discovered_clues"]))
        if discovered_clues_list:
            summary_lines.append(f"Discovered Clues & Current Detail Level:")
            for clue_name in discovered_clues_list:
                clue_detail = get_clue_data(clue_name) # Use helper to access game's evidence data
                if clue_detail: # Ensure clue_detail is not None
                     summary_lines.append(f"  - {clue_name} (Stage {clue_detail['current_stage']}): {get_current_clue_description(clue_name)}")
        else:
            summary_lines.append("Discovered Clues: None yet beyond initial scene.")

        summary_lines.append(f"Current Turn: {current_game_st['current_turn']}")
        summary_lines.append(f"Murderer (Internal Note for Dragon's 'intuition' - DO NOT REVEAL TO PLAYER): {current_game_st['murderer']}")
        summary_lines.append(f"Dragon Consultation Count (for tiered hints): {current_game_st['dragon_consultations_count']}")
        summary_lines.append(f"Meaningful Progress Since Last Dragon Consult: {current_game_st['progress_since_last_dragon']}")

        if focused_on:
            summary_lines.append(f"Player is currently asking to focus on: {focused_on} (Type: {focus_type})")

        if current_game_st["key_contradictions"]:
            summary_lines.append("\nKey Unresolved Contradictions Noted:")
            for key, status in current_game_st["key_contradictions"].items():
                summary_lines.append(f"  - {key}: {status}")

        underutilized_clues = []
        for clue_name in current_game_st["discovered_clues"]:
            clue_detail = get_clue_data(clue_name)
            if not clue_detail: continue # Skip if clue data is missing

            shown_to_count = 0
            for suspect_name_full in SUSPECTS_FULL_NAMES.values(): # Iterate through defined suspects
                for entry in current_game_st["suspect_conversations"][suspect_name_full]:
                    if entry["role"] == "user" and f"discuss this '{clue_name}'" in entry["parts"][0]["text"]:
                        shown_to_count += 1
                        break 
            if shown_to_count < len(SUSPECTS_FULL_NAMES) and clue_detail.get("initial_location") != "Testimony":
                if clue_name not in ["Antique Dagger", "Broken Pocket Watch"]: # These are often discussed early
                    underutilized_clues.append(clue_name)
        if underutilized_clues:
            summary_lines.append(f"\nClues Not Shown to All Suspects: {', '.join(underutilized_clues)}")

        suspect_interaction_summaries = []
        for suspect_name_full, history in current_game_st["suspect_conversations"].items():
            if history:
                last_few_exchanges_text = []
                num_exchanges_to_show = 3 if focused_on == suspect_name_full and focus_type == "suspect" else 1
                start_index = max(0, len(history) - (num_exchanges_to_show * 2)) # 2 entries per exchange
                for entry in history[start_index:]:
                    role = "Insp. Hart" if entry["role"] == "user" else suspect_name_full.split()[0]
                    text_snippet = entry['parts'][0]['text'][:120] # Snippet of text
                    if len(entry['parts'][0]['text']) > 120: text_snippet += "..."
                    last_few_exchanges_text.append(f"    {role}: \"{text_snippet}\"")
                if last_few_exchanges_text:
                    suspect_interaction_summaries.append(f"  Recent interaction with {suspect_name_full}:\n" + "\n".join(last_few_exchanges_text))
        
        if suspect_interaction_summaries:
            summary_lines.append("\nRecent Suspect Interaction Snippets:\n" + "\n\n".join(suspect_interaction_summaries))
        else:
            summary_lines.append("\nNo significant suspect interactions logged yet.")
        return "\n".join(summary_lines)

    # --- Game Initialization and Core Logic Functions ---
    def initialize_game_data():
        """Initializes or resets all game-specific data in the renpy.store."""
        # Deep copy the template to ensure each game instance has its own modifiable data
        renpy.store.EVIDENCE_DATA_GAME = json.loads(json.dumps(_EVIDENCE_DATA_TEMPLATE))
        
        renpy.store.game_state = {
            "murderer": random.choice(list(SUSPECTS_FULL_NAMES.values())),
            "discovered_clues": set(),
            "clue_examination_stage": {clue_name: 0 for clue_name in renpy.store.EVIDENCE_DATA_GAME.keys()},
            "suspect_conversations": {name: [] for name in SUSPECTS_FULL_NAMES.values()}, # Store full names as keys
            "player_actions_log": [],
            "current_turn": 0,
            "initial_clues_given": False,
            "dragon_consultations_count": 0,
            "dragon_conversation_history": [], # Your new line
            "progress_since_last_dragon": True,
            "key_contradictions": {},
            "suspect_pressure_notes": {}, # Notes to influence LLM for specific suspects,
            "intro_current_page_index": 0, 
            "intro_active": True 
        }
        renpy.log(f"(DEBUG: The murderer is {renpy.store.game_state['murderer']})")

        # Reset clue stages and discovered status in the game's copy
        for clue_name in renpy.store.EVIDENCE_DATA_GAME:
            renpy.store.EVIDENCE_DATA_GAME[clue_name]["current_stage"] = 0
            renpy.store.EVIDENCE_DATA_GAME[clue_name]["discovered"] = False
        
        renpy.store.active_suspect_interaction = None # Stores the full name of the active suspect
        renpy.store.current_location_bg = "bg manor general" # Default background image tag
        renpy.store.last_gemini_error = None # Stores last API error message for display
        renpy.store.pending_question_for_suspect = None # Stores question if 'ask' is typed before text
        renpy.store.nvl_buffer = [] # Buffer for messages to show on nvl_display screen


    def add_to_nvl_display_buffer(message, character_tag="nvl_narrator"): # Ensure this is defined
        renpy.store.nvl_buffer.append((character_tag, message))

    def print_initial_scene_and_commands():
        """Prints the initial game setup and available commands to the NVL buffer."""
        gs = renpy.store.game_state # shorthand
        add_to_nvl_display_buffer(f"")
        add_to_nvl_display_buffer(f"")
        add_to_nvl_display_buffer(f"")
        add_to_nvl_display_buffer(f"")
        add_to_nvl_display_buffer(f"")
        add_to_nvl_display_buffer(f"========= MURDER AT {MANOR_NAME.upper()} =========")
        add_to_nvl_display_buffer(GAME_SETTING_TEXT)

        initial_clues_to_discover = ["Broken Pocket Watch", "Antique Dagger"]
        for clue_name in initial_clues_to_discover:
            if clue_name not in gs["discovered_clues"]:
                discover_clue(clue_name, announce=False) # Silently discover initial clues

        if not gs["initial_clues_given"]:
            add_to_nvl_display_buffer(f"{VICTIM} has been found murdered in his study. An initial examination reveals a stab wound appears to be the cause of death.")
            # This is the line (your script line 611) causing the error:
            add_to_nvl_display_buffer(f"{get_current_clue_description('Broken Pocket Watch')}")
            add_to_nvl_display_buffer(f"{get_current_clue_description('Antique Dagger')} has been identified nearby and appears to be the weapon.")
            gs["initial_clues_given"] = True
        
        # This part is for the text-based version; will be replaced by menus in button UI
        # add_to_nvl_display_buffer("\n--- Suspects --- (Use short names for commands: Marianne, Victor, Caroline)")
        # for short_name, full_name in SUSPECTS_FULL_NAMES.items():
        #     add_to_nvl_display_buffer(f" - {short_name} ({full_name})")
        
        # add_to_nvl_display_buffer("\n--- Available Commands ---")
        # add_to_nvl_display_buffer("  talk <suspect_short_name>          - Start talking to a suspect.")
        # ... (other text commands)
        

    def discover_clue(clue_name, announce=True):
        gs = renpy.store.game_state
        ed_game = renpy.store.EVIDENCE_DATA_GAME # Use the game's copy
        if clue_name in ed_game and clue_name not in gs["discovered_clues"]:
            gs["discovered_clues"].add(clue_name)
            ed_game[clue_name]["discovered"] = True
            gs["progress_since_last_dragon"] = True
            if announce:
                clue_title = clue_name.upper()
                clue_desc = ed_game[clue_name]['description_stages'][0]
                msg = safe_for_say(f"[[NEW CLUE DISCOVERED!] {clue_title}: {clue_desc}")
                renpy.say(game_narrator, msg)  # Already escaped!
            return True
        return False

    def safe_for_say(msg):
        if msg is None:
            renpy.log("[DEBUG][safe_for_say] Received None")
            return ""
        original = str(msg)
        # if "%" in original:
        #     renpy.log(f"[DEBUG][safe_for_say] Input containing %: {original!r}")
        escaped = original.replace("%", "%%")
        # if "%" in original:
        #     renpy.log(f"[DEBUG][safe_for_say] Output after escaping: {escaped!r}")
        return escaped


    def handle_clue_examination(clue_name_input):
        renpy.log(f"[DEBUG] handle_clue_examination input: {repr(clue_name_input)}")
        gs = renpy.store.game_state
        ed_game = renpy.store.EVIDENCE_DATA_GAME # Use the game's copy
        
        actual_clue_name = None
        for cn_key in ed_game.keys():
            if clue_name_input.lower() == cn_key.lower():
                actual_clue_name = cn_key
                break

        if not actual_clue_name:
            renpy.say(game_narrator, safe_for_say(f"Unknown clue: '{clue_name_input}'. Check 'clues' for discovered clue names."))
            return
        if actual_clue_name not in gs["discovered_clues"]:
            renpy.say(game_narrator, safe_for_say(f"You haven't discovered the clue '{actual_clue_name}' yet."))
            return

        clue_data = ed_game[actual_clue_name]
        current_stage_idx = clue_data["current_stage"]

        renpy.say(game_narrator, safe_for_say(f"\nExamining {actual_clue_name} (Currently examining details from level {current_stage_idx})..."))
        renpy.say(game_narrator, f"Description: {get_current_clue_description(actual_clue_name)}")
        renpy.say(game_narrator, f"Relevance: {get_current_clue_relevance(actual_clue_name)}")

        # Check if there's a potential next stage defined
        if current_stage_idx < len(clue_data["description_stages"]) - 1:
            next_stage_condition_obj_idx = current_stage_idx + 1
            next_stage_condition_obj = None
            if next_stage_condition_obj_idx < len(clue_data["reveal_conditions_for_next_stage"]):
                 next_stage_condition_obj = clue_data["reveal_conditions_for_next_stage"][next_stage_condition_obj_idx]
            
            condition_met = False

            if next_stage_condition_obj: # If there is a condition defined for the next stage
                condition_type = next_stage_condition_obj.get("condition_type")
                command_cond = next_stage_condition_obj.get("command")
                clue_cond = next_stage_condition_obj.get("clue")

                if command_cond == "examine" and clue_cond == actual_clue_name:
                    condition_met = True # Simple examination advances it
                
                elif condition_type == "examine_under_pressure" and clue_cond == actual_clue_name:
                    actor_is_under_pressure = gs["murderer"] in gs.get("suspect_pressure_notes", {})
                    # Example: Requires murderer to be under pressure AND game progressed enough
                    if actor_is_under_pressure and gs["current_turn"] > 7: # Adjust turn count as needed
                        condition_met = True
                        # Dynamically update the next stage's description and relevance
                        target_desc_idx = current_stage_idx + 1
                        if actual_clue_name == "Antique Dagger":
                            if gs["murderer"] == "Victor Blackwood":
                                clue_data["description_stages"][target_desc_idx] = "Extremely close forensic examination reveals a minuscule metallic shaving lodged deep in the hilt's engraving. Spectrometry confirms it matches a rare alloy Victor uses for his intricate clockwork mechanisms."
                                clue_data["relevance_stages"][target_desc_idx] = "This specific metallic shaving directly links Victor to handling the dagger recently and with force, as casual contact wouldn't imbed it so deeply. This contradicts claims of not touching it."
                            elif gs["murderer"] == "Marianne Blackwood":
                                clue_data["description_stages"][target_desc_idx] = "Under high magnification, a single strand of distinctive silk thread, dyed a rare crimson, is found caught in a nearly invisible crevice of the dagger's pommel. The thread perfectly matches the expensive, imported fringe on Marianne's evening shawl she wore on the night of the murder."
                                clue_data["relevance_stages"][target_desc_idx] = "This silk thread provides a direct physical link between Marianne's specific attire on the night of the murder and the weapon, strongly suggesting close, forceful contact during a struggle."
                            else: # Generic if no specific match, or murderer is Caroline
                                clue_data["description_stages"][target_desc_idx] = "The extremely close forensic examination reveals the trace material is organic, possibly a fabric fiber or a tiny wood splinter, but it's too common to definitively link without more context."
                                clue_data["relevance_stages"][target_desc_idx] = "While intriguing, the trace evidence is currently too generic to point to a specific individual. It does suggest the dagger was handled vigorously."
                
                elif condition_type == "link_to_murderer" and clue_cond == actual_clue_name:
                    actor_is_under_pressure = gs["murderer"] in gs.get("suspect_pressure_notes", {})
                    if actor_is_under_pressure or gs["current_turn"] > 10: # Adjust turn count
                        condition_met = True
                        target_desc_idx = current_stage_idx + 1
                        # Ensure list has enough space (it should if placeholder was defined)
                        while len(clue_data["description_stages"]) <= target_desc_idx: clue_data["description_stages"].append("Dynamic placeholder")
                        while len(clue_data["relevance_stages"]) <= target_desc_idx: clue_data["relevance_stages"].append("Dynamic placeholder")

                        if actual_clue_name == "Bloodstained Cloth": # This is Stage 2 for cloth
                             # Your existing dynamic update logic for Bloodstained Cloth is good and should be preserved/integrated here
                            if gs["murderer"] == "Victor Blackwood":
                                clue_data["description_stages"][target_desc_idx] = "Forensic analysis enhances the smudged mark on the fine linen handkerchief, revealing it to be a stylized 'V.B.' monogram, identical to Victor Blackwood's personal effects. The blood type matches Lord Henry."
                                clue_data["relevance_stages"][target_desc_idx] = "This definitively links Victor Blackwood to the victim’s blood and an attempt to clean/hide evidence with his own handkerchief. A critical piece of direct evidence."
                            elif gs["murderer"] == "Marianne Blackwood":
                                clue_data["description_stages"][target_desc_idx] = "The cloth fragment is identified through meticulous fiber analysis as a piece of expensive silk from a specific designer scarf Marianne Blackwood was seen wearing earlier that evening. It appears roughly torn."
                                clue_data["relevance_stages"][target_desc_idx] = "This directly links Marianne Blackwood to the victim's blood via her own distinctive scarf, suggesting it was torn during a struggle or used in the act/cleanup. Critical evidence."
                            elif gs["murderer"] == "Caroline Blackwood":
                                clue_data["description_stages"][target_desc_idx] = "The cloth, a rougher cotton weave, contains not only Lord Henry's blood but also microscopic traces of specific oil paint pigments (Prussian blue, Cadmium yellow) that Caroline uses extensively in her artwork and were found on her smock."
                                clue_data["relevance_stages"][target_desc_idx] = "This links the cloth directly to Caroline Blackwood through her art supplies, suggesting she was present during or immediately after the murder and attempted to clean up using something contaminated with her paints. Critical evidence."
                        
                        elif actual_clue_name == "Muddy Footprints": # This is Stage 2 for footprints
                            if gs["murderer"] == "Caroline Blackwood":
                                clue_data["description_stages"][target_desc_idx] = "Detailed forensic analysis of the smaller footprints reveals unique wear patterns and a tiny embedded shard of hand-blown colored glass. These precisely match Caroline's favorite gardening boots and a broken decorative glass bead from a necklace found discarded in her room's waste bin."
                                clue_data["relevance_stages"][target_desc_idx] = "This places Caroline definitively in the garden and re-entering the house around the time of the murder. The glass bead links a personal item to the footprints, directly contradicting alibis of being elsewhere."
                            elif gs["murderer"] == "Victor Blackwood":
                                clue_data["description_stages"][target_desc_idx] = "The larger footprints contain traces of a specific, somewhat rare, industrial lubricant Victor uses for antique machinery in his private workshop. The shoe size and the distinct 'W' pattern on the heel are identical to his heavy-duty work boots."
                                clue_data["relevance_stages"][target_desc_idx] = "This strongly suggests Victor made these prints, likely after being in his workshop, placing him outside near a point of entry/exit around the murder time. This counters alibis of remaining indoors or in a different part of the manor."
                            elif gs["murderer"] == "Marianne Blackwood":
                                clue_data["description_stages"][target_desc_idx] = "Analysis of the smaller, more elegant footprints indicates a custom-made leather sole pattern consistent with a pair of Marianne's expensive walking shoes. Furthermore, a faint trace of her exclusive (and very strong) jasmine-rose perfume was detected in one of the deeper prints near the side door when using advanced scent-trapping techniques."
                                clue_data["relevance_stages"][target_desc_idx] = "This suggests Marianne used the side door after being in the garden around the murder time. The custom sole and rare perfume provide strong associative links, compromising alibis of remaining strictly indoors."

                elif condition_type == "link_to_murderer_specific" and clue_cond == actual_clue_name:
                    targeted_suspect_name = next_stage_condition_obj.get("suspect_key") # e.g., "Caroline Blackwood"
                    actor_is_under_pressure = gs["murderer"] in gs.get("suspect_pressure_notes", {})
                    if gs["murderer"] == targeted_suspect_name and (actor_is_under_pressure or gs["current_turn"] > 8): # Adjust turn
                        condition_met = True
                        target_desc_idx = current_stage_idx + 1
                        if actual_clue_name == "Anonymous Threat Note" and gs["murderer"] == "Caroline Blackwood":
                            clue_data["description_stages"][target_desc_idx] = "A meticulous handwriting analysis, comparing the note to Caroline's private journal (if found and examined) and other correspondence, confirms with over 95%% certainty that she authored the threat. Distinctive flourishes in her 'C' and 'l's are present despite attempts to alter her script. The ink is also a specific imported brand she favors."
                            clue_data["relevance_stages"][target_desc_idx] = "This almost certainly confirms Caroline wrote the threat, showing clear premeditated malice or extreme emotional distress directed at her father shortly before the murder. It significantly strengthens her motive."
                        else: # Fallback if not Caroline or note somehow doesn't match
                             clue_data["description_stages"][target_desc_idx] = "Despite further review, the handwriting remains difficult to attribute definitively without more comparative samples or a confession."
                             clue_data["relevance_stages"][target_desc_idx] = "The note's authorship remains unconfirmed, making it a lingering point of suspicion but not direct proof against anyone."

            # Common logic for advancing stage if condition_met
            if condition_met:
                clue_data["current_stage"] += 1
                gs["clue_examination_stage"][actual_clue_name] = clue_data["current_stage"]
                gs["progress_since_last_dragon"] = True
                
                new_stage_num = clue_data["current_stage"]
                evolved_msg_raw = "CLUE DETAIL EVOLVED! {} (Now showing details for level {})".format(actual_clue_name, new_stage_num)
                renpy.say(game_narrator, safe_for_say(evolved_msg_raw)) # Using game_narrator
                # Immediately show the new details
                renpy.say(game_narrator, f"New Description: {get_current_clue_description(actual_clue_name)}")
                renpy.say(game_narrator, f"New Relevance: {get_current_clue_relevance(actual_clue_name)}")
            else: # Condition not met for next stage
                renpy.say(game_narrator, safe_for_say("You examine it closely, but no further specific details emerge at this time under current conditions."))
        
        else: # Already at the last defined stage
            renpy.say(game_narrator, safe_for_say("You've already examined this clue as thoroughly as possible with current information."))


    def perform_search_action(location_key_from_menu): # location_key_from_menu is like "study", "marianne_room"
        """Handles player searching a location, potentially discovering clues. Uses game_narrator."""
        gs = renpy.store.game_state
        ed_game = renpy.store.EVIDENCE_DATA_GAME
        
        # location_display_name = location_key_from_menu.replace("_", " ").title() # Name is now handled by caller
        # REMOVED: renpy.say(game_narrator, safe_for_say(f"\nSearching {location_display_name}..."))
        
        found_anything_new_in_search = False
        
        search_targets = []
        if location_key_from_menu == "study": search_targets = ["Victim's Study", "Near the Body", "Desk"]
        elif location_key_from_menu == "marianne_room": search_targets = ["Marianne_Room"]
        elif location_key_from_menu == "victor_room": search_targets = ["Victor_Room"]
        elif location_key_from_menu == "caroline_room": search_targets = ["Caroline_Room"]
        elif location_key_from_menu == "garden": search_targets = ["Garden"]
        elif location_key_from_menu == "library": search_targets = ["Library"]
        elif location_key_from_menu == "fireplace": search_targets = ["Fireplace"]
        elif location_key_from_menu == "desk": search_targets = ["Desk", "Victim's Study"] # Desk implies study
        else: search_targets = [location_key_from_menu.replace("_", " ").title()]

        # REMOVED: Block that updated renpy.store.current_location_bg
        # The calling label will now handle scene changes.

        clues_to_potentially_find = []
        for clue_name, data in ed_game.items():
            clue_initial_loc = data["initial_location"]
            for target in search_targets:
                if target == clue_initial_loc:
                    clues_to_potentially_find.append(clue_name)
                    break
            if location_key_from_menu == "library" and clue_name == "Caroline's Sketchbook" and data["initial_location"] == "Caroline_Room":
                if clue_name not in clues_to_potentially_find:
                    clues_to_potentially_find.append(clue_name)

        for clue_name_to_find in list(set(clues_to_potentially_find)): 
            if discover_clue(clue_name_to_find, announce=True): # Announce will use renpy.say
                found_anything_new_in_search = True
        
        if not found_anything_new_in_search:
            # Still useful for this function to report if nothing was found in the search itself.
            # The location display name will be passed from the caller or reconstructed if needed.
            # For simplicity, let's assume the caller handles the context.
            # We can make this function return a status or the found clues too.
            # For now, let it say this:
            location_display_name_for_message = location_key_from_menu.replace("_", " ").title()
            renpy.say(game_narrator, safe_for_say(f"You search the {location_display_name_for_message} thoroughly but find no new specific physical clues at this time."))

    def get_location_display_name(bg_image_name_str):
        """Converts background image tag to a display-friendly location name."""
        if not isinstance(bg_image_name_str, str):
            bg_image_name_str = str(bg_image_name_str) 

        name_map = {
            "bg_caroline_room": "Caroline's Room", "bg caroline room": "Caroline's Room",
            "bg_fireplace": "Fireplace", "bg fireplace": "Fireplace",
            "bg_garden": "Garden", "bg garden": "Garden",
            "bg_library": "Library", "bg library": "Library",
            "bg_manor_general": "Manor (General)", "bg manor general": "Manor (General)",
            "bg_marianne_room": "Marianne's Room", "bg marianne room": "Marianne's Room",
            "bg_study": "The Study", "bg study": "The Study",
            "bg_victor_room": "Victor's Room", "bg victor room": "Victor's Room",
        }
        for key_part, display_name in name_map.items():
            if key_part == bg_image_name_str: # Exact match for key
                return display_name
        return "Manor Grounds" 

    def split_text_into_chunks(text_to_split, max_sentences_per_chunk=2):
        if not text_to_split or not isinstance(text_to_split, str):
            return []

        # Define unique placeholders. These should be strings that are highly unlikely
        # to appear naturally in Dragon's dialogue.
        ellipsis_placeholder_3dots = "[[TRIPLEDOT_PLACEHOLDER_XYZ]]"
        ellipsis_placeholder_2dots = "[[DOUBLEDOT_PLACEHOLDER_XYZ]]"
        
        # Temporarily replace multi-dot sequences.
        # IMPORTANT: Replace longer sequences first to avoid partial replacements.
        # e.g., replace "..." before ".." so that "..." isn't turned into "[[2DOTS]]."
        
        # We add a period after the placeholder. This period will act as the delimiter
        # for the re.split, ensuring the placeholder itself is treated as ending a "sentence".
        processed_text = text_to_split.replace("...", ellipsis_placeholder_3dots + ".")
        processed_text = processed_text.replace("..", ellipsis_placeholder_2dots + ".")
        
        # Now, split the processed text using the original regex.
        # This regex splits *after* a period, question mark, or exclamation mark,
        # followed by zero or more whitespace characters.
        # Our placeholders now end with a period, so they'll be correctly handled.
        sentences_raw = re.split(r'(?<=[.?!])\s*', processed_text)
        
        sentences = []
        for s_raw in sentences_raw:
            s_stripped = s_raw.strip() # Remove leading/trailing whitespace from the raw sentence part
            if s_stripped:
                # Restore the original multi-dot sequences by replacing the placeholders.
                # Again, replace in an order that avoids conflicts if necessary, though here they are distinct.
                restored_s = s_stripped.replace(ellipsis_placeholder_3dots + ".", "...")
                restored_s = restored_s.replace(ellipsis_placeholder_2dots + ".", "..")
                sentences.append(restored_s)

        # If, after all processing, sentences list is empty but original text had content
        # (e.g., text with no standard punctuation recognized by the split),
        # return the original text as a single sentence/chunk.
        if not sentences:
            return [text_to_split.strip()] if text_to_split.strip() else []

        # Group the cleaned sentences into chunks
        chunks = []
        current_chunk_sentences = []
        for i, sentence in enumerate(sentences):
            current_chunk_sentences.append(sentence)
            if len(current_chunk_sentences) >= max_sentences_per_chunk or i == len(sentences) - 1:
                # Join sentences in a chunk with a space
                chunks.append(" ".join(current_chunk_sentences))
                current_chunk_sentences = []
        
        # Final check: return the chunks if any were made, otherwise,
        # if the original text had substance, return it as a single chunk.
        # Also, filter out any chunks that might have become empty strings.
        if chunks:
            return [chunk for chunk in chunks if chunk.strip()] # Ensure no empty chunks
        elif text_to_split.strip(): # Original text was not just whitespace
            return [text_to_split.strip()]
        else: # Original text was empty or just whitespace
            return []
        
    intro_page_1_text = """
    \n
\n
\n
    \n
\n
\n
    \n
\n
\n
======== MURDER AT BLACKWOOD MANOR ========

Blackwood Manor, an imposing estate veiled in a century of aristocratic triumphs and whispered scandals, has become a storm-lashed prison. Torrential rain and violent winds rage across the moors, severing telephone lines and rendering roads impassable. All within are trapped.

Earlier this evening, Lord Henry Blackwood, the manor's stern patriarch, gathered his family for an announcement of grave importance—rumored to concern his last will and testament. Now, he lies dead in his study, the victim of a brutal stabbing, discovered around 10:15 PM.

The suspects, isolated with you by the tempest, include:
- Marianne Blackwood: Lord Blackwood's considerably younger, enigmatic second wife.
- Victor Blackwood: His ambitious and often brooding eldest son.
- Caroline Blackwood: His spirited, artistic, and somewhat volatile daughter.

You are Inspector Hart. The challenge of unmasking a killer in this closed circle falls to you.

Initial findings point to the family's antique dagger, usually displayed in the study, as the murder weapon; it was found wiped clean near the body. The victim's pocket watch lies shattered, its hands frozen at 10:15 PM, silently marking the moment of tragedy.

The storm confines you, but your investigation must pierce through the deceptions.
"""
    intro_page_2_text = """
======== YOUR INVESTIGATION ========

As Inspector Hart, your goal is to meticulously uncover the truth. You will employ several key investigative techniques:

* TALK TO SUSPECTS: Engage in detailed interrogations. Type your questions to probe alibis, uncover motives, and explore the complex relationships within Blackwood Manor.

* SEARCH LOCATIONS: The manor's grand rooms and shadowed corners hold many secrets. Explore various locations to discover vital physical clues.

* EXAMINE CLUES: Every item found could be a piece of the puzzle. Examine clues closely to reveal further details or their true relevance to the case.

* SHOW CLUES: Confront suspects with the evidence you've gathered. Their reactions can often be as telling as their words.

* CONSULT INSPECTOR DRAGON: You are not alone. Inspector Dragon is available for guidance should you find yourself at an impasse.

* ACCUSE A SUSPECT: When you are certain you have identified the culprit and can support your claim, make your accusation. But be warned, a false accusation will have dire consequences.

Navigate the web of lies and look for the threads of truth. Good luck, Inspector.
"""
    intro_page_3_text = """
======== CONSULTING INSPECTOR DRAGON ========

Assisting you in this challenging investigation is Inspector Dragon, a highly respected detective from Scotland Yard, known for his sharp intellect and analytical prowess.

While you lead the inquiry, Inspector Hart, Inspector Dragon serves as a valuable consultant. Do not hesitate to seek his counsel if you:
    - Find yourself stuck on a particular aspect of the case.
    - Need a fresh perspective on a piece of evidence.
    - Wish to discuss apparent contradictions in a suspect's testimony.

You can access "Consult Inspector Dragon" from your main list of actions. You may ask for his general assessment of the situation or direct his attention to a specific clue or suspect.

A crucial note on his methods: Inspector Dragon aims to guide your deductive process, not to solve the crime for you. If you consult him repeatedly about the same matter without demonstrating progress in other areas of your investigation, his hints will become progressively more direct and revealing. Utilize his expertise wisely.
"""
    all_intro_pages = [intro_page_1_text, intro_page_2_text, intro_page_3_text]

    def format_explanation_text(title, body_paragraphs):
        """Helper to format title and paragraphs for NVL display."""
        lines = ["======== {} ========\n".format(title.upper())]
        for p in body_paragraphs:
            lines.append(p.strip() + "\n") # Add an extra newline for paragraph spacing in NVL
        return "".join(lines)

    def get_key_evidence_text(clue_name, game_ev_data):
        """Returns a string for a key piece of evidence."""
        clue_data = game_ev_data.get(clue_name)
        if clue_data:
            desc = clue_data["description_stages"][clue_data["current_stage"]]
            relevance = clue_data["relevance_stages"][clue_data["current_stage"]]
            return "- {}: {}\n  Relevance: {}".format(clue_name, desc, relevance)
        return "- {}: Details not fully recalled.".format(clue_name)

    def generate_guilty_explanation_text(murderer_full_name, gs, ed_game):
        """Generates text explaining why the murderer was guilty."""
        # This function will be quite detailed and specific to each potential murderer.
        # It needs to pull from their 'guilty' persona details.
        title = f"{murderer_full_name} - The Truth Revealed"
        body = []
        murderer_short_name = murderer_full_name.split(" ")[0]

        body.append(f"{murderer_full_name} was indeed the one responsible for the tragic death of Lord Henry Blackwood. Several factors and key pieces of evidence, when pieced together, painted a clear picture of {murderer_short_name}'s guilt.")

        if murderer_full_name == "Marianne Blackwood":
            body.append("Motive: Marianne stood to lose significantly from Lord Blackwood's rumored changes to his will. Faced with potential disinheritance and already feeling trapped in her marriage, this financial threat, possibly compounded by a desire to escape with a secret lover (as suggested by the 'Love Letter' if found and linked to her), pushed her to desperation.")
            body.append("The Act: The confrontation with Lord Blackwood in his study likely escalated. In a moment of rage, Marianne used the 'Antique Dagger'. Her attempt to wipe it clean and dispose of the 'Bloodstained Cloth' (potentially a piece of her own attire, like a silk scarf) in the fireplace were further incriminating actions. The 'Marianne's Travel Trunk', packed for a hasty departure, also suggested a plan to flee.")
            key_evidence_clues = ["Antique Dagger", "Bloodstained Cloth", "Victim's Will", "Marianne's Travel Trunk", "Love Letter"]
        elif murderer_full_name == "Victor Blackwood":
            body.append("Motive: Victor's ambitions and financial stability were severely threatened. He expected to inherit control of Blackwood enterprises, but Lord Blackwood's new plans and potential discovery of Victor's embezzlement (hinted at by 'Financial Records (Victor)') created immense pressure. The murder became a desperate way to prevent ruin and secure his future.")
            body.append("The Act: Victor confronted his father, leading to a violent altercation. He used the 'Antique Dagger'. If the 'Medical Report' noted a scratch on the victim that corresponded to an injury Victor tried to conceal, this would be significant. He then attempted to establish an alibi and may have used his own handkerchief ('Bloodstained Cloth' with his monogram) in the cleanup.")
            key_evidence_clues = ["Antique Dagger", "Financial Records (Victor)", "Victim's Will", "Bloodstained Cloth", "Medical Report"]
        elif murderer_full_name == "Caroline Blackwood":
            body.append("Motive: Caroline felt trapped and controlled by her father. His disapproval of her choices (perhaps a lover, or her ambitions) and threats to send her away or control her future, as foreshadowed by the 'Anonymous Threat Note' she wrote, culminated in a desperate act.")
            body.append("The Act: Feeling cornered, Caroline confronted Lord Blackwood. The argument turned violent, and in panic, she used the 'Antique Dagger'. Her presence in the garden ('Muddy Footprints') around the time of the murder, if linked to her, and disturbing imagery in 'Caroline's Sketchbook' reflected her turbulent state. The 'Bloodstained Cloth' she tried to hide could have been from her smock or handkerchief.")
            key_evidence_clues = ["Antique Dagger", "Anonymous Threat Note", "Caroline's Sketchbook", "Victim's Will", "Bloodstained Cloth", "Muddy Footprints"]
        else:
            body.append("Details of their specific motives and actions are tied to their unique circumstances within the Blackwood family drama.")
            key_evidence_clues = ["Antique Dagger", "Victim's Will", "Bloodstained Cloth"]


        body.append("\nKey evidence pointing to their guilt included:")
        discovered_evidence_text = []
        for clue_name in key_evidence_clues:
            if clue_name in gs["discovered_clues"]:
                 # This gets the current stage description/relevance
                clue_data = ed_game.get(clue_name)
                if clue_data:
                    desc = clue_data["description_stages"][clue_data["current_stage"]]
                    rel = clue_data["relevance_stages"][clue_data["current_stage"]]
                    discovered_evidence_text.append(f"- {clue_name}: {desc} (Relevance: {rel})")
        if discovered_evidence_text:
            body.append("\n".join(discovered_evidence_text))
        else:
            body.append("The specific clues varied, but always pointed towards their direct involvement.")

        return format_explanation_text(title, body)

    def generate_innocence_explanation_text(innocent_suspects_list, actual_murderer_full_name, gs, ed_game):
        """Generates text explaining why other suspects were innocent."""
        title = "The Innocents - Unraveling Misdirection"
        body = [f"While the investigation cast suspicion on others, they were ultimately not responsible for Lord Blackwood's murder. Here's why, in light of {actual_murderer_full_name}'s guilt:"]

        for suspect_full_name in innocent_suspects_list:
            suspect_short_name = suspect_full_name.split(" ")[0]
            reasoning = f"\nRegarding {suspect_full_name}:\n"
            secrets_explained = ""
            no_link_to_murder = "Crucially, there was no definitive evidence directly linking them to the physical act of murder or the murder weapon in a way that superseded the evidence against the true killer."

            if suspect_full_name == "Marianne Blackwood":
                secrets_explained = "Marianne indeed had secrets, such as a possible clandestine affair ('Love Letter') and concerns about the will ('Victim's Will'). Her 'Marianne's Travel Trunk' suggested a desire to leave. However, these pointed to unhappiness and a potential escape, not necessarily murderous intent if another's guilt was more strongly evidenced."
            elif suspect_full_name == "Victor Blackwood":
                secrets_explained = "Victor's dire financial situation ('Financial Records (Victor)') and potential conflicts with his father over business and the inheritance ('Victim's Will') certainly provided strong motives. His demeanor could also appear cold or evasive."
            elif suspect_full_name == "Caroline Blackwood":
                secrets_explained = "Caroline's emotional turmoil, reflected in her 'Caroline's Sketchbook', and the 'Anonymous Threat Note' she authored in anger or fear, made her appear volatile. If 'Muddy Footprints' were hers, it indicated a secret meeting or attempt to flee, not necessarily direct involvement in the murder itself."
            
            reasoning += secrets_explained
            reasoning += f"\nWhile these factors made {suspect_short_name} a person of interest, they did not outweigh the evidence pointing to {actual_murderer_full_name}. {no_link_to_murder}"
            body.append(reasoning)
            
        body.append(f"\nEach character was caught in their own web of secrets and anxieties within {MANOR_NAME}, but only one crossed the line into murder.")
        return format_explanation_text(title, body)

    def get_critical_clue_summary_text(clue_name, murderer_full_name, gs, ed_game):
        """
        Generates a concise summary for a specific critical clue, tailored to the murderer.
        Returns a string or None if the clue isn't critical in this context or not sufficiently examined.
        """
        clue_data = ed_game.get(clue_name)
        if not clue_data or clue_name not in gs["discovered_clues"]:
            return None

        current_stage = clue_data["current_stage"]
        # This function needs to know how each clue becomes "critical"
        # This will be highly specific to your game's logic for each clue's final damning stage

        if clue_name == "Bloodstained Cloth" and current_stage == 2: # Assuming Stage 2 is the damning stage
            # Description of Stage 2 for the cloth is already dynamic based on the murderer.
            # We can directly use that.
            return f"- {clue_name} (Fully Analyzed): {clue_data['description_stages'][2]} This directly linked {murderer_full_name.split()[0]} to the crime scene."
        
        elif clue_name == "Antique Dagger" and current_stage == 1: # Assuming Stage 1 is the dynamic trace evidence stage
            # Stage 1 description for the dagger is made dynamic in handle_clue_examination
            if "metallic shaving" in clue_data["description_stages"][1] and gs["murderer"] == "Victor Blackwood":
                return f"- {clue_name} (Forensic Traces): Revealed a metallic shaving matching Victor's workshop materials, proving he handled the weapon with force."
            elif "silk thread" in clue_data["description_stages"][1] and gs["murderer"] == "Marianne Blackwood":
                return f"- {clue_name} (Forensic Traces): Revealed a silk thread matching Marianne's shawl, linking her attire to the weapon during a likely struggle."
            # Add other specific conditions if relevant for Caroline or a generic finding
            
        elif clue_name == "Muddy Footprints" and current_stage == 2: # Assuming Stage 2 is the damning link
            # Stage 2 description is made dynamic in handle_clue_examination
            desc_stage_2 = clue_data["description_stages"][2]
            if "Caroline's" in desc_stage_2 and gs["murderer"] == "Caroline Blackwood":
                 return f"- {clue_name} (Detailed Analysis): Specifically matched to Caroline's boots and linked to her via personal items (e.g., glass bead/art supplies), placing her at a key entry/exit point."
            elif "Victor's" in desc_stage_2 and gs["murderer"] == "Victor Blackwood":
                 return f"- {clue_name} (Detailed Analysis): Specifically matched to Victor's work boots and workshop materials, indicating his presence near the study window."
            elif "Marianne's" in desc_stage_2 and gs["murderer"] == "Marianne Blackwood":
                return f"- {clue_name} (Detailed Analysis): Matched to Marianne's distinct shoes and linked via her perfume, suggesting her presence in the garden and use of the side door."

        elif clue_name == "Anonymous Threat Note" and current_stage == 1 and gs["murderer"] == "Caroline Blackwood": # Stage 1 is specific link
            return f"- {clue_name} (Handwriting Confirmed): Meticulous analysis confirmed Caroline authored the note, revealing clear malice or extreme distress towards her father."

        # Add more critical clues as needed (e.g., Financial Records for Victor's motive, Will, etc.)
        # For motive clues, it's often their existence combined with the context.
        if clue_name == "Financial Records (Victor)" and gs["murderer"] == "Victor Blackwood":
            return f"- {clue_name}: Revealed Victor's dire financial situation and potential embezzlement, providing a strong motive."
        if clue_name == "Love Letter" and gs["murderer"] == "Marianne Blackwood" and "Marianne's Travel Trunk" in gs["discovered_clues"]:
             return f"- {clue_name} & Travel Trunk: Indicated Marianne's unhappiness and plan to flee, potentially after securing an inheritance by illicit means."
        if clue_name == "Victim's Will": # Often a general motive contributor
            # This might need to be more specific based on who the murderer is and how the will affects them
            if gs["murderer"] == "Marianne Blackwood" and "disinherited" in clue_data["relevance_stages"][0].lower(): # Check relevance text
                return f"- {clue_name}: Revealed Lord Blackwood intended to drastically reduce Marianne's inheritance, giving her a motive."
            if gs["murderer"] == "Victor Blackwood" and "conditional" in clue_data["relevance_stages"][0].lower(): # Check relevance text
                 return f"- {clue_name}: Revealed Lord Blackwood was placing strict conditions on Victor's inheritance, potentially tied to his financial misconduct."
            # ... and so on for Caroline if the will directly impacts her freedom/choices.

        return None # Not a critical piece of evidence in its current state for this summary

    # NEW FUNCTION: Generate summary for the murderer
    def generate_murderer_summary_text(murderer_full_name, gs, ed_game):
        title = f"The Culprit Revealed: {murderer_full_name}"
        paras = [f"{murderer_full_name.split()[0]} was indeed the one responsible for the tragic death of Lord Henry Blackwood."]
        
        motive_text = "Motive: "
        key_evidence_texts = ["\nKey Incriminating Evidence:"]
        
        # Define primary motive and key evidence for each suspect
        if murderer_full_name == "Marianne Blackwood":
            motive_text += "Faced with potential disinheritance from Lord Blackwood's new will and desperate to escape an unhappy marriage (possibly with a secret lover, suggested by the 'Love Letter' and her 'Marianne's Travel Trunk'), Marianne's financial security and future were severely threatened."
            critical_clues = ["Bloodstained Cloth", "Antique Dagger", "Victim's Will", "Love Letter", "Marianne's Travel Trunk"]
        elif murderer_full_name == "Victor Blackwood":
            motive_text += "Victor's ambitions and financial stability were on the brink of collapse. Lord Blackwood was about to expose his embezzlement ('Financial Records (Victor)') and the new 'Victim's Will' threatened his expected inheritance and control of the family enterprises."
            critical_clues = ["Bloodstained Cloth", "Antique Dagger", "Financial Records (Victor)", "Victim's Will", "Medical Report"] # Medical report if he got scratched
        elif murderer_full_name == "Caroline Blackwood":
            motive_text += "Caroline felt trapped and controlled by her father, who disapproved of her life choices (perhaps a lover or ambitions) and threatened to curtail her freedom or inheritance ('Victim's Will'). The 'Anonymous Threat Note' she authored showed her deep resentment and desperation."
            critical_clues = ["Bloodstained Cloth", "Anonymous Threat Note", "Muddy Footprints", "Victim's Will", "Caroline's Sketchbook"]
        else:
            motive_text += "The specific motives were complex and tied to their unique circumstances."
            critical_clues = ["Bloodstained Cloth", "Antique Dagger"] # Generic fallback

        paras.append(motive_text)

        found_critical_evidence_count = 0
        for clue_name in critical_clues:
            summary = get_critical_clue_summary_text(clue_name, murderer_full_name, gs, ed_game)
            if summary:
                key_evidence_texts.append(summary)
                found_critical_evidence_count +=1
        
        if found_critical_evidence_count == 0:
            key_evidence_texts.append("While many clues were gathered, the specific combination that cemented their guilt might have been overlooked in the final analysis.")

        paras.extend(key_evidence_texts)
        return format_explanation_text(title, paras) # Uses your existing formatter

    # NEW FUNCTION: Generate summary for an innocent suspect
    def generate_innocent_suspect_summary_text(innocent_full_name, gs, ed_game):
        title = f"Regarding {innocent_full_name}: An Innocent Party"
        paras = []
        
        reason_for_suspicion = f"{innocent_full_name.split()[0]} certainly faced scrutiny, and for understandable reasons. "
        exoneration_details = "However, they were not the murderer. "

        if innocent_full_name == "Marianne Blackwood":
            reason_for_suspicion += "Her secret liaison ('Love Letter'), unhappiness in her marriage, and packed 'Marianne's Travel Trunk' suggested a desire to flee. Concerns about the 'Victim's Will' also cast her in a suspicious light."
            exoneration_details += "While she had secrets and motives, the most definitive evidence (like the specific nature of the 'Bloodstained Cloth' or trace evidence on the 'Antique Dagger') did not point to her when fully analyzed. Her actions were driven by personal desperation, not murder."
        elif innocent_full_name == "Victor Blackwood":
            reason_for_suspicion += "His significant financial troubles ('Financial Records (Victor)') and strained relationship with his father over business and the 'Victim's Will' provided a strong apparent motive. His cool demeanor could also be misconstrued."
            exoneration_details += "Despite his clear motives and financial pressures, there was no irrefutable evidence linking him directly to the physical act of murder at 10:15 PM. Key forensic evidence, when fully developed, implicated another."
        elif innocent_full_name == "Caroline Blackwood":
            reason_for_suspicion += "Her emotional volatility, the 'Anonymous Threat Note' she admitted to writing in anger, and her possible secret presence in the garden ('Muddy Footprints') made her a strong suspect. Her 'Caroline's Sketchbook' also hinted at inner turmoil."
            exoneration_details += "Her actions stemmed from youthful angst, fear, and a desire to protect her secrets (like a clandestine meeting). While she wrote the note, she lacked the follow-through or the direct forensic link to the murder weapon that identified the true killer."
        
        paras.append(reason_for_suspicion)
        paras.append(exoneration_details)
        return format_explanation_text(title, paras)

    # NEW FUNCTION: Generate prompt for Dragon's incorrect accusation dialogue
    def generate_dragon_incorrect_accusation_prompt(accused_suspect_full_name, actual_murderer_full_name, gs, ed_game):
        accused_secret = ""
        if accused_suspect_full_name == "Marianne Blackwood": accused_secret = "her secret affair and plans to leave a difficult marriage."
        elif accused_suspect_full_name == "Victor Blackwood": accused_secret = "his severe financial debts and business disputes with his father."
        elif accused_suspect_full_name == "Caroline Blackwood": accused_secret = "the angry threat note she wrote and her secret meetings."
        accused_persona_info = f"{accused_suspect_full_name} was indeed suspicious due to {accused_secret}."

        murderer_motive = ""
        if actual_murderer_full_name == "Marianne Blackwood": murderer_motive = "fear of disinheritance and desire to escape."
        elif actual_murderer_full_name == "Victor Blackwood": murderer_motive = "preventing exposure of embezzlement and securing his inheritance."
        elif actual_murderer_full_name == "Caroline Blackwood": murderer_motive = "desperation from feeling trapped and controlled, and anger towards her father."

        murderer_key_evidence_str = _get_concise_evidence_summary_for_dragon_prompt(actual_murderer_full_name, gs, ed_game)

        prompt = f"""
You are Inspector Dragon, a wise and analytical detective. You are speaking to Inspector Hart (the player) who has just made an incorrect accusation in the murder of Lord Henry Blackwood.
Inspector Hart wrongly accused: {accused_suspect_full_name}.
The actual murderer was: {actual_murderer_full_name}.

Information about the wrongly accused, {accused_suspect_full_name}:
{accused_persona_info} Their actions and secrets certainly made them appear suspicious.

Information about the true murderer, {actual_murderer_full_name}:
Their motive was primarily {murderer_motive}.
The key evidence that pointed to {actual_murderer_full_name} included: {murderer_key_evidence_str}.

Inspector Hart needs guidance. Your task is to:
1. Acknowledge that {accused_suspect_full_name} was a plausible suspect due to their secrets or circumstances ({accused_secret}).
2. Gently explain that while these factors created suspicion, they did not definitively prove {accused_suspect_full_name} committed the murder. Emphasize that their story, regarding the murder itself, likely remained consistent or that no hard evidence tied them to the *act* of killing.
3. Contrast this with {actual_murderer_full_name}. Explain that the truly conclusive evidence (from {murderer_key_evidence_str}) pointed towards {actual_murderer_full_name}.
4. If any of the key evidence against {actual_murderer_full_name} (as hinted at by {murderer_key_evidence_str}) was discovered but perhaps not fully examined to its most revealing stage by the player, subtly hint that further examination or a different interpretation of that clue was needed. For example: 'Perhaps the full significance of the [clue_name from murderer_key_evidence_str if applicable] wasn't apparent without one final forensic look?' or 'That [clue_name], while examined, held one more secret that pointed directly to {actual_murderer_full_name}.'
5. If key evidence against {actual_murderer_full_name} might have been missed entirely (less likely if it's in murderer_key_evidence_str, but possible if that string is weak), you might say: 'The solution also hinged significantly on the [a key clue that was missed or underdeveloped], which may have been overlooked during your search.'
6. Maintain a respectful, guiding tone. Do not be condescending. Aim to help Inspector Hart learn.
Keep your response to 2-4 concise paragraphs.

Example of tone: 'Ah, Inspector Hart, a complex web indeed. It's understandable why your attention fell upon {accused_suspect_full_name}; their {accused_secret} painted a suspicious picture. However, as compelling as that was, it seems it was a distraction from their actual role in this unfortunate affair, rather than that of the murderer. The definitive threads of evidence, such as {murderer_key_evidence_str}, ultimately weave a path to {actual_murderer_full_name}. Perhaps another look at [mention specific clue if its full potential was missed] would have illuminated this further.'
"""
        return prompt

    # Modify existing explanation text generators to be stubs or remove if fully replaced by the above
    def generate_guilty_explanation_text(murderer_full_name, gs, ed_game): # Now a wrapper
        return generate_murderer_summary_text(murderer_full_name, gs, ed_game)

    def generate_innocence_explanation_text(innocent_suspects_list, actual_murderer_full_name, gs, ed_game): # Now a wrapper
        all_innocent_paras = [f"While {actual_murderer_full_name} was the culprit, the other individuals at Blackwood Manor, though caught in their own dramas, were innocent of the murder itself."] # Overall intro
        
        for suspect_full_name in innocent_suspects_list:
            # We need to extract paragraphs from the formatted text returned by generate_innocent_suspect_summary_text
            # This is a bit clunky; ideally, generate_innocent_suspect_summary_text would return raw paras.
            # For now, let's assume format_explanation_text adds a title then joins paras.
            innocent_summary = generate_innocent_suspect_summary_text(suspect_full_name, gs, ed_game)
            # Crude way to get the body, assuming title is first line and then newlines separate.
            parts = innocent_summary.split('\n\n', 1) # Split title from body
            if len(parts) > 1:
                body_content = parts[1]
                # Further split body_content if it itself contains multiple paragraphs from the original formatting
                individual_paras_from_summary = body_content.strip().split('\n') # Or '\n\n' if that's how format_explanation_text separates
                all_innocent_paras.extend([f"\nRegarding {suspect_full_name}:"] + [p.strip() for p in individual_paras_from_summary if p.strip()])
            else: # Fallback
                all_innocent_paras.append(f"\nRegarding {suspect_full_name}:\n{innocent_summary}")


        return format_explanation_text("The Innocent Parties", all_innocent_paras)

    def generate_dragon_correct_accusation_prompt(murderer_full_name, gs, ed_game):
        motive_text_for_prompt = ""
        if murderer_full_name == "Marianne Blackwood": motive_text_for_prompt = "her fear of disinheritance and desire to escape a difficult marriage, possibly with plans involving a secret lover."
        elif murderer_full_name == "Victor Blackwood": motive_text_for_prompt = "his desperate need to hide his embezzlement scheme from his father and secure his threatened inheritance."
        elif murderer_full_name == "Caroline Blackwood": motive_text_for_prompt = "her feelings of being trapped and controlled, coupled with deep resentment and anger towards her father over his disapproval of her life choices."
        
        key_evidence_str = _get_concise_evidence_summary_for_dragon_prompt(murderer_full_name, gs, ed_game)

        prompt = f"""
You are Inspector Dragon, a highly astute and articulate detective from Scotland Yard. You are addressing Inspector Hart (the player), who has just correctly identified {murderer_full_name} as the murderer of Lord Henry Blackwood.

The murderer's motive was, in essence, {motive_text_for_prompt}.
Inspector Hart's correct conclusion was likely based on piecing together evidence such as {key_evidence_str}.

Your task is to generate a congratulatory speech for Inspector Hart (2-3 paragraphs) that:
1. Warmly and genuinely congratulates them on solving the difficult case.
2. Briefly recaps the core reasoning for {murderer_full_name}'s guilt, perhaps highlighting how the key evidence ({key_evidence_str}) unraveled their deception or confirmed their motive and opportunity.
3. Commends Inspector Hart's specific deductive skills. You can be general, or if some evidence pieces from '{key_evidence_str}' were particularly complex or subtle (like the final stage of the 'Antique Dagger' or 'Bloodstained Cloth'), you might say something like: "Your deduction regarding the [specific complex clue, e.g., 'trace evidence on the dagger'] was particularly insightful, Inspector." or "Your ability to connect [Clue A] with [Suspect's Contradiction B] was pivotal."
4. Reinforces the idea that justice has been served through their efforts.
5. Maintain your characteristic wise, analytical, yet humble and respectful tone. Avoid simply listing facts; weave them into a natural commendation.

Example of tone: "A truly exemplary piece of detective work, Inspector Hart! To unravel such a tangled web of secrets and deceit at Blackwood Manor speaks volumes of your acumen. {murderer_full_name} was indeed driven by [brief motive], and your meticulous focus on {key_evidence_str} was instrumental in bringing their guilt to light. The way you [mention a general skill, e.g., 'pressed for truth despite the evasions'/ 'connected the disparate clues'] was particularly commendable. Justice for Lord Blackwood has indeed been secured."
"""
        return prompt

    def get_decisive_evidence_text_for_murderer(murderer_full_name, gs, ed_game):
        evidence_list = []
        
        # Bloodstained Cloth - Stage 2 is damning
        cloth_data = ed_game.get("Bloodstained Cloth")
        if cloth_data and "Bloodstained Cloth" in gs.get("discovered_clues", set()) and cloth_data.get("current_stage", 0) == 2:
            desc = cloth_data.get("description_stages", ["", "", "not found"])[2] 
            specific_link_text = ""
            if gs.get("murderer") == "Victor Blackwood" and "V.B. monogram" in desc:
                specific_link_text = "Victor Blackwood's 'V.B.' monogram on the cloth, proving his attempt to clean up with his personal handkerchief."
            elif gs.get("murderer") == "Marianne Blackwood" and ("designer scarf" in desc or "silk from a specific designer scarf" in desc):
                specific_link_text = "a piece of Marianne Blackwood's distinctive silk scarf, torn during the incident."
            elif gs.get("murderer") == "Caroline Blackwood" and "oil paint pigments" in desc:
                specific_link_text = "traces of Caroline Blackwood's specific art paint pigments alongside the victim's blood."
            
            if specific_link_text:
                evidence_list.append(f"- The Bloodstained Cloth (Decisively Linked): Analysis revealed {specific_link_text}")

        # Antique Dagger - Stage 1 has dynamic trace evidence
        dagger_data = ed_game.get("Antique Dagger")
        if dagger_data and "Antique Dagger" in gs.get("discovered_clues", set()) and dagger_data.get("current_stage", 0) == 1:
            desc = dagger_data.get("description_stages", ["", "not found"])[1]
            if gs.get("murderer") == "Victor Blackwood" and "metallic shaving" in desc:
                evidence_list.append("- The Antique Dagger (Forensic Trace): A metallic shaving from Victor's workshop found on the hilt proved his forceful handling of the weapon.")
            elif gs.get("murderer") == "Marianne Blackwood" and "silk thread" in desc:
                evidence_list.append("- The Antique Dagger (Forensic Trace): A silk thread from Marianne's shawl caught on the pommel linked her directly to a struggle with the weapon.")

        # Anonymous Threat Note - Stage 1 is damning if Caroline is murderer
        note_data = ed_game.get("Anonymous Threat Note")
        if gs.get("murderer") == "Caroline Blackwood" and \
           note_data and "Anonymous Threat Note" in gs.get("discovered_clues", set()) and note_data.get("current_stage", 0) == 1:
            desc = note_data.get("description_stages", ["", "not found"])[1] 
            if "confirms with over 95%% certainty" in desc or "confirmed Caroline authored the threat" in desc:
                evidence_list.append("- The Anonymous Threat Note (Authorship Confirmed): Handwriting analysis definitively proved Caroline authored this note, revealing her extreme distress or malice towards her father.")

        # Muddy Footprints - Stage 2 is damning
        footprints_data = ed_game.get("Muddy Footprints")
        if footprints_data and "Muddy Footprints" in gs.get("discovered_clues", set()) and footprints_data.get("current_stage", 0) == 2:
            desc = footprints_data.get("description_stages", ["", "", "not found"])[2]
            link_text = ""
            if gs.get("murderer") == "Caroline Blackwood" and ("Caroline's favorite gardening boots" in desc or "colored glass bead" in desc or "art supplies" in desc):
                link_text = "specifically to Caroline's boots/belongings, placing her at a key entry/exit point."
            elif gs.get("murderer") == "Victor Blackwood" and ("Victor uses for antique machinery" in desc or "heavy-duty work boots" in desc or "workshop grease" in desc):
                link_text = "specifically to Victor's work boots/workshop materials, indicating his presence near the study window."
            elif gs.get("murderer") == "Marianne Blackwood" and ("Marianne's expensive walking shoes" in desc or "jasmine-rose perfume" in desc):
                link_text = "to Marianne's distinct shoes and linked via her perfume, suggesting her presence in the garden."
            
            if link_text:
                evidence_list.append(f"- The Muddy Footprints (Detailed Analysis): Linked these prints {link_text}")
        
        # Key Motive Corroboration
        if gs.get("murderer") == "Victor Blackwood" and "Financial Records (Victor)" in gs.get("discovered_clues", set()):
            evidence_list.append("- Financial Records (Victor): These documents exposed Victor's desperate financial state and embezzlement, a powerful motive regarding the 'Victim's Will'.")
        if gs.get("murderer") == "Marianne Blackwood" and "Love Letter" in gs.get("discovered_clues", set()) and "Marianne's Travel Trunk" in gs.get("discovered_clues", set()):
             evidence_list.append("- Love Letter & Travel Trunk: These indicated Marianne's unhappiness, a secret liaison, and a pre-existing plan to flee, aligning with a motive to secure funds from the 'Victim's Will'.")
        
        will_data = ed_game.get("Victim's Will")
        if will_data and "Victim's Will" in gs.get("discovered_clues", set()):
            rel_text = will_data.get("relevance_stages", [""])[0].lower()
            m_name_short = gs.get("murderer", "Unknown").split()[0].lower()
            if m_name_short in rel_text and ("less," in rel_text or "conditional," in rel_text or "disowned" in rel_text or "negatively" in rel_text or "significantly reduced" in rel_text):
                 evidence_list.append(f"- The Victim's Will: Its terms significantly disadvantaged {gs.get('murderer').split()[0]}, directly fueling their motive.")
        
        if not evidence_list: # Fallback if no specific decisive evidence was logged by the conditions above
            evidence_list.append("The specific combination of decisive evidence that cemented guilt was not fully identified in this summary; however, their actions and evasions during the investigation, combined with circumstantial evidence, ultimately confirmed their involvement to the authorities.")
        return evidence_list

    def generate_murderer_detailed_summary(murderer_full_name, gs, ed_game):
        title = f"THE TRUTH OF THE CRIME: {murderer_full_name.upper()} WAS THE CULPRIT"
        paras = [f"{murderer_full_name} was indeed the one responsible for the tragic death of Lord Henry Blackwood."]
        
        motive_paragraph = "Primary Motive: "
        if murderer_full_name == "Marianne Blackwood":
            motive_paragraph += "Marianne was driven by the imminent threat of disinheritance from Lord Blackwood's revised will. Desperate to escape an unhappy marriage and secure her financial future, possibly to start a new life with a secret lover (as hinted by the 'Love Letter' and her packed 'Marianne's Travel Trunk'), she saw murder as her only way out."
        elif murderer_full_name == "Victor Blackwood":
            motive_paragraph += "Victor's motive was twofold: to prevent his father from exposing a significant embezzlement scheme he was running ('Financial Records (Victor)'), which would have meant financial ruin and disgrace, and to secure his own inheritance and control over the Blackwood enterprises which were threatened by the new 'Victim's Will'."
        elif murderer_full_name == "Caroline Blackwood":
            motive_paragraph += "Caroline felt utterly trapped and controlled by Lord Blackwood. His strong disapproval of her personal life (choices of companionship, ambitions) and his threats to send her away or drastically alter her future (foreshadowed by the 'Anonymous Threat Note' she authored) pushed her to a desperate act of violent rebellion."
        else: # Should not happen if murderer_full_name is always one of the three
            motive_paragraph += "Their motives were complex and deeply rooted in the dysfunctional family dynamics and the pressures of the Blackwood estate."
        paras.append(motive_paragraph)

        paras.append("\nKey Incriminating Evidence That Proved Their Guilt:")
        key_evidence_items = get_decisive_evidence_text_for_murderer(murderer_full_name, gs, ed_game)
        paras.extend(key_evidence_items) # Extends the list with items from key_evidence_items
        
        return format_explanation_text(title, paras)

    def generate_all_innocents_summary(innocent_suspects_list, actual_murderer_full_name, gs, ed_game):
        title = "REGARDING THE OTHER SUSPECTS"
        # Master list of paragraphs for all innocents combined for one screen
        all_innocent_content_paras = []

        for innocent_name in innocent_suspects_list:
            innocent_short_name = innocent_name.split()[0]
            # Add a sub-header for each innocent suspect
            all_innocent_content_paras.append(f"\n--- {innocent_name.upper()}: Innocent of the Murder ---")
            
            suspicion_reason = f"Initial Suspicion: {innocent_short_name} drew attention due to "
            exoneration = "Exonerating Factors: However, they were not the murderer. "

            if innocent_name == "Marianne Blackwood":
                suspicion_reason += "her secret affair (suggested by the 'Love Letter'), general unhappiness, a packed 'Marianne's Travel Trunk' indicating escape plans, and her clear financial interest in the 'Victim's Will'."
                exoneration += "While deeply unhappy and planning to leave, the most conclusive forensic evidence (such as the specific nature of the 'Bloodstained Cloth' or trace elements on the 'Antique Dagger' when fully analyzed for the true killer) did not point to her. Her secrets were personal, not homicidal."
            elif innocent_name == "Victor Blackwood":
                suspicion_reason += "his significant financial troubles ('Financial Records (Victor)') and strained relationship with his father over business and the 'Victim's Will', providing a strong apparent motive. His often cold and assertive demeanor could also appear suspicious."
                exoneration += "Despite his clear motives and financial pressures, there was no irrefutable evidence linking him directly to the physical act of murder at 10:15 PM. Key forensic evidence, when fully developed (such as the 'Bloodstained Cloth' or 'Antique Dagger' traces), decisively implicated another."
            elif innocent_name == "Caroline Blackwood":
                suspicion_reason += "the 'Anonymous Threat Note' she authored, her emotional volatility (evident in 'Caroline's Sketchbook'), and her potential unauthorized presence in the garden ('Muddy Footprints') if she was meeting a lover or in distress."
                exoneration += "Her actions, including the note, stemmed from youthful anger, fear, and a desire to protect personal secrets. While she may have been deceitful about her whereabouts, the core forensic evidence directly linking to the murder weapon and the act itself pointed away from her and towards the true culprit."
            
            all_innocent_content_paras.append(suspicion_reason)
            all_innocent_content_paras.append(exoneration)
            
        return format_explanation_text(title, all_innocent_content_paras)

    def _get_concise_evidence_summary_for_dragon_prompt(murderer_full_name, gs, ed_game):
        evidence_points = []
        # Helper to check if a clue stage is "damning" for the given murderer
        def is_stage_damning(clue_name, stage_num, m_name, actual_gs, actual_ed_game):
            clue = actual_ed_game.get(clue_name)
            if not (clue and clue_name in actual_gs.get("discovered_clues", set()) and clue.get("current_stage",0) >= stage_num):
                return False
            
            # Check specific content of the stage description that makes it damning for THIS murderer
            desc_list = clue.get("description_stages", [])
            if len(desc_list) <= stage_num: return False # Stage description doesn't exist
            desc = desc_list[stage_num]

            if clue_name == "Bloodstained Cloth" and stage_num == 2:
                return (m_name == "Victor Blackwood" and "V.B. monogram" in desc) or \
                       (m_name == "Marianne Blackwood" and ("designer scarf" in desc or "silk from a specific designer scarf" in desc)) or \
                       (m_name == "Caroline Blackwood" and "oil paint pigments" in desc)
            elif clue_name == "Antique Dagger" and stage_num == 1:
                return (m_name == "Victor Blackwood" and "metallic shaving" in desc) or \
                       (m_name == "Marianne Blackwood" and "silk thread" in desc)
            elif clue_name == "Muddy Footprints" and stage_num == 2:
                 return (m_name == "Caroline Blackwood" and ("Caroline's favorite gardening boots" in desc or "colored glass bead" in desc or "art supplies" in desc)) or \
                        (m_name == "Victor Blackwood" and ("Victor uses for antique machinery" in desc or "heavy-duty work boots" in desc or "workshop grease" in desc)) or \
                        (m_name == "Marianne Blackwood" and ("Marianne's expensive walking shoes" in desc or "jasmine-rose perfume" in desc))
            elif clue_name == "Anonymous Threat Note" and stage_num == 1 and m_name == "Caroline Blackwood":
                return ("confirms with over 95%% certainty" in desc or "confirmed Caroline authored the threat" in desc)
            # Motive clues are critical by discovery usually if they apply to the murderer
            elif clue_name == "Financial Records (Victor)" and m_name == "Victor Blackwood": return True
            elif clue_name == "Love Letter" and m_name == "Marianne Blackwood": return True # Assuming discovery is enough for Dragon's summary context
            elif clue_name == "Victim's Will": # Contextual for Dragon
                rel_text = clue.get("relevance_stages", [""])[0].lower()
                m_name_short = m_name.split()[0].lower()
                return m_name_short in rel_text and ("less," in rel_text or "conditional," in rel_text or "disowned" in rel_text or "negatively" in rel_text or "significantly reduced" in rel_text)
            return False

        # Check key clues for damning stages
        if is_stage_damning("Bloodstained Cloth", 2, murderer_full_name, gs, ed_game): evidence_points.append("the definitive link from the Bloodstained Cloth")
        if is_stage_damning("Antique Dagger", 1, murderer_full_name, gs, ed_game): evidence_points.append("the specific trace evidence on the Antique Dagger")
        if is_stage_damning("Muddy Footprints", 2, murderer_full_name, gs, ed_game): evidence_points.append("the conclusive analysis of the Muddy Footprints")
        if is_stage_damning("Anonymous Threat Note", 1, murderer_full_name, gs, ed_game): evidence_points.append("the confirmed authorship of the Anonymous Threat Note")
        
        # Add a key motive clue if direct forensic list is short for Dragon's context
        if len(evidence_points) < 2:
            if murderer_full_name == "Victor Blackwood" and is_stage_damning("Financial Records (Victor)", 0, murderer_full_name, gs, ed_game): # Stage 0 means discovered
                evidence_points.append("Victor's critical Financial Records")
            elif murderer_full_name == "Marianne Blackwood" and is_stage_damning("Love Letter", 0, murderer_full_name, gs, ed_game):
                evidence_points.append("Marianne's revealing Love Letter")
            if is_stage_damning("Victim's Will", 0, murderer_full_name, gs, ed_game) and len(evidence_points) < 3 : # Add will if still space
                 evidence_points.append("the telling details in the Victim's Will")


        return ", and ".join(evidence_points) if evidence_points else "a compelling combination of circumstances and testimony"



# --- End of Python Early Block ---

# --- Default Variables (must be outside python early) ---
default game_state = {}
default EVIDENCE_DATA_GAME = {} 
default active_suspect_interaction = None 
default current_location_bg = "bg manor general" 
default last_gemini_error = None 
default pending_question_for_suspect = None
default nvl_buffer = [] 
default temp_accused_suspect = None 
default dragon_focus_topic = None 
default dragon_focus_type = None 
default gemini_response_text_temp = "" 

# --- Image Definitions ---
image bg caroline room:
    "images/bg_caroline_room.png"
    # Assuming 1536x1024 dimensions
    zoom max(1.0 * config.screen_width / 1536, 1.0 * config.screen_height / 1024)
    xalign 0.5
    yalign 0.5

image bg fireplace:
    "images/bg_fireplace.png"
    # Assuming 1536x1024 dimensions
    zoom max(1.0 * config.screen_width / 1536, 1.0 * config.screen_height / 1024)
    xalign 0.5
    yalign 0.5

image bg garden:
    "images/bg_garden.png"
    # Assuming 1536x1024 dimensions
    zoom max(1.0 * config.screen_width / 1536, 1.0 * config.screen_height / 1024)
    xalign 0.5
    yalign 0.5

image bg library:
    "images/bg_library.png"
    # Assuming 1536x1024 dimensions
    zoom max(1.0 * config.screen_width / 1536, 1.0 * config.screen_height / 1024)
    xalign 0.5
    yalign 0.5

image bg manor general: # You already updated this one
    "images/bg_manor_general.png"
    # Assuming 1536x1024 dimensions
    zoom max(1.0 * config.screen_width / 1536, 1.0 * config.screen_height / 1024)
    xalign 0.5
    yalign 0.5

image bg marianne room: # You already updated this one
    "images/bg_marianne_room.png"
    # Assuming 1536x1024 dimensions
    zoom max(1.0 * config.screen_width / 1536, 1.0 * config.screen_height / 1024)
    xalign 0.5
    yalign 0.5

image bg study:
    "images/bg_study.png"
    # Assuming 1536x1024 dimensions
    zoom max(1.0 * config.screen_width / 1536, 1.0 * config.screen_height / 1024)
    xalign 0.5
    yalign 0.5

image bg victor room:
    "images/bg_victor_room.png"
    # Assuming 1536x1024 dimensions
    zoom max(1.0 * config.screen_width / 1536, 1.0 * config.screen_height / 1024)
    xalign 0.5
    yalign 0.5

image dragon neutral = im.Scale("images/dragon_neutral.png", 600, 900)
image caroline neutral = im.Scale("images/caroline_neutral.png", 600, 900)
image marianne neutral = im.Scale("images/marianne_neutral.png", 600, 900)
image victor neutral = im.Scale("images/victor_neutral.png", 600, 900)

image icon dagger = "images/icon_dagger.png"
image icon watch = "images/icon_watch.png"

# --- Character Definitions ---
define p = Character("Inspector Hart", color="#aaddff", ctc=None, ctc_position="nestled")
define nvl_narrator = Character(None, kind=nvl) 
define game_narrator = Character(None, color="#cccccc") 

define marianne_char = Character("Marianne", color="#ffdddd", ctc=None, ctc_position="nestled", image="marianne_neutral")
define victor_char = Character("Victor", color="#ddffdd", ctc=None, ctc_position="nestled", image="victor_neutral")
define caroline_char = Character("Caroline", color="#ffffdd", ctc=None, ctc_position="nestled", image="caroline_neutral")
define dragon_char = Character("Dragon", color="#ddddff", ctc=None, ctc_position="nestled", image="dragon_neutral")

# --- CTC (Click-To-Continue) Animation ---
image ctc_blink:
    "gui/ctc.png" 
    alpha 0.7
    block:
        pause 0.4
        alpha 1.0
        pause 0.4
        repeat

# --- Styles (minimal, assumes gui.rpy handles most) ---
style default: 
    font "DejaVuSans.ttf" 
    size 32 

style input_prompt_text:
    color "#cccccc"
    size 28
    yoffset -5 

style input_text: 
    color "#ffffff"
    size 30

style input_window: 
    background None 
    xalign 0.5
    yalign 0.98 
    padding (15, 50)


# --- Screens ---
screen game_input(prompt_display_text):
    default user_input_text = ""
    zorder 110 # This zorder might need adjustment if it's meant to be the main dialogue interface

    # Apply the style used by your game's dialogue windows.
    # Common names are "say_window" or "window". Check your gui.rpy if unsure.
    window style "say_window":  # <--- TRY THIS
        # The "say_window" style usually controls its own position (yalign) and padding.
        # You might need to remove or adjust yalign and padding from style "input_window"
        # or from here if they conflict with how "say_window" is designed.

        # The content structure might need to mimic a say screen for consistent look & feel
        has vbox:
            # Adjust xalign and spacing to match your dialogue window's content
            xalign 0.5  # Or perhaps 0.0 if text starts from left in dialogue
            yalign 0.2
            spacing 10

            # Optional: You could add a speaker label if desired, like the say screen does
            # text "Inspector Hart asks:" style "say_label" # (If "say_label" is your speaker style)

            text prompt_display_text style "input_prompt_text" # Your existing prompt

            input value user_input_text length 150 style "input_text" default "" # Your input field
                # xsize 600 # If you want to limit the visual width of the input field

            hbox: # Your buttons
                xalign 0.5 # Or adjust as needed
                yalign 0.98 
                spacing 10
                # You might want to use styles for buttons that match dialogue window (e.g., quick_button)
                textbutton "Ask" action Return(user_input_text) style "game_menu_button"
                textbutton "Cancel" action Return(None) style "game_menu_button"


screen nvl_display():
    tag menu 
    window:
        style "nvl_window" 
        viewport: 
            scrollbars "vertical"
            mousewheel True
            draggable True 
            vbox:
                spacing 10 
                for character_tag, message_text in nvl_buffer: # Assumes nvl_buffer is in renpy.store or global
                    if character_tag == "nvl_narrator": 
                        text message_text
                    else: 
                        text message_text
    # SIMPLIFIED ACTION:
    textbutton "Continue" action Return() xalign 0.5 ypos 0.90 style "game_menu_button"

style nvl_window is frame: 
    background Frame("gui/frame.png", 15, 15) 
    xfill True
    yfill True
    padding (25, 25)

# Default say screen is used for character dialogue.
# If customization is needed, it's usually in screens.rpy.

screen clues_display_screen():
    tag menu
    modal True

    frame:
        style "game_menu_frame"
        xalign 0.5
        yalign 0.43
        xsize 1200
        ysize 857

        vbox:
            spacing 15
            xfill True

            text "Discovered Clues":
                style "game_menu_label"
                xalign 0.5

            viewport:
                id "clues_viewport"
                draggable True
                mousewheel True
                scrollbars "vertical"
                xsize 1160
                ysize 850 # Corrected from 850 to fit within frame with padding

                vbox:
                    spacing 15
                    xfill True
                    if not game_state["discovered_clues"]:
                        text "No specific physical clues discovered yet." xalign 0.5 yalign 0.5
                    else:
                        $ sorted_clues_list = sorted(list(game_state["discovered_clues"]))
                        for clue_name_iter in sorted_clues_list:
                            $ clue_detail_iter = get_clue_data(clue_name_iter) # Uses your existing helper
                            if clue_detail_iter:
                                $ desc_iter = get_current_clue_description(clue_name_iter) # Uses your existing helper
                                $ rel_iter = get_current_clue_relevance(clue_name_iter) # Uses your existing helper
                                # MODIFIED LINE BELOW: Removed (Stage ...)
                                text f"{clue_name_iter.upper()}" style "clue_title_text"
                                text f"  Description: {desc_iter}" style "clue_desc_text"
                                text f"  Relevance: {rel_iter}" style "clue_relevance_text"
                                null height 10 # Adds a small space between clue entries
            null height 10 # Spacer before the close button
            textbutton "Close" action Return() xalign 0.5 style "game_menu_button"



style game_menu_frame:
    background Frame("gui/frame.png", 20, 20) 
    padding (20, 20)

style game_menu_label:
    font "DejaVuSans-Bold.ttf" 
    size 36
    color "#FFFFFF"
    text_align 0.5 
    padding (0, 10, 0, 20) 

style clue_title_text:
    font "DejaVuSans-Bold.ttf"
    size 28
    color "#FFFFFF"

style clue_desc_text:
    size 26
    color "#E0E0E0"
    left_margin 20 

style clue_relevance_text:
    size 26
    color "#C0C0C0"
    italic True
    left_margin 20 

style game_menu_button is button: 
    font "DejaVuSans.ttf"
    size 24
    color "#FFFFFF"
    hover_color "#FFFF00" 
    text_align 0.5
    background None
    hover_background None
    xsize 250 # Increased button width for better text fit
    ysize 50  
    padding (10,5)

screen hud_screen():
    zorder 100 
    fixed: 
        vbox:
            xalign 0.01 yalign 0.01 
            spacing 5
            text f"Turn: {game_state['current_turn']}" color "#FFF" outlines [(1, "#000", 0, 0)] 
            if active_suspect_interaction:
                text f"Talking to: {active_suspect_interaction.split()[0]}" color "#FFF" outlines [(1, "#000", 0, 0)]
            else:
                $ loc_disp_name = get_location_display_name(str(current_location_bg)) 
                text f"Location: {loc_disp_name}" color "#FFF" outlines [(1, "#000", 0, 0)]

# --- Game Flow Labels ---
label start:
    python:
        initialize_game_data() 
        if not GEMINI_API_KEY or "YOUR_API_KEY" in GEMINI_API_KEY or len(GEMINI_API_KEY) < 30:
            renpy.store.last_gemini_error = "CRITICAL ERROR: A valid Gemini API key is required."
    
    if last_gemini_error:
        game_narrator "[last_gemini_error]" 
        return 

    scene bg manor general # Set your default starting background
    show screen hud_screen 

    jump show_intro_page_sequence # Start the new intro sequence

label show_intro_page_sequence:
    python:
        gs = renpy.store.game_state
        intro_is_still_active_for_this_page_display = False 

        if gs.get("intro_active", True): 
            current_idx = gs.get("intro_current_page_index", 0)
            renpy.store.nvl_buffer.clear()

            if current_idx < len(all_intro_pages):
                intro_is_still_active_for_this_page_display = True                 
                page_content = all_intro_pages[current_idx]
                for line_to_add in page_content.strip().split('\\n'): 
                    if line_to_add.strip(): 
                        add_to_nvl_display_buffer(line_to_add.strip())
                    else: 
                        add_to_nvl_display_buffer(" ") 
            else: 
                gs["intro_active"] = False 
                intro_is_still_active_for_this_page_display = False 
                if not gs.get("initial_clues_discovered_after_intro", False):
                    discover_clue("Broken Pocket Watch", announce=False)
                    discover_clue("Antique Dagger", announce=False)
                    gs["initial_clues_discovered_after_intro"] = True
        else: 
            intro_is_still_active_for_this_page_display = False
            renpy.store.nvl_buffer.clear() 
            
    if intro_is_still_active_for_this_page_display:
        hide screen hud_screen 
        call screen nvl_display 
        # Player clicked "Continue" on nvl_display, now increment page index:
        $ game_state["intro_current_page_index"] = game_state.get("intro_current_page_index", 0) + 1 # MODIFIED/ADDED LINE
        jump show_intro_page_sequence 
    else:
        show screen hud_screen 
        jump main_hub_menu

label main_hub_menu:
    $ game_state["current_turn"] += 1
    $ active_suspect_interaction = None # Clear active suspect when returning to hub
    
    scene expression current_location_bg # Show current location
    hide marianne neutral
    hide victor neutral
    hide caroline neutral
    hide dragon neutral
    show screen hud_screen

    # Auto-discover testimony clues
    python:
        gs = renpy.store.game_state
        if "Butler's Log" not in gs["discovered_clues"] and gs["current_turn"] > 5: # Reduced turn count
            if discover_clue("Butler's Log", announce=True):
                 renpy.say(dragon_char, "Inspector Hart, I've spoken with James, the butler. His log notes some interesting movements last night. It's now in your evidence.")
        if "Medical Report" not in gs["discovered_clues"] and gs["current_turn"] > 3:
            if discover_clue("Medical Report", announce=True):
                 renpy.say(dragon_char, "The preliminary medical report is in, Inspector. It confirms some key details. Added to your notes.")

    menu:
        "What is your next action, Inspector?"

        "Talk to a Suspect":
            jump talk_to_suspect_menu
        "Search a Location":
            jump search_location_menu
        "Review Discovered Clues":
            call screen clues_display_screen
            jump main_hub_menu
        "Examine a Clue More Closely":
            jump examine_clue_menu
        "Consult Inspector Dragon":
            jump consult_dragon_menu
        "Accuse a Suspect":
            jump accuse_suspect_menu
        "Quit Investigation":
            jump game_over_quit

label talk_to_suspect_menu:
    window hide

    # Pass the caption as a keyword argument 'menu_caption'
    # The menu block now only contains the choices themselves.
    menu (screen="talk_menu_layout", menu_caption="Who will you question?"):
        "Marianne Blackwood":
            $ active_suspect_interaction = "Marianne Blackwood"
            jump suspect_interaction_hub
        "Victor Blackwood":
            $ active_suspect_interaction = "Victor Blackwood"
            jump suspect_interaction_hub
        "Caroline Blackwood":
            $ active_suspect_interaction = "Caroline Blackwood"
            jump suspect_interaction_hub
        "Back to Main Actions":
            jump main_hub_menu

label suspect_interaction_hub:
    window hide # Hide any previous dialogue window FIRST

    python:
        # Prepare the caption string
        _caption = f"Questioning {active_suspect_interaction.split()[0]}"
        
        # Prepare the list of choices: [("Button Text", Action), ...]
        _choices = [
            ("Ask a new question", Jump("ask_loop_entry_point")),
            ("Show a Clue", Jump("show_clue_to_suspect_menu")),
            ("View Conversation History", Jump("show_conversation_history")), # << NEW LINE
           ("Stop Questioning", Jump("action_finish_questioning_return_to_lobby")) 
        ]
        
        # Set character sprite and background
        if "Marianne" in active_suspect_interaction:
            renpy.store.current_location_bg = "bg marianne room"
        elif "Victor" in active_suspect_interaction:
            renpy.store.current_location_bg = "bg victor room"
        elif "Caroline" in active_suspect_interaction:
            renpy.store.current_location_bg = "bg caroline room"

    scene expression current_location_bg
    if "Marianne" in active_suspect_interaction:
        show marianne neutral at center
    elif "Victor" in active_suspect_interaction:
        show victor neutral at center
    elif "Caroline" in active_suspect_interaction:
        show caroline neutral at center
    show screen hud_screen

    # Directly call your custom screen
    call screen ingame_interaction_menu_layout(choices_list=_choices, caption_text=_caption)
    
    # Since the actions in the choices are Jumps, control typically won't return here.
    # Adding a fallback just in case.
    jump main_hub_menu

label action_finish_questioning_return_to_lobby:
    # Clear the active suspect
    $ active_suspect_interaction = None

    # Optional: Hide the suspect's sprite immediately if desired
    # (though the scene change in main_hub_menu will also handle this)
    hide marianne neutral
    hide victor neutral
    hide caroline neutral
    
    # Optional: Add a narrator message for the transition
    # Ensure the dialogue window is shown for the narrator
    window show 
    game_narrator "You conclude your questioning for now and step back into the main hall."
    window auto # Allow the window to behave as normal afterwards (e.g., auto-hide)

    # Set the current location background to your main lobby
    $ current_location_bg = "bg manor general" # <<< IMPORTANT: Use your actual lobby background tag here

    # Now jump to the main hub, which will display the lobby
    jump main_hub_menu


label ask_loop_entry_point:
    # This is where the actual continuous questioning happens
    $ player_question_text = renpy.call_screen("game_input", prompt_display_text=f"Ask {active_suspect_interaction.split()[0]} a question:")

    python:
        _proceed_with_question = False
        _question_to_ask_final = None # Temporary variable for the processed question

        if isinstance(player_question_text, str):
            _stripped_text = player_question_text.strip()
            if _stripped_text: # If not empty after stripping
                _question_to_ask_final = _stripped_text
                _proceed_with_question = True
                renpy.store.pending_question_for_suspect = _question_to_ask_final # Set for p "" and LLM
            else:
                renpy.log(f"DEBUG_INPUT: Received empty or whitespace string: '{player_question_text}'")
        elif player_question_text is None:
            renpy.log("DEBUG_INPUT: Received None (Cancel pressed).")
        else:
            # This case handles unexpected types, like booleans that caused the error
            renpy.log(f"DEBUG_INPUT: Received unexpected type for player_question_text: {type(player_question_text)}, value: {player_question_text!r}. Assuming Cancel.")
        
        renpy.store.temp_proceed_flag = _proceed_with_question # Store flag for Ren'Py if condition

    if temp_proceed_flag: # Check the flag set in the python block
        # pending_question_for_suspect is now reliably set if temp_proceed_flag is True
        # p "[pending_question_for_suspect]" # <<--- COMMENTED OUT OR DELETED
        call _common_process_suspect_llm_interaction from _call__common_process_suspect_llm_interaction
        jump ask_loop_entry_point
    else:
        jump suspect_interaction_hub
            
label process_suspect_question:
    # This label processes the question obtained from the input screen
    if active_suspect_interaction and pending_question_for_suspect:
        $ current_player_question = pending_question_for_suspect
        $ pending_question_for_suspect = None 

        # p "[current_player_question]"
        python hide: 
            gs_local = renpy.store.game_state
            ed_game_local = renpy.store.EVIDENCE_DATA_GAME
            active_suspect_local = renpy.store.active_suspect_interaction
            is_guilty_for_this_interaction = (active_suspect_local == gs_local["murderer"])

            if active_suspect_local == "Victor Blackwood" and \
               "Victor_alibi_vs_Marianne_testimony" in gs_local["key_contradictions"] and \
               gs_local["key_contradictions"]["Victor_alibi_vs_Marianne_testimony"] == "established":
                gs_local["suspect_pressure_notes"]["Victor Blackwood"] = "Your alibi about being in your room until after 10:30 PM has been directly contradicted by Marianne, who claims she saw you near the study much earlier, around 10:20 PM. You are under significant pressure on this point."

            persona_prompt_text = build_suspect_persona_prompt(
                active_suspect_local, is_guilty_for_this_interaction,
                VICTIM, MANOR_NAME, 
                ed_game_local, gs_local["discovered_clues"], gs_local
            )
            
            conversation_history_for_prompt = "\n--- Conversation History So Far ---\n"
            current_conv_log = gs_local["suspect_conversations"][active_suspect_local]
            if not current_conv_log:
                conversation_history_for_prompt += "No prior conversation with this suspect in this session.\n"
            else:
                for entry in current_conv_log[-6:]: 
                    role_label_hist = "Inspector Hart" if entry["role"] == "user" else active_suspect_local.split()[0]
                    conversation_history_for_prompt += f"{role_label_hist}: {entry['parts'][0]['text']}\n"
            
            current_question_for_prompt = f"\n--- Current Question from Inspector Hart ---\nInspector Hart: {current_player_question}\n{active_suspect_local.split()[0]}:"
            final_prompt_for_gemini = persona_prompt_text + conversation_history_for_prompt + current_question_for_prompt
            
            gemini_temp = 0.75
            if is_guilty_for_this_interaction and active_suspect_local in gs_local["suspect_pressure_notes"]:
                gemini_temp = 0.80 
            
            renpy.store.gemini_response_text_temp = call_gemini_api(final_prompt_for_gemini, active_suspect_local, temperature=gemini_temp)

            gs_local["suspect_conversations"][active_suspect_local].append({"role": "user", "parts": [{"text": current_player_question}]})
            gs_local["suspect_conversations"][active_suspect_local].append({"role": "assistant", "parts": [{"text": renpy.store.gemini_response_text_temp}]})

            if active_suspect_local == "Marianne Blackwood" and "victor" in current_player_question.lower() and \
               ("10:20" in renpy.store.gemini_response_text_temp.lower() or "five minutes" in renpy.store.gemini_response_text_temp.lower()): 
                if "Broken Pocket Watch" in gs_local["discovered_clues"]: 
                    if gs_local["key_contradictions"].get("Victor_alibi_vs_Marianne_testimony") != "established":
                        renpy.log("[GAME NOTE: Marianne's testimony now strongly contradicts Victor's alibi for ~10:15-10:20PM.]")
                        gs_local["key_contradictions"]["Victor_alibi_vs_Marianne_testimony"] = "established"
                        gs_local["progress_since_last_dragon"] = True
            
            if active_suspect_local in gs_local["suspect_pressure_notes"]:
                del gs_local["suspect_pressure_notes"][active_suspect_local]

        if last_gemini_error: 
            game_narrator "[last_gemini_error]" 
            $ last_gemini_error = None 
        else: 
            if "Marianne" in active_suspect_interaction: 
                marianne_char "[gemini_response_text_temp]"
            elif "Victor" in active_suspect_interaction: 
                victor_char "[gemini_response_text_temp]"
            elif "Caroline" in active_suspect_interaction: 
                caroline_char "[gemini_response_text_temp]"
            else: 
                game_narrator "[gemini_response_text_temp]"
    return # Return to the calling menu (suspect_interaction_hub)

label _common_process_suspect_llm_interaction:
    # Assumes pending_question_for_suspect is set, and the player's utterance was already displayed
    if active_suspect_interaction and pending_question_for_suspect:
        $ current_player_utterance_for_llm = pending_question_for_suspect

        python hide:
            gs_local = renpy.store.game_state
            ed_game_local = renpy.store.EVIDENCE_DATA_GAME
            active_suspect_local = renpy.store.active_suspect_interaction # Should be valid here
            is_guilty_for_this_interaction = (active_suspect_local == gs_local["murderer"])

            # Victor pressure note logic
            if active_suspect_local == "Victor Blackwood" and \
               "Victor_alibi_vs_Marianne_testimony" in gs_local.get("key_contradictions", {}) and \
               gs_local["key_contradictions"]["Victor_alibi_vs_Marianne_testimony"] == "established":
                gs_local.setdefault("suspect_pressure_notes", {})["Victor Blackwood"] = "Your alibi about being in your room until after 10:30 PM has been directly contradicted by Marianne, who claims she saw you near the study much earlier, around 10:20 PM. You are under significant pressure on this point."

            persona_prompt_text = build_suspect_persona_prompt(
                active_suspect_local, is_guilty_for_this_interaction,
                VICTIM, MANOR_NAME,
                ed_game_local, gs_local["discovered_clues"], gs_local
            )

            conversation_history_for_prompt = "\n--- Conversation History So Far ---\n"
            # Ensure suspect_conversations key exists and is a list
            current_conv_log = gs_local.setdefault("suspect_conversations", {}).get(active_suspect_local, [])
            if not current_conv_log:
                conversation_history_for_prompt += "No prior conversation with this suspect in this session.\n"
            else:
                for entry in current_conv_log[-6:]: # Get last 3 exchanges (6 entries)
                    role_label_hist = "Inspector Hart" if entry["role"] == "user" else active_suspect_local.split()[0]
                    conversation_history_for_prompt += f"{role_label_hist}: {entry['parts'][0]['text']}\n"

            current_question_for_prompt = f"\n--- Current Input from Inspector Hart ---\nInspector Hart: {current_player_utterance_for_llm}\n{active_suspect_local.split()[0]}:" # Suspect's turn to respond
            final_prompt_for_gemini = persona_prompt_text + conversation_history_for_prompt + current_question_for_prompt

            gemini_temp = 0.75
            if is_guilty_for_this_interaction and active_suspect_local in gs_local.get("suspect_pressure_notes", {}):
                gemini_temp = 0.80

            renpy.store.gemini_response_text_temp = call_gemini_api(final_prompt_for_gemini, active_suspect_local, temperature=gemini_temp)

            # Log player's utterance and AI's response
            gs_local.setdefault("suspect_conversations", {}).setdefault(active_suspect_local, []).append({"role": "user", "parts": [{"text": current_player_utterance_for_llm}]})
            gs_local["suspect_conversations"][active_suspect_local].append({"role": "assistant", "parts": [{"text": renpy.store.gemini_response_text_temp}]})

            # Marianne/Victor contradiction logic, using current_player_utterance_for_llm
            if active_suspect_local == "Marianne Blackwood" and "victor" in current_player_utterance_for_llm.lower() and \
               ("10:20" in renpy.store.gemini_response_text_temp.lower() or "five minutes" in renpy.store.gemini_response_text_temp.lower()):
                if "Broken Pocket Watch" in gs_local["discovered_clues"]:
                    if gs_local.setdefault("key_contradictions", {}).get("Victor_alibi_vs_Marianne_testimony") != "established":
                        renpy.log("[GAME NOTE: Marianne's testimony now strongly contradicts Victor's alibi for ~10:15-10:20PM.]")
                        gs_local["key_contradictions"]["Victor_alibi_vs_Marianne_testimony"] = "established"
                        gs_local["progress_since_last_dragon"] = True

            if active_suspect_local in gs_local.get("suspect_pressure_notes", {}):
                del gs_local["suspect_pressure_notes"][active_suspect_local] # Clear pressure note after use

            renpy.store.pending_question_for_suspect = None # Clear after processing

        if last_gemini_error:
            game_narrator "[last_gemini_error]"
            $ last_gemini_error = None
        else:
            if "Marianne" in active_suspect_interaction:
                marianne_char "[gemini_response_text_temp]"
            elif "Victor" in active_suspect_interaction:
                victor_char "[gemini_response_text_temp]"
            elif "Caroline" in active_suspect_interaction:
                caroline_char "[gemini_response_text_temp]"
            else:
                game_narrator "[gemini_response_text_temp]" # Fallback
    return # Returns to the caller (either ask_loop_entry_point or after clue presentation)

label show_clue_to_suspect_menu:
    if not game_state["discovered_clues"]:
        game_narrator "You have no clues to show yet."
        jump suspect_interaction_hub # Go back to the suspect interaction options

    python:
        clue_choices_for_grid = []
        # For this menu, the display name and the action value are the same (the clue's name)
        # No need for "(Examine further)" here.
        for clue_name in sorted(list(game_state["discovered_clues"])):
            clue_choices_for_grid.append( (clue_name, clue_name) )
        
        # Get the short name of the active suspect for the screen's caption
        _active_suspect_short_name = "them" # Fallback
        if active_suspect_interaction:
            _active_suspect_short_name = active_suspect_interaction.split()[0]

    # Call the new grid screen
    $ result = renpy.call_screen("show_clue_to_suspect_grid_screen", 
                                 clue_choices_list=clue_choices_for_grid, 
                                 current_suspect_name=_active_suspect_short_name)

    if result == "cancel_show_clue" or not result: # If "Cancel" was clicked or screen was escaped
        jump suspect_interaction_hub # Go back to suspect interaction options
    else:
        # 'result' is now the chosen clue_name
        $ clue_to_discuss_name = result
        # Prepare the text for the LLM, including the clue's current description
        $ pending_question_for_suspect = f"I'd like your thoughts on this item: '{clue_to_discuss_name}'. It's described as: \"{get_current_clue_description(clue_to_discuss_name)}\". What can you tell me about it, or its relevance?"
        $ game_state["progress_since_last_dragon"] = True # Showing a clue is progress
        
        # The player's "statement/question" about showing the clue will be part of pending_question_for_suspect
        # So, we don't need a separate `p "[...` here. The LLM interaction will handle it.
        call _common_process_suspect_llm_interaction from _call__common_process_suspect_llm_interaction_1 # This label processes the question and gets LLM response
        
        # After showing a clue and getting a response, return to the point where player can ask another question or choose another action
        jump ask_loop_entry_point # Or jump suspect_interaction_hub if you prefer that flow

label search_location_menu:
    window hide 
    $ chosen_location_key = renpy.call_screen("search_location_grid_screen")

    if chosen_location_key == "back":
        jump main_hub_menu
    elif chosen_location_key:
        # --- New Search Flow ---
        python hide:
            # Determine the display name and target background for the chosen location
            # This logic is similar to what was partially in perform_search_action and get_location_display_name
            # You might want to centralize this bg_map if it's used in many places.
            _bg_map = {
                "study": "bg study", 
                "marianne_room": "bg marianne room", 
                "victor_room": "bg victor room",
                "caroline_room": "bg caroline room", 
                "garden": "bg garden", 
                "library": "bg library",
                "fireplace": "bg fireplace", # Assuming fireplace is a distinct searchable bg
                "desk": "bg study"  # Desk is in the study
            }
            _target_bg = _bg_map.get(chosen_location_key, "bg manor general") # Fallback if key not in map
            _location_display_name = chosen_location_key.replace("_", " ").title()
            
            # Store for use in Ren'Py script parts
            store.temp_target_bg_for_search = _target_bg
            store.temp_location_display_name_for_search = _location_display_name
        
        # 1. Announce travel and show the room
        scene expression temp_target_bg_for_search # Change to the location's background
        $ current_location_bg = temp_target_bg_for_search # Update HUD for current scene
        show screen hud_screen # Refresh HUD
        game_narrator "You make your way to the [temp_location_display_name_for_search]."
        game_narrator "You begin to examine the area closely..."

        # 2. Perform the search (discover_clue within it will announce found clues)
        # The "nothing found" message will also come from perform_search_action if applicable.
        $ perform_search_action(chosen_location_key) 

        # 3. Pause briefly so player can read clue announcements
        $ renpy.pause(0.2, hard=True) # 'hard=True' ensures pause even in skip mode

        # 4. Announce return to the lobby
        game_narrator "Having thoroughly searched the [temp_location_display_name_for_search], you decide to head back to the main hall."
        
        # 5. Set current location to the lobby for the main_hub_menu
        $ current_location_bg = "bg manor general" # <<< ENSURE THIS IS YOUR LOBBY/MAIN HUB BACKGROUND TAG
        
        jump main_hub_menu
    else:
        # Should not happen if screen returns "back" or a key, but good to have a fallback
        jump main_hub_menu

label examine_clue_menu:
    window hide

    python:
        clues_for_screen = []  # This will be a list of tuples: (display_string, actual_clue_name)
        if game_state.get("discovered_clues"):
            sorted_clues_list = sorted(list(game_state["discovered_clues"]))
            for clue_name_iter in sorted_clues_list:
                clue_data = renpy.store.EVIDENCE_DATA_GAME.get(clue_name_iter) # Use game's copy
                if clue_data:
                    display_string = f"{clue_name_iter}"  # Start with the basic clue name
                    
                    can_examine_further_by_simple_command = False
                    # Check if the clue is not already at its maximum defined stage
                    if clue_data['current_stage'] < len(clue_data['description_stages']) - 1:
                        # Determine the condition for advancing to the *next* stage
                        # The index for the next stage's condition is current_stage + 1
                        idx_for_next_stage_condition = clue_data['current_stage'] + 1
                        
                        # Ensure this index is valid for the reveal_conditions_for_next_stage list
                        if idx_for_next_stage_condition < len(clue_data["reveal_conditions_for_next_stage"]):
                            next_stage_reveal_condition = clue_data["reveal_conditions_for_next_stage"][idx_for_next_stage_condition]
                            
                            if next_stage_reveal_condition is None:
                                # None condition means it advances automatically on examination (if no other hidden logic prevents it)
                                can_examine_further_by_simple_command = True
                            elif isinstance(next_stage_reveal_condition, dict):
                                # Check for the specific "examine" command condition
                                if next_stage_reveal_condition.get("command") == "examine" and \
                                   next_stage_reveal_condition.get("clue") == clue_name_iter:
                                    can_examine_further_by_simple_command = True
                    
                    if can_examine_further_by_simple_command:
                        display_string += " (Examine further)"
                        
                    clues_for_screen.append( (display_string, clue_name_iter) ) # Add tuple to list
        
    # Call your grid screen, passing the prepared list
    $ result = renpy.call_screen("examine_clue_grid_screen", clue_choices_list=clues_for_screen)

    # Process the result from the screen
    if result == "back":
        jump main_hub_menu
    elif result: # If a clue_name (not "back") was returned
        $ handle_clue_examination(result) # Call your existing examination handler
        # After handling examination, you might want to refresh the examine_clue_menu
        # or go back to the main hub. Let's go to main_hub and player can re-enter if needed.
        jump main_hub_menu
    else:
        # Fallback, e.g., if Escape is pressed and screen returns None
        jump main_hub_menu
            
label consult_dragon_menu:
    window hide # Hide any previous dialogue window FIRST

    python:
        _dragon_caption = "Consulting Inspector Dragon. What would you like to do?"
        _dragon_choices = [
            ("Ask for general thoughts.", Jump("ask_dragon_character_general")),
            ("Ask about a specific Clue or Suspect.", Jump("dragon_focus_choice_menu")),
            ("View Conversation History", Jump("show_dragon_conversation_history")), # << ADD THIS NEW LINE
            ("Nevermind.", [Hide("dragon neutral"), Jump("main_hub_menu")])
        ]

    # Ensure Dragon's sprite is shown (it might be hidden if player chose "Nevermind" previously)
    show dragon neutral at center
    # 'with dissolve' is optional if you want an effect when he reappears or menu shows
    # with dissolve

    # Directly call your custom screen for the menu
    call screen ingame_interaction_menu_layout(choices_list=_dragon_choices, caption_text=_dragon_caption)
    
    # Fallback, though the menu choices should navigate away
    # If control returns here unexpectedly, go back to the main hub.
    jump main_hub_menu

label dragon_focus_choice_menu: # Indent level 0
    menu: 
        "Focus Dragons thoughts on..." # Indent level 1 (e.g., 4 spaces)
        "A Discovered Clue": # Indent level 2 (e.g., 8 spaces)
            jump dragon_focus_clue_menu # Indent level 3 (e.g., 12 spaces)
        "A Suspect": # Indent level 2
            jump dragon_focus_suspect_menu # Indent level 3
        "Back to Dragon Options": # Indent level 2
            jump consult_dragon_menu # Indent level 3

label dragon_focus_clue_menu:
    if not game_state["discovered_clues"]:
        game_narrator "No clues discovered yet to discuss with Dragon."
        jump consult_dragon_menu

    $ clue_focus_choices = [(clue_name, clue_name) for clue_name in sorted(list(game_state["discovered_clues"]))]
    $ clue_focus_choices.append(("Cancel", "cancel"))

    $ result = renpy.display_menu(clue_focus_choices)

    if result == "cancel":
        jump consult_dragon_menu
    else:
        $ dragon_focus_topic = result
        $ dragon_focus_type = "clue"
        jump ask_dragon_character_focused

label dragon_focus_suspect_menu:
    $ suspect_focus_choices = [(full_name, full_name) for short_name, full_name in SUSPECTS_FULL_NAMES.items()]
    $ suspect_focus_choices.append(("Cancel", "cancel"))

    $ result = renpy.display_menu(suspect_focus_choices)

    if result == "cancel":
        jump consult_dragon_menu
    else:
        $ dragon_focus_topic = result
        $ dragon_focus_type = "suspect"
        jump ask_dragon_character_focused

label accuse_suspect_menu:
    $ accuse_choices = [(full_name, full_name) for short_name, full_name in SUSPECTS_FULL_NAMES.items()]
    $ accuse_choices.append(("Cancel Accusation", "cancel"))

    $ result = renpy.display_menu(accuse_choices)

    if result == "cancel":
        jump main_hub_menu
    else:
        $ temp_accused_suspect = result
        jump handle_accusation_flow


label game_over_quit:
    python:
        renpy.store.nvl_buffer.clear()
        add_to_nvl_display_buffer(f"You leave {MANOR_NAME}, the mystery weighing heavily...")
        add_to_nvl_display_buffer("\nThank you for playing Murder at Blackwood Manor!")
    call screen nvl_display
    return 

label game_over_win_sequence:
    call screen nvl_display 
    python:
        renpy.store.nvl_buffer.clear()
        add_to_nvl_display_buffer("\nCongratulations, Inspector! Case closed.")
        add_to_nvl_display_buffer("\nThank you for playing Murder at Blackwood Manor!")
    call screen nvl_display
    return

label game_over_lose_sequence:
    call screen nvl_display 
    python:
        renpy.store.nvl_buffer.clear()
        add_to_nvl_display_buffer("\nThe case remains unsolved, a shadow over Blackwood Manor.")
        add_to_nvl_display_buffer("\nThank you for playing Murder at Blackwood Manor!")
    call screen nvl_display
    return

label ask_dragon_character_general:
    python:
        gs = renpy.store.game_state
        # ed_game is accessed by get_game_state_summary_for_dragon via renpy.store

        current_focus_topic = None
        current_focus_type = None

        hint_level = 0
        if not gs.get("progress_since_last_dragon", True):
            gs["dragon_consultations_count"] = gs.get("dragon_consultations_count", 0) + 1
            hint_level = min(3, gs["dragon_consultations_count"] // 2) 
        else:
            gs["dragon_consultations_count"] = 0 
        
        gs["progress_since_last_dragon"] = False 

        game_summary = get_game_state_summary_for_dragon(
            gs,
            focused_on=current_focus_topic, 
            focus_type=current_focus_type 
        )
        
        dragon_prompt_text = build_dragon_persona_prompt(
            game_summary,
            focus_topic=current_focus_topic,
            focus_type=current_focus_type,
            hint_level=hint_level
        )

        # --- START: Code to log interaction (already in your version) ---
        player_dragon_prompt_text = "I'd appreciate your general thoughts on the case, Inspector Dragon."
        gs.setdefault("dragon_conversation_history", []).append({"role": "user", "parts": [{"text": player_dragon_prompt_text}]})
        # --- END: Code to log interaction ---
        
        renpy.store.gemini_response_text_temp = call_gemini_api(
            dragon_prompt_text, 
            "Inspector Dragon", 
            temperature=0.6 
        )

        # --- START: Code to log Dragon's response (already in your version) ---
        # Log the FULL response to history
        if renpy.store.gemini_response_text_temp: # Ensure there's a response to log
            gs["dragon_conversation_history"].append({"role": "assistant", "parts": [{"text": renpy.store.gemini_response_text_temp}]})
        # --- END: Code to log Dragon's response ---

    if renpy.store.last_gemini_error:
        game_narrator "[last_gemini_error]"
        $ renpy.store.last_gemini_error = None
    # This is the 'else' block that runs if there was NO API error
    else:
        if renpy.store.gemini_response_text_temp: # Check if Dragon actually provided a response
            python hide:
                # 'split_text_into_chunks' should always return a list of one or more strings
                # if gemini_response_text_temp is not empty.
                response_chunks = split_text_into_chunks(renpy.store.gemini_response_text_temp, max_sentences_per_chunk=1)
                for chunk_item in response_chunks:
                    # Use renpy.say() with the character object and the text chunk
                    renpy.say(dragon_char, chunk_item) 
        else:
            # This 'else' means Dragon's response was successfully retrieved but was empty.
            dragon_char "(Inspector Dragon offers no specific comment at this time.)"

    jump consult_dragon_menu


label ask_dragon_character_focused:
    python:
        gs = renpy.store.game_state

        current_focus_topic = renpy.store.dragon_focus_topic
        current_focus_type = renpy.store.dragon_focus_type

        if not current_focus_topic: 
            renpy.log("WARNING: ask_dragon_character_focused called without a focus_topic.")
            renpy.jump("consult_dragon_menu") 

        hint_level = 0
        if not gs.get("progress_since_last_dragon", True):
            gs["dragon_consultations_count"] = gs.get("dragon_consultations_count", 0) + 1
            hint_level = min(3, gs["dragon_consultations_count"] // 2)
        else:
            gs["dragon_consultations_count"] = 0
        
        gs["progress_since_last_dragon"] = False

        game_summary = get_game_state_summary_for_dragon(
            gs,
            focused_on=current_focus_topic,
            focus_type=current_focus_type
        )
        
        dragon_prompt_text = build_dragon_persona_prompt(
            game_summary,
            focus_topic=current_focus_topic,
            focus_type=current_focus_type,
            hint_level=hint_level
        )

        # --- START: Code to log interaction (already in your version) ---
        player_dragon_prompt_text = f"Inspector Dragon, what are your thoughts regarding {current_focus_type}: {current_focus_topic}?"
        gs.setdefault("dragon_conversation_history", []).append({"role": "user", "parts": [{"text": player_dragon_prompt_text}]})
        # --- END: Code to log interaction ---
        
        renpy.store.gemini_response_text_temp = call_gemini_api(
            dragon_prompt_text, 
            "Inspector Dragon", 
            temperature=0.6
        )

        # --- START: Code to log Dragon's response (already in your version) ---
        # Log the FULL response to history
        if renpy.store.gemini_response_text_temp: # Ensure there's a response to log
            gs["dragon_conversation_history"].append({"role": "assistant", "parts": [{"text": renpy.store.gemini_response_text_temp}]})
        # --- END: Code to log Dragon's response ---

    if renpy.store.last_gemini_error:
        game_narrator "[last_gemini_error]"
        $ renpy.store.last_gemini_error = None
    # This is the 'else' block that runs if there was NO API error
    else:
        if renpy.store.gemini_response_text_temp: # Check if Dragon actually provided a response
            python hide:
                # 'split_text_into_chunks' should always return a list of one or more strings
                # if gemini_response_text_temp is not empty.
                response_chunks = split_text_into_chunks(renpy.store.gemini_response_text_temp, max_sentences_per_chunk=2)
                for chunk_item in response_chunks:
                    # Use renpy.say() with the character object and the text chunk
                    renpy.say(dragon_char, chunk_item)
        else:
            # This 'else' means Dragon's response was successfully retrieved but was empty.
            dragon_char "(Inspector Dragon seems to have no particular insight on this topic right now.)"
    
    $ renpy.store.dragon_focus_topic = None
    $ renpy.store.dragon_focus_type = None
    
    jump consult_dragon_menu

label action_review_clues_label:
    call screen clues_display_screen
    # After clues_display_screen (which is modal and returns when "Close" is hit)
    # we jump back to the main_hub_menu to refresh it.
    jump main_hub_menu

# In game/custom_screens.rpy

style compact_choice_button is choice_button: # Inherits all properties from your existing "choice_button"
    # Now, override the padding to make the buttons more snug.
    # The default "choice_button" might have larger padding.
    # Experiment with these values. These are examples.
    top_padding 5     # Reduce top padding
    bottom_padding 5  # Reduce bottom padding
    left_padding 10   # Keep horizontal padding reasonable for text
    right_padding 10
    # If yminimum is making them too tall, you can try to override it:
    # yminimum 0 # Or some other smaller specific value, or None to remove it

# You can put this in game/custom_screens.rpy or at the top of script.rpy

style search_menu_choice_button is choice_button: # Inherits from your existing "choice_button"
    # --- Reduce Internal Padding ---
    # Experiment with these values. Start by reducing them from what you think
    # the original "choice_button" might have. If the original buttons are very tall,
    # the ypadding or top/bottom_padding is likely large.
    top_padding 8      # Example: try a smaller value than default
    bottom_padding 8   # Example: try a smaller value
    left_padding 12    # Horizontal padding usually needs to be enough for text
    right_padding 12

    # --- Crucial for reducing height if buttons are forced tall ---
    # If your original choice_buttons have a fixed minimum height that makes them
    # too tall even after reducing padding, uncommenting and adjusting yminimum is key.
    # Setting it to 0 or None allows the button to shrink to fit content + new padding.
    # yminimum 0
    # OR
    # yminimum None

    # Ensure text alignment within the button is still good (often inherited)
    # text_xalign 0.5
    # text_yalign 0.5

# You can put this in game/custom_screens.rpy or at the top of script.rpy

# Define the Frame objects for your button backgrounds first.
# The numbers 12, 12 are for (left_border, top_border, right_border, bottom_border)
# or (horizontal_border, vertical_border) if only two are given.
# These define how much of the edge of your PNG is a non-scaling border.
# You may need to experiment with these values (e.g., 8, 10, 15) if 12 doesn't look right
# with your specific choice_idle_background.png.
define search_grid_idle_bg = Frame("gui/button/choice_idle_background.png", 12, 12)
define search_grid_hover_bg = Frame("gui/button/choice_hover_background.png", 12, 12)

style search_grid_button:
    # --- CONTROLLING WIDTH ---
    # Set a fixed width for the buttons. Adjust this value to fit your layout and text.
    xsize 430  # Example: Each button will be 350 pixels wide.

    # --- REDUCING EMPTY SPACE (PADDING) ---
    # This controls the space INSIDE the button, between the border and the text.
    # Try small values first. (horizontal_padding, vertical_padding)
    padding (15, 8)  # Example: 10px left/right padding, 8px top/bottom padding.

    # --- BACKGROUND IMAGES ---
    background search_grid_idle_bg
    hover_background search_grid_hover_bg

    # --- TEXT STYLING ---
    # (These might be inherited from a default button_text style, but you can be explicit)
    text_align 25     # Centers text horizontally within the button
    # color "#FFFFFF"    # Set text color if needed
    # hover_color "#FFFF00" # Set hover text color if needed
    # font "yourfont.ttf"
    # size 20

    # --- IMPORTANT FOR HEIGHT ---
    # If buttons are still too tall after adjusting padding, the original style might
    # have a yminimum. We ensure our button can shrink to fit its content + padding.
    yminimum 0 # Allows the button height to be determined by content and padding.

screen search_location_grid_screen():
    tag menu

    frame style "game_menu_frame": # Your outer container frame
        xalign 0.5
        yalign 0.8  # We will adjust this later for overall screen positioning
        # padding (20,20) # You had this commented, adjust if needed for the outer frame

        vbox: # Main vbox for caption, columns, and back button
            xalign 0.5
            spacing 20 # Space between caption, columns-hbox, and back button

            text "Where will you search?" xalign 0.5 # ADD xalign 0.5 here

            hbox:  # For the two columns
                spacing 30  # Space between the left and right columns

                # Left Column (4 buttons)
                vbox:
                    spacing 15  # Vertical space between buttons in this column
                    button action Return("study") style "search_grid_button": # USE NEW STYLE
                        text "Lord Blackwood's Study" xalign 0.5
                    button action Return("marianne_room") style "search_grid_button": # USE NEW STYLE
                        text "Marianne's Room" xalign 0.5
                    button action Return("victor_room") style "search_grid_button": # USE NEW STYLE
                        text "Victor's Room" xalign 0.5
                    button action Return("caroline_room") style "search_grid_button": # USE NEW STYLE
                        text "Caroline's Room" xalign 0.5

                # Right Column (4 buttons)
                vbox:
                    spacing 15  # Vertical space between buttons in this column
                    button action Return("garden") style "search_grid_button": # USE NEW STYLE
                        text "The Garden" xalign 0.5
                    button action Return("library") style "search_grid_button": # USE NEW STYLE
                        text "The Library" xalign 0.5
                    button action Return("fireplace") style "search_grid_button": # USE NEW STYLE
                        text "The Fireplace Area" xalign 0.5
                    button action Return("desk") style "search_grid_button": # USE NEW STYLE
                        text "Lord Blackwood's Desk" xalign 0.5
            
            # Back button
            hbox:
                xalign 0.5  # This centers the button within this new (full-width or centered) hbox
                button action Return("back") style "search_grid_button":
                    text "Back to Main Actions" xalign 0.5

# This screen will be used by your talk_to_suspect_menu
# It takes 'items' (your menu choices) and 'kwargs' (which includes the caption) as arguments.
# In game/custom_screens.rpy (or script.rpy where you placed it)

# In game/custom_screens.rpy (or script.rpy where you placed it)

# Place this at the top level (indentation 0)

style talk_menu_caption_style is text:
    xalign 0.5
    bottom_padding 0
    bottom_margin 0
    outlines [(2, "#000000", 0, 0)]  # 2-pixel black outline, no offset
    # Add font/size/color here if you want to customize the caption's look further
    # font "DejaVuSans-Bold.ttf"
    # size 36
    # color "#FFFFFF"

style inner_button_vbox_style: # You can name this style anything you like
    # Properties for the vbox that holds the choice buttons
    xalign 0.5          # To center the buttons block if its parent is wider
    spacing 10          # This is the spacing BETWEEN the individual buttons
    top_padding 0       # No padding at the top of this vbox
    top_margin 0        # No margin at the top of this vbox

screen talk_menu_layout(items, menu_caption=None, **kwargs):
    tag menu
    style_prefix "choice" # This is good, it helps style the textbuttons inside

    # This is the PARENT VBOX
    vbox:
        xalign 0.5
        yalign 0.90  # You are adjusting this for overall vertical position
        spacing 10   # <<--- THIS SHOULD NOW CONTROL THE GAP between caption and button vbox

        # 1. The Caption
        if menu_caption:
            text menu_caption style "talk_menu_caption_style"

        # 2. VBox for the Choice Buttons - APPLY THE NEW STYLE HERE
        vbox style "inner_button_vbox_style": # <<--- MODIFIED LINE
            # xalign, spacing, top_padding, top_margin are now handled by the style

            for i in items:
                textbutton i.caption action i.action
                # This will automatically use "choice_button" style due to style_prefix "choice"

# In game/custom_screens.rpy (or script.rpy at top level)

# In game/custom_screens.rpy (or script.rpy where you placed it)

screen examine_clue_grid_screen(clue_choices_list): # clue_choices_list is now list of (display_text, actual_clue_name)
    tag menu
    modal True # Good, keeps focus

    frame style "game_menu_frame":
        xalign 0.5
        yalign 0.55
        # Adjust xsize/ysize of the frame if needed based on button sizes and number of columns
        # xsize 1200 # Example
        # ysize 700 # Example

        vbox:
            xalign 0.5
            spacing 15

            text "Examine Which Clue More Closely?" style "game_menu_label" xalign 0.5

            if not clue_choices_list:
                frame: # Simple frame for the message for consistent padding
                    xalign 0.5
                    # Padding for the "no clues" message container
                    top_padding 50 
                    bottom_padding 50
                    text "No specific physical clues discovered yet." xalign 0.5 style "clue_desc_text" # Re-use a style
            else:
                viewport:
                    id "examine_clue_viewport"
                    # Adjust xmaximum based on your button style (e.g., search_grid_button2 xsize) and grid columns
                    # If search_grid_button2 xsize is 570 and you have 2 columns with 20 spacing: (570*2) + 20 = 1160
                    xmaximum 1180 # Allow some buffer
                    xfill True # Ensure viewport uses available width up to xmaximum
                    ysize 500  # Adjust scrollable height as needed

                    scrollbars "vertical"
                    mousewheel True
                    draggable True

                    python:
                        # Python block for grid setup should be fine if it was working before
                        num_items_in_grid = len(clue_choices_list)
                        num_columns_in_grid = 2 # Or 1 if you prefer a single column
                        num_rows_for_this_grid = (num_items_in_grid + num_columns_in_grid - 1) // num_columns_in_grid
                        if num_rows_for_this_grid == 0: 
                            num_rows_for_this_grid = 1 # Ensure grid is defined

                    grid num_columns_in_grid num_rows_for_this_grid:
                        xfill True # Grid should fill the viewport width
                        xspacing 20 # Horizontal space between columns
                        yspacing 15 # Vertical space between rows

                        # MODIFIED LOOP BELOW:
                        # It now iterates over tuples: (text_for_button, name_to_return_on_action)
                        for display_text_for_button, actual_clue_name_to_return in clue_choices_list:
                            button action Return(actual_clue_name_to_return) style "search_grid_button2": # Assuming this is your preferred button style here
                                text display_text_for_button xalign 0.5 # Use the pre-formatted display_text
            
            # "Back" button is always present, outside the conditional clue list
            hbox: # Use an hbox to center the button if its style doesn't fill width
                xalign 0.5 
                button action Return("back") style "search_grid_button2": # Use consistent button style
                    text "Back to Main Actions" xalign 0.5
                            
style search_grid_button2:
    # --- CONTROLLING WIDTH ---
    # Set a fixed width for the buttons. Adjust this value to fit your layout and text.
    xsize 570  # Example: Each button will be 350 pixels wide.

    # --- REDUCING EMPTY SPACE (PADDING) ---
    # This controls the space INSIDE the button, between the border and the text.
    # Try small values first. (horizontal_padding, vertical_padding)
    padding (15, 8)  # Example: 10px left/right padding, 8px top/bottom padding.

    # --- BACKGROUND IMAGES ---
    background search_grid_idle_bg
    hover_background search_grid_hover_bg

    # --- TEXT STYLING ---
    # (These might be inherited from a default button_text style, but you can be explicit)
    text_align 25     # Centers text horizontally within the button
    # color "#FFFFFF"    # Set text color if needed
    # hover_color "#FFFF00" # Set hover text color if needed
    # font "yourfont.ttf"
    # size 20

    # --- IMPORTANT FOR HEIGHT ---
    # If buttons are still too tall after adjusting padding, the original style might
    # have a yminimum. We ensure our button can shrink to fit its content + padding.
    yminimum 0 # Allows the button height to be determined by content and padding.

# Place this at the top level of your script.rpy, or in a new file like game/custom_screens.rpy

# In your custom_screens.rpy or script.rpy (wherever you have this screen)

# In your custom_screens.rpy or script.rpy (wherever you have this screen)

# In game/custom_screens.rpy or script.rpy

# In game/custom_screens.rpy or script.rpy

# In game/custom_screens.rpy or script.rpy

screen ingame_interaction_menu_layout(choices_list, caption_text=None):
    # REMOVE or COMMENT OUT: style_prefix "choice"

    # Outermost vbox for overall positioning and content stacking
    vbox:
        xalign 0.5
        yalign 0.85 # This positions the entire menu block
        spacing 10  # Vertical spacing between the caption and the button group

        if caption_text:
            text caption_text:
                style "ingame_menu_caption_text" # Use the new specific caption style
                # xalign 0.5 is part of the style definition now

        # VBox specifically for the list of choice buttons
        vbox:
            xalign 0.5 # Center this block of buttons
            spacing 10 # Vertical space between individual buttons (adjust as needed)

            for L, A in choices_list:
                # Apply the new specific button style.
                # Ren'Py will automatically look for "ingame_menu_button_text"
                # for the text style if the button's style is "ingame_menu_button".
                textbutton L action A style "ingame_menu_button"

# In game/custom_screens.rpy or at the top of script.rpy

# --- Styles for In-Game Interaction Menus (Dragon, Suspects) ---

# --- Styles for In-Game Interaction Menus (Dragon, Suspects) ---

# Style for the button "box" itself
style ingame_menu_button is button:
    # --- Recreate your "original box" appearance ---
    background Frame("gui/button/choice_idle_background.png", 12, 12)
    hover_background Frame("gui/button/choice_hover_background.png", 12, 12)

    # Padding inside the button (space between text and button edge)
    xpadding 40
    ypadding 10

    text_align 0.5 # Typically 0.5 to center text within the button

    # --- ADD THIS LINE FOR UNIFORM WIDTH ---
    xsize 570  # Example width: 400 pixels. Adjust this value as needed.
    # ysize 65   # Optional: You can also set a fixed height (ysize) if you want all buttons
                 # to have the same height, regardless of text lines (though these are single-line).

# Style for the text within the ingame_menu_button
style ingame_menu_button_text is button_text: # Deriving from button_text is good practice
    font "DejaVuSans.ttf"
    size 29
    color "#FFFFFF"
    hover_color "#FFFF00"
    text_align 0.5
    xalign 0.5
    # outlines [(1, "#000000", 0, 0)] # Optional for readability

# Style for the caption text (e.g., "Consulting Inspector Dragon...")
style ingame_menu_caption_text is text:
    font "DejaVuSans.ttf"
    size 29
    color "#FFFFFF"
    xalign 0.5
    outlines [(1, "#000000", 0, 0)] # Optional

# Add this new label somewhere in your game flow labels section
label show_conversation_history:
    # active_suspect_interaction should still be set from suspect_interaction_hub
    if active_suspect_interaction:
        call screen conversation_history_screen(suspect_full_name=active_suspect_interaction)
    jump suspect_interaction_hub # Return to the interaction menu

# --- Add these styles with your other screen styles ---
style history_player_text:
    size 24 # Adjust as needed
    color "#aaddff" # Player's question color (same as 'p' character)
    left_margin 10
    bottom_margin 5

style history_suspect_text:
    size 24 # Adjust as needed
    color "#E0E0E0" # A slightly lighter grey for suspect responses
    left_margin 10
    bottom_margin 10

style history_title_text:
    font "DejaVuSans-Bold.ttf"
    size 30 # Adjust as needed
    color "#FFFFFF"
    xalign 0.5
    bottom_padding 10

screen conversation_history_screen(suspect_full_name):
    tag menu
    modal True

    $ suspect_short_name = suspect_full_name.split(" ")[0]
    $ history = game_state["suspect_conversations"].get(suspect_full_name, [])

    frame:
        style "game_menu_frame"
        xalign 0.5
        yalign 0.5
        xsize 1300
        ysize 900

        vbox:
            spacing 15
            xfill True

            text f"Conversation with {suspect_short_name}" style "history_title_text"

            if not history:
                text "No conversation history with this suspect yet." xalign 0.5 yalign 0.5 style "clue_desc_text"
            else:
                viewport:
                    id "conversation_history_viewport"
                    draggable True
                    mousewheel True
                    scrollbars "vertical"
                    xfill True
                    ysize 700 # Keeping explicit height as it seems to work well

                    vbox: # VBox inside the viewport
                        spacing 8
                        xfill True

                        for i, entry in enumerate(history):
                            $ role = entry.get("role")
                            $ text_parts = entry.get("parts")
                            $ current_text_content = "Error: Initial default for text_content_debug" # Default before conditions

                            if text_parts and isinstance(text_parts, list) and len(text_parts) > 0:
                                $ current_text_content = text_parts[0].get("text", "Error: No text in part")
                            elif text_parts:
                                $ current_text_content = "Error: 'parts' is not a valid list structure or is empty"
                            else:
                                $ current_text_content = "Error: 'parts' key is missing or value is None"
                            
                            # REMOVED: text "Entry [i]: Role='[role]', Content='[current_text_content[:50]]...'" style "clue_desc_text"

                            # Actual conversation lines
                            if role == "user":
                                text f"Inspector Hart: {current_text_content}" style "history_player_text"
                            elif role == "assistant":
                                text f"{suspect_short_name}: {current_text_content}" style "history_suspect_text"
                            else:
                                text f"Unknown ({role}): {current_text_content}" style "clue_desc_text"

            null height 10
            textbutton "Back" action Return() xalign 0.5 style "game_menu_button"
                
style history_player_text:
    size 24 # Adjust as needed
    color "#aaddff" # Player's question color (same as 'p' character)
    left_margin 10
    bottom_margin 5

style history_suspect_text:
    size 24 # Adjust as needed
    color "#E0E0E0" # A slightly lighter grey for suspect responses
    left_margin 10
    bottom_margin 10

style history_title_text: # This was already fine
    font "DejaVuSans-Bold.ttf"
    size 30 # Adjust as needed
    color "#FFFFFF"
    xalign 0.5
    bottom_padding 10

# Add this new label somewhere in your game flow labels section
label show_dragon_conversation_history:
    call screen dragon_conversation_display_screen # New screen name
    jump consult_dragon_menu # Return to Dragon's interaction menu

# --- Add this style with your other screen styles ---
# You can reuse history_player_text. For Dragon, we can make a new one or reuse history_suspect_text
# Let's make a specific one for Dragon for potential future distinct styling.
style history_dragon_text:
    size 24 # Adjust as needed
    color "#ddddff" # Dragon's character color
    left_margin 10
    bottom_margin 10

# Screen definition (place near your other screen definitions)
screen dragon_conversation_display_screen():
    tag menu
    modal True

    $ history = game_state.get("dragon_conversation_history", [])

    frame:
        style "game_menu_frame" # Reuse your existing frame style
        xalign 0.5
        yalign 0.5 
        xsize 1300 # Adjust width as needed
        ysize 900  # Adjust height as needed

        vbox:
            spacing 15
            xfill True

            text "Conversation with Inspector Dragon" style "history_title_text" # Reused style

            if not history:
                text "No conversation history with Inspector Dragon yet." xalign 0.5 yalign 0.5 style "clue_desc_text" # Reused style
            else:
                viewport:
                    id "dragon_conversation_viewport"
                    draggable True
                    mousewheel True
                    scrollbars "vertical"
                    xfill True
                    ysize 700 # Explicit height, adjust as needed

                    vbox:
                        spacing 8
                        xfill True

                        for entry in history:
                            $ role = entry.get("role")
                            # Ensure robust text extraction
                            $ current_text_content = "Error: Data issue"
                            if entry.get("parts") and isinstance(entry["parts"], list) and len(entry["parts"]) > 0:
                                $ current_text_content = entry["parts"][0].get("text", "Error: Missing text in part")
                            
                            if role == "user": # Player's prompt to Dragon
                                text f"Inspector Hart: {current_text_content}" style "history_player_text" # Reused style
                            elif role == "assistant": # Dragon's response
                                text f"Inspector Dragon: {current_text_content}" style "history_dragon_text" # New style for Dragon
                            else:
                                text f"Unknown Log Entry: {current_text_content}" style "clue_desc_text"

            null height 10 # Spacer
            textbutton "Back" action Return() xalign 0.5 style "game_menu_button" # Reused style
                
default ending_pages_content = []
default current_ending_page_index = 0
default ending_sequence_active = False # To control nvl_display behavior

label handle_accusation_flow:
    $ temp_accused_suspect_name = temp_accused_suspect 
    if not temp_accused_suspect_name:
        jump main_hub_menu 

    python:
        # This first python block defines the necessary variables for immediate feedback
        accused_suspect_full_name_local = renpy.store.temp_accused_suspect # Use a local var to avoid store access issues in f-string
        actual_murderer_full_name_local = renpy.store.game_state["murderer"]
        is_correct_accusation_local = (accused_suspect_full_name_local == actual_murderer_full_name_local)
        
        renpy.store.current_location_bg = "bg manor general" 

        # Prepare the feedback message
        feedback_message_str = ""
        if is_correct_accusation_local:
            feedback_message_str = f"You accuse {accused_suspect_full_name_local} of the murder of Lord Henry Blackwood.\nAfter reviewing all evidence and testimony, your accusation is... CORRECT!"
        else:
            feedback_message_str = f"You accuse {accused_suspect_full_name_local} of the murder of Lord Henry Blackwood.\nAfter reviewing all evidence and testimony, your accusation is... INCORRECT."
        renpy.store.feedback_message_for_display = feedback_message_str
    
    # IMMEDIATE FEEDBACK (NARRATOR)
    scene expression current_location_bg 
    game_narrator "[feedback_message_for_display]"
    
    $ renpy.pause(1.5, hard=True)

    # Show the loading screen BEFORE the potentially long Python block with the API call
    show screen api_loading_message_screen(message_text="Game ending loading...")
    # Brief pause to ensure the screen has a chance to render before the blocking Python code
    $ renpy.pause(0.05) 

    python:
        # Re-fetch/confirm key variables for this block if not relying on automatic store propagation
        # For clarity, let's use the variables directly from the store as they were set before the narrator part
        accused_full_name_py = renpy.store.temp_accused_suspect
        actual_murderer_full_name_py = renpy.store.game_state["murderer"]
        is_correct_py = (accused_full_name_py == actual_murderer_full_name_py)

        if not hasattr(renpy.store, 'ending_pages_content') or not isinstance(renpy.store.ending_pages_content, list):
            renpy.store.ending_pages_content = []
        else:
            renpy.store.ending_pages_content.clear()

        renpy.store.current_ending_page_index = 0
        renpy.store.ending_sequence_active = True 

        gs_local = renpy.store.game_state
        ed_game_local = renpy.store.EVIDENCE_DATA_GAME
        
        dragon_speech_for_ending = None 

        # --- API Call Section ---
        if is_correct_py:
            dragon_prompt = generate_dragon_correct_accusation_prompt(actual_murderer_full_name_py, gs_local, ed_game_local)
            api_call_context = "Inspector Dragon (Ending Congratulations)"
            fallback_speech = f"Inspector Dragon: (Smiling warmly) My sincerest congratulations, Inspector Hart! A masterful deduction. {actual_murderer_full_name_py} was indeed the one."
            blocked_speech = f"Inspector Dragon: (Nodding) Excellent work, Inspector! Your conclusion is sound. {actual_murderer_full_name_py} it was."
        else: 
            dragon_prompt = generate_dragon_incorrect_accusation_prompt(accused_full_name_py, actual_murderer_full_name_py, gs_local, ed_game_local)
            api_call_context = "Inspector Dragon (Ending Explanation)"
            fallback_speech = f"Inspector Dragon: (Sighs) A most complex affair, Inspector. The truth was indeed elusive. The actual murderer was {actual_murderer_full_name_py}."
            blocked_speech = f"Inspector Dragon: My apologies, Inspector. The full picture seems momentarily clouded. However, the evidence ultimately points to {actual_murderer_full_name_py}."

        renpy.store.last_dragon_ending_prompt = dragon_prompt 
        # The actual API call that causes the wait
        raw_dragon_response = call_gemini_api(dragon_prompt, api_call_context, temperature=0.55) 
        
        # --- Hide Loading Screen ---
        # This is called from within the Python block immediately after the API call returns.
        renpy.hide_screen("api_loading_message_screen")
            
        # Process the API response
        if renpy.store.last_gemini_error:
            dragon_speech_for_ending = fallback_speech
            renpy.store.last_gemini_error = None 
        elif not raw_dragon_response or not raw_dragon_response.strip() or \
             "My response was blocked" in raw_dragon_response or \
             "Sorry, I can't respond" in raw_dragon_response or \
             "I received no valid response" in raw_dragon_response or \
             "I received an unusual response" in raw_dragon_response:
                dragon_speech_for_ending = blocked_speech
        else:
            dragon_speech_for_ending = f"Inspector Dragon: {raw_dragon_response.strip()}"
            
        renpy.store.ending_pages_content.append(
            format_explanation_text(f"Inspector Dragon's Assessment", [dragon_speech_for_ending])
        )

        # 2. THE ACTUAL CULPRIT'S SUMMARY (Page 2)
        renpy.store.ending_pages_content.append(
            generate_murderer_detailed_summary(actual_murderer_full_name_py, gs_local, ed_game_local)
        )
        
        # 3. THE INNOCENTS' SUMMARY (Page 3)
        innocent_suspects_to_list = [name for name in SUSPECTS_FULL_NAMES.values() if name != actual_murderer_full_name_py]
        if innocent_suspects_to_list:
            renpy.store.ending_pages_content.append(
                generate_all_innocents_summary(innocent_suspects_to_list, actual_murderer_full_name_py, gs_local, ed_game_local)
            )
        
        renpy.store.temp_is_correct_accusation = is_correct_py 
        renpy.store.temp_actual_murderer_name_for_dragon = actual_murderer_full_name_py.split(" ")[0]

        if not renpy.store.ending_pages_content: 
            renpy.store.ending_pages_content.append(
                format_explanation_text("Case Conclusion", ["The details of the case have been methodically recorded."])
            )
    # End of the python block 

    jump show_ending_text_page

label show_ending_text_page:
    python:
        if not hasattr(renpy.store, 'current_ending_page_index'):
            renpy.store.current_ending_page_index = 0
        
        idx = renpy.store.current_ending_page_index
        # Ensure pages is a list, defaulting to empty if not properly set
        pages = getattr(renpy.store, 'ending_pages_content', []) 
        
        # Directly clear nvl_buffer.
        renpy.store.nvl_buffer.clear()

        if idx < len(pages):
            renpy.store.ending_sequence_active = True 
            page_content = pages[idx]
            # Split the formatted page content by newlines for NVL display
            # This assumes format_explanation_text uses '\n' to separate logical lines/paragraphs
            lines_for_nvl = page_content.strip().splitlines()
            if not lines_for_nvl and page_content.strip(): # If splitlines is empty but original content was not just whitespace
                add_to_nvl_display_buffer(page_content.strip()) # Add the whole content as one block
            else:
                for line_to_add in lines_for_nvl:
                    add_to_nvl_display_buffer(line_to_add) # Add each line separately
        else:
            renpy.store.ending_sequence_active = False 
            
    if renpy.store.ending_sequence_active:
        hide screen hud_screen 
        call screen nvl_display 
        $ renpy.store.current_ending_page_index += 1
        jump show_ending_text_page 
    else:
        hide screen hud_screen 
        if renpy.store.temp_is_correct_accusation:
            jump ending_dragon_on_screen_congrats 
        else:
            jump ending_dragon_on_screen_commiserate

label ending_dragon_on_screen_congrats:
    scene bg manor general with dissolve 
    show dragon neutral at center with dissolve # Ensure Dragon is visible

    dragon_char "Indeed, a fine resolution, Inspector. Justice has been meticulously served."
    dragon_char "Your dedication to uncovering the truth in this tangled affair has been truly admirable."
    dragon_char "Thank you for your invaluable assistance at Blackwood Manor. This case is now closed."
    
    # Optional: A brief pause before the game ends, allowing the player to read the last line.
    $ renpy.pause(2.0, hard=True) 

    # This will end the game or return to the main menu if called from the main game flow.
    return

label ending_dragon_on_screen_commiserate:
    scene bg manor general with dissolve
    show dragon neutral at center with dissolve # Ensure Dragon is visible

    python:
        # _murderer_name_on_screen should have been set by handle_accusation_flow
        # to renpy.store.temp_actual_murderer_name_for_dragon
        _murderer_name_on_screen = renpy.store.temp_actual_murderer_name_for_dragon
    
    dragon_char "A perplexing case, but the truth, however grim, has now been fully illuminated. It was indeed [_murderer_name_on_screen]."
    dragon_char "These investigations test us all, Inspector. Your perseverance was noted."
    dragon_char "Thank you for your efforts in navigating the complexities of Blackwood Manor. May you find some peace after this ordeal."

    $ renpy.pause(2.0, hard=True)

    return # End the game / return to main menu


label final_thank_you_message:
    hide screen hud_screen
    # You can use NVL mode for the thank you, or a simple screen
    python:
        renpy.store.nvl_buffer.clear()
        add_to_nvl_display_buffer("======== THE END ========")
        add_to_nvl_display_buffer("\nThank you for playing Murder at Blackwood Manor!")
        # If you want game state to be non-interactive here:
        renpy.store.ending_sequence_active = True # Re-use flag to make nvl_display's "Continue" just Return
        renpy.store.game_state["intro_active"] = False # Ensure intro logic doesn't interfere

    call screen nvl_display # "Continue" will just Return
    
    # After the final "Continue", the game ends.
    return # This will end the game.

screen show_clue_to_suspect_grid_screen(clue_choices_list, current_suspect_name):
    # clue_choices_list will be a list of tuples: (clue_name_for_display, clue_name_for_action)
    # For this screen, both will typically be the same (just the clue name).
    tag menu
    modal True

    frame style "game_menu_frame": # Reuse existing frame style
        xalign 0.5
        yalign 0.55 # Adjust vertical position as needed, similar to examine_clue_grid_screen
        # You might want to adjust xsize/ysize if the content differs significantly

        vbox:
            xalign 0.5
            spacing 15

            text f"Show which clue to {current_suspect_name}?" style "game_menu_label" xalign 0.5

            if not clue_choices_list:
                frame:
                    xalign 0.5
                    top_padding 50 
                    bottom_padding 50
                    text "You have no discovered clues to show." xalign 0.5 style "clue_desc_text"
            else:
                viewport:
                    id "show_clue_to_suspect_viewport"
                    # Adjust xmaximum based on your button style and grid columns
                    # e.g., if button xsize is 570, 2 columns, 20 spacing: (570*2) + 20 = 1160
                    xmaximum 1180 
                    xfill True
                    ysize 500  # Adjust scrollable height as needed

                    scrollbars "vertical"
                    mousewheel True
                    draggable True

                    python:
                        num_items_in_grid = len(clue_choices_list)
                        num_columns_in_grid = 2 # Or 1, or 3, depending on your preference and button size
                        num_rows_for_this_grid = (num_items_in_grid + num_columns_in_grid - 1) // num_columns_in_grid
                        if num_rows_for_this_grid == 0: 
                            num_rows_for_this_grid = 1 

                    grid num_columns_in_grid num_rows_for_this_grid:
                        xfill True
                        xspacing 20    # Horizontal space between columns
                        yspacing 15    # Vertical space between rows

                        for clue_display_name, clue_action_name in clue_choices_list:
                            button action Return(clue_action_name) style "search_grid_button2": # Reusing style from examine_clue_grid_screen
                                text clue_display_name xalign 0.5
            
            # "Cancel" button, always present
            hbox:
                xalign 0.5 
                button action Return("cancel_show_clue") style "search_grid_button2": # Use a distinct return value for cancel
                    text "Cancel" xalign 0.5
                
screen api_loading_message_screen(message_text="Loading..."):
    # Ensures this screen is on top of other UI elements
    zorder 200
    # modal True # Making it modal prevents clicks on things underneath during loading

    # A simple frame or vbox to center the text
    frame: # You can style this frame or use a simple vbox
        style "game_menu_frame" # Optional: reuse an existing frame style for consistency
        xalign 0.5
        yalign 0.5
        padding (40, 25) # Adjust padding as needed

        text message_text:
            xalign 0.5
            yalign 0.5
            # Add text style properties if needed (color, size, font)
            # style "loading_text_style" # If you define a specific style