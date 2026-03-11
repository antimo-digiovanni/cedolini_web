from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


PAYMENT_PENDING = "Pending"
PAYMENT_PAID = "Pagato"
PAYMENT_STATUSES = [PAYMENT_PENDING, PAYMENT_PAID]

QUOTE_TO_CONFIRM = "Da confermare"
QUOTE_CONFIRMED = "Confermato"
QUOTE_WORK_DONE = "Lavoro fatto"
QUOTE_STATUSES = [QUOTE_TO_CONFIRM, QUOTE_CONFIRMED, QUOTE_WORK_DONE]


@dataclass
class QuoteInput:
    progressive_number: int
    client_name: str
    client_contact_person: str
    client_email: str
    client_phone: str
    client_address: str
    offer_date: str
    recipient_attention: str
    work_site: str
    title: str
    description: str
    opening_text: str
    included_items_text: str
    amount: float
    payment_reference: str
    payment_status: str
    quote_status: str
    notes: str = ""
    closing_text: str = ""
    signature_name: str = ""
    include_discount_note: bool = False
    items: list["QuoteItemInput"] = field(default_factory=list)


@dataclass
class ClientInput:
    name: str
    contact_person: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""


@dataclass
class QuoteItemInput:
    description: str
    quantity: float
    unit_price: float

    @property
    def total_amount(self) -> float:
        return round(self.quantity * self.unit_price, 2)


@dataclass
class QuoteRecord:
    id: int
    progressive_number: int
    quote_code: str
    client_name: str
    client_contact_person: str
    client_email: str
    client_phone: str
    client_address: str
    offer_date: str
    recipient_attention: str
    work_site: str
    title: str
    description: str
    opening_text: str
    included_items_text: str
    amount: float
    payment_reference: str
    payment_status: str
    quote_status: str
    notes: str
    closing_text: str
    signature_name: str
    include_discount_note: bool
    pdf_path: Optional[Path]
    excel_path: Optional[Path]
    created_at: str
    updated_at: str
