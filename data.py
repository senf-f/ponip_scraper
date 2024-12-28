from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

# Base class for all SQLAlchemy models
Base = declarative_base()


# Nekretnina model mapped to the properties table
@dataclass
class Nekretnina(Base):
    __tablename__ = "properties"  # Specifies the database table name

    # Column definitions
    id_nadmetanja: int = Column(Integer, primary_key=True)  # Primary key, scraped from data
    nadlezno_tijelo: str = Column(Text, nullable=False)
    poslovni_broj: str = Column(String, nullable=False)
    opis: str = Column(Text, nullable=False)
    vrsta_predmeta: str = Column(Text, nullable=False)
    opseg_imovine: str = Column(Text, nullable=False)
    utvrdjena_vrijednost: float = Column(Float, nullable=False)
    napomena_uz_detalje: str = Column(Text, nullable=True)
    broj_drazbe: str = Column(String, nullable=False)
    datum_odluke: datetime = Column(DateTime, nullable=False)
    datum_pocetka: datetime = Column(DateTime, nullable=False)
    datum_pocetka_nadmetanja: datetime = Column(DateTime, nullable=False)
    datum_zavrsetka_nadmetanja: datetime = Column(DateTime, nullable=False)
    ostali_uvjeti_prodaje: str = Column(Text, nullable=True)
    min_cijena: float = Column(Float, nullable=False)
    pocetna_cijena: float = Column(Float, nullable=False)
    iznos_drazbenog_koraka: float = Column(Float, nullable=False)
    jamcevina: float = Column(Float, nullable=False)
    ostali_uvjeti_za_jamcevinu: str = Column(Text, nullable=True)
    razgledavanje: str = Column(Text, nullable=True)
    napomena_uz_uvjete_prodaje: str = Column(Text, nullable=True)
