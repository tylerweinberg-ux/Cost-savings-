"""Pydantic models matching Zenoti API response shapes."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ZenotiCenter(BaseModel):
    id: str
    name: str
    code: str | None = None
    city: str | None = None
    country: str | None = None
    currency_id: int | None = None
    time_zone: str | None = None


class ZenotiGuest(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    mobile: str | None = None
    gender: int | None = None  # 0=unknown,1=male,2=female
    date_of_birth: str | None = None
    center_id: str | None = None
    created_date: str | None = None


class ZenotiEmployee(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    code: str | None = None
    designation: str | None = None
    center_id: str | None = None


class ZenotiService(BaseModel):
    id: str
    name: str | None = None
    code: str | None = None
    category_name: str | None = None
    duration: int | None = None  # minutes
    price: dict[str, Any] | None = None
    center_id: str | None = None


class ZenotiAppointmentGuest(BaseModel):
    guest_id: str | None = None
    service_id: str | None = None
    service_name: str | None = None
    therapist_id: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    price: float | None = None
    status: int | None = None


class ZenotiAppointment(BaseModel):
    id: str
    center_id: str | None = None
    appointment_group_id: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    status: int | None = None
    appointment_services: list[ZenotiAppointmentGuest] = Field(default_factory=list)
    created_date: str | None = None


class ZenotiInvoiceItem(BaseModel):
    item_id: str | None = None
    item_type: int | None = None  # 1=service,2=product,3=membership,...
    name: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    final_price: float | None = None
    discount: float | None = None
    tax: float | None = None


class ZenotiInvoice(BaseModel):
    id: str
    invoice_number: str | None = None
    center_id: str | None = None
    guest_id: str | None = None
    appointment_id: str | None = None
    total_price: float | None = None
    total_tax: float | None = None
    total_discount: float | None = None
    final_price: float | None = None
    created_date: str | None = None
    invoice_items: list[ZenotiInvoiceItem] = Field(default_factory=list)
    status: int | None = None
