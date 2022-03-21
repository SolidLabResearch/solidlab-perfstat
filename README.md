# SolidLab PerfStat

Monitors the CPU, Mem, Disk I/O and network I/O of a system until interrupted.

Intended use case: monitor system resources during a test run of some piece of software.

Monitoring is done until the process is interrupted with SIGINT (CTRL-C).
At that point, the following data is outputted:
- A CSV with statistics for each second.
- Graphs of these CSVs
- A CSV with aggregate data (totals, averages, ...)
`solidlab-perfstat` exits after outputting this data.

## Internal details

Uses python libs `psutils` for system monitoring, and `pygal` for easy graph creation.

## Data output

### Generic: files

If no arguments are given, all data is written to local (`.csv` and `.svg`) files.

### SolidLab: upload

When a [solidlab-perftest-server](link TODO) result endpoint is provided as argument, instead of writing files, the data will be uploaded using the URL.

(This method depends heavily on the `solidlab-perftest-server` API and is thus not generic in any way.)
