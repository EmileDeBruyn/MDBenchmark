# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; coding:utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 fileencoding=utf-8
#
# MDBenchmark
# Copyright (c) 2017-2020 The MDBenchmark development team and contributors
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
# import string
import subprocess
import numpy as np
# from shutil import copyfile

from mdbenchmark import console

NAME = "rest2"

def prepare_benchmark(name, relative_path, *args, **kwargs):
    benchmark = kwargs["benchmark"]

    top_file = name + ".top"
    gro_file = name + ".gro"
    mdp_file = name + ".mdp"

    # filepath = os.path.join(relative_path, full_filename)

    if not kwargs["multidir"] >= 1:
        raise ValueError("For REST2 benchmarks, the multidir option must be given a number larger than 1")

    N_replicas = kwargs["multidir"]
    temp_range = np.array([float(x) for x in kwargs["temprange"].split(",")])

    def calc_replica_temps(N_replicas, temp_range):
        replica_temps = temp_range.min() \
            * np.exp(np.arange(0, N_replicas) * np.log(temp_range.max()/temp_range.min())/(N_replicas - 1))
        return replica_temps

    temps = calc_replica_temps(N_replicas, temp_range)

    plumeddat = benchmark["plumed.dat"].touch()

    for rep, temp in enumerate(temps):
        l = f"{temps[0] / temp:.6f}"
        rep_string = "rep" + f"{rep+1:02d}"
        subdir = benchmark[rep_string + "/"].make()
        plumed_cmd = f"plumed partial_tempering {l} < {top_file} | tail -n +2 > {subdir}/rep.top"
        plumed_process = subprocess.Popen(plumed_cmd, shell=True, executable="/bin/bash")
        plumed_process.wait()
        # grompp_cmd = f"gmx grompp -maxwarn 1 -o {subdir}/rep.tpr -c {gro_file} -f {mdp_file} -p {subdir}/rep.top -quiet &> {subdir}/grompp.out &"
        grompp_cmd = f"gmx grompp -maxwarn 1 -o {subdir}/rep.tpr -c {gro_file} -f {mdp_file} -p {subdir}/rep.top &> {subdir}/grompp.out &"
        subprocess.Popen(grompp_cmd, shell=True, executable="/bin/bash")

    return name


def prepare_multidir(multidir):
    multidir_string = ""

    multidir_string = "-multidir"
    for i in range(multidir):
        multidir_string += " rep" + f"{i+1:02d}"

    return multidir_string


def check_input_file_exists(name):
    """Check if the top, gro and mdp files exist."""
    fn = name
    extensions = [".top", ".gro", ".mdp"]
    for extension in extensions:
        if not os.path.exists(fn + extension):
            console.error(
                "File {} does not exist, but is needed for REST2 benchmarks.", fn + extension
            )

    return True
