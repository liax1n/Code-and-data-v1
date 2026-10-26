#-----------------------------------------------------------------------------
#Calculate Flow using Mannings equation on USGS stations
## units = m3/s
#-----------------------------------------------------------------------------

# Import the ParFlow TCL package
lappend   auto_path $env(PARFLOW_DIR)/bin
package   require parflow
namespace import Parflow::*

pfset     FileVersion    4

pfset Process.Topology.P 11
pfset Process.Topology.Q 5
pfset Process.Topology.R 1

#-----------------------------------------------------------------------------
# Computational Grid
#-----------------------------------------------------------------------------
pfset ComputationalGrid.Lower.X           0.0
pfset ComputationalGrid.Lower.Y           0.0
pfset ComputationalGrid.Lower.Z           0.0

pfset ComputationalGrid.NX                330
pfset ComputationalGrid.NY                200
pfset ComputationalGrid.NZ                10

pfset ComputationalGrid.DX                1000.0
pfset ComputationalGrid.DY                1000.0
pfset ComputationalGrid.DZ                1.0

set dx                                    1000.0
set dy                                    1000.0
set dz                                    1.0

# Manning coefficient ——s m^(-1/3)
array set station_n {
    GJB  0.018
    HJM  0.020
    HS    0.033
    DS    0.030
    SM   0.025
    ZSY  0.028
}

set station_name "SM"

# transform from s m^(-1/3) to hr m^(-1/3)
set n_hour [expr {$station_n($station_name) / 3600.0}]

#-----------------------------------------------------------------------------
# Runname Directory and timing
#-----------------------------------------------------------------------------
set timesteps  8760
set runname        "mao"
cd "./run_1"        #run_1 folder is the output folder of run.py

# Read in all of the general files
set mask                [pfload $runname.out.mask.pfb]
set top                 [pfcomputetop $mask]
set sx                  [pfload slopex.pfb]
set sy                  [pfload slopey.pfb]
set manning             [pfload mannings.pfb]

# Create output directory if it doesn't exist
set output_dir "../2_q_outputs/1shenmu"
if {![file exists $output_dir]} {
    file mkdir $output_dir
    puts stdout "Created output directory: $output_dir"
}

# Define the points to calculate (X, Y coordinates)
set points [list \
    [list 317 141] \
]

puts stdout "Pre-calculating slopes and opening output files..."
array unset slope
array unset output

foreach point $points {
    set Xloca [lindex $point 0]
    set Yloca [lindex $point 1]
    
    set sx1 [pfgetelt $sx $Xloca $Yloca 0]
    set sy1 [pfgetelt $sy $Xloca $Yloca 0]
    set S [expr ($sx1**2+$sy1**2)**0.5]
    set slope($Xloca,$Yloca) $S
    puts stdout "Slope at $Xloca $Yloca = $S"
    
    set filename "$output_dir/${Xloca}_${Yloca}.txt"
    set output($Xloca,$Yloca) [open $filename w]
    puts $output($Xloca,$Yloca) "Time\t  Pressure(m)\t  Flow(cms)\t"
}

# read every timesteps
puts stdout "Starting time series processing..."
for {set ii 0} {$ii <= $timesteps} {incr ii} {
    
    set press [pfload [format $runname.out.press.%05d.pfb $ii]]
    set satin [format $runname.out.satur.%05d.pfb $ii]
    set satur [pfload $satin]
    
    # print
    if {$ii % 100 == 0} {
        puts stdout "Processing time step $ii of $timesteps"
        puts stdout "  Reading: $runname.out.press.[format %05d $ii].pfb"
    }
    
    foreach point $points {
        set Xloca [lindex $point 0]
        set Yloca [lindex $point 1]
        
        # press (lay9 is on the top)
        set P [pfgetelt $press $Xloca $Yloca 9]
        
        # slope
        set S $slope($Xloca,$Yloca)
        
        # Calculate the flow ($dx/6.0$ more closely approximates the actual river width based on cross-sectional measurements reported in the China Hydrological Yearbook.)
        if {$P >= 0} {
            if {$ii % 1000 == 0} {
                puts stdout "Top Pressure = $P at time $ii for point ($Xloca, $Yloca)"
            }
            set QT [expr {(1.0/$n_hour)*($dx/6.0)*($S**0.5)*($P**(5.0/3.0))/3600.0}]
        } else {
            set P 0
            set QT 0
        }
        
        # output
        puts $output($Xloca,$Yloca) "$ii\t $P\t $QT\t"
    }
    
    # Clean up
    pfdelete $press
    unset press
    pfdelete $satur
    unset satur
}

# close
puts stdout "Closing output files..."
foreach point $points {
    set Xloca [lindex $point 0]
    set Yloca [lindex $point 1]
    close $output($Xloca,$Yloca)
    puts stdout "Finished processing point ($Xloca, $Yloca)"
}

cd "../"
puts stdout "All processing complete!"