from unittest.mock import AsyncMock

import pytest
from core.domain.entities.components import (
    Component,
    InputComponent,
    SwitchComponent,
    SystemComponent,
)
from core.domain.entities.device_status import DeviceStatus
from core.domain.entities.discovered_device import DiscoveredDevice
from core.domain.entities.exceptions import BulkOperationError
from core.domain.enums.enums import Status
from core.domain.value_objects.action_result import ActionResult
from core.use_cases.bulk_operations import BulkOperationsUseCase


class TestBulkOperationsUseCase:

    @pytest.fixture
    def use_case(self, mock_device_gateway):
        return BulkOperationsUseCase(device_gateway=mock_device_gateway)

    async def test_it_updates_multiple_devices_successfully(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100", "192.168.1.101"]
        expected_results = [
            ActionResult(
                success=True,
                action_type="update",
                device_ip="192.168.1.100",
                message="Update successful",
            ),
            ActionResult(
                success=True,
                action_type="update",
                device_ip="192.168.1.101",
                message="Update successful",
            ),
        ]
        mock_device_gateway.execute_bulk_action = AsyncMock(
            return_value=expected_results
        )

        results = await use_case.execute_bulk_update(device_ips, "stable")

        assert len(results) == 2
        assert all(result.success for result in results)
        mock_device_gateway.execute_bulk_action.assert_called_once_with(
            device_ips, "shelly", "Update", {"channel": "stable"}
        )

    async def test_it_updates_with_beta_channel(self, use_case, mock_device_gateway):
        device_ips = ["192.168.1.100"]
        expected_results = [
            ActionResult(
                success=True,
                action_type="update",
                device_ip="192.168.1.100",
                message="Beta update successful",
            )
        ]
        mock_device_gateway.execute_bulk_action = AsyncMock(
            return_value=expected_results
        )

        results = await use_case.execute_bulk_update(device_ips, "beta")

        assert len(results) == 1
        assert results[0].success is True
        mock_device_gateway.execute_bulk_action.assert_called_once_with(
            device_ips, "shelly", "Update", {"channel": "beta"}
        )

    async def test_it_raises_bulk_operation_error_on_update_failure(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100"]
        mock_device_gateway.execute_bulk_action = AsyncMock(
            side_effect=Exception("Gateway error")
        )

        with pytest.raises(BulkOperationError, match="Bulk update failed"):
            await use_case.execute_bulk_update(device_ips)

    async def test_it_reboots_multiple_devices_successfully(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100", "192.168.1.101"]
        expected_results = [
            ActionResult(
                success=True,
                action_type="reboot",
                device_ip="192.168.1.100",
                message="Reboot successful",
            ),
            ActionResult(
                success=True,
                action_type="reboot",
                device_ip="192.168.1.101",
                message="Reboot successful",
            ),
        ]
        mock_device_gateway.execute_bulk_action = AsyncMock(
            return_value=expected_results
        )

        results = await use_case.execute_bulk_reboot(device_ips)

        assert len(results) == 2
        assert all(result.success for result in results)
        mock_device_gateway.execute_bulk_action.assert_called_once_with(
            device_ips, "shelly", "Reboot", {}
        )

    async def test_it_raises_bulk_operation_error_on_reboot_failure(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100"]
        mock_device_gateway.execute_bulk_action = AsyncMock(
            side_effect=Exception("Gateway error")
        )

        with pytest.raises(BulkOperationError, match="Bulk reboot failed"):
            await use_case.execute_bulk_reboot(device_ips)

    async def test_it_factory_resets_multiple_devices(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100", "192.168.1.101"]
        expected_results = [
            ActionResult(
                success=True,
                action_type="shelly.FactoryReset",
                device_ip="192.168.1.100",
                message="Factory reset completed",
            ),
            ActionResult(
                success=True,
                action_type="shelly.FactoryReset",
                device_ip="192.168.1.101",
                message="Factory reset completed",
            ),
        ]
        mock_device_gateway.execute_bulk_action = AsyncMock(
            return_value=expected_results
        )

        results = await use_case.execute_bulk_factory_reset(device_ips)

        assert len(results) == 2
        assert all(result.success for result in results)
        mock_device_gateway.execute_bulk_action.assert_called_once_with(
            device_ips, "shelly", "FactoryReset", {}
        )

    async def test_it_handles_mixed_results_in_bulk_operations(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100", "192.168.1.101", "192.168.1.102"]
        expected_results = [
            ActionResult(
                success=True,
                action_type="reboot",
                device_ip="192.168.1.100",
                message="Reboot successful",
            ),
            ActionResult(
                success=False,
                action_type="reboot",
                device_ip="192.168.1.101",
                message="Reboot failed",
                error="Device offline",
            ),
            ActionResult(
                success=True,
                action_type="reboot",
                device_ip="192.168.1.102",
                message="Reboot successful",
            ),
        ]
        mock_device_gateway.execute_bulk_action = AsyncMock(
            return_value=expected_results
        )

        results = await use_case.execute_bulk_reboot(device_ips)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
        assert results[1].error == "Device offline"

    async def test_it_handles_empty_device_list_for_bulk_operations(
        self, use_case, mock_device_gateway
    ):
        empty_ips = []
        mock_device_gateway.execute_bulk_action = AsyncMock(return_value=[])

        update_result = await use_case.execute_bulk_update(empty_ips)
        reboot_result = await use_case.execute_bulk_reboot(empty_ips)

        assert update_result == []
        assert reboot_result == []

    @pytest.fixture
    def mock_device_status_with_components(self):
        return DeviceStatus(
            device_ip="192.168.1.100",
            device_name="Test Device",
            device_type="shelly1pm",
            firmware_version="20230913-112003",
            mac_address="AA:BB:CC:DD:EE:FF",
            app_name="switch",
            components=[
                SwitchComponent(
                    key="switch:0",
                    component_type="switch",
                    status={"output": True},
                    config={"in_mode": "flip", "initial_state": "restore_last"},
                    attrs={},
                ),
                InputComponent(
                    key="input:0",
                    component_type="input",
                    status={"state": False},
                    config={"type": "switch", "invert": False},
                    attrs={},
                ),
                SystemComponent(
                    key="sys",
                    component_type="sys",
                    status={},
                    config={"device": {"name": "Test Device"}},
                    attrs={},
                ),
            ],
        )

    async def test_it_exports_bulk_config_successfully(
        self, use_case, mock_device_gateway, mock_device_status_with_components
    ):
        device_ips = ["192.168.1.100", "192.168.1.101"]
        component_types = ["switch", "input"]

        mock_device_gateway.get_device_status = AsyncMock(
            return_value=mock_device_status_with_components
        )

        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=True,
                action_type="switch.GetConfig",
                device_ip="192.168.1.100",
                message="Config retrieved",
                data={"in_mode": "flip", "initial_state": "restore_last"},
            )
        )

        result = await use_case.export_bulk_config(device_ips, component_types)

        assert "export_metadata" in result
        assert "devices" in result
        assert result["export_metadata"]["total_devices"] == 2
        assert result["export_metadata"]["component_types"] == component_types

        device_data = result["devices"]["192.168.1.100"]
        assert "device_info" in device_data
        assert "components" in device_data
        assert device_data["device_info"]["device_name"] == "Test Device"

        assert "switch:0" in device_data["components"]
        assert device_data["components"]["switch:0"]["type"] == "switch"
        assert device_data["components"]["switch:0"]["success"] is True

    async def test_it_exports_bulk_config_with_unreachable_device(
        self, use_case, mock_device_gateway, mock_device_status_with_components
    ):
        device_ips = ["192.168.1.100", "192.168.1.101"]
        component_types = ["switch"]

        mock_device_gateway.get_device_status = AsyncMock(
            side_effect=[mock_device_status_with_components, None]
        )

        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=True,
                action_type="switch.GetConfig",
                device_ip="192.168.1.100",
                message="Config retrieved",
                data={"in_mode": "flip"},
            )
        )

        result = await use_case.export_bulk_config(device_ips, component_types)

        assert len(result["devices"]) == 1
        assert "192.168.1.100" in result["devices"]
        assert "192.168.1.101" not in result["devices"]

    async def test_it_exports_bulk_config_with_component_failures(
        self, use_case, mock_device_gateway, mock_device_status_with_components
    ):
        device_ips = ["192.168.1.100"]
        component_types = ["switch", "input"]

        mock_device_gateway.get_device_status = AsyncMock(
            return_value=mock_device_status_with_components
        )

        mock_device_gateway.execute_component_action = AsyncMock(
            side_effect=[
                ActionResult(
                    success=True,
                    action_type="switch.GetConfig",
                    device_ip="192.168.1.100",
                    message="Config retrieved",
                    data={"in_mode": "flip"},
                ),
                ActionResult(
                    success=False,
                    action_type="input.GetConfig",
                    device_ip="192.168.1.100",
                    message="Config retrieval failed",
                    error="Component not accessible",
                ),
            ]
        )

        result = await use_case.export_bulk_config(device_ips, component_types)

        device_data = result["devices"]["192.168.1.100"]

        switch_data = device_data["components"]["switch:0"]
        input_data = device_data["components"]["input:0"]

        assert switch_data["success"] is True
        assert switch_data["config"] == {"in_mode": "flip"}
        assert input_data["success"] is False
        assert input_data["error"] == "Component not accessible"

    async def test_it_exports_bulk_config_filters_component_types(
        self, use_case, mock_device_gateway, mock_device_status_with_components
    ):
        device_ips = ["192.168.1.100"]
        component_types = ["switch"]

        mock_device_gateway.get_device_status = AsyncMock(
            return_value=mock_device_status_with_components
        )

        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=True,
                action_type="switch.GetConfig",
                device_ip="192.168.1.100",
                message="Config retrieved",
                data={"in_mode": "flip"},
            )
        )

        result = await use_case.export_bulk_config(device_ips, component_types)

        device_data = result["devices"]["192.168.1.100"]
        components = device_data["components"]

        assert "switch:0" in components
        assert "input:0" not in components
        assert "sys" not in components
        assert len(components) == 1

    async def test_it_exports_multiple_script_components(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100"]
        component_types = ["script"]

        device_status = DeviceStatus(
            device_ip="192.168.1.100",
            device_name="Test Device",
            device_type="shellypro1pm",
            firmware_version="1.0.0",
            mac_address="AA:BB:CC:DD:EE:FF",
            app_name="test",
            components=[
                Component(
                    key="script:0",
                    component_type="script",
                    status={},
                    config={"name": "script_one"},
                    attrs={},
                ),
                Component(
                    key="script:1",
                    component_type="script",
                    status={},
                    config={"name": "script_two"},
                    attrs={},
                ),
            ],
        )

        mock_device_gateway.get_device_status = AsyncMock(return_value=device_status)
        mock_device_gateway.execute_component_action = AsyncMock(
            side_effect=[
                ActionResult(
                    success=True,
                    action_type="script.GetConfig",
                    device_ip="192.168.1.100",
                    message="Config retrieved",
                    data={"name": "script_one"},
                ),
                ActionResult(
                    success=True,
                    action_type="script.GetCode",
                    device_ip="192.168.1.100",
                    message="Code retrieved",
                    data={"data": "console.log('Script 1');", "left": 0},
                ),
                ActionResult(
                    success=True,
                    action_type="script.GetConfig",
                    device_ip="192.168.1.100",
                    message="Config retrieved",
                    data={"name": "script_two"},
                ),
                ActionResult(
                    success=True,
                    action_type="script.GetCode",
                    device_ip="192.168.1.100",
                    message="Code retrieved",
                    data={"data": "console.log('Script 2');", "left": 0},
                ),
            ]
        )

        result = await use_case.export_bulk_config(device_ips, component_types)

        device_data = result["devices"]["192.168.1.100"]
        assert len(device_data["components"]) == 2

        script_0 = device_data["components"]["script:0"]
        assert script_0["code"] == {"data": "console.log('Script 1');", "left": 0}

        script_1 = device_data["components"]["script:1"]
        assert script_1["code"] == {"data": "console.log('Script 2');", "left": 0}

    async def test_it_exports_schedules_successfully(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100"]
        component_types = ["schedules"]

        device_status = DeviceStatus(
            device_ip="192.168.1.100",
            device_name="Test Device",
            device_type="shellypro1pm",
            firmware_version="1.0.0",
            mac_address="AA:BB:CC:DD:EE:FF",
            app_name="test",
            components=[],  # Schedules don't appear here
        )

        mock_device_gateway.get_device_status = AsyncMock(return_value=device_status)
        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=True,
                action_type="schedule.List",
                device_ip="192.168.1.100",
                message="Schedules retrieved",
                data={
                    "jobs": [
                        {
                            "id": 1,
                            "enable": True,
                            "timespec": "0 0 8 * * SUN,MON,TUE,WED,THU,FRI,SAT",
                            "calls": [
                                {
                                    "method": "Switch.Set",
                                    "params": {"id": 0, "on": False},
                                }
                            ],
                        },
                        {
                            "id": 2,
                            "enable": True,
                            "timespec": "0 30 19 * * MON,TUE,WED,THU,FRI",
                            "calls": [
                                {
                                    "method": "Switch.Set",
                                    "params": {"id": 0, "on": True},
                                }
                            ],
                        },
                    ],
                    "rev": 4,
                },
            )
        )

        result = await use_case.export_bulk_config(device_ips, component_types)

        # Verify schedule is exported
        device_data = result["devices"]["192.168.1.100"]
        assert "schedules" in device_data["components"]

        schedule = device_data["components"]["schedules"]
        assert schedule["type"] == "schedule"
        assert schedule["success"] is True
        assert schedule["config"]["jobs"] is not None
        assert len(schedule["config"]["jobs"]) == 2
        assert schedule["config"]["rev"] == 4

    async def test_it_exports_schedules_when_list_fails(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100"]
        component_types = ["schedules"]

        device_status = DeviceStatus(
            device_ip="192.168.1.100",
            device_name="Test Device",
            device_type="shellypro1pm",
            firmware_version="1.0.0",
            mac_address="AA:BB:CC:DD:EE:FF",
            app_name="test",
            components=[],
        )

        mock_device_gateway.get_device_status = AsyncMock(return_value=device_status)
        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=False,
                action_type="schedule.List",
                device_ip="192.168.1.100",
                message="Failed",
                error="Schedule component not available",
            )
        )

        result = await use_case.export_bulk_config(device_ips, component_types)

        # Verify schedule export shows failure
        device_data = result["devices"]["192.168.1.100"]
        assert "schedules" in device_data["components"]

        schedule = device_data["components"]["schedules"]
        assert schedule["type"] == "schedule"
        assert schedule["success"] is False
        assert schedule["config"] is None
        assert schedule["error"] == "Schedule component not available"

    async def test_it_exports_schedules_when_none_exist(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100"]
        component_types = ["schedules"]

        device_status = DeviceStatus(
            device_ip="192.168.1.100",
            device_name="Test Device",
            device_type="shellypro1pm",
            firmware_version="1.0.0",
            mac_address="AA:BB:CC:DD:EE:FF",
            app_name="test",
            components=[],
        )

        mock_device_gateway.get_device_status = AsyncMock(return_value=device_status)
        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=True,
                action_type="schedule.List",
                device_ip="192.168.1.100",
                message="Schedules retrieved",
                data={"jobs": [], "rev": 0},
            )
        )

        result = await use_case.export_bulk_config(device_ips, component_types)

        # Verify empty schedule list is exported
        device_data = result["devices"]["192.168.1.100"]
        schedule = device_data["components"]["schedules"]
        assert schedule["success"] is True
        assert schedule["config"]["jobs"] == []
        assert schedule["config"]["rev"] == 0

    async def test_it_exports_mixed_components_with_schedules(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100"]
        component_types = ["switch", "schedules"]

        device_status = DeviceStatus(
            device_ip="192.168.1.100",
            device_name="Test Device",
            device_type="shellypro1pm",
            firmware_version="1.0.0",
            mac_address="AA:BB:CC:DD:EE:FF",
            app_name="test",
            components=[
                Component(
                    key="switch:0",
                    component_type="switch",
                    status={},
                    config={"name": "Main Switch"},
                    attrs={},
                ),
            ],
        )

        mock_device_gateway.get_device_status = AsyncMock(return_value=device_status)
        mock_device_gateway.execute_component_action = AsyncMock(
            side_effect=[
                # Switch GetConfig
                ActionResult(
                    success=True,
                    action_type="switch.GetConfig",
                    device_ip="192.168.1.100",
                    message="Config retrieved",
                    data={"name": "Main Switch"},
                ),
                # Schedule.List
                ActionResult(
                    success=True,
                    action_type="schedule.List",
                    device_ip="192.168.1.100",
                    message="Schedules retrieved",
                    data={
                        "jobs": [
                            {
                                "id": 1,
                                "enable": True,
                                "timespec": "0 9 8 * * *",
                                "calls": [],
                            }
                        ],
                        "rev": 1,
                    },
                ),
            ]
        )

        result = await use_case.export_bulk_config(device_ips, component_types)

        # Verify both switch and schedule are exported
        device_data = result["devices"]["192.168.1.100"]
        assert "switch:0" in device_data["components"]
        assert "schedules" in device_data["components"]

        # Verify schedule has jobs
        assert device_data["components"]["schedules"]["config"]["jobs"] is not None
        assert len(device_data["components"]["schedules"]["config"]["jobs"]) == 1

    async def test_it_applies_bulk_config_successfully(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100", "192.168.1.101"]
        component_type = "switch"
        config = {"in_mode": "button", "initial_state": "off"}

        mock_device_gateway.get_component_keys = AsyncMock(return_value=["switch:0"])

        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=True,
                action_type="switch.SetConfig",
                device_ip="192.168.1.100",
                message="Config applied successfully",
            )
        )

        results = await use_case.apply_bulk_config(device_ips, component_type, config)

        assert len(results) == 2
        assert all(result.success for result in results)

        assert mock_device_gateway.execute_component_action.call_count == 2
        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.100",
            "switch:0",
            "SetConfig",
            {"config": config},
        )
        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.101",
            "switch:0",
            "SetConfig",
            {"config": config},
        )

    async def test_it_applies_bulk_config_with_unreachable_device(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100", "192.168.1.101"]
        component_type = "switch"
        config = {"in_mode": "button"}

        # First device has components, second returns empty (unreachable)
        mock_device_gateway.get_component_keys = AsyncMock(
            side_effect=[["switch:0"], []]
        )

        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=True,
                action_type="switch.SetConfig",
                device_ip="192.168.1.100",
                message="Config applied",
            )
        )

        results = await use_case.apply_bulk_config(device_ips, component_type, config)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].device_ip == "192.168.1.101"
        assert results[1].success is False

    async def test_it_applies_bulk_config_with_component_failures(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100"]
        component_type = "switch"
        config = {"in_mode": "button"}

        mock_device_gateway.get_component_keys = AsyncMock(return_value=["switch:0"])

        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=False,
                action_type="switch.SetConfig",
                device_ip="192.168.1.100",
                message="Config apply failed",
                error="Invalid configuration",
            )
        )

        results = await use_case.apply_bulk_config(device_ips, component_type, config)

        # Should have 1 result (all results are included, even failed ones)
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error == "Invalid configuration"

    async def test_it_applies_bulk_config_filters_by_component_type(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100"]
        component_type = "cover"
        config = {"motor": {"idle_power_thr": 2.0}}

        # No cover components found
        mock_device_gateway.get_component_keys = AsyncMock(return_value=[])

        results = await use_case.apply_bulk_config(device_ips, component_type, config)

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].action_type == "cover.SetConfig"
        assert "No cover components found" in results[0].message

        mock_device_gateway.execute_component_action.assert_not_called()

    async def test_it_applies_bulk_config_multiple_components_same_type(
        self, use_case, mock_device_gateway
    ):
        device_ips = ["192.168.1.100"]
        component_type = "switch"
        config = {"in_mode": "button"}

        mock_device_gateway.get_component_keys = AsyncMock(
            return_value=["switch:0", "switch:1"]
        )
        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=True,
                action_type="switch.SetConfig",
                device_ip="192.168.1.100",
                message="Config applied",
            )
        )

        results = await use_case.apply_bulk_config(device_ips, component_type, config)

        assert len(results) == 2
        assert all(result.success for result in results)

        assert mock_device_gateway.execute_component_action.call_count == 2
        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.100",
            "switch:0",
            "SetConfig",
            {"config": config},
        )
        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.100",
            "switch:1",
            "SetConfig",
            {"config": config},
        )


