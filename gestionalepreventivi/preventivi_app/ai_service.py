import os
from typing import Dict

from openai import OpenAI

from preventivi_app.settings_service import get_setting


DEFAULT_MODEL = "gpt-5.4"
API_KEY_SETTING = "openai_api_key"
MODEL_SETTING = "openai_model"


class AIServiceError(Exception):
    pass


def get_configured_model() -> str:
    return str(get_setting(MODEL_SETTING, DEFAULT_MODEL) or DEFAULT_MODEL)


def has_api_key() -> bool:
    return bool(_get_api_key())


def generate_quote_texts(context: Dict[str, str]) -> Dict[str, str]:
    api_key = _get_api_key()
    if not api_key:
        raise AIServiceError("Configura prima la chiave API OpenAI.")

    client = OpenAI(api_key=api_key)
    model = get_configured_model()
    prompt = _build_prompt(context)

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
        )
    except Exception as exc:
        raise AIServiceError(f"Errore chiamando OpenAI: {exc}") from exc

    text = getattr(response, "output_text", "") or ""
    parsed = _parse_response(text)
    if not parsed["opening_text"] and not parsed["included_items_text"]:
        raise AIServiceError("Risposta AI non valida o vuota.")
    return parsed


def _get_api_key() -> str:
    return str(get_setting(API_KEY_SETTING, "") or os.getenv("OPENAI_API_KEY", ""))


def _build_prompt(context: Dict[str, str]) -> str:
    return f"""
Sei un assistente commerciale italiano specializzato nella scrittura di preventivi industriali per manutenzione e multiservizi.

Genera una risposta in italiano con questo formato esatto:
OPENING_TEXT:
<testo introduttivo>
INCLUDED_ITEMS:
<punto 1>
<punto 2>
<punto 3>
...

Vincoli:
- Tono professionale, chiaro e commerciale.
- Non inventare prezzi, tempi o condizioni non presenti.
- Non aggiungere saluti finali.
- I punti in INCLUDED_ITEMS devono essere una riga per punto, senza numerazione.
- Se i dati sono scarsi, scrivi comunque un testo prudente e generico ma utile.

Dati preventivo:
Cliente: {context.get('client_name', '')}
Referente: {context.get('client_contact_person', '')}
Oggetto: {context.get('title', '')}
Sede lavoro: {context.get('work_site', '')}
Descrizione generale: {context.get('description', '')}
Righe lavoro: {context.get('items_summary', '')}
Punti già inseriti: {context.get('included_items_text', '')}
""".strip()


def _parse_response(text: str) -> Dict[str, str]:
    opening_text = ""
    included_items_text = ""

    if "OPENING_TEXT:" in text:
        opening_part = text.split("OPENING_TEXT:", 1)[1]
        if "INCLUDED_ITEMS:" in opening_part:
            opening_text, included_items_text = opening_part.split("INCLUDED_ITEMS:", 1)
        else:
            opening_text = opening_part
    elif "INCLUDED_ITEMS:" in text:
        included_items_text = text.split("INCLUDED_ITEMS:", 1)[1]
    else:
        opening_text = text

    return {
        "opening_text": opening_text.strip(),
        "included_items_text": _normalize_items(included_items_text.strip()),
    }


def _normalize_items(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip().lstrip("-*	 .")
        if line:
            lines.append(line)
    return "\n".join(lines)
