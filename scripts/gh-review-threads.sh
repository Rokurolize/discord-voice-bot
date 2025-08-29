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
  --host  <hostname>     GitHub hostname (default: $GH_HOST or github.com)

Environment:
  GH_OWNER, GH_REPO, GH_PR — defaults for flags above
  DRY_RUN=1 — show actions without mutating
  GH_HOST — overrides GitHub hostname (e.g., ghe.company.com)

Subcommands:
  list                     List all threads (id/status/comment ids)
  list-unresolved          List only unresolved threads (id/status/comment ids)
  list-details             List all threads with per-comment details (path/url/body)
  list-unresolved-details  List only unresolved threads with per-comment details
  list-unresolved-details-full
                           List unresolved threads with FULL bodies (no truncation)
  list-unresolved-json     Dump unresolved thread nodes (JSON) including bodies/diffs
  list-unresolved-xml      Dump unresolved threads as XML with full bodies
  list-unresolved-ndjson   Dump unresolved comments as NDJSON (one JSON per line)
  resolve-all-unresolved   Resolve every unresolved thread
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

# Ensure gh is authenticated (mutations require auth; queries often do too)
ensure_gh_auth() {
  if ! gh auth status -h "$HOST" >/dev/null 2>&1; then
    abort "gh is not authenticated to $HOST. Run: gh auth login -h $HOST"
  fi
}

OWNER="${GH_OWNER:-}"
REPO="${GH_REPO:-}"
PR_NUMBER="${GH_PR:-}"
HOST="${GH_HOST:-github.com}"

# Parse flags (allow flags before or after subcommand)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner)
      if [[ -z "${2:-}" || "${2}" == --* ]]; then
        abort "--owner requires a value"
      fi
      OWNER="${2}"; shift 2 ;;
    --repo)
      if [[ -z "${2:-}" || "${2}" == --* ]]; then
        abort "--repo requires a value"
      fi
      REPO="${2}"; shift 2 ;;
    --pr)
      if [[ -z "${2:-}" || "${2}" == --* ]]; then
        abort "--pr requires a value"
      fi
      if ! [[ "${2}" =~ ^[0-9]+$ ]]; then
        abort "--pr must be an integer"
      fi
      PR_NUMBER="${2}"; shift 2 ;;
    --host|--hostname)
      if [[ -z "${2:-}" || "${2}" == --* ]]; then
        abort "--host requires a value"
      fi
      HOST="${2}"; shift 2 ;;
    -h|--help) print_usage; exit 0 ;;
    list|list-unresolved|list-details|list-unresolved-details|list-unresolved-details-full|list-unresolved-json|list-unresolved-xml|list-unresolved-ndjson|resolve-all-unresolved|resolve-by-discussion-ids|resolve-by-urls|unresolve-thread-ids)
      SUBCOMMAND="${SUBCOMMAND:-$1}"; shift; continue ;;
    *)
      if [[ -n "${SUBCOMMAND:-}" ]]; then
        # Treat remaining args as positional for the subcommand
        break
      else
        echo "Unknown arg: $1" >&2; print_usage; exit 1
      fi ;;
  esac
done

[[ -n "${SUBCOMMAND:-}" ]] || { print_usage; exit 1; }
[[ -n "$OWNER" ]] || abort "--owner or GH_OWNER required"
[[ -n "$REPO"  ]] || abort "--repo or GH_REPO required"
[[ -n "$PR_NUMBER" ]] || abort "--pr or GH_PR required"

info() { printf '%s\n' "$*" >&2; }

# Verify authentication early for consistent UX
ensure_gh_auth

# readarray/mapfile compatibility for bash <4 (e.g., macOS default bash)
readarray_compat() {
  local __arrname="$1"; shift
  if command -v mapfile >/dev/null 2>&1; then
    # shellcheck disable=SC2178,SC2207
    mapfile -t "$__arrname" < <("$@")
  else
    local _line
    local _buf=()
    while IFS= read -r _line; do _buf+=("$_line"); done < <("$@")
    # shellcheck disable=SC2178
    eval "$__arrname=(\"\${_buf[@]}\")"
  fi
}

