#! /usr/bin/env python


# Description
# This python script accomplishes the following:
# - takes a set of sars-cov-2 sequences (either as a multi sequence fasta or a directory of single sequence fasta files) and aligns each to the reference genome (pairwise alignment)
# - identifies all insertions and deletions within each sample sequence and generates an output table
# - removes nucleotide insertions from sample sequences
# - using the pair-wise alignments generates a MSA (multi sequence alignment) output alignment fasta

# Example Usage:
#   indel_finder.py -i <multi_sequence.fasta> -o . --ref_path <path_to_ref_genome> --prefix <prefix>



# import modules
from Bio import SeqIO
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
from Bio.Align.Applications import MafftCommandline
from Bio import AlignIO

import os
import shutil
import glob
import sys
import argparse

import pandas as pd
import re

from datetime import date
import time


###################
#### FUNCTIONS ####
###################
def getOptions(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="Parses command.")
    parser.add_argument("-i", "--input", help="either a single multi-sequence fasta file or path to a directory containing multiple single fasta files")
    parser.add_argument("-o", "--output", help="specifies the output directory where the output results where be written to; if not specified, the output results will be written to the current directory")
    parser.add_argument('--ref_path', help = 'path to the reference genome')
    parser.add_argument("--prefix",  help="optional: prefix used to save files, default uses today's date")

    options = parser.parse_args(args)
    return options


def get_ref_seq_record(ref_genome_path):
    ref = SeqIO.read(ref_genome_path, 'fasta')
    return {'ref_record': ref, 'ref_id': ref.id, 'ref_seq': ref.seq}



def create_temp_directories(wd):
    '''
    creates two temp directories for the alignment of each sequence to the reference genome
    these temp directories will be deleted at the end
    '''
    # get date
    today_date = str(date.today())

    # create tempory directory to store fastas and alignments
    fasta_temp_dir = os.path.join(wd, 'temp-fastas_%s' % today_date)
    alignment_temp_dir = os.path.join(wd, 'temp-alignments_%s' % today_date)

    if os.path.exists(fasta_temp_dir):
        shutil.rmtree(fasta_temp_dir)

    if os.path.exists(alignment_temp_dir):
        shutil.rmtree(alignment_temp_dir)

    os.makedirs(fasta_temp_dir)
    os.makedirs(alignment_temp_dir)

    return {'alignment_temp_dir' : alignment_temp_dir, 'fasta_temp_dir': fasta_temp_dir}


def delete_temp_directory(directory_name):
    if os.path.exists(directory_name):
        print('removing the temp directory: %s' % directory_name)
        shutil.rmtree(directory_name)
    return None


def create_multi_fasta(fasta_files_dir_path, out_fasta):
    print('1A - generating multi sequence fasta')
    print('')

    if os.path.exists(out_fasta):
        os.remove(out_fasta)


    os.chdir(fasta_files_dir_path)

    for file in glob.glob('*.fa'):
        record = SeqIO.read(file, 'fasta')
        with open(out_fasta, 'a') as outhandle:
             SeqIO.write(record, outhandle, 'fasta')

    return None

def add_ref_genome(multifasta, ref_genome, fasta_temp_dir):
    '''
    generates a fasta file for each sequence that contains the reference sequence and sample sequence
    these are saved to the temp fasta files directory
    '''
    # how many sequnces are in the fasta file:
    num_records = len(list(SeqIO.parse(multifasta, "fasta")))
    print('1- adding reference genome to each sequence and saving to temp fasta files directory')
    print('  ....there are %d sequences' % num_records)

    # are any seqeunces duplicated in the multifasta?? If so, print warning because only one of the
    # duplicates will be proccessed becasue the files will be overwritten

    duplicated_records = []
    all_records = []
    for record in SeqIO.parse(multifasta, 'fasta'):
        if record.id not in all_records:
            all_records.append(record.id)
        else:
            duplicated_records.append(record.id)


    print('  ....there are %d records with same record.id in the multifasta' % len(duplicated_records))
    print('  ....any records with the same record.id will not get processed; the file will be overwritten')
    if len(duplicated_records) > 0 :
        print('  ....the records wtih the same record.id are:')
        for record in duplicated_records:
            print(  '  ........ %s' % record)

    n = 0

    for record in SeqIO.parse(multifasta, 'fasta'):
        n = n + 1

        # reset_records list
        records = [ref_genome]

        # get record from fasta file
