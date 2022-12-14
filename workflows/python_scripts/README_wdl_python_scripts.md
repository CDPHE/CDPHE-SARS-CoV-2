# SC2 wdl python scripts

## Overview

This repo contains three custom python scripts called in our SC2 wdl workflows. These scripts should be stored in a google bucket and linked to your workspace data within your Terra.bio workspace, so they can be used as inputs within each respective workflow. Below lists the three scripts and their associated workflows and further below provides greater detail about each script.  
- ``calc_percent_coverage.py`` is called in the ``SC2_ont_assembly.wdl``, ``SC2_illumina_pe_assembly.wdl``, and ``SC2_illumina_se_assembly.wdl``.

- ``nextclade_json_parser.py`` is called in the ``SC2_lineage_calling_and_results.wdl``.

- ``concat_seq_metrics_and_lineage_results.py`` is called in the ``Sc2_lineage_calling_and_results.wdl``.  



## calc_percent_coverage.py
<details>
<summary>click to expand</summary>

### overview
This script is called in the `SC2_illumina_pe_assembly.wdl`, ``SC2_ilumina_se_assembly.wdl``, and ``SC2_nanopore_assembly.wdl`` WDL workflows. These workflows act on individual samples (as opposed to sample sets), therefore this script also works on individual samples. The script reads in a consensus genome as a fasta file and calculates the percent coverage of the sample consensus genome. Specifically, the percent coverage is calculated as:


$$
\percent_coverage = \frac{number_non_ambigous_bases}{29903}, * 100
$$

where the number_non_ambigous_bases is the number of basepair calls not including Ns in the sample consensus sequence and 29903 is the number of basepairs in the reference genome (NC_045512).

### inputs
  - ``--sample_id``: sample id

  - ``--fasta_file``: consensus sequence saved as a fasta file

### outputs
The script also records the number of aligned bases, the number of ambigous bases (Ns), and the number of nonambigous bases (A,G,C,T). The output is a csv file called ``{accession_id}_consensus_cvg_stats.csv`` and has the following column headers:

- accession_id: sample name and the sample id found in the ``entity:sample_ID`` column in the terra data table.

- number_aligned_bases: the total lenght of the consensus genome (inlcuding Ns)

- number_N_bases: the number of ambigous (N) bases in the consensus genome

- number_non_ambigous_bases: the number of non-ambigous (A, C, G, T) bases in the consenuss genome

- percent_non_ambigous_bases: as calcuated above

- number_seqs_in_fasta: should be 1, we included this column when we were having trouble with our ont assebly and never removed it.

Thre is an example output in the example data directory within this repo.
</details>

## nextclade_json_parser.py
<details>
<summary>click to expand</summary>

### overview
This script is called in the ``SC2_lineage_calling_and_results`` WDL workflow. This workflow acts on sample sets and so therefore this script also works on a sample set. This script is called in the ``parse_nextclade`` task within the workflow which can be seen in the ``SC2_lineage_calling_and_results.wdl`` workflow diagram in the README.md one directory out. Briefly, the workflow concatentates all consesnus sequences of the samples in the sample set into a single fasta file (``concatenate`` task). The concatentated fasta file is run through nextclade which generates a ``nextclade.json`` file (``nextclade`` task). Within the ``nextclade.json`` file is data for each sample consensus sequence inlcuding the nextclade clade designation, AA substitutions, deletions, insertions, etc. Generally, this script reads in the ``nextclade.json`` file, parses the json file to extract the data of interest, formats the data into a table and saves it as a csv file.

### inputs
There are 2 inputs for this script:
1. ``--nextclade_json``: the nextclade.json file generated in the ``nextclade`` task of the workflow.

2. ``--seq_run_file_list``: the list of the seq_run input variable for the workflow saved as a text file. See below in the header details about working with sample sets for more on how this is formated and generated within the wdl workflow.


### outputs
There are two outputs from this script, each accomplished from a seperate function within the script. Example outputs can be found in the example data directory within this repo. These functions are:

