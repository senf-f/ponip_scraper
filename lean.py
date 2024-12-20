#!/usr/bin/python3
import logging
import os
from datetime import datetime
from time import perf_counter

import requests

from configurator import load_config, validate_config
from data import Nekretnina

CONFIG = load_config()
validate_config(CONFIG)

BASE_DIR = CONFIG["directory_base"]
LOG_FILES = CONFIG["log_files"]
CSV_URL = CONFIG["csv_url"]
MAX_PRICE = CONFIG["max_price"]
EXPECTED_FIELDS_COUNT = CONFIG["expected_fields_count"]
GRADOVI = CONFIG["gradovi"]
VRSTA_NEKRETNINE = CONFIG["vrsta_nekretnine"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(os.path.join(BASE_DIR, log_file).replace("\\", "/")) for log_file in LOG_FILES] + [
        logging.StreamHandler()]
)


def parsiraj_csv():
    start = perf_counter()
    errors = ""
    nepotpuni = []
    data_items = []
    logging.info(f"[*] Current directory: {os.getcwd()}")

    # Download the CSV file
    r = requests.get(CSV_URL, stream=True)
    csv_path = os.path.join(BASE_DIR, 'ponip_ocevidnik.csv').replace("\\", "/")
    with open(csv_path, 'wb') as file:
        file.write(r.content)

    with open(os.path.join(BASE_DIR, 'idevi')) as f:
        id_evi = f.read().splitlines()

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

            # Process the line
            result = "---------------------------------------"
            result += f"\nID: {fields[8]} | Početna cijena: {fields[17]} | Oznaka EJD: {fields[9]} | Poslovni broj spisa: {fields[1]}"
            result += "\n---------------------------------------"
            result += f"\nOpis: {fields[2]}"
            result += f"\nNapomena: {fields[6]}"
            result += f"\nDatum početka i završetka nadmetanja: {fields[12]} - {fields[13]}"
            result += f"\nRazgledavanje: {fields[22]}"
            result += f"\nDodatna napomena: {fields[23]}"
            id_evi.append(fields[8])

            # Create a RealEstateItem instance
            item = Nekretnina(
                nadlezno_tijelo=fields[0],
                poslovni_broj=fields[1],
                opis=fields[2][1:-1],
                vrsta_predmeta=fields[3],
                opseg_imovine=fields[4],
                utvrdjena_vrijednost=float(fields[5]),
                napomena_uz_detalje=fields[6],
                id_nadmetanja=int(fields[8]),
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

            # Add to list for further processing
            data_items.append(item)

            send_to_telegram(content=f"Novo na PONIP scraperu:\n{result}")
            logging.info(f"{result=}")

        footer = f"Counter: {counter} | Errors: {error_counter} | Performance: {perf_counter() - start} s\n"
        footer += "https://ponip.fina.hr/ocevidnik-web/pretrazivanje/nekretnina"

        logging.info(str(datetime.now()) + " " + footer.split('\n')[0])

        with open(f"{BASE_DIR}idevi", mode="wt") as fi:
            fi.write("\n".join(id_evi))

        if error_counter:
            send_to_telegram(content=f"Greške na 'PONIP' scraperu:\n{errors}\n{footer}")

        if counter:
            send_to_telegram(content=footer)


def send_to_telegram(content):
    import creds

    api_token = creds.TELEGRAM_API_TOKEN_PONIP
    chat_id = creds.TELEGRAM_CHAT_ID

    api_url = f"https://api.telegram.org/bot{api_token}/sendMessage"

    try:
        response = requests.post(api_url, json={'chat_id': chat_id, 'text': content}, timeout=10)
        response.raise_for_status()
        logging.info("Telegram message sent successfully.")
    except requests.RequestException as e:
        logging.error(f"Failed to send Telegram message: {e}")


if __name__ == '__main__':
    parsiraj_csv()
