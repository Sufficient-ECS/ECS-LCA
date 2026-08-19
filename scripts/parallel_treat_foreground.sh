#!/usr/bin/env bash

set -euo pipefail

echo "Beware, this script is not an automatic speed-up"
echo "It will only save time to treat a very big number"
echo "of foregrounds with small custom databases."

nproc="$1"
shift

treat_args=("$@")

p_value=""
t_value=""
o_value="./results"

yaml_files=()
child_pids=()

cleanup() {
    echo "Interrupt received, stopping child processes..."

    for pid in "${child_pids[@]:-}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done

    wait || true
    exit 130
}

trap cleanup SIGINT SIGTERM

while getopts ":p:t:c:o:m:i:e:v:" opt; do
    case "$opt" in
        p)
            p_value="$OPTARG"
            ;;
        t)
            t_value="$OPTARG"
            ;;
        o)
            o_value="$OPTARG"
            ;;
        :)
            # Missing argument: ignore
            ;;
        \?)
            # Unknown option: ignore
            ;;
    esac
done

for arg in "${treat_args[@]}"; do
    case "$arg" in
        *.yaml|*.yml)
            yaml_files+=("$arg")
            ;;
    esac
done

# Remove previous impact files
for yaml in "${yaml_files[@]}"; do
    stem=$(basename "$yaml")
    stem="${stem%.*}"

    rm -f "${o_value}/${stem}"*
done

setup_args=()

if [[ -n "$p_value" ]]; then
    setup_args+=("$p_value")
fi

if [[ -n "$t_value" ]]; then
    setup_args+=("$t_value")
fi

setup_args_py=$(printf "'%s'," "${setup_args[@]}")
setup_args_py="[${setup_args_py%,}]"


for ((i=0; i<nproc; i++)); do

    uv run python -c "from src import setup_project_ei; setup_project_ei('ECS-LCA-$i', $setup_args_py)"

done

for ((i=0; i<nproc; i++)); do

    ./scripts/treat_foreground.py -i $i "${treat_args[@]}" -e &
    child_pids+=("$!")

    sleep 2 # avoid synchronization which leads to lag spike

done

wait