1. ``extract_variant_list()`` function : This function generates a summmary of the AA substitions, insertions, and deletions for each sample within the ``nextclade.json`` file. The output is a csv file called ``{seq_run}_nextclade_variant_summary.csv`` which is one of the files that is transfered to the google bucket as outputs of the workflow. The data is formatted such that each row corresponds to a either an AA substition, insertion, or deletion, such that each consensus seuqence can have more than one row of data. The csv file has the following column headers:

  - accession_id: the sample name as listed in the fasta header (therefore there will be a "CO-CDPHE-" prefix added to the accession id)

  - variant_name: the full name of the variant formatted as {gene}_{refAA}{AApos}{altAA} (e.g. S_L452Q or S_L24del).

    - For insertions the gene is not listed, the refAA is defined as "ins", the AA position is the nucleotide position in the genome and the altAA is listed as the string of nucleotides. So the variant is formated to look something like this: "_ins1027T" which would be interpreted as an insertion of a T nucleotide occured at genome position 1027.

  -  gene: the gene where the AA substition, deletion or insertion occurs (e.g. N, S, ORF1a, M etc.). No gene is listed for insertions.

  - codon_position: the codon position (or protien position) within the gene where the AA substition, deletion or insertion occured. For insertions it is the nucleotide genome position.

  - refAA: the reference AA at the position where the AA substition, deletion, or insertion occured. For insertions the refAA is listed as "ins".

  - altAA: the AA in the consensus sequence at the position where the AA substition, deletion, or insertion occured. For insertions the altAA is the string of nucleotide base pairs that were inserted.

  - start_nuc_pos: the starting nucleotide position within the genome where the AA substition, deletion, or insertion occured.

  - end_nuc_pos: the ending nucleotide position within the genome where the AA substition, deletion, or insertion occured (for a single AA substition the start_ncu_pos and end_nuc_pos will be a difference of 3).

    -

2.  ``get_nextclade()`` function: This function generates a summary of the nextclade designation, total nucleotide and AA substitions, total nucleotide and AA deletions, and total nucleotide insertions. The output file is called ``{seq_run}_nextclade_results.csv`` and is used as input for the ``concat_seq_metrics_and_lineage_results.py`` called in the ``results_table`` task in the workflow. The output file has the following column headers:
  - accession_id: the sample name as listed in the fasta header (therefore there will be a "CO-CDPHE-" prefix added to the accession id)

  - nextclade: nextclade clade designation (e.g. 22C (Omicron))

  - total_nucleotide_mutations: number of SNPs in consensus genome

  - total_nucleotide_deletions: number of deletions in conesnuss genome

  - total_nucleotide_insertions: number of insertions in consensus genome

  - total_AA_substitutions: number of AA substitions in the consensus genome

  - total_AA_deletions: number of AA deletions in teh consensus genome

</details>  

## concat_seq_metrics_and_lineage_results.py

<details>
<summary>click to expand</summary>

### overview
This script is called in the ``SC2_lineage_calling_and_results`` WDL workflow. This workflow acts on sample sets and so therefore this script also works on a sample set. This script is called in the ``results_table`` task within the workflow which can be seen in the ``SC2_lineage_calling_and_results.wdl`` workflow diagram in the README.md one directory out. Generally, this script pulls together a bunch of metadata and data regarding the consensus sequence and outputs the data in csv file.  

