version 1.0

workflow SC2_ont_assembly {

    input {
        String    gcs_fastq_dir
        String    sample_id
        String    barcode
        String    primer_set
        File    covid_genome
        File    preprocess_python_script
        File    primer_bed
    }
    call ListFastqFiles {
        input:
            gcs_fastq_dir = gcs_fastq_dir
    }
    call Demultiplex {
        input:
            fastq_files = ListFastqFiles.fastq_files,
            barcode = barcode
    }
    call Read_Filtering {
        input:
            fastq_files = Demultiplex.guppy_demux_fastq,
            barcode = barcode,
            sample_id = sample_id,
            primer_set = primer_set
    }
    call Medaka {
        input:
            filtered_reads = Read_Filtering.guppyplex_fastq,
            sample_id = sample_id,
            barcode = barcode,
            primer_bed = primer_bed
    }
    call Bam_stats {
        input:
            bam = Medaka.trimsort_bam,
            sample_id = sample_id,
            barcode = barcode
    }
    call Scaffold {
        input:
            sample_id = sample_id,
            barcode = barcode,
            ref = covid_genome,
            fasta = Medaka.consensus
    }

    call rename_fasta {
        input:
            sample_id = sample_id,
            fasta = Scaffold.scaffold_consensus
    }

    call calc_percent_cvg {
        input:
            sample_id = sample_id,
            fasta = rename_fasta.renamed_consensus,
            preprocess_python_script = preprocess_python_script
    }

    output {
        File barcode_summary = Demultiplex.barcode_summary
        Array[File] guppy_demux_fastq = Demultiplex.guppy_demux_fastq
        File filtered_fastq = Read_Filtering.guppyplex_fastq
        File sorted_bam = Medaka.sorted_bam
        File trimsort_bam = Medaka.trimsort_bam
        File trimsort_bai = Medaka.trimsort_bai
        File flagstat_out = Bam_stats.flagstat_out
        File samstats_out = Bam_stats.stats_out
        File covhist_out = Bam_stats.covhist_out
        File cov_out = Bam_stats.cov_out
        File variants = Medaka.variants
        File consensus = Medaka.consensus
        File scaffold_consensus = Scaffold.scaffold_consensus
        File renamed_consensus = rename_fasta.renamed_consensus
        File percent_cvg_csv = calc_percent_cvg.percent_cvg_csv
        String assembler_version = Medaka.assembler_version
    }
}

