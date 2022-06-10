import logging
import signal
import sys
from time import sleep

from solidlab_perfstat.measurement import Measurement

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG)
# logger.setLevel(logging.ERROR)


def main() -> int:
    # very minimal CLI support for now.
    show_help = True
    network_iface = None
    perftest_endpoint = None
    if len(sys.argv) in (2, 3):
        perftest_endpoint = sys.argv[1].strip()
        show_help = not perftest_endpoint.startswith("http")
        assert perftest_endpoint.startswith("http")
        assert "/perftest/" in perftest_endpoint
        assert not perftest_endpoint.endswith("/")
        assert not perftest_endpoint.endswith("perftest/")
        assert not perftest_endpoint.endswith("perftest")
        assert not perftest_endpoint.endswith("artifact")
        assert not perftest_endpoint.endswith("artifact/")

        if len(sys.argv) == 3:
            network_iface = sys.argv[2].strip()
    elif len(sys.argv) == 1:
        perftest_endpoint = None
        show_help = False
    if show_help:
        print(
            "Usage: interval-system-monitor [<perftest_post_endpoint> [<network_iface>]]"
        )
        print(
            "          perftest_post_endpoint: the URL of the solidlab-perftest-server perftest endpoint (optional)"
            "          network_iface: the name of the network interface to monitor (default: all) (optional)"
        )
        return 1

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
    sys.exit(main())