### inputs
The script takes the following inputs:

  - ``--sample_list``: the list of the sample_IDs input variable (column in the terra data table) for the workflow written to a text file. This is provided in the terra data table upload.  See below in the header details about working with sample sets for more on how this is formated and generated within the wdl workflow.

  - ``--plate_name_file_list``: the list of the plate_name input variable (column in the terra data table) for the workflow written to a text file. This is provided in the terra data table upload.

  - ``--plate_sample_well_file_list``: the list of the plate_sample_well variable (column in the terra data table) for the worfklow written to a text file. This is provided in the terra data table upload.

  - ``--primer_set_file_list``: the list of the primer_set variable (column in the terra data table) for the worfklow written to a text file. This is provided in the terra data table upload.

  - ``--tech_platform_file_list``: the list of the tech_platform variable (column in the terra data table) for the worfklow written to a text file. This is provided in the terra data table upload.

  - ``--read_type_file_list``: the list of the read_type variable (column in the terra data table) for the worfklow written to a text file. This is provided in the terra data table upload.

  - ``--bam_file_list``: the list of the cov_out_txt variable (column in the terra data table) for the worfklow written to a text file. This variable is a file path to a file with the bam stats generated in the ``SC2_ont_assembly.wdl``, ``SC2_ilumina_se_assembly.wdl`` or ``SC2_illumina_pe_assembly.wdl`` from the bam stats task.

  - ``--percent_cvg_file_list``: the list of the cov_out_txt variable (column in the terra data table) for the worfklow written to a text file. This variable is a file path to a file with the bam stats generated in the ``SC2_ont_assembly.wdl``, ``SC2_ilumina_se_assembly.wdl`` or ``SC2_illumina_pe_assembly.wdl`` workflows from the ``calc_percent_coverage.py`` script called during the ``calc_percent_cvg`` task.

  - ``--pangolin_lineage_csv``: this is the lineage report csv file generated from pangolin during the ``pangolin`` task.

  - ``--pangolin_version``: this is the pangolin version which is defined as output during the ``pangolin`` task.

  - ``--assembler_version_table_list``: the list of the assembler_version variable (column in the terra data table) for the worfklow written to a text file. This is written to the terra data table during the ``SC2_ont_assembly.wdl``, ``SC2_ilumina_se_assembly.wdl`` or ``SC2_illumina_pe_assembly.wdl`` workflows.

  - ``--nextclade_clades_csv``: this is the ``{seq_run}_nextclade_results.csv`` file generated from the ``nextclade_json_parser.py`` script during the ``parse_nextclade`` task.

  - ``--nextclade_variants_csv``: this is the ``{seq_run}_nextclade_variant_summary.csv`` file generated from the ``nextclade_json_parser.py`` script during the ``parse_nextclade`` task.

  - ``--nextclade_version``: this is the nextclade version which is defined as output during the ``nextclade`` task.

  - ``--seq_run_file_list``: the list of the seq_run variable (column in the terra data table) for the worfklow written to a text file. This is provided in the terra data table upload.

### outputs
There are three outputs from this script. Example outputs can be found in the example data directory within this repo.   
1. ``{seq_run}_sequencing_results.csv``: summary of sequencing metrics for all samples within the sample set. Below is a table of the column headers and their description. There are a lot; we sort of just keep adding on.
|column header name| description |
|------------|-----------|
|``accession_id``| sample name|
|``plate_name``| internal id given to the sequencing plate|
|``plate_sample_well``| well location of the sample on the sequencing plate|
|``primer_set``|name of primer set used for tiled amplicon squenicng (Artic V3, Artic V4, Artic V4.1, Midnight or COVIDSeqV3)|
|``percent_non_ambigous_bases``| percent coverage; the total proportion of the genome that is covered not including regions where an N is called for a basecall|
|``nextclade``| the nextclade clade assignment|
|``panoglin_lineage``| the pangolin lineage assignment|
|``assembler_version``|assembler software version (either bwa or minimpa depending on assembly workflow used)|
|``omicron_spike_mutations``| list of spike mutations in the spike gene sequence that correspond to key omircon mutations identified in the sample consensus seqeunce|
|``delta_plus_spike_mutations``|list of spike mutations in the spike gene sequence that correspond to the ky delta plus mutations identified in the sample consensus sequence|
|``spike_mutations``| list of spike muations in the spike gene squence that correspond to key spike mutations identified in the sample consensus sequence (this column was created prior to VOCs and inlcudes spike mutatuations we were watching and has not been updated since)|
|``total_nucleotide_mutations``|number of SNPs in the consensus sequence genome|
|``total_AA substitutions``|number of amino acid substitions in the consensus sequence genome|
|``total_AA_deletions``|number of deletions in the consensus sequence genome|
|``mean_depth``| average number of reads per nucleotide site in the the conesnus sequnce genome|
|``number_aligned_bases``| total number of bases aligned to the refernece genome (including Ns; so pretty much tells you how much was cut of the ends of the genome)|
|``number_non_ambious_bases``|total number of non-N bases in the conesnus genome sequence|
|``number_seqs_in_fasta``|total number of sequences in the concensus fasta - should always be 1|
|``total_nucleotide_deletions``|number of deletions in the consensus genome sequence|
|``total_nucleotide_insertions``|number of insertions in the consensus genome seqeunce|
|``num_reads``|total sequencing reads|
|``mean_base_quality``|mean quality score across all reads|
|``mean_map_quality``|mean mapping quality score for reads mapping to reference genome sequence|
|``number_N_bases``|number of bases called as N in the consensus genome sequence|
|``nextclade_version``|nextclade version|
|``panolgin_version``| pangolin version|
|``pangoLEARN_conflict``|from pangolin lineage report file|
|``pangolin_ambiguity_score``|from pangolin lineage report file|
|``pangolin_scorpio_call``|from pangolin lineage report file|
|``pangolin_scropio_support``|from pangolin lineage report file|
|``pangolin_scropio_conflict``|from pangolin lineage report file|
|``panoglin_scorpio_notes``|from pangolin lineage report file|
|``pangolin_designation_Version``|from pangolin lineage report file|
|``pangolin_scorpio_version``|from pangolin lineage report file|
|``pangolin_constellation_version``|from pangolin lineage report file|
|``pngolin_is_designated``|from pangolin lineage report file|
|``pangolin_qc_status``|from pangolin lineage report file|
|``pangolin_qc_notes``|from pangolin lineage report file|
|``panoglin_note``|from pangolin lineage report file|
|``seq_run``|sequencing run name|
|``tech_platform``|seuqencing platform (e.g. Illumina MiSeq, Illumina NextSeq, Oxford Nanopore GridION)|
|``read_type``| single or paired end|
|``fasta_header``|name of the fasta header for gisaid submission (e.g. CO-CDPHE-{accession_id})|
|``analysis_date``|date assembly workflow ran|


