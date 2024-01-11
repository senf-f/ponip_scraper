#!/usr/bin/python3
import os
from datetime import datetime
from time import perf_counter
import requests
import logging


directory_base = "/opt/ponip_scraper/"  # za dev izvrsavanje: ""

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{directory_base}ponip_scraped.log"),
        logging.FileHandler("/var/log/scrapers/ponip_scrape_log.txt"),
        logging.StreamHandler()
    ]
)


def main():
    start = perf_counter()
    errors = ""
    nepotpuni = []

    logging.debug("Debug: ", os.getcwd())

    # Download the CSV file
    url = "https://ponip.fina.hr/ocevidnik-web/preuzmi/csv"
    r = requests.get(url, stream=True)
    with open(f'{directory_base}ponip_ocevidnik.csv', 'wb')as file:
        file.write(r.content)

    with open(f'{directory_base}idevi') as f:
        id_evi = f.read().splitlines()

    logging.debug(id_evi)

    # Open the CSV file
    with open(f'{directory_base}ponip_ocevidnik.csv', 'r', encoding='utf-8') as f:

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
                if "nije slobodna" in fields[6]:
                    continue

                # Opis
                gradovi = ["Split", "Zagreb", "Omiš", "Trogir", "Klis", "Dicmo", "Kaštel", "Klinča", "Pisarovina", "Jastrebarsko", "Samobor", "Nedelja", "Zaprešić", "Dugi Rat", "Solin", "Sesvete", "Lužan", "Klara"]
                if not any(grad in fields[2][1:-1] for grad in gradovi):
                    continue

                vrsta_nekretnine = ["kuća", "stan", "Stan", "Kuća", "nekretnina", "Nekretnina", "Poslovni", "poslovni"]
                if not any(vrsta in fields[2][1:-1] for vrsta in vrsta_nekretnine):
                    continue

                # Minimalna zakonska cijena ispod koje se predmet prodaje ne može prodati
                if float(fields[16][1:-1]) > 200000:
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

            send_to_telegram(f"Novo na PONIP scraperu:\n{result}")
            logging.debug("result = ", result)
            logging.debug("errors = ", errors)

        footer = f"Counter: {counter} | Errors: {error_counter} | Performance: {perf_counter() - start} s\n"
        footer += "https://ponip.fina.hr/ocevidnik-web/pretrazivanje/nekretnina"

        logging.info(str(datetime.now()) + " " + footer.split('\n')[0])
        logging.info(f"Nepotpuni: {len(nepotpuni)}")

        with open(f"{directory_base}idevi", mode="wt") as fi:
            for identifikator in id_evi:
                fi.write(identifikator + "\n")

        if error_counter:
            send_to_telegram(f"Greške na PONIP scraperu:\n{errors}\n{footer}")

        if counter:
            send_to_telegram(footer)


def send_to_telegram(content):

    import creds

    api_token = creds.TELEGRAM_API_TOKEN_PONIP
    chat_id = creds.TELEGRAM_CHAT_ID

    api_url = f"https://api.telegram.org/bot{api_token}/sendMessage"

    try:
        response = requests.post(api_url, json={'chat_id': chat_id, 'text': content})
        logging.debug(response.text)
    except Exception as e:
        logging.error(e)


if __name__ == '__main__':
    main()
