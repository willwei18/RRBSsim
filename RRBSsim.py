# !/usr/bin/env python
# !/usr/bin/python
# -*- coding:utf-8 -*-

# =============================================================================================================
#
# FILE:  simRRBS.py
#
#        USAGE:  ./simRRBS.py
#
#  DESCRIPTION:  simRRBS: reduced representation bisulfite sequencing simulator for next-generation sequencing
#
#      OPTIONS:  ---
# REQUIREMENTS:  ---
#         BUGS:  ---
#        NOTES:  It is modified from the software BSSim,thanks for their source codes.
#       AUTHOR:  Xiwei Sun, xwsun@zju.edu.cn
#      COMPANY:  ZJU
#      VERSION:  1.0
#      CREATED:  2017/6/2
#     REVISION:  ---
# ==========================================  ===================================================================
import time
import os
import sys
import random
import pyfasta
from collections import defaultdict
import getopt
import re


def read_fa(fa_file):  # Reader users input fasta files
    from pyfasta import Fasta
    fa = Fasta(fa_file)
    return fa


def read_path(path):
    # Read all the *.fa file from the Path and return the dict like from single file
    from pyfasta import Fasta

    fa = {}
    for root, dirs, files in os.walk(path):
        for fn in files:
            if fn.endswith('fa'):
                fa_file = root + fn
                fa_chr = Fasta(fa_file)
                fa.update(fa_chr)
        return fa


def read_dbsnp(dbsnpfile):
    # read dbsnpfile and create database.
    f = open(dbsnpfile, 'r')
    max_len = 0
    dbsnp = defaultdict(int)
    while f:
        line = f.readline().rstrip("\n")
        if len(line) == 0:  # Zero length indicates EOF
            break
        line = line.split('\t')
        chrom = line[0]
        k = str(line[1])
        if line[2] == "-":
            dbsnp[chrom, k] = line[4] + "\t" + line[3] + "\t" + line[6] + "\t" + line[5]
        else:
            dbsnp[chrom, k] = line[3] + "\t" + line[4] + "\t" + line[5] + "\t" + line[6]
    f.close()  # close the file
    return dbsnp


# randomly introducing snp in the reference sequence for the single strand
def random_snp(fa, p1, p2, DS, Polyploid, seed):
    if seed:
        random.seed(seed)
    if Polyploid == 1:
        p2 = 0
    p0 = 1 - p1 - p2  # don't have SNP
    tmp = "".join(fa)
    tmp = tmp.upper()
    ref = ['A'] * len(tmp)
    snp_state = [0] * len(tmp)  # 0 is not snp, 1 is snp in '+', -1 is snp in '-'
    for i in range(0, len(tmp)):
        ref[i] = tmp[i]
        ref[i] = re.sub(r'N', random.choice('A'), tmp[i])  # use another random deoxyribo_nucleotide replace 'N'
    del tmp
    if not DS:
        for i in range(0, len(ref)):
            if random.random() > p0:  # have SNP
                snp_state[i] = 1  # homozygote
                if random.random() <= p1 / (p1 + p2):
                    if ref[i] == 'A':
                        if random.random() <= 4 / 6.0:
                            ref[i] = 'G'
                        else:
                            if random.random() <= 0.5:
                                ref[i] = 'C'
                            else:
                                ref[i] = 'T'
                    elif ref[i] == 'G':
                        if random.random() <= 4 / 6.0:
                            ref[i] = 'A'
                        else:
                            if random.random() <= 0.5:
                                ref[i] = 'C'
                            else:
                                ref[i] = 'T'
                    elif ref[i] == 'C':
                        if random.random() <= 4 / 6.0:
                            ref[i] = 'T'
                        else:
                            if random.random() <= 0.5:
                                ref[i] = 'A'
                            else:
                                ref[i] = 'G'
                    elif ref[i] == 'T':
                        if random.random() <= 4 / 6.0:
                            ref[i] = 'C'
                        else:
                            if random.random() <= 0.5:
                                ref[i] = 'A'
                            else:
                                ref[i] = 'G'
                else:  # heterozygote
                    # print "333333333\t heterozygote \t%d\t%s" % (i,ref[i])
                    ref[i] = 'N'
    ref = "".join(ref)
    return snp_state, ref


#  introducing snp in the reference sequence from the user specified file for both strands
def input_snp(fa, chrom, dbsnp, DS, seed):  # DS do not add snp
    if seed:
        random.seed(seed)
    tmp = "".join(fa)
    tmp = tmp.upper()
    ref = ['A'] * len(tmp)
    snp_state = [0] * len(tmp)  # 0 is not snp, 1 is snp in '+', -1 is snp in '-',2 is in both
    for i in range(0, len(tmp)):
        ref[i] = tmp[i]
        ref[i] = re.sub(r'N', random.choice('A'), tmp[i])  # use another random deoxyribo_nucleotide replace 'N'
    del tmp
    ref = "".join(ref)
    if not DS:
        for i in range(0, len(ref)):
            if dbsnp[chrom, i]:
                snp_state[i] = 1
                snp = dbsnp.split("\t")
                r = random.random()
                if r <= snp[0]:
                    ref[i] = "A"
                elif snp[0] < r <= (snp[0] + snp[1]):
                    ref[i] = "T"
                elif (snp[0] + snp[1]) < r <= (snp[0] + snp[1] + snp[2]):
                    ref[i] = "C"
                elif (snp[0] + snp[1] + snp[2]) < r <= (snp[0] + snp[1] + snp[2] + snp[3]):
                    ref[i] = "G"
    ref = "".join(ref)
    return snp_state, ref


# specify methylated level(C to T possibility ) and methylated pattern for each methylated cytosine
def methyl(ref, conversion_rate, CG_conversion_rate, CHG_conversion_rate, CHH_conversion_rate, mC_rate, mCG_rate,
           mCHG_rate, mCHH_rate, CG_beta_distribution, mCG_mu, mCG_sigma, CHG_beta_distribution, mCHG_mu, mCHG_sigma,
           CHH_beta_distribution, mCHH_mu, mCHH_sigma, seed):
    if seed:
        random.seed(seed)
    ref_rate = [0] * len(ref)
    ref_pattern = [""] * len(ref)
    for j in range(0, len(ref)):
        if ref[j] == 'C':
            if (len(ref) - j) < 3:
                ref_rate[j] = conversion_rate
                continue
            if ref[j + 1] == 'G':  # CG
                ref_pattern[j] = "CG"
                if random.random() <= mCG_rate:
                    ref_rate[j] = (1 - ref_methyl_rate('CG', CG_beta_distribution, mCG_mu,
                                                       mCG_sigma)) * CG_conversion_rate  # methylated site
                else:
                    ref_rate[j] = CG_conversion_rate  # not methylated site
            else:
                if ref[j + 2] == 'G':  # CHG
                    ref_pattern[j] = "CHG"
                    if random.random() <= mCHG_rate:
                        ref_rate[j] = (1 - ref_methyl_rate('CHG', CHG_beta_distribution, mCHG_mu,
                                                           mCHG_sigma)) * CHG_conversion_rate
                    else:
                        ref_rate[j] = CHG_conversion_rate
                else:
                    ref_pattern[j] = "CHH"
                    if random.random() <= mCHH_rate:  # CHH
                        ref_rate[j] = (1 - ref_methyl_rate('CHH', CHH_beta_distribution, mCHH_mu,
                                                           mCHH_sigma)) * CHH_conversion_rate
                    else:
                        ref_rate[j] = CHH_conversion_rate
        elif ref[j] == 'G':
            if j < 2:
                ref_rate[j] = conversion_rate
                continue
            if ref[j - 1] == 'C':  # CG
                ref_pattern[j] = "CG"
                if random.random() <= mCG_rate:
                    ref_rate[j] = (1 - ref_methyl_rate('CG', CG_beta_distribution, mCG_mu,
                                                       mCG_sigma)) * CG_conversion_rate
                else:
                    ref_rate[j] = CG_conversion_rate
            else:
                if ref[j - 2] == 'C':  # CHG
                    ref_pattern[j] = "CHG"
                    if random.random() <= mCHG_rate:
                        ref_rate[j] = (1 - ref_methyl_rate('CHG', CHG_beta_distribution, mCHG_mu,
                                                           mCHG_sigma)) * CHG_conversion_rate
                    else:
                        ref_rate[j] = CHG_conversion_rate
                else:
                    ref_pattern[j] = "CHH"
                    if random.random() <= mCHH_rate:  # CHH
                        ref_rate[j] = (1 - ref_methyl_rate('CHH', CHH_beta_distribution, mCHH_mu,
                                                           mCHH_sigma)) * CHH_conversion_rate
                    else:
                        ref_rate[j] = CHH_conversion_rate
        else:
            ref_rate[j] = 0
            ref_pattern[j] = ""
    return ref_rate, ref_pattern


def ref_methyl_rate(mc, beta_distribution, mu, sigma):
    i = 1
    if mc == 'CG':
        while i:
            if beta_distribution:
                k = beta_fun(mu, sigma)
            else:
                k = random.gauss(1.696, 0.3761)
            if 0 < k <= 1:
                return k

    elif mc == 'CHG':
        while i:
            if beta_distribution:
                k = beta_fun(mu, sigma)
            else:
                k = random.gauss(-0.3255, 0.1995)
            if 0 < k <= 1:
                return k
    elif mc == 'CHH':
        while i:
            if beta_distribution:
                k = beta_fun(mu, sigma)
                if 0 < k <= 1:
                    return k
            else:
                if random.random() <= 0.9091:
                    k = random.gauss(-0.3994, 0.2396)
                    if 0 < k <= 0.75:
                        return k
                    else:
                        k = random.gauss(2.669, 0.6518)
                        if 0.75 < k <= 1:
                            return k


def beta_fun(mu, sigma):
    k = mu * (1 - mu) / sigma - 1
    alpha = mu * k
    beta = (1 - mu) * k
    # print "mu%f\t sigma %f\t alpha %f\t beta %f\n" % (mu,sigma,alpha,beta)
    return random.betavariate(alpha, beta)


# specify (C to T possibility ) for each methylated cytosine in adapters ; methylated level of cytosine in adapters is 1
def methyl_adapter(adapter, meth_adapter, conversion_rate, CG_conversion_rate, CHG_conversion_rate,
                   CHH_conversion_rate):
    adapter_rate = [0] * len(adapter)
    if not meth_adapter:
        for j in range(0, len(adapter)):
            if adapter[j] == 'C':
                if (len(adapter) - j) < 3:
                    adapter_rate[j] = conversion_rate
                    continue
                if adapter[j + 1] == 'G':
                    adapter_rate[j] = CG_conversion_rate
                else:
                    if adapter[j + 2] == 'G':
                        adapter_rate[j] = CHG_conversion_rate
                    else:
                        adapter_rate[j] = CHH_conversion_rate

            elif adapter[j] == 'G':
                if j < 2:
                    adapter_rate[j] = conversion_rate
                    continue
                if adapter[j - 1] == 'C':
                    adapter_rate[j] = CG_conversion_rate
                else:
                    if adapter[j - 2] == 'C':
                        adapter_rate[j] = CHG_conversion_rate
                    else:
                        adapter_rate[j] = CHH_conversion_rate

            else:
                adapter_rate[j] = 0
            if (adapter[j] == 'A' or adapter[j] == 'T') and adapter_rate[j] > 0:
                print("%d\t%s\t%s" % (j, adapter[j], adapter_rate[j]))
    return adapter_rate


