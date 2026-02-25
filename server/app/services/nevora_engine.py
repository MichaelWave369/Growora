import json
from typing import Any

import httpx

from app.core.config import settings
from app.services.network_guard import ensure_url_allowed


def enrich_with_llm(prompt: str) -> str:
    if settings.growora_llm_provider != "ollama":
        return ""
    ensure_url_allowed(settings.growora_ollama_url)
    try:
        with httpx.Client(timeout=20) as client:
            r = client.post(
                f"{settings.growora_ollama_url}/api/generate",
                json={"model": settings.growora_ollama_model, "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            return r.json().get("response", "")
    except Exception:
        return ""


def build_worksheet(topic: str, level: str, day: int) -> str:
    base = f"# {topic} Worksheet (Day {day})\n\n- Level: {level}\n- Warm-up: 5 minutes\n- Practice: 20 minutes\n- Reflection: 5 minutes"
    llm = enrich_with_llm(f"Create concise worksheet for {topic} {level} day {day}")
    return base + ("\n\n## Extra Tips\n" + llm if llm else "")


def build_flashcards(topic: str, count: int = 8) -> list[dict[str, Any]]:
    return [
        {"front": f"{topic}: key idea {i+1}?", "back": f"Definition/explanation for key idea {i+1}", "tags": [topic, "core"]}
        for i in range(count)
    ]


def build_quiz(topic: str) -> dict[str, Any]:
    return {
        "questions": [
            {
                "type": "mcq",
                "prompt": f"Which statement best describes a foundational concept in {topic}?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": 0,
            },
            {
                "type": "short",
                "prompt": f"Write one practical use-case of {topic}.",
                "answer": "Any reasonable practical use-case.",
            },
        ]
    }


def build_coding_scaffold(topic: str) -> dict[str, str]:
    return {
        "README.md": f"# Mini project for {topic}\n\nBuild a tiny app demonstrating one core concept.",
        "main.py": "print('Start your project here')\n",
    }


def package_markdown(course: dict[str, Any]) -> str:
    return json.dumps(course, indent=2)
