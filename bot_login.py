"""
bot_login.py

Lightweight script that performs login/auth to the UCAM dashboard using Selenium.
This file reproduces the login part of `bot_v0.py` in a small, reusable script.

Usage:
  - Create a `.env` file with USER_ID and PASSWORD (and optional TELEGRAM vars if needed later)
  - Install requirements from `requirements.txt`
  - Run: python bot_login.py

The script returns exit code 0 on successful login and non-zero on failure.
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import os
import sys
from dotenv import load_dotenv
import json
from datetime import datetime
import logging

# Load environment variables from .env
load_dotenv()

LOGIN_URL = 'https://ucam.uiu.ac.bd/Security/Login.aspx'


def create_driver(headless: bool = True, window_size: str = "1920,1080"):
    """Create and return a Chrome WebDriver and a default WebDriverWait.

    Returns (driver, wait)
    """
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument(f'--window-size={window_size}')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-notifications')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 15)
    return driver, wait


# Configure simple console logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def login_ucam(driver, user_id: str, password: str, wait: WebDriverWait, max_retries: int = 3) -> bool:
    """Attempt to log in to UCAM and return True when authenticated.

    The function will retry navigation and form submission up to max_retries times.
    It validates success by waiting for the page URL to change away from the login URL
    or by waiting until the username input is no longer visible.
    """
    if not user_id or not password:
        logger.error('USER_ID or PASSWORD not provided')
        return False

    for attempt in range(1, max_retries + 1):
        try:
            driver.get(LOGIN_URL)

            # Wait for username and password fields
            wait.until(EC.presence_of_element_located((By.ID, 'logMain_UserName')))
            username_input = driver.find_element(By.ID, 'logMain_UserName')
            password_input = driver.find_element(By.ID, 'logMain_Password')

            username_input.clear()
            username_input.send_keys(user_id)
            password_input.clear()
            password_input.send_keys(password)

            # Click login
            login_button = driver.find_element(By.ID, 'logMain_Button1')
            login_button.click()

            # Primary success check: URL changes from the login URL
            try:
                wait.until(EC.url_changes(LOGIN_URL))
            except Exception:
                # Fallback: wait until username field is invisible (meaning we left login form)
                try:
                    wait.until(EC.invisibility_of_element_located((By.ID, 'logMain_UserName')))
                except Exception:
                    # If still on login page, treat as failure for this attempt
                    raise

            # At this point we consider login successful
            logger.info('Login successful')
            return True
        except Exception as exc:
            logger.warning(f'Login attempt {attempt} failed: {exc}')
            if attempt == max_retries:
                return False
            time.sleep(2)


def click_xpath(driver, wait: WebDriverWait, xpath: str, timeout: int = 15) -> bool:
    """Wait until an element located by XPath is clickable and click it."""
    try:
        elem = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        elem.click()
        return True
    except Exception as e:
        logger.error(f'click_xpath failed for {xpath}: {e}')
        return False


def with_retries(fn, max_retries: int = 3, delay: float = 1.5, *args, **kwargs):
    """Run a function with retries. Returns the function's return value or None on failure."""
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.warning(f'Attempt {attempt} failed: {exc}')
            if attempt == max_retries:
                return None
            time.sleep(delay)


# removed save_page_html debug helper (cleanup)


def get_course_options(driver):
    """Return a list of tuples (value, text) for the course select options."""
    try:
        sel = Select(driver.find_element(By.ID, 'ctl00_MainContainer_ddlAcaCalSection'))
        options = [(o.get_attribute('value'), o.text.strip()) for o in sel.options]
        return options
    except Exception as e:
        logger.error(f'Failed to read course options: {e}')
        return []


