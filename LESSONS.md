# Lessons

A running log of what I'm learning while building `fiti` as CKAD prep — one
entry per concept, in the order I hit them. Co-written with my study partner as
we go: the partner explains the *why*, I run the commands on my own machine.

## Lesson 1 — Prove it works outside the container first

A container image is a **frozen copy of a working local environment**. The image
never fixes broken code — it faithfully reproduces it. So debug at the lowest
layer that reproduces the bug, never two layers up:

1. App runs on my machine → `uv run` starts uvicorn
2. App runs in a container → `docker run`
3. App runs in the cluster → `kubectl apply`, Pod is `Running`

Skip a layer and you're debugging your code *and* Docker *and* Kubernetes at the
same time. Every problem gets an order of magnitude harder to find.

## Lesson 2 — The Dockerfile is the app's frozen runtime

The image is the single source of truth for "what my app's runtime looks like."
A Pod later runs this exact image. What I learned from the uv-based Dockerfile:

- **`COPY --from=ghcr.io/astral-sh/uv ...`** borrows the `uv` binary from the
  official uv image instead of installing it with pip. `--from` means "copy out
  of an image, not the build context."
- **Manifest before code is a caching trick.** Copy `pyproject.toml` + `uv.lock`
  *before* `COPY app/ .`, so the `uv sync` layer only rebuilds when dependencies
  change — not on every code edit. Copy code first and you'd reinstall deps on
  every rebuild.
- **`.dockerignore` excludes `.venv/`** so the local Fedora venv never leaks into
  the image and stomps the image's own venv. Without it, the container would
  silently run Fedora binaries.
- **`uv sync --frozen`** installs exactly what `uv.lock` pins and errors if the
  lock is stale, instead of silently drifting. Reproducible builds.

## Lesson 3 — Docker → Kubernetes: the declarative shift

The mental model that changes everything:

- `docker run` is **imperative** — "do this now."
- `kubectl apply -f k8s/` is **declarative** — "make the cluster *look like this*."

I never say "start 2 containers." I declare a Deployment with 2 replicas, and a
controller loop makes the cluster match — and rebuilds a Pod if one dies. The
chain: `Deployment → ReplicaSet → Pods`, with the **scheduler** deciding which
node each Pod lands on (I never choose).

Two things that make this work with `kind`:

- **kind is not a registry.** `docker build` puts the image in my Docker daemon,
  but kind's nodes run their own containerd and can't see it. `kind load
  docker-image` copies the image *into* the kind nodes. That's why the Deployment
  says `imagePullPolicy: Never` — "the image is already loaded, don't pull."
- **Namespace discipline.** `kubectl config set-context --current --namespace=fiti`
  only edits my local kubeconfig — it does **not** create the namespace. I still
  have to `kubectl apply -f k8s/00-namespace.yaml` first. (Offline command vs
  online command.)

**Verified:** 2 pods running on `control-plane`; `/config` reports
`api_key_loaded: true` — a Secret in the cluster injected into the Pod with no
change to the image. Self-healing demo: `kubectl delete pod fiti-api-<name>` and
the ReplicaSet spawned a replacement almost instantly. The pod name is
`fiti-api-<rs-hash>-<pod-hash>` — after deletion the `rs-hash` stayed, the
`pod-hash` changed. Deployment → ReplicaSet → Pod, right there in the name.

## Lesson 4 — "Restart" means two different things

The word "restart" is two mechanisms, and conflating them costs points:

- **Container restart** (kubelet + `restartPolicy`): a *container* that crashes
  is restarted in the same pod — same name, same IP, `RESTARTS` climbs.
- **Pod recreation** (controller): a *pod* that's deleted is replaced by a new
  one (new name, new IP) — but only because a Deployment/ReplicaSet is watching.

A bare pod (`--restart=Never`) I delete is gone forever — nobody recreates it.
And `kubectl run nginx --image=nginx` doesn't even make a bare pod; it makes a
Deployment. `--restart=Never` is required for a true bare pod (exam trap).

To see it: `kubectl run crashy --image=busybox --restart=Always -- sh -c "exit 1"`
→ pod name never changes, `RESTARTS` climbs (container restart). Delete a
Deployment-managed pod → name changes (pod recreation).

## Lesson 5 — Rolling updates and rollback

`latest` is a moving pointer, not a version — two different images can both be
"latest", so Kubernetes can't tell when the image changed. Use versioned tags
(`fiti-api:v2`).

`maxSurge` and `maxUnavailable` are one rule — "grow first, then shrink":

- `maxSurge: 1` → at most 1 pod above the desired count (the "3").
- `maxUnavailable: 0` → never below the desired count (the "2").

With 2 replicas: `2 old → 3 → 2 → 3 → 2 new` — zero downtime.

```bash
docker build -t fiti-api:v2 .
kind load docker-image fiti-api:v2 --name ckad
kubectl set image deployment/fiti-api api=fiti-api:v2   # api = container name
kubectl rollout status deployment/fiti-api
kubectl rollout history deployment/fiti-api
kubectl rollout undo deployment/fiti-api                # rollback
```

Gotchas:

- `kubectl set image` changes the **live cluster**, not the YAML. Sync the YAML
  after, or the next `kubectl apply` rolls back to whatever the file says.
- The rollback was instant because the old image was still on the node under
  `:latest` (and `imagePullPolicy: Never` skips pulls). If `:latest` had been
  overwritten, the "rollback" would roll *forward*. Versioned tags make rollback
  meaningful.
