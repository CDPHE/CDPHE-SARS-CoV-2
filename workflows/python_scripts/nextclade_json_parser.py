#! /usr/bin/env python


import re
import pandas as pd 
import sys
import json

import argparse

# note before you can use this script from the command line you must make the script executable
# locate this script in ~/scripts and be sure that ~/scripts is ammended to your $PATH variable
# to use nexclade_json_parser.py <path to json file>
# will create two output files:
# nextclade_variant_summary.csv
# nextclade_results.csv

# updated 2022-06-29
# under data['results'][i]['insertions']
# the new nextclade update got ride of the 'lenght' key 
# only keys under insertions are 'pos' and 'ins'
# i use len(data['results'][i]['insertions']['ins'] to find the length


#### FUNCTIONS #####
def getOptions(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="Parses command.")
    parser.add_argument("--nextclade_json",  help="nextclade json file")
    parser.add_argument('--seq_run_file_list')
    options = parser.parse_args(args)
    return options


def extract_variant_list(json_path, seq_run_file_list):

    # create pd data frame to fill
    df = pd.DataFrame()
    accession_id_list = []
    mutation_list = []
    gene_list = []
    refAA_list = []
    altAA_list = []
    codon_pos_list = []
    nuc_start_list = []
    nuc_end_list = []


    with open(json_path) as f:
        data = json.load(f)

    for i in range(len(data['results'])):

    #     print(data[i]['seqName'])
        if 'aaDeletions' in data['results'][i].keys():
            aa_deletions = data['results'][i]['aaDeletions']
            for item in aa_deletions:
                gene=item['gene']
                refAA= item['refAA']
                altAA= 'del'
                pos=item['codon'] + 1
                nuc_start = item['codonNucRange']['begin']
                nuc_end = item['codonNucRange']['end']

                mutation = '%s_%s%d%s' % (gene, refAA, pos, altAA)
                
                accession_id_list.append(data['results'][i]['seqName'])
                mutation_list.append(mutation)
                gene_list.append(gene)
                refAA_list.append(refAA)
                altAA_list.append(altAA)
                codon_pos_list.append(pos)
                nuc_start_list.append(nuc_start)
                nuc_end_list.append(nuc_end)
                
        if 'insertions' in data['results'][i].keys():
            insertions = data['results'][i]['insertions']
            for item in insertions:
                gene= ''
                refAA= 'ins'
                altAA= item['ins']
                pos=item['pos'] + 1
                nuc_start = item['pos'] + 1
                
                # to find length now that update removed length key
                insert_seq = item['ins']
                length = len(insert_seq)
                #####
                
                nuc_end = item['pos'] + 1 + length

                mutation = '%s_%s%d%s' % (gene, refAA, pos, altAA)
                
                accession_id_list.append(data['results'][i]['seqName'])
                mutation_list.append(mutation)
                gene_list.append(gene)
                refAA_list.append(refAA)
                altAA_list.append(altAA)
                codon_pos_list.append(pos)
                nuc_start_list.append(nuc_start)
                nuc_end_list.append(nuc_end)

        if 'aaSubstitutions' in data['results'][i].keys():
            aa_subs = data['results'][i]['aaSubstitutions']
            for item in aa_subs:
                gene = item['gene']
                refAA = item['refAA']
                if item['queryAA'] == '*':
                    altAA = 'stop'
                else:
                    altAA = item['queryAA']     
                
                pos = item['codon'] + 1
                nuc_start = item['codonNucRange']['begin']
                nuc_end = item['codonNucRange']['end']

                mutation = '%s_%s%d%s' % (gene, refAA, pos, altAA)
                accession_id_list.append(data['results'][i]['seqName'])
                mutation_list.append(mutation)
                gene_list.append(gene)
                refAA_list.append(refAA)
                altAA_list.append(altAA)
                codon_pos_list.append(pos)
                nuc_start_list.append(nuc_start)
                nuc_end_list.append(nuc_end)


    df['accession_id'] = accession_id_list
    df['variant_name'] = mutation_list
    df['gene'] = gene_list
    df['codon_position'] = codon_pos_list
    df['refAA'] = refAA_list
    df['altAA'] = altAA_list
    df['start_nuc_pos'] = nuc_start_list
    df['end_nuc_pos'] = nuc_end_list

        
    seq_run_list = []
    with open(seq_run_file_list, 'r') as f:
        for line in f:
            seq_run_list.append(line.strip())
        
    path = '%s_nextclade_variant_summary.csv' % seq_run_list[0]
    df.to_csv(path, index=False)
    
    
def get_nextclade(json_path, seq_run_file_list):

    # create pd data frame to fill
    accession_id_list = []
    clade_list = []
    totalSubstitutions_list = []
    totalDeletions_list = []
    totalInsertions_list = []
    totalAASubstitutions_list = []
    totalAADeletions_list = []
    
    
    
    df = pd.DataFrame()

    with open(json_path) as f:
        data = json.load(f)

    for i in range(len(data['results'])):
        if 'clade' in data['results'][i].keys():
            accession_id_list.append(data['results'][i]['seqName'])
            clade_list.append(data['results'][i]['clade'])
            totalSubstitutions_list.append(data['results'][i]['totalSubstitutions'])
            totalDeletions_list.append(data['results'][i]['totalDeletions'])
            totalInsertions_list.append(data['results'][i]['totalInsertions'])
            totalAASubstitutions_list.append(data['results'][i]['totalAminoacidSubstitutions'])
            totalAADeletions_list.append(data['results'][i]['totalAminoacidDeletions'])
            

    df['accession_id'] = accession_id_list
    df['nextclade'] = clade_list
    df['total_nucleotide_mutations'] = totalSubstitutions_list
    df['total_nucleotide_deletions'] = totalDeletions_list
    df['total_nucleotide_insertions'] = totalInsertions_list
    df['total_AA_substitutions'] = totalAASubstitutions_list
    df['total_AA_deletions'] = totalAADeletions_list
    
    seq_run_list = []
    with open(seq_run_file_list, 'r') as f:
        for line in f:
            seq_run_list.append(line.strip())

    path = '%s_nextclade_results.csv' % seq_run_list[0]
    df.to_csv(path, index = False)

    
if __name__ == '__main__':
    
    options = getOptions()
    get_nextclade(json_path = options.nextclade_json, seq_run_file_list = options.seq_run_file_list)
    extract_variant_list(json_path = options.nextclade_json, seq_run_file_list = options.seq_run_file_list)
        