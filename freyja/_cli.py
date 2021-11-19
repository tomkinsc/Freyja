import click
import pandas as pd
from freyja.convert_paths2barcodes import parse_tree_paths,\
     convert_to_barcodes, reversion_checking
from freyja.sample_deconv import buildLineageMap, build_mix_and_depth_arrays,\
    reindex_dfs, map_to_constellation, solve_demixing_problem
from freyja.updates import download_tree, convert_tree,\
                           get_curated_lineage_data
import os
import subprocess
import sys

locDir = os.path.abspath(os.path.join(os.path.realpath(__file__), os.pardir))


@click.group()
def cli():
    pass


@cli.command()
@click.argument('variants', type=click.Path(exists=True))
@click.argument('depths', type=click.Path(exists=True))
@click.option('--output', default='demixing_result.csv', help='Output file',
              type=click.Path(exists=False))
def demix(variants, depths, output):
    locDir = os.path.abspath(os.path.join(os.path.realpath(__file__),
                             os.pardir))
    df_barcodes = pd.read_csv(os.path.join(locDir,
                              'data/usher_barcodes.csv'), index_col=0)
    muts = list(df_barcodes.columns)
    mapDict = buildLineageMap()
    print('building mix/depth matrices')
    # assemble data from of (possibly) mixed samples
    mix, depths_ = build_mix_and_depth_arrays(variants, depths, muts)
    print('demixing')
    df_barcodes, mix, depths_ = reindex_dfs(df_barcodes, mix, depths_)
    sample_strains, abundances, error = solve_demixing_problem(df_barcodes,
                                                               mix,
                                                               depths_)
    localDict = map_to_constellation(sample_strains, abundances, mapDict)
    # assemble into series and write.
    sols_df = pd.Series(data=(localDict, sample_strains, abundances, error),
                        index=['summarized', 'lineages',
                        'abundances', 'resid'],
                        name=mix.name)
    sols_df.to_csv(output, sep='\t')


@cli.command()
def update():
    # get data from UShER
    print('Downloading a new global tree')
    download_tree()
    print('Getting outbreak data')
    get_curated_lineage_data()
    print("Converting tree info to barcodes")
    convert_tree()  # returns paths for each lineage
    # Now parse into barcode form
    lineagePath = os.path.join(os.curdir,"lineagePaths.txt")
    print('Building barcodes from global phylogenetic tree')
    df = pd.read_csv(lineagePath, sep='\t')
    df = parse_tree_paths(df)
    df_barcodes = convert_to_barcodes(df)
    df_barcodes = reversion_checking(df_barcodes)
    df_barcodes.to_csv(os.path.join(locDir, 'data/usher_barcodes.csv'))
    # delete files generated along the way that aren't needed anymore
    print('Cleaning up')
    os.remove(lineagePath)
    os.remove(os.path.join(locDir, "data/public-latest.all.masked.pb.gz"))


@cli.command()
@click.argument('bamfile', type=click.Path(exists=True))
@click.option('--ref', help='Reference',
              default=os.path.join(locDir,
                                   'data/NC_045512_Hu-1.fasta'),
              type=click.Path())
@click.option('--variants', help='Variant call output file', type=click.Path())
@click.option('--depths', help='Sequencing depth output file',
              type=click.Path())
def variants(bamfile, ref, variants, depths):
    bashCmd = f"samtools mpileup -aa -A -d 600000 -Q 20 -q 0 -B -f "\
              f"{ref} {bamfile} | tee >(cut -f1-4 > {depths}) |"\
              f" ivar variants -p {variants} -q 20 -t 0.0 -r {ref}"
    sys.stdout.flush()  # force python to flush
    completed = subprocess.run(bashCmd, shell=True, executable="/bin/bash",
                               stdout=subprocess.PIPE)
    sys.exit(completed.returncode)


@cli.command()
@click.argument('results', type=click.Path(exists=True))
@click.option('--output', default='aggregated_result.csv', help='Output file',
              type=click.Path(exists=False))
def aggregate(results,output):
    allResults = [pd.read_csv(results+fn,skipinitialspace=True,sep='\t',index_col=0) for fn in os.listdir(results)]
    df_demix = pd.concat(allDat,axis=1).T
    df_demix.index = [x.split('/')[1] for x in df_demix.index]
    df_demix.to_csv(output,sep='\t')

if __name__ == '__main__':
    cli()
