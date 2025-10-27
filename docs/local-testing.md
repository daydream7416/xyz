# Local Test Environment

Follow these steps to try the `kayit.html` form locally and view the submitted data in `landing/main.html`.

## Prerequisites
- Python 3.10+ (virtual environment recommended)

## Backend setup
1. `cd backend`
2. Create and activate a virtual environment:
   - Windows PowerShell: `python -m venv .venv; .\.venv\Scripts\Activate.ps1`
3. Install dependencies: `pip install -r requirements.txt`
4. Copy the example overrides so the app uses SQLite and local URLs: `Copy-Item .env.local.example .env.local`
5. Start the API on port 8000: `uvicorn main:app --reload --port 8000`

The override file enables SQLite (`test.db`) and points generated landing links at `http://localhost:8080`.

## Frontend setup
1. From the repository root run: `python -m http.server 8080`
2. Visit `http://localhost:8080/kayit.html` to open the registration form.

## Test flow
1. Submit the form with sample data (profile photo optional).
2. The success message displays a link like `http://localhost:8080/landing/main.html?agent=<slug>`. Open it to see the personalised page.
3. You can also verify the API payload via `http://localhost:8000/agents/<slug>` in a browser or with `curl`.

Stop the servers with `Ctrl+C`. Remove or adjust `.env.local` when you need to switch back to production settings.
