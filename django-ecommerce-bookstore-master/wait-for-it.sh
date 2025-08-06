#!/bin/sh
# wait-for-it.sh

# A script to wait for a service to be available on a given host and port.
# This is a robust way to handle service dependencies in Docker Compose.

TIMEOUT=15
QUIET=0
WAITFORIT_host=
WAITFORIT_port=
WAITFORIT_command=
WAITFORIT_child=$!

# Parse command-line arguments.
while [ $# -gt 0 ]; do
  case "$1" in
    *:* )
    WAITFORIT_host=$(printf "%s\n" "$1"| cut -d : -f 1)
    WAITFORIT_port=$(printf "%s\n" "$1"| cut -d : -f 2)
    ;;
    -t)
    TIMEOUT="$2"
    if [ "$TIMEOUT" -le 0 ]; then
      echo "Error: timeout must be a positive integer" >&2
      exit 1
    fi
    shift
    ;;
    -q | --quiet)
    QUIET=1
    ;;
    --)
    shift
    WAITFORIT_command="$@"
    break
    ;;
    * )
    WAITFORIT_host=$(printf "%s\n" "$1"| cut -d : -f 1)
    WAITFORIT_port=$(printf "%s\n" "$1"| cut -d : -f 2)
    ;;
  esac
  shift
done

if [ -z "$WAITFORIT_host" ] || [ -z "$WAITFORIT_port" ]; then
  echo "Error: host and port must be specified" >&2
  exit 1
fi

# Main waiting loop.
i=0
while [ $i -lt $TIMEOUT ]; do
  if [ $QUIET -eq 0 ]; then
    echo "Waiting for $WAITFORIT_host:$WAITFORIT_port... ($i/$TIMEOUT)"
  fi
  # Use netcat to check if the port is open.
  if nc -z "$WAITFORIT_host" "$WAITFORIT_port"; then
    if [ $QUIET -eq 0 ]; then
      echo "Success: $WAITFORIT_host:$WAITFORIT_port is available!"
    fi
    break
  fi
  sleep 1
  i=$((i+1))
done

if [ $i -eq $TIMEOUT ]; then
  echo "Error: Timeout reached. $WAITFORIT_host:$WAITFORIT_port is not available." >&2
  exit 1
fi

# Execute the final command if it was provided.
if [ -n "$WAITFORIT_command" ]; then
  exec sh -c "$WAITFORIT_command"
fi
