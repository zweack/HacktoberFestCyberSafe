"""Curated, India-first helpline directory. Every entry carries an official source_url."""

import json
from functools import lru_cache
from pathlib import Path

from app.schemas import Contact, Language

_PATH = Path(__file__).with_name("directory.json")


@lru_cache
def load_directory() -> tuple[Contact, ...]:
    return tuple(Contact.model_validate(c) for c in json.loads(_PATH.read_text("utf-8")))


def get_contact(id: str) -> Contact | None:
    return next((c for c in load_directory() if c.id == id), None)


def localized(contact: Contact, lang: Language) -> Contact:
    """Copy with name/description in the requested language (falls back to English)."""
    if lang == Language.hi:
        return contact.model_copy(
            update={
                "name": contact.name_hi or contact.name,
                "description": contact.description_hi or contact.description,
            }
        )
    return contact


def contacts_for(ids: list[str], lang: Language) -> list[Contact]:
    return [localized(c, lang) for i in ids if (c := get_contact(i))]
