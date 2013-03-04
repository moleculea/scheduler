#! /usr/bin/env python
# -*- coding: utf-8  -*-
import sys
import os
import re
import collections
import platform
import copy
from scripts import utilities
try:
    import argparse
    from scripts.scheduler import *
except:
    utilities.check_version()

def getArgs():
    """Parse command-line arguments with optional functionalities"""
    
    parser = argparse.ArgumentParser(
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="Schedule process with a specific scheduling algorithm (FCFS, RR, or SRJF)\n\n\
  FCFS : First-Come-First-Served (non-preemptive)\n\
  RR   : Round-Robin with quantum 2\n\
  SRJF : Shortest remaining job first (preemptive)", 
                                     usage="python %(prog)s [-hnpv] code input_file",
                                     epilog="usage examples: \n\
  %(prog)s 0 input.txt                (save output without printing)\n\
  %(prog)s -p 1 input.txt             (print output)\n\
  %(prog)s -v 2 input.txt             (print verbose info)\n\
  %(prog)s -pn 3 input.txt            (simply print and do not save output)\n"
                                     )
    parser.add_argument('code', metavar="code ({0,1,2,3})", type=int, choices=[0, 1, 2, 3], help="code (0, 1, 2, or 3) for scheduling algorithm (0: FCFS; 1: RR; 2: SRJF; 3: all of them)")    
    parser.add_argument('input_file', help="/path/to/input-file.txt")
    parser.add_argument('-n','--no-save', action="store_true", dest="no_save", help="do not save output to files")
    parser.add_argument('-p','--print', action="store_true", dest="to_print", help="print output file content to standard output")
    parser.add_argument('-v','--verbose', action="store_true", dest="to_verbose", help="print verbose information")
    
    # if no argument is given, print help message
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    code, input_file, to_print, verbose, no_save = args.code, args.input_file, args.to_print, args.to_verbose, args.no_save
    return code, input_file, to_print, verbose, no_save


def checkPaths(input_file, verbose=False):
    """Check validity of paths of input file and output file """
    abs_path = os.path.abspath(input_file)  # absolute path of input file
    if verbose:
        utilities.output.debug("Input file name: %s." %abs_path)
        
    if os.path.isfile(abs_path):
        pass
    else:
        if os.path.exists(abs_path):
            if os.path.isdir:
                utilities.output.error("Input file \"%s\" is a directory, not a file." % abs_path)
                sys.exit(1)
        else:
            utilities.output.error("Input file \"%s\" does not exist." % abs_path)
            sys.exit(1)
            
    dir_name = os.path.dirname(abs_path)
    base_name = os.path.basename(abs_path)
    return dir_name, base_name

def readInput(input_file, verbose=False):
    f = None
    text = ""
    try:
        if verbose:
            utilities.output.debug("Opening input file \"%s\"..." %input_file)
        f = open(input_file, "r")
        text = f.read()
        f.close()
        
    except:
        utilities.output.error("Cannot open the file \"%s\"" % input_file)
        sys.exit(1)
    
    finally:
        f.close()

    return text

def splitInput(text, verbose=False):
    if verbose:
        utilities.output.debug("Reading input file...")
    s = text.split()
    return s

def parseList(raw_list, verbose=False):
    length = len(raw_list)
    proc_list = [] # list of processes
    proc_id_set = set() # set of process IDs
    proc = None  # temporary variable for process in the iteration
    if length % 4:
        utilities.output.error("There seems to be syntax error in the input file: incomplete process")
        sys.exit(1)
        
    for i in xrange(length):
        current = 0 # current element as integer
        try:
            current = int(raw_list[i])
        except: 
            utilities.output.error("There seems to be syntax error in the input file: non-integer element %s" % raw_list[i])
            sys.exit(1)
        #print current
        
        if current < 0:
            utilities.output.error("There seems to be syntax error in the input file: negative integer is meaningless %s" % raw_list[i])
            sys.exit(1)           

        if i % 4 == 0:
            if current not in proc_id_set:  # check whether this ID is already in the set
                proc_id_set.add(current)
            else:
                utilities.output.error("There seems to be syntax error in the input file: duplicate process ID %d" % current)
                sys.exit(1)
            #print proc_id_set
            proc = Process(current) # initialize a Process object with the current ID
            
        if i % 4 == 1:
            if current == 0:
                utilities.output.error("There seems to be syntax error in the input file: CPU time cannot be 0" )
                sys.exit(1)
            proc.cpu_time = current
            
        if i % 4 == 2:
            proc.io_time = current
            
        if i % 4 == 3:
            proc.arr_time = current
            proc_list.append(proc) # append this Process object into proc_list
    
    return proc_list

