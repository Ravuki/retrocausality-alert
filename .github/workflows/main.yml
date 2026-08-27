name: Retrocausality Checker

on:
  schedule:
    - cron: "*/5 * * * *"
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: hypermyst-alert
  cancel-in-progress: false

jobs:
  check:
    runs-on: ubuntu-latest

    steps:
      - name: Pobierz kod
        uses: actions/checkout@v4

      - name: Ustaw Go
        uses: actions/setup-go@v6
        with:
          go-version: "1.26"

      - name: Zainstaluj x-cli
        run: |
          go install github.com/tamnd/x-cli/cmd/x@latest
          echo "$(go env GOPATH)/bin" >> "$GITHUB_PATH"

      - name: Sprawdź x-cli
        run: |
          x version

      - name: Ustaw Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      - name: Instalacja bibliotek
        run: pip install requests

      - name: Start bota
        env:
          DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
        run: python retro_alert.py

      - name: Zapisz pamięć ostatniego tweeta
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          git add last_tweet.txt

          if git diff --cached --quiet; then
            echo "Brak zmian w pamięci."
          else
            git commit -m "Update HyperMyst tweet memory"
            git push
          fi
