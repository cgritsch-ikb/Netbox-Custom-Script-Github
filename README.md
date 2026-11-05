# NetBox CPE-GIN Cisco-Konfigurationen

Dieses Repository enthält nur den CPE-GIN-Workflow zur Generierung von
Cisco-IOS/IOS-XE-Konfigurationen aus NetBox. Das Playbook liest Geräte mit der
NetBox-Rolle `cpe-gin`, deren Interfaces und zugewiesene IP-Adressen. Es
überträgt keine Konfigurationen auf Geräte und benötigt weder eine Primary-IP
noch eine SSH-Verbindung.

## Voraussetzungen

- Python ≥ 3.9
- Ansible ≥ 2.14
- Ansible-Collection `ansible.utils` sowie das Python-Paket `netaddr`

```bash
ansible-galaxy collection install -r ansible/requirements.yml
python -m pip install netaddr
```

## Ausführen

Der API-Token benötigt Leserechte auf Geräte, Interfaces und IP-Adressen.
TLS-Zertifikatsprüfungen sind eingeschaltet; bei einer internen CA muss deren
Zertifikat auf dem Ansible-Controller vertrauenswürdig installiert sein.

```bash
export NETBOX_API="https://netbox.example.com"
export NETBOX_TOKEN="your-api-token-here"
cd ansible
ansible-playbook -i localhost, playbooks/generate_cpe_gin_config.yml
```

Der Rollenfilter nutzt den NetBox-Slug `cpe-gin`. Bei einem anderen Slug:

```bash
ansible-playbook -i localhost, playbooks/generate_cpe_gin_config.yml \
  -e netbox_device_role=mein-rollen-slug
```

Ausgaben werden unter `ansible/configs/generated/<gerätename>.cfg` gespeichert.
Alle API-Seiten für Geräte, Interfaces und IP-Adressen werden berücksichtigt.
IPv4-Adressen werden mit Netzmaske ausgegeben, weitere IPv4-Adressen desselben
Interfaces als `secondary`; IPv6-Adressen behalten ihre Präfixlänge und
Link-Local-Adressen werden mit `link-local` gerendert. NetBox bleibt die Quelle
für Interface-Namen, Beschreibungen und Aktivierung. Ohne zugewiesene IPs wird
das Interface trotzdem erzeugt.

NTP, DNS, SNMP, Syslog und IOS-Version vor Verwendung in
`ansible/group_vars/all.yml` prüfen und die generierten Konfigurationen
validieren. Das Template richtet sich an geroutete Cisco-IOS/IOS-XE-Interfaces
und ersetzt keine vollständige Switchport-, VRF- oder Service-Konfiguration.

## Tests

Die Integrationstests verwenden eine lokale, paginierte NetBox-Test-API:

```bash
python -m unittest discover -s tests -v
```

Die Tests benötigen Ansible, die Collection `ansible.utils` und `netaddr`.