#         print(n, record.id)

        #append record to reference genome
        records.append(record)

        #write records list to a fasta file
        path = os.path.join(fasta_temp_dir, '%s.fasta' % record.id)

        with open(path, 'w') as handle:
            SeqIO.write(records, handle, 'fasta')

    return num_records

def align_sequences(fasta_temp_dir, alignment_temp_dir, num_records):
    os.chdir(fasta_temp_dir)
    print('')
    print('2- aligning each sample sequence to reference genome and saving to temp alignments directory')

    n=0
    for file in glob.glob('*.fasta'):
        n = n + 1
        remainder = n%25
        if remainder == 0 or n == 1:
            print('  ....%d/%d complete' % (n, num_records))
        elif n == num_records:
            print('  ....%d/%d complete' % (n, num_records))

        sample_seq_name = file.split('.fasta')[0]

        # create outpath file name for alignment
        alignment_file_name = os.path.join(alignment_temp_dir, '%s.alignment.fasta' % sample_seq_name)

        if not os.path.isfile(alignment_file_name):

            # do alignment
            mafft_cline = MafftCommandline (input=file)
#             print(mafft_cline)
            stdout, stderr = mafft_cline()
            with open(alignment_file_name, 'w') as handle:
                handle.write(stdout)

    return None

def remove_insertions(alignment_temp_dir, ref_id, ref_seq ):
    print('')
    print('3- recording but NOT removing insertions from sequences')

    ref_seq = str(ref_seq)

    # prepare empty lists for data table
    seq_list = []
    ref_start_list = []
    seq_start_list = []
    length_list = []
    ref_seq_list = []
    upstream_list = []
    downstream_list = []


    os.chdir(alignment_temp_dir)

    insertions_dict = {}
    for file in glob.glob('*.alignment.fasta'):
        alignment_name = file.split('.alignment')[0] # this should be the sample name

        # read each record in the alignmet (i.e. the ref sequence and the sample sequence)
        for record in AlignIO.read(file, 'fasta'):

            # only perform the following code if find insertions in ref alignment
            # if the record is the reference genome and there are "-" then that means there is a insertion in the sample sequence
            if record.id == ref_id:
                ref_alignment_seq_str = str(record.seq)
                if re.search('[-]+', ref_alignment_seq_str):
                    insertions = re.findall('[-]+', ref_alignment_seq_str) # the lenght of this tells us how many insertions ther are
#                         print('')
                    print('  ....found %d insertion(s) in %s' % (len(insertions), alignment_name))


                    # now get the sample record
                    for sample_record in AlignIO.read(file, 'fasta'):
                        if sample_record.id == alignment_name:
                            sample_seq_str = str(sample_record.seq)

                    moving_length = 0
                    k = 0
                    for i in re.finditer('[-]+', ref_alignment_seq_str):
                        k = k + 1
#                         print('.........removing insertion %d of %d' % (k, len(insertions)))

                        seq_list.append(alignment_name)

                        ref_start = i.start() - moving_length # account for previous insertions removed
                        seq_start = i.start()
                        length = i.end() - i.start()  # gets you teh insertion length

                        ref_start_list.append(ref_start)
                        seq_start_list.append(seq_start)
                        length_list.append(length)

                        # get bp around teh insertion from the sample sequence
                        insert_nucleotides = sample_seq_str[seq_start: seq_start+length]
                        ref_seq_list.append('+%s' % insert_nucleotides)

                        # get the sequence around the insert from the reference
                        upstream = ref_seq[seq_start-7: seq_start]
                        downstream = ref_seq[seq_start: seq_start + 7]

                        upstream_list.append(upstream)
                        downstream_list.append(downstream)

                        # update moving length
                        moving_length = moving_length + length



    # fill in pandas table
    df = pd.DataFrame()
    df['accession_id'] = seq_list
    df['indel'] = ref_seq_list
    df['ref_start_pos'] = ref_start_list
    df['seq_start_pos'] = seq_start_list
    df['length'] = length_list
    df['upstream_ref'] = upstream_list
    df['downstream_ref'] = downstream_list

    return {'insertions_df': df, 'mod_seq_list': seq_list}