class TestDeployBulkScript:

    @pytest.fixture
    def use_case(self, mock_device_gateway):
        return BulkOperationsUseCase(device_gateway=mock_device_gateway)

    @staticmethod
    def _ok(action_type, data=None):
        return ActionResult(
            success=True,
            action_type=action_type,
            device_ip="192.168.1.100",
            message="ok",
            data=data,
        )

    @staticmethod
    def _fail(action_type, error="boom"):
        return ActionResult(
            success=False,
            action_type=action_type,
            device_ip="192.168.1.100",
            message="failed",
            error=error,
        )

    async def test_it_deploys_a_script_and_enables_and_starts_it(
        self, use_case, mock_device_gateway
    ):
        async def side_effect(ip, component_key, action, parameters=None):
            if component_key == "script" and action == "List":
                return self._ok("script.List", {"result": {"scripts": []}})
            if component_key == "script" and action == "Create":
                return self._ok("script.Create", {"result": {"id": 3}})
            if component_key == "script:3" and action == "PutCode":
                return self._ok("script:3.PutCode")
            if component_key == "script:3" and action == "SetConfig":
                return self._ok("script:3.SetConfig")
            if component_key == "script:3" and action == "Start":
                return self._ok("script:3.Start")
            raise AssertionError(f"Unexpected call: {component_key}.{action}")

        mock_device_gateway.execute_component_action = AsyncMock(
            side_effect=side_effect
        )

        results = await use_case.deploy_bulk_script(
            ["192.168.1.100"], "my-script", "console.log('hi');"
        )

        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.data["script_id"] == 3
        assert result.data["steps"] == {
            "create": True,
            "put_code": True,
            "enable": True,
            "start": True,
        }

        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.100", "script", "Create", {"name": "my-script"}
        )
        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.100",
            "script:3",
            "PutCode",
            {"code": "console.log('hi');"},
        )
        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.100", "script:3", "SetConfig", {"config": {"enable": True}}
        )
        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.100", "script:3", "Start", {}
        )

    async def test_it_skips_enable_and_start_when_disabled(
        self, use_case, mock_device_gateway
    ):
        async def side_effect(ip, component_key, action, parameters=None):
            if component_key == "script" and action == "List":
                return self._ok("script.List", {"result": {"scripts": []}})
            if component_key == "script" and action == "Create":
                return self._ok("script.Create", {"result": {"id": 1}})
            if component_key == "script:1" and action == "PutCode":
                return self._ok("script:1.PutCode")
            raise AssertionError(f"Unexpected call: {component_key}.{action}")

        mock_device_gateway.execute_component_action = AsyncMock(
            side_effect=side_effect
        )

        results = await use_case.deploy_bulk_script(
            ["192.168.1.100"],
            "my-script",
            "code",
            enable=False,
            run=False,
        )

        assert results[0].success is True
        assert "enable" not in results[0].data["steps"]
        assert "start" not in results[0].data["steps"]

    async def test_it_reports_failure_when_code_upload_fails(
        self, use_case, mock_device_gateway
    ):
        async def side_effect(ip, component_key, action, parameters=None):
            if component_key == "script" and action == "List":
                return self._ok("script.List", {"result": {"scripts": []}})
            if component_key == "script" and action == "Create":
                return self._ok("script.Create", {"result": {"id": 5}})
            if component_key == "script:5" and action == "PutCode":
                return self._fail("script:5.PutCode", error="Device rejected code")
            raise AssertionError(f"Unexpected call: {component_key}.{action}")

        mock_device_gateway.execute_component_action = AsyncMock(
            side_effect=side_effect
        )

        results = await use_case.deploy_bulk_script(
            ["192.168.1.100"], "my-script", "broken code"
        )

        assert results[0].success is False
        assert results[0].error == "Device rejected code"
        assert results[0].data["script_id"] == 5

    async def test_it_deletes_existing_script_with_same_name_before_deploying(
        self, use_case, mock_device_gateway
    ):
        async def side_effect(ip, component_key, action, parameters=None):
            if component_key == "script" and action == "List":
                return self._ok(
                    "script.List",
                    {"result": {"scripts": [{"id": 9, "name": "my-script"}]}},
                )
            if component_key == "script:9" and action == "Delete":
                return self._ok("script:9.Delete")
            if component_key == "script" and action == "Create":
                return self._ok("script.Create", {"result": {"id": 10}})
            if component_key == "script:10" and action == "PutCode":
                return self._ok("script:10.PutCode")
            if component_key == "script:10" and action == "SetConfig":
                return self._ok("script:10.SetConfig")
            if component_key == "script:10" and action == "Start":
                return self._ok("script:10.Start")
            raise AssertionError(f"Unexpected call: {component_key}.{action}")

        mock_device_gateway.execute_component_action = AsyncMock(
            side_effect=side_effect
        )

        results = await use_case.deploy_bulk_script(
            ["192.168.1.100"], "my-script", "code"
        )

        assert results[0].success is True
        assert results[0].data["steps"]["removed_existing"] is True
        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.100", "script:9", "Delete", {}
        )

    async def test_it_deploys_to_multiple_devices_in_parallel(
        self, use_case, mock_device_gateway
    ):
        async def side_effect(ip, component_key, action, parameters=None):
            if component_key == "script" and action == "List":
                return ActionResult(
                    success=True,
                    action_type="script.List",
                    device_ip=ip,
                    message="ok",
                    data={"result": {"scripts": []}},
                )
            if component_key == "script" and action == "Create":
                return ActionResult(
                    success=True,
                    action_type="script.Create",
                    device_ip=ip,
                    message="ok",
                    data={"result": {"id": 1}},
                )
            return ActionResult(
                success=True,
                action_type=f"script:1.{action}",
                device_ip=ip,
                message="ok",
            )

        mock_device_gateway.execute_component_action = AsyncMock(
            side_effect=side_effect
        )

        device_ips = ["192.168.1.100", "192.168.1.101", "192.168.1.102"]
        results = await use_case.deploy_bulk_script(device_ips, "my-script", "code")

        assert len(results) == 3
        assert {r.device_ip for r in results} == set(device_ips)
        assert all(r.success for r in results)


