# Netbox-Custom-Script-Github

Ansible-basiertes Projekt zur automatischen Konfigurationsgenerierung für **Cisco**- und **Huawei**-Geräte sowie zum Abgleich von **Soll-Konfiguration (NetBox/Jinja)** und **Ist-Konfiguration (Running-Config)**.  
Die Gerätedaten werden direkt aus **NetBox** bezogen (Rolle **CPE-Business-Pro**, nur aktiv mit Primary-IP).

---

## CPE-GIN: Cisco-Konfigurationen mit allen Interface-IPs

Das zusätzliche Playbook
`ansible/playbooks/generate_cpe_gin_config.yml` fragt die NetBox-API ab und
erzeugt pro Cisco-Gerät der Rolle **CPE-GIN** eine lokale Konfiguration.
Es berücksichtigt alle API-Seiten für Geräte, Interfaces und zugewiesene
IP-Adressen, auch bei einem serverseitigen Seitenlimit.
Eine Primary-IP oder SSH-Verbindung zum Gerät ist nicht erforderlich;
es werden keine Konfigurationen auf Geräte übertragen.

```bash
export NETBOX_API="https://netbox.example.com"
export NETBOX_TOKEN="your-api-token-here"
cd ansible
ansible-playbook -i localhost, playbooks/generate_cpe_gin_config.yml
```

`NETBOX_TOKEN` benötigt nur Leserechte auf Geräte, Interfaces und IP-Adressen.
Die vorhandenen Collections sowie das Python-Paket `netaddr` müssen in der
Python-Umgebung von Ansible installiert sein. Das statische Localhost-Inventory
umgeht die abweichenden Filter des bisherigen dynamischen Inventorys.

Der Rollenfilter verwendet den **Slug**, nicht den Anzeigenamen.
Standard ist `cpe-gin`; bei einem anderen Slug:

```bash
ansible-playbook -i localhost, playbooks/generate_cpe_gin_config.yml -e netbox_device_role=mein-rollen-slug
```

Ausgabe: `ansible/configs/generated/<gerätename>.cfg`.
IPv4-Adressen werden mit Netzmaske ausgegeben, weitere IPv4-Adressen desselben
Interfaces als `secondary`; IPv6-Adressen behalten ihre Präfixlänge.
IPv6-Link-Local-Adressen werden mit dem Cisco-Schlüsselwort `link-local`
ohne Präfixlänge erzeugt.
Die Primary-IP wird nicht zusätzlich auf ein erfundenes Loopback kopiert.
NetBox bleibt die Quelle für Interface-Namen, Beschreibungen und Aktivierung.
Ohne zugewiesene IPs wird nur das Interface erzeugt.

Die TLS-Zertifikatsprüfung ist eingeschaltet. Bei einer internen CA sollte deren
Zertifikat auf dem Ansible-Controller als vertrauenswürdig installiert werden.
NTP, DNS, SNMP und weitere Basiswerte vor Verwendung in
`ansible/group_vars/all.yml` anpassen und die generierten Konfigurationen prüfen.
Das Template richtet sich an geroutete Cisco-IOS/IOS-XE-Interfaces, nicht an
eine vollständige Switchport-, VRF- oder herstellerspezifische Service-Konfiguration.

Die nachfolgenden bisherigen Playbooks und Inventory-Filter bleiben unverändert.

Die Integrationstests verwenden eine lokale, paginierte NetBox-Test-API:

```bash
python -m unittest discover -s tests -v
```

Hierfür müssen Ansible, die Collections und `netaddr` installiert sein.
Der Testbefehl wird im Repository-Hauptverzeichnis ausgeführt.

---

## Voraussetzungen

| Software | Version |
|----------|---------|
| Python   | ≥ 3.9   |
| Ansible  | ≥ 2.14  |

Benötigte Ansible Collections installieren:

```bash
ansible-galaxy collection install -r ansible/requirements.yml
```

---

## Umgebungsvariablen

| Variable          | Beschreibung                          | Beispiel                      |
|-------------------|---------------------------------------|-------------------------------|
| `NETBOX_API`      | Basis-URL der Netbox-Instanz          | `https://netbox.example.com`  |
| `NETBOX_TOKEN`    | Netbox API-Token                      | `abc123...`                   |
| `DEVICE_USER`     | SSH-Benutzer für Geräte (optional)    | `admin`                       |
| `DEVICE_PASSWORD` | SSH-Passwort für Geräte (optional)    | `geheim`                      |

```bash
export NETBOX_API="https://netbox.example.com"
export NETBOX_TOKEN="your-api-token-here"
```

---

## Projektstruktur

