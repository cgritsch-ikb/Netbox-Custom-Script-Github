
from dcim.models import DeviceType
from extras.scripts import ObjectVar, Script


class SelectDeviceTypeScript(Script):
    class Meta:
        name = "Select Device Type"

    device_type = ObjectVar(
        label="Device Type",
        model=DeviceType,
        query_params={"manufacturer": ["socomec", "eaton"]},
        description="Select a DeviceType from Socomec or Eaton",
    )

    def run(self, data, commit):
        self.log_success(f"Selected DeviceType: {data['device_type']}")
