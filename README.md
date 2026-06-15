# EmptySearcher

Desktop app Python cross-platform per individuare cartelle vuote o "effettivamente vuote" in base a regole di ignore.

## Funzionalita'

- Scansione ricorsiva di una cartella radice
- Pattern file ignorati: i file corrispondenti non contano come contenuto
- Pattern cartelle ignorate: le cartelle corrispondenti non contano come contenuto
- Pattern esclusi: la ricerca non entra in questi percorsi e non li propone per l'eliminazione
- Salvataggio e ricarica della configurazione con ripristino automatico all'avvio
- Memoria dell'ultima cartella selezionata anche per il dialog di scelta cartella
- Risultati in struttura ad albero con checkbox, tutte selezionate di default
- Menu contestuale per aggiungere pattern di ignore/exclude o inviare subito al cestino
- Eliminazione sicura nel cestino di sistema tramite `Send2Trash`
- Configurazione persistente per root e pattern

## Avvio sviluppo

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
emptysearcher
```

## Build eseguibile

Esempio con PyInstaller:

```bash
pip install ".[build]"
pyinstaller --noconfirm --windowed --name EmptySearcher --paths src src/emptysearcher/app.py
```

Per un vero output cross-platform, la build va eseguita sulla piattaforma di destinazione:

- Windows -> `.exe`
- macOS -> `.app`
- Linux -> binario nativo

## Build automatica su GitHub

Il repository include la workflow [build-release.yml](.github/workflows/build-release.yml) che:

- compila l'app su `Windows`, `macOS` e `Linux`;
- allega i pacchetti come artifact del workflow a ogni `push`, `pull request` o avvio manuale;
- pubblica automaticamente gli asset della release quando viene creato un tag `v*`, per esempio `v0.1.0`.

Asset pubblicati:

- `EmptySearcher-windows.zip`
- `EmptySearcher-macos.zip`
- `EmptySearcher-linux.tar.gz`

Esempio di pubblicazione release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Una volta esiste una release GitHub, i binari possono essere scaricati direttamente da remoto dalla pagina release o tramite URL stabili del tipo:

- `https://github.com/<owner>/<repo>/releases/latest/download/EmptySearcher-windows.zip`
- `https://github.com/<owner>/<repo>/releases/latest/download/EmptySearcher-macos.zip`
- `https://github.com/<owner>/<repo>/releases/latest/download/EmptySearcher-linux.tar.gz`
