import random

# Helper functions
def round_up_units(bytes_needed, unit_size):
    """Convert bytes to memory units, rounding UP."""
    if bytes_needed <= 0:
        return 0
    if bytes_needed % unit_size == 0:
        return bytes_needed // unit_size
    else:
        return (bytes_needed // unit_size) + 1

def init_free_list(total_units):
    """Start with one big free block."""
    return [(0, total_units)]  # list of (start, length)

# malloc

def mallocFF(bytes_needed, unit_size, free_list, stats):
    """First Fit malloc. size is bytes, we allocate in units."""
    units_needed = round_up_units(bytes_needed, unit_size)
    if units_needed == 0:
        return -1

    stats["alloc_calls"] += 1

    for i in range(len(free_list)):
        stats["ops_malloc"] += 1  # looking at this block
        start, length = free_list[i]
        if length >= units_needed:
            # allocating here
            alloc_start = start
            new_length = length - units_needed
            if new_length > 0:
                free_list[i] = (start + units_needed, new_length)
            else:
                free_list.pop(i)
            return alloc_start

    stats["alloc_fail"] += 1
    return -1


def mallocNF(bytes_needed, unit_size, free_list, stats, last_index):
    """Next Fit malloc. We remember where we left off."""
    units_needed = round_up_units(bytes_needed, unit_size)
    if units_needed == 0:
        return -1, last_index

    stats["alloc_calls"] += 1

    n = len(free_list)
    if n == 0:
        stats["alloc_fail"] += 1
        return -1, last_index

    # scan starting at last_index and wrap around
    for j in range(n):
        i = (last_index + j) % n
        stats["ops_malloc"] += 1
        start, length = free_list[i]
        if length >= units_needed:
            alloc_start = start
            new_length = length - units_needed
            if new_length > 0:
                free_list[i] = (start + units_needed, new_length)
                return alloc_start, i
            else:
                free_list.pop(i)
                # adjusting last_index if needed
                if i < last_index and last_index > 0:
                    last_index -= 1
                return alloc_start, last_index

    stats["alloc_fail"] += 1
    return -1, last_index


def mallocBF(bytes_needed, unit_size, free_list, stats):
    """Best Fit malloc. Choose smallest block that fits."""
    units_needed = round_up_units(bytes_needed, unit_size)
    if units_needed == 0:
        return -1

    stats["alloc_calls"] += 1

    best_index = -1
    best_size = None

    for i, (start, length) in enumerate(free_list):
        stats["ops_malloc"] += 1
        if length >= units_needed:
            if best_size is None or length < best_size:
                best_size = length
                best_index = i

    if best_index == -1:
        stats["alloc_fail"] += 1
        return -1

    start, length = free_list[best_index]
    alloc_start = start
    leftover = length - units_needed

    if leftover > 0:
        free_list[best_index] = (start + units_needed, leftover)
    else:
        free_list.pop(best_index)

    return alloc_start


def mallocWF(bytes_needed, unit_size, free_list, stats):
    """Worst Fit malloc. Choose largest block that fits."""
    units_needed = round_up_units(bytes_needed, unit_size)
    if units_needed == 0:
        return -1

    stats["alloc_calls"] += 1

    worst_index = -1
    worst_size = -1

    for i, (start, length) in enumerate(free_list):
        stats["ops_malloc"] += 1
        if length >= units_needed and length > worst_size:
            worst_size = length
            worst_index = i

    if worst_index == -1:
        stats["alloc_fail"] += 1
        return -1

    start, length = free_list[worst_index]
    alloc_start = start
    leftover = length - units_needed

    if leftover > 0:
        free_list[worst_index] = (start + units_needed, leftover)
    else:
        free_list.pop(worst_index)

    return alloc_start


def free_block(start, units, free_list, stats):
    """Free a block of memory and merge neighbors."""
    if start < 0 or units <= 0:
        return

    stats["free_calls"] += 1

    # add new free block
    free_list.append((start, units))
    # sort by start
    free_list.sort(key=lambda x: x[0])

    # merge neighbors
    merged = []
    for blk in free_list:
        stats["ops_free"] += 1
        if not merged:
            merged.append(blk)
        else:
            last_start, last_len = merged[-1]
            cur_start, cur_len = blk
            if last_start + last_len == cur_start:
                merged[-1] = (last_start, last_len + cur_len)
            else:
                merged.append(blk)
    free_list[:] = merged


# Job representation
class Job:
    def __init__(self, jid, jtype, run_time, code_bytes, stack_bytes,
                 heap_total, start_time, is_lost):
        self.id = jid
        self.type = jtype
        self.run_total = run_time
        self.run_left = run_time
        self.code_bytes = code_bytes
        self.stack_bytes = stack_bytes
        self.heap_total = heap_total  # total heap elements this job will allocate
        self.heap_left = heap_total
        self.start_time = start_time
        self.code_loc = -1
        self.stack_loc = -1
        # list of heap blocks allocated: dicts with loc, units, death time, bytes
        self.heap_blocks = []
        self.is_lost = is_lost

    def heap_per_tick(self):
        """How many heap elements this job should allocate each time unit."""
        if self.run_total <= 0:
            return 0
        per_tick = self.heap_total // self.run_total
        if per_tick <= 0:
            per_tick = 1
        return per_tick
# Metrics helper
def compute_memory_metrics(total_units, unit_size, allocated_units,
                           required_bytes_sum, free_list,
                           heap_alloc_count, heap_bytes_sum,
                           lost_count, lost_bytes,
                           max_allocated_units):
    total_bytes = total_units * unit_size
    used_bytes = allocated_units * unit_size
    free_bytes = total_bytes - used_bytes

    # internal fragmentation
    internal_frag_bytes = max(0, used_bytes - required_bytes_sum)
    if used_bytes > 0:
        internal_frag_percent = (internal_frag_bytes / used_bytes) * 100.0
    else:
        internal_frag_percent = 0.0

    if total_bytes > 0:
        mem_used_percent = (used_bytes / total_bytes) * 100.0
        mem_free_percent = (free_bytes / total_bytes) * 100.0
        lost_percent = (lost_bytes / total_bytes) * 100.0
        peak_used_percent = (max_allocated_units * unit_size / total_bytes) * 100.0
    else:
        mem_used_percent = 0.0
        mem_free_percent = 0.0
        lost_percent = 0.0
        peak_used_percent = 0.0

    # external fragmentation
    num_free_areas = len(free_list)
    if num_free_areas > 0:
        sizes = [length for (start, length) in free_list]
        largest = max(sizes)
        smallest = min(sizes)
        avg_free_size = sum(sizes) / len(sizes)
    else:
        largest = 0
        smallest = 0
        avg_free_size = 0

    metrics = {
        "total_bytes": total_bytes,
        "used_bytes": used_bytes,
        "free_bytes": free_bytes,
        "mem_used_percent": mem_used_percent,
        "mem_free_percent": mem_free_percent,
        "internal_frag_bytes": internal_frag_bytes,
        "internal_frag_percent": internal_frag_percent,
        "num_free_areas": num_free_areas,
        "largest_free": largest,
        "smallest_free": smallest,
        "avg_free_size": avg_free_size,
        "heap_alloc_count": heap_alloc_count,
        "heap_bytes_sum": heap_bytes_sum,
        "lost_count": lost_count,
        "lost_bytes": lost_bytes,
        "lost_percent": lost_percent,
        "peak_used_percent": peak_used_percent
    }
    return metrics


# Simulation function
def simulate(algorithm_name, job_pcts, unit_size, total_units,
             test_name, summary_base, log_base, lost_mode):
    """
    Run the memory simulation for one algorithm.
    algorithm_name: "FF", "NF", "BF", or "WF"
    """

    # fixed seed for repeatable results per algorithm
    random.seed(10)

    small_pct, med_pct, large_pct = job_pcts

    sim_time = 0
    total_time = 12000
    prefill_time = 2000

    # output file names
    summary_file_name = summary_base + "_" + algorithm_name + ".txt"
    log_file_name = log_base + "_" + algorithm_name + ".txt"

    summary = open(summary_file_name, "w")
    log = open(log_file_name, "w")

    # header info
    summary.write("Test name: " + test_name + "\n")
    summary.write("Algorithm: " + algorithm_name + "\n")
    summary.write("Small %: " + str(small_pct) + "\n")
    summary.write("Medium %: " + str(med_pct) + "\n")
    summary.write("Large %: " + str(large_pct) + "\n")
    summary.write("Memory unit size: " + str(unit_size) + "\n")
    summary.write("Total units: " + str(total_units) + "\n")
    summary.write("Lost objects mode: " + lost_mode + "\n\n")

    # memory structure
    free_list = init_free_list(total_units)
    allocated_units = 0
    required_bytes_sum = 0

    # heap stats
    heap_alloc_count = 0
    heap_bytes_sum = 0

    # lost object stats
    lost_count = 0
    lost_bytes = 0

    # extra memory metrics
    max_allocated_units = 0
    alloc_fail_count = 0

    # operation counters
    stats = {
        "ops_malloc": 0,
        "ops_free": 0,
        "alloc_calls": 0,
        "free_calls": 0,
        "alloc_fail": 0
    }

    # job state
    ready_queue = []
    active_jobs = []  # all jobs currently in system
    cpu_idle = True
    current_job = None

    # I/O state
    io_queue = []
    io_idle = True
    io_job = None
    io_done_time = -1

    # job counting for lost objects
    job_type_counts = {"small": 0, "medium": 0, "large": 0}
    job_id_counter = 1

    # arrival time control (3 +/- 2 rule)
    base_arrival = 1
    next_arrival = base_arrival + random.randint(0, 4)

    # Next Fit pointer
    next_fit_index = 0

    # metrics per algorithm to return later
    result_summary = {
        "small_jobs": 0,
        "medium_jobs": 0,
        "large_jobs": 0
    }

    # main simulation loop
    while sim_time < total_time:
        # Phase info
        if sim_time == 0:
            log.write("time 0: Prefill Phase begins\n")
        if sim_time == prefill_time:
            log.write(f"time {sim_time}: Main Simulation Phase begins\n")

        # Job arrivals
        if sim_time >= next_arrival:
            # schedule next arrival time
            base_arrival += 3
            next_arrival = base_arrival + random.randint(0, 4)

            # decide job type based on percentages
            r = random.randint(1, 100)
            if r <= small_pct:
                jtype = "small"
                run_time = 5 + random.randint(-1, 1)
                code_size = 60 + random.randint(-20, 20)
                stack_size = 30 + random.randint(-10, 10)
                heap_total = run_time * 50
            elif r <= small_pct + med_pct:
                jtype = "medium"
                run_time = 10 + random.randint(-1, 1)
                code_size = 90 + random.randint(-30, 30)
                stack_size = 60 + random.randint(-20, 20)
                heap_total = run_time * 100
            else:
                jtype = "large"
                run_time = 25 + random.randint(-1, 1)
                code_size = 170 + random.randint(-50, 50)
                stack_size = 90 + random.randint(-30, 30)
                heap_total = run_time * 250

            # make sure values are at least 1
            if run_time < 1:
                run_time = 1
            if code_size < 1:
                code_size = 1
            if stack_size < 1:
                stack_size = 1

            job_type_counts[jtype] += 1
            result_summary[jtype + "_jobs"] = job_type_counts[jtype]

            # decide lost-object job
            is_lost = False
            if lost_mode.lower() == "y":
                if job_type_counts[jtype] % 100 == 0:
                    is_lost = True

            job = Job(job_id_counter, jtype, run_time,
                      code_size, stack_size, heap_total,
                      sim_time, is_lost)

            # allocate code and stack memory
            if algorithm_name == "FF":
                code_loc = mallocFF(code_size, unit_size, free_list, stats)
                stack_loc = mallocFF(stack_size, unit_size, free_list, stats)
            elif algorithm_name == "NF":
                code_loc, next_fit_index = mallocNF(code_size, unit_size, free_list,
                                                    stats, next_fit_index)
                stack_loc, next_fit_index = mallocNF(stack_size, unit_size, free_list,
                                                     stats, next_fit_index)
            elif algorithm_name == "BF":
                code_loc = mallocBF(code_size, unit_size, free_list, stats)
                stack_loc = mallocBF(stack_size, unit_size, free_list, stats)
            else:
                code_loc = mallocWF(code_size, unit_size, free_list, stats)
                stack_loc = mallocWF(stack_size, unit_size, free_list, stats)

            if code_loc != -1 and stack_loc != -1:
                # successful job allocation
                job.code_loc = code_loc
                job.stack_loc = stack_loc

                code_units = round_up_units(code_size, unit_size)
                stack_units = round_up_units(stack_size, unit_size)
                allocated_units += (code_units + stack_units)

                # required bytes for this job's code + stack
                required_bytes_sum += (code_size + stack_size)

                if allocated_units > max_allocated_units:
                    max_allocated_units = allocated_units

                log.write(f"time {sim_time}: job {job.id} ARRIVE type={job.type} "
                          f"code_loc={code_loc} stack_loc={stack_loc}\n")

                ready_queue.append(job)
                active_jobs.append(job)
                job_id_counter += 1
            else:
                # failed to allocate job
                alloc_fail_count += 1
                log.write(f"time {sim_time}: job {job_id_counter} REJECTED (not enough memory)\n")

        # Heap deallocation (lifetime expired)
        for job in list(active_jobs):  # copy for safe modification
            new_blocks = []
            for blk in job.heap_blocks:
                if sim_time >= blk["death"]:
                    # time to free or lose
                    if not job.is_lost:
                        free_block(blk["loc"], blk["units"], free_list, stats)
                        allocated_units -= blk["units"]
                        # this heap block is no longer required
                        required_bytes_sum -= blk["bytes"]
                        if required_bytes_sum < 0:
                            required_bytes_sum = 0
                        log.write(f"time {sim_time}: job {job.id} HEAP_FREE "
                                  f"loc={blk['loc']} units={blk['units']}\n")
                    else:
                        # lost object
                        lost_count += 1
                        lost_bytes += blk["bytes"]
                else:
                    new_blocks.append(blk)
            job.heap_blocks = new_blocks

        # I/O completion
        if (not io_idle) and sim_time >= io_done_time:
            # I/O finished for current io_job
            ready_queue.append(io_job)
            log.write(f"time {sim_time}: job {io_job.id} IO_DONE\n")
            io_job = None
            io_idle = True

        # Start new I/O if device idle
        if io_idle and io_queue:
            io_job = io_queue.pop(0)
            io_idle = False
            # simple I/O duration: 1 to 3 time units
            io_done_time = sim_time + random.randint(1, 3)
            log.write(f"time {sim_time}: job {io_job.id} IO_START\n")

        # CPU dispatch
        if (current_job is None) and ready_queue:
            current_job = ready_queue.pop(0)
            cpu_idle = False
            log.write(f"time {sim_time}: job {current_job.id} DISPATCH\n")

        finished_jobs = []

        # Job execution + possible I/O request + heap alloc
        if current_job is not None:
            # simulate a chance this job requests I/O (only if it has time left)
            if current_job.run_left > 1:
                # small probability to do I/O during this tick
                if random.random() < 0.05:
                    log.write(f"time {sim_time}: job {current_job.id} IO_REQUEST\n")
                    io_queue.append(current_job)
                    current_job = None
                    cpu_idle = True
                else:
                    # normal CPU work with heap allocations
                    per_tick = current_job.heap_per_tick()
                    for k in range(per_tick):
                        if current_job.heap_left <= 0:
                            break

                        # heap element size (35 +/- 15 bytes)
                        heap_size = 35 + random.randint(-15, 15)
                        if heap_size < 1:
                            heap_size = 1

                        # lifetime between 1 and remaining run time
                        if current_job.run_left > 0:
                            life = random.randint(1, current_job.run_left)
                        else:
                            life = 1
                        death_time = sim_time + life

                        # allocate heap memory
                        if algorithm_name == "FF":
                            loc = mallocFF(heap_size, unit_size, free_list, stats)
                        elif algorithm_name == "NF":
                            loc, next_fit_index = mallocNF(heap_size, unit_size, free_list,
                                                           stats, next_fit_index)
                        elif algorithm_name == "BF":
                            loc = mallocBF(heap_size, unit_size, free_list, stats)
                        else:
                            loc = mallocWF(heap_size, unit_size, free_list, stats)

                        if loc != -1:
                            units = round_up_units(heap_size, unit_size)
                            current_job.heap_blocks.append({
                                "loc": loc,
                                "units": units,
                                "death": death_time,
                                "bytes": heap_size
                            })
                            allocated_units += units
                            required_bytes_sum += heap_size
                            heap_alloc_count += 1
                            heap_bytes_sum += heap_size
                            if allocated_units > max_allocated_units:
                                max_allocated_units = allocated_units
                            log.write(f"time {sim_time}: job {current_job.id} HEAP_ALLOC "
                                      f"loc={loc} units={units}\n")
                            current_job.heap_left -= 1
                        else:
                            # failed heap alloc
                            alloc_fail_count += 1

                    # run one unit of CPU time
                    current_job.run_left -= 1
            else:

                # last time unit: just run, no new I/O or heap alloc
                current_job.run_left -= 1

            # check for job completion
            if current_job is not None and current_job.run_left <= 0:
                code_units = round_up_units(current_job.code_bytes, unit_size)
                stack_units = round_up_units(current_job.stack_bytes, unit_size)

                # free stack and code
                free_block(current_job.stack_loc, stack_units, free_list, stats)
                free_block(current_job.code_loc, code_units, free_list, stats)
                allocated_units -= (code_units + stack_units)

                # their code+stack are no longer required
                required_bytes_sum -= (current_job.code_bytes + current_job.stack_bytes)
                if required_bytes_sum < 0:
                    required_bytes_sum = 0

                # free remaining heap, unless lost job
                if not current_job.is_lost:
                    for blk in current_job.heap_blocks:
                        free_block(blk["loc"], blk["units"], free_list, stats)
                        allocated_units -= blk["units"]
                        required_bytes_sum -= blk["bytes"]
                        if required_bytes_sum < 0:
                            required_bytes_sum = 0
                        log.write(f"time {sim_time}: job {current_job.id} HEAP_FREE "
                                  f"loc={blk['loc']} units={blk['units']}\n")
                else:
                    for blk in current_job.heap_blocks:
                        lost_count += 1
                        lost_bytes += blk["bytes"]

                log.write(f"time {sim_time}: job {current_job.id} FINISH\n")

                finished_jobs.append(current_job)
                current_job = None
                cpu_idle = True

        # remove finished jobs from active list
        for fj in finished_jobs:
            if fj in active_jobs:
                active_jobs.remove(fj)

        # Metrics output
        if sim_time == prefill_time:
            # print prefill steady-state metrics once
            metrics = compute_memory_metrics(
                total_units, unit_size, allocated_units,
                required_bytes_sum, free_list,
                heap_alloc_count, heap_bytes_sum,
                lost_count, lost_bytes,
                max_allocated_units
            )
            summary.write(" PREFILL STEADY STATE METRICS (time 2000)\n")
            summary.write(f"% memory in use: {metrics['mem_used_percent']:.2f}\n")
            summary.write(f"% memory free: {metrics['mem_free_percent']:.2f}\n")
            summary.write(f"internal frag bytes: {metrics['internal_frag_bytes']}\n")
            summary.write(f"% internal frag: {metrics['internal_frag_percent']:.2f}\n")
            summary.write(f"external frag (free areas): {metrics['num_free_areas']}\n")
            summary.write(f"largest free block (units): {metrics['largest_free']}\n")
            summary.write(f"smallest free block (units): {metrics['smallest_free']}\n")
            summary.write(f"avg free block size (units): {metrics['avg_free_size']:.2f}\n")
            summary.write(f"heap allocations so far: {metrics['heap_alloc_count']}\n")
            summary.write(f"lost objects so far: {metrics['lost_count']}\n")
            summary.write(f"% memory of lost objects: {metrics['lost_percent']:.2f}\n\n")

        if sim_time >= prefill_time and sim_time % 20 == 0:
            metrics = compute_memory_metrics(
                total_units, unit_size, allocated_units,
                required_bytes_sum, free_list,
                heap_alloc_count, heap_bytes_sum,
                lost_count, lost_bytes,
                max_allocated_units
            )
            summary.write("time " + str(sim_time) + ":\n")
            summary.write(f"  total memory bytes: {metrics['total_bytes']}\n")
            summary.write(f"  used bytes: {metrics['used_bytes']}\n")
            summary.write(f"  free bytes: {metrics['free_bytes']}\n")
            summary.write(f"  % memory in use: {metrics['mem_used_percent']:.2f}\n")
            summary.write(f"  % memory free: {metrics['mem_free_percent']:.2f}\n")
            summary.write(f"  required bytes: {required_bytes_sum}\n")
            summary.write(f"  internal frag bytes: {metrics['internal_frag_bytes']}\n")
            summary.write(f"  % internal frag: {metrics['internal_frag_percent']:.2f}\n")
            summary.write(f"  external frag (free areas): {metrics['num_free_areas']}\n")
            summary.write(f"  largest free block (units): {metrics['largest_free']}\n")
            summary.write(f"  smallest free block (units): {metrics['smallest_free']}\n")
            summary.write(f"  avg free block size (units): {metrics['avg_free_size']:.2f}\n")
            summary.write(f"  heap allocations: {metrics['heap_alloc_count']}\n")
            summary.write(f"  total heap bytes: {metrics['heap_bytes_sum']}\n")
            summary.write(f"  lost objects: {metrics['lost_count']}\n")
            summary.write(f"  lost bytes: {metrics['lost_bytes']}\n")
            summary.write(f"  % memory of lost objects: {metrics['lost_percent']:.2f}\n")
            summary.write("\n")

        # advance simulation time
        sim_time += 1

    # End of simulation: final metrics
    metrics = compute_memory_metrics(
        total_units, unit_size, allocated_units,
        required_bytes_sum, free_list,
        heap_alloc_count, heap_bytes_sum,
        lost_count, lost_bytes,
        max_allocated_units
    )

    summary.write("\n FINAL METRICS\n")
    summary.write(f"Total memory bytes: {metrics['total_bytes']}\n")
    summary.write(f"Max allocated units: {max_allocated_units}\n")
    summary.write(f"Allocation failures: {alloc_fail_count}\n")
    summary.write(f"% memory in use: {metrics['mem_used_percent']:.2f}\n")
    summary.write(f"% memory free: {metrics['mem_free_percent']:.2f}\n")
    summary.write(f"Required bytes total (current): {required_bytes_sum}\n")
    summary.write(f"Internal frag bytes: {metrics['internal_frag_bytes']}\n")
    summary.write(f"% internal frag: {metrics['internal_frag_percent']:.2f}\n")
    summary.write(f"External frag free areas: {metrics['num_free_areas']}\n")
    summary.write(f"Largest free block (units): {metrics['largest_free']}\n")
    summary.write(f"Smallest free block (units): {metrics['smallest_free']}\n")
    summary.write(f"Avg free block size (units): {metrics['avg_free_size']:.2f}\n")
    summary.write(f"Heap allocations: {heap_alloc_count}\n")
    summary.write(f"Total heap bytes: {heap_bytes_sum}\n")
    summary.write(f"Lost objects: {lost_count}\n")
    summary.write(f"Lost bytes: {lost_bytes}\n")
    summary.write(f"% memory of lost objects: {metrics['lost_percent']:.2f}\n\n")

    # extra memory metrics (4 of my choosing)
    summary.write(" EXTRA MEMORY METRICS\n")
    summary.write(f"Max allocated units at any time: {max_allocated_units}\n")
    summary.write(f"Peak % memory in use: {metrics['peak_used_percent']:.2f}\n")
    summary.write(f"Average free block size (final): {metrics['avg_free_size']:.2f}\n")
    summary.write(f"Total allocation failures: {alloc_fail_count}\n\n")

    # efficiency metrics
    summary.write(" EFFICIENCY METRICS\n")
    summary.write(f"Number of allocation calls: {stats['alloc_calls']}\n")
    summary.write(f"Number of free calls: {stats['free_calls']}\n")
    summary.write(f"Malloc operations: {stats['ops_malloc']}\n")
    summary.write(f"Free operations: {stats['ops_free']}\n")

    if stats["alloc_calls"] > 0:
        avg_ops_alloc = stats["ops_malloc"] / stats["alloc_calls"]
    else:
        avg_ops_alloc = 0.0

    if stats["free_calls"] > 0:
        avg_ops_free = stats["ops_free"] / stats["free_calls"]
    else:
        avg_ops_free = 0.0

    summary.write(f"Average operations per allocation: {avg_ops_alloc:.2f}\n")
    summary.write(f"Average operations per free: {avg_ops_free:.2f}\n")
    total_ops = stats["ops_malloc"] + stats["ops_free"]
    summary.write(f"Total allocation+free operations: {total_ops}\n")

    summary.close()
    log.write("simulation complete\n")
    log.close()

    # store some final numbers in result_summary for comparison table
    result_summary["total_bytes"] = metrics["total_bytes"]
    result_summary["used_bytes"] = metrics["used_bytes"]
    result_summary["required_bytes"] = required_bytes_sum
    result_summary["mem_used_percent"] = metrics["mem_used_percent"]
    result_summary["internal_frag_percent"] = metrics["internal_frag_percent"]
    result_summary["mem_free_percent"] = metrics["mem_free_percent"]
    result_summary["num_free_areas"] = metrics["num_free_areas"]
    result_summary["largest_free"] = metrics["largest_free"]
    result_summary["smallest_free"] = metrics["smallest_free"]
    result_summary["heap_allocations"] = heap_alloc_count
    result_summary["heap_bytes"] = heap_bytes_sum
    result_summary["lost_objects"] = lost_count
    result_summary["lost_bytes"] = lost_bytes
    result_summary["lost_percent"] = metrics["lost_percent"]
    result_summary["alloc_calls"] = stats["alloc_calls"]
    result_summary["ops_malloc"] = stats["ops_malloc"]
    result_summary["avg_ops_alloc"] = avg_ops_alloc
    result_summary["free_calls"] = stats["free_calls"]
    result_summary["ops_free"] = stats["ops_free"]
    result_summary["avg_ops_free"] = avg_ops_free
    result_summary["max_allocated_units"] = max_allocated_units
    result_summary["peak_used_percent"] = metrics["peak_used_percent"]
    result_summary["alloc_failures"] = alloc_fail_count
    result_summary["avg_free_block"] = metrics["avg_free_size"]

    print(f"Finished simulation for {algorithm_name}. "
          f"Summary in {summary_file_name}, log in {log_file_name}")

    return result_summary


# Print final comparison table
def print_final_table(test_name, results):
    algs = ["FF", "NF", "BF", "WF"]
    print()
    print("                  FINAL METRICS SUMMARY TABLE")
    print("                  Test Name:", test_name)
    print("---------------------------------------------------------------")

    def get(alg, key):
        return results[alg].get(key, 0)

    print(f"{'Metric':<30} {'FF':>12} {'NF':>12} {'BF':>12} {'WF':>12}")
    print("-" * 84)

    # Helper for formatted row
    def row(name, key, fmt="{}"):
        print(f"{name:<30} "
            f"{fmt.format(get('FF', key)):>12} "
            f"{fmt.format(get('NF', key)):>12} "
            f"{fmt.format(get('BF', key)):>12} "
            f"{fmt.format(get('WF', key)):>12}"
        )

    row("Small jobs", "small_jobs")
    row("Medium jobs", "medium_jobs")
    row("Large jobs", "large_jobs")
    print()

    row("Total memory (bytes)", "total_bytes")
    row("Used memory (bytes)", "used_bytes")
    row("% memory in use", "mem_used_percent", "{:.2f}")
    row("Required bytes", "required_bytes")
    row("% internal frag", "internal_frag_percent", "{:.2f}")
    row("% memory free", "mem_free_percent", "{:.2f}")
    row("Free areas", "num_free_areas")
    row("Largest free block", "largest_free")
    row("Smallest free block", "smallest_free")
    print()

    row("Heap allocations", "heap_allocations")
    row("Heap bytes", "heap_bytes")
    row("Lost objects", "lost_objects")
    row("Lost bytes", "lost_bytes")
    row("% lost memory", "lost_percent", "{:.2f}")
    print()

    row("Alloc requests", "alloc_calls")
    row("Alloc operations", "ops_malloc")
    row("Avg ops per alloc", "avg_ops_alloc", "{:.2f}")
    row("Free requests", "free_calls")
    row("Free operations", "ops_free")
    row("Avg ops per free", "avg_ops_free", "{:.2f}")
    print("-" * 84)



# Main
def main():
    print(" Memory Simulation Program - Program 2 ")

    # user parameters
    small = int(input("Enter % small jobs: "))
    medium = int(input("Enter % medium jobs: "))
    large = int(input("Enter % large jobs: "))

    if small + medium + large != 100:
        print("Error: percentages must add to 100")
        return

    unit_size = int(input("Enter memory unit size (must be multiple of 8): "))
    if unit_size % 8 != 0:
        print("Warning: unit size is not a multiple of 8 (assignment says it should be).")

    total_units = int(input("Enter total number of memory units: "))
    test_name = input("Enter test name: ")
    summary_base = input("Enter base name for summary files: ")
    log_base = input("Enter base name for log files: ")
    lost_mode = input("Lost objects mode (y/n): ")

    job_pcts = (small, medium, large)

    # run 4 algorithms and store results
    results = {}
    results["FF"] = simulate("FF", job_pcts, unit_size, total_units,
                             test_name, summary_base, log_base, lost_mode)
    results["NF"] = simulate("NF", job_pcts, unit_size, total_units,
                             test_name, summary_base, log_base, lost_mode)
    results["BF"] = simulate("BF", job_pcts, unit_size, total_units,
                             test_name, summary_base, log_base, lost_mode)
    results["WF"] = simulate("WF", job_pcts, unit_size, total_units,
                             test_name, summary_base, log_base, lost_mode)

    # print final comparison table to screen
    print_final_table(test_name, results)

    # optional master summary file for all tests
    choice = input("Append final results to master summary file (master_summary.txt)? (y/n): ")
    if choice.lower() == "y":
        with open("master_summary.txt", "a") as f:
            for alg in ["FF", "NF", "BF", "WF"]:
                r = results[alg]
                f.write(
                    f"{test_name}\t{alg}\t"
                    f"{r['mem_used_percent']:.2f}\t"
                    f"{r['internal_frag_percent']:.2f}\t"
                    f"{r['mem_free_percent']:.2f}\t"
                    f"{r['lost_percent']:.2f}\t"
                    f"{r['heap_allocations']}\t"
                    f"{r['alloc_calls']}\t"
                    f"{r['ops_malloc']}\t"
                    f"{r['free_calls']}\t"
                    f"{r['ops_free']}\n"
                )
        print("Results appended to master_summary.txt")


if __name__ == "__main__":
    main()
