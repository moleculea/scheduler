# -*- coding: utf-8  -*-
import collections
import decimal
import itertools
import copy
from operator import attrgetter
import utilities

class PlannedProcess(object):
    """
    PlannedProcess: a single process with planned CPU, I/O and Arrival Time
    """
    def __init__(self, proc_id=-1):
        self.__proc_id = proc_id
        self.__cpu_time = -1
        self.__io_time = -1
        self.__arr_time = -1
    
    @property
    def proc_id(self):
        return self.__proc_id
    
    @proc_id.setter
    def proc_id(self, value):
        self.__proc_id = value
    
    @property
    def cpu_time(self):
        return self.__cpu_time
    
    @cpu_time.setter
    def cpu_time(self, value):
        self.__cpu_time = value
           
    @property
    def io_time(self):
        return self.__io_time
    
    @io_time.setter
    def io_time(self, value):
        self.__io_time = value  
    
    @property
    def arr_time(self):
        return self.__arr_time
    
    @arr_time.setter
    def arr_time(self, value):
        self.__arr_time = value     
    
    def __str__(self):
        return "Process ID: %d    CPU Time: %d    I/O Time: %d    Arrival Time: %d" % \
            (self.proc_id, self.cpu_time, self.io_time, self.arr_time)
        
class Process(PlannedProcess):
    """
    Process: a single process which is being scheduled and updated in each cycle clock
    """
    def __init__(self, proc_id=-1):
        super(Process, self).__init__(proc_id)
        self.__fin_time = -1  # cycle this process finished (last running cycle before it terminated)
        self.__first_half = 0
        self.__second_half = 0
        self.__total_cpu_time = 0
        self.__rem_cpu_time = 0
        self.__rem_io_time = 0
        self.__ready_time = -1  # the first cycle at which this process becomes 'Ready' 
        self.__state = None  #  current state (Running, Ready and Blocked)
        self.__consecutive = 0  # consecutive running cycles

    
    def propagate(self):
        """
        Propagate planned parameters (in base class) to current class
            * Called after planned parameters (cpu_time, io_time) are set
        """
        self.__first_half = utilities.roundup(self.cpu_time / 2.0)   # first half cycles of CPU time
        self.__second_half = utilities.roundup(self.cpu_time / 2.0)  # second half cycles of CPU time
        self.__total_cpu_time = self.__first_half + self.__second_half if not self.hasNoIO() else self.cpu_time # total CPU cycles (rounded up)
        self.__rem_cpu_time = self.__total_cpu_time  # remaining CPU cycles
        self.__rem_io_time = self.io_time
                   
    @property
    def state(self):
        return self.__state
    
    @property
    def fin_time(self):
        return self.__fin_time

    @property
    def rem_cpu_time(self):
        return self.__rem_cpu_time
    
    @property
    def ready_time(self):
        return self.__ready_time
    
    def isFirstHalf(self):
        """
        For processes that have I/O time
            Check whether this process is in still the first half of CPU cycles
        """
        passed_time = self.__total_cpu_time - self.__rem_cpu_time
        if passed_time < self.__first_half:
            return True
        else:
            return False
    
    def hasNoIO(self):
        """
        Check whether this process has no planned I/O time
        """
        if self.io_time == 0:
            return True
        else:
            return False
        
    def toBlocked(self):
        """
        For 'Running' process:
            Check whether this 'Running' process is to transit from 'Running' to 'Blocked' in the next cycle
            If this 'Running' process has finished its "First Half" and has full I/O time remained, it is to be 'Blocked'
        """
        if not self.isFirstHalf():
            if self.__rem_io_time == self.io_time:
                return True
        return False
    
    def toTerminate(self):
        """
        For 'Running' process
            Check whether this 'Running' process is to terminate (due to finishing CPU time) in the next cycle
        """
        return 0 == self.__rem_cpu_time
                      
    def isBlocked(self):
        """
        For 'Blocked' process
            Check whether this 'Blocked' process is still in 'Blocked' state (remaining I/O time still > 0)
        """
        if self.__rem_io_time > 0:
            return True
        else:
            return False
        
    def hasRunning(self, number):
        """
        For 'Running' process (For RR algorithm)
            Check whether this 'Running' process has already be running number of cycles (consecutive)
        """
        return number == self.__consecutive
               
    def running(self):
        """
        Running for one cycle
        """
        if self.__rem_cpu_time > 0:
            self.__rem_cpu_time -= 1
            self.__state = 'Running'
            self.__consecutive += 1
        else:
            utilities.output.error("Cannot run this process any more: CPU time exhausted.")
        return self
    
    def blocked(self):
        """
        Blocked for one cycle
        """
        if self.__rem_io_time > 0:
            self.__rem_io_time -= 1
            self.__state = 'Blocked'
            self.__consecutive = 0  # clear consecutive running
        else:
            utilities.output.error("Cannot block this process any more: I/O time exhausted.")
        return self
    
    def waiting(self, ready_time):
        """
        Waiting in the queue (Ready)
        """
        self.__state = 'Ready'
        self.__ready_time = ready_time  # the first cycle at which this process becomes 'Ready' (then push in queue)
        self.__consecutive = 0  # clear consecutive running
        return self
    
    def finish(self, fin_time):
        """
        Finish at fin_time (last 'Running' cycle)
        """
        self.__fin_time = fin_time
        
    def __str__(self):
        planned = super(Process, self).__str__()
        realtime = "State: %s    Remaining CPU Time: %d    Ready Time: %d    Finishing Time: %d" % \
            (self.state, self.rem_cpu_time, self.ready_time, self.fin_time)
        return planned + '\n' + realtime + '\n'
        
