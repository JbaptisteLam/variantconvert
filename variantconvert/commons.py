# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function

import logging as log
import os
import time

from functools import lru_cache
from pyfasta import Fasta


def set_log_level(verbosity):
    configs = {
        "debug": log.DEBUG,
        "info": log.INFO,
        "warning": log.WARNING,
        "error": log.ERROR,
        "critical": log.CRITICAL,
    }
    if verbosity not in configs.keys():
        raise ValueError(
            "Unknown verbosity level:"
            + verbosity
            + "\nPlease use any in:"
            + configs.keys()
        )
    log.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=configs[verbosity],
    )


def is_helper_func(arg):
    if isinstance(arg, list):
        if arg[0] == "HELPER_FUNCTION":
            return True
        else:
            raise ValueError(
                "This config file value should be a String or a HELPER_FUNCTION pattern:"
                + arg
            )
    return False


@lru_cache
def get_genome(fasta_path):
    return Fasta(fasta_path)


@lru_cache
def varank_to_vcf_coords(coord_conversion_file):
    """
    outside of helper class to avoid caching issues
    """
    id_to_coords = {}
    with open(coord_conversion_file, "r") as f:
        next(f)
        for l in f:
            l = l.strip().split("\t")
            id_to_coords[l[0]] = {
                "#CHROM": "chr" + l[1],
                "POS": l[2],
                "REF": l[3],
                "ALT": l[4],
            }
    return id_to_coords


def clean_string(s):
    """
    replace characters that will crash bcftools and/or cutevariant
    those in particular come from Varank files

    NB: the "fmt: off/on" comments are used to prevent black
    from making the replace dict into a one line mess
    """
    # fmt: off
    replace = {";": ",", "“": '"', "”": '"', "‘": "'", "’": "'"}
    # fmt: on
    for k, v in replace.items():
        s = s.replace(k, v)
    return s


# JB
def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False


# JB sam tu vas m'insulter fort pour le merge
def clean_values(values):
    """
    JB
    regarding IGV errors, sample field values  > 1 can't have decimal values for examples 150.45 even if the header is discarded
    so if values are sup or equal to 1 remove decimal part
    """
    if isfloat(values):
        if "." in values and float(values) > 1.0:
            values = values.split(".")[0]
    return values


def create_vcf_header(input_path, config, sample_list):
    header = []
    header.append("##fileformat=VCFv4.3")
    header.append("##fileDate=%s" % time.strftime("%d/%m/%Y"))
    header.append("##source=" + config["GENERAL"]["origin"])
    header.append("##InputFile=%s" % os.path.abspath(input_path))

    # TODO: FILTER is not present in any tool implemented yet
    # so all variants are set to PASS
    if config["VCF_COLUMNS"]["FILTER"] != "":
        raise ValueError(
            "Filters are not implemented yet. "
            'Leave config["COLUMNS_DESCRIPTION"]["FILTER"] empty '
            "or whip the developer until he does it."
            "If you are trying to convert an annotSV file, "
            'use "annotsv" in the input file format argument'
        )
    header.append('##FILTER=<ID=PASS,Description="Passed filter">')

    if "ALT" in config["COLUMNS_DESCRIPTION"]:
        for key, desc in config["COLUMNS_DESCRIPTION"]["ALT"].items():
            header.append("##ALT=<ID=" + key + ',Description="' + desc + '">')
    if "INFO" in config["COLUMNS_DESCRIPTION"]:
        for key, dic in config["COLUMNS_DESCRIPTION"]["INFO"].items():
            header.append(
                "##INFO=<ID="
                + key
                + ",Number=1,Type="
                + dic["Type"]
                + ',Description="'
                + dic["Description"]
                + '">'
            )
    if "FORMAT" in config["COLUMNS_DESCRIPTION"]:
        for key, dic in config["COLUMNS_DESCRIPTION"]["FORMAT"].items():
            header.append(
                "##FORMAT=<ID="
                + key
                + ",Number=1,Type="
                + dic["Type"]
                + ',Description="'
                + dic["Description"]
                + '">'
            )

    header += config["GENOME"]["vcf_header"]
    header.append(
        "\t".join(
            ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT"]
            + sample_list
        )
    )
    return header


if __name__ == "__main__":
    pass
