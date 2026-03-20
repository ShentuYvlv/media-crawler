#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${SCRIPT_DIR}/MediaCrawler"
UPSTREAM_URL="https://github.com/NanmiCoder/MediaCrawler.git"
UPSTREAM_BRANCH="main"
DELETE_MODE=0
FORCE_MODE=0

usage() {
  cat <<'EOF'
Usage:
  ./sync_mediacrawler.sh [--branch <name>] [--target <dir>] [--url <repo>] [--delete] [--force]

Options:
  --branch <name>   Upstream branch name. Default: main
  --target <dir>    Local target directory. Default: ./MediaCrawler
  --url <repo>      Upstream git URL. Default: https://github.com/NanmiCoder/MediaCrawler.git
  --delete          Delete files in target that do not exist upstream.
  --force           Continue even if target directory has uncommitted changes.
  -h, --help        Show this help message.

Examples:
  ./sync_mediacrawler.sh
  ./sync_mediacrawler.sh --branch main
  ./sync_mediacrawler.sh --delete
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      UPSTREAM_BRANCH="${2:-}"
      shift 2
      ;;
    --target)
      TARGET_DIR="${2:-}"
      shift 2
      ;;
    --url)
      UPSTREAM_URL="${2:-}"
      shift 2
      ;;
    --delete)
      DELETE_MODE=1
      shift
      ;;
    --force)
      FORCE_MODE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${UPSTREAM_BRANCH}" || -z "${UPSTREAM_URL}" || -z "${TARGET_DIR}" ]]; then
  echo "branch, url, and target must not be empty" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required" >&2
  exit 1
fi

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "target directory does not exist: ${TARGET_DIR}" >&2
  exit 1
fi

if git -C "${SCRIPT_DIR}" rev-parse --show-toplevel >/dev/null 2>&1; then
  if [[ "${FORCE_MODE}" -ne 1 ]]; then
    DIRTY_STATE="$(git -C "${SCRIPT_DIR}" status --porcelain -- "${TARGET_DIR}" || true)"
    if [[ -n "${DIRTY_STATE}" ]]; then
      echo "target directory has uncommitted changes. Commit/stash them first, or rerun with --force." >&2
      exit 1
    fi
  fi
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

echo "cloning upstream..."
git clone --depth 1 --branch "${UPSTREAM_BRANCH}" "${UPSTREAM_URL}" "${TMP_DIR}/upstream"

RSYNC_ARGS=(
  -a
  -v
  --exclude
  .git
)

if [[ "${DELETE_MODE}" -eq 1 ]]; then
  RSYNC_ARGS+=(--delete)
fi

echo "syncing files into ${TARGET_DIR}..."
rsync "${RSYNC_ARGS[@]}" "${TMP_DIR}/upstream/" "${TARGET_DIR}/"

echo
echo "sync complete."
echo "next steps:"
echo "  cd \"${SCRIPT_DIR}\""
echo "  git status"
echo "  git add MediaCrawler"
echo "  git commit -m \"sync MediaCrawler from upstream\""
echo "  git push origin HEAD"
