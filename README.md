# JobShield AI

JobShield AI analyzes job postings for recruitment fraud using machine learning
and rule-based checks.

| Link | Description |
|---|---|
| [Project preview](https://balachandu187.github.io/jobfraud/) | GitHub Pages project landing page |
| [Deploy the full app](https://render.com/deploy?repo=https://github.com/balachandu187/jobfraud) | Create the React + FastAPI service on Render |
| [Source code](https://github.com/balachandu187/jobfraud) | Browse this repository |

The GitHub Pages link is a static landing page. To use scanning, email sign-in,
or Google sign-in, deploy the full-stack service with the Render button above.
Set `GOOGLE_CLIENT_ID` in the Render service environment, then add the deployed
service origin to the Google OAuth client's Authorized JavaScript origins.
Never put OAuth secrets in this repository.

See [JobShieldAI/README.md](./JobShieldAI/README.md) for local setup, architecture,
and deployment details.
