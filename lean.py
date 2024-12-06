#!/usr/bin/python3
import json
import logging
import os
import platform
import sys
from datetime import datetime
from time import perf_counter

import requests


def load_config():
    # Load the base configuration
    with open("config.json", "r") as base_config_file:
        config = json.load(base_config_file)

    # Check if running on Windows and if the dev config exists
    if platform.system() == "Windows" and os.path.exists("config.dev.json"):
        with open("config.dev.json", "r") as dev_config_file:
            dev_config = json.load(dev_config_file)
            # Merge configurations (dev values override base values)
            config.update(dev_config)

    return config


def validate_config(config):
    required_keys = ["directory_base", "log_files", "csv_url", "max_price", "expected_fields_count"]
    for key in required_keys:
        if key not in config:
            raise KeyError(f"Missing required configuration: {key}")
    if not isinstance(config["log_files"], list):
        raise TypeError("log_files must be a list of file paths")
    if not os.path.exists(config["directory_base"]):
        raise FileNotFoundError(f"Base directory does not exist: {config['directory_base']}")


CONFIG = load_config()
validate_config(CONFIG)

BASE_DIR = CONFIG["directory_base"]
LOG_FILES = CONFIG["log_files"]
CSV_URL = CONFIG["csv_url"]
MAX_PRICE = CONFIG["max_price"]
EXPECTED_FIELDS_COUNT = CONFIG["expected_fields_count"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(os.path.join(BASE_DIR, log_file)) for log_file in LOG_FILES] + [logging.StreamHandler()]
)


def main(ukljuci_neslobodne: bool = False):
    parsiraj_csv(ukljuci_neslobodne=ukljuci_neslobodne)


def parsiraj_csv(ukljuci_neslobodne: bool = False):
    start = perf_counter()
    errors = ""
    nepotpuni = []
    logging.debug("Debug: ", os.getcwd())
    # Download the CSV file
    r = requests.get(CSV_URL, stream=True)
    with open(os.path.join(BASE_DIR, 'ponip_ocevidnik.csv'), 'wb') as file:
        file.write(r.content)
    with open(os.path.join(BASE_DIR, 'idevi')) as f:
        id_evi = f.read().splitlines()
    logging.debug(id_evi)
    # Open the CSV file
    with open(os.path.join(BASE_DIR, 'ponip_ocevidnik.csv'), 'r', encoding='utf-8') as f:

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
                    continue

                # Datum i vrijeme početka nadmetanja
                if datetime.strptime(fields[13][1:-1], "%Y-%m-%d %H:%M:%S") < datetime.today():
                    continue

                # Je li već korišten
                if fields[8] in id_evi:
                    continue

                # Napomena uz detalje predmeta prodaje
                if not ukljuci_neslobodne:
                    if "nije slobodna" in fields[6]:
                        continue

                # Opis
                gradovi = ["Split", "Zagreb", "Omiš", "Trogir", "Klis", "Dicmo", "Kaštel", "Klinča", "Pisarovina",
                           "Jastrebarsko", "Samobor", "Nedelja", "Zaprešić", "Dugi Rat", "Solin", "Sesvete", "Lužan",
                           "Klara"]
                if not any(grad in fields[2][1:-1] for grad in gradovi):
                    continue

                vrsta_nekretnine = ["kuća", "stan", "Stan", "Kuća", "nekretnina", "Nekretnina", "Poslovni", "poslovni"]
                if not any(vrsta in fields[2][1:-1] for vrsta in vrsta_nekretnine):
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

            # send_to_telegram(content=f"Novo na PONIP scraperu:\n{result}",
            #                  ukljuci_neslobodne=ukljuci_neslobodne)
            logging.debug("result = ", result)
            logging.debug("errors = ", errors)

        footer = f"Counter: {counter} | Errors: {error_counter} | Performance: {perf_counter() - start} s\n"
        footer += "https://ponip.fina.hr/ocevidnik-web/pretrazivanje/nekretnina"

        logging.info(str(datetime.now()) + " " + footer.split('\n')[0])
        logging.info(f"Nepotpuni: {len(nepotpuni)}")

        with open(f"{BASE_DIR}idevi", mode="wt") as fi:
            for identifikator in id_evi:
                fi.write(identifikator + "\n")

        if error_counter:
            send_to_telegram(content=f"Greške na 'PONIP' scraperu:\n{errors}\n{footer}",
                             ukljuci_neslobodne=ukljuci_neslobodne)

        if counter:
            # send_to_telegram(content=footer, ukljuci_neslobodne=ukljuci_neslobodne)
            print(f"[MM] {footer}")


def send_to_telegram(content, ukljuci_neslobodne: bool = False):
    import creds

    if not ukljuci_neslobodne:
        api_token = creds.TELEGRAM_API_TOKEN_PONIP
    else:
        api_token = creds.TELEGRAM_API_TOKEN_PONIP_OCCUPIED
    chat_id = creds.TELEGRAM_CHAT_ID

    api_url = f"https://api.telegram.org/bot{api_token}/sendMessage"

    try:
        response = requests.post(api_url, json={'chat_id': chat_id, 'text': content})
        logging.debug(response.text)
    except Exception as e:
        logging.error(e)


if __name__ == '__main__':
    ukljuci_neslobodne = False
    if len(sys.argv) > 2:
        raise ValueError("Previse argumenata!")
    if len(sys.argv) == 2:
        param_1 = eval(sys.argv[1])
        if not isinstance(param_1, bool):
            raise TypeError("Argument nije boolean!")
        else:
            ukljuci_neslobodne = param_1
    main(ukljuci_neslobodne=ukljuci_neslobodne)
