#!/usr/bin/env bash
# Ждём, пока все сервисы стека postgres-ha станут X/X с X>=1 и совпадающими числами.
# Вызывается из CI между `docker stack deploy postgres-ha` и `docker stack deploy restful-slice`.
set -eu

STACK="${POSTGRES_HA_STACK_NAME:-postgres-ha}"
MAX_TRIES="${POSTGRES_HA_WAIT_MAX_TRIES:-180}"
SLEEP_SEC="${POSTGRES_HA_WAIT_SLEEP:-5}"

echo "[wait-postgres-ha] stack=$STACK (до ~$((MAX_TRIES * SLEEP_SEC / 60)) мин)"

attempt=1
while [ "$attempt" -le "$MAX_TRIES" ]; do
	if ! svc_out="$(docker stack services "$STACK" --format '{{.Name}}\t{{.Replicas}}' 2>/dev/null)"; then
		echo "[wait-postgres-ha] попытка $attempt: стек недоступен"
		sleep "$SLEEP_SEC"
		attempt=$((attempt + 1))
		continue
	fi

	ok=1
	cnt=0
	while IFS= read -r line; do
		[ -z "$line" ] && continue
		name="${line%%	*}"
		repl="${line#*	}"
		case "$name" in
			"${STACK}_"*) ;;
			*) continue ;;
		esac
		cnt=$((cnt + 1))
		before="${repl%%/*}"
		after="${repl#*/}"
		if [ "$before" != "$after" ] || [ "$before" = "0" ]; then
			ok=0
			if [ $((attempt % 12)) -eq 1 ]; then
				echo "[wait-postgres-ha] пока не готово: $name -> $repl"
			fi
		fi
	done <<EOF
$svc_out
EOF

	if [ "$cnt" -eq 0 ]; then
		echo "[wait-postgres-ha] попытка $attempt: нет сервисов $STACK_* — ждём"
		sleep "$SLEEP_SEC"
		attempt=$((attempt + 1))
		continue
	fi

	if [ "$ok" -eq 1 ]; then
		echo "[wait-postgres-ha] все $cnt сервисов имеют нужные replicas:"
		echo "$svc_out"
		exit 0
	fi

	sleep "$SLEEP_SEC"
	attempt=$((attempt + 1))
done

echo "[wait-postgres-ha] TIMEOUT после $MAX_TRIES попыток — диагностика:" >&2
docker stack services "$STACK" >&2 || true
echo "--- etcd0 ---" >&2
docker service ps "${STACK}_etcd0" --no-trunc >&2 | head -20 || true
echo "--- patroni_spilo_a ---" >&2
docker service ps "${STACK}_patroni_spilo_a" --no-trunc >&2 | head -20 || true
exit 1
