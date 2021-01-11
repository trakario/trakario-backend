#!/usr/bin/env bash

#############################################
set -e; cd "$(dirname "$0")" # Script Start #
#############################################

[[ -f .venv/bin/python ]] || python3 -m venv .venv/

.venv/bin/pip install -e '.'
source .venv/bin/activate

python3 -c 'import en_core_web_sm' 2>/dev/null || ({
  python -m spacy download en_core_web_sm
})

[[ -f .env ]] || {
    cp .env.example .env
    echo '======= Created default ".env" file ======='
    echo "= Edit this to configure your environment ="
}