def record_deletions(alignment_temp_dir, ref_seq, mod_seq_list, ref_id):
    print('')
    print('4- recording deletions')

    # prepare empty lists for data table
#     ref_seq = str(ref_seq)

    seq_list = []
    ref_start_list = []
    seq_start_list = []
    length_list = []
    ref_seq_list = []
    upstream_list = []
    downstream_list = []

    os.chdir(alignment_temp_dir)

    for file in glob.glob('*.alignment.fasta'):

        alignment_name = file.split('.alignment.fasta')[0]

        for record in AlignIO.read(file, 'fasta'):
            if record.id == ref_id:
                ref_str = str(record.seq)

                for record in AlignIO.read(file, 'fasta'):
                    if record.id == alignment_name:
                        seq_str = str(record.seq)

                        if re.search('[-]+', seq_str) and record.id == alignment_name:
                            deletions = re.findall('[-]+', seq_str)
            #                         print('....found %d deletion(s) in %s' % (len(deletions), alignment_name))

                            for i in re.finditer('[-]+', seq_str):

                                # locate first deletion, record size and location, repeat for next deletion
                                seq_start = i.start()
                                if seq_start != 0:
                                    length = i.end() - i.start()

                                    seq_start_list.append(seq_start)
                                    ref_start_list.append('')
                                    length_list.append(length)
                                    seq_list.append(alignment_name)

                                    # get the ref sequence
                                    insert_nucleotides = ref_str[seq_start: seq_start+length]
                                    ref_seq_list.append('-%s' % insert_nucleotides)

                                    # get the sequence around the deletion
                                    upstream = ref_str[seq_start-7: seq_start]
                                    downstream = ref_str[seq_start: seq_start + 7]

                                    upstream_list.append(upstream)
                                    downstream_list.append(downstream)

    df = pd.DataFrame()
    df['accession_id'] = seq_list
    df['indel'] = ref_seq_list
    df['ref_start_pos'] = ref_start_list
    df['seq_start_pos'] = seq_start_list
    df['length'] = length_list
    df['upstream_ref'] = upstream_list
    df['downstream_ref'] = downstream_list

    return df


def join_insertion_and_deletions_dfs(insertions_df, deletions_df, prefix, wd):
    print('')
    print('5- writing indel table to csv')

    if insertions_df.shape[0] > 0 and deletions_df.shape[0] > 0:
        dataframe_list = [insertions_df, deletions_df]
        joined_df = pd.concat(dataframe_list)
    elif insertions_df.shape[0] > 0:
        joined_df = insertions_df
    elif deletions_df.shape[0] >0:
        joined_df = deletions_df
    else:
        joined_df = pd.DataFrame()
        joined_df['accession_id'] = ''
        joined_df['indel'] = ''
        joined_df['start_pos'] = ''
        joined_df['length'] = ''
        joined_df['upstream_ref'] = ''
        joined_df['downstream_ref'] = ''

    outfile = os.path.join(wd, '%s_indels.csv' % prefix)
    joined_df.to_csv(outfile, index = False)
    print('  ....indel table csv file name: %s' % outfile)


def create_concatenated_seq_records(wd, temp_alignment_dir, mod_seq_list, ref_genome, prefix):
    print('')
    print('5- concatenating sequence records into a MSA file')

    # create file that will append each record to
    concat_fasta_outfile = os.path.join(wd, '%s.alignment.fasta' % prefix)
    if os.path.exists(concat_fasta_outfile):
        os.remove(concat_fasta_outfile)
    print('  ....MSA file name: %s' % concat_fasta_outfile)

#     # first add the reference sequence
#     with open(concat_fasta_outfile, 'w') as handle:
#         SeqIO.write(ref_genome, handle, 'fasta')

    # first append the non - modified records
    os.chdir(temp_alignment_dir)
    for file in glob.glob('*.fasta'):
        sample_name = file.split('.alignment.fasta')[0]
