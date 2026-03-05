Rain Production Deployment Guide

Prerequisites

- Python 3.9+
- Ollama (local) or API keys (OpenAI, Anthropic)
- ~2GB disk for ChromaDB + embeddings (first run downloads model)

Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | — |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `RAIN_LLM_PROVIDER` | `openai`, `anthropic`, or `ollama` | `ollama` if no keys |
| `RAIN_SAFETY_ENABLED` | Enable safety vault | `true` |
| `RAIN_WEB_API_KEY` | Require X-API-Key for /chat | — (recommended in prod) |
| `RAIN_USER_NAME` | Bootstrap user identity | — |
| `RAIN_DRIFT_WEBHOOK` | Webhook URL for drift alerts (cron) | — |

Directory Layout

```
data/
├── vector/          # ChromaDB (embeddings)
├── symbolic.db      # Facts, beliefs, lessons
├── timeline.db      # Event log
├── audit.log        # Action log (hash chain)
├── drift_baseline.json   # Drift detection baseline
└── kill_switch      # Create with "1" to halt all actions
```

Backup & Restore

Backup: Copy entire `data/` directory. ChromaDB is in `data/vector/`.

```bash
tar -czvf rain-backup-$(date +%Y%m%d).tar.gz data/
```

Restore: Extract over `data/`. Ensure Rain is not running.

Kill Switch

Create `data/kill_switch` with content `1` to block all actions:

```bash
echo 1 > data/kill_switch
```

Delete or clear the file to resume.

Web UI (Production)

```bash
RAIN_WEB_API_KEY=your-secret-key python run.py --web
```

Clients must send `X-API-Key: your-secret-key` on `/chat` requests.

Drift Monitoring (Cron)

1. Create baseline: `python scripts/drift_check.py`
2. Add to crontab: `0 2 * * * /path/to/scripts/cron_drift_check.sh`
3. Optional: Set `RAIN_DRIFT_WEBHOOK=https://your-alert-endpoint/drift` for alerts

Memory Hygiene (Periodic)

Scan for policy-violating content:

```bash
python scripts/memory_hygiene.py        # Report only
python scripts/memory_hygiene.py --fix  # Delete flagged (use with care)
```

Security Checklist

- [ ] Set `RAIN_WEB_API_KEY` if exposing web UI
- [ ] Run behind reverse proxy (nginx, Caddy) for HTTPS
- [ ] Restrict network access to Ollama/API endpoints
- [ ] Backup `data/` regularly
- [ ] Run `python scripts/memory_hygiene.py` periodically
- [ ] Schedule drift check (cron + webhook)