def select_course_and_expected_grade(driver, wait, course_value: str = None, expected_grade: str = 'A') -> bool:
    """Select a course by value (or pick first non-default) and set expected grade to 'A'.

    Saves the updated page HTML and returns True on success.
    """
    try:
        # Wait for course select to be present
        wait.until(EC.presence_of_element_located((By.ID, 'ctl00_MainContainer_ddlAcaCalSection')))
        sel_elem = driver.find_element(By.ID, 'ctl00_MainContainer_ddlAcaCalSection')
        sel = Select(sel_elem)

        # Determine course to select
        if not course_value:
            # pick first option whose value is not default or zero
            options = [(o.get_attribute('value'), o.text.strip()) for o in sel.options]
            picked = None
            for val, txt in options:
                if val and val.lower() not in ('0', '0_0'):
                    picked = val
                    break
            if not picked:
                logger.error('No selectable course options found')
                return False
            course_value = picked
            logger.info(f'Auto-picked course value: {course_value}')

        logger.info(f'Selecting course: {course_value}')
        sel.select_by_value(course_value)

        # After selecting, page likely triggers postback/UpdatePanel. Wait for progress then for form panel.
        try:
            # Wait for progress indicator to appear or for panel to be updated
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.panel.panel-default.pp')))
        except Exception:
            # fallback: wait for evaluation table (may appear later)
            pass

        # Wait for evaluation table to be present (longer timeout)
        longwait = WebDriverWait(driver, 20)
        try:
            longwait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.evaluationTable')))
        except Exception:
            logger.debug('evaluation table not found after selecting course (it may be loaded later).')

        # Now set expected grade to 'A'
        try:
            wait.until(EC.presence_of_element_located((By.ID, 'ctl00_MainContainer_ddlExpectedGrade')))
            grade_sel = Select(driver.find_element(By.ID, 'ctl00_MainContainer_ddlExpectedGrade'))
            # Ensure 'A' exists; if not, fallback to first non-zero option
            values = [o.get_attribute('value') for o in grade_sel.options]
            if 'A' in values:
                grade_sel.select_by_value('A')
                logger.info('Selected Expected Grade = A')
            else:
                # try selecting by visible text 'A'
                try:
                    grade_sel.select_by_visible_text('A')
                    logger.info('Selected Expected Grade by visible text A')
                except Exception:
                    logger.info('Expected Grade A not present; leaving default')
        except Exception as e:
            logger.warning(f'Failed to set expected grade: {e}')

        # Give the page a moment to settle after grade selection (best-effort)
        try:
            wait_for_ajax_and_postbacks(driver, timeout=3)
        except Exception:
            pass
        return True
    except Exception as e:
        logger.error(f'select_course_and_expected_grade failed: {e}')
        return False


def wait_for_evaluation_loaded(driver, wait, timeout: int = 20):
    """Wait until the evaluation table and faculty label are present and populated."""
    try:
        longwait = WebDriverWait(driver, timeout)
        longwait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.evaluationTable')))

        # Wait until faculty name is not the placeholder (underscores) and not empty
        def faculty_ready(d):
            try:
                text = d.find_element(By.ID, 'ctl00_MainContainer_lblFacultyName').text.strip()
                return text != '' and not set(text).issubset({'_', ' '})
            except Exception:
                return False

        longwait.until(faculty_ready)
        return True
    except Exception as e:
        logger.debug(f'wait_for_evaluation_loaded timeout or error: {e}')
        return False


def wait_until_not_pending(driver, wait, timeout: int = 20):
    """Wait until the evaluation status label does not read 'Pending!'."""
    try:
        def status_ready(d):
            try:
                text = d.find_element(By.ID, 'ctl00_MainContainer_lblEvaluationStatus').text.strip()
                return text.lower() != 'pending!'
            except Exception:
                return False
        WebDriverWait(driver, timeout).until(status_ready)
        return True
    except Exception:
        return False


def wait_until_evaluation_completed(driver, wait, timeout: int = 20):
    """Wait until the evaluation status label is 'Completed!'. Returns True when matched."""
    try:
        def status_completed(d):
            try:
                text = d.find_element(By.ID, 'ctl00_MainContainer_lblEvaluationStatus').text.strip()
                return text.lower() == 'completed!'
            except Exception:
                return False
        WebDriverWait(driver, timeout).until(status_completed)
        return True
    except Exception:
        return False


def fill_strongly_agree_in_table(driver, wait):
    """Find all radio inputs inside the evaluation table with value='5' and click them.

    Returns the count of radios clicked.
    """
    try:
        table = driver.find_element(By.CSS_SELECTOR, 'table.evaluationTable')
        radios = table.find_elements(By.CSS_SELECTOR, 'input[type=radio][value="5"]')
        clicked = 0
        for r in radios:
            try:
                # scrolling into view then click
                driver.execute_script('arguments[0].scrollIntoView({block: "center"});', r)
                if not r.is_selected():
                    # prefer JavaScript click to avoid overlay/scroll races
                    try:
                        driver.execute_script('arguments[0].click();', r)
                    except Exception:
                        r.click()
                clicked += 1
            except Exception as e:
                logger.debug(f'Failed to click radio {r.get_attribute("id")}: {e}')
        return clicked
    except Exception as e:
        logger.error(f'fill_strongly_agree_in_table failed: {e}')
        return 0


