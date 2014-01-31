#!/usr/bin/env python
# File created on 02 Nov 2011
from __future__ import division

__author__ = "Greg Caporaso"
__copyright__ = "Copyright 2011, The QIIME project"
__credits__ = ["Greg Caporaso"]
__license__ = "GPL"
__version__ = "1.8.0-dev"
__maintainer__ = "Greg Caporaso"
__email__ = "gregcaporaso@gmail.com"

from os import makedirs

from qiime.util import (parse_command_line_parameters,
                        make_option, get_options_lookup, load_qiime_config)
from qiime.parse import parse_qiime_parameters
from qiime.workflow.util import (validate_and_set_jobs_to_start,
                                 call_commands_serially, print_commands, no_status_updates, print_to_stdout)
from qiime.workflow.pick_open_reference_otus import (
    pick_subsampled_open_reference_otus,
    iterative_pick_subsampled_open_reference_otus)

qiime_config = load_qiime_config()
options_lookup = get_options_lookup()

script_info = {}
script_info['brief_description'] = """
This script is used to pick subsampled open reference OTUs"""
script_info['script_description'] = """
This script is broken down into 4 possible OTU picking steps, and 2 steps 
involving the creation of OTU tables and trees. The commands for each step are 
described below, including what the input and resulting output files are. 
Additionally, the optional specified parameters of this script that can be passed
are referenced. Note that the workflow of this script was designed to minimize
runtime for very large datasets, and therefore if you wish to have possibly more
detailed results (with slower runtimes), a few parameters in particular can be 
changed.

Step 1) Prefilting and Picking Closed Reference OTUs
The first step is to prefilter the input fasta file to remove sequences that do 
not hit the reference database with a given sequence identity. By default, the 
prefilter reference database is assumed to be the same as the OTU picking 
reference database, and the prefilter percent identity has a default of 0.60, 
although both of this prefilter parameters can be changed with the options:
--prefilter_refseqs_fp
--prefilter_percent_id
This filtering is accomplished by picking closed reference OTUs at the specified
prefilter percent id to produce:
prefilter_otus/seqs_otus.log
prefilter_otus/seqs_otus.txt
prefilter_otus/seqs_failures.txt
prefilter_otus/seqs_clusters.uc
Next, the seqs_failures.txt file is used to remove these failed sequences from 
the original input fasta file to produce:
prefilter_otus/prefiltered_seqs.fna
This prefiltered_seqs.fna file is then considered to contain the high quality 
sequences which are used for downstream OTU picking, and the failed sequences 
are discarded.

With the prefiltered_seqs.fna file, the Step 1 closed reference OTU picking is 
done against the supplied reference database. This command produces:
step1_otus/prefiltered_seqs_clusters.uc
step1_otus/prefiltered_seqs_failures.txt
step1_otus/prefiltered_seqs_otus.log
step1_otus/prefiltered_seqs_otus.txt 

The representative sequence for each of the Step 1 picked OTUs are selected to 
produce:
step1_otus/step1_rep_set.fna

Next, the sequences that failed to hit the reference database in Step 1 are 
filtered from the Step 1 input fasta file to produce:
step1_otus/failures.fasta
Then an additional filtering step occurs whereby the failures.fasta file is 
randomly subsampling a certain percentage of the failed sequences to produce a 
subsampled_failures.fna (which is not written to an output file). The percent 
of the Step 1 failures to keep for a later de novo step can be specified with 
the -s PERCENT_SUBSAMPLE option. Larger percentages than the default can be 
specified to produce more comprehensive results, but the the compute time 
required will be longer.

** Note that Steps 2 and 3 are paired together to decrease compute time. Ideally, 
what you'd like to do is to pick de novo OTUs using all of the sequences that 
failed to hit the reference database in Step 1. However, depending on your samples 
there is the possibility that the number of failed sequences is still so large 
that picking de novo OTUs is prohibitively expensive in terms of compute. In 
order to get around this computational hit, a subset of the failed sequence are 
clustered de novo and are used as the 'reference' database for running a 
reference-based OTU picking algorithm.

Step 2) Pick de novo OTUs on the subsampled_failures.fna
This step is used to create the temporary reference database for Step 3 OTU 
picking. The randomly subsampled failure sequences from Step 1 are pre-clustered 
de novo to produce:
step2_otus/subsampled_seqs_clusters.uc
step2_otus/subsampled_seqs_otus.log
step2_otus/subsampled_seqs_otus.txt

The representative sequence for the clustered OTUs is then chosen to produce:
step2_otus/step2_rep_set.fna

Step 3) Pick Closed Reference OTUs against Step 2 de novo OTUs
Closed reference OTU picking is performed using the failures.fasta file created 
in Step 1 against the 'reference' de novo database created in Step 2 to produce:
step3_otus/failures_seqs_clusters.uc
step3_otus/failures_seqs_failures.txt
step3_otus/failures_seqs_otus.log
step3_otus/failures_seqs_otus.txt

Assuming the user has NOT passed the --suppress_step4 flag:
The sequences which failed to hit the reference database in Step 3 are removed 
from the Step 3 input fasta file to produce:
step3_otus/failures_failures.fasta

Step 4) Additional de novo OTU picking
It is assumed by this point that the majority of sequences have been assigned 
to an OTU, and thus the sequence count of failures_failures.fasta is small 
enough that de novo OTU picking is computationally feasible. However, depending 
on the sequences being used, it might be that the failures_failures.fasta file 
is still prohibitively large for de novo clustering, and the jobs might take 
too long to finish. In this case it is likely that the user would want to pass 
the --suppress_step4 flag to avoid this additional de novo step.

A final round of de novo OTU picking is done on the failures_failures.fasta file 
to produce:
step4_otus/failures_failures_cluster.uc
step4_otus/failures_failures_otus.log
step4_otus/failures_failures_otus.txt

A representative sequence for each cluster is chosen to produce:
step4_otus/step4_rep_set.fna

Step 5) Produce the final OTU map and rep set
If Step 4 is completed, the OTU maps from Step 1, Step 3, and Step 4 are 
concatenated to produce:
final_otu_map.txt

If Step 4 was not completed, the OTU maps from Steps 1 and Step 3 are 
concatenated together to produce:
final_otu_map.txt

Next, the minimum specified OTU size required to keep an OTU is specified with
the --min_otu_size flag. For example, if the user left the --min_otu_size as the 
default value of 2, requiring each OTU to contain at least 2 sequences, the any
OTUs which failed to meet this criteria would be removed from the
final_otu_map.txt to produce:
final_otu_map_mc2.txt

If --min_otu_size 10 was passed, it would produce:
final_otu_map_mc10.txt

The final_otu_map_mc2.txt is used to build the final representative set:
rep_set.fna

Step 6) Making the OTU tables and trees
An OTU table is built using the final_otu_map_mc2.txt file to produce:
otu_table_mc2.biom

If the run_assign_tax flag is passed, then taxonomy will be assigned to each of 
the represenatative sequences in the final rep_set produced in Step 5, producing:
rep_set_tax_assignments.log
rep_set_tax_assignments.txt
This taxonomic metadata is then added to the otu_table_mc2.biom to produce:
otu_table_mc_w_tax.biom

If the run_align_and_tree flag is passed, then the rep_set.fna file will be used 
to align the sequences and build the phylogenetic tree, which includes the de 
novo OTUs. Any sequences that fail to align are removed from the rep_set.fna to 
produce:
otu_table_mc_no_pynast_failures.biom
rep_set.tre

Passing both the run_assign_tax and run_align_and_tree options will produce:
otu_table_mc_w_tax_no_pynast_failures.biom

It is important to remember that with a large workflow script like this that 
the user can jump into intermediate steps. For example, imagine that for some 
reason the script was interrupted on Step 2, and the user did not want to go 
through the process of re-picking OTUs as was done in Step 1. They can simply 
rerun the script and pass in the:
--step_1_otu_map_fp
--step1_failures_fasta_fp
parameters, and the script will continue with Steps 2 - 4.

Steps 2 - 4 cannot be 'saved' and must be re-run if interrupted because they 
involve de novo OTU picking.
"""

