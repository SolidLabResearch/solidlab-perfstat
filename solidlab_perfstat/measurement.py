from datetime import datetime, timezone
from os.path import basename
from typing import List, Dict, Tuple, Optional

import psutil
import pygal
import requests
from solidlab_perftest_common.upload_artifact import (
    upload_artifact_file,
    upload_artifact,
)


class Measurement:
    def __init__(self, nic_name=None):
        self.nic_name = nic_name
        self.running = True
        self.times: List[datetime] = []
        self.stats: List[Dict[str, float]] = []
        self.prev_stats: Optional[Dict[str, float]] = None
        self.cpu_count = 0

    @staticmethod
    def now() -> datetime:
        res = datetime.now(timezone.utc)
        return res.replace(microsecond=round(res.microsecond / 1_000_00) * 10)

    def add(self):
        if self.running:
            stat = {}

            self.times.append(self.now())

            # CPU
            # noinspection PyProtectedMember
            cpu_combined_times = psutil.cpu_times_percent(
                percpu=False
            )  # type: psutil._pslinux.scputimes
            stat["cpu_all_user_perc"] = cpu_combined_times.user
            stat["cpu_all_system_perc"] = cpu_combined_times.system
            stat["cpu_all_user+system_perc"] = (
                cpu_combined_times.user + cpu_combined_times.system
            )
            stat["cpu_all_idle_perc"] = cpu_combined_times.idle
            stat["cpu_all_other_perc"] = 100.0 - (
                cpu_combined_times.user
                + cpu_combined_times.system
                + cpu_combined_times.idle
            )

            # noinspection PyTypeChecker
            cpu_separate_perc: List[float] = psutil.cpu_percent(percpu=True)
            self.cpu_count = len(cpu_separate_perc)
            for index, cpu_perc in enumerate(cpu_separate_perc):
                stat[f"cpu_{index}_perc"] = cpu_perc

            # NET
            net_stats = psutil.net_io_counters(pernic=self.nic_name is not None)
            stat[f"net_bytes_sent"] = (
                net_stats[self.nic_name].bytes_sent
                if self.nic_name
                else net_stats.bytes_sent
            )
            stat[f"net_bytes_recv"] = (
                net_stats[self.nic_name].bytes_recv
                if self.nic_name
                else net_stats.bytes_recv
            )

            # Disk I/O
            disk_stats = psutil.disk_io_counters(nowrap=True)
            stat[f"disk_read_bytes"] = disk_stats.read_bytes
            stat[f"disk_write_bytes"] = disk_stats.write_bytes

            full_state = dict(stat)

            # some stats keep aggregating, and thus need the previous stats subtracted
            for stat_name in (
                "net_bytes_sent",
                "net_bytes_recv",
                "disk_read_bytes",
                "disk_write_bytes",
            ):
                if self.prev_stats:
                    stat[stat_name] = stat[stat_name] - self.prev_stats[stat_name]
                else:
                    stat[stat_name] = 0  # no stats after first interval

            self.prev_stats = full_state
            self.stats.append(stat)

    def start(self):
        self.add()
        self.stats.clear()

    def finish(self):
        self.running = False

    def make_all(self):
        if not self.stats:
            print("No measurement yet")
            return

        detail_csv = self.make_detail_csv()
        summary_csv = self.make_summary_csv()
        graph_files = self.make_graphs()

        # Save to file
        try:
            detail_csv_file = "details.csv"
            with open(detail_csv_file, "w") as f:
                f.write(detail_csv)
            graph_files.append(detail_csv_file)

            summary_csv_file = "summary.csv"
            with open(summary_csv_file, "w") as f:
                f.write(summary_csv)
            graph_files.append(summary_csv_file)
        except IOError:
            raise

        for graph_file in graph_files:
            print(f"Wrote: {graph_file}")

    def post_all(self, perftest_endpoint: str, auth_token: Optional[str]):
        if not self.stats:
            print("No measurement yet")
            return

        detail_csv = self.make_detail_csv()
        graph_files = self.make_graphs()
        summary_csv = self.make_summary_csv()

        # POST perftest
        with requests.Session() as session:
            upload_artifact(
                session=session,
                perftest_endpoint=perftest_endpoint,
                attach_type="CSV",
                sub_type="summary",
                description="Summary of all measurements",
                content=summary_csv.encode(),
                content_type="text/csv",
                auth_token=auth_token,
            )
            upload_artifact(
                session=session,
                perftest_endpoint=perftest_endpoint,
                attach_type="CSV",
                sub_type="detail",
                description="Detailed measurements",
                content=detail_csv.encode(),
                content_type="text/csv",
                auth_token=auth_token,
            )

            for graph_file in graph_files:
                upload_artifact_file(
                    session=session,
                    perftest_endpoint=perftest_endpoint,
                    attach_type="GRAPH",
                    sub_type=basename(graph_file),
                    description="Graph " + basename(graph_file),
                    filename=graph_file,
                    auth_token=auth_token,
                )

    def make_detail_csv(self) -> str:
        keys = list(self.stats[0].keys())
        keys.sort()
        res = ""
        for key in keys:
            res += f"{key},"
        res += "\n"
        for stat in self.stats:
            keys = list(stat.keys())
            keys.sort()
            for key in keys:
                res += f"{stat[key]},"
            res += "\n"
        return res

    def make_graphs(self) -> List[str]:
        return [
            self.make_graph_cpu1(),
            self.make_graph_cpu3(),
            self.make_graph_cpus(),
            self.make_graph_net(),
            self.make_graph_disk(),
        ]

    def make_graph_net(self) -> str:
        data_sent = []
        data_recv = []
        prev_t = None
        for i in range(len(self.stats)):
            t = self.times[i]
            stat = self.stats[i]
            if prev_t:
                seconds_passed = (t - prev_t).total_seconds()
                data_sent.append(
                    (t, (stat["net_bytes_sent"] * 8 / (seconds_passed * 1_000_000)))
                )
                data_recv.append(
                    (t, (stat["net_bytes_recv"] * 8 / (seconds_passed * 1_000_000)))
                )
            prev_t = t
        dateline = pygal.DateLine(x_label_rotation=25)
        dateline.x_labels = self.times
        dateline.add("Data Sent (Mbit/s)", data_sent)
        dateline.add("Data Received (Mbit/s)", data_recv)
        dateline.render_to_file("net.svg")
        return "net.svg"

    def make_graph_disk(self) -> str:
        data_read = []
        data_write = []
        prev_t = None
        for i in range(len(self.stats)):
            t = self.times[i]
            stat = self.stats[i]
            if prev_t:
                seconds_passed = (t - prev_t).total_seconds()
                data_read.append(
                    (t, (stat["disk_read_bytes"] / (seconds_passed * 1_048_576)))
                )
                data_write.append(
                    (t, (stat["disk_write_bytes"] / (seconds_passed * 1_048_576)))
                )
            prev_t = t
        dateline = pygal.DateLine(x_label_rotation=25)
        dateline.x_labels = self.times
        dateline.add("Disk Read (MB/s)", data_read)
        dateline.add("Disk Write (MB/s)", data_write)
        dateline.render_to_file("disk.svg")
        return "disk.svg"

    def make_graph_cpu1(self) -> str:
        data = []
        for i in range(len(self.stats)):
            t = self.times[i]
            stat = self.stats[i]
            data.append((t, stat["cpu_all_user+system_perc"]))
        dateline = pygal.DateLine(x_label_rotation=25)
        dateline.x_labels = self.times
        dateline.add("CPU Usage (%)", data)
        dateline.render_to_file("cpu1.svg")
        return "cpu1.svg"

    def make_graph_cpu3(self) -> str:
        data_user = []
        data_system = []
        data_other = []
        for i in range(len(self.stats)):
            t = self.times[i]
            stat = self.stats[i]
            data_user.append((t, stat["cpu_all_user_perc"]))
            data_system.append((t, stat["cpu_all_system_perc"]))
            data_other.append((t, stat["cpu_all_other_perc"]))
        dateline = pygal.DateLine(x_label_rotation=25)
        dateline.x_labels = self.times
        dateline.add("CPU User (%)", data_user)
        dateline.add("CPU System (%)", data_system)
        dateline.add("CPU Other (%)", data_other)
        dateline.render_to_file("cpu3.svg")
        return "cpu3.svg"

    def make_graph_cpus(self) -> str:
        data_cpus: List[List[Tuple[datetime, float]]] = [
            list() for _ in range(self.cpu_count)
        ]
        for i in range(len(self.stats)):
            t = self.times[i]
            stat = self.stats[i]
            for cpu_index in range(self.cpu_count):
                data_cpus[cpu_index].append((t, stat[f"cpu_{cpu_index}_perc"]))
        dateline = pygal.DateLine(x_label_rotation=25)
        dateline.x_labels = self.times
        for cpu_index in range(self.cpu_count):
            dateline.add(f"CPU{cpu_index} Usage (%)", data_cpus[cpu_index])
        dateline.render_to_file("cpus.svg")
        return "cpus.svg"

    def make_summary_csv(self) -> str:
        keys = list(self.stats[0].keys())
        keys.sort()
        res = "stat,total,count,average\n"
        for key in keys:
            total = 0.0
            count = 0
            for stat in self.stats:
                if key in stat:
                    total += stat[key]
                    count += 1
            res += f"{key},{total},{count},{total/count}\n"
        return res