def submit_evaluation_and_wait(driver, wait, preferred_ids=None):
    """Click the first available button from preferred_ids and wait for UpdatePanel to complete.

    Returns (clicked_id or None, True/False for success)
    """
    if preferred_ids is None:
        preferred_ids = ['ctl00_MainContainer_btnTheorySubmit', 'ctl00_MainContainer_btnTheoryTop']
    for bid in preferred_ids:
        try:
            btn = driver.find_element(By.ID, bid)
            driver.execute_script('arguments[0].scrollIntoView({block: "center"});', btn)
            # use JS click to avoid element overlay issues
            try:
                driver.execute_script('arguments[0].click();', btn)
            except Exception:
                btn.click()
            # Wait for any UpdatePanel/ajax work triggered by the submit
            try:
                wait_for_ajax_and_postbacks(driver, timeout=12)
            except Exception:
                # fallback: wait for evaluation status to change or progress to disappear
                try:
                    wait.until(EC.invisibility_of_element_located((By.ID, 'divProgress')))
                except Exception:
                    pass
            return bid, True
        except Exception:
            # button not found/click failed - try next
            continue
    return None, False


def check_expected_grade_error_and_fix(driver, wait, expected_value='A') -> bool:
    """Check #ctl00_MainContainer_lblMsg for expected-grade error message, set grade and return True if fixed."""
    try:
        try:
            msg_el = driver.find_element(By.ID, 'ctl00_MainContainer_lblMsg')
            msg = msg_el.text.strip()
        except Exception:
            msg = ''
        if not msg:
            return False
        if 'expected' in msg.lower() and ('grade' in msg.lower() or 'expected grade' in msg.lower()):
            logger.info(f'Detected message prompting expected grade selection: "{msg}"')
            # Try panel-scoped setter first, then general setter
            ok = set_expected_grade_in_panel_with_retries(driver, wait, value=expected_value, attempts=6, delay=0.6)
            if not ok:
                ok = set_expected_grade_with_retries(driver, wait, value=expected_value, attempts=6, base_delay=0.5)
            if ok:
                logger.info('Fixed expected grade after message')
                return True
            else:
                logger.warning('Failed to fix expected grade after message')
                return False
        return False
    except Exception as e:
        logger.error(f'check_expected_grade_error_and_fix failed: {e}')
        return False


def process_course(driver, wait, course_value, course_text):
    """For a given course value, select it, set expected grade A, fill radios, submit, and return status dict."""
    status = {'value': course_value, 'text': course_text, 'start': datetime.utcnow().isoformat()}
    try:
        # Select course (use JS set + postback to reduce stale refs)
        js_ok = js_set_select_and_postback(driver, wait, 'ctl00_MainContainer_ddlAcaCalSection', course_value, postback_target='ctl00$MainContainer$ddlAcaCalSection')
        if not js_ok:
            # fallback to Select
            try:
                Select(driver.find_element(By.ID, 'ctl00_MainContainer_ddlAcaCalSection')).select_by_value(course_value)
            except Exception:
                pass

        # Wait for evaluation to load
        if not wait_for_evaluation_loaded(driver, wait, timeout=25):
            status['error'] = 'evaluation_load_timeout'
            return status

    # removed debug snapshot save after select

        # Try to set expected grade using panel-scoped method
        set_ok = set_expected_grade_in_panel_with_retries(driver, wait, value='A', attempts=6, delay=0.6)
        if not set_ok:
            set_ok = set_expected_grade_with_retries(driver, wait, value='A', attempts=6, base_delay=0.5)
        status['expected_set_initial'] = bool(set_ok)

        # After setting grade, re-verify (re-find to avoid stale refs)
        try:
            grade_val = wait.until(EC.presence_of_element_located((By.ID, 'ctl00_MainContainer_ddlExpectedGrade'))).get_attribute('value')
            status['selected_expected_grade'] = grade_val
        except Exception:
            status['selected_expected_grade'] = None

        # Fill strongly agree for all radio questions
        clicked = fill_strongly_agree_in_table(driver, wait)
        status['radios_clicked'] = clicked

        # Clear comment textarea if present
        try:
            ta = driver.find_element(By.ID, 'ctl00_MainContainer_txtTheoryComments')
            ta.clear()
        except Exception:
            pass

    # removed debug snapshot save after fill

    # Submit using Lab submit id first as requested
        preferred = ['ctl00_MainContainer_btnLabSubmit', 'ctl00_MainContainer_btnTheorySubmit', 'ctl00_MainContainer_btnTheoryTop']
        clicked_id, ok = submit_evaluation_and_wait(driver, wait, preferred_ids=preferred)
        status['submitted'] = bool(ok)
        status['clicked_submit_id'] = clicked_id

        if not ok:
            status['submit_error'] = 'no_submit_button_found'
        else:
            # After submit check for expected-grade error message
            # wait a short while for server response to update message label
            try:
                wait_for_ajax_and_postbacks(driver, timeout=6)
            except Exception:
                pass
            fixed = check_expected_grade_error_and_fix(driver, wait, expected_value='A')
            if fixed:
                # Resubmit once
                clicked_id2, ok2 = submit_evaluation_and_wait(driver, wait, preferred_ids=preferred)
                status['resubmit_after_fix'] = bool(ok2)
                status['resubmit_clicked_id'] = clicked_id2
            else:
                status['resubmit_after_fix'] = False

    # removed debug snapshot save after submit

        status['end'] = datetime.utcnow().isoformat()
        return status
    except Exception as e:
        status['error'] = str(e)
        status['end'] = datetime.utcnow().isoformat()
        logger.error(f'process_course failed for {course_value}: {e}')
        return status