script_info['script_usage'] = []

script_info['script_usage'].append(("", "Run the subsampled open-reference "
                                    "OTU picking workflow on seqs1.fna using refseqs.fna as the reference "
                                    "collection. ALWAYS SPECIFY ABSOLUTE FILE PATHS (absolute path "
                                    "represented here as $PWD, but will generally look something like "
                                    "/home/ubuntu/my_analysis/", "%prog -i $PWD/seqs1.fna -r $PWD/refseqs.fna "
                                    "-o $PWD/ucrss/ -s 0.1 -p $PWD/ucrss_params.txt"))

script_info['script_usage'].append(("", "Run the subsampled open-reference "
                                    "OTU picking workflow on seqs1.fna using refseqs.fna as the reference "
                                    "collection and using usearch61 and usearch61_ref as the OTU picking "
                                    "methods. ALWAYS SPECIFY ABSOLUTE FILE PATHS (absolute path represented "
                                    "here as $PWD, but will generally look something like "
                                    "/home/ubuntu/my_analysis/", "%prog -i $PWD/seqs1.fna -r $PWD/refseqs.fna "
                                    "-o $PWD/ucrss_usearch/ -s 0.1 -p $PWD/ucrss_params.txt -m usearch61"))

script_info['script_usage'].append(("", "Run the subsampled open-reference "
                                    "OTU picking workflow in iterative mode on seqs1.fna and seqs2.fna using "
                                    "refseqs.fna as the initial reference collection. ALWAYS SPECIFY ABSOLUTE "
                                    "FILE PATHS (absolute path represented here as $PWD, but will generally "
                                    "look something like /home/ubuntu/my_analysis/", "%prog "
                                    "-i $PWD/seqs1.fna,$PWD/seqs2.fna -r $PWD/refseqs.fna -o $PWD/ucrss_iter/ "
                                    "-s 0.1 -p $PWD/ucrss_params.txt"))