class Scheduler(object):
    """
    Scheduler: schedule a list Process objects
        To be extended by different algorithm scheduler classes
    """
    def __init__(self, proc_list):
        self._proc_list = proc_list
        self._arrivals = collections.OrderedDict()  # ordered dictionary mapping arrival time to a list of processes
        self._arr_times = []  # list of times at which new process(es) will arrive
        self._queue = []      # queue (list of 'Ready' processes)
        self._running_proc = None  # (current/scheduled) running process
        self._blocked_procs = set()  # set of (current/scheduled) blocked processes
        self._record = []    # list of ordered dictionaries, each being what happens in each cycle, e.g.
                             # e.g. [{'Running': PROC_ID, 'Blocked': [PROC_ID1, PROC_ID1, ...], 'Ready':[PROC_ID3, PROC_ID4, ...]}, {...}]
        self._end_time = 0   # ending cycle
        self._reformat = []
        self._stat = []  # statistics
         
    def _mapArrival(self):
        """
        Map arrival times to a list of processes, and set arr_times
        """
        arr_times_set = set()
        for proc in self._proc_list:
            if not self._arrivals.has_key(proc.arr_time):
                self._arrivals[proc.arr_time] = [proc]
            else:
                self._arrivals[proc.arr_time].append(proc)   
            arr_times_set.add(proc.arr_time)          # add arrival time to set   
        self._arr_times = sorted(list(arr_times_set))  # save the set into sorted list for arrival times
    
    def prolog(self):
        """
        Things to be done before start()
        """
        self._mapArrival()
                    
    def start(self):
        """
        To be overridden in derived classes
        """
        self.prolog()
        
    def _getArrivalProcs(self, arr_time):
        """
        Get a list of processes at the arrival time (cycle) specified by arr_time 
            Then, remove (pop) this item
        """
        if self._arrivals.has_key(arr_time):
            return sorted(self._arrivals.pop(arr_time), key=lambda p: p.proc_id)  # return a list of processes sorted by process ID
        else:
            return []
    
    def _getArrivalTimes(self):
        return self._arr_times
       
    def _setScRunningProc(self, proc):
        """
        Set (Schedule) the 'Running' process for the next cycle
        """
        self._running_proc = proc
    
    def _unsetScRunningProc(self):
        """
        Unset (Schedule) the 'Running' process for the next cycle
            Set self._running_proc to None
        """
        self._running_proc = None
        
    def _setScBlockedProc(self, proc):
        """
        Add (Schedule) one 'Blocked' process for the next cycle
        """
        self._blocked_procs.add(proc)
    
    def _unsetScBlockedProc(self, proc):
        """
        Remove a process from self._blocked_procs
        """
        self._blocked_procs.remove(proc)
        
    def _getScRunningProc(self):
        """
        Get the scheduled 'Running' process at this cycle
        """
        return self._running_proc
    
    def _getScBlockedProcs(self):
        """
        Get a list scheduled 'Blocked' processes at this cycle
        """
        return self._blocked_procs
    
    def _getQueue(self):
        """
        Get a list of 'Ready' processes sorted by ready time and then by process ID
            "If two processes happen to be ready at the same time, give preference to the one with lower ID."
        """
        self._queue = sorted(self._queue, key=attrgetter('ready_time', 'proc_id'))  # sort by ready time and then by process ID
        return self._queue
    
    def printQueue(self):
        """
        Print queue with readable contents (proc_id and ready time)
        """
        queue = self._getQueue()
        for q in queue:
            print "Process ID: %d  Ready Time: %d" % (q.proc_id, q.ready_time)
            
    def _enqueue(self, proc):
        self._queue.append(proc)
    
    def _enqueueList(self, procs):
        """
        Enqueue a list of processes
        """

        self._queue += procs
    
    def _dequeue(self):
        """
        Dequeue a process
        """
        self._getQueue()  # sort the queue before dequeuing 
        return self._queue.pop(0)
    
    def _executeBlockedProcs(self):
        """
        Execute scheduled 'Blocked' process(es) if any
        
        ##!! Can be moved to Scheduler class
        """
        sc_blocked_procs = self._getScBlockedProcs()          # get list of scheduled 'Blocked' processes if any
        if sc_blocked_procs:                                  # execute scheduled 'Blocked' processes if any
            for proc in sc_blocked_procs:
                proc.blocked()                                
        blocked_procs = sc_blocked_procs
        return copy.copy(blocked_procs)
        
    def _recordCycle(self, running_proc=None, blocked_procs=[], ready_procs=[]):
        """
        Record what happens in each cycle (and print them out)
            * do not record those cycles that have nothing (no key for that kind of cycle)
            * record only process IDs
        """
        record = collections.OrderedDict()
        if running_proc != None:
            record['Running'] = running_proc.proc_id
        else:
            record['Running'] = None
            
        record['Blocked'] = [proc.proc_id for proc in blocked_procs]
        record['Ready'] = [proc.proc_id for proc in ready_procs]
        
        #print record  # testing
        
        # If nothing is to record at this cycle, then do not record this cycle
        if not (running_proc == None and blocked_procs == [] and ready_procs == []):
            self._record.append(record)
        else:
            self._record.append(None)
        
    def _terminate(self, cycle):
        self._end_time = cycle - 1
    
    
    def _reformatRecord(self):
        """
        Reformat original cycle record for output
        """
        reformat_record = []
        for record in self._record:
            rfm =  {} # reformatted dict
            #print record
            if record != None:
                if record['Running'] != None:
                    proc_id = record['Running']
                    rfm[proc_id] = 'running'
                    
                if record['Blocked']:
                    for proc_id in record['Blocked']:
                        rfm[proc_id] = 'blocked'
                        
                if record['Ready']:
                    for proc_id in record['Ready']:
                        rfm[proc_id] = 'ready'
            
            reformat_record.append(collections.OrderedDict(sorted(rfm.items(), key=lambda t: t[0])))
        self._reformat = reformat_record
    
    def _printable(self):
        """
        Generate printable list of reformatted record
        """
        self._reformatRecord()
        item_str_list = []
        for record in self._reformat:
            item_str = ""
            for item in record.items():
                item_str += "%d: %s " % (item[0], item[1])
            item_str_list.append(item_str)
        return item_str_list
    
    def output(self):
        """
        Return the output as a string
        """
        items = self._printable()
        output = ""
        for i in range(len(items)):
            output += "%d " % i + items[i] + "\n"
        
        self._getStat()
        output += "\n"
        output += "Finishing time: %d\n" % self._stat[0]
        output += "CPU utilization: %.2f\n" % self._stat[1]
        for item in self._stat[2].items():
            output += "Turnaround process %d: %d\n" % (item[0], item[1])
        return output
    
    def _getStat(self):
        """
        Generate statistics
        """
        self._stat.append(self._end_time)
        cpu_work = 0
        for record in self._record:
            if record:
                if record['Running'] != None:
                    cpu_work += 1
        cpu_util = utilities.roundup_2(float(cpu_work) / (self._end_time + 1))  # round up two digits, e.g. 0.66666666 => 0.67
        self._stat.append(cpu_util)
        turnaround = {}
        for proc in self._proc_list:
            turnaround[proc.proc_id] = proc.fin_time - proc.arr_time + 1
        self._stat.append(turnaround)
        

