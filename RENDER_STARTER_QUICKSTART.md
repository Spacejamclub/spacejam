# Render Starter Quickstart

1. Open [Render Dashboard](https://dashboard.render.com/).
2. Click `New +` -> `Blueprint`.
3. Select the GitHub repo `Spacejamclub/spacejam`.
4. Render will read [render.yaml](/Users/space_plug/Desktop/SPACE_JAM/render.yaml).
5. Check that the plan is `Starter`.
6. Click `Apply`.
7. Open the new service -> `Environment`.
8. Copy values from [render.env.starter](/Users/space_plug/Desktop/SPACE_JAM/render.env.starter).
9. Replace `BOT_TOKEN` with the real bot token.
10. Save changes and deploy.
11. Open `https://YOUR-SERVICE.onrender.com/healthz`.
12. If `healthz` opens, open `https://YOUR-SERVICE.onrender.com/miniapp`.
13. In Render -> `Settings` -> `Custom Domains`, add `pay.spacejam.by`.
14. Create the DNS record that Render shows.
15. After DNS is ready, open `https://pay.spacejam.by/healthz`.

What matters most:

- `RUN_BOT=1`
- `RUN_WEB=1`
- `MINI_APP_URL=https://pay.spacejam.by/miniapp`
- plan = `Starter`

Important:

- after Render starts the bot, stop any local `python bot.py` process on your computer
- only one running bot process can use the same Telegram token at a time
