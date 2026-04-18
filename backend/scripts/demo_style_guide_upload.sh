#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOCAL_ENV_FILE="${ROOT_DIR}/.env.local"

if [[ -f "${LOCAL_ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${LOCAL_ENV_FILE}"
  set +a
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: ${0} /chemin/vers/guide-style.pdf"
  exit 1
fi

PDF_PATH="$1"
if [[ ! -f "${PDF_PATH}" ]]; then
  echo "Fichier introuvable: ${PDF_PATH}"
  exit 1
fi

: "${GCP__STYLE_GUIDE_BUCKET_NAME:?GCP__STYLE_GUIDE_BUCKET_NAME est requis}"

API_BASE_URL="${API_BASE_URL:-http://localhost:8080}"
STYLE_GUIDE_OBJECT_PREFIX="${STYLE_GUIDE_OBJECT_PREFIX:-dev/style-guides}"
FILE_BASENAME="$(basename "${PDF_PATH}")"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OBJECT_NAME="${STYLE_GUIDE_OBJECT_PREFIX}/${TIMESTAMP}-${FILE_BASENAME}"

echo "Upload du PDF dans gs://${GCP__STYLE_GUIDE_BUCKET_NAME}/${OBJECT_NAME}"
gcloud storage cp "${PDF_PATH}" "gs://${GCP__STYLE_GUIDE_BUCKET_NAME}/${OBJECT_NAME}"

echo "Rejeu de l'événement Eventarc vers ${API_BASE_URL}/webhooks/eventarc/style-guide"
curl -i \
  -X POST "${API_BASE_URL}/webhooks/eventarc/style-guide" \
  -H "Content-Type: application/json" \
  -H "ce-type: google.cloud.storage.object.v1.finalized" \
  -d "{
    \"bucket\": \"${GCP__STYLE_GUIDE_BUCKET_NAME}\",
    \"name\": \"${OBJECT_NAME}\",
    \"contentType\": \"application/pdf\"
  }"

echo
echo "Terminé."
echo "Objet GCS: gs://${GCP__STYLE_GUIDE_BUCKET_NAME}/${OBJECT_NAME}"
echo "Temporal UI: http://localhost:8233"
echo "Endpoint API: ${API_BASE_URL}/webhooks/eventarc/style-guide"
