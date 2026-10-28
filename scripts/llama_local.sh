#!/usr/bin/env bash
# Modèle local sans API : compile llama-server (CPU), télécharge le modèle GGUF, lance le serveur.
# Usage : scripts/llama_local.sh [installer|lancer|arreter]   (défaut : installer puis lancer)
# Réseau requis : pypi.org (source llama.cpp) et huggingface.co (poids du modèle).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="${LLAMA_DIR:-$ROOT/.local/llama}"
VERSION="${LLAMA_CPP_PYTHON_VERSION:-0.3.36}"  # le paquet PyPI embarque les sources de llama.cpp
MODEL_URL="${LLAMA_MODEL_URL:-https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf}"
ALIAS="${LLAMA_ALIAS:-qwen3-4b}"  # doit correspondre au modèle « openai/<alias> » de megatron/llm.py
PORT="${LLAMA_PORT:-8080}"
BIN="$DIR/bin/llama-server"
MODEL="$DIR/models/$(basename "$MODEL_URL")"

installer() {
  mkdir -p "$DIR/bin" "$DIR/models" "$DIR/src"
  if [ ! -x "$BIN" ]; then
    python3 -m pip download --no-deps --no-binary :all: -q -d "$DIR/src" "llama-cpp-python==$VERSION"
    tar xzf "$DIR/src/llama_cpp_python-$VERSION.tar.gz" -C "$DIR/src"
    local src="$DIR/src/llama_cpp_python-$VERSION/vendor/llama.cpp"
    cmake -S "$src" -B "$src/build" -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF -DGGML_NATIVE=ON -DBUILD_SHARED_LIBS=OFF \
      -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF >/dev/null
    cmake --build "$src/build" --target llama-server -j"$(nproc)" >/dev/null
    cp "$src/build/bin/llama-server" "$BIN"
  fi
  if [ ! -s "$MODEL" ]; then
    curl -fL --retry 4 -o "$MODEL.part" "$MODEL_URL"
    mv "$MODEL.part" "$MODEL"
  fi
  echo "prêt : $BIN + $MODEL"
}

lancer() {
  # --reasoning-budget 0 coupe le mode « réflexion » de Qwen3 : réponses JSON directes.
  nohup "$BIN" -m "$MODEL" --alias "$ALIAS" --host 127.0.0.1 --port "$PORT" -c 8192 -t "$(nproc)" \
    --jinja --reasoning-budget 0 >"$DIR/server.log" 2>&1 &
  echo $! >"$DIR/server.pid"
  for _ in $(seq 1 120); do
    if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null; then
      echo "llama-server prêt sur http://127.0.0.1:$PORT/v1 (journal : $DIR/server.log)"; return 0
    fi
    sleep 1
  done
  echo "llama-server ne répond pas, voir $DIR/server.log" >&2; return 1
}

arreter() { [ -f "$DIR/server.pid" ] && kill "$(cat "$DIR/server.pid")" && rm "$DIR/server.pid"; }

case "${1:-tout}" in
  installer) installer ;;
  lancer) lancer ;;
  arreter) arreter ;;
  tout) installer && lancer ;;
  *) echo "usage : $0 [installer|lancer|arreter]" >&2; exit 2 ;;
esac
