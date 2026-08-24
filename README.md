# Eufy Smart Scale P3 BLE für Home Assistant

Private Home-Assistant-Custom-Integration für die **Eufy Smart Scale P3 (`eufy T9150`)**. Sie liest die Messung direkt aus den Bluetooth-Low-Energy-Advertisements der Waage – lokal, ohne Eufy-Konto, Cloud oder aktive Verbindung zur Waage.

Der Hauptzweck ist die zuverlässige Übernahme des **finalen Gewichts**. Manche ESPHome-Bluetooth-Proxies liefern in einem Advertisement gleichzeitig ein altes Live-Paket und ein neueres abgeschlossenes Paket. Die Integration wertet alle Einträge aus und entscheidet anhand des 8-Bit-Sequenzzählers, welches Paket tatsächlich aktuell ist.

## Unterstützte Werte

| Entität | Verhalten |
|---|---|
| **Gewicht** | Letzte abgeschlossene Messung; wird nach Neustarts wiederhergestellt |
| **Live-Gewicht** | Aktueller Wert während des Wiegens |
| **Impedanz** | Direkt von der Waage gesendeter Rohwert in Ω; wird wiederhergestellt |
| **Herzfrequenz** | Direkt von der Waage gesendeter Wert in bpm; wird wiederhergestellt |
| **Letzte Messung** | Zeitpunkt, an dem die letzte Messung erstmals fixiert wurde |
| **Paketstatus** | Diagnosewert für die aktuelle BLE-Messphase inklusive Status-Hexwert und Sequenznummer |

Bewusst **nicht** enthalten sind berechnete Werte wie Körperfett, Muskelmasse, Wasseranteil oder BMI. Die Waage überträgt dafür Rohdaten; verlässliche Resultate würden zusätzliche Profildaten und eine validierte Berechnungsformel benötigen.

## Voraussetzungen

- Home Assistant **2026.8.0 oder neuer**
- funktionierende Home-Assistant-Bluetooth-Integration
- lokaler Bluetooth-Adapter oder ESPHome Bluetooth Proxy in Reichweite
- Eufy Smart Scale P3 mit Bluetooth-Namen `eufy T9150`

## Installation

### HACS

Da dieses Repository privat ist, funktioniert die Installation über HACS nur, wenn deine HACS-/GitHub-Anbindung Zugriff auf das Repository besitzt.

1. Öffne **HACS → Integrationen**.
2. Öffne das Menü oben rechts und wähle **Benutzerdefinierte Repositories**.
3. Trage `https://github.com/Skriipt/eufy-smart-scale-ble` ein.
4. Wähle als Kategorie **Integration**.
5. Installiere **Eufy Smart Scale P3 BLE** und starte Home Assistant neu.

### Manuell

1. Kopiere den Ordner `custom_components/eufy_p3_ble` nach:

   ```text
   /config/custom_components/eufy_p3_ble
   ```

2. Starte Home Assistant neu.
3. Öffne **Einstellungen → Geräte & Dienste → Integration hinzufügen**.
4. Suche nach **Eufy Smart Scale P3 BLE**.
5. Steige kurz auf die Waage, damit sie ein Bluetooth-Advertisement sendet, und bestätige das gefundene Gerät.

## Wichtiger Hinweis zur offiziellen EufyLife-Integration

Home Assistant kann dieselbe T9150 parallel auch über die offizielle Integration **EufyLife** entdecken. Entferne oder ignoriere deren Eintrag für diese Waage, bevor du diese Custom Integration einrichtest. Andernfalls entstehen doppelte Geräte und Sensoren.

Die Custom Integration verwendet eine eigene Domain (`eufy_p3_ble`) und verändert keine Dateien von Home Assistant Core.

## Funktionstest

Nach der Einrichtung:

1. Öffne das Gerät **Eufy Smart Scale P3** in Home Assistant.
2. Steige auf die Waage und bleibe stehen, bis die Messung fixiert ist.
3. **Live-Gewicht** sollte sich währenddessen ändern.
4. **Gewicht** sollte anschließend exakt auf dem fixierten Wert stehen bleiben.
5. Bei vollständiger Körpermessung können etwas später **Impedanz** und **Herzfrequenz** eintreffen.
6. Starte Home Assistant testweise neu. Die abgeschlossenen Werte müssen erhalten bleiben.

## Fehleranalyse

Für gezieltes Debug-Logging ergänze vorübergehend:

```yaml
logger:
  logs:
    custom_components.eufy_p3_ble: debug
```

Danach Home Assistant neu starten und eine vollständige Messung durchführen. Die Integration schreibt standardmäßig keine Rohpakete in normale Logs und protokolliert identische unerwartete Parserfehler nur einmal pro Fehlersignatur.

Typische Prüfungen:

- Ist mindestens ein Bluetooth-Proxy oder Adapter in Reichweite?
- Wird die Waage unter **Einstellungen → Geräte & Dienste → Bluetooth** gesehen?
- Wurde der offizielle EufyLife-Eintrag für dieselbe Adresse entfernt oder ignoriert?
- Läuft mindestens Home Assistant 2026.8.0?

## Datenschutz

- keine Cloud-Verbindung
- keine Zugangsdaten
- keine Eufy-API
- keine Übertragung von Alter, Größe, Geschlecht oder Profildaten
- ausschließlich lokale Verarbeitung der BLE-Advertisements in Home Assistant

## Entwicklung

Die reine Protokoll- und Sessionlogik ist unabhängig von Home Assistant testbar. Die vollständige Suite läuft unter Python 3.14 und Home Assistant 2026.8 in GitHub Actions:

```bash
python -m pip install -e '.[test]'
ruff format --check .
ruff check .
mypy
pytest --cov=custom_components/eufy_p3_ble --cov-branch
```

## Lizenz

MIT