script_info['script_usage'].append(("", "Run the subsampled open-reference "
                                    "OTU picking workflow in iterative mode on seqs1.fna and seqs2.fna using "
                                    "refseqs.fna as the initial reference collection. This is useful if "
                                    "you're working with marker genes that do not result in useful alignment "
                                    "(e.g., fungal ITS). ALWAYS SPECIFY ABSOLUTE FILE PATHS (absolute path "
                                    "represented here as $PWD, but will generally look something like "
                                    "/home/ubuntu/my_analysis/", "%prog -i $PWD/seqs1.fna,$PWD/seqs2.fna -r "
                                    "$PWD/refseqs.fna -o $PWD/ucrss_iter_no_tree/ -s 0.1 "
                                    "-p $PWD/ucrss_params.txt --suppress_align_and_tree"))

script_info['script_usage'].append(("", "Run the subsampled open-reference "
                                    "OTU picking workflow in iterative mode on seqs1.fna and seqs2.fna using "
                                    "refseqs.fna as the initial reference collection, suppressing assignment "
                                    "of taxonomy. This is useful if you're working with a reference "
                                    "collection without associated taxonomy. ALWAYS SPECIFY ABSOLUTE FILE "
                                    "PATHS (absolute path represented here as $PWD, but will generally look "
                                    "something like /home/ubuntu/my_analysis/", "%prog "
                                    "-i $PWD/seqs1.fna,$PWD/seqs2.fna -r $PWD/refseqs.fna "
                                    "-o $PWD/ucrss_iter_no_tax/ -s 0.1 -p $PWD/ucrss_params.txt "
                                    "--suppress_taxonomy_assignment"))

script_info['script_usage_output_to_remove'] = [
    '$PWD/ucrss/', '$PWD/ucrss_iter/', '$PWD/ucrss_usearch/',
    '$PWD/ucrss_iter_no_tree/', '$PWD/ucrss_iter_no_tax/'
]

