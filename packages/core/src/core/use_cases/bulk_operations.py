import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from ..domain.entities.device_status import DeviceStatus
from ..domain.entities.exceptions import BulkOperationError
from ..domain.value_objects.action_result import ActionResult
from ..gateways.device import DeviceGateway

_DEVICE_ID_PLACEHOLDER = "{{device_id}}"


def _config_needs_device_id(config: dict[str, Any]) -> bool:
    """Cheap check for whether a config contains the device_id placeholder,
    so we only pay for an extra device-info lookup when it's actually used."""
    try:
        return _DEVICE_ID_PLACEHOLDER in json.dumps(config)
    except (TypeError, ValueError):
        return False


def _substitute_device_id(value: Any, device_id: str) -> Any:
    """Recursively replace the {{device_id}} placeholder in any string
    values within a (possibly nested) config structure."""
    if isinstance(value, str):
        return value.replace(_DEVICE_ID_PLACEHOLDER, device_id)
    if isinstance(value, dict):
        return {k: _substitute_device_id(v, device_id) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_device_id(v, device_id) for v in value]
    return value


class BulkOperationsUseCase:

    def __init__(
        self,
        device_gateway: DeviceGateway,
    ):
        self._device_gateway = device_gateway

    async def execute_bulk_update(
        self, device_ips: list[str], channel: str = "stable"
    ) -> list[ActionResult]:
        """
        Update firmware on multiple devices.

        Args:
            device_ips: List of device IP addresses
            channel: Update channel (stable/beta)

        Returns:
            List of action results
        """
        try:
            return await self._device_gateway.execute_bulk_action(
                device_ips, "shelly", "Update", {"channel": channel}
            )
        except Exception as e:
            raise BulkOperationError(
                "bulk_update", device_ips, f"Bulk update failed: {str(e)}"
            ) from e

    async def execute_bulk_reboot(self, device_ips: list[str]) -> list[ActionResult]:
        """
        Reboot multiple devices.

        Args:
            device_ips: List of device IP addresses

        Returns:
            List of action results
        """
        try:
            return await self._device_gateway.execute_bulk_action(
                device_ips, "shelly", "Reboot", {}
            )
        except Exception as e:
            raise BulkOperationError(
                "bulk_reboot", device_ips, f"Bulk reboot failed: {str(e)}"
            ) from e

    async def execute_bulk_factory_reset(
        self, device_ips: list[str]
    ) -> list[ActionResult]:
        """
        Factory reset multiple devices.

        Args:
            device_ips: List of device IP addresses

        Returns:
            List of action results
        """
        try:
            return await self._device_gateway.execute_bulk_action(
                device_ips, "shelly", "FactoryReset", {}
            )
        except Exception as e:
            raise BulkOperationError(
                "bulk_factory_reset", device_ips, f"Bulk factory reset failed: {str(e)}"
            ) from e

    async def get_bulk_status(
        self, device_ips: list[str], include_updates: bool = True
    ) -> list[DeviceStatus]:
        """
        Get status of multiple devices.

        Args:
            device_ips: List of device IP addresses
            include_updates: Include update information (parameter kept for compatibility but not used)

        Returns:
            List of device statuses
        """
        results = []

        for ip in device_ips:
            try:
                device = await self._device_gateway.get_device_status(ip)
                if device:
                    results.append(device)
            except Exception as e:
                print(f"Error getting status for {ip}: {str(e)}")

        return results

    async def export_bulk_config(
        self,
        device_ips: list[str],
        component_types: list[str],
    ) -> dict[str, Any]:
        """
        Export component configurations organized per device.

        Args:
            device_ips: List of device IP addresses
            component_types: List of component types to export

        Returns:
            Dictionary containing export metadata and device configurations
        """
        result = {
            "export_metadata": {
                "timestamp": datetime.now(UTC).isoformat() + "Z",
                "total_devices": len(device_ips),
                "component_types": component_types,
            },
            "devices": {},
        }

        for device_ip in device_ips:

            device_status = await self._device_gateway.get_device_status(device_ip)
            if not device_status:
                continue

            device_data: dict[str, Any] = {
                "device_info": {
                    "device_name": device_status.device_name,
                    "device_type": device_status.device_type,
                    "firmware_version": device_status.firmware_version,
                    "mac_address": device_status.mac_address,
                    "app_name": device_status.app_name,
                },
                "components": {},
            }

            for component in device_status.components:
                if component.component_type in component_types:

                    config_result = await self._device_gateway.execute_component_action(
                        device_ip, component.key, "GetConfig", {}
                    )

                    component_export = {
                        "type": component.component_type,
                        "success": config_result.success,
                        "config": config_result.data if config_result.success else None,
                        "error": (
                            config_result.error if not config_result.success else None
                        ),
                    }

                    if component.component_type == "script" and config_result.success:
                        code_data = await self._fetch_script_code(
                            device_ip, component.key
                        )
                        if code_data is not None:
                            component_export["code"] = code_data

                    device_data["components"][component.key] = component_export

            if "schedules" in component_types:
                schedules = await self._fetch_schedules(device_ip)
                device_data["components"].update(schedules)

            result["devices"][device_ip] = device_data

        return result

    async def _fetch_script_code(
        self, device_ip: str, component_key: str
    ) -> dict[str, Any] | None:
        try:
            script_id = int(component_key.split(":")[1])
            code_result = await self._device_gateway.execute_component_action(
                device_ip, component_key, "GetCode", {"id": script_id}
            )
            if code_result.success and code_result.data:
                return code_result.data
        except (ValueError, IndexError, AttributeError):
            pass

        return None

    async def _fetch_schedules(self, device_ip: str) -> dict[str, Any]:
        schedule_export = {}

        list_result = await self._device_gateway.execute_component_action(
            device_ip, "schedule", "List", {}
        )
        schedule_data = list_result.data
        if list_result.success and schedule_data:
            schedule_export["schedules"] = {
                "type": "schedule",
                "success": True,
                "config": schedule_data,
                "error": None,
            }
        elif not list_result.success:
            schedule_export["schedules"] = {
                "type": "schedule",
                "success": False,
                "config": None,
                "error": list_result.error,
            }

        return schedule_export

    async def apply_bulk_config(
        self,
        device_ips: list[str],
        component_type: str,
        config: dict[str, Any],
    ) -> list[ActionResult]:
        """
        Apply component configuration to multiple devices.

        Resolves actual component keys (e.g. cover:0) per device to ensure
        the RPC call includes the required component ID.

        The config may contain the literal placeholder "{{device_id}}" in
        any string value (e.g. for topic_prefix); it is replaced per-device
        with that device's actual id (from Shelly.GetDeviceInfo) before the
        config is sent, so the same request can be applied to many devices
        while still producing a device-specific value on each one.

        Args:
            device_ips: List of device IP addresses
            component_type: Type of component to apply configuration to
            config: Configuration to apply

        Returns:
            List of action results
        """
        tasks = [
            self._apply_config_to_device(device_ip, component_type, config)
            for device_ip in device_ips
        ]
        results_per_device = await asyncio.gather(*tasks)

        all_results: list[ActionResult] = []
        for results in results_per_device:
            all_results.extend(results)
        return all_results

    async def _apply_config_to_device(
        self,
        device_ip: str,
        component_type: str,
        config: dict[str, Any],
    ) -> list[ActionResult]:
        """Apply config to a single device; returns one ActionResult per
        resolved component key (usually one, more for multi-instance
        components like switch)."""
        keys = await self._device_gateway.get_component_keys(device_ip, component_type)

        if not keys:
            return [
                ActionResult(
                    device_ip=device_ip,
                    action_type=f"{component_type}.SetConfig",
                    success=False,
                    message=f"No {component_type} components found on device",
                    error=f"Component type {component_type} not present"
                    " or device unreachable",
                )
            ]

        device_config = config
        if _config_needs_device_id(config):
            discovered = await self._device_gateway.discover_device(device_ip)
            device_id = (
                discovered.device_id
                if discovered and discovered.device_id
                else device_ip
            )
            device_config = _substitute_device_id(config, device_id)

        results = []
        for key in keys:
            result = await self._device_gateway.execute_component_action(
                device_ip, key, "SetConfig", {"config": device_config}
            )
            results.append(result)
        return results

    async def deploy_bulk_script(
        self,
        device_ips: list[str],
        name: str,
        code: str,
        enable: bool = True,
        run: bool = True,
        overwrite: bool = True,
    ) -> list[ActionResult]:
        """
        Deploy a script to multiple devices simultaneously.

        For each device this creates a new script (Gen2/Gen3 only), uploads
        the source code, and optionally enables autostart on boot and starts
        it immediately. Devices are processed in parallel.

        Args:
            device_ips: List of device IP addresses
            name: Script name as shown on the device
            code: Script source code (Shelly's mJS/JS engine)
            enable: If True, enable the script so it autostarts on boot
            run: If True, start the script immediately after upload
            overwrite: If True, an existing script with the same name on a
                device is deleted first, so re-running the deployment does
                not accumulate duplicate scripts

        Returns:
            One ActionResult per device summarizing the deployment outcome
        """
        tasks = [
            self._deploy_script_to_device(ip, name, code, enable, run, overwrite)
            for ip in device_ips
        ]
        return await asyncio.gather(*tasks)

    async def _deploy_script_to_device(
        self,
        device_ip: str,
        name: str,
        code: str,
        enable: bool,
        run: bool,
        overwrite: bool,
    ) -> ActionResult:
        steps: dict[str, bool] = {}

        if overwrite:
            await self._delete_script_by_name(device_ip, name, steps)

        create_result = await self._device_gateway.execute_component_action(
            device_ip, "script", "Create", {"name": name}
        )
        steps["create"] = create_result.success

        script_id = self._extract_result_field(create_result.data, "id")

        if not create_result.success or script_id is None:
            return ActionResult(
                device_ip=device_ip,
                action_type="script.Deploy",
                success=False,
                message=f"Failed to create script '{name}' on device",
                error=create_result.error or "Script.Create did not return an id",
                data={"steps": steps},
            )

        component_key = f"script:{script_id}"

        put_code_result = await self._device_gateway.execute_component_action(
            device_ip, component_key, "PutCode", {"code": code}
        )
        steps["put_code"] = put_code_result.success
        if not put_code_result.success:
            return ActionResult(
                device_ip=device_ip,
                action_type="script.Deploy",
                success=False,
                message=(
                    f"Script '{name}' created (id={script_id}) but "
                    "uploading the code failed"
                ),
                error=put_code_result.error,
                data={"steps": steps, "script_id": script_id},
            )

        if enable:
            enable_result = await self._device_gateway.execute_component_action(
                device_ip, component_key, "SetConfig", {"config": {"enable": True}}
            )
            steps["enable"] = enable_result.success
            if not enable_result.success:
                return ActionResult(
                    device_ip=device_ip,
                    action_type="script.Deploy",
                    success=False,
                    message=(
                        f"Script '{name}' uploaded (id={script_id}) but "
                        "enabling autostart failed"
                    ),
                    error=enable_result.error,
                    data={"steps": steps, "script_id": script_id},
                )

        if run:
            start_result = await self._device_gateway.execute_component_action(
                device_ip, component_key, "Start", {}
            )
            steps["start"] = start_result.success
            if not start_result.success:
                return ActionResult(
                    device_ip=device_ip,
                    action_type="script.Deploy",
                    success=False,
                    message=(
                        f"Script '{name}' uploaded (id={script_id}) but "
                        "starting it failed"
                    ),
                    error=start_result.error,
                    data={"steps": steps, "script_id": script_id},
                )

        return ActionResult(
            device_ip=device_ip,
            action_type="script.Deploy",
            success=True,
            message=f"Script '{name}' deployed successfully (id={script_id})",
            data={"steps": steps, "script_id": script_id},
        )

    async def _delete_script_by_name(
        self, device_ip: str, name: str, steps: dict[str, bool]
    ) -> None:
        """Delete any existing script with the same name on the device, so a
        re-deploy overwrites it instead of creating a duplicate."""
        list_result = await self._device_gateway.execute_component_action(
            device_ip, "script", "List", {}
        )
        if not list_result.success:
            return

        scripts = self._extract_result_field(list_result.data, "scripts") or []
        for script in scripts:
            if isinstance(script, dict) and script.get("name") == name:
                await self._device_gateway.execute_component_action(
                    device_ip, f"script:{script.get('id')}", "Delete", {}
                )
                steps["removed_existing"] = True

    @staticmethod
    def _extract_result_field(data: dict[str, Any] | None, field: str) -> Any:
        """Pull a field out of a raw JSON-RPC response, which may or may not
        be wrapped in a top-level 'result' object depending on the gateway."""
        if not isinstance(data, dict):
            return None
        payload = data.get("result", data)
        if not isinstance(payload, dict):
            return None
        return payload.get(field)