```
ansible/
├── ansible.cfg                     # Ansible-Konfiguration
├── requirements.yml                # Collections (netbox.netbox, cisco.ios, ...)
├── inventory/
│   └── netbox.yml                  # Dynamisches Netbox-Inventory (nb_inventory)
├── group_vars/
│   ├── all.yml                     # Globale Variablen (NTP, DNS, SNMP, ...)
│   ├── manufacturer_cisco.yml      # Cisco-spezifische Verbindungsparameter
│   └── manufacturer_huawei.yml     # Huawei-spezifische Verbindungsparameter
├── playbooks/
│   ├── generate_config.yml         # Generiert Soll-Konfigs aus NetBox + Jinja
│   ├── collect_running_config.yml  # Holt Running-Config von Cisco IOS/IOS-XE
│   ├── export_config_json.yml      # Konvertiert Soll/Ist-Konfigs nach JSON
│   ├── compare_config_json.yml     # Vergleicht Soll/Ist JSON je Gerät
│   └── pipeline_config_audit.yml   # Führt den kompletten Ablauf aus
├── tasks/
│   ├── generate_single_device.yml        # Task-Include mit Interface-Anreicherung
│   ├── export_single_device_json.yml     # JSON-Export je Gerät
│   └── compare_single_device_configs.yml # JSON-Vergleich je Gerät
├── templates/
│   ├── cisco/
│   │   └── base_config.j2          # Jinja2-Template für Cisco IOS/IOS-XE
│   └── huawei/
│       └── base_config.j2          # Jinja2-Template für Huawei VRP
└── configs/                        # Ausgabeverzeichnis (wird automatisch erstellt)
```

---

## Verwendung

Alle Playbooks arbeiten auf Geräten mit NetBox-Rolle **CPE-Business-Pro**, Status **active** und gesetzter **Primary-IP**.

### Konfigurationen für alle Geräte generieren

```bash
cd ansible
ansible-playbook playbooks/generate_config.yml
```

### Nur Cisco-Geräte

```bash
ansible-playbook playbooks/generate_config.yml --limit manufacturer_cisco
```

### Nur Huawei-Geräte

```bash
ansible-playbook playbooks/generate_config.yml --limit manufacturer_huawei
```

### Einzelnes Gerät

```bash
ansible-playbook playbooks/generate_config.yml --limit router-01
```

Die generierten Soll-Konfigurationsdateien werden unter `ansible/configs/generated/<gerätename>.cfg` gespeichert.

---

## End-to-End Workflow (Soll/Ist Vergleich)

```bash
cd ansible

# 1) Soll-Konfig aus NetBox/Jinja erzeugen
ansible-playbook playbooks/generate_config.yml

# 2) Running-Config von Cisco IOS/IOS-XE holen
ansible-playbook playbooks/collect_running_config.yml

# 3) Beide Konfigurationsquellen in JSON exportieren
ansible-playbook playbooks/export_config_json.yml

# 4) Soll/Ist vergleichen und JSON-Reports erzeugen
ansible-playbook playbooks/compare_config_json.yml
```

Alternativ als Pipeline in einem Lauf:

```bash
cd ansible
ansible-playbook playbooks/pipeline_config_audit.yml
```

Ausgabe:

- `ansible/configs/generated/*.cfg` – Soll-Konfigurationen aus NetBox/Jinja  
- `ansible/configs/running/*.running.cfg` – Running-Configs der Cisco-Geräte  
- `ansible/configs/json/*.generated.json` und `*.running.json` – normalisierte JSON-Dateien  
- `ansible/configs/compare/*.comparison.json` – Vergleich pro Gerät  
- `ansible/configs/compare/summary.json` – Gesamtzusammenfassung

---

## Dynamisches Inventory prüfen

```bash
cd ansible
ansible-inventory --list
ansible-inventory --graph
```

---

## Templates anpassen

Die Jinja2-Templates liegen in `ansible/templates/`.  
Verfügbare Variablen in den Templates:

| Variable           | Beschreibung                                      |
|--------------------|---------------------------------------------------|
| `inventory_hostname` | Gerätename aus Netbox                           |
| `platform`         | Plattform/OS (z. B. IOS, VRP)                     |
| `site`             | Standort des Geräts                               |
| `device_role`      | Geräterolle (z. B. Router, Switch)                |
| `primary_ip4`      | Primäre IPv4-Adresse                              |
| `interfaces`       | Liste der Interfaces mit IPs (enriched mode)      |
| `management_vlan_id` | Management-VLAN aus dem ersten passenden NetBox-Interface wie `Vlanif12` (Huawei, enriched mode; leer ohne passendes `Vlanif*`) |
| `management_ip4`   | Management-IP aus dem ersten passenden NetBox-`Vlanif*`-Interface (Huawei, enriched mode) |
| `ntp_servers`      | NTP-Server (aus `group_vars/all.yml`)             |
| `dns_servers`      | DNS-Server (aus `group_vars/all.yml`)             |
| `snmp_*`           | SNMP-Einstellungen (aus `group_vars/all.yml`)     |
| `syslog_server`    | Syslog-Ziel (aus `group_vars/all.yml`)            |

---

## Interface-Anreicherung (optional)

Standardmäßig werden Interfaces als leere Liste übergeben.  
Um Interface-Details (inklusive IP-Adressen) in die Konfiguration aufzunehmen,  
den zweiten Play in `playbooks/generate_config.yml` auskommentieren (den mit `include_tasks: tasks/generate_single_device.yml`).  
Dies erzeugt zwei zusätzliche API-Aufrufe pro Gerät. Bei Huawei werden dabei auch
Management-VLAN und Management-IP aus einem NetBox-Interface wie `Vlanif12`
abgeleitet. Wenn kein passendes `Vlanif*` vorhanden ist, bleibt die
Management-VLAN leer.