2. ``{seq_run}_assembly_metrics.csv``: summary of sequencing metrics for all samples within the sample set. Very similiar to ``{seq_run}_sequencing_results.csv`` with a few less columns. For internal use to pull data from bucket. Below is a table of the column headers and their description.

  |column header name| description |
  |------------|-----------|
  |``accession_id``| sample name|
  |``plate_name``| internal id given to the sequencing plate|
  |``plate_sample_well``| well location of the sample on the sequencing plate|
  |``primer_set``|name of primer set used for tiled amplicon squenicng (Artic V3, Artic V4, Artic V4.1, Midnight or COVIDSeqV3)|
  |``percent_non_ambigous_bases``| percent coverage; the total proportion of the genome that is covered not including regions where an N is called for a basecall|
  |``nextclade``| the nextclade clade assignment|
  |``panoglin_lineage``| the pangolin lineage assignment|
  |``assembler_version``|assembler software version (either bwa or minimpa depending on assembly workflow used)|
  |``omicron_spike_mutations``| list of spike mutations in the spike gene sequence that correspond to key omircon mutations identified in the sample consensus seqeunce|
  |``delta_plus_spike_mutations``|list of spike mutations in the spike gene sequence that correspond to the ky delta plus mutations identified in the sample consensus sequence|
  |``spike_mutations``| list of spike muations in the spike gene squence that correspond to key spike mutations identified in the sample consensus sequence (this column was created prior to VOCs and inlcudes spike mutatuations we were watching and has not been updated since)|
  |``total_nucleotide_mutations``|number of SNPs in the consensus sequence genome|
  |``total_AA substitutions``|number of amino acid substitions in the consensus sequence genome|
  |``total_AA_deletions``|number of deletions in the consensus sequence genome|
  |``mean_depth``| average number of reads per nucleotide site in the the conesnus sequnce genome|
  |``number_aligned_bases``| total number of bases aligned to the refernece genome (including Ns; so pretty much tells you how much was cut of the ends of the genome)|
  |``number_non_ambious_bases``|total number of non-N bases in the conesnus genome sequence|
  |``number_seqs_in_fasta``|total number of sequences in the concensus fasta - should always be 1|
  |``total_nucleotide_deletions``|number of deletions in the consensus genome sequence|
  |``total_nucleotide_insertions``|number of insertions in the consensus genome seqeunce|
  |``num_reads``|total sequencing reads|
  |``mean_base_quality``|mean quality score across all reads|
  |``mean_map_quality``|mean mapping quality score for reads mapping to reference genome sequence|
  |``number_N_bases``|number of bases called as N in the consensus genome sequence|
  |``nextclade_version``|nextclade version|
  |``panolgin_version``| pangolin version|
  |``pangoLEARN_conflict``|from pangolin lineage report file|
  |``pangolin_ambiguity_score``|from pangolin lineage report file|
  |``pangolin_scorpio_call``|from pangolin lineage report file|
  |``pangolin_scropio_support``|from pangolin lineage report file|
  |``pangolin_scropio_conflict``|from pangolin lineage report file|
  |``panoglin_scorpio_notes``|from pangolin lineage report file|
  |``pangolin_designation_Version``|from pangolin lineage report file|
  |``pangolin_scorpio_version``|from pangolin lineage report file|
  |``pangolin_constellation_version``|from pangolin lineage report file|
  |``pngolin_is_designated``|from pangolin lineage report file|
  |``pangolin_qc_status``|from pangolin lineage report file|
  |``pangolin_qc_notes``|from pangolin lineage report file|
  |``panoglin_note``|from pangolin lineage report file|
  |``seq_run``|sequencing run name|
  |``tech_platform``|seuqencing platform (e.g. Illumina MiSeq, Illumina NextSeq, Oxford Nanopore GridION)|
  |``read_type``| single or paired end|
  |``fasta_header``|name of the fasta header for gisaid submission (e.g. CO-CDPHE-{accession_id})|
  |``analysis_date``|date assembly workflow ran|

