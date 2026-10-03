import os
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


class GrokClient:
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY", "")
        self.model = os.getenv("GROK_MODEL", "grok-2-latest")
        self.base_url = "https://api.x.ai/v1/chat/completions"

    def generate_custom_message(
        self,
        business_name: str,
        category: str,
        city: str = "India",
        website: Optional[str] = None,
    ) -> str:
        if website:
            fallback = (
                f"Hi {business_name}, your {category} already has a website, which is a great start. "
                "We help local businesses improve their website with AI-assisted search optimization and workflow automation, "
                "so more nearby customers can find you and your team can save time. Would you be open to a short conversation?"
            )
        else:
            fallback = (
                f"Hi {business_name}, I couldn't find a website for your {category} in {city}. "
                "We build clear, mobile-friendly websites for local businesses and can help you make it easier for new customers "
                "to discover and contact you. Would you be open to a short conversation?"
            )

        if not self.api_key:
            return fallback

        if website:
            prompt = (
                f"Write a short, polite outreach message for {category} business '{business_name}' in {city}. "
                f"They already have a website: {website}. Offer AI-assisted website/search optimization and workflow automation "
                "to help attract more customers and save time. Do not suggest they lack a website. "
                "Keep it warm, specific, under 100 words, and avoid guarantees."
            )
        else:
            prompt = (
                f"Write a short, polite outreach message for {category} business '{business_name}' in {city}. "
                "No website was listed for them. Offer to build a mobile-friendly website that helps customers discover and contact them. "
                "Keep it warm, specific, under 100 words, and avoid guarantees."
            )

        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]["content"].strip()
            return message or fallback
        except Exception:
            return fallback
