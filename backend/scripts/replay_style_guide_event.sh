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
  echo "Usage: ${0} AXOLOTL_STYLE_GUIDE_V4.pdf"
  exit 1
fi

OBJECT_NAME="$1"

: "${GCP__STYLE_GUIDE_BUCKET_NAME:?GCP__STYLE_GUIDE_BUCKET_NAME est requis}"

API_BASE_URL="${API_BASE_URL:-http://localhost:8080}"
CONTENT_TYPE="${STYLE_GUIDE_CONTENT_TYPE:-application/pdf}"

echo "Rejeu de l'événement Eventarc vers ${API_BASE_URL}/webhooks/eventarc/style-guide"
curl -i \
  -X POST "${API_BASE_URL}/webhooks/eventarc/style-guide" \
  -H "Content-Type: application/json" \
  -H "ce-type: google.cloud.storage.object.v1.finalized" \
  -d "{
    \"bucket\": \"${GCP__STYLE_GUIDE_BUCKET_NAME}\",
    \"name\": \"${OBJECT_NAME}\",
    \"contentType\": \"${CONTENT_TYPE}\"
  }"

echo
echo "Terminé."
echo "Objet GCS: gs://${GCP__STYLE_GUIDE_BUCKET_NAME}/${OBJECT_NAME}"
echo "Note: ce replay suppose que l'objet existe déjà dans le bucket."
echo "Temporal UI: http://localhost:8233"
echo "Endpoint API: ${API_BASE_URL}/webhooks/eventarc/style-guide"
