# Bot Capabilities

This document outlines what the UIU Course Evaluation Automation Bot can do for you.

## What This Bot Does

The bot automates the tedious process of filling out UIU (UCAM) course evaluations. Instead of manually clicking through each course and evaluation question, the bot handles it all automatically.

### Core Capabilities

#### 1. **Automated Login**
- Securely logs into UCAM using credentials from your `.env` file
- Retries login up to 3 times if network issues occur
- Validates successful authentication before proceeding

#### 2. **Course Evaluation Navigation**
- Automatically navigates to the Course Evaluation page from the dashboard
- Handles the ASP.NET menu system with proper wait times
- Robust retry logic for menu interactions

#### 3. **Automatic Course Processing**
- Detects all available courses requiring evaluation
- Processes each course automatically in sequence
- Handles ASP.NET UpdatePanel postbacks gracefully

#### 4. **Evaluation Form Completion**
For each course, the bot:
- Sets **Expected Grade** to "A" (highest grade)
- Selects **"Strongly Agree"** for all evaluation questions
- Fills out the entire evaluation table automatically
- Submits the completed evaluation

#### 5. **Error Handling & Retries**
- Built-in retry mechanisms for flaky elements
- Handles partial postback errors from ASP.NET UpdatePanels
- Waits for AJAX/jQuery operations to complete
- Recovers from common errors (missing expected grade, stale elements)

#### 6. **Audit Logging**
- Creates `completed_courses.json` with a summary of processed courses
- Logs include:
  - Course value and name
  - Faculty name
  - Number of questions filled
  - Submission status
  - Any errors encountered
  - Timestamp of processing

#### 7. **Headless & Visible Modes**
- **Headless mode (default)**: Runs in background without opening a browser window
- **Visible mode**: Set `HEADLESS=0` to watch the bot work in real-time for debugging

## What You Can Use This For

### ✅ Recommended Uses

1. **Save Time**: Automatically complete all your course evaluations in minutes instead of hours
2. **Consistent Feedback**: Provide uniform positive feedback across all courses
3. **Learning Tool**: Study the code to understand Selenium automation with ASP.NET sites
4. **Debugging**: Run in visible mode to troubleshoot UCAM page issues

### ⚠️ Limitations

1. **Fixed Responses**: Currently only selects "Strongly Agree" for all questions
   - Cannot customize individual question responses
   - Cannot add text comments (if UCAM supports them)

2. **Grade Selection**: Only sets Expected Grade to "A"
   - Cannot specify different expected grades per course

3. **Single User**: Processes evaluations for one user account per run

4. **No Selective Processing**: Processes all pending courses
   - Cannot skip specific courses
   - Cannot process only certain courses

## Configuration Options

The bot supports these environment variables in your `.env` file:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USER_ID` | Yes | - | Your UCAM username |
| `PASSWORD` | Yes | - | Your UCAM password |
| `HEADLESS` | No | `1` | Set to `0` to see the browser window |

## Future Enhancement Possibilities

While this bot is intentionally simple, potential enhancements could include:

- Custom response selection (not just "Strongly Agree")
- Different expected grades per course
- Text comment support
- Selective course processing
- Dry-run mode (preview without submitting)
- Optional audit logging
- Multiple user account support
- Email/Telegram notifications on completion

If you need any of these features, feel free to open an issue or submit a pull request!

## Technical Capabilities

For developers interested in the technical implementation:

### Key Features
- **Selenium WebDriver**: Browser automation using Chrome
- **webdriver-manager**: Automatic ChromeDriver version management
- **ASP.NET Handling**: Special logic for UpdatePanel postbacks
- **Wait Strategies**: Multiple explicit wait conditions for reliability
- **JavaScript Execution**: Direct DOM manipulation when needed
- **Retry Patterns**: Exponential backoff and configurable retry attempts

### Function Reference

The bot includes these main functions:

- `create_driver()`: Initialize Chrome WebDriver with options
- `login_ucam()`: Authenticate to UCAM
- `process_all_courses()`: Main orchestration function
- `process_course()`: Handle single course evaluation
- `fill_strongly_agree_in_table()`: Fill evaluation questions
- `submit_evaluation_and_wait()`: Submit form and verify
- `wait_for_ajax_and_postbacks()`: Handle ASP.NET async operations

## Getting Help

If you encounter issues:

1. **Check the logs**: The bot provides detailed console output
2. **Run in visible mode**: Set `HEADLESS=0` to watch what happens
3. **Check the audit log**: Review `completed_courses.json` for status
4. **Update Chrome**: Ensure Chrome browser is up to date
5. **Check network**: Verify you can access UCAM manually

## Responsible Use

⚠️ **Important**: This bot should be used responsibly and in accordance with your institution's policies. The author is not responsible for misuse.

- Only use with your own credentials
- Ensure automated evaluations align with actual feedback you'd provide
- Consider manually adding text comments for constructive feedback
- Don't share your credentials with anyone

---

**License**: MIT License - Free to use and modify