def create_reads(paired_end, directional, ref_start, ref, rate, start, reads_length, max_err):
    reads1T = [""] * reads_length
    reads2T = [""] * reads_length
    reads1B = [""] * reads_length
    reads2B = [""] * reads_length

    ref1T = [""] * len(ref)
    #ref2T = [""] * len(ref)
    ref1B = [""] * len(ref)
    #ref2B = [""] * len(ref)
    strand1T = '+.W'								# OT
    start1T = start + 1
    end1T = start + reads_length
    strand2T = '-.W'								# CTOT
    start2T = start+len(ref) - reads_length+1
    end2T = start+len(ref)
    strand2B = '+.C'								# CTOB
    start2B = start + 1
    end2B = start + reads_length
    strand1B = '-.C'								# OB
    start1B = start + len(ref) - reads_length + 1
    end1B = start + len(ref)


    # bisulfite converted the watson strand (OT)
    for i in range(0, len(ref)):
        if rate[i] == 0:
            ref1T[i] = ref[i]
        else:
            if ref[i] == 'C':
                if random.random() <= rate[i]:
                    ref1T[i] = 'T'
                else:
                    ref1T[i] = 'C'
            elif ref[i] == 'G':
                    ref1T[i] = 'G'
            else:
                print("11111\t%d\t%s\t%s" % (i, ref[i], rate[i]))
            # bisulfite converted the crick strand(OB)
    for i in range((len(ref) - 1), -1, -1):
        if rate[i] == 0:
            ref1B[len(ref) - 1 - i] = reverse_base(ref[i])
        else:
            if ref[i] == 'G':
                if random.random() <= rate[i]:
                    ref1B[len(ref) - 1 - i] = 'T'
                else:
                    ref1B[len(ref) - 1 - i] = 'C'
            elif ref[i] == 'C':
                ref1B[len(ref) - 1 - i] = 'G'
            else:
                print("44444\t%d\t%s\t%s" % (i, ref[i], rate[i]))
     # the complement strand of OT(CTOT)
    ref2T = reverse_complement(ref1T)
    # the complement strand of OB(CTOB)
    ref2B = reverse_complement(ref1B)

    reads1T = ref1T[0:reads_length]
    if paired_end or (not paired_end and not directional):
        reads1B = ref1B[0:reads_length]

    if max_err == 0:
        error = 0
    else:
        error = random.randrange(0, max_err)
    for i in range(len(reads1T) - 1, len(reads1T) - 1 - error, -1):
        reads1T[i] = random.choice("ATCG")
    for i in range(len(reads1B) - 1, len(reads1B) - 1 - error, -1):
        reads1B[i] = random.choice("ATCG")
    if directional:
        reads1 = "".join(reads1T)
        strand1 = strand1T
        start1 = start1T
        end1 = end1T
        if paired_end:
            reads2 = "".join(reads1B)
            strand2 = strand1B
            start2 = start1B
            end2 = end1B
    else:
        if random.random() <= 0.5:
            reads1 = "".join(reads1T)
            strand1 = strand1T
            start1 = start1T
            end1 = end1T
            if paired_end:
                reads2T = ref2T[0:reads_length]
                for i in range(len(reads2T) - 1, len(reads2T) - 1 - error, -1):
                        reads2T[i] = random.choice("ATCG")
                reads2 = "".join(reads2T)
                strand2 = strand2T
                start2 = start2T
                end2 = end2T
        else:
            reads1 = "".join(reads1B)
            strand1 = strand1B
            start1 = start1B
            end1 = end1B
            if paired_end:
                reads2B = ref2B[0:reads_length]
                for i in range(len(reads2B) - 1, len(reads2B) - 1 - error, -1):
                    reads2B[i] = random.choice("ATCG")
                reads2 = "".join(reads2B)
                strand2 = strand2B
                start2 = start2B
                end2 = end2B
    # print "%d\t%d" % (start1 , start2)
    if paired_end:
        return reads1, strand1, start1 + ref_start, end1 + ref_start, reads2, strand2, start2 + ref_start, end2 + ref_start
    else:
        return reads1, strand1, start1 + ref_start, end1 + ref_start


def create_reads_contain_adapter(paired_end, directional, ref_start, adapter1, adapter2, rate_adapter1,
                                 rate_adapter2, seq_fragment, rate_fragment, fragment_start, reads_length, max_err):
    reads1T_tmp = [""] * len(seq_fragment)
    reads2T_tmp = [""] * len(seq_fragment)
    reads1B_tmp = [""] * len(seq_fragment)
    reads2B_tmp = [""] * len(seq_fragment)
    strand1T = '+.W'								# OT we only tell the position of start, of end in the reference, not contain the adapter sequence
    start1T = fragment_start + 1
    end1T = fragment_start + len(seq_fragment)
    strand2T = '-.W'								# CTOT
    start2T = fragment_start  + 1
    end2T = fragment_start + len(seq_fragment)
    strand2B = '+.C'								# CTOB
    start2B = fragment_start + 1
    end2B = fragment_start + len(seq_fragment)
    strand1B = '-.C'								# OB
    start1B = fragment_start + 1
    end1B = fragment_start + len(seq_fragment)
    if max_err == 0:
        error = 0
    else:
        error = random.randrange(0, max_err)
# A-tailing
    adapter1 += 'T'
    rate_adapter1.append(0)
    adapter2 = 'A' + adapter2
    rate_adapter2.insert(0, 0)

# bisulfite converted the watson strand (OT)
    for i in range(0, len(seq_fragment)):
        if rate_fragment[i] == 0:
            reads1T_tmp[i] = seq_fragment[i]
        else:
            if seq_fragment[i] == 'C':
                if random.random() <= rate_fragment[i]:
                    reads1T_tmp[i] = 'T'
                else:
                    reads1T_tmp[i] = 'C'
            elif seq_fragment[i] == 'G':
                reads1T_tmp[i] = 'G'
            else:
                print("11111\t%d\t%s\t%s" % (i, seq_fragment[i], rate_fragment[i]))
# bisulfite converted the crick strand(OB)
    for i in range((len(seq_fragment) - 1), -1, -1):
        if rate_fragment[i] == 0:
            reads1B_tmp[len(seq_fragment) - 1 - i] = reverse_base(seq_fragment[i])
        else:
            if seq_fragment[i] == 'G':
                if random.random() <= rate_fragment[i]:
                    reads1B_tmp[len(seq_fragment) - 1 - i] = 'T'
                else:
                    reads1B_tmp[len(seq_fragment) - 1 - i] = 'C'
            elif seq_fragment[i] == 'C':
                reads1B_tmp[len(seq_fragment) - 1 - i] = 'G'
            else:
                print("44444\t%d\t%s\t%s" % (i, seq_fragment[i], rate_fragment[i]))
# the complement strand of OT(CTOT)
    reads2T_tmp = reverse_complement(reads1T_tmp)
# the complement strand of OB(CTOB)
    reads2B_tmp = reverse_complement(reads1B_tmp)
# add adapter sequence to strands
    if not paired_end:  # single end reads; only one adapter
        adapter1_length = len(adapter1)
        add_length = reads_length - len(seq_fragment)  # including A-tailing base
        if add_length > adapter1_length:
            add_length = adapter1_length  # if read length is longer then (adapter + seq_fragment),only obtain(adapter + seq_fragment)
        # OT
        for i in range(0, add_length):
            if rate_adapter1[i] == 0:
                reads1T_tmp.append(adapter1[i])
            else:
                if adapter1[i] == 'C':
                    if random.random() <= rate_adapter1[i]:
                        reads1T_tmp.append('T')
                    else:
                        reads1T_tmp.append('C')
                elif adapter1[i] == 'G':
                    reads1T_tmp.append('G')
                else:
                     print("11111\t%d\t%s\t%s" % (i, adapter1[i], rate_adapter1[i]))
        # OB
        for i in range(len(adapter1) - 1, len(adapter1) - add_length - 1, -1):
            if rate_adapter1[i] == 0:
                reads1B_tmp.append(reverse_base(adapter1[i]))
            else:
                if adapter1[i] == 'G':
                    if random.random() <= rate_adapter1[i]:
                        reads1B_tmp.append('T')
                    else:
                        reads1B_tmp.append('C')
                elif adapter1[i] == 'C':
                    reads1B_tmp.append('G')
                else:
                    print("11111\t%d\t%s\t%s" % (i, adapter1[i], rate_adapter1[i]))
        for i in range(len(reads1T_tmp) - 1, len(reads1T_tmp) - 1 - error, -1):
            reads1T_tmp[i] = random.choice("ATCG")
        for i in range(len(reads1B_tmp) - 1, len(reads1B_tmp) - 1 - error, -1):
            reads1B_tmp[i] = random.choice("ATCG")

        if directional:
            reads1 = "".join(reads1T_tmp)
            strand1 = strand1T
            start1 = start1T
            end1 = end1T
        else:
            if random.random() <= 0.5:
                reads1 = "".join(reads1T_tmp)
                strand1 = strand1T
                start1 = start1T
                end1 = end1T
            else:
                reads1 = "".join(reads1B_tmp)
                strand1 = strand1B
                start1 = start1B
                end1 = end1B
    else:  # paired-end ; two different adapters
        adapter1_length = len(adapter1)
        adapter2_length = len(adapter2)
        add_length1 = reads_length - len(seq_fragment)
        add_length2 = reads_length - len(seq_fragment)
        if add_length1 > adapter1_length:
            add_length1 = adapter1_length  # if read length is longer then (adapter + seq_fragment),only obtain(adapter + seq_fragment)
        if add_length2 > adapter2_length:
            add_length2 = adapter2_length  # if read length is longer then (adapter + seq_fragment),only obtain(adapter + seq_fragment)
        # OT
        for i in range(0, add_length2):  # add adapter2
            if rate_adapter2[i] == 0:
                reads1T_tmp.append(adapter2[i])
            else:
                if adapter2[i] == 'C':
                    if random.random() <= rate_adapter2[i]:
                        reads1T_tmp.append('T')
                    else:
                        reads1T_tmp.append('C')
                elif adapter2[i] == 'G':
                    reads1T_tmp.append('G')
                else:
                    print("11111\t%d\t%s\t%s" % (i, adapter2[i], rate_adapter2[i]))
        # OB
        for i in range(len(adapter1) - 1, len(adapter1) - add_length1 - 1, -1):  # add adapter1
            if rate_adapter1[i] == 0:
                reads1B_tmp.append(reverse_base(adapter1[i]))
            else:
                if adapter1[i] == 'G':
                    if random.random() <= rate_adapter1[i]:
                        reads1B_tmp.append('T')
                    else:
                        reads1B_tmp.append('C')
                elif adapter1[i] == 'C':
                    reads1B_tmp.append('G')
                else:
                    print("11111\t%d\t%s\t%s" % (i, adapter1[i], rate_adapter1[i]))
        # CTOT
        for i in range(len(adapter1) - 1, len(adapter1) - add_length1 - 1, -1):  # add adapter1
            if rate_adapter1[i] == 0:
                reads2T_tmp.append(reverse_base(adapter1[i]))
            else:
                if adapter1[i] == 'C':
                    if random.random() <= rate_adapter1[i]:
                        reads2T_tmp.append('A')
                    else:
                        reads2T_tmp.append('G')
                elif adapter1[i] == 'G':
                    reads2T_tmp.append('C')
                else:
                    print("11111\t%d\t%s\t%s" % (i, adapter1[i], rate_adapter1[i]))
        # CTOB
        for i in range(0, add_length2):  # add adapter2
            if rate_adapter2[i] == 0:
                reads2B_tmp.append(adapter2[i])
            else:
                if adapter2[i] == 'G':
                    if random.random() <= rate_adapter2[i]:
                        reads2B_tmp.append('A')
                    else:
                        reads2B_tmp.append('G')
                elif adapter2[i] == 'C':
                    reads2B_tmp.append('C')
                else:
                    print("11111\t%d\t%s\t%s" % (i, adapter2[i], rate_adapter2[i]))
        for i in range(len(reads1T_tmp) - 1, len(reads1T_tmp) - 1 - error, -1):
            reads1T_tmp[i] = random.choice("ATCG")
        for i in range(len(reads1B_tmp) - 1, len(reads1B_tmp) - 1 - error, -1):
            reads1B_tmp[i] = random.choice("ATCG")
        for i in range(len(reads2T_tmp) - 1, len(reads2T_tmp) - 1 - error, -1):
            reads2T_tmp[i] = random.choice("ATCG")
        for i in range(len(reads2B_tmp) - 1, len(reads2B_tmp) - 1 - error, -1):
            reads2B_tmp[i] = random.choice("ATCG")

        if directional:
            reads1 = "".join(reads1T_tmp)
            strand1 = strand1T
            start1 = start1T
            end1 = end1T
            reads2 = "".join(reads1B_tmp)
            strand2 = strand1B
            start2 = start1B
            end2 = end1B
        else:
            if random.random() <= 0.5:
                reads1 = "".join(reads1T_tmp)
                strand1 = strand1T
                start1 = start1T
                end1 = end1T
                reads2 = "".join(reads2T_tmp)
                strand2 = strand2T
                start2 = start2T
                end2 = end2T
            else:
                reads1 = "".join(reads1B_tmp)
                strand1 = strand1B
                start1 = start1B
                end1 = end1B
                reads2 = "".join(reads2B_tmp)
                strand2 = strand2B
                start2 = start2B
                end2 = end2B

    if paired_end:
            return reads1, strand1, start1 + ref_start, end1 + ref_start, reads2, strand2, start2 + ref_start, end2 + ref_start
    else:
        return reads1, strand1, start1 + ref_start, end1 + ref_start