def process_all_courses(driver, wait, log_path='completed_courses.json'):
    """Iterate over all course options and run process_course on each; append results to a JSON log.

    Re-queries the select options on each pass to avoid stale/initial snapshot problems.
    """
    results = []
    try:
        # Read initial course list (stable snapshot of options) to avoid dynamic changes
        sel = Select(wait.until(EC.presence_of_element_located((By.ID, 'ctl00_MainContainer_ddlAcaCalSection'))))
        initial_options = [(o.get_attribute('value'), o.text.strip()) for o in sel.options if o.get_attribute('value') and o.get_attribute('value').lower() not in ('0', '0_0')]
        processed_values = set()

        # We'll allow a few rounds in case the server still reports Pending! and some partial updates occur
        max_rounds = 4
        for rnd in range(max_rounds):
            made_progress = False
            for val, txt in initial_options:
                if val in processed_values:
                    continue
                logger.info(f'Processing course {val} - {txt} (round {rnd+1}/{max_rounds})')
                res = process_course(driver, wait, val, txt)
                logger.info(f'Result for {val}: submitted={res.get("submitted")}, error={res.get("error")}')
                results.append(res)
                processed_values.add(val)
                made_progress = True
                # Ensure any postback/async work settles before next iteration
                try:
                    wait_for_ajax_and_postbacks(driver, timeout=8)
                except Exception:
                    pass

            # If evaluation status is cleared, break early
            if wait_until_not_pending(driver, wait, timeout=6):
                break

            # If nothing made progress this round, stop to avoid endless loop
            if not made_progress:
                break

        # After main rounds, ensure server reports Completed!; if not, retry failed submissions
        if not wait_until_evaluation_completed(driver, wait, timeout=6):
            logger.info('Evaluation status is not Completed! — attempting to retry failed submissions')
            # Build list of values to retry: those with submitted==False or explicit failure
            retry_values = [r['value'] for r in results if not r.get('submitted')]
            # Also retry any where resubmit_after_fix was False but submitted False earlier
            extra_attempts = 2
            for attempt in range(extra_attempts):
                if not retry_values:
                    break
                new_retry = []
                for val in retry_values:
                    # find text from initial_options
                    text = next((t for v, t in initial_options if v == val), '')
                    logger.info(f'Retrying course {val} ({attempt+1}/{extra_attempts})')
                    res = process_course(driver, wait, val, text)
                    results.append(res)
                    if not res.get('submitted'):
                        new_retry.append(val)
                    # wait briefly for any server updates
                    try:
                        wait_for_ajax_and_postbacks(driver, timeout=6)
                    except Exception:
                        pass
                retry_values = new_retry

        # Save results to JSON
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f'Wrote course processing log to {log_path}')
        except Exception as e:
            logger.error(f'Failed to write log: {e}')
        return results
    except Exception as e:
        logger.error(f'process_all_courses failed: {e}')
        return results


