# 2FA Brute-Force Bypass (Broken Rate-Limiting)

A Python script that automates bypassing broken brute-force protection on a
2FA verification flow, developed while solving an expert-level lab from
PortSwigger's Web Security Academy.

## Objective

The objective of this project is to bypass a two-factor authentication
mechanism whose brute-force protection is poorly implemented. The application
allows only 2 code attempts (4 digits) per session before invalidating it,
requiring re-authentication (a new login) to obtain a new code — however, it
imposes no limit on how many times this login cycle can be repeated. This flaw
allows the entire cycle (login + 2 attempts) to be automated sequentially,
making success purely a matter of time, since each repetition carries a fixed
chance (2 in 10,000) of guessing the code correctly.

## How It Works

Basic flow, repeated in a loop until a 302 redirect confirms success:

1. `POST /login` with valid credentials, using the CSRF token from the prior response
2. Follow the redirect to `/login2`, extracting a fresh CSRF token from the form
3. Attempt up to 2 verification codes against `/login2`, advancing sequentially through the code space (with wraparound)
4. On lockout (2 wrong attempts), extract the new CSRF token embedded in the returned login form
5. Repeat from step 1, resuming from the last tested code index
6. On success (`302`), confirm authentication with a `GET /my-account` request

Parallelization was deliberately ruled out: the target application maintains
only one pending 2FA challenge per account at a time, so concurrent login
cycles would invalidate one another instead of increasing throughput.

## Technologies Used

- Python
- `requests` (with `requests.Session()` for automatic cookie/session persistence)
- `argparse` for CLI configuration
- `logging` for structured, timestamped output to both console and file
- `re` for CSRF token extraction

## Features

- Fully automated re-authentication cycling to bypass session-scoped brute-force protection
- Sequential code testing with automatic wraparound across the 0000–9999 space
- Differentiated error handling: transient network errors trigger a retry, while unexpected application responses raise immediately, avoiding a silent, wasted execution over a multi-hour run
- Structured logging (timestamped, file + console) for auditing long-running attacks
- Automatic post-success verification via `/my-account`

## Usage

```bash
pip install -r requirements.txt
python src/main.py --target https://<lab-id>.web-security-academy.net
```

Credentials are fixed as module-level constants (`USERNAME`, `PASSWORD` in
`src/main.py`), since they are static for this lab's account (`carlos`).

## Results

A full run against the live lab instance succeeded in **40 minutes and 44
seconds**, across **531 login cycles**, finding the valid code at `1061`
(out of the 0000–9999 space). This is faster than the statistical expectation
(~5,000 cycles on average, per a geometric distribution with p = 2/10,000
per cycle) — the actual run got a favorable early draw. A worst-case or
unlucky run could reasonably take several hours; total time is inherently
probabilistic, not fixed.

## Example Output

```
2026-09-21 15:41:23,705 | Testing code 0000...
2026-09-21 15:41:23,706 | Code failed!
2026-09-21 15:41:24,870 | Testing code 0001...
2026-09-21 15:41:24,870 | Code failed!
2026-09-21 15:41:24,874 | [Cycle 1] 4.61s | actual index: 2

...

2026-09-21 16:22:05,181 | Testing code 1060...
2026-09-21 16:22:05,181 | Code failed!
2026-09-21 16:22:06,311 | Testing code 1061...
2026-09-21 16:22:06,311 | Success! Code: 1061
2026-09-21 16:22:07,508 | [/my-account] status: 200 | confirmed: True
2026-09-21 16:22:07,512 | [Cycle 531] 5.73s | actual index: None
2026-09-21 16:22:07,512 | Authenticated session cookie: UoRaCCbmGu6YjaA8CJHkKlHMjGqUsxpL
```

Full log available at [`docs/run-success-2026-09-21.log`](./docs/run-success-2026-09-21.log).


## Project Structure

```
2fa-bruteforce-bypass-python/
├── src/
│   └── main.py
├── docs/
│   ├── codes.txt
│   ├── run-success-2026-09-21.log
├── README.md
├── .gitignore
└── LICENSE
```

## Learning Goals

- Identifying and exploiting logic flaws in session-scoped brute-force protections
- HTTP session and CSRF token lifecycle management with `requests.Session()`
- Regex-based token extraction from HTML responses
- Probabilistic modeling of brute-force success under a geometric distribution
- Structured logging and error-handling strategy for long-running network automation

## Limitations

- Assumes fixed, known-valid credentials (no credential brute-forcing)
- Sequential by design — not applicable to targets without the "one pending challenge per account" constraint that makes parallelization counterproductive here
- No checkpoint/resume mechanism: an interrupted run loses in-memory progress (index, CSRF token) and must restart from the beginning

## License

MIT — see [LICENSE](./LICENSE).

## Legal Notice

This tool was developed strictly for educational purposes against a
PortSwigger Web Security Academy lab instance under a personal, authorized
account. Do not use against systems you do not own or have explicit
authorization to test.