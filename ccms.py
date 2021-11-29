#!/usr/bin/env python3

import os
from ruamel.yaml import YAML
from multiprocessing import Pool
from functools import partial

from mf import MakeFile, Target

def mf_template(opts):
    mf = MakeFile(
        flgs=opts["compiler_flags"],
        trgs=None,
        cmplr=opts["compiler"],
        lbs=opts["libraries"],
    )
    return mf


def build_mf(drctry, tmplt, fext):
    """Build makefile for directory from template"""

    # Find all source files in directory
    srcs = get_sources(drctry, fext)

    # If no source code files, no makefile needed
    if len(srcs) == 0:
        return
    # Remove sources which don't contain main functions
    srcs = [src for src in srcs if is_main_source(os.path.join(drctry, src + fext))]

    # Get all dependencies
    targs = []
    for src in srcs:
        src_path = os.path.join(drctry, src + fext)
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


def get_sources(direc, ext):
    """
    Returns list of files with an extension in exts
    in direc with a main() function in the file
    """
    s = []
    for fl in os.scandir(direc):
        fext = os.path.splitext(fl)[1]
        fname = os.path.splitext(os.path.split(fl)[1])[0]
        if fext == ext:
            s.append(fname)
    return s


def follow_includes(file):
    """
    Get implementation (.cpp) file for header files included by #include ""
    """
    """
        Because each file has some includes, keep track of files
        visited, so that we don't visit a file more than once
    """
    # Files included for topmost file
    incs = get_incs(file)
    d = os.path.split(file)[0]
    visited = [os.path.split(file)[1]]
    resolved_incs = list(incs)
    while len(incs) > 0:
        inc = incs.pop()
        if inc in visited:
            continue
        visited.append(inc)
        tmp = get_incs(os.path.join(d, inc))
        incs.extend(tmp)
        resolved_incs.extend(tmp)

    return set(resolved_incs)


def get_incs(file):
    """
    Files included in file
    """
    incs = []
    ext = os.path.splitext(file)[1]
    with open(file) as f:
        for line in f:
            # Line starts with '#include "'
            if line.startswith("#include") and '"' in line:
                # Extract filename between quotes, replace extension with that of file
                inc_name = os.path.splitext(line.split('"')[1])[0]
                incs.append(inc_name + ext)
    return incs


def read_cfg(path):
    """
    Read config from yaml file
    """
    with open(path) as c:
        yaml = YAML(typ="safe")
        cfg = yaml.load(c)
    return cfg


def build_sub(drctry, tmplt, fext, igDirs):
    """
        Walks filesystem with root at drctry (creates it if it doesn't exist),
        and builds makefiles at each point
    """
    # Create drctry if it doesn't exist
    if not os.path.isdir(drctry):
        os.mkdir(drctry)

    for (thisDir, subsHere, filesHere) in os.walk(drctry, topdown=True):
        # Remove subdirectories we don't want to traverse
        subsHere[:] = [sub for sub in subsHere if sub not in igDirs]
        # Build makefile for current directory
        build_mf(thisDir, tmplt, fext)

def main(cfg_path):
    # Get configuration
    cfg = read_cfg(cfg_path)

    startDir = cfg["directory_structure"]["root"]
    subDirs = [os.path.join(startDir, sub) for sub in cfg["directory_structure"]["subs"]]
    igDirs = cfg["ignored_directories"]
    ext = cfg["source_extension"]
    tmplt = mf_template(cfg["makefile_options"])

    # Check that root directory exists, create if necessary
    if not os.path.isdir(startDir):
        os.makedirs(startDir)

    with Pool() as p:
        # Fix tmplt, exts as arguments to build_sub
        bld = partial(build_sub,tmplt=tmplt, fext=ext, igDirs=igDirs)
        p.map(bld, subDirs)

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(f"USAGE: {sys.argv[0]} CFG_FILE")
        exit(2)

    main(sys.argv[1])
