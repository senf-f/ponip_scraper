#!/usr/bin/python3

import os
import sys
from datetime import datetime
from time import perf_counter

import requests
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from configurator import load_config, validate_config
from data import Nekretnina, Base  # Updated for SQLAlchemy ORM integration

# Load and validate configuration
CONFIG = load_config()
validate_config(CONFIG)

load_dotenv()
# Detect environment (default to development)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
# Set database URL based on the environment
if ENVIRONMENT == "production":
    DATABASE_URL = os.getenv("DATABASE_URL")
else:
    DATABASE_URL = f"sqlite:///{os.getcwd()}/test_database.db"
# Database configuration
engine = create_engine(DATABASE_URL)

logger.debug(f"[M] DATABASE_URL={DATABASE_URL}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

BASE_DIR = CONFIG["directory_base"]
LOG_FILES = CONFIG["log_files"]
CSV_URL = CONFIG["csv_url"]
MAX_PRICE = CONFIG["max_price"]
EXPECTED_FIELDS_COUNT = CONFIG["expected_fields_count"]
GRADOVI = CONFIG["gradovi"]
VRSTA_NEKRETNINE = CONFIG["vrsta_nekretnine"]

# Configure logging using loguru
logger.add(LOG_FILES, rotation="1 year")
logger.add(sys.stdout, format="{time} {level} {message}", level="INFO")


def parsiraj_csv():
    start = perf_counter()
    errors = ""
    nepotpuni = []
    logger.info(f"[*] Current directory: {os.getcwd()}")

    # Download the CSV file
    r = requests.get(CSV_URL, stream=True)
    csv_path = os.path.join(BASE_DIR, 'ponip_ocevidnik.csv').replace("\\", "/")
    with open(csv_path, 'wb') as file:
        file.write(r.content)

    with open(os.path.join(BASE_DIR, 'idevi')) as f:
        id_evi = f.read().splitlines()

    # Open a database session
    session = SessionLocal()

    try:
        # Open the CSV file
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip first line (header)
            next(f)
            counter = 0
            error_counter = 0

            # Iterate over the lines
            for count, line in enumerate(f):
                # Split the line on the comma separator
                fields = line.strip().split(';')

                try:
                    # Nepotpuni podaci
                    if len(fields) != 26 or fields[13] == "":
                        nepotpuni += [fields]
                        ## MM kako hendlati nepotpune
                        continue

                    # Datum i vrijeme početka nadmetanja
                    if datetime.strptime(fields[13][1:-1], "%Y-%m-%d %H:%M:%S") < datetime.today():
                        continue

                    # Je li već korišten
                    if fields[8] in id_evi:
                        continue

                    # Opis
                    if not any(grad in fields[2][1:-1] for grad in GRADOVI):
                        continue

                    if not any(vrsta in fields[2][1:-1] for vrsta in VRSTA_NEKRETNINE):
                        continue

                    # Minimalna zakonska cijena ispod koje se predmet prodaje ne može prodati
                    if float(fields[16][1:-1]) > MAX_PRICE:
                        continue

                    counter += 1

                except ValueError as err:
                    # Debug dio zbog neujednačenog formatiranja
                    errors += f"\nID: {fields[8]} | Error: {err}"
                    error_counter += 1
                    continue

                # Create a Nekretnina instance
                item = Nekretnina(
                    nadlezno_tijelo=fields[0],
                    poslovni_broj=fields[1],
                    opis=fields[2][1:-1],
                    vrsta_predmeta=fields[3],
                    opseg_imovine=fields[4],
                    utvrdjena_vrijednost=float(fields[5]),
                    napomena_uz_detalje=fields[6],
                    id=int(fields[8]),
                    broj_drazbe=fields[9],
                    datum_odluke=datetime.strptime(fields[10][1:-1], "%Y-%m-%d"),
                    datum_pocetka=datetime.strptime(fields[11][1:-1], "%Y-%m-%d %H:%M:%S"),
                    datum_pocetka_nadmetanja=datetime.strptime(fields[12][1:-1], "%Y-%m-%d %H:%M:%S"),
                    datum_zavrsetka_nadmetanja=datetime.strptime(fields[13][1:-1], "%Y-%m-%d %H:%M:%S"),
                    ostali_uvjeti_prodaje=fields[15],
                    min_cijena=float(fields[16][1:-1]),
                    pocetna_cijena=float(fields[17]),
                    iznos_drazbenog_koraka=float(fields[18]),
                    jamcevina=float(fields[20]),
                    ostali_uvjeti_za_jamcevinu=fields[21],
                    razgledavanje=fields[22],
                    napomena_uz_uvjete_prodaje=fields[23]
                )

                # Add to database
                session.merge(item)
                id_evi.append(fields[8])

                # Notify and log the result
                result = f"ID: {item.id} | Opis: {item.opis} | Cijena: {item.pocetna_cijena}"
                send_to_telegram(content=f"Novo na PONIP scraperu:\n{result}")
                logger.info(result)

            # Commit all changes to the database
            session.commit()

        footer = f"Counter: {counter} | Errors: {error_counter} | Performance: {perf_counter() - start} s\n"
        footer += "https://ponip.fina.hr/ocevidnik-web/pretrazivanje/nekretnina"
        logger.info(footer)

        # Update processed IDs
        with open(f"{BASE_DIR}idevi", mode="wt") as fi:
            fi.write("\n".join(id_evi))

        if error_counter:
            send_to_telegram(content=f"Greške na 'PONIP' scraperu:\n{errors}\n{footer}")

    finally:
        session.close()


def send_to_telegram(content):
    import creds

    api_token = creds.TELEGRAM_API_TOKEN_PONIP
    chat_id = creds.TELEGRAM_CHAT_ID

    api_url = f"https://api.telegram.org/bot{api_token}/sendMessage"

    try:
        response = requests.post(api_url, json={'chat_id': chat_id, 'text': content}, timeout=10)
        response.raise_for_status()
        logger.info("Telegram message sent successfully.")
    except requests.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")


def initialize_database():
    logger.info("[M] Initializing database...")
    Base.metadata.create_all(engine)
    logger.info("[M] Database initialized.")


if __name__ == '__main__':
    initialize_database()
    parsiraj_csv()
