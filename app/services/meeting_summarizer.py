from typing import Dict, Any, List
from app.services.ai_engine import ai_engine

def summarize_meeting_notes(title: str, raw_notes: str) -> Dict[str, Any]:
    prompt = (
        f"Analyze these meeting notes for meeting: '{title}'\n\n"
        f"Raw Notes:\n{raw_notes}\n\n"
        f"Generate a concise executive summary and extract key action items.\n"
        f"Return JSON format with structure:\n"
        f"{{\n"
        f'  "summary": "High level bulleted summary of decisions made",\n'
        f'  "action_items": [\n'
        f'    {{"task": "Action description", "owner": "Assignee name", "deadline": "Expected deadline"}}\n'
        f"  ]\n"
        f"}}"
    )

    schema_desc = "JSON object with keys 'summary' (string) and 'action_items' (array of objects with 'task', 'owner', 'deadline')."
    structured_result = ai_engine.generate_structured_json(prompt, schema_desc)

    if not structured_result or "summary" not in structured_result:
        summary_text = ai_engine.generate_text(f"Summarize these meeting notes in 3 bullets:\n{raw_notes}")
        action_items = [
            {"task": "Follow up on meeting key points", "owner": "Team Lead", "deadline": "End of week"}
        ]
        return {
            "summary": summary_text,
            "action_items": action_items
        }

    return structured_result