def set_expected_grade_with_retries(driver, wait, value='A', attempts=8, base_delay=0.5, screenshot_on_fail=True):
    """Try multiple strategies to set the expected grade select to `value`.

    Strategies attempted each loop:
      - re-find select, open it and click the option element
      - JS set el.value and dispatch change event
      - Select API (select_by_value / select_by_visible_text)

    Verifies the value after each attempt. Returns the selected value on success, or None on failure.
    Optionally saves a screenshot on final failure for debugging.
    """
    last_exception = None
    for attempt in range(1, attempts + 1):
        try:
            # re-find the element each attempt
            grade_elem = wait.until(EC.presence_of_element_located((By.ID, 'ctl00_MainContainer_ddlExpectedGrade')))

            # Strategy 1: click the option element directly
            try:
                options = grade_elem.find_elements(By.TAG_NAME, 'option')
                target_option = None
                for o in options:
                    if o.get_attribute('value') == value or (o.text or '').strip() == value:
                        target_option = o
                        break
                if target_option:
                    try:
                        # click the select to open then click option
                        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', grade_elem)
                        grade_elem.click()
                        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', target_option)
                        target_option.click()
                        # Dispatch change event (some frameworks need it)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", grade_elem)
                    except Exception:
                        # ignore and fall through to next strategies
                        pass

            except Exception:
                # unable to find or click option; continue
                pass

            # Strategy 2: JS set + dispatch change
            try:
                driver.execute_script("var el=arguments[0]; el.value=arguments[1]; el.dispatchEvent(new Event('change',{bubbles:true}));", grade_elem, value)
            except Exception:
                pass

            # Strategy 3: Select API
            try:
                sel = Select(grade_elem)
                try:
                    sel.select_by_value(value)
                except Exception:
                    try:
                        sel.select_by_visible_text(value)
                    except Exception:
                        pass
            except Exception:
                pass

            # Short wait for DOM to settle and any UpdatePanel to process
            time.sleep(base_delay)

            # Best-effort: wait for any async postback/ajax work to finish before verification
            try:
                wait_for_ajax_and_postbacks(driver, timeout=6)
            except Exception:
                pass

            # Optionally wait for progress indicator (if it appears) and disappear
            try:
                # Wait briefly for progress to appear, then disappearance
                small_wait = WebDriverWait(driver, 1)
                small_wait.until(EC.presence_of_element_located((By.ID, 'divProgress')))
                # when present, wait until it's gone
                WebDriverWait(driver, 8).until(EC.invisibility_of_element_located((By.ID, 'divProgress')))
            except Exception:
                # ignore — progress may not be used for this action
                pass

            # Re-read the value
            try:
                grade_elem = driver.find_element(By.ID, 'ctl00_MainContainer_ddlExpectedGrade')
                selected_val = grade_elem.get_attribute('value')
                if selected_val == value:
                    return selected_val
            except Exception as e:
                last_exception = e

        except Exception as e:
            last_exception = e

        # incremental backoff
        time.sleep(base_delay * attempt)

    # on failure, optionally capture screenshot to help debugging
    # removed screenshot-on-fail to avoid writing debug artifacts
    if last_exception:
        logger.error(f'set_expected_grade_with_retries final error: {last_exception}')
    return None


def wait_for_ajax_and_postbacks(driver, timeout: int = 8):
    """Wait until jQuery activity and ASP.NET PageRequestManager async postbacks are idle.

    Polls window.jQuery.active (if jQuery present) and Sys.WebForms.PageRequestManager
    (if present) so callers can avoid racing with UpdatePanel replacements.
    Raises Exception on timeout.
    """
    import time as _time
    end = _time.time() + timeout
    while True:
        try:
            active = driver.execute_script(
                "var jq = window.jQuery?window.jQuery.active:0; var prm = (window.Sys && Sys.WebForms && Sys.WebForms.PageRequestManager)?Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostBack():false; return [jq, prm];"
            )
            if isinstance(active, (list, tuple)):
                jq_active, prm_busy = active[0], active[1]
            else:
                jq_active, prm_busy = 0, False
            if (not jq_active) and (not prm_busy):
                return True
        except Exception:
            # if script can't run, assume idle after short pause
            pass
        if _time.time() > end:
            raise Exception('wait_for_ajax_and_postbacks timed out')
        _time.sleep(0.12)