class FCFS(Scheduler):
    """
    FCFS: First-Come-First-Served Algorithm
    """
    def __init__(self, proc_list):
        super(FCFS, self).__init__(proc_list)
        self.__algorithm = 'FCFS'
    
    def start(self):
        """
        Main running cycle for FCFS
            Two major branches at each cycle:
                * (Branch 1) There is schedule for 'Running' process
                    ** Execute schedule ('Running' and 'Blocked')
                    ** Get new arrival processes and enqueue them
                    ** Record this cycle
                    ** Schedule next cycle
                * (Branch 2) There is NO schedule for 'Running' process
                    ** Check whether queue is empty
                        ** If empty, check new arrival processes, get the one with the smallest ID and make it 'Running'; 
                        ** If NOT empty, dequeue a process, and make it 'Running'
                    ** Schedule next cycle
                    
        """
        super(FCFS, self).start()
        
        # main iteration
        for i in itertools.count():

            sc_running_proc = self._getScRunningProc()
            sc_blocked_procs = self._getScBlockedProcs()
            
            # if scheduled 'Running' process is not None
            if sc_running_proc:
                
                # execute schedule ('Running', and 'Blocked' if any)
                running_proc = sc_running_proc.running()     # execute scheduled 'Running' process
                blocked_procs = self._executeBlockedProcs()                # execute scheduled 'Blocked' process(es) if any
                self._enqueueArrivals(i)                       # get new arrivals (if any) and enqueue them as ready
                ready_procs = self._getQueue()
                self._recordCycle(running_proc, blocked_procs, ready_procs)  # record this cycle
                self._scheduleNextCycle(i, running_proc, blocked_procs)    # schedule the next cycle using FCFS algorithm

            # if scheduled 'Running' process is None
            else:        
                # if queue is not empty (may include pre-enqueued processes at previous cycle)
                if self._getQueue():
                    self._enqueueArrivals(i)        # first, get new arrivals (if any) and enqueue them as ready
                    #self.printQueue()
                    running_proc = self._dequeue()                               # dequeue and run the proper process (smallest ready time and ID)
                    running_proc.running()
                    blocked_procs = self._executeBlockedProcs()                  # execute scheduled 'Blocked' processes if any
                    ready_procs = self._getQueue()
                    self._recordCycle(running_proc, blocked_procs, ready_procs)  # record this cycle
                    self._scheduleNextCycle(i, running_proc, blocked_procs)      # schedule the next cycle using FCFS algorithm                   
                       
                # if queue is empty
                else:
                    # if there are new arrivals at this cycle (run one from arrivals at this cycle)                        
                    if i in self._getArrivalTimes():   
                        arr_procs = self._getArrivalProcs(i)                       # get new arrivals
                        running_proc = arr_procs.pop(0)                            # get the process with the smallest process ID
                        running_proc.running()                                     # run this process
                        blocked_procs = self._executeBlockedProcs()                # execute scheduled 'Blocked' processes if any
                        self._enqueueList(arr_procs)                               # enqueue the rest of arrival processes
                        ready_procs = self._getQueue()
                        self._recordCycle(running_proc, blocked_procs, ready_procs)  # record this cycle
                        self._scheduleNextCycle(i, running_proc, blocked_procs)    # schedule the next cycle using FCFS algorithm
                     
                    # if there is no new arrivals at this cycle                             
                    else:
                        # if there is still new arrival in future cycles (self._arrivals not empty) or scheduled 'Blocked' processes not empty
                        if self._arrivals or sc_blocked_procs:
                            running_proc = None                                        # no running process at this cycle                    
                            blocked_procs = self._executeBlockedProcs()                # execute scheduled 'Blocked' processes if any
                            ready_procs = self._getQueue()                                           # no arrival processes at this cycle
                            self._recordCycle(running_proc, blocked_procs, ready_procs)  # record this cycle (only if blocked_procs exists)
                            self._scheduleNextCycle(i, running_proc, blocked_procs)    # schedule the next cycle using FCFS algorithm
                        
                        # if there is not any new arrival in future cycles                          
                        else:
                            self._terminate(i)  # update end time with (i-1)
                            break               # terminate the iteration                            
                

    def _enqueueArrivals(self, this_cycle):
        """
        Get the list of all new arrival processes and enqueue them as ready
        
        ##!! Can be moved to Scheduler class
        """
        if this_cycle in self._getArrivalTimes():   # if new process(es) arrive at this cycle
            arr_procs = self._getArrivalProcs(this_cycle)
            for proc in arr_procs:                  # set all processes in the list 'Ready'
                proc.waiting(this_cycle)             # with ready_time = i
            self._enqueueList(arr_procs)            # enqueue this list of processes (which is already sorted by process ID)        
            return arr_procs
        
        return []  # return [] if no new process(es) arrive at this cycle
    
    def _enqueueListReady(self, cycle, procs):
        """
        Enqueue the specified list of processes, calling waiting() on each process and sort by process ID
            * procs may be empty
              
        ##!! Can be moved to Scheduler class
        """
        if procs:
            for proc in procs:
                proc.waiting(cycle)
            
            sorted_procs = sorted(procs, key=lambda p: p.proc_id) 
            self._enqueueList(sorted_procs)

        
    def _scheduleNextCycle(self, this_cycle, running_proc, blocked_procs):
        """
        Schedule for the next cycle (FCFS)
            * Schedule 'Running' process
            * Schedule 'Blocked' process(es)
            * Enqueue 'Blocked'-to-'Ready' process(es) if any
        """
        # for the 'Running' process
        if running_proc:
            # for those with no I/O time
            if running_proc.hasNoIO():
                if running_proc.toTerminate():
                    self._unsetScRunningProc()            # to terminate
                    running_proc.finish(this_cycle)
                    
                else:
                    self._setScRunningProc(running_proc)  # keep 'Running'
            
            # for those with I/O time
            else:
                # from 'Running' to 'Blocked'
                if running_proc.toBlocked():             
                    self._unsetScRunningProc()             # unset scheduled 'Running' process
                    self._setScBlockedProc(running_proc)   # add it to scheduled 'Blocked' processes
                    
                # from 'Running' to Terminate 
                elif running_proc.toTerminate():          
                    self._unsetScRunningProc()             # unset scheduled 'Running' process
                    running_proc.finish(this_cycle)        # update process fin_time
                # keep 'Running' (still in first half, or )
                else:
                    self._setScRunningProc(running_proc)
        else:
            self._unsetScRunningProc()

        # for each of the 'Blocked' processes
        if blocked_procs:
            temp_procs = []  # temporary list processes to be enqueued
            for proc in blocked_procs:
                # keep 'Blocked'
                if proc.isBlocked():                     
                    self._setScBlockedProc(proc)
                    
                # from 'Blocked' to 'Ready' (Ready at next cycle)
                else:                                    
                    self._unsetScBlockedProc(proc)       # unset scheduled 'Blocked' process      
                    temp_procs.append(proc)              # append this process to temporary queue
            
            # This is for: "If two processes happen to be ready at the same time, give preference to the one with lower ID."
            self._enqueueListReady(this_cycle + 1, temp_procs)  # temp_procs may be empty


