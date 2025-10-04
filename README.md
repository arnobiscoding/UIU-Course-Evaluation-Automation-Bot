# UIU Course Evaluation Automation

A small, pragmatic Selenium script to automate filling the UIU (UCAM) Course Evaluation form.

I made this because course evaluations felt monotonous and repetitive — this tool does the boring parts for you so you can focus on real feedback.

This repository contains a single Python script that logs into the UCAM dashboard, navigates to the Course Evaluation page, selects each course, sets the expected grade to "A", chooses "Strongly Agree" for evaluation questions, and submits the form. It includes robust waits and retry strategies for the ASP.NET UpdatePanel-driven page.

> Free for all to use. Use responsibly and in accordance with your institution's policies.

---

## Highlights

- Logs in using credentials from a `.env` file.
- Navigates to the Course Evaluation page automatically.
- Selects each course and sets Expected Grade = `A`.
- Chooses the highest option (Strongly Agree) for all radio questions.
- Submits evaluations and retries when partial postbacks or transient errors occur.
- Writes a compact `completed_courses.json` audit log summarizing each course processed.

---

## Requirements

- Windows (tested)
- Python 3.10+ (your environment shows Python 3.13)
- Chrome browser installed

The included `requirements.txt` lists the Python dependencies (Selenium, webdriver-manager, python-dotenv).

---

## Quick start (PowerShell)

1. Clone or download this repository and open a PowerShell terminal in the folder.

2. Create and activate a virtual environment (recommended):

    ```powershell
    python -m venv .venv
    & .\.venv\Scripts\Activate.ps1
    ```

3. Create a `.env` file in the project root with your credentials and optional flags:

    ```ini
    USER_ID=your_uiu_user
    PASSWORD=your_password
    # Optional: set HEADLESS=0 to run with a visible browser for debugging
    HEADLESS=1
    ```

4. Install dependencies:

    ```powershell
    python -m pip install -r requirements.txt
    ```

5. Run the script:

    ```powershell
    python -u "./bot_login.py"
    ```

The script logs progress to the console. By default it runs headless (no browser window). Set `HEADLESS=0` in `.env` to see the browser while it runs.

---

## Files

- `bot_login.py` — main automation script.
- `requirements.txt` — dependencies.

---

## Configuration

- `USER_ID` and `PASSWORD` (required) — UCAM credentials used for login.
- `HEADLESS` (optional) — set to `0` to run with a visible browser; default is `1` (headless).

The script will write `completed_courses.json` with a summary of what it did. If you'd prefer not to keep that file, delete it after a run or ask me and I can make logging optional.

---

## Troubleshooting & Tips

- If ChromeDriver fails to start, ensure your local Chrome is up to date. The script uses `webdriver-manager` to download a compatible driver automatically.
- If the script times out waiting for page elements, try running with `HEADLESS=0` to watch the browser and identify where it gets stuck.
- The UI uses ASP.NET UpdatePanels which can replace DOM fragments after every selection; the script includes retry/wait logic to handle that, but network slowness or very slow server responses may still require increasing some wait timeouts in the script.

---

## Contributing & License

This project is intentionally small and single-purpose. If you'd like improvements (options, dry-run, skipping submit, or making the audit log optional), open an issue or a PR. Use it responsibly — the author is not responsible for misuse.

This repository is provided under the MIT License (use and modify freely).

---

If you'd like, I can:

- Make `completed_courses.json` optional via an environment flag.
- Add a `--dry-run` CLI mode that navigates and reports actions without clicking submit.
- Add a short troubleshooting GIF or screenshots to the README (if you provide one).

Which of these (if any) would you like next?