3. ``{seq_run}_wgs_horizon_report.csv``: for internal use, parsing sequencing results into LIMS.Below is a table of the column headers and their description.
|column header name| description |
|------------|-----------|
|``accession_id``| sample name|
|``percent_coverage``| percent coverage|
|``pangolin_lineage``| pangolin lineage|
|``pangolin_version``| pangolin version|
|``report_to_epi``| this column is meaningless now but have to keep |
|``Run_Date``| date assembly workflow ran|
|``pangoLEARN_version``| this column is also not used but we have to keep it|

</details>

## details about working with sample sets
(so it's written down somewhere and I don't forget)
<details>
<summary>click to expand</summary>

Here I describe a way to create a single summary data table output for sample sets using a wwdl workflow in terra. (It's a bit clunkly but seems to work). Essentially this method enables one to create python lists from the columns in the terra data table when workflows are run as a sample set. The easiest way to explain this is with an example.

So for example, in the ``concat_seq_metrics_and_lineage_results.py``, there is the input flag ``--plate_name_file_list``. As input for this flag I use ``${write_lines(plate_name)}``. The plate_name corresponds to the plate_name column in the terra data table. Each element in column is a string. The ``write_lines()`` wdl function will write each element it's own line to a text file. Thus, the input into the python script is really a text file with a list of plate names. I then wrote some code that reads in the text file and generates a python list, with each line being a new element in the list. So it looks something like this:
```
plate_name_list = []
with open(plate_name_file_list) as f:
  for line in f:
    plate_name_list.append(line.strip())
```


Similiarly in some cases, instead of string variables being stored in a column wihtin the terra data table, file paths are stored (ie. the data type is a ``File`` or ``Array[File]`` in the case of sample sets). For example, in the ``concat_seq_metrics_and_lineage_results.py``, there is the input flag ``--percent_cvg_file_list``. As input for this flag I use ``${write_lines(percent_cvg_csv_non_empty)}``, where the percent_cvg_csv_non_empty variable corresponds to the column percent_cvg_csv. (note the non-empty part just means that the variable may be empty for some samples in the terra data table. To set the variable as input at the begining of the wdl I use: ``Array[File?] percent_cvg_csv``). Similiarly as above, the script will create a list of file paths from the text file. The script can then loop through the list of file paths, open each file, extract the data from that file, and store it in a list or other dataframe to be written out.

</details>