#         if sample_name not in mod_seq_list:
        for record in AlignIO.read(file, 'fasta'):
            if record.id == sample_name:
                with open(concat_fasta_outfile, 'a') as handle:
                    SeqIO.write(record, handle, 'fasta')


    num_seqs = len(list(SeqIO.parse(concat_fasta_outfile, 'fasta')))
    # get length of sequences:
    seq_len_list = []
    for record in SeqIO.parse(concat_fasta_outfile, 'fasta'):
        seq_len = len(record.seq)
        if seq_len not in seq_len_list:
            seq_len_list.append(seq_len)

    print('  ...."alignment" has %d sequences' % num_seqs)
    print('  ....sequnce "alignment" length is:')
    for seq_len in seq_len_list:
        print('  .... .... %d' % seq_len)



if __name__ == '__main__':

    print('')
    print('********************************')
    print('*** starting INDEL FINDER ***')
    print('*** last updated 2021-12-05 ***')
    print('*** lastest update now only records insertions but does not remove them ***')
    print('')

    # parse command line arguments
    options = getOptions()
    wd = options.output
    ref_path = options.ref_path
    if options.prefix:
        prefix = options.prefix
    else:
        prefix = str(date.today())

    # get the refernce genome
    ref = get_ref_seq_record(ref_genome_path = ref_path)
    # ref['ref_id'] or ref['ref_seq'] or ref['ref_record']

    # create temp directories
    temp_dirs = create_temp_directories(wd)
    # temp_dirs['alignment_temp_dir'] or temp_dirs['fasta_temp_dir']


    #determine input type and create multifasta if neccessary:
    if re.search('.fa', options.input):
        input_type = 'single multi sequence fasta file'
        multifasta = options.input
        print('input type: %s' % input_type)
        print('')
    else:
        input_type = 'directory with multiple single sequence fasta files'
        print('input type: %s' % input_type)
        print('')

        multifasta = os.path.join(wd, '%s_multifasta.fasta' % prefix)
        create_multi_fasta(fasta_files_dir_path = options.input,
                           out_fasta = multifasta)

        print('multi sequence fasta saved to: %s' % multifasta)


    # add reference genome to each fasta file in temp fasta directory
    num_records = add_ref_genome(multifasta = multifasta,
                  ref_genome =ref['ref_record'],
                  fasta_temp_dir = temp_dirs['fasta_temp_dir'])

    # do alignment adn save alignment to temp alignment directory
    align_sequences(fasta_temp_dir = temp_dirs['fasta_temp_dir'],
                    alignment_temp_dir = temp_dirs['alignment_temp_dir'],
                   num_records = num_records)


    # remove and record the insertions
    insertions = remove_insertions(alignment_temp_dir = temp_dirs['alignment_temp_dir'],
                               ref_id = ref['ref_id'],
                               ref_seq = ref['ref_seq'] )
    # insertions['insertions_df'] or insert['mod_seq_list']

    # record deletions
    deletions_df = record_deletions(alignment_temp_dir = temp_dirs['alignment_temp_dir'],
                     ref_seq = ref['ref_seq'],
                     mod_seq_list = insertions['mod_seq_list'],
                                   ref_id = ref['ref_id'])

    # write out indel table
    join_insertion_and_deletions_dfs(insertions_df = insertions['insertions_df'],
                                  deletions_df = deletions_df,
                                  prefix = prefix,
                                  wd = wd)

    # write MSA
    create_concatenated_seq_records(wd = wd,
                                    temp_alignment_dir = temp_dirs['alignment_temp_dir'],
                                    mod_seq_list = insertions['mod_seq_list'],
                                    ref_genome = ref['ref_record'] ,
                                    prefix = prefix)

    # remove temp directories...
    delete_temp_directory(directory_name = temp_dirs['alignment_temp_dir'])
    delete_temp_directory(directory_name = temp_dirs['fasta_temp_dir'])

    print('********************************')
    print('DONE!')
    print('')
