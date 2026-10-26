#!/bin/bash
#SBATCH -p deimos
#SBATCH -N 1
#SBATCH -n 64

#=================================
export LD_LIBRARY_PATH=$PARFLOW_DIR/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$TCL_DIR/lib:$LD_LIBRARY_PATH
export PATH=$PARFLOW_DIR/bin:$PATH
export PATH=$TCL_DIR/bin:$PATH
export PATH=$PATH:/usr/bin
#=================================
export GLEX_USE_ZC_RNDV=0
alias tclsh=/HOME/bnu_xfyang/bnu_xfyangxy_1/parflow/softwares/tcl/bin/tclsh8.6

tclsh8.6 sa2pfb.tcl