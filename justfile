help:
    just --list

open-webui:
    xdg-open http://localhost:3000
    cd openwebui && docker compose up
