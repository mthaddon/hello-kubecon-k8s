## Kubecon Demonstration Charm

This charm is a demonstration of the new Sidecar Charm pattern for Juju 2.9. It uses [Pebble](https://github.com/canonical/pebble) and the [Python Operator Framework](https://pythonoperatorframework.io). It deploys a copy of [gosherve](https://github.com/jnsgruk/gosherve) and relies upon the sidecar container to populate a shared volume with web files.

Overview of features:

- Deploy a container running [gosherve](https://github.com/jnsgruk/gosherve)
- Charm container fetches a zip archive of a website [from Github](https://github.com/jnsgruk/test-site)
- Charm container put the contents of the archive in a storage volume
- Once a `redirect-map` config item is set, `gosherve` is started
- There is a `pull-site` action which will pull the latest version of the test site and extract it
- Ingress relation is implemented and creates an ingress of class "public" and hostname "hellokubecon.juju"

### Deployment

At present, this charm cannot be published to Charmhub, so you will need to build it locally. To setup a local test environment with [MicroK8s](https://microk8s.io), do the following:

```bash
$ sudo snap install --classic microk8s
$ sudo usermod -aG microk8s $(whoami)
$ sudo microk8s enable storage dns
$ sudo snap alias microk8s.kubectl kubectl
$ newgrp microk8s
```

Next install Charmcraft and build the Charm

```bash
# Install Charmcraft
$ sudo snap install charmcraft --edge

# Clone an example charm
$ git clone https://github.com/jnsgruk/hello-kubecon-k8s
# Build the charm
$ cd chello-kubecon-k8s
$ charmcraft build
```

Now you're ready to deploy the Charm:

```bash
# For now, we require the 2.9/edge channel until features land in candidate/stable
$ sudo snap refresh juju --channel=2.9/edge
# Create a model for our deployment
$ juju add-model kubecon

# Deploy!
$ juju deploy ./hello-kubecon.charm \
    --resource gosherve-image=jnsgruk/gosherve:latest \
    --config gist_url="<some redirect map url>"

$ cd ..
# Clone the ingress charm
$ git clone https://git.launchpad.net/charm-k8s-ingress
$ cd charm-k8s-ingress
# Build the ingress charm
$ charmcraft build
# Deploy the ingress charm
$ juju deploy ./nginx-ingress-integrator --config kube-config="$(microk8s config)"
# Relate our app to the ingress
$ juju relate hello-kubecon nginx-ingress-integrator
# Add an entry to /etc/hosts
$ echo "127.0.1.1 hellokubecon.juju" | sudo tee -a /etc/hosts
# Wait for the deployment to complete
$ watch -n1 --color "juju status --color"
```

You should be able to visit http://hellokubecon.juju in your browser.