script_info['output_description'] = ""
script_info['required_options'] = [
    make_option('-i', '--input_fps', help='the input sequences filepath or '
                'comma-separated list of filepaths', type='existing_filepaths'),
    make_option('-r', '--reference_fp', type='existing_filepath', help='the '
                'reference sequences'),
    make_option('-o', '--output_dir', type='new_dirpath', help='the output '
                'directory'),
]

script_info['optional_options'] = [
    make_option('-m', '--otu_picking_method', type='choice',
                choices=['uclust', 'usearch61'], help=('The OTU picking method to use '
                                                       'for reference and de novo steps. Passing usearch61, for example, '
                                                       'means that usearch61 will be used for the de novo steps and '
                                                       'usearch61_ref will be used for reference steps. [default: %default]'),
                default='uclust'),
    make_option('-p', '--parameter_fp', type='existing_filepath', help='path '
                'to the parameter file, which specifies changes to the default '
                'behavior. See http://www.qiime.org/documentation/file_formats.html#'
                'qiime-parameters . [if omitted, default values will be used]'),
    make_option('--prefilter_refseqs_fp', type='existing_filepath',
                help='the reference sequences to use for the prefilter, if different '
                'from the reference sequecnces to use for the OTU picking [default: '
                'same as passed for --reference_fp]'),
    make_option('-n', '--new_ref_set_id', default='New', type='string',
                help='Unique identifier for OTUs that get created in this ref set '
                '(this is useful to support combining of reference sets) '
                '[default:%default]'),
    make_option('-f', '--force', action='store_true', dest='force',
                help='Force overwrite of existing output directory (note: existing '
                'files in output_dir will not be removed) [default: %default]'),
    # print to shell script doesn't work for this workflow as there is a mix of
    # command calls and api calls. i need to refactor the workflow scripts...
    # make_option('-w','--print_only',action='store_true',
    #        dest='print_only',help='Print the commands but don\'t call them -- '+
    #        'useful for debugging [default: %default]',default=False),
    make_option('-a', '--parallel', action='store_true', dest='parallel',
                default=False, help='Run in parallel where available '
                '[default: %default]'),
    options_lookup['jobs_to_start_workflow'],
    make_option('-s', '--percent_subsample', type='float', default='0.001',
                help='Percent of failure sequences to include in the subsample to '
                'cluster de novo (larger numbers should give more comprehensive '
                'results but will be slower) [default:%default]'),
    make_option('--prefilter_percent_id', type='float', default='0.60',
                help='Sequences are pre-clustered at this percent id against the '
                'reference and any reads which fail to hit are discarded (a quality '
                'filter); pass 0.0 to disable [default:%default]'),
    make_option('--step1_otu_map_fp', type='existing_filepath',
                help='reference OTU picking OTU map  (to avoid rebuilding if one has '
                'already been built)'),
    make_option('--step1_failures_fasta_fp', type='existing_filepath',
                help='reference OTU picking failures fasta filepath  (to avoid '
                'rebuilding if one has already been built)'),
    make_option('--suppress_step4', action='store_true', default=False,
                help='suppress the final de novo OTU picking step  (may be necessary '
                'for extremely large data sets) [default: %default]'),
    make_option('--min_otu_size', type='int', default=2,
                help='the minimum otu size (in number of sequences) to retain the otu '
                '[default: %default]'),
    make_option('--suppress_taxonomy_assignment', action='store_true',
                default=False, help='skip the taxonomy assignment step, resulting in '
                'an OTU table without taxonomy [default: %default]'),
    make_option('--suppress_align_and_tree', action='store_true',
                default=False,
                help='skip the sequence alignment and tree-building steps [default: '
                '%default]')
]
script_info['version'] = __version__


