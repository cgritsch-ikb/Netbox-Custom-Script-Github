
from dcim.models import DeviceType
from extras.scripts import ObjectVar, Script


class SelectDeviceTypeScript(Script):
    class Meta:
        name = "Select Device Type"

    device_type = ObjectVar(
        label="Device Type",
        model=DeviceType,
        query_params={"manufacturer": ["socomec", "eaton"]},
        description="Wähle einen DeviceType von Socomec oder Eaton",
    )

    def run(self, data, commit):
        self.log_success(f"Ausgewählter DeviceType: {data['device_type']}")
