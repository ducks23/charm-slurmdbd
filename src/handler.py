from pathlib import Path

import logging

import subprocess

import os

logger = logging.getLogger()


class SlurmSnapOps():

    def install(self):
        cmd = ["snap", "install"]
        resource_found = True
        
        #checks to see if resource is supplied locally
        try:
            resource = subprocess.check_output(['resource-get', 'slurm'])
            resource = resource.decode().strip()
        except:
            resource_found = False
            logger.info("couldn't find snap locally")
        
        if resource_found is True:
            cmd.append(resource)
            cmd.append("--dangerous")
            cmd.append("--classic")

        #installs from the snap store
        else:
            cmd.append("slurm")
            cmd.append("--edge")

        subprocess.call(cmd)
        subprocess.call(["snap", "connect", "slurm:network-control"])
        subprocess.call(["snap", "connect", "slurm:system-observe"])
        subprocess.call(["snap", "connect", "slurm:hardware-observe"])

    def render_config(self, source, target, context):
        """Render the context into the source template and write
        it to the target location.
        """

        source = Path(source)
        target = Path(target)

        if context and type(context) == dict:
            ctxt = context
        else:
            raise TypeError(
                f"Incorect type {type(context)} for context - Please debug."
            )

        if not source.exists():
            raise Exception(
                f"Source config {source} does not exist - Please debug."
            )

        if target.exists():
            target.unlink()

        with open(str(target), 'w') as f:
            f.write(open(str(source), 'r').read().format(**ctxt))


    def set_mode(self, snap_mode):
        command = f"snap.mode={snap_mode}"
        subprocess.call(["snap", "set", "slurm", command])
