from datetime import datetime, timezone
from os.path import basename
from typing import List, Dict, Tuple

import psutil
import pygal
import requests

from solidlab_perfstat.perftest_attach import post_attachment


class Result:
    def __init__(self):
        self.running = True
        self.times: List[datetime] = []
        self.stats: List[Dict[str, float]] = []
        self.cpu_count = 0

    @staticmethod
    def now() -> datetime:
        res = datetime.now(timezone.utc)
        return res.replace(microsecond=round(res.microsecond / 1_000_00) * 10)

    def add(self):
        if self.running:
            stat = {}

            self.times.append(self.now())
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

            self.stats.append(stat)

    def start(self):
        self.add()
        self.stats.clear()

    def finish(self):
        self.running = False

    def make_all(self):
        if not self.stats:
            print("No results yet")
            return

        detail_csv = self.make_detail_csv()
        summary_csv = self.make_summary_csv()
        result_files = self.make_graphs()

        # Save to file
        try:
            detail_csv_file = "details.csv"
            with open(detail_csv_file, "w") as f:
                f.write(detail_csv)
            result_files.append(detail_csv_file)

            summary_csv_file = "summary.csv"
            with open(summary_csv_file, "w") as f:
                f.write(summary_csv)
            result_files.append(summary_csv_file)
        except IOError:
            raise

        for result_file in result_files:
            print(f"Wrote: {result_file}")

    def post_all(self, result_post_endpoint: str):
        if not self.stats:
            print("No results yet")
            return

        detail_csv = self.make_detail_csv()
        graph_files = self.make_graphs()
        summary_csv = self.make_summary_csv()

        if not result_post_endpoint.endswith("/"):
            result_post_endpoint += "/"

        # POST results
        with requests.Session() as session:
            get_result_resp = session.get(result_post_endpoint)
            get_result_resp.raise_for_status()
            resp_json = get_result_resp.json()
            assert (
                "test_result_id" in resp_json
            ), f"test_result_id is not in {resp_json!r}"
            result_id = resp_json["test_result_id"]

            post_attachment(
                session=session,
                result_post_endpoint=result_post_endpoint,
                result_id=result_id,
                attach_type="CSV",
                subtype="summary",
                description="Summary of all measurements",
                content=summary_csv.encode(),
            )
            post_attachment(
                session=session,
                result_post_endpoint=result_post_endpoint,
                result_id=result_id,
                attach_type="CSV",
                subtype="detail",
                description="Detailed measurements",
                content=detail_csv.encode(),
            )

            for graph_file in graph_files:
                with open(graph_file, "rb") as f:
                    graph_content = f.read()
                post_attachment(
                    session=session,
                    result_post_endpoint=result_post_endpoint,
                    result_id=result_id,
                    attach_type="GRAPH",
                    subtype=basename(graph_file),
                    description="TODO " + basename(graph_file),
                    content=graph_content,
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
        res_files = []
        dateline = pygal.DateLine(x_label_rotation=25)
        dateline.x_labels = self.times
        data = []
        for i in range(len(self.stats)):
            t = self.times[i]
            stat = self.stats[i]
            data.append((t, stat["cpu_all_user+system_perc"]))
        dateline.add("CPU Usage (%)", data)
        dateline.render_to_file("cpu1.svg")
        res_files.append("cpu1.svg")

        data_user = []
        data_system = []
        data_other = []
        for i in range(len(self.stats)):
            t = self.times[i]
            stat = self.stats[i]
            data_user.append((t, stat["cpu_all_user_perc"]))
            data_system.append((t, stat["cpu_all_system_perc"]))
            data_other.append((t, stat["cpu_all_other_perc"]))
        dateline.add("CPU User (%)", data_user)
        dateline.add("CPU System (%)", data_system)
        dateline.add("CPU Other (%)", data_other)
        dateline.render_to_file("cpu3.svg")
        res_files.append("cpu3.svg")

        data_cpus: List[List[Tuple[datetime, float]]] = [
            list() for _ in range(self.cpu_count)
        ]
        for i in range(len(self.stats)):
            t = self.times[i]
            stat = self.stats[i]
            for cpu_index in range(self.cpu_count):
                data_cpus[cpu_index].append((t, stat[f"cpu_{cpu_index}_perc"]))
        for cpu_index in range(self.cpu_count):
            dateline.add(f"CPU{cpu_index} Usage (%)", data_cpus[cpu_index])
        dateline.render_to_file("cpus.svg")
        res_files.append("cpus.svg")
        return res_files

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
