The table below draws the comparison between the different compression formats namely [ 'tar', 'bztar', 'gztar', 'xztar', 'zip'] for the files ['biotestmine', 'postgress', 'solr'] on the basis time taken to compress and the size after compression. 
The timing function used to calculate the time taken by each of the compression formats was from a Python defined module, “time” which allows us to handle various operations regarding time, its conversions and representations. The start and end of the compression process were marked and the difference was reported as the time taken for the same. 
The values presented in the table are subject to changes depending on the CPU model of the machine being used to carry out this process. This study was conducted on a machine equipped with I7 7700hq. More details are given at the bottom of the table.


Comparsion for the compression formats:


|     **File**    	| **Format** 	| **Time taken to compress(s)** 	| **Size after compression(MB)** 	|
|:---------------:	|:----------:	|:-----------------------------:	|:------------------------------:	|
| **biotestmine** 	|     tar    	|             1.069             	|               231              	|
| **biotestmine** 	|    bztar   	|             9.329             	|               201              	|
| **biotestmine** 	|    gztar   	|             3.463             	|               202              	|
| **biotestmine** 	|    xztar   	|             19.930            	|               196              	|
| **biotestmine** 	|     zip    	|              3.79             	|               204              	|
|                 	|            	|                               	|                                	|
|   **postgres**  	|     tar    	|             1.497             	|               567              	|
|   **postgres**  	|    bztar   	|             2.101             	|               77               	|
|   **postgres**  	|    gztar   	|             5.733             	|               96               	|
|   **postgres**  	|    xztar   	|             7.962             	|               50               	|
|   **postgres**  	|     zip    	|             2.703             	|               98               	|
|                 	|            	|                               	|                                	|
|     **solr**    	|     tar    	|             0.0255            	|               59               	|
|     **solr**    	|    bztar   	|             0.0788            	|               9.8              	|
|     **solr**    	|    gztar   	|             0.074             	|               12               	|
|     **solr**    	|    xztar   	|             0.112             	|               8.0              	|
|     **solr**    	|     zip    	|             0.177             	|               12               	|
|                 	|            	|                               	|                                	|


More details about the CPU model:


Architecture: x86_64
CPU op-mode(s): 32-bit, 64-bit
Byte Order: Little Endian
CPU(s): 8
On-line CPU(s) list: 0-7
Thread(s) per core: 2
Core(s) per socket: 4
Socket(s): 1
NUMA node(s): 1
Vendor ID: GenuineIntel
CPU family: 6
Model: 158
Model name: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz
Stepping: 9
CPU MHz: 800.038
CPU max MHz: 3800.0000
CPU min MHz: 800.0000
BogoMIPS: 5599.85
Virtualization: VT-x
L1d cache: 32K
L1i cache: 32K
L2 cache: 256K
L3 cache: 6144K
NUMA node0 CPU(s): 0-7
Flags: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc art arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm 3dnowprefetch cpuid_fault epb invpcid_single pti ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid ept_ad fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid mpx rdseed adx smap clflushopt intel_pt xsaveopt xsavec xgetbv1 xsaves dtherm ida arat pln pts hwp hwp_notify hwp_act_window hwp_epp md_clear flush_l1d
