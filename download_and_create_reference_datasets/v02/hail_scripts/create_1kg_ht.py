import logging

import hail as hl

from hail_scripts.v02.utils.hail_utils import import_vcf

logger = logging.getLogger('v02.hail_scripts.create_1kg_ht')

CONFIG= {
    "38": "gs://seqr-reference-data/GRCh38/1kg/1kg.wgs.phase3.20170504.GRCh38_sites.vcf.gz"
}

def vcf_to_mt(path, genome_version):
    '''
    Converts 1kg vcf to mt. The 1kg dataset has multi-allelic variants and duplicates.
    This function independently filters the mutli-allelics to split, then unions with
    the bi-allelics.

    :param path: vcf path
    :param genome_version: genome version
    :return:
    '''
    # Import but do not split multis here.
    mt = import_vcf(path,
                    genome_version=genome_version,
                    min_partitions=1000,
                    split_multi_alleles=False)

    multiallelic_mt = mt.filter_rows(hl.len(mt.alleles) > 2)
    multiallelic_mt = hl.split_multi_hts(multiallelic_mt)

    # We annotate some rows manually to conform to the multiallelic_mt (after split).
    # Calling split_multi_hts on biallelic to annotate the rows causes problems.
    biallelic_mt = mt.filter_rows(hl.len(mt.alleles) == 2)
    biallelic_mt = biallelic_mt.annotate_rows(a_index=1, was_split=False)

    all_mt = biallelic_mt.union_rows(multiallelic_mt)
    all_mt = all_mt.key_rows_by(all_mt.locus, all_mt.alleles)
    return all_mt


def run():
   for genome_version, path in CONFIG.items():
       logger.info('reading from input path: %s' % path)
       mt = vcf_to_mt(path, genome_version)

       mt.describe()
       mt.rows().show()

       output_path = path.replace(".vcf", "").replace(".gz", "").replace(".bgz", "")\
                         .replace(".*", "").replace("*", "") + ".ht"
       logger.info('writing to output path: %s' % output_path)
       mt.rows().write(output_path)

run()
