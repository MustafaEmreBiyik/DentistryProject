# Streamlit Cloud Deployment - Fixing Database Connection Error

## Problem

You're encountering `sqlalchemy.exc.OperationalError` because Streamlit Cloud cannot access your Supabase database URL from the `.env` file.

## Solution

### Step 1: Configure Secrets in Streamlit Cloud

1. **Go to your Streamlit Cloud Dashboard**
   - Visit: https://share.streamlit.io/
   - Find your deployed app

2. **Open App Settings**
   - Click on your app
   - Click the **"⋮"** (three dots) menu in the bottom right
   - Select **"Settings"**

3. **Add Secrets**
   - Go to the **"Secrets"** section
   - Copy and paste the following into the secrets editor, replacing the placeholder values with your own credentials:

```toml
# Database Configuration - REQUIRED
DATABASE_URL = "postgresql://postgres:YOUR_ENCODED_PASSWORD@YOUR_SUPABASE_HOST:5432/postgres"

# API Keys
GEMINI_API_KEY = "your-gemini-api-key"
HUGGINGFACE_API_KEY = "your-huggingface-api-key"
```

4. **Save the Secrets**
   - Click **"Save"**
   - The app will automatically restart

### Step 2: Alternative - Use Supabase Connection Pooler (Recommended)

Streamlit Cloud is a serverless environment, so using Supabase's connection pooler is better:

**Get your Pooler Connection String from Supabase:**

1. Go to your Supabase project: https://supabase.com/dashboard
2. Click on **"Database"** → **"Connection Info"**
3. Switch to **"Connection Pooling"** tab
4. Copy the **"Connection string"** and ensure it's in **"Transaction"** mode
5. The pooler uses port **6543** instead of 5432

**Update your Streamlit Cloud secrets to:**

```toml
DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@db.jofhtrekpiwuidrkihse.supabase.co:6543/postgres?sslmode=require"
```

## What Changed in Your Code

### database.py

Updated to read from `st.secrets` first (for Streamlit Cloud), then falls back to environment variables (for local development):

```python
# Streamlit Cloud için st.secrets'dan oku, yoksa environment variable'dan al
try:
    import streamlit as st
    DATABASE_URL = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL"))
except (ImportError, FileNotFoundError, AttributeError):
    DATABASE_URL = os.getenv("DATABASE_URL")
```

### Local Development

For local testing, secrets are now in `.streamlit/secrets.toml` which works the same as Streamlit Cloud.

## Important Notes

### Password URL Encoding

Special characters in passwords must be URL-encoded:

- `*` → `%2A`
- `%` → `%25`
- `@` → `%40`
- `!` → `%21`

For example, a password like `NMVn*A%gCnq59Z3` would be encoded as `NMVn%2AA%25gCnq59Z3`.

### Security

- **Never commit `.streamlit/secrets.toml` to Git** (it's already in `.gitignore`)
- The secrets in Streamlit Cloud are encrypted and only accessible to your app
- Rotate your API keys if they've been exposed publicly

## Verifying the Fix

After updating secrets in Streamlit Cloud:

1. The app will automatically restart
2. Navigate to the Account page
3. The database connection should now work
4. You should see your profile data without errors

## Troubleshooting

### If you still get connection errors:

1. **Check Supabase Database Status**
   - Ensure your Supabase project is active (not paused)
   - Free tier databases pause after inactivity

2. **Verify Connection String**
   - Go to Supabase Dashboard → Database → Connection Info
   - Copy the exact connection string
   - Make sure to URL-encode the password

3. **Check Streamlit Cloud Logs**
   - In your app, click "Manage app" (bottom right)
   - View the logs for detailed error messages

4. **Try Direct Connection Port**
   - Direct: port 5432
   - Pooler: port 6543 (better for Streamlit Cloud)

5. **Add SSL Mode**
   - Some connections require: `?sslmode=require` at the end of the URL

## Example: Complete Correct Connection String

```toml
# Option 1: Direct Connection (Port 5432)
DATABASE_URL = "postgresql://postgres:YOUR_ENCODED_PASSWORD@YOUR_SUPABASE_HOST:5432/postgres"

# Option 2: Connection Pooler (Port 6543 - RECOMMENDED for Streamlit Cloud)
DATABASE_URL = "postgresql://postgres:YOUR_ENCODED_PASSWORD@YOUR_SUPABASE_HOST:6543/postgres?sslmode=require"
```

## Need More Help?

If the issue persists:

1. Check if your Supabase project is in the same region (reduces latency)
2. Verify database is not paused (Supabase free tier auto-pauses)
3. Check Supabase logs for connection attempts
4. Ensure your password hasn't changed in Supabase

---

**After configuring, your app should connect successfully to Supabase! 🎉**
