#!/usr/bin/env python3

import os
from ruamel.yaml import YAML

from mf import MakeFile, Target

def mf_template(opts):
    mf = MakeFile(
        flgs=opts["compiler_flags"],
        trgs=None,
        cmplr=opts["compiler"],
        lbs=opts["libraries"],
    )
    return mf


def build_mf(drctry, tmplt, fexts):
    """Build makefile for directory from template"""
    # Find all source files in directory
    srcs = get_sources(drctry, fexts)

    # If no source code files, no makefile needed
    if len(srcs) == 0:
        return
    # Remove sources which don't contain main functions
    srcs = [src for src in srcs if is_main_source(os.path.join(drctry, src + ".cpp"))]

    # Get all dependencies
    targs = []
    for src in srcs:
        src_path = os.path.join(drctry, src + ".cpp")
        incs = follow_includes(src_path)
        targs.append(Target(nm=src, dps=incs))

    m = MakeFile(
        flgs=tmplt.flags, trgs=targs, cmplr=tmplt.compiler, lbs=tmplt.libraries
    )

    # Write mf to file
    m.to_file(drctry)


def is_main_source(src) -> bool:
    """
    A source file is a 'main' source if it has a 'main' function.
    Because we're only dealing with C or C++ files,
    """
    with open(src) as f:
        return "int main(" in f.read()


def get_sources(direc, exts):
    """
    Returns list of files with an extension in exts
    in direc with a main() function in the file
    """
    s = []
    for fl in os.scandir(direc):
        fext = os.path.splitext(fl)[1]
        fname = os.path.splitext(os.path.split(fl)[1])[0]
        if fext in exts:
            s.append(fname)
    return s


def follow_includes(file):
    """
    Get implementation (.cpp) file for header files included by #include ""
    Extracts lines with #include "FNAME", then appends FNAME.cpp to
    list returned to caller
    """
    """
        Because each .cpp file has some includes, keep track of files
        visited, so that we don't visit a file more than once
    """
    # Files included for topmost file
    incs = get_incs(file)

    d = os.path.split(file)[0]
    visited = [os.path.split(file)[1]]
    resolved_incs = list(incs)
    return resolved_incs
    while len(incs) > 0:
        inc = incs.pop()
        visited.append(inc)

    return resolved_incs


def get_incs(file):
    """
    Files included in file
    """
    incs = []
    with open(file) as f:
        for line in f:
            # Line starts with '#include "'
            if line.startswith("#include") and '"' in line:
                # Extract filename between quotes, replace extension with .cpp
                inc_name = os.path.splitext(line.split('"')[1])[0]
                incs.append(inc_name + ".cpp")
    return incs


def read_cfg(path):
    """
    Read config from yaml file
    """
    with open(path) as c:
        yaml = YAML(typ="safe")
        cfg = yaml.load(c)
    return cfg


def main(cfg_path):
    # Get configuration
    cfg = read_cfg(cfg_path)

    startDir = cfg["directory_structure"]["root"]
    subDirs = [os.path.join(startDir, sub) for sub in cfg["directory_structure"]["subs"]]
    exts = cfg["source_extensions"]
    tmplt = mf_template(cfg["makefile_options"])

    # Check that root directory exists, create if necessary
    if not os.path.isdir(startDir):
        os.makedirs(startDir)

    for s in subDirs:
        # Create s if necessary
        if not os.path.isdir(s):
            os.mkdir(s)

        # Iterate over subdirectories of s, building makefiles in each subdir
        for (thisDir, subsHere, filesHere) in os.walk(s, topdown=True):
            # Remove subdirectories we don't want to traverse
            subsHere[:] = [sub for sub in subsHere if sub not in igDirs]
            # Build makefile for current directory
            build_mf(thisDir, tmplt, exts)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(f"USAGE: {sys.argv[0]} CFG_FILE")
        exit(2)

    main(sys.argv[1])