class RR(FCFS):
    """
    RR: Round-Robin with quantum 2
        * Derived from FCFS
        * Override _scheduleNextCycle() method
    """
    def __init__(self, proc_list):
        super(FCFS, self).__init__(proc_list)
        self.__algorithm = 'RR'
        self.quantum = 2  # set quantum
        
    def start(self):
        """
        Main running cycle for RR
                    
        """
        super(RR, self).start()
        
    def _enqueueReady(self, cycle ,proc):
        """
        Enqueue a single process, calling waiting()
        """
        proc.waiting(cycle)
        self._enqueue(proc)
        
    def _scheduleNextCycle(self, this_cycle, running_proc, blocked_procs):
        """
        Schedule for the next cycle (RR)
            * Schedule 'Running' process
            * Schedule 'Blocked' process(es)
            * Enqueue 'Blocked'-to-'Ready' process(es) if any
            * Enqueue 'Running'-to-'Ready' process(es) if any
        """
        # for the 'Running' process
        if running_proc:
            # for those with no I/O time
            if running_proc.hasNoIO():
                if running_proc.toTerminate():              # to terminate
                    self._unsetScRunningProc()
                    running_proc.finish(this_cycle)             
                    
                elif running_proc.hasRunning(self.quantum):          # if it has already running for quantum cycles
                    self._unsetScRunningProc()                       # from 'Running' to 'Ready'
                    self._enqueueReady(this_cycle + 1, running_proc) # enqueue this process with ready time of next cycle   
                    
                else:
                    self._setScRunningProc(running_proc)  # keep 'Running'
            
            # for those with I/O time
            else:
                # from 'Running' to 'Blocked'
                if running_proc.toBlocked():
                    self._unsetScRunningProc()             # unset scheduled 'Running' process
                    self._setScBlockedProc(running_proc)   # add it to scheduled 'Blocked' processes
                    
                # from 'Running' to Terminate 
                elif running_proc.toTerminate():          
                    self._unsetScRunningProc()             # unset scheduled 'Running' process
                    running_proc.finish(this_cycle)        # update process fin_time

                # others
                else:
                    # if it has already running for quantum cycles
                    if running_proc.hasRunning(self.quantum):  
                        self._unsetScRunningProc()                       # from 'Running' to 'Ready'
                        self._enqueueReady(this_cycle + 1, running_proc) # enqueue this process with ready time of next cycle   
                    
                    # else, schedule it 'Running'
                    else:
                        self._setScRunningProc(running_proc)
        else:
            self._unsetScRunningProc()

        # for each of the 'Blocked' processes
        if blocked_procs:
            temp_procs = []  # temporary list processes to be enqueued
            for proc in blocked_procs:
                # keep 'Blocked'
                if proc.isBlocked():                     
                    self._setScBlockedProc(proc)
                    
                # from 'Blocked' to 'Ready' (Ready at next cycle)
                else:                                    
                    self._unsetScBlockedProc(proc)       # unset scheduled 'Blocked' process      
                    temp_procs.append(proc)              # append this process to temporary queue
            
            self._enqueueListReady(this_cycle + 1, temp_procs)  # temp_procs may be empty            
        
        
