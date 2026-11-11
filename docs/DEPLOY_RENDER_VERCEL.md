# Hosting under the no-charge requirement

Updated 2026-11-12. **The user requires no AI/API charges and no hosting charges.** This supersedes the earlier managed Render deployment guide. The full application is supported locally; see [cost policy](COST_POLICY.md).

## Run the complete app without cloud service fees

```sh
git clone https://github.com/Gagandeepkaurrr/WorkQuest.git
cd WorkQuest
make setup
make dev
```

Open http://localhost:5173. Verification/reset emails arrive at http://localhost:8025. Use `make admin` to create an administrator. Teammates and coaching use built-in authored content and no external model tokens. No API keys, cloud account, paid worker, subscription or model download is needed.

## Render

`render.yaml` deliberately contains empty service/database/environment-group lists. Applying it does not provision the former paid stack. Do not copy the paid Blueprint from Git history or provision replacement paid services.

The complete previous architecture required dedicated workers and cron, which have no free Render instances. Free PostgreSQL expires after 30 days, free web services can sleep, and SMTP ports are restricted. It would be misleading to label that stack free and permanently available. [Render free services](https://render.com/docs/free), [service types and free availability](https://render.com/docs/your-first-deploy).

No Render services were created by this project. Removing declarations does not cancel any resources you might separately have created yourself; inspect your provider account before assuming existing bills have stopped. No existing account resources were modified by this change.

## Vercel

`vercel.json` remains in the repository with the React build, SPA fallback and security headers. Vercel Hobby can host the frontend for eligible personal/non-commercial use within its free limits. **That does not host the FastAPI/PostgreSQL/Redis/worker backend**, and the placeholder API destination is not a working service. A public frontend cannot use the PostgreSQL or API running on your private localhost.

If you later choose frontend-only Hobby hosting, the commands are:

```sh
pnpm dlx vercel@65.14.0 login
pnpm dlx vercel@65.14.0 link
pnpm dlx vercel@65.14.0 deploy --prod
```

Choose Hobby; do not enable a paid plan. No hosted deployment was performed, and public full-application hosting remains **NOT PROVIDED / NOT VERIFIED**. The full no-service-fee application is available locally. [Vercel Hobby limits](https://vercel.com/docs/plans/hobby), [CLI deployment](https://vercel.com/docs/projects/deploy-from-cli).