class Config(object):
    def __init__(self, code, input_file, to_print, verbose, dir_name, base_name, no_save):
        self.code = code
        self.input_file = input_file
        self.to_print = to_print
        self.verbose = verbose
        self.dir_name = dir_name
        self.base_name = base_name
        self.no_save = no_save
        
def preprocess():
    code, input_file, to_print, verbose, no_save = getArgs()
    dir_name, base_name = checkPaths(input_file, verbose)
    return Config(code, input_file, to_print, verbose, dir_name, base_name, no_save)

def postprocess(dir_name, base_name, code, outputs, verbose=False, no_save=False):
    s = os.path.splitext(base_name)
    file_name = s[0]
    ext_name  = s[1]
    if code in [0, 1, 2]:
        output_file = "%s/%s-%d%s" % (dir_name, file_name, code, ext_name)         
        if not no_save:
            writeOutput(output_file, outputs[0], verbose)

    if code == 3:
        for i in range(3):
            output_file = "%s/%s-%d%s" % (dir_name, file_name, i, ext_name)
            if not no_save:
                writeOutput(output_file, outputs[i], verbose)


def writeOutput(output_file, output, verbose=False):
    f = None
    try:
        if verbose:
            utilities.output.debug("Opening output file \"%s\" to write." % output_file)
        f = open(output_file, "w")
        f.write(output)
        
    except:
        utilities.output.error("Cannot write output to file \"%s\"." %output_file)
        sys.exit(1)
        
    finally:
        f.close()
        
def printOutput(code, outputs, verbose):
    messages = ["FCFS:", "RR:", "SRJF:"]
    if verbose:
        print "-"*24
    if code in [0, 1, 2]:
        print messages[code]
        print outputs[0]
    if code == 3:
        for i in range(3):
            print messages[i]
            print outputs[i]
            if i in [0,1]:
                print "-"*24

       
def main():
    # get config
    config = preprocess()
    code = config.code
    input_file = config.input_file
    to_print = config.to_print
    verbose = config.verbose
    dir_name = config.dir_name
    base_name = config.base_name
    no_save = config.no_save
    # process input file
    text = readInput(input_file, verbose)
    s = splitInput(text, verbose)
    proc_list0 = parseList(s, verbose)
    for p in proc_list0:
        p.propagate()
    
    proc_list1 = copy.deepcopy(proc_list0)
    proc_list2 = copy.deepcopy(proc_list0)
    fcfs  = None
    rr    = None
    srjf  = None
    outputs = []
    
    # FCFS
    if code == 0 or code == 3:
        if verbose:
            utilities.output.debug("Scheduling with FCFS (non-preemptive) algorithm")
        fcfs = FCFS(proc_list0)
        fcfs.start()
        output = fcfs.output()
        outputs.append(output)
        
    # RR (or all)
    if code == 1 or code == 3:
        if verbose:
            utilities.output.debug("Scheduling with RR (Round-Robin with quantum 2) algorithm")
        rr = RR(proc_list1)
        rr.start()
        output = rr.output()
        outputs.append(output)
        
    # SRJF (or all)
    if code == 2 or code == 3:
        if verbose:
            utilities.output.debug("Scheduling with SRJF (preemptive) algorithm")
        srjf = SRJF(proc_list2)
        srjf.start()
        output = srjf.output()
        outputs.append(output)

    if to_print:
        printOutput(code, outputs, verbose)
        
    postprocess(dir_name, base_name, code, outputs, verbose, no_save)
    
if __name__ == '__main__':
    main()