class TestApplyBulkConfigDeviceIdPlaceholder:

    @pytest.fixture
    def use_case(self, mock_device_gateway):
        return BulkOperationsUseCase(device_gateway=mock_device_gateway)

    async def test_it_sends_config_unchanged_when_no_placeholder_present(
        self, use_case, mock_device_gateway
    ):
        mock_device_gateway.get_component_keys = AsyncMock(return_value=["mqtt"])
        mock_device_gateway.discover_device = AsyncMock()
        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=True,
                action_type="mqtt.SetConfig",
                device_ip="192.168.1.100",
                message="ok",
            )
        )

        config = {"enable": True, "server": "192.168.1.50:1883"}
        await use_case.apply_bulk_config(["192.168.1.100"], "mqtt", config)

        mock_device_gateway.discover_device.assert_not_called()
        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.100", "mqtt", "SetConfig", {"config": config}
        )

    async def test_it_substitutes_device_id_placeholder_per_device(
        self, use_case, mock_device_gateway
    ):
        mock_device_gateway.get_component_keys = AsyncMock(return_value=["mqtt"])

        async def discover_side_effect(ip, timeout=None):
            return DiscoveredDevice(
                ip=ip,
                status=Status.DETECTED,
                device_id="shellypro4pm-" + ip.replace(".", ""),
            )

        mock_device_gateway.discover_device = AsyncMock(
            side_effect=discover_side_effect
        )
        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=True,
                action_type="mqtt.SetConfig",
                device_ip="192.168.1.100",
                message="ok",
            )
        )

        config = {
            "enable": True,
            "topic_prefix": "telemetry/{{device_id}}",
            "nested": {"also": "{{device_id}}-suffix"},
        }

        await use_case.apply_bulk_config(
            ["192.168.1.100", "192.168.1.101"], "mqtt", config
        )

        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.100",
            "mqtt",
            "SetConfig",
            {
                "config": {
                    "enable": True,
                    "topic_prefix": "telemetry/shellypro4pm-1921681100",
                    "nested": {"also": "shellypro4pm-1921681100-suffix"},
                }
            },
        )
        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.101",
            "mqtt",
            "SetConfig",
            {
                "config": {
                    "enable": True,
                    "topic_prefix": "telemetry/shellypro4pm-1921681101",
                    "nested": {"also": "shellypro4pm-1921681101-suffix"},
                }
            },
        )
        # original config dict passed in must not be mutated
        assert config["topic_prefix"] == "telemetry/{{device_id}}"

    async def test_it_falls_back_to_ip_when_device_id_unavailable(
        self, use_case, mock_device_gateway
    ):
        mock_device_gateway.get_component_keys = AsyncMock(return_value=["mqtt"])
        mock_device_gateway.discover_device = AsyncMock(return_value=None)
        mock_device_gateway.execute_component_action = AsyncMock(
            return_value=ActionResult(
                success=True,
                action_type="mqtt.SetConfig",
                device_ip="192.168.1.100",
                message="ok",
            )
        )

        config = {"topic_prefix": "telemetry/{{device_id}}"}
        await use_case.apply_bulk_config(["192.168.1.100"], "mqtt", config)

        mock_device_gateway.execute_component_action.assert_any_call(
            "192.168.1.100",
            "mqtt",
            "SetConfig",
            {"config": {"topic_prefix": "telemetry/192.168.1.100"}},
        )
