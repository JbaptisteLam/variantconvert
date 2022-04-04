# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function

import logging as log
import os
import pandas as pd
import re
import sys
import time

from converters.abstract_converter import AbstractConverter

sys.path.append("..")
from commons import clean_string, varank_to_vcf_coords
from helper_functions import HelperFunctions


class VcfFromVarank(AbstractConverter):
    """
    TODO: update vcffromvarank.py to fit the interface and import it instead
    """

    def _init_dataframe(self, filepath):
        self.filepath = filepath
        self.df = pd.read_csv(
            filepath,
            skiprows=self.config["GENERAL"]["skip_rows"],
            sep="\t",
            low_memory=False,
        )
        self.df.sort_values(
            [self.config["VCF_COLUMNS"]["#CHROM"], self.config["VCF_COLUMNS"]["POS"]],
            inplace=True,
        )
        self.df.reset_index(drop=True, inplace=True)
        # print(self.df)

    def get_sample_name(self, varank_tsv):
        # with open(varank_file, 'r') as f:
        # next(f)
        # name = f.readline()
        # if not name.startswith("## FamilyBarcode: "):
        # raise ValueError("Couldn't find FamilyBarcode in 2nd line of header. File causing issue: " + varank_file)
        # name = name.split("## FamilyBarcode: ")[1].strip()
        # return name
        name = os.path.basename(varank_tsv)
        name = re.sub("^fam[0-9]*_", "", name)
        for end in self.config["GENERAL"]["varank_filename_ends"]:
            if name.endswith(end):
                return name.split(end)[0]
        raise ValueError(
            "Couldn't determine sample name from varank filename:" + varank_tsv
        )

    def set_coord_conversion_file(self, coord_conversion_file):
        self.coord_conversion_file = coord_conversion_file

    def get_known_columns(self):
        """
        TODO: load self.config[VCF_COLUMNS] instead and flatten it with https://stackoverflow.com/a/31439438
        """
        known = ["chr", "start", "end", "ref", "alt"]
        known.append("QUALphread")  # QUAL
        known.append("zygosity")  # GT
        known.append("totalRead")  # DP
        known.append("varReadDepth")  # AD[1] ; AD[0] = DP - AD[1]
        known.append("varReadPercent")  # VAF
        # No GQ, no PL, and apparently no multi allelic variants
        return known

    def convert(self, varank_tsv, output_path):
        log.info("Converting to vcf from varank using config: " + self.config_filepath)
        id_to_coords = varank_to_vcf_coords(self.coord_conversion_file)
        self.sample_name = self.get_sample_name(varank_tsv)
        self._init_dataframe(varank_tsv)

        with open(output_path, "w") as vcf:
            vcf_header = self.create_vcf_header()
            for l in vcf_header:
                vcf.write(l + "\n")

            data = self.df.fillna(".").astype(str).to_dict()
            # "#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT", self.sample_name]
            for i in range(len(data["variantID"])):
                line = id_to_coords[data["variantID"][i]]["#CHROM"] + "\t"
                line += id_to_coords[data["variantID"][i]]["POS"] + "\t"
                line += data[self.config["VCF_COLUMNS"]["ID"]][i] + "\t"
                line += id_to_coords[data["variantID"][i]]["REF"] + "\t"
                line += id_to_coords[data["variantID"][i]]["ALT"] + "\t"
                line += data[self.config["VCF_COLUMNS"]["QUAL"]][i] + "\t"
                line += "PASS\t"

                info_field = []
                for key in data.keys():
                    if key not in self.get_known_columns():
                        s = key + "=" + data[key][i]
                        s = clean_string(s)
                        info_field.append(s)
                line += ";".join(info_field) + "\t"

                line += "GT:DP:AD:VAF\t"
                gt_dic = {"hom": "1/1", "het": "0/1"}
                sample_field = (
                    gt_dic[data[self.config["VCF_COLUMNS"]["FORMAT"]["GT"]][i]] + ":"
                )
                sample_field += (
                    data[self.config["VCF_COLUMNS"]["FORMAT"]["DP"]][i] + ":"
                )
                sample_field += (
                    str(int(data["totalReadDepth"][i]) - int(data["varReadDepth"][i]))
                    + ","
                    + data["varReadDepth"][i]
                    + ":"
                )
                vaf = data[self.config["VCF_COLUMNS"]["FORMAT"]["VAF"]][i]
                if vaf != ".":
                    vaf = str(int(float(vaf) / 100))
                sample_field += vaf
                line += sample_field

                vcf.write(line + "\n")

        # print("Wrote: "+ output_filepath)

    def create_vcf_header(self):
        header = []
        # basics
        header.append("##fileformat=VCFv4.3")
        header.append("##fileDate=%s" % time.strftime("%d/%m/%Y"))
        header.append("##source=" + self.config["GENERAL"]["origin"])
        header.append("##InputFile=%s" % os.path.abspath(self.filepath))
        # FILTER is not present in Varank, so all variants are set to PASS
        header.append('##FILTER=<ID=PASS,Description="Passed filter">')
        # INFO contains all columns that are not used anywhere specific
        # print(dict(self.df.dtypes))
        for key in self.df.columns:
            if key in self.get_known_columns():
                continue
            if str(self.df[key].dtypes) in ("object", "O", "bool"):
                info_type = "String"
            elif str(self.df[key].dtypes) == "float64":
                info_type = "Float"
            elif str(self.df[key].dtypes) == "int64":
                info_type = "Integer"
            else:
                raise ValueError(
                    "Unrecognized type in Varank dataframe. Column causing issue: "
                    + key
                )
            if key in self.config["COLUMNS_DESCRIPTION"]:
                description = self.config["COLUMNS_DESCRIPTION"][key]
            else:
                description = "Extracted from " + self.config["GENERAL"]["origin"]
                info_type = "String"  # ugly fix of that bug where bcftools change POOL_ columns to Float (--> cutevariant crash)
            header.append(
                "##INFO=<ID="
                + key
                + ",Number=1,Type="
                + info_type
                + ',Description="'
                + description
                + '">'
            )
        # FORMAT
        header.append(
            '##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths for the ref and alt alleles in the order listed">'
        )
        header.append(
            '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Approximate read depth (reads with MQ=255 or with bad mates are filtered)">'
        )
        header.append('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">')
        header.append(
            '##FORMAT=<ID=VAF,Number=1,Type=Float,Description="VAF Variant Frequency">'
        )
        # genome stuff
        header += self.config["GENOME"]["vcf_header"]
        header.append(
            "\t".join(
                [
                    "#CHROM",
                    "POS",
                    "ID",
                    "REF",
                    "ALT",
                    "QUAL",
                    "FILTER",
                    "INFO",
                    "FORMAT",
                    self.sample_name,
                ]
            )
        )
        return header


if __name__ == "__main__":
    pass
