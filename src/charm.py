#!/usr/bin/env python3
# Copyright 2021 Jon Seager
# See LICENSE file for licensing details.

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

    https://discourse.charmhub.io/t/4208
"""

import logging
import shutil
from os.path import isdir
from urllib.request import urlopen
from zipfile import ZipFile

from charms.nginx_ingress_integrator.v0.ingress import IngressRequires
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus

logger = logging.getLogger(__name__)

STORAGE_PATH = "/var/lib/juju/storage/webroot/0"
SITE_SRC = "https://github.com/jnsgruk/test-site/archive/refs/heads/master.zip"


class HelloKubeconCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.pull_site_action, self._pull_site_action)

        self.ingress = IngressRequires(self, {
            "service-hostname": "hellokubecon.juju",
            "ingress-class": "public",
            "service-name": self.app.name,
            "service-port": 8080
        })

    def _on_install(self, _):
        # Download the site
        self._fetch_site()

    def _on_config_changed(self, _):
        """Handle the config changed event."""
        # Get the gosherve container so we can configure/manipulate it
        container = self.unit.get_container("gosherve")
        # Do not continue if the configuration is incomplete
        if not self._check_config():
            return

        # Create a new config layer
        layer = self._gosherve_layer()
        # Get the current config
        plan = container.get_plan()
        # Check if there are any changes to services
        if plan.services != layer["services"]:
            # Changes were made, add the new layer
            container.add_layer("gosherve", layer, combine=True)
            logging.info("Added updated layer 'gosherve' to Pebble plan")
            # Stop the service if it is already running
            if container.get_service("gosherve").is_running():
                container.stop("gosherve")
            # Restart it and report a new status to Juju
            container.start("gosherve")
            logging.info("Restarted gosherve service")

        # All is well, set an ActiveStatus
        self.unit.status = ActiveStatus()

    def _gosherve_layer(self) -> dict:
        """Returns a Pebble configuration layer for Gosherve"""
        return {
            "summary": "gosherve layer",
            "description": "pebble config layer for gosherve",
            "services": {
                "gosherve": {
                    "override": "replace",
                    "summary": "gosherve service",
                    "command": "/gosherve",
                    "startup": "enabled",
                    "environment": {
                        "REDIRECT_MAP_URL": self.model.config["redirect-map"],
                        "WEBROOT": "/srv/hello-kubecon",
                    },
                }
            },
        }

    def _pull_site_action(self, event):
        """Action handler that pulls the latest site archive and unpacks it"""
        self._fetch_site()
        event.set_results({"result": "site pulled"})

    def _fetch_site(self):
        """Fetch latest copy of website from Github and move into webroot"""
        # Set some status and do some logging
        self.unit.status = MaintenanceStatus("Fetching web site")
        logger.info("Downloading site archive from %s", SITE_SRC)
        # Download the zip
        resp = urlopen(SITE_SRC)
        with open("/tmp/site.zip", "wb") as tmp:
            tmp.write(resp.read())

        # Extract the zip
        with ZipFile("/tmp/site.zip") as zf:
            zf.extractall(path="/tmp/site")

        # Remove existing version if it exists
        if isdir(f"{STORAGE_PATH}/hello-kubecon"):
            shutil.rmtree(f"{STORAGE_PATH}/hello-kubecon")
        # Move the downloaded web files into place
        shutil.move(src="/tmp/site/test-site-master", dst=f"{STORAGE_PATH}/hello-kubecon")
        self.unit.status = ActiveStatus()

    def _check_config(self):
        """Check that everything is in place to start Gosherve"""
        if self.model.config["redirect-map"] == "":
            self.unit.status = BlockedStatus("No 'redirect-map' config specified")
            return False
        return True


if __name__ == "__main__":
    main(HelloKubeconCharm)
