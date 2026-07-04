#!/usr/bin/env bash
set -euo pipefail

mkdir -p reference_repos

clone_reference() {
  local url="$1"
  local name="$2"
  local target="reference_repos/${name}"

  if [ -d "${target}/.git" ]; then
    echo "${name} já existe em ${target}; pulando."
    return
  fi

  git clone --depth 1 "${url}" "${target}"
}

echo "Clonando repositórios apenas para estudo arquitetural e funcional."
clone_reference "https://github.com/suitecrm/SuiteCRM" "SuiteCRM"
clone_reference "https://github.com/espocrm/espocrm" "espocrm"
clone_reference "https://github.com/twentyhq/twenty" "twenty"
clone_reference "https://github.com/odoo/odoo" "odoo"
clone_reference "https://github.com/monicahq/monica" "monica"
echo "Referências disponíveis em reference_repos/."