def reverse_complement(seq):
    complement_seq = [""] * len(seq)
    for i in range(len(seq) - 1, -1, -1):
        complement_seq[len(seq) - 1 - i] = reverse_base(seq[i])
   # complement_seq = "".join(complement_seq)
    return complement_seq


def reverse_base(orin):
    if orin == 'A':
        return 'T'
    if orin == 'T':
        return 'A'
    if orin == 'G':
        return 'C'
    if orin == 'C':
        return 'G'


# create reads from RRBS library for input SNP
def create_reads_for_input_or_random_snp(ref, ref_start, cut_site, end_repair_format, enzyme_format, end_repair_bases, rate_end_repair_bases, directional, seed, depth_mu, adapter1,
                               adapter2, rate_adapter1, rate_adapter2, rate, max_err, output_ref, reads_length_mu,
                               reads_length_sigma, SAM, samw, samc, paired_end, fq1, fq2,
                               reads_r1, quals_r1, reads_r2, quals_r2, technology, chrom, out, position, index,
                               qual_mu, qual_sigma, random_sequencing_errors, end_part, end_part_sigma,
                               end_qual, end_qual_sigma, dynamic_qual, input_quals, first_qual_R1, first_qual_R2, matrix_qual_R1, matrix_qual_R2, phred33_quals, phred64_quals):
    # open output file
    FQ1 = FQ2 = READS_R1 = READS_R2 = QUALS_R1 = QUALS_R2 = SAMW = SAMC = ''
    if technology == 'Solexa':
        FQ1 = open(fq1 + '.tmp', 'w')
        if paired_end:
            FQ2 = open(fq2 + '.tmp', 'w')
    if SAM:
        SAMW = open(samw + '.tmp', 'w')
        SAMC = open(samc + '.tmp', 'w')

    repair_cytosine_position = {}

    for site_key, site_position in cut_site.items():
        fragment_start = int(site_position[0])
        fragment_end = int(site_position[1])
        fragment_length = fragment_end - fragment_start + 1

        reads_length = int(random.normalvariate(reads_length_mu, reads_length_sigma))
        reads_depth = int(random.expovariate(1.0 / depth_mu))
        #print(reads_length, reads_depth)
        end_repair_format_each = end_repair_format[site_key]
        enzyme_format_each = enzyme_format[site_key]

        # end bases repairs
        if enzyme_format_each == (1, 1):
            if end_repair_format_each == (1, 2):
                fragment_start = fragment_start
                fragment_end += len(end_repair_bases["enzyme1"])
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'C':
                        rate_fragment[-(len(end_repair_bases["enzyme1"]) - i)] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme1"]) - i))] = '+'
                    elif end_repair_bases["enzyme1"][i] == 'G':
                        rate_fragment[i] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '-'

            elif end_repair_format_each == (2, 1):
                fragment_start -= len(end_repair_bases["enzyme1"])
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'C':
                        rate_fragment[i] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '+'
                    elif end_repair_bases["enzyme1"][i] == 'G':
                        rate_fragment[-(len(end_repair_bases["enzyme1"]) - i)] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme1"]) - i))] = '+'
            elif end_repair_format_each == (0, 0):
                fragment_start = fragment_start
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                rate_fragment = rate[fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
        elif enzyme_format_each == (2, 2):
            if end_repair_format_each == (1, 2):
                fragment_start = fragment_start
                fragment_end += len(end_repair_bases["enzyme2"])
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'C':
                        rate_fragment[-(len(end_repair_bases["enzyme2"]) - i)] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme2"]) - i))] = '+'
                    elif end_repair_bases["enzyme2"][i] == 'G':
                        rate_fragment[i] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '-'
            elif end_repair_format_each == (2, 1):
                fragment_start -= len(end_repair_bases["enzyme1"])
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'C':
                        rate_fragment[i] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '+'
                    elif end_repair_bases["enzyme1"][i] == 'G':
                        rate_fragment[-(len(end_repair_bases["enzyme1"]) - i)] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme1"]) - i))] = '+'
            elif end_repair_format_each == (0, 0):
                fragment_start = fragment_start
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                rate_fragment = rate[fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
        elif enzyme_format_each == (1, 2):
            if end_repair_format_each == (1, 2):
                fragment_start = fragment_start
                fragment_end += len(end_repair_bases["enzyme2"])
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'G':
                        rate_fragment[i] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '-'
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'C':
                        rate_fragment[-(len(end_repair_bases["enzyme2"]) - i)] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme2"]) - i))] = '+'
            elif end_repair_format_each == (1, 1):
                fragment_start = fragment_start
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'G':
                        rate_fragment[i] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '-'
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'G':
                        rate_fragment[-(len(end_repair_bases["enzyme2"]) - i)] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme2"]) - i))] = '-'
            elif end_repair_format_each == (1, 0):
                fragment_start = fragment_start
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'G':
                        rate_fragment[i] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '-'
            elif end_repair_format_each == (2, 2):
                fragment_start -= len(end_repair_bases["enzyme1"])
                fragment_end += len(end_repair_bases["enzyme2"])
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'C':
                        rate_fragment[i] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '+'
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'C':
                        rate_fragment[-(len(end_repair_bases["enzyme2"]) - i)] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme2"]) - i))] = '+'
            elif end_repair_format_each == (2, 1):
                fragment_start -= len(end_repair_bases["enzyme1"])
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'C':
                        rate_fragment[i] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '+'
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'G':
                        rate_fragment[-(len(end_repair_bases["enzyme2"]) - i)] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme2"]) - i))] = '-'
            elif end_repair_format_each == (2, 0):
                fragment_start -= len(end_repair_bases["enzyme1"])
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'C':
                        rate_fragment[i] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '+'
            elif end_repair_format_each == (0, 2):
                fragment_start = fragment_start
                fragment_end += len(end_repair_bases["enzyme2"])
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'C':
                        rate_fragment[-(len(end_repair_bases["enzyme2"]) - i)] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme2"]) - i))] = '+'
            elif end_repair_format_each == (0, 1):
                fragment_start = fragment_start
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'G':
                        rate_fragment[-(len(end_repair_bases["enzyme2"]) - i)] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme2"]) - i))] = '-'
            elif end_repair_format_each == (0, 0):
                fragment_start = fragment_start
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
        elif enzyme_format_each == (2, 1):
            if end_repair_format_each == (1, 2):
                fragment_start = fragment_start
                fragment_end += len(end_repair_bases["enzyme1"])
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'G':
                        rate_fragment[i] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '-'
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'C':
                        rate_fragment[-(len(end_repair_bases["enzyme1"]) - i)] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme1"]) - i))] = '+'
            elif end_repair_format_each == (1, 1):
                fragment_start = fragment_start
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'G':
                        rate_fragment[i] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '-'
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'G':
                        rate_fragment[-(len(end_repair_bases["enzyme1"]) - i)] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme1"]) - i))] = '-'
            elif end_repair_format_each == (1, 0):
                fragment_start = fragment_start
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'G':
                        rate_fragment[i] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '-'
            elif end_repair_format_each == (2, 2):
                fragment_start -= len(end_repair_bases["enzyme2"])
                fragment_end += len(end_repair_bases["enzyme1"])
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'C':
                        rate_fragment[i] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '+'
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'C':
                        rate_fragment[-(len(end_repair_bases["enzyme1"]) - i)] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme1"]) - i))] = '+'
            elif end_repair_format_each == (2, 1):
                fragment_start -= len(end_repair_bases["enzyme2"])
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'C':
                        rate_fragment[i] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '+'
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'G':
                        rate_fragment[-(len(end_repair_bases["enzyme1"]) - i)] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme1"]) - i))] = '-'
            elif end_repair_format_each == (2, 0):
                fragment_start -= len(end_repair_bases["enzyme2"])
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme2"])):
                    if end_repair_bases["enzyme2"][i] == 'C':
                        rate_fragment[i] = rate_end_repair_bases["enzyme2"][i]
                        repair_cytosine_position[(site_key, fragment_start + i)] = '+'
            elif end_repair_format_each == (0, 2):
                fragment_start = fragment_start
                fragment_end += len(end_repair_bases["enzyme1"])
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'C':
                        rate_fragment[-(len(end_repair_bases["enzyme1"]) - i)] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme1"]) - i))] = '+'
            elif end_repair_format_each == (0, 1):
                fragment_start = fragment_start
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]
                for i in range(0, len(end_repair_bases["enzyme1"])):
                    if end_repair_bases["enzyme1"][i] == 'G':
                        rate_fragment[-(len(end_repair_bases["enzyme1"]) - i)] = rate_end_repair_bases["enzyme1"][i]
                        repair_cytosine_position[(site_key, fragment_end + 1 - (len(end_repair_bases["enzyme1"]) - i))] = '-'
            elif end_repair_format_each == (0, 0):
                fragment_start = fragment_start
                fragment_end = fragment_end
                seq_fragment = ref[ref_start + fragment_start:fragment_end + 1]
                seq_fragment = "".join(seq_fragment)
                rate_fragment = rate[fragment_start:fragment_end + 1]

        fragment_length = fragment_end - fragment_start + 1
        if reads_length <= fragment_length:
            for i in range(0, reads_depth):
                if paired_end:
                    (reads1, strand1, start1, end1,
                     reads2, strand2, start2, end2) = create_reads(paired_end, directional, ref_start, seq_fragment,
                                                                   rate_fragment, fragment_start, reads_length, max_err)
                else:
                    (reads1, strand1, start1, end1) = create_reads(paired_end, directional, ref_start, seq_fragment,
                                                                   rate_fragment, fragment_start, reads_length, max_err)
                # output to files
                if paired_end:
                    output(SAM, SAMW, SAMC, paired_end, FQ1, FQ2, READS_R1, QUALS_R1, READS_R2, QUALS_R2, technology, chrom,
                           reads1, strand1, start1, end1, reads2, strand2, start2, end2, out, position, index, qual_mu,
                           qual_sigma, random_sequencing_errors, end_part, end_part_sigma, end_qual, end_qual_sigma, dynamic_qual, input_quals, first_qual_R1, first_qual_R2, matrix_qual_R1, matrix_qual_R2, phred33_quals, phred64_quals)
                else:
                    output(SAM, SAMW, SAMC,paired_end, FQ1, FQ2, READS_R1, QUALS_R1, READS_R2, QUALS_R2, technology, chrom,
                           reads1, strand1, start1, end1, '', '', '', '', out, position, index, qual_mu, qual_sigma,
                           random_sequencing_errors, end_part, end_part_sigma, end_qual, end_qual_sigma, dynamic_qual, input_quals, first_qual_R1, first_qual_R2, matrix_qual_R1, matrix_qual_R2, phred33_quals, phred64_quals)
        else:
            for i in range(0, reads_depth):
                if paired_end:
                    (reads1, strand1, start1, end1,
                     reads2, strand2, start2, end2) =\
                        create_reads_contain_adapter(paired_end, directional, ref_start, adapter1, adapter2,
                                                     rate_adapter1, rate_adapter2, seq_fragment, rate_fragment,
                                                     fragment_start, reads_length, max_err)
                else:
                    (reads1, strand1, start1, end1) = \
                        create_reads_contain_adapter(paired_end, directional, ref_start, adapter1,adapter2,
                                                     rate_adapter1, rate_adapter2, seq_fragment, rate_fragment,
                                                     fragment_start, reads_length, max_err)
                # output to files
                if paired_end:
                    output(SAM, SAMW, SAMC, paired_end, FQ1, FQ2, READS_R1, QUALS_R1, READS_R2, QUALS_R2, technology, chrom,
                           reads1, strand1, start1, end1, reads2, strand2, start2, end2, out, position, index, qual_mu,
                           qual_sigma, random_sequencing_errors, end_part, end_part_sigma, end_qual, end_qual_sigma, dynamic_qual, input_quals, first_qual_R1, first_qual_R2, matrix_qual_R1, matrix_qual_R2, phred33_quals, phred64_quals)
                else:
                    output(SAM, SAMW, SAMC,paired_end, FQ1, FQ2, READS_R1, QUALS_R1, READS_R2, QUALS_R2, technology, chrom,
                           reads1, strand1, start1, end1, '', '', '', '', out, position, index, qual_mu, qual_sigma,
                           random_sequencing_errors, end_part, end_part_sigma, end_qual, end_qual_sigma, dynamic_qual, input_quals, first_qual_R1, first_qual_R2, matrix_qual_R1, matrix_qual_R2, phred33_quals, phred64_quals)
    if technology == 'Solexa':
        FQ1.close()
        SAMW.close()
        SAMC.close()
        if paired_end:
            FQ2.close()


def find_end_repair_bases(cut_site):
    cut_position = cut_site.find('-')
    cut_site_new = cut_site.replace('-', '')
    cut_site_len = len(cut_site_new)
    cut_index = cut_site_len - cut_position - cut_position  # index cutting format; cut_index > 0 top end; cut_index < 0 bottom end; cut_index = 0 blunt end;
    end_repair_bases_len = abs(cut_index)
    if cut_index > 0:
        end_repair_bases = cut_site_new[cut_position:cut_position + end_repair_bases_len]
    elif cut_index < 0:
        end_repair_bases = cut_site_new[cut_position - end_repair_bases_len:cut_position]
    else:
        end_repair_bases = ''
    return cut_index, cut_position, cut_site_new, end_repair_bases


def cut_sequence(ref, ref_start, num_site, cut_seq, cut_index, cut_position, fragment_min, fragment_max):
    cut_site = {}
    end_repair_format = {}
    enzyme_format = {}
    cut_seq1 = str(cut_seq["enzyme1"])
    cut_seq2 = str(cut_seq["enzyme2"])
    i = ref_start
    j = 0

    flag = False
    RRSeq = ''
    if num_site == 1:  # only one enzyme cutting site
        while i < len(ref) - 1:
                start = i
                start = ref.find(cut_seq1, start)
                end = ref.find(cut_seq1, start + 1)
                if end == -1:
                    print("No cutting site has been searched")
                    break
                start_cut = start + cut_position["enzyme1"]
                end_cut = end + cut_position["enzyme1"] - 1
                frag_length = end_cut - start_cut + 1
               # print(frag_length)
                #print( '>', start_cut, end_cut)
                #print(ref[start_cut:end_cut])
                if fragment_min <= frag_length <= fragment_max:
                   # print(start_cut, end_cut)
                    #print(ref[start_cut:end_cut])
                    cut_site[j] = (start_cut, end_cut)
                    enzyme_format[j] = (1, 1)  # The enzyme cutting format of two ends; 1 represent enzyme1, 2 represent enzyme2;
                    if cut_index["enzyme1"] > 0:
                        end_repair_format[j] = (1, 2)  # 0 represent blunt end ; 1 represent top end ; 2 represent bottom end;The first index left ends; The second index right ends;
                    elif cut_index["enzyme1"] < 0:
                        end_repair_format[j] = (2, 1)
                    else:
                        end_repair_format[j] = (0, 0)
                    j += 1
                i = end
    elif num_site == 2:  # Two enzymes cutting site
        while i < len(ref) - 1:
            start = i
            start1 = ref.find(cut_seq1, start)
            start2 = ref.find(cut_seq2, start)

            if start1 <= start2:
                start = start1
                start_cut = start + cut_position["enzyme1"]
                flag_enzyme_left = 1
            else:
                start = start2
                start_cut = start + cut_position["enzyme2"]
                flag_enzyme_left = 2
            end1 = ref.find(cut_seq1, start + 1)
            end2 = ref.find(cut_seq2, start + 1)
            if end1 <= end2:
                end = end1
                end_cut = end + cut_position["enzyme1"]
                flag_enzyme_right = 1
            else:
                end = end2
                end_cut = end + cut_position["enzyme2"]
                flag_enzyme_right = 2
            frag_length = end_cut - start_cut
            if fragment_min <= frag_length <= fragment_max:
                cut_site[j] = (start_cut, end_cut)
                enzyme_format[j] = (flag_enzyme_left, flag_enzyme_right)
                if flag_enzyme_left == 1 and flag_enzyme_right == 1:
                    if cut_index["enzyme1"] > 0:
                        end_repair_format[j] = (1, 2)  # 0 represent blunt end ; 1 represent top end ; 2 represent bottom end;The first index right ends; The second index left ends;
                    elif cut_index["enzyme1"] < 0:
                        end_repair_format[j] = (2, 1)
                    else:
                        end_repair_format[j] = (0, 0)
                elif flag_enzyme_left == 2 and flag_enzyme_right == 2:
                    if cut_index["enzyme2"] > 0:
                        end_repair_format[j] = (1, 2)  # 0 represent blunt end ; 1 represent top end ; 2 represent bottom end;The first index right ends; The second index left ends;
                    elif cut_index["enzyme2"] < 0:
                        end_repair_format[j] = (2, 1)
                    else:
                        end_repair_format[j] = (0, 0)
                elif flag_enzyme_left == 1 and flag_enzyme_right == 2:
                    if cut_index["enzyme1"] > 0:
                        left_format = 1
                    elif cut_index["enzyme1"] < 0:
                        left_format = 2
                    else:
                        left_format = 0
                    if cut_index["enzyme2"] > 0:
                        right_format = 2
                    elif cut_index["enzyme2"] < 0:
                        right_format = 1
                    else:
                        right_format = 0
                    end_repair_format[j] = (left_format, right_format)
                elif flag_enzyme_left == 2 and flag_enzyme_right == 1:
                    if cut_index["enzyme2"] > 0:
                        left_format = 1
                    elif cut_index["enzyme2"] < 0:
                        left_format = 2
                    else:
                        left_format = 0
                    if cut_index["enzyme1"] > 0:
                        right_format = 2
                    elif cut_index["enzyme1"] < 0:
                        right_format = 1
                    else:
                        right_format = 0
                    end_repair_format[j] = (left_format, right_format)
                j += 1
            i = end
    return cut_site, end_repair_format, enzyme_format


def output(SAM, SAMW, SAMC, paired_end, FQ1, FQ2, READS_R1, QUALS_R1, READS_R2, QUALS_R2, technology, chrom, reads1, strand1,
           start1, end1, reads2, strand2, start2, end2, out, position, index, qual_mu, qual_sigma, random_sequencing_errors,
           end_part, end_part_sigma, end_qual, end_qual_sigma, dynamic_qual, input_quals, first_qual_R1, first_qual_R2, matrix_qual_R1, matrix_qual_R2, phred33_quals, phred64_quals):  # add quality values
            if input_quals:
                (reads1, qual1) = input_quality(reads1, random_sequencing_errors, first_qual_R1, matrix_qual_R1, phred33_quals, phred64_quals)
                (reads2, qual2) = input_quality(reads2, random_sequencing_errors, first_qual_R2, matrix_qual_R2, phred33_quals, phred64_quals)

                #(reads1, qual1) = input_base_quality_distribution(reads1, random_sequencing_errors, matrix_qual_R1, phred33_quals, phred64_quals)
                #(reads2, qual2) = input_base_quality_distribution(reads2, random_sequencing_errors,  matrix_qual_R2, phred33_quals, phred64_quals)

            elif dynamic_qual:
                quality = beta_fun(qual_mu, qual_sigma)
                if quality < 0.5:
                    quality = 0.5
                (reads1, qual1) = dynamic_quality(reads1, quality, random_sequencing_errors, end_part, end_part_sigma, end_qual, end_qual_sigma)
                (reads2, qual2) = dynamic_quality(reads2, quality, random_sequencing_errors, end_part, end_part_sigma, end_qual, end_qual_sigma)
            else:
                qual1 = [qual_mu * 40] * len(reads1)
                qual2 = [qual_mu * 40] * len(reads2)
            if technology == 'Solexa':
                output_solexa(SAM, SAMW, SAMC, paired_end, FQ1, qual1, FQ2, qual2, chrom, reads1, strand1, start1, end1, reads2, strand2, start2, end2, out, position, index, phred33_quals, phred64_quals)


def output_solexa(SAM, SAMW, SAMC, paired_end, FQ1, qual1, FQ2, qual2, chrom, reads1, strand1, start1, end1, reads2, strand2, start2, end2, out, position, index, phred33_quals, phred64_quals):
    seq_id = ':1' + ':2102' + ':' + str(random.randint(1, 99999)) + ':' + str(random.randint(1, 99999))
    quality1 = [""] * len(qual1)
    if phred33_quals:
        for i in range(0, len(qual1)):
            quality1[i] = chr(int(qual1[i]) + 33)
    elif phred64_quals:
        for i in range(0, len(qual1)):
            quality1[i] = chr(int(qual1[i]) + 64)
    quality1 = "".join(quality1)
    if position:
        first = chrom + '.' + str(start1) + '-' + str(end1) + '.' + strand1 + str(start2) + '-' + str(end2) + '.' + strand2 + seq_id + '/1'
    else:
        first = 'DF94KKQ1:316:D04NRACXX' + seq_id + ' ' + '1:N:0:' + index
    FQ1.write('@' + first + '\n' + reads1 + '\n' + '+' + '\n' + quality1 + '\n')
    second = quality2 = ''
    if paired_end:
        quality2 = [""] * len(qual2)
        if phred33_quals:
            for i in range(0, len(qual2)):
                quality2[i] = chr(int(qual2[i]) + 33)
        elif phred64_quals:
            for i in range(0, len(qual2)):
                quality2[i] = chr(int(qual2[i]) + 64)
        quality2 = "".join(quality2)
        if position:
            second = chrom + '.' + str(start1) + '-' + str(end1) + '.' + strand1 + str(start2) + '-' + str(end2) + '.' + strand2 + seq_id + '/2'
        else:
            second = 'DF94KKQ1:316:D04NRACXX' + seq_id + ' ' + '2:N:0:' + index
        FQ2.write('@' + second + '\n' + reads2 + '\n' + '+' + '\n' + quality2 + '\n')
        if SAM:
            output_SAM(SAM, SAMW, SAMC, chrom, first, reads1, strand1, start1, end1, qual1, second, reads2, strand2, start2, end2, qual2)


def output_SAM(SAM, samw, samc, chrom, first, reads1, strand1, start1, end1, qual1, first2, reads2, strand2, start2, end2, qual2):
    if reads2:
        if strand1 == '+.W' and strand2 == '-.C':						# PE and directional
            quality1 = quality_sanger(qual1,'')
            samw.write(first + '\t0\t' + chrom + '\t' + str(start1) + '\t0\t' + str(len(reads1)) + 'M\t=\t0\t0\t' + str(reads1) + '\t' + str(quality1) + '\n')
            reads2 = reverse_complement(reads2)
            reads2 = "".join(reads2)
            quality2 = quality_sanger(qual2, True)
            samc.write(first2 + '\t0\t'+ chrom + '\t'+str(start2) + '\t0\t' + str(len(reads2)) + 'M\t=\t0\t0\t' + str(reads2) + '\t' + str(quality2) + '\n')
        if strand1 == '+.W' and strand2 == '-.W':						# PE and Watson
            quality1 = quality_sanger(qual1, '')
            samw.write(first + '\t0\t'+ chrom + '\t' + str(start1) + '\t0\t' + str(len(reads1)) + 'M\t=\t' + str(start2) + '\t' + str(start2 - start1 + len(reads2)) + '\t' + str(reads1) + '\t' + str(quality1) + '\n')
            reads2 = reverse_complement(reads2)
            reads2 = "".join(reads2)
            quality2 = quality_sanger(qual2, True)
            samw.write(first2 + '\t0\t' + chrom + '\t' + str(start2) + '\t0\t' + str(len(reads2)) + 'M\t=\t' + str(start1) + '\t-' + str(start2 - start1 + len(reads2)) + '\t' + str(reads2) + '\t' + str(quality2) + '\n')
        if strand1 == '-.C' and strand2 == '+.C':						# PE and Crick
            quality2 = quality_sanger(qual2, '')
            samc.write(first2 + '\t0\t' + chrom + '\t' + str(start2) + '\t0\t' + str(len(reads2)) + 'M\t=\t' + str(start1) + '\t' + str(start1 - start2 + len(reads2)) + '\t' + str(reads2) + '\t' + str(quality2) + '\n')
            reads1 = reverse_complement(reads1)
            reads1 = "".join(reads1)
            quality1 = quality_sanger(qual1, True)
            samc.write(first + '\t0\t' + chrom + '\t' + str(start1) + '\t0\t' + str(len(reads1))+'M\t=\t' + str(start2) + '\t-' + str(start1 - start2 + len(reads2)) + '\t' + str(reads1) + '\t' + str(quality1) + '\n')
    else:
        if strand1 == '+.W':											# SE and +.Watson
            quality1 = quality_sanger(qual1, '')
            samw.write(first + '\t0\t' + chrom + '\t' + str(start1) + '\t0\t' + str(len(reads1)) + 'M\t=\t0\t0\t' + str(reads1) + '\t' + str(quality1) + '\n')
        if strand1 == '-.W': 										# SE and -.Watson
            reads1 = reverse_complement(reads1)
            quality1 = quality_sanger(qual1, True)
            samw.write(first2 + '\t0\t' + chrom + '\t' + str(start1) + '\t0\t' + str(len(reads1)) + 'M\t=\t0\t0\t' + str(reads1) + '\t' + str(quality1) + '\n')
        if strand1 == '-.C':											# SE and -.Crick
            reads1 = reverse_complement(reads1)
            quality1 = quality_sanger(qual1, True)
            samc.write(first + '\t0\t' + chrom + '\t' + str(start1) + '\t0\t' + str(len(reads1)) + 'M\t=\t0\t0\t' + str(reads1) + '\t' + str(quality1) + '\n')
        if strand1 == '+.C':											# SE and +.Crick
            quality1 = quality_sanger(qual1, '')
            samc.write(first2 + '\t0\t' + chrom + '\t' + str(start1) + '\t0\t' + str(len(reads1)) + 'M\t=\t0\t0\t' + str(reads1) + '\t' + str(quality1) + '\n')


def quality_sanger(qual, reverse):
    quality = [""] * len(qual)
    if reverse:
        for i in range(len(qual) - 1, -1, -1):
            quality[len(qual) - 1 - i] = chr(int(qual[i]) + 33)
    else:
        for i in range(0, len(qual)):
            quality[i] = chr(int(qual[i]) + 33)
    quality = "".join(quality)
    return quality


def input_quality(reads, random_sequencing_errors, first_qual, matrix_qual, phred33_quals, phred64_quals):
    qual_score = []
    # set the  first quality score
    (total_first, first_qual_key, first_qual_value) = read_first_qual_file(first_qual)
    # print(total_first)
    #print(first_qual_key)
    #print(first_qual_value)
    random_int_first = random.randint(1, total_first)
    #print(random_int_first)
    for i in range(0, len(first_qual_key)):
        if first_qual_value[i] >= int(random_int_first):
            qual_score.append(first_qual_key[i])
            last_value = first_qual_key[i]
            #print(last_value)
            break
    # set the next  quality score
    (qual_num, values, qual_dict) = read_matrix_qual_file(matrix_qual)
    # print(qual_num, values)
    for i in range(1, len(reads)):
        qual_dict_score = [0] * 1
        qual_dict_key = ['a'] * 1
        total = 0
        line_qual = qual_dict[str(i), last_value]
        #print(line_qual)
        for j in range(0, len(line_qual)):
            # print(line_qual[j])
            qual = line_qual[j]
            if qual != '0':
                total += int(qual)
                qual_dict_score.append(total)
                qual_dict_key.append(values[j])
        del qual_dict_score[0]
        del qual_dict_key[0]
        if total:
            random_int = random.randint(1, total)
            for k in range(0, len(qual_dict_key)):
                if qual_dict_score[k] >= random_int:
                    qual_score.append(qual_dict_key[k])
                    last_value = qual_dict_key[k]
                    break
        else:
            random_int = random.randint(1, len(values))
            qual_score.append(values[random_int - 1])
            last_value = values[random_int - 1]

    # get new reads based on quality values
    reads_out = [""] * len(reads)
    qual = [''] * len(reads)
    #print(len(qual_score))
    if phred33_quals:
        for i in range(0, len(reads)):
            qual[i] = ord(str(qual_score[i])) - 33
            if random_sequencing_errors and random.random() < sequencing_error_probability(qual[i]):
                reads_out[i] = random.choice("ATCG")
            else:
                reads_out[i] = reads[i]
    elif phred64_quals:
        for i in range(0, len(reads)):
            qual[i] = ord(str(qual_score[i])) - 64
            if random_sequencing_errors and random.random() < sequencing_error_probability(qual[i]):
                reads_out[i] = random.choice("ATCG")
            else:
                reads_out[i] = reads[i]
    reads = "".join(reads_out)
    return reads, qual


def read_matrix_qual_file(matrix_qual):
    qual_dict = {}
    f = open(matrix_qual, 'r')
    idx = 0
    while f:
        line = f.readline().strip('\n')
        if len(line) == 0:
            break
        line = line.split('\t')
        if line[0].startswith('position'):
            position = re.sub(r'position_', '', line[0])
            values = line[1:]
            idx += 1
        else:
            qual_dict[position, line[0]] = line[1:]
            #print(position, line[0])
    f.close()
    return idx, values, qual_dict


def read_first_qual_file(first_qual):
    f = open(first_qual, 'r')
    first_qual_value = [0] * 1
    first_qual_key = ['a'] * 1
    total = 0
    index = 0
    while f:
        line = f.readline().strip('\n')
        if len(line) == 0:
            break
        line = line.split('\t')
        total += int(line[1])
        first_qual_value.append(total)
        first_qual_key.append(line[0])
    del first_qual_value[0]
    del first_qual_key[0]
    f.close()
    return total, first_qual_key, first_qual_value


def input_base_quality_distribution(reads, random_sequencing_errors, base_qual_distribution_file, phred33_quals, phred64_quals):
    qual_score = []
    (position, base_qual_distribution) = read_base_distribution_file(base_qual_distribution_file)
    # set the quality score


    for i in range(0, len(reads)):
        qual_dict_score = [0] * 1
        qual_dict_key = ['a'] * 1
        total = 0
        line_qual = base_qual_distribution[str(i)]
        #print(line_qual)
        for j in range(0, len(line_qual)):
            # print(line_qual[j])
            qual = line_qual[j]
            if qual != '0':
                total += int(qual)
                qual_dict_score.append(total)
                qual_dict_key.append(position[j])
        del qual_dict_score[0]
        del qual_dict_key[0]
        if total:
            random_int = random.randint(1, total)
            for k in range(0, len(qual_dict_key)):
                if qual_dict_score[k] >= random_int:
                    qual_score.append(qual_dict_key[k])
                    break
        else:
            random_int = random.randint(1, len(position))
            qual_score.append(position[random_int - 1])

    # get new reads based on quality values
    reads_out = [""] * len(reads)
    qual = [''] * len(reads)
    # print(len(qual_score))
    if phred33_quals:
        for i in range(0, len(reads)):
            qual[i] = ord(str(qual_score[i])) - 33
            if random_sequencing_errors and random.random() < sequencing_error_probability(qual[i]):
                reads_out[i] = random.choice("ATCG")
            else:
                reads_out[i] = reads[i]
    elif phred64_quals:
        for i in range(0, len(reads)):
            qual[i] = ord(str(qual_score[i])) - 64
            if random_sequencing_errors and random.random() < sequencing_error_probability(qual[i]):
                reads_out[i] = random.choice("ATCG")
            else:
                reads_out[i] = reads[i]
    reads = "".join(reads_out)
    return reads, qual


def read_base_distribution_file(base_qual_distribution_file):
    base_qual_distribution = {}
    f = open(base_qual_distribution_file, 'r')
    while f:
        line = f.readline().strip('\n')
        if len(line) == 0:
            break
        line = line.split('\t')
        if line[0].startswith('position'):
            position = line[1:]
        else:
            base_qual_distribution[line[0]] = line[1:]
    f.close()
    return position, base_qual_distribution


def dynamic_quality(reads, quality, random_sequencing_errors, end_part, end_part_sigma, end_qual, end_qual_sigma):
    qual = [quality * 40] * len(reads)
    reads_out = [""] * len(reads)
    end = len(reads) * random.normalvariate(end_part, end_part_sigma)
    for i in range(0, len(reads)):
        if i > end:
            qual[i] = beta_fun(end_qual, end_qual_sigma) * 36 + 2
            if random_sequencing_errors and random.random < sequencing_error_probability(qual[i]):
                reads_out[i] = random.choice("ATCG")
            else:
                reads_out[i] = reads[i]
        elif i <= end:
            if random_sequencing_errors and random.random < sequencing_error_probability(qual[i]):
                reads_out[i] = random.choice("ATCG")
            else:
                reads_out[i] = reads[i]
    reads = "".join(reads_out)
    return reads, qual


def cat_map(samw, samc, fq1, fq2):
    if fq1:
        os.system('cat ' + fq1 + '.tmp >>' + fq1 + ' && rm ' + fq1 + '.tmp')
    if fq2:
        os.system('cat ' + fq2 + '.tmp >>' + fq2 + ' && rm ' + fq2 + '.tmp')
    if samw:
        os.system('cat ' + samw + '.tmp >>' + samw + ' && rm ' + samw + '.tmp')
    if samc:
        os.system('cat ' + samc + '.tmp >>' + samc + ' && rm ' + samc + '.tmp')


def sequencing_error_probability(phred_score):
    return 10 ** (-phred_score/10.0)


def usage():
    print('''\n\n==============================================================================================\n
simRRBS: reduced representation bisulfite sequencing simulator for next-generation sequencing\n
                        Written in January by Xiwei Sun Ph.D                               \n
                               xwsun@zju.edu.cn                                            \n


==============================================================================================\n

\nsimRRBS is implemented in the Python language and run in an operating system-independent manner. It can allow users
 to mimic various methylated level (total methylated level of cytosine, percentage of cytosine that methylated and
 methylated level of total methylcytosines) and bisulfite conversion rate in CpG, CHG and CHH context, respectively. It
 can also simulate genetic variations that are divergent from the reference sequence along with the sequencing error and
quality distributions. In the output, both directional/non-directional, various read length, single/paired-end reads and
alignment data in the SAM format can be generated. BSSim is a cross-platform BS-seq simulator offers output read
 datasets not only suitable for Illumina's Solexa, but also for Roche's 454 and Applied Biosystems' SOLiD.
 \nUsage:        ./simRRBS.py [options]
 \nOptions:
 \nGeneral
    -h/--help	Help.
    -f/--fasta	Input reference sequence in the fasta format.
    --genome_folder<path/to/genome/folder> Input the genome folder including reference sequence in the fasta format.

    -d <int>	Expectation of sequencing depth (>0),exponential distribution are supposed here. Default: 30.
    --multicore <int>     The max number of processes core (>0). Default: 2.
    -l/--length <int>     Read length (>0). Default: 100 bp.
    -s/--single_end	Single-end pattern.
    -p/--paired_end	Paired-end pattern (default).
    --non_directional    Directional: reads 1 is same direction with reference sequencing (Watson strand) and read 2 is
                        from Crick strand.Non-directional:reads 1 and reads 2 can be of all four bisulfite strands. Default: directional.
    -t	Sequencing platform: Solexa/SOLiD/454. Default: Solexa.
    -e <int>	Number of max error base at the end of a reads [0~l]. Default: 0.

    --cut_site      The cutting site is separated by -.For example Mspl cutting site is C-CGG;here,at most two cutting
                    sites is support and they must separated by comma; Default is C-CGG.
    --min <int>	The minimum size-selected fragment length of RRBS library (library size) (>0). Default: 40 bp.
    --max <int>     The maximum size-selected fragment length of RRBS library (library size) (>0).  Default: 220 bp.
    --adapter1      The ligated adapter sequence of the  first end of RRBS fragment.
    --adapter2      The ligated adapter sequence of the  second end of RRBS fragment.
    --non_meth_adapter  The state of cytosines in adapters is unmethylated.Default is methylated.
    --non_meth_end_repair_bases The state of cytosines in end repair  is unmethylated.Default is methylated

    -o/--output	Prefix of output file. Default is set by name of input file.
    -P/--PosInfo	Output position information into the output file. Default is not.
    --SAM	Output alignment result in SAM format. Default is not.
    -v/--version	Version information.
    --seed <int>         Simulation seed.Default is function of system time and vary among different simulations.
    -R/--ref_methInfo	Output the reference methylation information. Default is not.

    format is:\nchromosome	position	ref_genome	ref_A	methylation pattern	default methylation rate(ignore it if ref is A,T)

    ref_B(homologous chromosome)	methylation pattern	default methylation rate


\nDNA methylation
    --ml <float>	Total methylation level of cytosines (overall DNA methylation level) (0~1). Default: 0.0612.
         --CG_level  <float>	CG methylation level (0~1). Default: 0.8653.
         --CHG_level <float>	CHG methylation level (0~1). Default: 0.0203.
         --CHH_level <float>	CHH methylation level (0~1). Default: 0.0227.

    --mr <float>	All mC/C rate (the ratio of total methylcytosines/total cytosines) (0~1). Default: 0.073.
        --CG_rate  <float>	mCG/CG rate (0~1). Default: 0.852.
        --CHG_rate <float>	mCHG/CHG rate (0~1). Default: 0.019.
        --CHH_rate <float>	mCHH/CHH rate (0~1). Default: 0.025.

    --mC_ml <int>	Methylation level of total methylcytosines. Default: 0.8529.
        --mCG_level <float>	mCG methylation level (0~1). Default: 0.8529.
        --mCHG_level <float>	mCHG methylation level (0~1). Default: 0.0837.
        --mCHH_level <float>	mCHH methylation level (0~1). Default: 0.9091*0.0994+(1-0.9091)*0.8965.

    --mCS <float>	    Standard deviation of --mC_ml (0~(1-mC_ml)*mC_ml). Default: 0.01.
        --mCGS  <float>	Standard deviation of --mCG_level (0~(1-mCG_level)*mCG_level).
                        Default: (1-mCG_level)*mCG_level/2.0.
        --mCHGS <float>	Standard deviation of --mCHG_level (0~(1-mCHG_level)*mCHG_level).
                        Default: (1-mCHG_level)*mCHG_level/2.0.
        --mCHHS <float>	Standard deviation of --mCHH_level(0~(1-mCHH_level)*mCHH_level).
                        Default: (1-mCHH_level)*mCHH_level/2.0.

    --cr <float>	All cytosines  bisulfite conversion rate [0~1]. Default is 0.998.
        --CG_conversion  <float>	CG conversion rate [0~1]. Default: 0.998.
        --CHG_conversion <float>	CHG conversion rate [0~1]. Default: 0.998.
        --CHH_conversion <float>	CHH conversion rate [0~1]. Default: 0.998.


\nSNP
    -S	SNP file with SNP information, specifying location and frequency of SNPs.
        format is:\nChromosome	position	strand	frequency of A	frequency of T	frequency of C	frequency of G
        chr10	1	+	0	0.4	0	0.6
        chr10	2	+	0.3	0.2	0.1	0.4
    --non_SNP	Do not add SNP. Default is add (based on prior probability).
    --homo_freq <float>	The frequency of homozygous SNPs [0~(1-Z)]. Default: 0.0005.
    --heter_freq <float>	The frequency of heterozygous SNPs [0~(1-Y)]. Default: 0.001.


 \nRead quality

    -q/--quality <float>	Quality score (mean value of quality score). Default: 0.95 (95% of highest score).
    --qs <float>	Standard deviation of -q (0~(1-q)*q). Default: (1-q)*q/2.
    --rand_quals	Randomly introduce quality value. Default: uniform quality score.
    --rand_error	Randomly introduce sequencing errors by sequencing quality value
                    (Q =-10*log10(e),Q is the sequencing quality value (Phred score),
                    e is the error rate, Massingham, et al., 2012). Default is not.

    --input_quals Introduce quality value empirically from real data. Default:False
    --first_qual_R1 The file including the distribution of first quality value counts for reads 1.
    --first_qual_R2 The file including the distribution of first quality value counts for reads 2.
    --matrix_qual_R1 The file including the probability matrix of  quality value counts at each position for reads 1.
    --matrix_qual_R2 The file including the probability matrix of  quality value counts at each position for reads 2.

    --phred33_quals FastQ qualities are ASCII transformation of that Phred quality plus 33.Default:on.
    --phred64_quals FastQ qualities are ASCII transformation of that Phred quality plus 64.Default:off.

    simRRBS can also allow users to  to add different quality value at the end part of the read.
    --ep <float>		(Length of the end part)/(total read length) (0~1). Default: 0.3 (30% of total read length).
    --eps <float>		Standard deviation of --ep (0~(1-ep)*ep). Default: (1-ep)*ep/2.
    --eq <float>		The mean quality value of the end part less than -q (0~q). Default: 0.2
    --es <float>		Standard deviation of --eq (0~(1-(q-eq))*(q-eq)). Default: (1-(q-eq))*(q-eq)/4.

 \nExample:
    ./simRRBS.py -i test.fa
    ./simRRBS.py -i test.fa -d 10 -t 454 -U 4 -G 1 -s -A -R -o out
    ./simRRBS.py -i test.fa -d 10 -t 454 -U 4 -G 1 -s -A -R --CR 0.9 --CM 0.4 --HM 0.3 --HC 0.7 -o out\n\n''')


def main(argv):
    print(time.strftime('simRRBS start work at: %Y-%m-%d %H:%M:%S'))
    start_time = time.time()
    ref_file = ''
    ref_path = ''
    path = False
    depth_mu = 30
    cpus = 2
    seed = 1
    reads_length_mu = 100
    reads_length_sigma = 0
    paired_end = True
    technology = 'Solexa'
    fragment_min = 40
    fragment_max = 220
    cut_site1 = "C-CGG"
    cut_site2 = "C-CGG"
    num_site = 1
    qual_mu = 0.95
    qual_sigma = 0.005
    Dynamic_qual = False
    random_sequencing_errors = False
    end_part = 0.1
    end_part_sigma = (1 - end_part) * end_part / 2.0
    end_qual = 0.8
    end_qual_sigma = (1 - (qual_mu - end_qual)) * (qual_mu - end_qual) / 4.0
    input_quals = False
    first_qual_R1 = "D:\\simRRBS_re\\prob\\first_count.R1"
    first_qual_R2 = "D:\\simRRBS_re\\prob\\first_count.R2"
    matrix_qual_R1 = "D:\\simRRBS_re\\prob\\prob_matrix.R1"
    matrix_qual_R2 = "D:\\simRRBS_re\\prob\\prob_matrix.R2"
    phred33_quals = True
    phred64_quals = False
    max_err = 0
    CG_conversion_rate = CHG_conversion_rate = CHH_conversion_rate = conversion_rate = 0.998
    CG_methylation_level = CHG_methylation_level = CHH_methylation_level = C_methylation_level = 0
    mC_rate = 0.06122667  # Date from Yanhuang
    mCG_rate = 0.8653  # Date from Yanhuang
    mCHG_rate = 0.0203  # Date from Yanhuang
    mCHH_rate = 0.0227  # Date from Yanhuang
    mCG_mu = 0.8529
    mCHG_mu = 0.0837
    mCHH_mu = 0.9091 * 0.0994 + (1 - 0.9091) * 0.8965
    mCG_sigma = mCHG_sigma = mCHH_sigma = mC_sigma = 0.01
    directional = False
    out = 'D:\\simRRBS_re\\test\\rrbs'
    position = False
    non_snp = True
    p1 = 0.0005  # homozygote
    p2 = 0.001  # heterozygote
    CG_beta_distribution = CHG_beta_distribution = CHH_beta_distribution = beta_distribution = False
    output_ref = True
    dbsnpfile = ''
    Polyploid = 2
    meta = False
    complementary = 1
    SAM = True
    adapter = True
    adapter1 = "ACACTCTTTCCCTACACGACGCTCTTCCGATCT"
    adapter2 = "GATCGGAAGAGCACACGTCTGAACTCCAGTCAC"
    p5 = "AAAAATGATACGGCGACCACCGAGATCT"
    p7 = "ATCTCGTATGCCGTCTTCTGCTTG"
    index = "ATCACG"
    adapter2_p7 = adapter2 + index + 'A' + p7
    adapter1_p5 = p5 + adapter1
    meth_adapter = True
    meth_end_repair_bases = False
    # test parameter
    ref_file = "D:\\simRRBS_re\\test\\chr21_1.fa"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hf:d:l:spt:e:o:PvRS:q",
                                   ["help", "fasta=", "genome_folder=", "multicore=", "seed=", "length=", "single_end",
                                    "pair_end", "non_directional", "cut_site=", "min=", "max=", "adapter1=",
                                    "adapter2=", "non_meth_adapter", "non_meth_end_repair_bases", "output=", "PosInfo",
                                    "SAM", "version", "ref_methInfo", "ml=", "CG_level=", "CHG_level=", "CHH_level=", "mr=", "CG_rate=",
                                    "CHG_rate=", "CHH_rate=", "mC_ml=", "mCG_level=", "mCHG_level=", "mCHH_level=",
                                    "mCS=", "mCGS=", "mCHGS=", "mCHHS=", "ep=", "eps=", "eq=", "es=", "non_SNP",
                                    "homo_freq=", "heter_freq=", "quality=", "qs=", "rand_quals", "rand_error",
                                    "phred33_quals", "phred64_quals", "input_quals", "first_qual_R1=", "first_qual_R2=", "matrix_qual_R1=", "matrix_qual_R2="])
    except getopt.GetoptError as e:
        usage()
        print(e.msg)
        print("Please check your options.")
        sys.exit()
    for opt, arg in opts:
        if opt == '-h' or opt == '--help':
            usage()
            sys.exit()
        elif opt == '-f' or opt == '--fasta':
            ref_file = arg
        elif opt == '--genome_folder':
            ref_path = arg
            path = True
        elif opt == '-d':
            depth_mu = int(arg)
        elif opt == '--multicore':
            cpus = int(arg)
        elif opt == '--seed':
            seed = arg
        elif opt == '-s' or opt == '--single_end':
            single_end = True
            paired_end = False
        elif opt == '-p' or opt == '--paired_end':
            paired_end = True
        elif opt == '-t':
            technology = arg
            if technology == 'SOLiD':
                reads_length_mu = 50
                qual_mu = 0.98
            elif technology == '454':
                reads_length_mu = 250
                reads_length_sigma = 100
                qual_mu = 0.99
                end_qual = 0.03
                end_qual_sigma = 0.01
            elif technology == 'Solexa':
                tmp = 1
            else:
                print("Sequencing platform must be Solexa/SOLiD/454.\n")
                sys.exit()
        elif opt == '-l' or opt == '--length':
            reads_length_mu = int(arg)
        elif opt == '--min':
            fragment_min = int(arg)
        elif opt == '--max':
            fragment_max = int(arg)
        elif opt == '--cut_site':
            arg_list = arg.split(',')
            num_site = len(arg_list)
            if num_site == 1:
                cut_site1 = cut_site2 = arg_list[0]
            elif num_site == 2:
                cut_site1 = arg_list[0]
                cut_site2 = arg_list[1]
            else:
                print("The number of cutting sites must be 1 or 2.\n")
                sys.exit()
        elif opt == '--adapter1':
            adapter1 = arg
        elif opt == '--adapter2':
            adapter2 = arg
        elif opt == '--non_meth_adapter':
            meth_adapter = False
        elif opt == '--non_meth_end_repair_bases':
            meth_end_repair_bases = False
        elif opt == '-q':
            qual_mu = float(arg)
            if qual_mu >= 0 and qual_mu <= 1:
                tmp = 1
            else:
                print("Quality score (mean value of quality score) must at range of [0~1].\n")
                sys.exit()
        elif opt == '--input_quals':
            input_quals = True
        elif opt == '--matrix_qual_R1':
            matrix_qual_R1 = arg
        elif opt == '--matrix_qual_R2':
            matrix_qual_R2 = arg
        elif opt == '--first_qual_R1':
            first_qual_R1 = arg
        elif opt == '--first_qual_R2':
            first_qual_R2 = arg
        elif opt == '--phred33_quals':
            phred33_quals = True
            phred64_quals = False
        elif opt == '--phred64_quals':
            phred33_quals = False
            phred64_quals = True
        elif opt == '-e':
            max_err = int(arg)
        elif opt == '-o' or opt == '--output':
            out = arg
        elif opt == '-P' or opt == 'PosInfo':
            position = True
        elif opt == '--non_directional':
            directional = False
            print( "Simulate the non_directional reads!")
        elif opt == '-B':
            CG_beta_distribution = CHG_beta_distribution = CHH_beta_distribution = beta_distribution = True
        elif opt == '--CB':
            CG_beta_distribution = True
        elif opt == '--GB':
            CHG_beta_distribution = True
        elif opt == '--HB':
            CHH_beta_distribution = True
        elif opt == '--non_SNP':
            non_snp = True
        elif opt == '-S':
            dbsnpfile = arg
        elif opt == '-G':
            Polyploid = int(arg)
        elif opt == '--homo_freq':
            p1 = float(arg)
        elif opt == '--heter_freq':
            p2 = float(arg)
        elif opt == '-R' or opt == '--ref_methInfo':
            output_ref = True
        elif opt == '--SAM':
            SAM = True
        elif opt == '-v' or opt == '--version':
            print("Program: simRRBS\n\nAuthor Affiliations: Institute of Translational medicine ,Zhejiang University, China\nVersion: 1.0\nContact: xwsun@zju.edu.cn")
            sys.exit()
        elif opt == '--cr':
            conversion_rate = float(arg)
            if conversion_rate >= 0 and conversion_rate <= 1:
                CHH_conversion_rate = CHG_conversion_rate = CG_conversion_rate = conversion_rate
            else:
                print("All cytosines' bisulfite conversion rate must at range of [0~1].\n")
                sys.exit()
        elif opt == '--CG_conversion':
            CG_conversion_rate = float(arg)
            if CG_conversion_rate >= 0 and CG_conversion_rate <= 1:
                tmp = 1
            else:
                print("CG conversion rate must at range of [0~1].\n")
                sys.exit()
        elif opt == '--CHG_conversion':
            CHG_conversion_rate = float(arg)
            if CHG_conversion_rate >= 0 and CHG_conversion_rate <= 1:
                tmp = 1
            else:
                print("CHG conversion rate must at range of [0~1].\n")
                sys.exit()
        elif opt == '--CHH_conversion':
            CHH_conversion_rate = float(arg)
            if CHH_conversion_rate >= 0 and CHH_conversion_rate <= 1:
                tmp = 1
            else:
                print("CHH conversion rate must at range of [0~1].\n")
                sys.exit()
        elif opt == '--ml':
            C_methylation_level = float(arg)
            if C_methylation_level > 0 and C_methylation_level < 1:
                CHH_methylation_level = CHG_methylation_level = CG_methylation_level = C_methylation_level
            else:
                print("Total methylation level of cytosines must at range of (0~1).\n")
                sys.exit()
        elif opt == '--CG_level':
            CG_methylation_level = float(arg)
            if CG_methylation_level > 0 and CG_methylation_level < 1:
                tmp = 1
            else:
                print("CG methylation level of cytosines must at range of (0~1).\n")
                sys.exit()
        elif opt == '--CHG_level':
            CHG_methylation_level = float(arg)
            if CHG_methylation_level > 0 and CHG_methylation_level < 1:
                tmp = 1
            else:
                print("CHG methylation level of cytosines must at range of (0~1).\n")
                sys.exit()
        elif opt == '--CHH_level':
            CHH_methylation_level = float(arg)
            if CHH_methylation_level > 0 and CHH_methylation_level < 1:
                tmp = 1
            else:
                print("CHH methylation level of cytosines must at range of (0~1).\n")
                sys.exit()
        elif opt == '--mr':
            mC_rate = float(arg)
            if mC_rate > 0 and mC_rate < 1:
                mCHH_rate = mCHG_rate = mCG_rate = mC_rate
            else:
                print("The ratio of total methylcytosines/total cytosines must at range of (0~1).\n")
                sys.exit()
        elif opt == '--CG_rate':
            mCG_rate = float(arg)
            if mCG_rate > 0 and mCG_rate < 1:
                tmp = 1
            else:
                print("mCG/CG rate must at range of (0~1).\n")
                sys.exit()
        elif opt == '--CHG_rate':
            mCHG_rate = float(arg)
            if mCHG_rate > 0 and mCHG_rate < 1:
                tmp = 1
            else:
                print("mCHG/CHG rate must at range of (0~1).\n")
                sys.exit()
        elif opt == '--CHH_rate':
            mCHH_rate = float(arg)
            if mCHH_rate > 0 and mCHH_rate < 1:
                tmp = 1
            else:
                print("mCHH/CHH rate must at range of (0~1).\n")
                sys.exit()
        elif opt == '--mC_ml':
            mC_mu = float(arg)
            if mC_mu > 0 and mC_mu < 1:
                mCG_mu = mCHG_mu = mCHH_mu = mC_mu
                mCG_sigma = mCHG_sigma = mCHH_sigma = (1 - mC_mu) * (mC_mu) / 2.0
                beta_distribution = True
            else:
                print("Methylation level of total methylcytosines must at range of (0~1).\n")
                sys.exit()
        elif opt == '--mCG_level':
            mCG_mu = float(arg)
            if mCG_mu > 0 and mCG_mu < 1:
                mCG_sigma = (1 - mCG_mu) * (mCG_mu) / 2.0
                CG_beta_distribution = True
            else:
                print("mCG methylation level must at range of (0~1).\n")
                sys.exit()
        elif opt == '--mCHG_level':
            mCHG_mu = float(arg)
            if mCHG_mu > 0 and mCHG_mu < 1:
                mCHG_sigma = (1 - mCHG_mu) * (mCHG_mu) / 2.0
                CHG_beta_distribution = True
            else:
                print("mCHG methylation level must at range of (0~1).\n")
                sys.exit()
        elif opt == '--mCHH_level':
            mCHH_mu = float(arg)
            if mCHH_mu > 0 and mCHH_mu < 1:
                mCHH_sigma = (1 - mCHH_mu) * (mCHH_mu) / 2.0
                CHH_beta_distribution = True
            else:
                print("mCHH methylation level must at range of (0~1).\n")
                sys.exit()
        elif opt == '--mCS':
            mC_sigma = float(arg)
            if mC_sigma > 0 and mC_sigma < ((1 - mC_mu) * (mC_mu)):
                mCG_sigma = mCHG_sigma = mCHH_sigma = mC_sigma
                beta_distribution = True
            else:
                print("Standard deviation of --MM must at range of (0~(1-MM)*MM).\n")
                sys.exit()
        elif opt == '--mCGS':
            mCG_sigma = float(arg)
            if mCG_sigma > 0 and mCG_sigma < ((1 - mCG_mu) * (mCG_mu)):
                CG_beta_distribution = True
            else:
                print("Standard deviation of --CM must at range of (0~(1-CM)*CM).\n")
                sys.exit()
        elif opt == '--mCHGS':
            mCHG_sigma = float(arg)
            if mCHG_sigma > 0 and mCHG_sigma < ((1 - mCHG_mu) * (mCHG_mu)):
                CHG_beta_distribution = True
            else:
                print("Standard deviation of --GM must at range of (0~(1-GM)*GM).\n")
                sys.exit()
        elif opt == '--mCHHS':
            mCHH_sigma = float(arg)
            if mCHH_sigma > 0 and mCHH_sigma < ((1 - mCHH_mu) * (mCHH_mu)):
                CHH_beta_distribution = True
            else:
                print("Standard deviation of --HM must at range of (0~(1-HM)*HM).\n")
                sys.exit()
        elif opt == '--rand_quals':
            Dynamic_qual = True
            print( "Boot the randomly introduce quality value!\n")
        elif opt == '--rand_error':
            random_sequencing_errors = True
            print("Randomly introduce sequencing errors by sequencing quality value!\n")
        elif opt == '--qs':
            qual_sigma = float(arg)
            Dynamic_qual = True
            print("Boot the randomly introduce quality value!\n")
        elif opt == '--ep':
            end_part = float(arg)
            if 0 < end_part < 1:
                end_part_sigma = (1 - end_part) * (end_part) / 2.0
            else:
                print("(Length of the end part)/(total read length) must at range of (0~1).\n")
                sys.exit()
        elif opt == '--eps':
            end_part_sigma = float(arg)
            if 0 < end_part_sigma < ((1 - end_part) * (end_part)):
                tmp = 1
            else:
                print( "Standard deviation of --EP must at range of (0~(1-EP)*EP).\n")
                sys.exit()
        elif opt == '--eq':
            end_qual = float(arg)
            if 0 < end_qual < qual_mu:
                end_qual_sigma = (1 - qual_mu + end_qual) * (qual_mu - end_qual) / 4.0
            else:
                print( "The mean quality value of the end part less than -q must at range of (0~q).\n")
                sys.exit()
        elif opt == '--es':
            end_qual_sigma = float(arg)
            if 0 < end_qual_sigma < ((1 - qual_mu + end_qual) * (qual_mu - end_qual)):
                tmp = 1
            else:
                print("Standard deviation of --EQ must at range of (0~(1-(q-EQ))*(q-EQ)).\n")
                sys.exit()

    if ref_file == '':
        usage()
        print("Input a fasta file as reference, please!")
        sys.exit()
    if CG_methylation_level > 0 and not CG_beta_distribution:
        if CG_methylation_level > mCG_mu:
            mCG_mu = CG_methylation_level / mCG_rate
            if mCG_mu < 1:
                # print "The CG methylation level is higher than default mCG_mu, auto changed, new mCG_mu is %s." %
                #  (mCG_mu)
                CG_beta_distribution = True
            if mCG_mu > 1:
                mCG_mu = mCG_rate = CG_methylation_level ** (1 / 2.0)
                CG_beta_distribution = True
        else:
            mCG_rate = CG_methylation_level / mCG_mu
    else:
        CG_methylation_level = mCG_rate * mCG_mu

    if CHG_methylation_level > 0 and not CHG_beta_distribution:
        if CHG_methylation_level > mCHG_mu:
            mCHG_mu = CHG_methylation_level / mCHG_rate
            if mCHG_mu < 1:
                # print "The CHG_methylation_level is higher than default mCHG_mu, auto changed, new mCHG_mu is %s." % (mCHG_mu)
                CHG_beta_distribution = True
            if mCHG_mu > 1:
                mCHG_mu = mCHG_rate = CHG_methylation_level ** (1 / 2.0)
                CHG_beta_distribution = True
            # print "mCHG_mu is larger than 1, you need to set two of the follow.(mCHG_mu=CHG_methylation_level/mCHG_rate)\n"
        else:
            mCHG_rate = CHG_methylation_level / mCHG_mu
    else:
        CHG_methylation_level = mCHG_rate * mCHG_mu

    if CHH_methylation_level > 0 and not CHH_beta_distribution:
        if CHH_methylation_level > mCHH_mu:
            mCHH_mu = CHH_methylation_level / mCHH_rate
            if mCHH_mu < 1:
                # print "The CHH_methylation_level is higher than default mCHH_mu, auto changed, new mCHH_mu is %s." % (mCHH_mu)
                CHH_beta_distribution = True
            if mCHH_mu > 1:
                mCHH_mu = mCHH_rate = CHH_methylation_level ** (1 / 2.0)
                CHH_beta_distribution = True
            # print "mCHH_mu is larger than 1, you need to set two of the follow.(mCHH_mu=CHH_methylation_level/mCHH_rate)\n"
        else:
            mCHH_rate = CHH_methylation_level / mCHH_mu
    else:
        CHH_methylation_level = mCHH_rate * mCHH_mu
    #### OPENING OUTPUT FILEHANDLES
    fq1 = fq2 = reads_r1 = reads_r2 = quals_r1 = quals_r2 = samw = samc = ''
    if out == '':
        out = "rrbs"
    if technology == 'Solexa':
        fq1 = out + '.1.fq'
        FQ1 = open(fq1, 'w')
        FQ1.close()

        if paired_end:
            fq2 = out + '.2.fq'
            FQ2 = open(fq2, 'w')
            FQ2.close()
    if output_ref:
        Ref = out + '.ref'
        REF = open(Ref, 'w')
    print(time.strftime('start read fasta file at: %Y-%m-%d %H:%M:%S'))
    # read the input reference sequence files
    if path:
        fa = read_path(ref_path)  #if reference sequence is given separately for each chromosome in multiple fasta files.
    else:
        fa = read_fa(ref_file)  #if reference sequence is in a single fasta file.
    # output header lines for sam format files
    if SAM:
        samw = out + '.Watson.sam'
        SAMW = open(samw, 'w')
        samc = out + '.Crick.sam'
        SAMC = open(samc, 'w')
        SAMW.write(
            '@HD\tVN:1.0\tSO:unsorted\tYou can get methylcytosine points on the Watson strand, the cytosines\' methylation information on reference.\n')
        SAMC.write(
            '@HD\tVN:1.0\tSO:unsorted\tYou can get methylcytosine points on the Crick strand, the guanines\' methylation information on reference.\n')
        for chrom in sorted(fa.keys()):
            SAMW.write('@SQ\tSN:' + chrom + '\tLN:' + str(len(fa[chrom])) + '\n')
            SAMC.write('@SQ\tSN:' + chrom + '\tLN:' + str(len(fa[chrom])) + '\n')
        SAMW.close()
        SAMC.close()
    # generate simulated reads with different SNP database
    # user input SNP
    if dbsnpfile:
        dbsnp = read_dbsnp(dbsnpfile)
        for chrom in sorted(fa.keys()):
            if seed:
                seed += 10
            print("\n simulate reads from: %s" % chrom)
            print(time.strftime('start at: %Y-%m-%d %H:%M:%S'))
            to_len = len(fa[chrom])
            ref_start = 0
            ref_tmp = str(fa[chrom])
            # introduce user input snp
            (snp_state, ref) = input_snp(ref_tmp, chrom, dbsnp, non_snp, seed)
            # identify methylation point
            (Rate, ref_pattern) = methyl(ref, conversion_rate, CG_conversion_rate, CHG_conversion_rate,
                                         CHH_conversion_rate, mC_rate, mCG_rate, mCHG_rate, mCHH_rate,
                                         CG_beta_distribution, mCG_mu, mCG_sigma, CHG_beta_distribution, mCHG_mu,
                                         mCHG_sigma, CHH_beta_distribution, mCHH_mu, mCHH_sigma)

            # identify methylation sites for adapters
            rate_adapter1 = methyl_adapter(adapter1_p5, meth_adapter, conversion_rate, CG_conversion_rate,
                                           CHG_conversion_rate, CHH_conversion_rate)
            rate_adapter2 = methyl_adapter(adapter2_p7, meth_adapter, conversion_rate, CG_conversion_rate,
                                           CHG_conversion_rate, CHH_conversion_rate)
            # out put ref
            if output_ref:
                for j in range(0, len(ref)):
                    REF.write(chrom + '\t' + str(ref_start + j + 1) + '\t' + fa[chrom][ref_start + j] + '\t' + ref[
                        j] + '\t' + str(ref_pattern[j]) + '\t' + str(1 - Rate[j]) + '\t' + str(snp_state[j]) + '\n')

            # find end repair bases
            end_repair_bases = {}
            rate_end_repair_bases = {}
            cut_index = {}
            cut_position = {}
            cut_seq = {}

            (cut_index["enzyme1"], cut_position["enzyme1"],cut_seq["enzyme1"], end_repair_bases["enzyme1"]) = find_end_repair_bases(cut_site1)
            (cut_index["enzyme2"], cut_position["enzyme2"],cut_seq["enzyme2"], end_repair_bases["enzyme2"]) = find_end_repair_bases(cut_site2)

            rate_end_repair_bases["enzyme1"] = methyl_adapter(end_repair_bases["enzyme1"], meth_end_repair_bases, conversion_rate, CG_conversion_rate,
                                                    CHG_conversion_rate, CHH_conversion_rate)
            rate_end_repair_bases["enzyme2"] = methyl_adapter(end_repair_bases["enzyme2"], meth_end_repair_bases, conversion_rate, CG_conversion_rate,
                                                  CHG_conversion_rate, CHH_conversion_rate)
            # find cutting site of restrict enzyme for RRBS library
            (cut_site, end_repair_format, enzyme_format) = cut_sequence(ref, ref_start, num_site, cut_seq, cut_index, cut_position, fragment_min, fragment_max)

            # create reads for RRBS library
            create_reads_for_input_or_random_snp(ref, ref_start, cut_site,end_repair_format, enzyme_format, end_repair_bases, rate_end_repair_bases, directional, seed, depth_mu, adapter1_p5,
                                       adapter2_p7, rate_adapter1, rate_adapter2, Rate, max_err, output_ref,
                                       reads_length_mu, reads_length_sigma, SAM, samw, samc, paired_end, fq1, fq2,
                                       reads_r1, quals_r1, reads_r2, quals_r2, technology, chrom, out, position, index,
                                       qual_mu, qual_sigma, random_sequencing_errors, end_part, end_part_sigma,
                                      end_qual, end_qual_sigma, Dynamic_qual,input_quals, first_qual_R1, first_qual_R2, matrix_qual_R1, matrix_qual_R2, phred33_quals, phred64_quals)
            cat_map(samw, samc, fq1, fq2)
        REF.close()
        print(time.strftime('\tend at: %Y-%m-%d %H:%M:%S'))

    elif Polyploid == 2:
        for chrom in sorted(fa.keys()):
            if seed:
                seed += 10
            print("\n simulate reads from: %s" % chrom)
            print(time.strftime('start at: %Y-%m-%d %H:%M:%S'))
            to_len = len(fa[chrom])
            ref_start = 0
            ref_tmp = str(fa[chrom])
            # introduce random  snp
            (snp_state, ref) = random_snp(ref_tmp, p1, p2, non_snp, Polyploid, seed)
            # identify methylation point
            (Rate, ref_pattern) = methyl(ref, conversion_rate, CG_conversion_rate, CHG_conversion_rate,
                                         CHH_conversion_rate, mC_rate, mCG_rate, mCHG_rate, mCHH_rate,
                                         CG_beta_distribution, mCG_mu, mCG_sigma, CHG_beta_distribution, mCHG_mu,
                                         mCHG_sigma, CHH_beta_distribution, mCHH_mu, mCHH_sigma, seed)

            # identify methylation sites for adapters
            rate_adapter1 = methyl_adapter(adapter1_p5, meth_adapter, conversion_rate, CG_conversion_rate,
                                           CHG_conversion_rate, CHH_conversion_rate)
            rate_adapter2 = methyl_adapter(adapter2_p7, meth_adapter, conversion_rate, CG_conversion_rate,
                                           CHG_conversion_rate, CHH_conversion_rate)
            # output ref
            if output_ref:
                for j in range(0, len(ref)):
                    REF.write(chrom + '\t' + str(ref_start + j + 1) + '\t' + fa[chrom][ref_start + j] + '\t' + ref[
                        j] + '\t' + str(ref_pattern[j]) + '\t' + str(1 - Rate[j]) + '\t' + str(snp_state[j]) + '\n')

            # find end repair bases
            end_repair_bases = {}
            rate_end_repair_bases = {}
            cut_index = {}
            cut_position = {}
            cut_seq = {}

            (cut_index["enzyme1"], cut_position["enzyme1"], cut_seq["enzyme1"], end_repair_bases["enzyme1"]) = find_end_repair_bases(cut_site1)
            (cut_index["enzyme2"], cut_position["enzyme2"], cut_seq["enzyme2"], end_repair_bases["enzyme2"]) = find_end_repair_bases(cut_site2)

            rate_end_repair_bases["enzyme1"] = methyl_adapter(end_repair_bases["enzyme1"], meth_end_repair_bases, conversion_rate, CG_conversion_rate,
                                                              CHG_conversion_rate, CHH_conversion_rate)
            rate_end_repair_bases["enzyme2"] = methyl_adapter(end_repair_bases["enzyme2"], meth_end_repair_bases, conversion_rate, CG_conversion_rate,
                                                              CHG_conversion_rate, CHH_conversion_rate)
            # find cutting site of restrict enzyme for RRBS library
            (cut_site, end_repair_format, enzyme_format) = cut_sequence(ref, ref_start, num_site, cut_seq, cut_index, cut_position, fragment_min, fragment_max)

            # create reads for RRBS library
            create_reads_for_input_or_random_snp(ref, ref_start, cut_site, end_repair_format, enzyme_format, end_repair_bases, rate_end_repair_bases, directional, seed, depth_mu, adapter1_p5,
                                       adapter2_p7, rate_adapter1, rate_adapter2, Rate, max_err, output_ref,
                                       reads_length_mu, reads_length_sigma, SAM, samw, samc, paired_end, fq1, fq2,
                                       reads_r1, quals_r1, reads_r2, quals_r2, technology, chrom, out, position, index,
                                       qual_mu, qual_sigma, random_sequencing_errors, end_part, end_part_sigma,
                                       end_qual, end_qual_sigma, Dynamic_qual,input_quals, first_qual_R1, first_qual_R2, matrix_qual_R1, matrix_qual_R2, phred33_quals, phred64_quals)
            cat_map(samw, samc, fq1, fq2)
    REF.close()
    print(time.strftime('\tend at: %Y-%m-%d %H:%M:%S'))
    elapsed = (time.time() - start_time) / 3600.0
    print("Total time used: %f h" % elapsed)

if __name__ == '__main__':
    main(sys.argv[1:])








