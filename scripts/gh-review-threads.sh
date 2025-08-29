#!/usr/bin/env bash
set -euo pipefail

# gh-review-threads.sh
#
# List, resolve, and unresolve GitHub Pull Request review threads via GraphQL using gh CLI.
#
# Requirements:
# - gh (authenticated with write access if resolving)
# - jq
#
# Usage examples:
#   scripts/gh-review-threads.sh --owner Rokurolize --repo discord-voice-bot --pr 4 list-unresolved
#   scripts/gh-review-threads.sh --owner Rokurolize --repo discord-voice-bot --pr 4 resolve-all-unresolved
#   scripts/gh-review-threads.sh --owner Rokurolize --repo discord-voice-bot --pr 4 resolve-by-discussion-ids 2308929360 2308929366
#   scripts/gh-review-threads.sh --owner Rokurolize --repo discord-voice-bot --pr 4 resolve-by-urls \
#     https://github.com/Rokurolize/discord-voice-bot/pull/4#discussion_r2308929360 \
#     https://github.com/Rokurolize/discord-voice-bot/pull/4#discussion_r2308929366
#   DRY_RUN=1 scripts/gh-review-threads.sh --owner ... --repo ... --pr ... resolve-all-unresolved
#
# Notes:
# - Resolve/Unresolve live in GitHub GraphQL API (not REST).
# - discussion_rNNNNN is a review comment databaseId (REST id), which we map to its thread.id first.

DRY_RUN="${DRY_RUN:-0}"

print_usage() {
  cat <<'USAGE'
gh-review-threads.sh — manage PR review threads (GraphQL)

Flags:
  --owner <org/user>     GitHub repository owner (default: $GH_OWNER)
  --repo  <name>         GitHub repository name  (default: $GH_REPO)
  --pr    <number>       Pull request number     (default: $GH_PR)

Environment:
  GH_OWNER, GH_REPO, GH_PR — defaults for flags above
  DRY_RUN=1 — show actions without mutating

Subcommands:
  list                  List all threads with status and comment ids
  list-unresolved       List only unresolved threads
  resolve-all-unresolved  Resolve every unresolved thread
  resolve-by-discussion-ids <id ...>
                        Resolve threads containing the given discussion_r numeric IDs
  resolve-by-urls <url ...>
                        Resolve threads referenced by discussion_r URLs
  unresolve-thread-ids <thread-id ...>
                        Unresolve threads by GraphQL thread node ids

Examples:
  scripts/gh-review-threads.sh --owner O --repo R --pr 4 list-unresolved
  scripts/gh-review-threads.sh --owner O --repo R --pr 4 resolve-all-unresolved
  scripts/gh-review-threads.sh --owner O --repo R --pr 4 resolve-by-discussion-ids 123 456
  scripts/gh-review-threads.sh --owner O --repo R --pr 4 resolve-by-urls \
    https://github.com/O/R/pull/4#discussion_r123 https://github.com/O/R/pull/4#discussion_r456
USAGE
}

abort() { echo "Error: $*" >&2; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || abort "missing dependency: $1"; }

need_cmd gh
need_cmd jq

OWNER="${GH_OWNER:-}"
REPO="${GH_REPO:-}"
PR_NUMBER="${GH_PR:-}"

# Parse flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner) OWNER="${2:-}"; shift 2 ;;
    --repo)  REPO="${2:-}"; shift 2 ;;
    --pr)    PR_NUMBER="${2:-}"; shift 2 ;;
    -h|--help) print_usage; exit 0 ;;
    list|list-unresolved|resolve-all-unresolved|resolve-by-discussion-ids|resolve-by-urls|unresolve-thread-ids)
      SUBCOMMAND="$1"; shift; break ;;
    *) echo "Unknown arg: $1" >&2; print_usage; exit 1 ;;
  esac
done

[[ -n "${SUBCOMMAND:-}" ]] || { print_usage; exit 1; }
[[ -n "$OWNER" ]] || abort "--owner or GH_OWNER required"
[[ -n "$REPO"  ]] || abort "--repo or GH_REPO required"
[[ -n "$PR_NUMBER" ]] || abort "--pr or GH_PR required"

info() { printf '%s\n' "$*" >&2; }

