# Retail Intelligence Monitor

Vier Reiter: Handels-News, Konsumtrends, Technologie & KI, Verhaltenspsychologie. Die ersten drei enthalten je bis zu zehn Meldungen aus den vergangenen sieben Tagen, einen heuristischen Relevanzwert und eine Kurzzusammenfassung. Der Psychologiebeitrag rotiert zwischen redaktionell vorgeprüften, theoriegestützten Texten mit je zehn Sätzen.

## Installation

1. Ein **neues öffentliches** GitHub-Repository namens `retail-intelligence-monitor` anlegen.
2. **Den Inhalt dieses Ordners**, nicht den übergeordneten Ordner, ins Hauptverzeichnis hochladen. Die versteckte Datei `.github/workflows/update.yml` muss mit hochgeladen werden. Bei Upload über die GitHub-Weboberfläche kann die Workflow-Datei alternativ über `Add file > Create new file` unter genau diesem Pfad angelegt werden.
3. `Settings > Pages > Build and deployment > Source: GitHub Actions` auswählen.
4. `Actions > Daily Intelligence Monitor > Run workflow` manuell starten. Nach grünem Häkchen sollte die Website unter `https://DEIN-NAME.github.io/retail-intelligence-monitor/` erscheinen.
5. Auf Android in Chrome öffnen und `Zum Startbildschirm hinzufügen` auswählen.

## Automatisierung

Der Workflow läuft täglich um 06:30 UTC (07:30 MEZ / 08:30 MESZ). GitHub kann geplante Läufe verzögern. Manuelles Aktualisieren über `Actions > Daily Intelligence Monitor > Run workflow`.

## Wichtige Grenzen

- Die erste Version nutzt öffentliche Google-News-RSS-Suchergebnisse und keine direkte Volltext-API aller genannten Medien. **Es wird keine vollständige Abdeckung der 30 Quellen garantiert.** Bezahlartikel bleiben gegebenenfalls hinter Paywalls.
- Mehrfachberichterstattung wird mit Titelähnlichkeit geschätzt. Inhaltlich gleiche Nachrichten mit stark unterschiedlichen Überschriften können getrennt bleiben, verschiedene Meldungen können fälschlich zusammengefasst werden.
- Scores sind eine nachvollziehbare **Heuristik**, keine wissenschaftlich validierte Relevanzmessung. Die Quellenzahl berücksichtigt nur im Feed erkannte unterschiedliche Quellennamen, nicht die Unabhängigkeit von Agenturmeldungen.
- Die Zwei-Satz-Texte bestehen aus dem Titel und einer öffentlich verfügbaren Feed-Beschreibung bzw. einem gekennzeichneten neutralen Ersatzsatz. Sie sind **keine KI-generierte redaktionelle Synthese**. Ebenso fasst die Drei-Satz-Übersicht die Top-Schlagzeilen zusammen, statt analytische Schlussfolgerungen zu erfinden.
- Der Psychologiebeitrag ist eine **kuratierte, rotierende** Sammlung, keine automatisch täglich neu recherchierte Fachpublikation. Quellen dienen der Theorieeinordnung.
- Für echte semantische Dublettenerkennung, überprüfte journalistische Synthesen und tägliche neue Psychologieartikel wäre eine LLM-API mit sicher hinterlegtem GitHub-Secret sowie Quellenvalidierung erforderlich.

## Konfiguration

`collect.py`: `SOURCES` enthält priorisierte Quellen zur Orientierung, `QUERIES` die tatsächlich verwendeten Suchanfragen. Ergänzende Quellen sind durch breitere Suchanfragen möglich. Ranking: Trefferzahl von Kategoriebegriffen, Quellenvielfalt und Aktualität. Alle Artikel müssen in den letzten sieben Tagen veröffentlicht worden sein, sofern der RSS-Feed einen auswertbaren Zeitstempel liefert.
