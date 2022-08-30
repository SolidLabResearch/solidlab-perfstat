import logging
import os
import signal
import sys
from time import sleep
from typing import Optional

import click
from solidlab_perftest_common.upload_artifact import validate_artifact_endpoint

from solidlab_perfstat.measurement import Measurement

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG)
# logger.setLevel(logging.ERROR)


@click.command()
@click.option(
    "-e",
    "--endpoint",
    envvar="PERFSTAT_ENDPOINT",
    required=False,
    help="URL of the solidlab-perftest-server artifact endpoint",
)
@click.option(
    "-t",
    "--auth-token",
    envvar="PERFSTAT_AUTH_TOKEN",
    required=False,
    help="Authentication token for talking to solidlab-perftest-server artifact endpoint",
)
@click.option(
    "-i",
    "--iface",
    envvar="PERFSTAT_IFACE",
    required=False,
    help="Name of the network interface to monitor (default: all)",
)
def main(
    endpoint: Optional[str], iface: Optional[str], auth_token: Optional[str]
) -> int:
    if endpoint:
        try:
            endpoint = validate_artifact_endpoint(endpoint)
        except ValueError as e:
            raise click.ClickException(getattr(e, "message", repr(e)))

    measurement = Measurement(iface)

    # noinspection PyUnusedLocal
    def signal_handler(sig, frame):
        print(f"{signal.Signals(sig).name} received. Will finishing work.")
        measurement.finish()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    measurement.start()  # forget first values, we can only get relevant values after 1 second.
    while measurement.running:
        sleep(1.0)
        measurement.add()

    if not endpoint:
        measurement.make_all()
    else:
        measurement.post_all(endpoint, auth_token)

    return 0


if __name__ == "__main__":
    # Note: auto_envvar_prefix didn't seem to work, though it should:
    #       https://click.palletsprojects.com/en/8.1.x/options/#values-from-environment-variables
    sys.exit(main(auto_envvar_prefix="PERFSTAT"))
