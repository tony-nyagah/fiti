# fiti — a workout tracker that doubles as your CKAD lab

`fiti` is Swahili for "fit." It's a small FastAPI workout-tracking API whose real
job is to be the **thing you build** while studying for the CKAD.

It's also a working answer to a question: *can you run your own infrastructure
instead of renting someone else's?* Everything here runs on open infrastructure —
Linux containers, Kubernetes, open standards — deployed to a local cluster with no
vendor lock-in. Public money should buy public code; personal projects should run
on infrastructure you actually own.

## Why one project instead of a dry study repo

Your three goals collapse into one:

- **Fun project** → this API (something you'll actually use for your own gym tracking)
- **Open source** → public commits recruiters can read
- **CKAD** → every concept becomes a real feature of a working app

Each CKAD domain maps to a change you make *here*:

| CKAD Domain (weight) | What you do in fiti |
|---|---|
| 1. Application Design & Build (20%) | Multi-container pod, init containers, volumes |
| 2. Application Deployment (20%) | Rolling updates, rollbacks, Jobs (migrations), CronJobs (weekly summary) |
| 3. Observability & Maintenance (15%) | Liveness/readiness probes, logs, events |
| 4. Config & Security (25%) | ConfigMaps, Secrets, SecurityContexts, RBAC, resource limits |
| 5. Services & Networking (20%) | ClusterIP → NodePort → Ingress, NetworkPolicies |

## The rules (encoded from your CKAD plan)

1. **Never hand-write YAML from scratch** — generate with `kubectl create --dry-run=client -o yaml`, then edit in vim.
2. **Use vim for every edit** — no VS Code. It's your #1 exam bottleneck.
3. **Set the namespace first:** `kubectl config set-context --current --namespace=fiti`
4. **Commit after every session** — at least one commit per day.

## Run it locally

```bash
cd app
uv sync
uv run uvicorn main:app --reload
# open http://localhost:8000/docs
```

## Deploy to kind

```bash
docker build -t fiti-api:latest .
kind load docker-image fiti-api:latest --name ckad
kubectl apply -f k8s/
kubectl -n fiti get all
kubectl -n fiti port-forward svc/fiti-api 8080:80
# open http://localhost:8080/docs
```

## Endpoints

- `GET /` — service info
- `GET /health` — used by the liveness/readiness probes
- `GET /config` — proves ConfigMap + Secret are wired in (without leaking the secret)
- `GET /workouts`, `POST /workouts` — the actual API

## Roadmap (roughly = your study weeks)

- **Week 2:** add SQLite + a PersistentVolume; run a rolling update + rollback
- **Week 3:** NodePort/Ingress + a NetworkPolicy
- **Week 4:** real Secret via `kubectl create secret`, RBAC, tighten SecurityContexts
- **Week 5:** tune probes, `kubectl debug`, Jobs + CronJobs
