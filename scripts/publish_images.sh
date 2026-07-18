#!/usr/bin/env bash
# Publish the license-permissive Lazarus component images to GHCR.
#
# Only images whose upstream license permits redistribution are listed here
# (Apache-2.0 / MIT). HELD, do NOT publish:
#   • dmasif  — CC BY-NC-ND (no derivatives; a resurrected image is a derivative)
#   • basset  — license unclear ("see source repo"); verify upstream first
# Those are rebuilt locally by users via Lazarus (see docs/IMAGES.md).
#
# Prereq (auth is YOURS to do — this script never handles credentials):
#   echo "$GHCR_PAT" | docker login ghcr.io -u <your-github-user> --password-stdin
#   …on whichever docker host holds the images (set DOCKER_HOST to point there).
#
# Usage:
#   DOCKER_HOST=ssh://you@your-gpu-box NS=ghcr.io/doctordean scripts/publish_images.sh
#
set -euo pipefail

NS="${NS:-ghcr.io/doctordean}"          # GHCR namespace (your github owner, lowercased)
SRC="${DOCKER_HOST:-}"                   # docker host holding the images (empty = local)
DOCKER="${DOCKER:-docker}"

# local source tag  |  GHCR destination (name:tag)
MAP=(
  "lazarus/masif:site-ready|$NS/lazarus-masif:site-ready"
  "lazarus/scannet:ppi-noMSA-proven|$NS/lazarus-scannet:ppi-noMSA-proven"
  "lazarus/fpocket:working|$NS/lazarus-fpocket:working"
  "lazarus/diffdock:site-ready|$NS/lazarus-diffdock:site-ready"
  # promoted from the N=20 benchmark (permissive: MIT / Apache-2.0)
  "lazarus/dlm:working|$NS/lazarus-dlm:working"
  "lazarus/hitea:working|$NS/lazarus-hitea:working"
  "lazarus/dnafeaturesviewer:genbank-plot-ready|$NS/lazarus-dnafeaturesviewer:genbank-plot-ready"
  "lazarus/coconet:working|$NS/lazarus-coconet:working"
  # SE(3)-equivariant docking, MIT (from the comp-bio pilot)
  "lazarus/equidock:working|$NS/lazarus-equidock:working"
  "lazarus/equibind:contract-ready|$NS/lazarus-equibind:contract-ready"
  # HELD pending an image slim (54.5 GB is impractical to publish/pull):
  # "lazarus/sequoya:nsgaii-ready|$NS/lazarus-sequoya:nsgaii-ready"
)

hostflag=(); [ -n "$SRC" ] && hostflag=(-H "$SRC")

echo "Publishing to $NS  (source docker: ${SRC:-local})"
echo "Make sure you've run 'docker login ghcr.io' on that host first."
echo

pushed=0
for pair in "${MAP[@]}"; do
  local_tag="${pair%%|*}"; ghcr_ref="${pair##*|}"
  echo "→ $local_tag  →  $ghcr_ref"
  if ! "$DOCKER" "${hostflag[@]}" image inspect "$local_tag" >/dev/null 2>&1; then
    echo "  ✗ source image not found on this docker host — skipping"; continue
  fi
  "$DOCKER" "${hostflag[@]}" tag "$local_tag" "$ghcr_ref"
  "$DOCKER" "${hostflag[@]}" push "$ghcr_ref"
  echo "  ✓ pushed"
  pushed=$((pushed + 1))
done

echo
echo "Pushed $pushed image(s)."
echo "Next (one-time, in the GHCR web UI): set each package's visibility to Public."
echo "Then mark them public in the registry:"
echo "  • add image_public=True to those 4 entries in scripts/build_registry.py"
echo "  • rerun: python scripts/build_registry.py"