task ListFastqFiles {
    input {
        String gcs_fastq_dir
    }

    String indir = sub(gcs_fastq_dir, "/$", "")

    command <<<
        gsutil ls ~{indir}/* > fastq_files.txt
    >>>

    output {
        Array[File] fastq_files = read_lines("fastq_files.txt")
    }

    runtime {
        cpu:    1
        memory:    "1 GB"
        disks:    "local-disk 1 HDD"
        bootDiskSizeGb:    10
        preemptible:    0
        maxRetries:    0
        docker:    "us.gcr.io/broad-dsp-lrma/lr-utils:0.1.6"
    }
}

task Demultiplex {
    input {
        Array[File] fastq_files
        String barcode
    }

    Int disk_size = 3 * ceil(size(fastq_files, "GB"))

    command <<<
        set -e
        mkdir fastq_files
        ln -s ~{sep=' ' fastq_files} fastq_files
        ls -alF fastq_files
        guppy_barcoder --require_barcodes_both_ends --barcode_kits "EXP-NBD196" --fastq_out -i fastq_files -s demux_fastq
        ls -alF demux_fastq
    >>>

    output {
        Array[File] guppy_demux_fastq = glob("demux_fastq/${barcode}/*.fastq")
        File barcode_summary = "demux_fastq/barcoding_summary.txt"
    }

    runtime {
        cpu:    8
        memory:    "16 GB"
        disks:    "local-disk 100 SSD"
        preemptible:    0
        maxRetries:    3
        docker:    "genomicpariscentre/guppy:6.0.1"
    }
}

task Read_Filtering {
    input {
        Array[File] fastq_files 
        String barcode
        String sample_id
        String primer_set
    }

    Int max_length = if primer_set == "Midnight" then 1500 else 700

    command <<<
        set -e
        mkdir fastq_files
        ln -s ~{sep=' ' fastq_files} fastq_files
        ls -alF fastq_files
        
        artic guppyplex --min-length 400 --max-length ~{max_length} --directory fastq_files --output ~{sample_id}_~{barcode}.fastq

    >>>

    output {
        File guppyplex_fastq = "${sample_id}_${barcode}.fastq"
    }

    runtime {
        docker: "quay.io/staphb/artic-ncov2019:1.3.0"
        memory: "16 GB"
        cpu: 8
        disks: "local-disk 100 SSD"
        preemptible: 0
    }
}

task Medaka {
    input {
        String barcode
        String sample_id
        File filtered_reads
        File primer_bed
    }

    command <<<
    
        mkdir -p ./primer-schemes/nCoV-2019/Vuser
        cp /primer-schemes/nCoV-2019/V3/nCoV-2019.reference.fasta ./primer-schemes/nCoV-2019/Vuser/nCoV-2019.reference.fasta
        cp ~{primer_bed} ./primer-schemes/nCoV-2019/Vuser/nCoV-2019.scheme.bed
        
        artic -v > VERSION
        artic minion --medaka --medaka-model r941_min_high_g360 --normalise 20000 --threads 8 --scheme-directory ./primer-schemes --read-file ~{filtered_reads} nCoV-2019/Vuser ~{sample_id}_~{barcode}

    >>>

    output {
        File consensus = "${sample_id}_${barcode}.consensus.fasta"
        File sorted_bam = "${sample_id}_${barcode}.trimmed.rg.sorted.bam"
        File trimsort_bam = "${sample_id}_${barcode}.primertrimmed.rg.sorted.bam"
        File trimsort_bai = "${sample_id}_${barcode}.primertrimmed.rg.sorted.bam.bai"
        File variants = "${sample_id}_${barcode}.pass.vcf.gz"
        String assembler_version = read_string("VERSION")
    }

    runtime {
        docker: "quay.io/staphb/artic-ncov2019:1.3.0"
        memory: "16 GB"
        cpu: 8
        disks: "local-disk 100 SSD"
        preemptible: 0
    }
}

task Bam_stats {
    input {
        String sample_id
        String barcode
        File bam
    }

    Int disk_size = 3 * ceil(size(bam, "GB"))

    command {

        samtools flagstat ${bam} > ${sample_id}_${barcode}_flagstat.txt

        samtools stats ${bam} > ${sample_id}_${barcode}_stats.txt

        samtools coverage -m -o ${sample_id}_${barcode}_coverage_hist.txt ${bam}

        samtools coverage -o ${sample_id}_${barcode}_coverage.txt ${bam}

    }

    output {

        File flagstat_out  = "${sample_id}_${barcode}_flagstat.txt"
        File stats_out  = "${sample_id}_${barcode}_stats.txt"
        File covhist_out  = "${sample_id}_${barcode}_coverage_hist.txt"
        File cov_out  = "${sample_id}_${barcode}_coverage.txt"
    }

    runtime {
        cpu:    4
        memory:    "8 GiB"
        disks:    "local-disk " + disk_size + " HDD"
        bootDiskSizeGb:    10
        preemptible:    0
        maxRetries:    0
        docker:    "staphb/samtools:1.10"
    }
}

task Scaffold {
    input {
        String sample_id
        String barcode
        File fasta
        File ref
    }

    Int disk_size = 3 * ceil(size(fasta, "GB"))

    command {

        pyScaf.py -f ${fasta} -o ${sample_id}_${barcode}_consensus_scaffold.fa -r ${ref}

    }

    output {
        File scaffold_consensus = "${sample_id}_${barcode}_consensus_scaffold.fa"
    }

    runtime {
        cpu:    4
        memory:    "8 GiB"
        disks:    "local-disk " + disk_size + " HDD"
        bootDiskSizeGb:    10
        preemptible:    0
        maxRetries:    0
        docker:    "chrishah/pyscaf-docker"
    }
}

task rename_fasta {

    input {

        String sample_id
        File fasta
    }

    command {

        sed 's/>.*/>CO-CDPHE-~{sample_id}/' ~{fasta} > ~{sample_id}_consensus_renamed.fa

    }

    output {

        File renamed_consensus  = "${sample_id}_consensus_renamed.fa"

    }

    runtime {
        docker: "theiagen/utility:1.0"
        memory: "1 GB"
        cpu: 1
        disks: "local-disk 10 SSD"
    }
}

task calc_percent_cvg {

    input {

        File fasta
        String sample_id
        File preprocess_python_script
    }

    command {
        python ~{preprocess_python_script} \
          --sample_id ~{sample_id} \
          --fasta_file ~{fasta}
      }

    output {

      File percent_cvg_csv  = "${sample_id}_consensus_cvg_stats.csv"

    }

    runtime {

      docker: "mchether/py3-bio:v4"
      memory: "1 GB"
      cpu: 4
      disks: "local-disk 10 SSD"

    }

}
