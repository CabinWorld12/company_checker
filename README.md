# Company Checker

A deliberately simple private dashboard for annual company revenue, operating profit and P/E history, with tables, charts and side-by-side comparisons.

## What it does
- Looks up companies by ticker symbol (up to 8 at once).
- Shows latest annual revenue, operating profit and P/E.
- Shows historical annual tables and line graphs.
- Compares selected companies in a table and graph.
- Caches data for one hour to reduce API calls.
- Optional password gate. For real privacy, also deploy it as a **private Streamlit app** and invite only approved viewers.

## Data provider
This app uses Financial Modeling Prep (FMP) stable API endpoints:
- `profile`
- `income-statement`
- `ratios`

You need an FMP API key. The free plan is suitable for testing but may not include all the historical financial statement/ratio access you want. Check the provider's current coverage and plan limits before paying. The Starter plan currently lists annual fundamentals and ratios for US exchanges; non-US listings may need a different plan/provider.

## Run it on your computer
1. Install Python 3.10 or newer.
2. Unzip this folder.
3. Open a terminal in this folder.
4. Run:
   ```bash
   python -m venv .venv
   ```
5. Activate the environment:
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`
6. Install packages:
   ```bash
   pip install -r requirements.txt
   ```
7. Create `.streamlit` folder, then create `.streamlit/secrets.toml` with:
   ```toml
   FMP_API_KEY = "paste-your-FMP-key-here"
   APP_PASSWORD = "choose-a-long-private-password"
   ```
8. Start:
   ```bash
   streamlit run app.py
   ```
9. It opens in your browser, usually at `http://localhost:8501`.

**Never upload `secrets.toml` to GitHub.** Add `.streamlit/secrets.toml` to `.gitignore` if you use Git.

## Host it privately online (recommended: Streamlit Community Cloud)
1. Create a GitHub repository and upload `app.py`, `requirements.txt`, and this README. Keep the repository **private**.
2. Do not upload your API key or password. Add `.streamlit/secrets.toml` to `.gitignore`.
3. Sign in to Streamlit Community Cloud using your GitHub account.
4. Choose **Create app**, select your private repository, branch and `app.py`, then deploy.
5. In the app's settings/secrets area, add:
   ```toml
   FMP_API_KEY = "your-FMP-key"
   APP_PASSWORD = "your-long-private-password"
   ```
6. In Streamlit app sharing/access settings, keep the app **private** and add only the email addresses you want to allow as viewers.
7. Test the app while signed out / with an uninvited account to check access is restricted.

Streamlit's private-app access controls are the main privacy layer. The password in this app is an optional extra layer, not a replacement for private viewer permissions. Streamlit Community Cloud currently allows one private app per workspace.

## Important notes
- The free hosting option and the market-data API are separate: data-provider limits/fees may apply even if hosting is free.
- This first version compares reported currencies as supplied. It deliberately does not pretend USD and GBP amounts are directly comparable.
- "Similar companies" are selected by entering their ticker symbols yourself. That keeps the app simple and avoids unreliable automatic peer selection.
- Annual P/E values may be missing. P/E can be misleading or unavailable when earnings are negative or data coverage is incomplete.
- The app is for learning and company research, not financial advice.
