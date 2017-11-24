#!/usr/bin/env python3
#
# Copyright (c) 2017 Aaron LI
# MIT license
#
# Create image from OSKAR simulated visibility data using `WSClean`.
# WSClean: https://sourceforge.net/p/wsclean/
#
# 2017-09-01
#


import os
import sys
import re
import argparse
import subprocess
import time


def printlog(msg, logfile=None, **kwargs):
    if logfile:
        files = [sys.stdout, logfile]
    else:
        files = [sys.stdout]
    for f in files:
        print(msg, file=f, **kwargs)


def wsclean(args, dryrun=False, logfile=None):
    # NOTE: Convert all arguments to strings
    cmd = ["wsclean"] + [str(arg) for arg in args]
    printlog("CMD: %s" % " ".join(cmd), logfile=logfile)
    if dryrun:
        print(">>> DRY RUN MODE <<<")
        return

    t1 = time.perf_counter()
    with subprocess.Popen(cmd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          universal_newlines=True) as proc:
        for line in proc.stdout:
            printlog(line.strip(), logfile=logfile)
        retcode = proc.wait()
        if retcode:
            raise subprocess.CalledProcessError(retcode, cmd)
    t2 = time.perf_counter()
    printlog("-----------------------------------------------------------",
             logfile=logfile)
    printlog("WSClean Elapsed time: %.1f [min]" % ((t2-t1)/60),
             logfile=logfile)
    printlog("-----------------------------------------------------------",
             logfile=logfile)


