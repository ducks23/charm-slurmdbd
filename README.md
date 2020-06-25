# Slurmdbd Charm


![alt text](.github/slurm.png)

<p align="center"><b>This is the Slurmdbd charm for the Slurm Workload Manager</b>, <i>"The Slurm Workload Manager (formerly known as Simple Linux Utility for Resource Management or SLURM), or Slurm, is a free and open-source job scheduler for Linux and Unix-like kernels, used by many of the world's supercomputers and computer clusters."</i></p>

Quickstart
----------


```bash
python3 -m venv venv
source venv/bin/activate
make build
juju deploy ./slurmdbd.charm
juju deploy mysql
juju relate mysql:db slurmdbd:db
juju relate slurmdbd:munge slurmdctld:munge
```
There is also the option of supplying the Slurmdbd Charm with the slurm-snap as a resource to avoid downloading from the snapstore

```bash
juju deploy ./slurmdbd.charm --resource slurm=/path/to/slurm_snap
```

Contact
-------
 - Author: Jesse <jesse@omnivector.solutions>
 - Bug Tracker: [here](https://github.com/omnivector-solutions/charm-slurmdbd)
