# main.py
from agent.research_agent import ResearchAgent
from agent.plan_editor import PlanEditor
from agent import voice as voice_mod

def display_plan(plan):
    print("\n===== GENERATED ACCOUNT PLAN =====")
    for key, value in plan.items():
        if key == "sources":
            print(f"\n### {key.upper()} ###")
            for i, s in enumerate(value):
                print(f"{i+1}. {s}")
            continue
        print(f"\n### {key.upper()} ###")
        print(value)
    print("\n================================\n")

def run_text_flow():
    agent = ResearchAgent()
    editor = PlanEditor()

    company = input("Enter company name: ").strip()
    print("\nResearching... please wait...\n")
    research_data, sources = agent.search_company(company)
    plan = agent.generate_account_plan(research_data, sources, company)
    display_plan(plan)

    print("Reading the plan aloud...")
    voice_mod.speak_text(f"Here is the account plan for {company}. {plan.get('company_overview','')[:800]}")

    while True:
        choice = input("\nDo you want to edit any section? (yes/no): ").lower()
        if choice != "yes":
            break
        section = input("Enter section name (company_overview, key_findings, pain_points, opportunities, competitors, recommended_strategy): ").strip()
        new_text = input("Enter new content: ")
        result = editor.edit_section(plan, section, new_text)
        print(result)
    print("\nFinal Plan:")
    display_plan(plan)
    print("Reading final plan aloud...")
    voice_mod.speak_text(f"Final account plan for {company}. {plan.get('company_overview','')[:800]}")

def run_voice_flow():
    agent = ResearchAgent()
    editor = PlanEditor()

    dur = input("How many seconds to record the company name? (default 4): ").strip()
    dur = float(dur) if dur else 4.0
    audio_path = voice_mod.record_audio(duration_seconds=dur)
    company_text = voice_mod.transcribe_audio(audio_path)
    if not company_text:
        print("Could not transcribe audio. Try again or use text mode.")
        return
    print(f"Transcribed company input: {company_text}")

    confirm = input(f"Use this as company name? [{company_text}] (yes/no): ").lower()
    if confirm != "yes":
        print("Aborting voice flow.")
        return

    company = company_text.strip()
    print("\nResearching... please wait...\n")
    research_data, sources = agent.search_company(company)
    plan = agent.generate_account_plan(research_data, sources, company)
    display_plan(plan)

    print("Reading the plan aloud now...")
    chunk = f"Here is the account plan for {company}. {plan.get('company_overview','')}"
    voice_mod.speak_text(chunk)

    while True:
        resp = input("\nDo you want to edit a section by voice? (yes/no): ").lower()
        if resp != "yes":
            break
        section = input("Which section to edit? (company_overview, key_findings, pain_points, opportunities, competitors, recommended_strategy): ").strip()
        sec_dur = input("How many seconds to record the new content? (default 6): ").strip()
        sec_dur = float(sec_dur) if sec_dur else 6.0
        print(f"Recording new content for section '{section}'...")
        a_path = voice_mod.record_audio(duration_seconds=sec_dur)
        new_text = voice_mod.transcribe_audio(a_path)
        if not new_text:
            print("Could not transcribe edit audio. Try again.")
            continue
        print(f"Transcribed new text: {new_text}")
        confirm_edit = input("Apply this edit? (yes/no): ").lower()
        if confirm_edit == "yes":
            result = editor.edit_section(plan, section, new_text)
            print(result)
            print("Reading updated section aloud...")
            voice_mod.speak_text(new_text)
        else:
            print("Edit discarded.")
    print("\nFinal Plan:")
    display_plan(plan)
    print("Reading final plan aloud...")
    voice_mod.speak_text(f"Final account plan for {company}. {plan.get('company_overview','')}")

def main():
    print("Company Research Assistant — choose mode:")
    print("1) Text chat mode")
    print("2) Voice mode (record + TTS)")
    mode = input("Enter 1 or 2: ").strip()
    if mode == "2":
        run_voice_flow()
    else:
        run_text_flow()

if __name__ == "__main__":
    main()
