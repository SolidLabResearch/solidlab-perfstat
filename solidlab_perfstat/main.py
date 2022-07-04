import logging
import os
import signal
import sys
from time import sleep

import click

from solidlab_perfstat.measurement import Measurement

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG)
# logger.setLevel(logging.ERROR)


@click.command()
@click.option(
    "-e",
    "--endpoint",
    required=False,
    help="URL of the solidlab-perftest-server perftest endpoint",
)
@click.option(
    "-i",
    "--iface",
    required=False,
    help="Name of the network interface to monitor (default: all)",
)
def main(endpoint, iface) -> int:
    perftest_endpoint = endpoint
    network_iface = iface
    if perftest_endpoint:
        assert perftest_endpoint.startswith("http")
        assert "/perftest/" in perftest_endpoint
        assert not perftest_endpoint.endswith("/")
        assert not perftest_endpoint.endswith("perftest/")
        assert not perftest_endpoint.endswith("perftest")
        assert not perftest_endpoint.endswith("artifact")
        assert not perftest_endpoint.endswith("artifact/")

    if "PERFSTAT_NETWORK_IFACE" in os.environ:
        network_iface = os.environ["PERFSTAT_NETWORK_IFACE"]
    if "PERFSTAT_PERFTEST_ENDPOINT" in os.environ:
        perftest_endpoint = os.environ["PERFSTAT_PERFTEST_ENDPOINT"]

    args_left = list(sys.argv[0])
    args_left.pop(0)  # drop exe name

    if args_left and not perftest_endpoint:
        arg = args_left.pop(0)

        perftest_endpoint = arg.strip()
        show_help = not perftest_endpoint.startswith("http")
        assert perftest_endpoint.startswith("http")
        assert "/perftest/" in perftest_endpoint
        assert not perftest_endpoint.endswith("/")
        assert not perftest_endpoint.endswith("perftest/")
        assert not perftest_endpoint.endswith("perftest")
        assert not perftest_endpoint.endswith("artifact")
        assert not perftest_endpoint.endswith("artifact/")

    measurement = Measurement(network_iface)

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

    if not perftest_endpoint:
        measurement.make_all()
    else:
        measurement.post_all(perftest_endpoint)

    return 0


if __name__ == "__main__":
    sys.exit(main(auto_envvar_prefix="PERFSTAT"))
