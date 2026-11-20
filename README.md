# JobShield AI

JobShield AI analyzes job postings for recruitment fraud using machine learning
and rule-based checks.

| Link | Description |
|---|---|
| [Deploy the full app](https://render.com/deploy?repo=https://github.com/balachandu187/jobfraud) | Create the public React + FastAPI service on Render |
| [GitHub Pages deployment status](https://github.com/balachandu187/jobfraud/actions/workflows/pages.yml) | Static landing-page deployment workflow |
| [Source code](https://github.com/balachandu187/jobfraud) | Browse this repository |

There is not an active public app preview yet: the GitHub Pages deployment is
currently failing, and its URL still serves an outdated login page. Use the
Render deploy button above to create the full-stack service. Set `GOOGLE_CLIENT_ID`
in the Render service environment, then add the deployed service origin to the
Google OAuth client's Authorized JavaScript origins. Never put OAuth secrets in
this repository.

See [JobShieldAI/README.md](./JobShieldAI/README.md) for local setup, architecture,
and deployment details.
