lappend auto_path $env(PARFLOW_DIR)/bin
package require parflow
namespace import Parflow::*

pfset FileVersion 4


set filename5 "permeability.sa"
set filename6 "permeability.pfb"
puts $filename5
puts $filename6
set filepfb [pfload $filename5]
pfsave $filepfb -pfb $filename6

