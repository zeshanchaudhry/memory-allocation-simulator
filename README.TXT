1. Overview
This program simulates how an operating system allocates and frees memory using four different memory management algorithms:
    First Fit (FF)
    Next Fit (NF)
    Best Fit (BF)
    Worst Fit (WF)
The simulator runs for 12,000 time units, where the first 2,000 time units are a prefill phase, and the remaining 10,000 time 
units are the normal running phase. Jobs arrive randomly using the 3 +/- 2 rule, and each job requests memory for code, stack 
and many heap elements. Heap elements are allocated and freed throughout the job’s life, unless lost-object mode is turned on. 
The program tracks memory fragmentation, usage, heap behavior, lost objects, and counts every operation performed by malloc/free. 
This assignment compares how each algorithm behaves under different conditions.

2. How to Run the Program
You can run the program in any Python 3 environment. When the program starts, it will ask you for several inputs.

3. User Inputs
When prompted, enter the following inputs:
    Percentage of small jobs 
    Percentage of medium jobs 
    Percentage of large jobs 
        These percentage of jobs must total 100%.
    Memory unit size Must be a multiple of 8 (example: 8, 16, 24) 
    Total number of memory units 
    Test name 
        For example: test1 
    Base name for summary files 
        For example: summary_test1 
    Base name for log files 
        For example: log_test1 
    Lost objects mode (y/n) 
        choosing y means every 100th job of each type loses its heap frees 
        choosing n means no lost objects 
    At the end, the program will ask: Append final results to master summary file (master_summary.txt)? (y/n) 
        Choose y to automatically save the results for the comparison tables.

4. Output Files
The program creates multiple files for each test:
    summary files in the following format for each test:
        summary_<testname>_FF.txt
        summary_<testname>_NF.txt
        summary_<testname>_BF.txt
        summary_<testname>_WF.txt
        
        These files contain: 
        Prefill steady state metrics
        Time-based metrics printed every 20 time units 
        Final memory metrics 
        Extra memory metrics 
        Efficiency metrics

    Log Files will be printed in following format for each test:
        log_<testname>_FF.txt
        log_<testname>_NF.txt
        log_<testname>_BF.txt
        log_<testname>_WF.txt
        
        These log file have:
        Every memory allocation 
        Every heap event 
        I/O requests and completions
        Job arrivals 
        Job terminations
        Lost object events (if enabled)
    
    Master Summary File
        master_summary.txt
        If selected, this file collects one line per algorithm per test so we can easily build: 
        % memory in use tables 
        % internal fragmentation tables 
        % memory free tables 
        Lost objects tables 
        Operations tables

5. Running Multiple Tests
For this assignment, I ran a set of tests to compare how the algorithms behave under different conditions. These tests match the test plan I submitted in Part 2.
    test1_normal – normal memory (8-byte units, 10,000 units)
    test2_lowmem – small memory stress test (8-byte units, 4,000 units)
    test3_highmem – large memory system (8-byte units, 25,000 units)
    test4_lostmode – lost objects enabled (8-byte units, 10,000 units)
    test5_unit16 – memory unit size = 16 bytes
    test6_unit32 – memory unit size = 32 bytes
    test7_medheavy – medium-job heavy workload
    test8_largeheavy – large-job heavy workload
    test9_tinymem – extremely small memory (2,000 units)
Each test produces four summary files and four log files, one for each algorithm.

6. Notes and Assumptions 
    Heap element size is 35 +/- 15 bytes
    Job arrival times follow 3 +/- 2 rule
    Heap element lifetime is random between 1 and job completion
    Next Fit remembers the last scanned position
    All free lists merge adjacent spaces
    All memory sizes are tracked in memory units, not bytes
    Total simulation time = 12,000 time units
    
If something looks off like all memory filling too fast or something, you can rerun the test using the same parameters. The program overwrites old files
so you don’t need to delete them manually.