# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function

from commons import get_genome


class HelperFunctions:
    """
    For when you can't just convert columns by changing column names
    Steps needed:
    - define the helper function
    - update self.dispatcher so this class can redirect to the proper function
    - tell the config file you want to use a HELPER_FUNCTION with the following pattern:
            [HELPER_FUNCTION, <name of your function>, <arg1>, <arg2>, ..., <argN>]

    Example: I need a LENGTH value in my destination format,
    but my source file only has START and END columns.
    You would need:
    # somewhere in the module
            def get_length(start, end):
                    return str(end - start)
    #in this class __init__():
            self.dispatcher["get_length_from_special_format"]: get_length
    # in the JSON configfile
            LENGTH: [HELPER_FUNCTION, "get_length_from_special_format", START, END]
    """

    def __init__(self, config):
        self.config = config
        self.dispatcher = {
            "get_ref_from_decon": self.get_ref_from_decon,
            "get_alt_from_decon": self.get_alt_from_decon,
            "get_svlen_from_decon": self.get_svlen_from_decon,
            "get_info_from_annotsv": self.get_info_from_annotsv,
            "get_ref_from_canoes_bed": self.get_ref_from_canoes_bed,
            "get_alt_from_canoes_bed": self.get_alt_from_canoes_bed,
            "get_ref_from_tsv": self.get_ref_from_tsv,
            "get_alt_from_tsv": self.get_alt_from_tsv,
            "get_gt_from_zygosity": self.get_gt_from_zygosity,
            "get_pos": self.get_pos,
            "calc_vaf": self.calc_vaf,
        }

    def calc_vaf(self, alleledepth, depth):
        return str(float(alleledepth) / float(depth))

    def get_pos(self, start, ref, alt):
        if ref == "-":
            return start
        elif alt == "-":
            return str(int(start) - 1)
        else:
            return start

    def get_gt_from_zygosity(HomHet):
        if HomHet == "Het":
            return "0/1"
        else:
            return "1/1"

    def get_ref_from_tsv(self, chr, start, ref, alt):
        f = get_genome(self.config["GENOME"]["path"])
        # Del
        if len(ref) > 1:
            return (f[str(chr)][int(start) - 2] + ref).upper()
        # INS
        elif ref == "-":
            return f[str(chr)][int(start) - 1].upper()
        # DEL one base doesn't care
        elif len(ref) == 1 and len(alt) == 1 and alt == "-":
            return (f[str(chr)][int(start) - 2] + ref).upper()
        # SNV
        else:
            return ref.upper()

    def get_alt_from_tsv(self, chr, start, ref, alt):
        f = get_genome(self.config["GENOME"]["path"])
        # INS
        if len(alt) > 1:
            return (f[str(chr)][int(start) - 1] + alt).upper()
        # DEL
        elif alt == "-":
            return f[str(chr)][int(start) - 2].upper()
        # SNV
        else:
            return alt

    def get(self, func_name):
        return self.dispatcher[func_name]

    def get_ref_from_decon(self, chr, start):
        f = get_genome(self.config["GENOME"]["path"])
        return f[chr][int(start) - 1]

    def get_ref_from_canoes_bed(self, chr, start):
        f = get_genome(self.config["GENOME"]["path"])
        return f["chr" + str(chr)][int(start) - 1]

    @staticmethod
    def get_alt_from_decon(cnv_type_field):
        if cnv_type_field == "deletion":
            return "<DEL>"
        if cnv_type_field == "duplication":
            return "<DUP>"
        raise ValueError("Unexpected CNV.type value:" + str(cnv_type_field))

    @staticmethod
    def get_alt_from_canoes_bed(cnv_type_field):
        if cnv_type_field == "DEL":
            return "<DEL>"
        if cnv_type_field == "DUP":
            return "<DUP>"
        raise ValueError("Unexpected CNV.type value:" + str(cnv_type_field))

    @staticmethod
    def get_svlen_from_decon(start, end):
        return str(int(end) - int(start))

    @staticmethod
    def get_info_from_annotsv(info):
        """
        only used in attempts to convert annotsv files
        as if they were generic TSV (not recommended)
        """
        return "."


if __name__ == "__main__":
    pass