# Fetch all review threads for the PR with pagination; outputs a JSON array of nodes
fetch_threads() {
  local threads_json='[]'

  # First page (no 'after')
  local resp
  if ! resp=$(gh api --hostname "$HOST" graphql \
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
                comments(first: 100) { nodes { databaseId url path body diffHunk } }
              }
            }
          }
        }
      }
    '); then
    abort "Failed to fetch review threads via gh api (initial page)"
  fi
  # Detect GraphQL errors
  if jq -e '.errors and (.errors | length > 0)' >/dev/null 2>&1 <<<"$resp"; then
    abort "GraphQL returned errors on initial page: $(jq -c '.errors' <<<"$resp")"
  fi

  threads_json=$(jq '(.data.repository.pullRequest.reviewThreads.nodes // [])' <<<"$resp")
  local hasNext endCursor
  hasNext=$(jq -r '(.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage // false)' <<<"$resp")
  endCursor=$(jq -r '(.data.repository.pullRequest.reviewThreads.pageInfo.endCursor // "")' <<<"$resp")

  # Subsequent pages
  while [[ "$hasNext" == "true" && -n "$endCursor" && "$endCursor" != "null" ]]; do
    if ! resp=$(gh api --hostname "$HOST" graphql \
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
                  comments(first: 100) { nodes { databaseId url path body diffHunk } }
                }
              }
            }
          }
        }
      '); then
      abort "Failed to fetch review threads via gh api (paged)"
    fi

    # Detect GraphQL errors on page
    if jq -e '.errors and (.errors | length > 0)' >/dev/null 2>&1 <<<"$resp"; then
      abort "GraphQL returned errors on paged fetch: $(jq -c '.errors' <<<"$resp")"
    fi

    threads_json=$(jq -sc '.[0] + .[1]' <(printf '%s' "$threads_json") <(jq '(.data.repository.pullRequest.reviewThreads.nodes // [])' <<<"$resp"))
    hasNext=$(jq -r '(.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage // false)' <<<"$resp")
    endCursor=$(jq -r '(.data.repository.pullRequest.reviewThreads.pageInfo.endCursor // "")' <<<"$resp")
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
  local out
  if ! out=$(gh api --hostname "$HOST" graphql -f query='
    mutation($t:ID!) {
      resolveReviewThread(input:{threadId:$t}) {
        thread { id isResolved }
      }
    }
  ' -F t="$tid" --jq '.data.resolveReviewThread.thread'); then
    abort "Failed to resolve thread $tid via gh api"
  fi
  printf '%s\n' "$out"
}

