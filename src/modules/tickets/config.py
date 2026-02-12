from __future__ import annotations

import datetime
import os
from dataclasses import dataclass


@dataclass(slots=True)
class TicketsSettings:
    ticket_category_id: int
    fraction_category_id: int
    rp_category_id: int
    log_channel_id: int
    support_role_id: int
    embed_color: int = 0xFCD005
    main_color: int = 0xFCD005
    rp_color: int = 0x27AE60
    fraction_color: int = 0x3498DB
    panel_image_url: str = (
        "https://media.discordapp.net/attachments/1077268549371965493/"
        "1426205017223856320/img.png?ex=68ea606d&is=68e90eed&hm="
        "740c9377ee444b8c147ad7df00715be59fa7fbc8007aac41fc41d6c754e7a920"
        "&=&format=webp&quality=lossless"
    )


MSK_TIMEZONE = datetime.timezone(datetime.timedelta(hours=3))


def _require_int_env(name: str) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        raise RuntimeError(f"Требуется переменная окружения {name}.")

    try:
        return int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"Переменная окружения {name} должна быть целым числом, получено: {raw_value!r}") from error


def load_tickets_settings() -> TicketsSettings:
    return TicketsSettings(
        ticket_category_id=_require_int_env("TICKET_CATEGORY_ID"),
        fraction_category_id=_require_int_env("FRACTION_CATEGORY_ID"),
        rp_category_id=_require_int_env("RP_CATEGORY_ID"),
        log_channel_id=_require_int_env("LOG_CHANNEL_ID"),
        support_role_id=_require_int_env("SUPPORT_ROLE_ID"),
    )


def get_msk_time() -> datetime.datetime:
    return datetime.datetime.now(MSK_TIMEZONE)


def convert_to_msk(utc_time: datetime.datetime) -> datetime.datetime:
    return utc_time.replace(tzinfo=datetime.timezone.utc).astimezone(MSK_TIMEZONE)