def js_set_select_and_postback(driver, wait, select_id: str, value: str, postback_target: str = None, wait_for_locator=None, timeout: int = 20) -> bool:
    """Set a select's value using JS, optionally call __doPostBack on the given target, and wait for a locator change.

    - select_id: element id of the <select>
    - value: option value to set
    - postback_target: if provided, will call __doPostBack(postback_target, '') after setting the value
    - wait_for_locator: an (By, selector) tuple to wait for after the postback (or presence of evaluationTable if None)

    Returns True when the wait condition is met, False otherwise.
    """
    try:
        # Ensure select is present
        grade_elem = wait.until(EC.presence_of_element_located((By.ID, select_id)))
        # Set value and dispatch change
        driver.execute_script("var el=arguments[0]; el.value=arguments[1]; el.dispatchEvent(new Event('change',{bubbles:true}));", grade_elem, value)

        # If we must call __doPostBack explicitly (ASP.NET handlers), do it
        if postback_target:
            # call __doPostBack if available
            driver.execute_script("if(typeof __doPostBack === 'function'){ __doPostBack(arguments[0], ''); }", postback_target)

            # Best-effort: wait for any AJAX / UpdatePanel postbacks or jQuery activity to finish
            try:
                wait_for_ajax_and_postbacks(driver, timeout=timeout)
            except Exception:
                pass

        # Wait for an expected change. Priority: provided locator, else faculty name change, else evaluation table presence
        if wait_for_locator:
            by, sel = wait_for_locator
            try:
                WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, sel)))
                return True
            except Exception:
                return False
        else:
            # Wait until evaluationTable is present OR faculty label is populated
            def condition(d):
                try:
                    # If evaluation table present -> success
                    if d.find_elements(By.CSS_SELECTOR, 'table.evaluationTable'):
                        return True
                    # Or faculty name populated
                    text = d.find_element(By.ID, 'ctl00_MainContainer_lblFacultyName').text.strip()
                    if text != '' and not set(text).issubset({'_', ' '}):
                        return True
                except Exception:
                    return False
                return False

            try:
                WebDriverWait(driver, timeout).until(condition)
                return True
            except Exception:
                return False
    except Exception as e:
        logger.error(f'js_set_select_and_postback error: {e}')
        return False


def set_expected_grade_in_panel_with_retries(driver, wait, value='A', attempts=6, delay=0.6):
    """Set Expected Grade by locating the select inside the panel where the label 'Expected Grade' appears.

    Retries to handle DOM replacement. Returns True if selection successful, False otherwise.
    """
    last_exc = None
    xpath = "//div[contains(@class,'panel') and contains(@class,'panel-default') and contains(@class,'pp')]//label[normalize-space()='Expected Grade']/following::select[1]"
    for attempt in range(1, attempts + 1):
        try:
            sel_elem = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            # try JS set
            try:
                driver.execute_script("var el=arguments[0]; el.value=arguments[1]; el.dispatchEvent(new Event('change',{bubbles:true}));", sel_elem, value)
            except Exception:
                pass
            # allow any handlers / partial postbacks to finish
            try:
                wait_for_ajax_and_postbacks(driver, timeout=6)
            except Exception:
                pass
            time.sleep(0.25)
            # verify
            try:
                sel_elem = driver.find_element(By.XPATH, xpath)
                if sel_elem.get_attribute('value') == value:
                    return True
            except Exception as e:
                last_exc = e
        except Exception as e:
            last_exc = e
        time.sleep(delay)
    logger.error(f'set_expected_grade_in_panel_with_retries failed after {attempts} attempts; last: {last_exc}')
    return False


def process_and_save_first_n_courses(driver, wait, n=2, log_path='completed_courses.json'):
    """Process first n non-default courses using process_course and save results/logs.

    Returns results list.
    """
    results = []
    try:
        sel = Select(wait.until(EC.presence_of_element_located((By.ID, 'ctl00_MainContainer_ddlAcaCalSection'))))
        options = [(o.get_attribute('value'), o.text.strip()) for o in sel.options if o.get_attribute('value') and o.get_attribute('value').lower() not in ('0', '0_0')]
        to_process = options[:n]
        for val, txt in to_process:
            logger.info(f'Processing sample course {val} - {txt}')
            res = process_course(driver, wait, val, txt)
            results.append(res)
            # small delay
            time.sleep(0.8)
        # write log
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f'Wrote sample processing log to {log_path}')
        except Exception as e:
            logger.error(f'Failed to write sample log: {e}')
        return results
    except Exception as e:
        logger.error(f'process_and_save_first_n_courses failed: {e}')
        return results


