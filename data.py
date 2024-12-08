from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Nekretnina:
    nadlezno_tijelo: str
    poslovni_broj: str
    opis: str
    vrsta_predmeta: str
    opseg_imovine: str
    utvrdjena_vrijednost: float
    napomena_uz_detalje: str
    id_nadmetanja: int
    broj_drazbe: str
    datum_odluke: datetime
    datum_pocetka: datetime
    datum_pocetka_nadmetanja: datetime
    datum_zavrsetka_nadmetanja: datetime
    ostali_uvjeti_prodaje: Optional[str]
    min_cijena: float
    pocetna_cijena: float
    iznos_drazbenog_koraka: float
    jamcevina: float
    ostali_uvjeti_za_jamcevinu: Optional[str]
    razgledavanje: Optional[str]
    napomena_uz_uvjete_prodaje: Optional[str]
    iznos_najvise_ponude: Optional[str] = None
    status_nadmetanja: Optional[str] = None

