# Deployment Verification Checklist

## Services Status
- [ ] Web server running
- [ ] Database connected
- [ ] Redis cache connected

## Health Checks
- Web server: `curl http://localhost:8000/health`
- API: `curl http://localhost:8000/api/health`

## Rollback Plan
If deployment fails:
1. Restore previous version: `./scripts/rollback.sh`
2. Check logs: `./scripts/logs.sh`