def main():
    parser = argparse.ArgumentParser(
        description="Run WSClean with more handy arguments")
    parser.add_argument("-a", "--args", dest="args",
                        help="additional arguments for WSClean, " +
                        "in a quoted string separated by space, e.g.," +
                        "' -simulate-noise 0.001' (NOTE the beginning space!)")
    parser.add_argument("-d", "--dirty", dest="dirty", action="store_true",
                        help="only create dirty images (by setting niter=0)")
    parser.add_argument("-n", "--dry-run", dest="dryrun", action="store_true",
                        help="do not actually run WSClean")
    parser.add_argument("--update-model", dest="update_model",
                        action="store_true",
                        help="write/update the MODEL_DATA column in MS")
    parser.add_argument("--save-weights", dest="save_weights",
                        action="store_true",
                        help="save gridded weights in <name>-weights.fits")
    parser.add_argument("--save-uv", dest="save_uv",
                        action="store_true",
                        help="save gridded uv plane (i.e., FFT of the " +
                        "residual image) in <name>-uv-{real,imag}.fits")
    parser.add_argument("--circular-beam", dest="circular_beam",
                        action="store_true",
                        help="force the fitted beam to be circular, i.e., " +
                        "BMIN == BMAJ")
    parser.add_argument("--uv-range", dest="uv_range", default=":",
                        help="uv range [lambda] (i.e., baseline lengths) " +
                        "used for imaging; syntax: '<min>:<max>' " +
                        "(default: ':', i.e., all uv/baselines)")
    parser.add_argument("-w", "--weight", dest="weight", default="uniform",
                        choices=["uniform", "natural", "briggs"],
                        help="weighting method (default: 'uniform')")
    parser.add_argument("-B", "--briggs", dest="briggs",
                        type=float, default=0.0,
                        help="Briggs robustness parameter (default: 0); " +
                        "-1 (uniform) -> 1 (natural)")
    parser.add_argument("-#", "--niter", dest="niter",
                        type=int, default=200000,
                        help="maximum number of CLEAN iterations " +
                        "(default: 200,000)")
    parser.add_argument("--gain", dest="gain", type=float, default=0.1,
                        help="CLEAN gain for each minor iteration " +
                        "(default: 0.1)")
    parser.add_argument("--mgain", dest="mgain", type=float, default=0.85,
                        help="CLEAN gain for major iterations " +
                        "(default: 0.85)")
    parser.add_argument("-s", "--size", dest="size", type=int,
                        required=True,
                        help="output image size (pixel number on a side)")
    parser.add_argument("-p", "--pixelsize", dest="pixelsize", type=float,
                        required=True,
                        help="output image pixel size [arcsec]")
    parser.add_argument("-G", "--taper-gaus", dest="taper_gaus", type=float,
                        help="taper the weights with a Gaussian function " +
                        "to reduce the contribution of long baselines. " +
                        "Gaussian beam size in [arcsec].")
    parser.add_argument("--fit-spec-order", dest="fit_spec_order", type=int,
                        help="do joined-channel CLEAN by fitting the " +
                        "spectra with [order] polynomial in normal-space")
    #
    exgrp = parser.add_mutually_exclusive_group()
    exgrp.add_argument("-S", "--threshold-nsigma", dest="threshold_nsigma",
                       type=float, default=2.0,
                       help="estimate the noise level <sigma> and stop at " +
                       "nsigma*<sigma> (default: 2.0 <sigma>)")
    exgrp.add_argument("-t", "--threshold", dest="threshold", type=float,
                       help="stopping CLEAN threshold [mJy]")
    #
    parser.add_argument("-N", "--name", dest="name", required=True,
                        help="filename prefix for the output files")
    parser.add_argument("-m", "--ms", nargs="+", help="input visibility MSs")
    args = parser.parse_args()

    nms = len(args.ms)  # i.e., number of MS == number of channels

    cmdargs = [
        "-verbose",
        "-log-time",
        "-pol", "XX",  # OSKAR "Scalar" simulation only give "XX" component
        "-make-psf",  # always make the PSF, even no cleaning performed
        "-tempdir", "/tmp",
    ]

    if args.dirty:
        cmdargs += ["-niter", 0]  # make dirty image only
    else:
        cmdargs += ["-niter", args.niter]

    if args.weight == "uniform":
        cmdargs += ["-weight", "uniform",
                    "-weighting-rank-filter", 3]
    elif args.weight == "briggs":
        cmdargs += ["-weight", "briggs", args.briggs]
    else:
        cmdargs += ["-weight", args.weight]  # natural
    cmdargs += ["-gain", args.gain]
    cmdargs += ["-mgain", args.mgain]
    cmdargs += ["-size", args.size, args.size]
    cmdargs += ["-scale", "{0}asec".format(args.pixelsize)]

    if args.fit_spec_order:
        cmdargs += ["-joinchannels", "-channelsout", nms,
                    "-fit-spectral-pol", args.fit_spec_order+1]

    if args.update_model:
        cmdargs += ["-update-model-required"]
    else:
        cmdargs += ["-no-update-model-required"]

    if args.save_weights:
        cmdargs += ["-saveweights"]
    if args.save_uv:
        cmdargs += ["-saveuv"]
    if args.circular_beam:
        cmdargs += ["-circularbeam"]

    # uv/baseline range
    uvmin, uvmax = args.uv_range.strip().split(":")
    if uvmin:
        cmdargs += ["-minuv-l", float(uvmin)]
    if uvmax:
        cmdargs += ["-maxuv-l", float(uvmax)]

    if args.threshold:
        cmdargs += ["-threshold", args.threshold*1e-3]  # [mJy] -> [Jy]
    else:
        cmdargs += ["-auto-threshold", args.threshold_nsigma]

    if args.taper_gaus:
        cmdargs += ["-taper-gaussian", args.taper_gaus]

    # additional WSClean arguments
    if args.args:
        extra_args = re.split(r"\s+", args.args.strip())
        print("Additional WSClean arguments:", extra_args)
        cmdargs += extra_args

    nameprefix = args.name.rstrip("-_")
    cmdargs += ["-name", nameprefix]
    cmdargs += args.ms

    if args.dryrun:
        logfile = None
    else:
        logfilename = nameprefix + "-wsclean.log"
        logfile = open(logfilename, "w")
        logfile.write(" ".join(sys.argv) + "\n")
    wsclean(cmdargs, dryrun=args.dryrun, logfile=logfile)

    if args.dirty and not args.dryrun:
        # Remove the output "-image" since it is identical to "-dirty"
        os.remove(nameprefix+"-image.fits")


if __name__ == "__main__":
    main()
