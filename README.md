# Netbox-Custom-Script-Github

Ansible-basiertes Projekt zur automatischen Konfigurationsgenerierung für **Cisco**- und **Huawei**-Geräte.  
Die Gerätedaten (Namen, IPs, Interfaces) werden direkt aus **Netbox** bezogen.

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
│   └── generate_config.yml         # Hauptplaybook zur Konfigurationsgenerierung
├── tasks/
│   └── generate_single_device.yml  # Task-Include mit Interface-Anreicherung
├── templates/
│   ├── cisco/
│   │   └── base_config.j2          # Jinja2-Template für Cisco IOS/IOS-XE
│   └── huawei/
│       └── base_config.j2          # Jinja2-Template für Huawei VRP
└── configs/                        # Ausgabeverzeichnis (wird automatisch erstellt)
```

---

## Verwendung

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

Die generierten Konfigurationsdateien werden unter `ansible/configs/<gerätename>.cfg` gespeichert.

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
