#!/usr/bin/env python
# bwa_samtools_rocksort_picard 0.0.1
# Generated by dx-app-wizard.
#
# Basic execution pattern: Your app will run on a single machine from
# beginning to end.
#
# See https://wiki.dnanexus.com/Developer-Portal for documentation and
# tutorials on how to modify this file.
#
# DNAnexus Python Bindings (dxpy) documentation:
#   http://autodoc.dnanexus.com/bindings/python/current/

import os
import dxpy
import logging
import time


logger = logging.getLogger(__name__)
logger.addHandler(dxpy.DXLogHandler())
logger.propagate = False


try:
    from dx_applet_utilities import (
        common_job_operations as dx_utils,
        manage_command_execution as dx_exec,
        prepare_job_resources as dx_resources)
except ImportError:
    logger.error("Make sure to add the dx_applet_utilities to execDepends in dxapp.json!")
    sys.exit(1)


@dxpy.entry_point('main')
def main(reads_1, reference, reference_index, read_group_sample, loglevel,
    read_group_platform, read_group_platform_unit, read_group_library,
    reads_2=None, advanced_bwa_options=None, advanced_samtools_view_options=None,
    advanced_samtools_rocksort_options=None, advanced_picard_markdups_options=None,
    advanced_samtools_flagstat_options=None):

    """This is a dx applet that runs on the DNAnexus platform.

    :param: `reads_1`:
    :param: `reference`:
    :param: `reference_index`:
    :param: `read_group_sample`:
    :param: `read_group_platform`:
    :param: `read_group_platform_unit`:
    :param: `read_group_library`:
    :param: `advanced_bwa_options`:
    :param: `loglevel`:
    :param: `reads_2`:
    :param: `advanced_samtools_view_options`:
    :param: `advanced_samtools_rocksort_options`:
    :param: `advanced_picard_markdups_options`:
    :param: `advanced_samtools_flagstat_options`:
    :returns: This will return an dx object with output generated. This is
        actually taken care of by dxpy client libraries.
    """

    # Set up string variables that are not required

    if not advanced_bwa_options:
        advanced_bwa_options = ""

    if not advanced_samtools_view_options:
        advanced_samtools_view_options = ""

    if not advanced_samtools_rocksort_options:
        advanced_samtools_rocksort_options = ""

    if not advanced_picard_markdups_options:
        advanced_picard_markdups_options = ""

    if not advanced_samtools_flagstat_options:
        advanced_samtools_flagstat_options = ""

    if reads_2:
        if len(reads_1) != len(reads_2):
            logger.error("# of files for reads_1 and reads_2 does not match!")
            sys.exit(1)

    # Set up execution environment

    logger.setLevel(loglevel)
    cpus = dx_resources.number_of_cpus(1.0)
    max_ram = dx_resources.max_memory(0.85)
    logger.info("# of CPUs:{0}\nMax RAM:{1}".format(cpus, max_ram))

    temp_directories = [
        "genome/",
        "out/output_markdups_bams/",
        "out/output_cram_file_archive/",
        "out/download_quality_metrics/",
        "tmp/alignment/",
        "tmp/merged/",
        "tmp/sorted/",
        "tmp/markdup/"
    ]

    for temp_directory in temp_directories:
        create_dir = dx_exec.execute_command("mkdir -p {0}".format(
            temp_directory))
        dx_exec.check_execution_syscode(create_dir, "Created: {0}".format(
            temp_directory))
        chmod_dir = dx_exec.execute_command("chmod 777 -R {0}".format(
            temp_directory))
        dx_exec.check_execution_syscode(chmod_dir, "Modified: {0}".format(
            temp_directory))

    # The following line(s) initialize your data object inputs on the platform
    # into dxpy.DXDataObject instances that you can start using immediately.

    reference_filename = "in/reference/{0}".format(
        dxpy.DXFile(reference).describe()["name"])
    reference_index_filename = "in/reference_index/{0}".format(
        dxpy.DXFile(reference_index).describe()["name"])

    # Will prepare an array that has each pair of sequencing reads (read_1 and
    # read_2) to pass to BWA to align

    reads_to_align = []

    for index, file_object in enumerate(reads_1):

        # DNAnexus has this funky behavior when you have > 9 files, it creates
        # a folder in/parameter/08/file - this resolves that issue
        if len(reads_1) > 9 and index < 10:
            index = "0{0}".format(index)

        reads_1_filename = dxpy.DXFile(file_object).describe()["name"]
        if reads_2:
            reads_2_filename = dxpy.DXFile(reads_2[index]).describe()["name"]


        if dx_utils.check_compression(reads_1_filename) == '.bz2':
            reads_1_filename = "'<bunzip2 -c in/reads_1/{0}/{1}'".format(index,
                reads_1_filename)
        else:
            reads_1_filename = "in/reads_1/{0}/{1}".format(index,
                reads_1_filename)

        if reads_2:
            if dx_utils.check_compression(reads_2_filename) == ".bz2":
                reads_2_filename = "'<bunzip2 -c in/reads_2/{0}/{1}'".format(
                    index, reads_2_filename)
            else:
                reads_2_filename = "in/reads_2/{0}/{1}".format(index,
                    reads_2_filename)

        if reads_2_filename:
            read_files = "{0} {1}".format(reads_1_filename, reads_2_filename)
        else:
            read_files = "{0}".format(reads_1_filename)

        reads_to_align.append(read_files)

    # The following line(s) download your file inputs to the local file system
    # using variable names for the filenames.

    dx_download_inputs_cmd = "dx-download-all-inputs --parallel"
    download_inputs = dx_exec.execute_command(dx_download_inputs_cmd)
    dx_exec.check_execution_syscode(download_inputs, "Download input files")

    # The following line(s) are the body of the applet that
    # executes the bioinformatics processes

    # Prepare refernce genome for alignment

    untar_reference_index_cmd = "tar -xzvf {0} -C genome".format(
        reference_index_filename)
    unzip_reference_genome_cmd = "gzip -dc {0} > genome/genome.fa".format(
        reference_filename)
    reference_filename = "genome/genome.fa"

    untar_reference_index = dx_exec.execute_command(untar_reference_index_cmd)
    dx_exec.check_execution_syscode(untar_reference_index, "Untar reference Index")
    unzip_reference_genome = dx_exec.execute_command(unzip_reference_genome_cmd)
    dx_exec.check_execution_syscode(untar_reference_index, "Unzip reference genome")

    # FASTQ to BAM conversion

    read_group = "@RG\\tID:{0}-{1}\\tSM:{0}\\tCN:Genesis\\tPL:{2}\\tLB:{3}\\tPU:{1}".format(
        read_group_sample, read_group_platform_unit, read_group_platform,
        read_group_library)
    bwa_mem_cmd = "bwa mem {0} -t {1} -R \"{2}\" {3}".format(
        advanced_bwa_options, cpus, read_group, reference_filename)
    samtools_view_cmd = "samtools view {0} -hb -@ {1} -T {2} /dev/stdin".format(
        advanced_samtools_view_options, cpus, reference_filename)
    bam_files = []

    for index, reads in enumerate(reads_to_align):
        aligned_bam = "tmp/alignment/{0}.{1}.bam".format(read_group_sample, index)
        alignment_cmd = "{0} {1} | {2} -o {3}".format(bwa_mem_cmd, reads,
            samtools_view_cmd, aligned_bam)

        alignment = dx_exec.execute_command(alignment_cmd, debug=True)
        dx_exec.check_execution_syscode(alignment, "Alignemnt of reads {0}".format(
            index))

        bam_files.append(aligned_bam)

    # Clean up FASTQ files to make space on HDDs (especially useful for WGS)

    clean_up_fastq_cmd = "rm -rf in/reads_*/"
    clean_up_fastq = dx_exec.execute_command(clean_up_fastq_cmd)
    dx_exec.check_execution_syscode(clean_up_fastq, "FASTQ removed")

    # Merge BAM files if more than one pair of reads exist

    if len(bam_files) > 1:
        merged_bam = merged_bam = "tmp/merged/{0}.merged.bam".format(
            read_group_sample)
        samtools_merge_cmd = "samtools merge -@ {0} {1} {2}".format(cpus,
            merged_bam, " ".join(bam_files))
        samtools_merge = dx_exec.execute_command(samtools_merge_cmd)
        dx_exec.check_execution_syscode(samtools_merge, "Merge BAM")

        # Make sure to reset the bam_files array, it will be used for the next
        # set of processes
        bam_files = [merged_bam]

    sorted_bam = "tmp/sorted/sorted.{0}".format(read_group_sample)
    samtools_sort_merged_cmd = "dx-samtools rocksort {0} -@ {1} -m {2}M {3} {4}".format(
        advanced_samtools_rocksort_options, cpus, max_ram,
        bam_files[0], sorted_bam)
    samtools_sort_merge = dx_exec.execute_command(samtools_sort_merged_cmd)
    dx_exec.check_execution_syscode(samtools_sort_merge, "Sort BAM")

    # Clean up temporary BAM files - this will save space on HDDs (useful for WGS)

    tmp_bam_directories = ["tmp/alignment/", "tmp/merged/"]
    for tmp_bam_directory in tmp_bam_directories:
        clean_up_bam = dx_exec.execute_command("rm -rf {0}".format(
            tmp_bam_directory))
        dx_exec.check_execution_syscode(clean_up_bam, "Clean up BAM")

    # Mark duplicates in BAM file

    markdup_bam = "out/output_markdups_bams/{0}.markdups.bam".format(read_group_sample)
    dups_metrics_file = "{0}.markdups.metrics.txt".format(read_group_sample)
    picard_markdup_cmd = 'java -Xmx{0}m -jar /opt/jar/picard.jar MarkDuplicates {1} I={2} O={3} M={4}'.format(
        max_ram, advanced_picard_markdups_options, sorted_bam,
        markdup_bam, dups_metrics_file)
    picard_markdup = dx_exec.execute_command(picard_markdup_cmd, debug=True)
    dx_exec.check_execution_syscode(picard_markdup, "Mark Duplicates")

    samtools_index_cmd = "samtools index {0}".format(markdup_bam)
    samtools_index = dx_exec.execute_command(samtools_index_cmd)
    dx_exec.check_execution_syscode(samtools_index, "Index BAM file")

    # Clean up temporary BAM files - this will save space on HDDs (useful for WGS)

    tmp_bam_directories = ["tmp/sorted/"]
    for tmp_bam_directory in tmp_bam_directories:
        clean_up_bam = dx_exec.execute_command("rm -rf {0}".format(
            tmp_bam_directory))
        dx_exec.check_execution_syscode(clean_up_bam, "Clean up BAM")

    # FlagStat BAM file - get some prelim alignment metrics

    flagstat_output = "out/download_quality_metrics/{0}.stats.flagstat".format(
        read_group_sample)
    samtools_flagstat_cmd = 'samtools flagstat {0} {1} > {2}'.format(
        advanced_samtools_flagstat_options, markdup_bam, flagstat_output)
    samtools_flagstat = dx_exec.execute_command(samtools_flagstat_cmd)
    dx_exec.check_execution_syscode(samtools_flagstat, "flagstat BAM file")

    # Convert BAM file to CRAM file

    cram_file = "out/output_cram_file_archive/{0}.cram".format(read_group_sample)
    samtools_cram_cmd = "samtools view {0} -C -@ {1} -T {2} {3} -o {4}".format(
        advanced_samtools_view_options, cpus, reference_filename,
        markdup_bam, cram_file)
    samtools_cram = dx_exec.execute_command(samtools_cram_cmd)
    dx_exec.check_execution_syscode(samtools_cram, "Convert BAM to CRAM")

    # Remove index files

    rm_bai_files_cmd = "rm -rf out/output_markdups_bams/*bai"
    rm_bai_files = dx_exec.execute_command(rm_bai_files_cmd)
    dx_exec.check_execution_syscode(rm_bai_files, "Remove BAM index files")

    rm_cai_files_cmd = "rm -rf out/output_cram_file_archive/*cai"
    rm_cai_files = dx_exec.execute_command(rm_cai_files_cmd)
    dx_exec.check_execution_syscode(rm_cai_files, "Remove CRAM index files")

    # The following line(s) use the Python bindings to upload your file outputs
    # after you have created them on the local file system.  It assumes that you
    # have used the output field name for the filename for each output, but you
    # can change that behavior to suit your needs.

    dx_upload_outputs_cmd = "dx-upload-all-outputs --parallel"
    download_outputs = dx_exec.execute_command(dx_upload_outputs_cmd)
    dx_exec.check_execution_syscode(download_outputs, "Upload outputs")

    # The following line fills in some basic dummy output and assumes
    # that you have created variables to represent your output with
    # the same name as your output fields.

    upload_output_object = dx_utils.load_json_from_file("job_output.json")
    return dx_utils.prepare_job_output(
        dx_output_object=upload_output_object,
        must_be_array=False
    )

dxpy.run()
