# EmptySearcher

EmptySearcher e' un'app desktop per trovare cartelle vuote o "effettivamente vuote", cioe' cartelle che contengono solo file o sottocartelle ignorati.

## Installazione

Scarica il pacchetto adatto al tuo sistema dalla pagina `Releases` del repository GitHub:

- Windows: `EmptySearcher-windows.zip`
- macOS: `EmptySearcher-macos.zip`
- Linux: `EmptySearcher-linux.tar.gz`

Dopo il download:

1. estrai l'archivio;
2. avvia l'applicazione.

Avvio per sistema:

- Windows: esegui `EmptySearcher.exe`
- macOS: apri `EmptySearcher.app`
- Linux: esegui il binario `EmptySearcher`

## Utilizzo

1. seleziona la cartella radice da analizzare;
2. imposta, se necessario, file ignorati, cartelle ignorate e percorsi esclusi;
3. avvia la scansione;
4. controlla la barra di avanzamento, il numero di cartelle lette e il totale delle cartelle individuate;
5. se serve, interrompi la scansione con `Arresta scansione`;
6. nei risultati, lascia selezionate le cartelle da eliminare oppure deseleziona quelle da mantenere;
7. usa il menu contestuale per aprire una cartella, aggiungerla agli ignorati, aggiungerla agli esclusi oppure inviarla subito al cestino;
8. premi `Elimina selezionate nel cestino` per inviare al cestino tutte le cartelle selezionate.

## Comportamento

- I file ignorati non vengono conteggiati come contenuto della cartella.
- Le cartelle ignorate non vengono conteggiate come contenuto della cartella padre.
- I percorsi esclusi non vengono analizzati e non compaiono nei risultati.
- Le eliminazioni vengono inviate al cestino di sistema, non cancellate in modo definitivo.
- L'app salva la configurazione e riparte dall'ultima cartella e dagli ultimi pattern usati.