class SRJF(Scheduler):
    """
    SRJF: Shortest remaining job first (preemptive)
    """ 
    def __init__(self, proc_list):
        super(SRJF, self).__init__(proc_list)
        self.__algorithm = 'SRJF'
        self.__ready_procs = []
        
    def start(self):
        """
        Main running cycle for SRJF
                    
        """
        super(SRJF, self).start()
        
        # main iteration
        for i in itertools.count():

            # get scheduled 'Blocked' processes if any
            sc_blocked_procs = self._getScBlockedProcs()
                        
            # iteration exit conditions
            # DO NOT EXIT if there are still:
            # * new arrivals, or 
            # * scheduled 'Blocked' processes, or
            # * ready processes.
            if self._arrivals or sc_blocked_procs or self._getReadyProcs():
                pass
            else:
                self._terminate(i)  # update end time with (i-1)
                break               # terminate the iteration 
            
            if sc_blocked_procs:
                blocked_procs = self._executeBlockedProcs()
            else:
                blocked_procs = []  
                
            # if new processes arrived at this cycle
            if i in self._getArrivalTimes():
                arr_procs = self._getArrivalProcs(i)
                self._addReadyProcs(arr_procs)   # add new processes to ready processes
            
            ready_procs = self._getReadyProcs()
            running_proc = None  # local variable
            # if ready processes is not empty
            if ready_procs:
                running_proc = self._getProperProc()  # get the proper process from ready processes
                running_proc.running()
            else:
                running_proc = None
                
            ready_procs = self._getReadyProcs()  # get the remaining ready processes
            self._recordCycle(running_proc, blocked_procs, ready_procs)
            self._scheduleNextCycle(i, running_proc, blocked_procs)
            
    def _getReadyProcs(self):
        return self.__ready_procs
    
    def _getProperProc(self):
        """
        Get the proper process to run following SRJF algorithm
        """
        self.__ready_procs = sorted(self.__ready_procs, key=lambda p: p.rem_cpu_time)  # sort by remaining CPU time
        return self.__ready_procs.pop(0)  # pop the proper process
        
    def _addReadyProcs(self, procs):
        self.__ready_procs += procs
    
    def _addReadyProc(self, proc):
        self.__ready_procs.append(proc)
    
   
    def _scheduleNextCycle(self, this_cycle, running_proc, blocked_procs):
        """
        Schedule for the next cycle (SRJF)
            * Schedule the 'Blocked' processes for the next cycle
        """
        # for 'Running' process
        if running_proc:
            
            # for those with I/O time
            if not running_proc.hasNoIO():
                
                # from 'Running' to 'Blocked'
                if running_proc.toBlocked():
                    self._setScBlockedProc(running_proc)
                    
                # from 'Running' to terminate

                elif running_proc.toTerminate():
                    #self._delReadyProc(running_proc)  # do not add to ready processes
                    running_proc.finish(this_cycle)
                
                # others (add to ready processes)
                else:
                    self._addReadyProc(running_proc)
                    
            # for those with no I/O time (no block needed)
            else:
                if running_proc.toTerminate():
                    running_proc.finish(this_cycle)
                    
                else:
                    self._addReadyProc(running_proc)

        # for 'Blocked' processes
        if blocked_procs:

             for proc in blocked_procs:
                # keep 'Blocked'
                if proc.isBlocked():                     
                    self._setScBlockedProc(proc)
                # from 'Blocked' to 'Ready' (Ready at next cycle)
                else:
                    self._unsetScBlockedProc(proc)                   
                    self._addReadyProc(proc)
            
if __name__ == '__main__':
    utilities.output.warning("Please run main.py script from project's directory.")       
    