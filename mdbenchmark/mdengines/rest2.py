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
import shutil
import subprocess
import re
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
# from shutil import copyfile

from mdbenchmark import console

NAME = "rest2"


def calc_state_temps(N_states, temp_range):
    state_temps = temp_range.min() \
    * np.exp(np.arange(0, N_states) * np.log(temp_range.max()/temp_range.min())/(N_states - 1))
    return state_temps


def copy_first_benchmark(relative_path, first_benchmark_path):
    # print(f"{relative_path} to {first_benchmark_path}")
    shutil.copytree(first_benchmark_path, relative_path, dirs_exist_ok=True)
    print(f"Copied first REST2 benchmark to {relative_path}.")


def prepare_benchmark(name, relative_path, *args, **kwargs):
    benchmark = kwargs["benchmark"]
    # print(benchmark)

    top_file = name + ".top"
    gro_file = name + ".gro"
    mdp_file = name + ".mdp"

    # top_file = benchmark[name + ".top"]
    # gro_file = benchmark[name + ".gro"]
    # mdp_file = benchmark[name + ".mdp"]

    # filepath = os.path.join(relative_path, full_filename)

    if not kwargs["multidir"] >= 1:
        raise ValueError("For REST2 benchmarks, the multidir option must be given a number larger than 1")

    if kwargs["benchmark_counter"] != 0:
        copy_first_benchmark(benchmark, kwargs["first_benchmark"])

    else:
        N_states = kwargs["multidir"]
        temp_range = np.array([float(x) for x in kwargs["temprange"].split(",")])

        temps = calc_state_temps(N_states, temp_range)

        plumeddat = benchmark["plumed.dat"].touch()
        # for state, temp in enumerate(temps):
        def task(state, temp):
            l = f"{temps[0] / temp:.6f}"
            state_string = "state" + f"{state+1:02d}"
            subdir = benchmark[state_string + "/"].make()
            # plumed_cmd = f"plumed partial_tempering {l} < {top_file} | tail -n +2 > {subdir}/state{state+1:02d}.top"
            plumed_cmd = f"plumed --no-mpi partial_tempering {l} < {top_file} | tail -n +2 > {subdir}/state.top"
            plumed_process = subprocess.Popen(plumed_cmd, shell=True, executable="/bin/bash")
            plumed_process.wait()
            # process_cmaps(l, f"{subdir}/state.top")
            # grompp_cmd = f"gmx grompp -maxwarn 1 -o {subdir}/state.tpr -c {gro_file} -f {mdp_file} -p {subdir}/state.top -quiet &> {subdir}/grompp.out &"
            # grompp_cmd = f"gmx -nocopyright -nobackup grompp -maxwarn 2 -o {subdir}/state{state+1:02d}.tpr -c {gro_file} -f {mdp_file} -p {subdir}/state{state+1:02d}.top &> {subdir}/grompp.out"
            grompp_cmd = f"gmx -nocopyright -nobackup grompp -maxwarn 2 -o {subdir}/state.tpr -c {gro_file} -f {mdp_file} -p {subdir}/state.top &> {subdir}/grompp.out"
            proc = subprocess.Popen(grompp_cmd, shell=True, executable="/bin/bash")
            proc.wait()
            return
            # return f'{benchmark}, state {state+1} prepared.'

        with ThreadPoolExecutor(max_workers=12) as executor:
            for result in executor.map(task, range(N_states), temps):
                pass
                # print(result)

        print(f"Made first REST2 benchmark in {benchmark}.")
    return name


def prepare_multidir(multidir):
    multidir_string = ""

    multidir_string = "-multidir"
    for i in range(multidir):
        multidir_string += " state" + f"{i+1:02d}"

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


def process_cmaps(lambda_value, file_path):
    lambda_value = float(lambda_value)
    cmaptypes = False
    pairtypes = False
    output_lines = []

    with open(file_path, 'r') as file:
        for line in file:
            if re.search(r'\[ ', line):
                cmaptypes = False
                pairtypes = False
            # if re.search(r'\[ pairtypes \]', line):
            #     pairtypes = True
            if re.search(r'\[ cmaptypes \]', line):
                cmaptypes = True

            # if pairtypes:
            #     line = re.sub(r';', '; ', line)
            #     output_lines.append(line)
            #     fields = line.split()
            #     if fields and fields[0] != ";" and fields[0] != "[" and len(fields) > 0:
            #         output_lines.append(f"{fields[0]}_\t{fields[1]}_\t{fields[2]}\t{float(fields[3]):.12f}  {float(fields[4]) * lambda_value:.12f}    ; scaled\n")
            # elif cmaptypes:
            if cmaptypes:
                line = re.sub(r'\\', '', line)
                fields = line.split()
                if len(fields) == 8:
                    output_lines.append(f"{fields[0]} {fields[1]} {fields[2]} {fields[3]} {fields[4]} {fields[5]} {fields[6]} {fields[7]}\\\n")
                elif len(fields) == 10:
                    output_lines.append(f"{float(fields[0]) * lambda_value:.9f} {float(fields[1]) * lambda_value:.9f} {float(fields[2]) * lambda_value:.9f} {float(fields[3]) * lambda_value:.9f} {float(fields[4]) * lambda_value:.9f} {float(fields[5]) * lambda_value:.9f} {float(fields[6]) * lambda_value:.9f} {float(fields[7]) * lambda_value:.9f} {float(fields[8]) * lambda_value:.9f} {float(fields[9]) * lambda_value:.9f}\\\n")
                elif len(fields) == 6:
                    output_lines.append(f"{float(fields[0]) * lambda_value:.9f} {float(fields[1]) * lambda_value:.9f} {float(fields[2]) * lambda_value:.9f} {float(fields[3]) * lambda_value:.9f} {float(fields[4]) * lambda_value:.9f} {float(fields[5]) * lambda_value:.9f}\n")
                else:
                    output_lines.append(line)
            else:
                output_lines.append(line)

    with open(file_path, 'w') as file:
        file.writelines(output_lines)
