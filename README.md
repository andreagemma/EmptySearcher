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
pip install pyinstaller
pyinstaller --noconfirm --windowed --name EmptySearcher --paths src src/emptysearcher/app.py
```

Per un vero output cross-platform, la build va eseguita sulla piattaforma di destinazione:

- Windows -> `.exe`
- macOS -> `.app`
- Linux -> binario nativo
