"""SQLAlchemy ORM models for the Zenoti data warehouse."""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ------------------------------------------------------------------ #
# Dimension tables
# ------------------------------------------------------------------ #

class DimCenter(Base):
    __tablename__ = "dim_centers"

    id = Column(String, primary_key=True)
    name = Column(String)
    code = Column(String)
    city = Column(String)
    country = Column(String)
    currency_id = Column(Integer)
    time_zone = Column(String)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DimGuest(Base):
    __tablename__ = "dim_guests"

    id = Column(String, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    mobile = Column(String)
    gender = Column(Integer)
    date_of_birth = Column(String)
    center_id = Column(String, ForeignKey("dim_centers.id"))
    created_date = Column(String)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DimEmployee(Base):
    __tablename__ = "dim_employees"

    id = Column(String, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    code = Column(String)
    designation = Column(String)
    center_id = Column(String, ForeignKey("dim_centers.id"))
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DimService(Base):
    __tablename__ = "dim_services"

    id = Column(String, primary_key=True)
    name = Column(String)
    code = Column(String)
    category_name = Column(String)
    duration_minutes = Column(Integer)
    base_price = Column(Float)
    center_id = Column(String, ForeignKey("dim_centers.id"))
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ------------------------------------------------------------------ #
# Fact tables
# ------------------------------------------------------------------ #

class FactAppointment(Base):
    __tablename__ = "fact_appointments"

    id = Column(String, primary_key=True)
    center_id = Column(String, ForeignKey("dim_centers.id"))
    appointment_group_id = Column(String)
    guest_id = Column(String, ForeignKey("dim_guests.id"), nullable=True)
    service_id = Column(String, ForeignKey("dim_services.id"), nullable=True)
    therapist_id = Column(String, ForeignKey("dim_employees.id"), nullable=True)
    start_time = Column(String)
    end_time = Column(String)
    status = Column(Integer)  # 0=booked,1=confirmed,2=checkedin,3=closed,4=noshow,5=cancelled
    price = Column(Float)
    created_date = Column(String)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FactInvoice(Base):
    __tablename__ = "fact_invoices"

    id = Column(String, primary_key=True)
    invoice_number = Column(String)
    center_id = Column(String, ForeignKey("dim_centers.id"))
    guest_id = Column(String, ForeignKey("dim_guests.id"), nullable=True)
    appointment_id = Column(String, ForeignKey("fact_appointments.id"), nullable=True)
    total_price = Column(Float)
    total_tax = Column(Float)
    total_discount = Column(Float)
    final_price = Column(Float)
    status = Column(Integer)
    created_date = Column(String)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("FactInvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class FactInvoiceItem(Base):
    __tablename__ = "fact_invoice_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String, ForeignKey("fact_invoices.id"))
    item_id = Column(String)
    item_type = Column(Integer)  # 1=service,2=product,3=membership,4=package,5=giftcard
    name = Column(String)
    quantity = Column(Float)
    unit_price = Column(Float)
    final_price = Column(Float)
    discount = Column(Float)
    tax = Column(Float)

    invoice = relationship("FactInvoice", back_populates="items")


# ------------------------------------------------------------------ #
# Sync metadata
# ------------------------------------------------------------------ #

class SyncLog(Base):
    __tablename__ = "sync_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity = Column(String)          # centers|guests|employees|services|appointments|invoices
    center_id = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    records_synced = Column(Integer, default=0)
    status = Column(String)          # running|success|error
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
