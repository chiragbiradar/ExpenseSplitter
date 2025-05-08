@echo off
echo Deploying to Cloud Run...

REM Read environment variables from .env file
for /F "tokens=*" %%A in (.env) do (
    set %%A
)

REM Deploy to Cloud Run with environment variables
gcloud run deploy expensesplitter ^
  --source . ^
  --platform managed ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --set-env-vars "^
DATABASE_URL=%DATABASE_URL%,^
SESSION_SECRET=%SESSION_SECRET%,^
DEBUG=%DEBUG%,^
RESEND_API_KEY=%RESEND_API_KEY%,^
CURRENCY_API_KEY=%CURRENCY_API_KEY%,^
ALLOWED_HOSTS=%ALLOWED_HOSTS%"

echo Deployment complete!
