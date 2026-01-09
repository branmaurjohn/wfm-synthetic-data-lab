#!/usr/bin/env bash
set -euo pipefail

wfm-synth generate-pack scenarios/tiny_hospital_smoke.yaml --out-base .
PACK_PATH=$(ls -dt packs/tiny_hospital_smoke/* | head -n 1)

wfm-synth validate-pack "$PACK_PATH"
