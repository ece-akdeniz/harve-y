#!/usr/bin/env bash
set -euo pipefail

# This is the only command authorized for the CI SSH key. The account cannot
# open a shell, forward ports, or read the lab database and credentials.
[[ ${SSH_ORIGINAL_COMMAND:-} =~ ^deploy\ ([0-9a-f]{40})$ ]] || {
  echo 'Unsupported deploy command' >&2
  exit 2
}
sha=${BASH_REMATCH[1]}

base=/opt/y-agent-lab/deploy
exec 9>"$base/.lock"
flock -x 9

release="$base/releases/$sha"
previous=$(readlink "$base/current" || true)
mkdir -p "$release"
tar -xzf - -C "$release" --strip-components=1
cd "$release"
/usr/local/bin/uv sync --locked --no-dev --python /usr/bin/python3

ln -s "$release" "$base/current.next"
mv -Tf "$base/current.next" "$base/current"

rollback() {
  if [[ -n $previous ]]; then
    ln -s "$previous" "$base/current.next"
    mv -Tf "$base/current.next" "$base/current"
    sudo /bin/systemctl restart y-agent-lab || true
  fi
}

if ! sudo /bin/systemctl restart y-agent-lab; then
  rollback
  exit 1
fi

healthy=false
for _ in {1..30}; do
  if [[ $(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/runs || true) == 401 ]]; then
    healthy=true
    break
  fi
  sleep 1
done

if [[ $healthy != true ]]; then
  echo 'Lab health check failed; restoring previous release' >&2
  rollback
  exit 1
fi

echo "Deployed $sha"