# Unresolve a thread id
unresolve_thread() {
  local tid="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    info "DRY_RUN: would unresolve thread $tid"
    return 0
  fi
  local out
  if ! out=$(gh api --hostname "$HOST" graphql -f query='
    mutation($t:ID!) {
      unresolveReviewThread(input:{threadId:$t}) {
        thread { id isResolved }
      }
    }
  ' -F t="$tid" --jq '.data.unresolveReviewThread.thread'); then
    abort "Failed to unresolve thread $tid via gh api"
  fi
  printf '%s\n' "$out"
}

# Map discussion_r numeric ids -> unique thread ids using a threads JSON array
map_discussion_ids_to_threads() {
  local threads_json="$1"; shift
  if [[ $# -eq 0 ]]; then return 0; fi
  local ids_json
  # Build JSON array of ids
  ids_json=$(printf '%s\n' "$@" | jq -R . | jq -s .)
  jq -r --argjson ids "$ids_json" '
    [ .[] as $t | $ids[] as $cid | ($t | select((.comments.nodes // []) | any(.databaseId == ($cid|tonumber))) | .id) ]
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
  jq -r "$filter | .[] | [.id, (if .isResolved then \"resolved\" else \"unresolved\" end), ((.comments.nodes // []) | length), (((.comments.nodes // []) | map(.databaseId) | join(\",\")) // \"\")] | @tsv" <<<"$threads_json" |
  awk -F'\t' 'BEGIN{printf("%s\t%s\t%s\t%s\n","thread_id","status","comments","comment_databaseIds");} {print}'
}

# Render detailed per-comment rows with truncated body preview
render_comment_details() {
  local threads_json="$1"; shift
  local filter="$1"; shift || true
  local max_len="${1:-200}"; shift || true
  # sanitize and clamp to [200,400]
  if ! [[ "$max_len" =~ ^[0-9]+$ ]]; then max_len=200; fi
  if (( max_len < 200 )); then max_len=200; elif (( max_len > 400 )); then max_len=400; fi
  jq -r --argjson max "$max_len" "$filter | .[] as \$t | (\$t.comments.nodes[] | {tid: \$t.id, resolved: (if \$t.isResolved then \"resolved\" else \"unresolved\" end), outdated: \$t.isOutdated} + .) | [.tid, .resolved, .outdated, .path, .databaseId, .url, ((.body // \"\") | gsub(\"\\n\";\" \") | .[0:\$max])] | @tsv" <<<"$threads_json" |
  awk -F'\t' 'BEGIN{printf("%s\t%s\t%s\t%s\t%s\t%s\t%s\n","thread_id","status","outdated","path","comment_id","url","body_preview");} {print}'
}

# Render detailed rows with full, untruncated body
render_comment_details_full() {
  local threads_json="$1"; shift
  local filter="$1"; shift || true
  jq -r "$filter | .[] as \$t | (\$t.comments.nodes[] | {tid: \$t.id, resolved: (if \$t.isResolved then \"resolved\" else \"unresolved\" end), outdated: \$t.isOutdated} + .) | [.tid, .resolved, .outdated, .path, .databaseId, .url, ((.body // \"\") | gsub(\"\\n\";\" \") )] | @tsv" <<<"$threads_json" |
  awk -F'\t' 'BEGIN{printf("%s\t%s\t%s\t%s\t%s\t%s\t%s\n","thread_id","status","outdated","path","comment_id","url","body");} {print}'
}

# Emit NDJSON (newline-delimited JSON) for unresolved comments with full bodies
render_unresolved_ndjson() {
  local threads_json="$1"; shift
  jq -c '.[] | select(.isResolved == false) as $t | $t.comments.nodes[]? | {
    thread_id: $t.id,
    status: (if $t.isResolved then "resolved" else "unresolved" end),
    outdated: $t.isOutdated,
    path, databaseId, url, body, diffHunk
  }' <<<"$threads_json"
}

# Render unresolved threads as XML with full bodies
render_unresolved_xml() {
  local threads_json="$1"; shift
  printf '%s\n' "<reviewThreads>"
  jq -r '
    def esc: (.|tostring)
      | gsub("&";"&amp;")
      | gsub("<";"&lt;")
      | gsub(">";"&gt;")
      | gsub("\"";"&quot;")
      | gsub("'"'"'";"&apos;");
    .[] | select(.isResolved == false) |
    "  <thread id=\"" + (.id|esc) + "\" status=\"" + (if .isResolved then "resolved" else "unresolved" end) + "\" outdated=\"" + (if .isOutdated then "true" else "false" end) + "\">\n"
    + ( [ .comments.nodes[]? |
          "    <comment id=\"" + ((.databaseId|tostring)|esc) + "\">\n"
          + "      <path>" + ((.path // "")|esc) + "</path>\n"
          + "      <url>" + ((.url // "")|esc) + "</url>\n"
          + "      <body>" + ((.body // "")|esc) + "</body>\n"
          + "      <diffHunk>" + ((.diffHunk // "")|esc) + "</diffHunk>\n"
          + "    </comment>\n" ] | join("") )
    + "  </thread>"
  ' <<<"$threads_json"
  printf '%s\n' "</reviewThreads>"
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

  list-details)
    threads=$(fetch_threads)
    render_comment_details "$threads" '.' 400
    ;;

  list-unresolved-details)
    threads=$(fetch_threads)
    render_comment_details "$threads" '[ .[] | select(.isResolved == false) ]' 400
    ;;

  list-unresolved-details-full)
    threads=$(fetch_threads)
    render_comment_details_full "$threads" '[ .[] | select(.isResolved == false) ]'
    ;;

  list-unresolved-json)
    threads=$(fetch_threads)
    jq '[ .[] | select(.isResolved == false) ]' <<<"$threads"
    ;;

  list-unresolved-xml)
    threads=$(fetch_threads)
    render_unresolved_xml "$threads"
    ;;

  list-unresolved-ndjson)
    threads=$(fetch_threads)
    render_unresolved_ndjson "$threads"
    ;;

  resolve-all-unresolved)
    info "Fetching threads…"
    threads=$(fetch_threads)
    declare -a tids=()
    readarray_compat tids bash -lc 'jq -r '\''.[] | select(.isResolved == false) | .id'\'' <<<"$threads"'
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
    declare -a tids=()
    readarray_compat tids map_discussion_ids_to_threads "$threads" "$@"
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
    # Provide a wrapper that applies NF filter without spawning a subshell that loses function scope
    extract_ids_filtered() {
      extract_ids_from_urls "$@" | awk 'NF'
    }
    declare -a ids=()
    readarray_compat ids extract_ids_filtered "$@"
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