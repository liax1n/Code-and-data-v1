#!/bin/bash
#SBATCH -p deimos
#SBATCH -N 1
#SBATCH -n 55

module load python/python3/3.9.7 
#module load mpi/mpich/4.1.2-icc-oneapi2023.2-ch3-shared
#=================================
export PYTHON_DIR=/APP/u22/x86/python/3.9.7
export LD_LIBRARY_PATH=$PARFLOW_DIR/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$TCL_DIR/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$PYTHON_DIR/lib:$LD_LIBRARY_PATH
export PATH=$PARFLOW_DIR/bin:$PATH
export PATH=$TCL_DIR/bin:$PATH
export PATH=$PATH:/usr/bin
export PATH=$PYTHON_DIR/bin:$PATH
#=================================
export GLEX_USE_ZC_RNDV=0
alias python=/APP/u22/x86/python/3.9.7/bin/python

tclsh8.6 1shenmu_new.tcl
tclsh8.6 2gaojiabao_new.tcl
tclsh8.6 3zhaoshiyao_new.tcl
tclsh8.6 4hanjiamao_new.tcl
tclsh8.6 5hengshan_new.tcl
tclsh8.6 6dianshi_new.tcl
python hour2day_new.py