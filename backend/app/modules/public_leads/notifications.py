from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from urllib import request

from app.modules.public_leads.schemas import PublicLeadCreate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PublicLeadTelegramConfig:
    bot_token: str | None
    chat_id: str | None

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)


class PublicLeadTelegramNotifier:
    def __init__(self, config: PublicLeadTelegramConfig):
        self.config = config

    def send(self, payload: PublicLeadCreate, *, work_item_id: str) -> None:
        if not self.config.is_configured:
            return

        body = {
            "chat_id": self.config.chat_id,
            "text": self._format_message(payload, work_item_id=work_item_id),
            "disable_web_page_preview": True,
        }
        data = json.dumps(body).encode("utf-8")
        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"Telegram returned HTTP {response.status}")

    def _format_message(self, payload: PublicLeadCreate, *, work_item_id: str) -> str:
        lines = [
            "New Flexity public lead",
            f"Name: {payload.name}",
            f"Work item: {work_item_id}",
            f"Source page: {payload.source_page}",
        ]
        if payload.phone:
            lines.append(f"Phone: {payload.phone}")
        if payload.email:
            lines.append(f"Email: {payload.email}")
        if payload.company:
            lines.append(f"Company: {payload.company}")
        if payload.preferred_channel:
            lines.append(f"Preferred channel: {payload.preferred_channel}")
        if payload.process_area:
            lines.append(f"Process area: {payload.process_area}")
        if payload.message:
            lines.append(f"Message: {payload.message}")
        return "\n".join(lines)
