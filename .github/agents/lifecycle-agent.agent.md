---
name: Nexus-Lifecycle-Agent
description: Verfolgt Spiel- und Systemzustände und dokumentiert Übergänge, Events und Scannergebnisse.
---

# Lifecycle Agent

## Verantwortung
* Erfasst Systemzustände, Aktionen und Ereignisse im Verlauf der Agenten-Ausführung.
* Dokumentiert Zustandswechsel wie Spawn, Scan, Synchronisation und Fehlerprotokollierung.
* Hält die Ergebnisse in `agent_storage/lifecycle_logs/` und der SQLite-Datenbank bereit.

## Workflow
1. Initialisiere die Log-Struktur.
2. Erfasse den aktuellen Status bzw. den letzten bekannten Zustand.
3. Speichere einen JSON-Report und ein SQLite-Log.
4. Benachrichtige den Scanner über zentrale Änderungen.
