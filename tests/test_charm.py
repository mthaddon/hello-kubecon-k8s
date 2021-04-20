# Copyright 2021 Jon Seager
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import unittest
import yaml
from unittest.mock import patch, Mock

from ops.model import ActiveStatus
from ops.testing import Harness
from charm import HelloKubeconCharm


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(HelloKubeconCharm)
        self.harness.begin()

    def test_gosherve_layer(self):
        # Test with empty config.
        self.assertEqual(self.harness.charm.config['redirect-map'], '')
        expected = {
            "summary": "gosherve layer",
            "description": "pebble config layer for gosherve",
            "services": {
                "gosherve": {
                    "override": "replace",
                    "summary": "gosherve service",
                    "command": "/gosherve",
                    "startup": "enabled",
                    "environment": {
                        "REDIRECT_MAP_URL": "",
                        "WEBROOT": "/srv/hello-kubecon",
                    },
                }
            },
        }
        self.assertEqual(self.harness.charm._gosherve_layer(), expected)
        # And now test with a different value in the redirect-map config option.
        # Disable hook firing first.
        self.harness.disable_hooks()
        self.harness.update_config({"redirect-map": "test value"})
        expected["services"]["gosherve"]["environment"]["REDIRECT_MAP_URL"] = "test value"
        self.assertEqual(self.harness.charm._gosherve_layer(), expected)

    @patch('ops.model.Container.get_service')
    @patch('ops.model.Container.start')
    @patch('ops.model.Container.stop')
    def test_on_config_changed(self, _stop, _start, _get_service):
        class FakeService:
            def __init__(self, is_running_bool):
                self.is_running_bool = is_running_bool

            def is_running(self):
                return self.is_running_bool

        _get_service.return_value = FakeService(False)

        plan = self.harness.get_container_pebble_plan("gosherve")
        self.assertEqual(plan.to_yaml(), "{}\n")
        # Trigger a config-changed hook.
        self.harness.update_config({"redirect-map": "test value"})
        plan = self.harness.get_container_pebble_plan("gosherve")
        expected = {
            "services": {
                "gosherve": {
                    "override": "replace",
                    "summary": "gosherve service",
                    "command": "/gosherve",
                    "startup": "enabled",
                    "environment": {
                        "REDIRECT_MAP_URL": "test value",
                        "WEBROOT": "/srv/hello-kubecon",
                    },
                }
            }
        }
        self.assertEqual(plan.to_yaml(), yaml.dump(expected))
        # Because is_running was False, confirm we called start, but not stop.
        _start.assert_called_once
        _stop.assert_not_called
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

        # Now test with is_running == True.
        _start.reset_mock()
        _stop.reset_mock()
        _get_service.return_value = FakeService(True)
        self.harness.update_config({"redirect-map": "test2 value"})
        plan = self.harness.get_container_pebble_plan("gosherve")
        expected = {
            "services": {
                "gosherve": {
                    "override": "replace",
                    "summary": "gosherve service",
                    "command": "/gosherve",
                    "startup": "enabled",
                    "environment": {
                        "REDIRECT_MAP_URL": "test2 value",
                        "WEBROOT": "/srv/hello-kubecon",
                    },
                }
            }
        }
        self.assertEqual(plan.to_yaml(), yaml.dump(expected))
        # Because is_running was True, confirm we called start and stop.
        _start.assert_called_once
        _stop.assert_called_once
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

        # Now test with empty config. Confirm that _gosherve_layer isn't called.
        with patch("charm.HelloKubeconCharm._gosherve_layer") as _gosherve_layer:
            self.harness.update_config({"redirect-map": ""})
            _gosherve_layer.assert_not_called

    @patch('charm.HelloKubeconCharm._fetch_site')
    def test_on_install(self, _fetch_site):
        self.harness.charm._on_install("mock_event")
        _fetch_site.assert_called_once

    @patch('charm.HelloKubeconCharm._fetch_site')
    def test_pull_site_action(self, _fetch_site):
        mock_event = Mock()
        self.harness.charm._pull_site_action(mock_event)
        _fetch_site.assert_called_once
        mock_event.called_once_with({"result": "site pulled"})
