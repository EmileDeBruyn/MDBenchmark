# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; coding:utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 fileencoding=utf-8
#
# MDBenchmark
# Copyright (c) 2017 Max Linke & Michael Gecht and contributors
# (see the file AUTHORS for the full list of names)
#
# MDBenchmark is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MDBenchmark is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MDBenchmark.  If not, see <http://www.gnu.org/licenses/>.
import os
import subprocess
from glob import glob

import click

import mdsynthesis as mds
import numpy as np
import pandas as pd

from . import console
from .cli import cli
from .mdengines import detect_md_engine
from .mdengines.utils import cleanup_before_restart
from .utils import DataFrameFromBundle, ConsolidateDataFrame, PrintDataFrame

PATHS = os.environ["PATH"].split(":")
BATCH_SYSTEMS = {"slurm": "sbatch", "sge": "qsub", "Loadleveler": "llsubmit"}


def get_batch_command():
    for p in PATHS:
        for b in BATCH_SYSTEMS.values():
            if glob(os.path.join(p, b)):
                return b
    console.error(
        "Was not able to find a batch system. Are you trying to use this "
        "package on a host with a queuing system?"
    )


@cli.command()
@click.option(
    "-d",
    "--directory",
    help="Path in which to look for benchmarks.",
    default=".",
    show_default=True,
)
@click.option(
    "-f",
    "--force",
    "force_restart",
    help="Resubmit all benchmarks and delete all previous results.",
    is_flag=True,
)
@click.option("-y", "--yes", is_flag=True, help="Answer all prompts with yes.")
def submit(directory, force_restart, yes):
    """Submit benchmarks to queuing system.

    Benchmarks are searched recursively starting from the directory specified
    in `--directory`. If the option is not specified, the working directory
    will be used.

    Requests a user prompt. Using `--yes` flag skips this step.

    Checks whether benchmark folders were already generated, exits otherwise.
    Only runs benchmarks that were not already started. Can be overwritten with
    `--force`.
    """
    bundle = mds.discover(directory)

    # Exit if no bundles were found in the current directory.
    if not bundle:
        console.error("No benchmarks found.")

    df = DataFrameFromBundle(bundle)

    # Reformat NaN values nicely into question marks.
    df_to_print = df.replace(np.nan, "?")
    df_to_print = df.drop(columns=["ns/day", "ncores"])
    # with pd.option_context("display.max_rows", None):
    #    print(df_to_print)
    console.info("{}", "Benchmark Summary:")
    df_short = ConsolidateDataFrame(df_to_print)
    PrintDataFrame(df_short)

    # here I add the user promt to confirm the submission of the simulations
    if yes:
        console.info("The above benchmarks will be submitted.")
    elif not click.confirm("The above benchmarks will be submitted. Continue?"):
        console.error("Exiting. No benchmarks submitted.")

    grouped_bundles = bundle.categories.groupby("started")
    try:
        bundles_not_yet_started = grouped_bundles[False]
    except KeyError:
        bundles_not_yet_started = None
    if not bundles_not_yet_started and not force_restart:
        console.error(
            "All generated benchmarks were already started once. "
            "You can force a restart with {}.",
            "--force",
        )
    # Start all benchmark simulations if a restart was requested. Otherwise
    # only start the ones that were not run yet.
    bundles_to_start = bundle
    if not force_restart:
        bundles_to_start = bundles_not_yet_started
    batch_cmd = get_batch_command()
    console.info("Submitting a total of {} benchmarks.", len(bundles_to_start))
    for sim in bundles_to_start:
        # Remove files generated by previous mdbenchmark run
        if force_restart:
            engine = detect_md_engine(sim["module"])
            cleanup_before_restart(engine=engine, sim=sim)
        sim.categories["started"] = True
        os.chdir(sim.abspath)
        subprocess.call([batch_cmd, "bench.job"])
    console.info(
        "Submitted all benchmarks. Run {} once they are finished to get the results.",
        "mdbenchmark analyze",
    )
