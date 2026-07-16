# Component images

Every revived tool in the registry is backed by a **pinned container image** — the
reconstructed, commit-era environment the tool actually runs in. This page covers how to
run a component from its image, and (for maintainers) how images are published.

## Where images live

License-permissive components are published to the **GitHub Container Registry (GHCR)** under
`ghcr.io/doctordean/lazarus-<name>`:

| Component | Image | License |
|---|---|:--:|
| MaSIF-site | `ghcr.io/doctordean/lazarus-masif:site-ready` | Apache-2.0 |
| ScanNet | `ghcr.io/doctordean/lazarus-scannet:ppi-noMSA-proven` | Apache-2.0 |
| fpocket | `ghcr.io/doctordean/lazarus-fpocket:working` | MIT |
| DiffDock | `ghcr.io/doctordean/lazarus-diffdock:site-ready` (GPU) | MIT |

Two components are **not** redistributed as images, for licensing reasons — you rebuild them
locally (Lazarus regenerates the exact environment):

| Component | Why held | How to get it |
|---|---|---|
| dMaSIF | CC BY-NC-ND — no-derivatives forbids redistributing a resurrected image | `lazarus resurrect https://github.com/FreyrS/dMaSIF` |
| Basset | upstream license unclear ("see source repo") — pending verification | `lazarus resurrect https://github.com/davek44/Basset` |

> If a `docker pull` of one of the GHCR images 404s, it hasn't been published yet — a
> maintainer needs to run the publish step below.

## Running a component

`lazarus pull <name>` fetches the contract bundle (an importable module, a CLI, and the smoke
test). The bundle runs against the entry's `base_image`. Pull the image and run its smoke test:

```bash
lazarus pull scannet_ppi_binding_sites
docker pull ghcr.io/doctordean/lazarus-scannet:ppi-noMSA-proven
# then run the contract's CLI/smoke test against that image; for GPU tools add --gpus all
```

Or let `lazarus run` handle it in a pipeline — it reads `base_image` from the registry and
executes against whatever `--docker-host` / `DOCKER_HOST` you point at (local, remote, or a
GPU box):

```bash
lazarus run <pipeline.yaml> --input structure=4ZQK.pdb --docker-host ssh://you@gpu-box
```

## Publishing images (maintainers)

Images are pushed with [`scripts/publish_images.sh`](../scripts/publish_images.sh). Auth is
yours to provide — the script never handles credentials.

1. Authenticate to GHCR on the host that holds the images (create a PAT with `write:packages`):
   ```bash
   echo "$GHCR_PAT" | docker login ghcr.io -u <your-github-user> --password-stdin
   ```
2. Push (point `DOCKER_HOST` at the host holding the images — e.g. the GPU box):
   ```bash
   DOCKER_HOST=ssh://you@your-gpu-box scripts/publish_images.sh
   ```
3. In the GHCR web UI, set each new package's visibility to **Public**.
4. Reflect it in the registry: add `image_public=True` to those entries in
   [`scripts/build_registry.py`](../scripts/build_registry.py) and rerun it
   (`python scripts/build_registry.py`).

Only add an image whose upstream license permits redistribution. When in doubt, leave it as a
rebuild-locally entry (like dMaSIF / Basset above) rather than publishing.