# Fetch all review threads for the PR with pagination; outputs a JSON array of nodes
fetch_threads() {
  local after
  local threads_json='[]'

  # First page (no 'after')
  local resp
  resp=$(gh api graphql \
    -F owner="$OWNER" -F name="$REPO" -F number="$PR_NUMBER" \
    -f query='
      query($owner:String!, $name:String!, $number:Int!) {
        repository(owner:$owner, name:$name) {
          pullRequest(number:$number) {
            reviewThreads(first: 100) {
              pageInfo { hasNextPage endCursor }
              nodes {
                id
                isResolved
                isOutdated
                comments(first: 100) { nodes { databaseId url } }
              }
            }
          }
        }
      }
    ')

  threads_json=$(jq '.data.repository.pullRequest.reviewThreads.nodes' <<<"$resp")
  local hasNext endCursor
  hasNext=$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage' <<<"$resp")
  endCursor=$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor' <<<"$resp")

  # Subsequent pages
  while [[ "$hasNext" == "true" && -n "$endCursor" && "$endCursor" != "null" ]]; do
    resp=$(gh api graphql \
      -F owner="$OWNER" -F name="$REPO" -F number="$PR_NUMBER" -F after="$endCursor" \
      -f query='
        query($owner:String!, $name:String!, $number:Int!, $after:String!) {
          repository(owner:$owner, name:$name) {
            pullRequest(number:$number) {
              reviewThreads(first: 100, after: $after) {
                pageInfo { hasNextPage endCursor }
                nodes {
                  id
                  isResolved
                  isOutdated
                  comments(first: 100) { nodes { databaseId url } }
                }
              }
            }
          }
        }
      ')

    threads_json=$(jq -sc '.[0] + .[1]' <(printf '%s' "$threads_json") <(jq '.data.repository.pullRequest.reviewThreads.nodes' <<<"$resp"))
    hasNext=$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage' <<<"$resp")
    endCursor=$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor' <<<"$resp")
  done

  printf '%s\n' "$threads_json"
}

# Resolve a thread id
resolve_thread() {
  local tid="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    info "DRY_RUN: would resolve thread $tid"
    return 0
  fi
  gh api graphql -f query='
    mutation($t:ID!) {
      resolveReviewThread(input:{threadId:$t}) {
        thread { id isResolved }
      }
    }
  ' -F t="$tid" --jq '.data.resolveReviewThread.thread'
}

# Unresolve a thread id
unresolve_thread() {
  local tid="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    info "DRY_RUN: would unresolve thread $tid"
    return 0
  fi
  gh api graphql -f query='
    mutation($t:ID!) {
      unresolveReviewThread(input:{threadId:$t}) {
        thread { id isResolved }
      }
    }
  ' -F t="$tid" --jq '.data.unresolveReviewThread.thread'
}

# Map discussion_r numeric ids -> unique thread ids using a threads JSON array
map_discussion_ids_to_threads() {
  local threads_json="$1"; shift
  if [[ $# -eq 0 ]]; then return 0; fi
  local ids_json
  # Build JSON array of ids
  ids_json=$(printf '%s\n' "$@" | jq -R . | jq -s .)
  jq -r --argjson ids "$ids_json" '
    [ .[] as $t | $ids[] as $cid | ($t | select(.comments.nodes | any(.databaseId == ($cid|tonumber))) | .id) ]
    | unique | .[]
  ' <<<"$threads_json"
}

# Extract numeric ids from discussion_r URLs
extract_ids_from_urls() {
  for u in "$@"; do
    case "$u" in
      *"discussion_r"*)
        printf '%s\n' "${u##*discussion_r}" | tr -cd '0-9' ;;
      *) ;;
    esac
  done
}

# Render a readable list of (un)resolved threads
render_threads() {
  local threads_json="$1"; shift
  local filter="$1"; shift || true
  jq -r "$filter | .[] | [.id, (if .isResolved then \"resolved\" else \"unresolved\" end), (.comments.nodes | length), ((.comments.nodes | map(.databaseId) | join(\",\")) // \"\")] | @tsv" <<<"$threads_json" |
  awk -F'\t' 'BEGIN{printf("%s\t%s\t%s\t%s\n","thread_id","status","comments","comment_databaseIds");} {print}'
}

# Main subcommand handlers
case "$SUBCOMMAND" in
  list)
    threads=$(fetch_threads)
    render_threads "$threads" '.'
    ;;

  list-unresolved)
    threads=$(fetch_threads)
    render_threads "$threads" '[ .[] | select(.isResolved == false) ]'
    ;;

  resolve-all-unresolved)
    info "Fetching threads…"
    threads=$(fetch_threads)
    mapfile -t tids < <(jq -r '.[] | select(.isResolved == false) | .id' <<<"$threads")
    if [[ ${#tids[@]} -eq 0 ]]; then
      info "No unresolved threads found."
      exit 0
    fi
    info "Resolving ${#tids[@]} threads…"
    for t in "${tids[@]}"; do
      resolve_thread "$t"
    done
    ;;

  resolve-by-discussion-ids)
    [[ $# -gt 0 ]] || abort "provide at least one discussion_r numeric id"
    threads=$(fetch_threads)
    mapfile -t tids < <(map_discussion_ids_to_threads "$threads" "$@")
    if [[ ${#tids[@]} -eq 0 ]]; then
      abort "no matching threads found for provided discussion ids"
    fi
    info "Resolving ${#tids[@]} threads mapped from discussion ids…"
    for t in "${tids[@]}"; do
      resolve_thread "$t"
    done
    ;;

  resolve-by-urls)
    [[ $# -gt 0 ]] || abort "provide at least one discussion_r URL"
    # Extract numeric ids and reuse resolver
    mapfile -t ids < <(extract_ids_from_urls "$@" | awk 'NF')
    if [[ ${#ids[@]} -eq 0 ]]; then
      abort "no discussion_r ids could be extracted from URLs"
    fi
    "$0" --owner "$OWNER" --repo "$REPO" --pr "$PR_NUMBER" resolve-by-discussion-ids "${ids[@]}"
    ;;

  unresolve-thread-ids)
    [[ $# -gt 0 ]] || abort "provide at least one thread node id"
    info "Unresolving $# thread(s)…"
    for t in "$@"; do
      unresolve_thread "$t"
    done
    ;;

  *)
    print_usage; exit 1 ;;
esac