def main():
    user_id = os.getenv('USER_ID')
    password = os.getenv('PASSWORD')
    headless_env = os.getenv('HEADLESS', '1')
    headless = not (headless_env in ('0', 'false', 'False'))

    driver, wait = create_driver(headless=headless)

    try:
        success = login_ucam(driver, user_id, password, wait, max_retries=3)
        if not success:
            logger.error('Login failed after retries.')
            sys.exit(2)
        logger.info('Login successful — dashboard should be reachable now.')

        # Now navigate to Course Evaluation page by clicking the specified menu items.
        # 1) Click the top-level menu item (XPath provided)
        first_xpath = '/html/body/form/div[3]/div[2]/div/div/div/div/div[2]/div[1]/ul/li[5]/a'
        second_xpath = '/html/body/form/div[3]/div[2]/div/div/div/div/div[2]/div[1]/ul/li[1]'
        third_xpath = '/html/body/form/div[3]/div[2]/div/div/div/div/div[2]/div[1]/ul/li[1]/ul/li/a'

        # Click with retries and small delays to allow menus to animate/load
        if not with_retries(lambda: click_xpath(driver, wait, first_xpath), max_retries=3, delay=1):
            logger.error('Failed to click first menu item.')
            sys.exit(3)
        time.sleep(0.8)

        if not with_retries(lambda: click_xpath(driver, wait, second_xpath), max_retries=3, delay=1):
            logger.error('Failed to click second menu item.')
            sys.exit(4)
        time.sleep(0.5)

        if not with_retries(lambda: click_xpath(driver, wait, third_xpath), max_retries=3, delay=1):
            logger.error('Failed to click course evaluation submenu.')
            sys.exit(5)

        # If we reach here, assume we are on the course evaluation page. Wait for a known page element.
        try:
            # This selector is generic; if you have a specific element on the evaluation page, replace it.
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'h1')))
        except Exception:
            logger.debug('Reached target page but could not confirm with fallback selector.')

        logger.info('Navigation to Course Evaluation page attempted — check browser or logs for details.')

        # Process all courses: select, set grade A, fill radios, submit
        try:
            results = process_all_courses(driver, wait)
            logger.info('Finished main processing round.')
            # After main pass, if evaluation still pending, process any remaining unprocessed options
            try:
                if not wait_until_evaluation_completed(driver, wait, timeout=6):
                    logger.info('Evaluation status not Completed! after main pass — checking for remaining courses to process')
                    # compute processed values from results
                    processed_values = {r.get('value') for r in results if r.get('value')}
                    # read current options and process unprocessed ones
                    try:
                        sel = Select(driver.find_element(By.ID, 'ctl00_MainContainer_ddlAcaCalSection'))
                        options = [(o.get_attribute('value'), o.text.strip()) for o in sel.options if o.get_attribute('value') and o.get_attribute('value').lower() not in ('0', '0_0')]
                        for val, txt in options:
                            if val in processed_values:
                                continue
                            logger.info(f'Processing leftover course {val} - {txt}')
                            res = process_course(driver, wait, val, txt)
                            results.append(res)
                            processed_values.add(val)
                            try:
                                wait_for_ajax_and_postbacks(driver, timeout=6)
                            except Exception:
                                pass
                    except Exception as e:
                        logger.error(f'Failed to read remaing course options: {e}')
            except Exception:
                pass

            # Final wait for Completed! status before exit; allow a bit longer
            if not wait_until_evaluation_completed(driver, wait, timeout=20):
                logger.warning('Evaluation status did not reach Completed! before timeout.')
            else:
                logger.info('Evaluation status is Completed!')

        except Exception as e:
            logger.error(f'Error during select-and-save: {e}')

        # Keep browser open briefly for inspection when not headless
        if not headless:
            logger.info('Non-headless mode: keeping browser open for 5 seconds...')
            time.sleep(5)

        sys.exit(0)
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
