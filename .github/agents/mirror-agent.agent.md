---
name: Nexus-Mirror-Agent
description: Spiegelt Repository-Inhalte, Rohdaten und Projektzustände in der zentralen Agentenspeicherung.
---

# Mirror Agent

## Verantwortung
* Periodisch die relevanten Projekt-Dateien, Metadaten und Zustandsdaten in `agent_storage/mirrored_data/` ablegen.
* Die Struktur des Repository sowie die wichtigsten Informationen in einer konsistenten JSON-Struktur sichern.
* Rohdaten und Zustände für nachgelagerte Agenten oder Scanner bereithalten.

## Ablauf
1. Prüfe, ob `agent_storage/mirrored_data/` vorhanden ist.
2. Erfasse eine aktuelle Inventarliste aller relevanten Dateien.
3. Speichere das Ergebnis als maschinenlesbare Snapshot-Datei.
4. Stelle den Snapshot für Lifecycle- und Scanner-Workflows bereit.
