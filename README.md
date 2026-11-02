# GhoSty Dual-Client Expanded

Logger pattern (discord.py controller + raw gateway workers) with the important farm modules ported:

- Quest module (`owo q`, claim buttons, persistence file)
- HuntBot image captcha solver (PIL/numpy template match — needs `letters/*.png`)
- Zoo / cash / essence tracking (`owo zoo` parse + panel display)
- Gem checks / inventory (`owo inv` + `owo use`)
- Boss guild channel hardcodes (primary + backups)
- Full SPEED_MODES + command mix + huntbot + captcha pause

## Captcha templates

Place letter PNGs in `./letters/` named like `a.png`, `b.png`, … (same as original tool).
Without them, image captchas pause the worker instead of solving.

## Run

```bash
export DISCORD_BOT_TOKEN="bot-token"
bash prestart.sh
```