def main():
    option_parser, opts, args = parse_command_line_parameters(**script_info)
    verbose = opts.verbose

    input_fps = opts.input_fps
    refseqs_fp = opts.reference_fp
    output_dir = opts.output_dir
    otu_picking_method = opts.otu_picking_method
    verbose = opts.verbose
    print_only = False
    percent_subsample = opts.percent_subsample
    new_ref_set_id = opts.new_ref_set_id
    prefilter_refseqs_fp = opts.prefilter_refseqs_fp
    prefilter_percent_id = opts.prefilter_percent_id
    if prefilter_percent_id == 0.0:
        prefilter_percent_id = None

    if otu_picking_method == 'uclust':
        denovo_otu_picking_method = 'uclust'
        reference_otu_picking_method = 'uclust_ref'
    elif otu_picking_method == 'usearch61':
        denovo_otu_picking_method = 'usearch61'
        reference_otu_picking_method = 'usearch61_ref'
    else:
        # it shouldn't be possible to get here
        option_parser.error('Unkown OTU picking method: %s' %
                            otu_picking_method)

    parallel = opts.parallel
    # No longer checking that jobs_to_start > 2, but
    # commenting as we may change our minds about this.
    #if parallel: raise_error_on_parallel_unavailable()

    if opts.parameter_fp:
        try:
            parameter_f = open(opts.parameter_fp, 'U')
        except IOError:
            raise IOError("Can't open parameters file (%s). Does it exist? "
                          "Do you have read access?" % opts.parameter_fp)
        params = parse_qiime_parameters(parameter_f)
        parameter_f.close()
    else:
        params = parse_qiime_parameters([])
        # empty list returns empty defaultdict for now

    jobs_to_start = opts.jobs_to_start
    default_jobs_to_start = qiime_config['jobs_to_start']
    validate_and_set_jobs_to_start(params, jobs_to_start,
                                   default_jobs_to_start, parallel, option_parser)

    try:
        makedirs(output_dir)
    except OSError:
        if opts.force:
            pass
        else:
            option_parser.error("Output directory already exists. Please "
                                "choose a different directory, or force overwrite with -f.")

    if print_only:
        command_handler = print_commands
    else:
        command_handler = call_commands_serially

    if verbose:
        status_update_callback = print_to_stdout
    else:
        status_update_callback = no_status_updates

    if len(input_fps) == 1:
        pick_subsampled_open_reference_otus(input_fp=input_fps[0],
                                            refseqs_fp=refseqs_fp, output_dir=output_dir,
                                            percent_subsample=percent_subsample, new_ref_set_id=new_ref_set_id,
                                            command_handler=command_handler, params=params,
                                            min_otu_size=opts.min_otu_size,
                                            run_assign_tax=not opts.suppress_taxonomy_assignment,
                                            run_align_and_tree=not opts.suppress_align_and_tree,
                                            qiime_config=qiime_config,
                                            prefilter_refseqs_fp=prefilter_refseqs_fp,
                                            prefilter_percent_id=prefilter_percent_id,
                                            step1_otu_map_fp=opts.step1_otu_map_fp,
                                            step1_failures_fasta_fp=opts.step1_failures_fasta_fp,
                                            parallel=parallel, suppress_step4=opts.suppress_step4, logger=None,
                                            denovo_otu_picking_method=denovo_otu_picking_method,
                                            reference_otu_picking_method=reference_otu_picking_method,
                                            status_update_callback=status_update_callback)
    else:
        iterative_pick_subsampled_open_reference_otus(input_fps=input_fps,
                                                      refseqs_fp=refseqs_fp, output_dir=output_dir,
                                                      percent_subsample=percent_subsample, new_ref_set_id=new_ref_set_id,
                                                      command_handler=command_handler, params=params,
                                                      min_otu_size=opts.min_otu_size,
                                                      run_assign_tax=not opts.suppress_taxonomy_assignment,
                                                      run_align_and_tree=not opts.suppress_align_and_tree,
                                                      qiime_config=qiime_config,
                                                      prefilter_refseqs_fp=prefilter_refseqs_fp,
                                                      prefilter_percent_id=prefilter_percent_id,
                                                      step1_otu_map_fp=opts.step1_otu_map_fp,
                                                      step1_failures_fasta_fp=opts.step1_failures_fasta_fp,
                                                      parallel=parallel, suppress_step4=opts.suppress_step4, logger=None,
                                                      denovo_otu_picking_method=denovo_otu_picking_method,
                                                      reference_otu_picking_method=reference_otu_picking_method,
                                                      status_update_callback=status_update_callback)

if __name__ == "__main__":
    main()
