import pandas as pd
import sys


def parse_tree_paths(df):
    df = df.set_index('clade')
    # Make sure to check with new tree versions, lineages could get trimmed.
    df = df.drop_duplicates(keep='last')
    df['from_tree_root'] = df['from_tree_root'].fillna('')
    df['from_tree_root'] = df['from_tree_root']\
        .apply(lambda x: x.replace(' ', '').strip('>').split('>'))
    return df


def sortFun(x):
    # sort based on nuc position, ignoring nuc identities
    return int(x[1:(len(x)-1)])


def convert_to_barcodes(df):
    # builds simple barcodes, not accounting for reversions
    df_barcodes = pd.DataFrame()
    for clade in df.index:
        # sparse,binary encoding
        cladeSeries = pd.Series({c: 1 for c in
                                 df.loc[clade, 'from_tree_root']}, name=clade)
        df_barcodes = df_barcodes.append(cladeSeries)

    print('separating combined splits')
    df_barcodes = df_barcodes.drop(columns='')
    df_barcodes = df_barcodes.fillna(0)
    temp = pd.DataFrame()
    dropList = []
    for c in df_barcodes.columns:
        # if column includes multiple mutations,
        # split into separate columns and concatenates
        # TODO: change to concat, sometimes warning comes up.
        if "," in c:
            for mt in c.split(","):
                if mt not in temp.columns:
                    temp[mt] = df_barcodes[c]
                else:
                    # to handle multiple different groups with mut
                    temp[mt] += df_barcodes[c]
            dropList.append(c)
    df_barcodes = df_barcodes.drop(columns=dropList)
    df_barcodes = pd.concat((df_barcodes, temp), axis=1)
    df_barcodes = df_barcodes.groupby(axis=1, level=0).sum()
    return df_barcodes


def reversion_checking(df_barcodes):
    print('checking for mutation pairs')
    # check if a reversion is present.
    flipPairs = [(d, d[-1] + d[1:len(d)-1]+d[0]) for d in df_barcodes.columns
                 if (d[-1] + d[1:len(d)-1]+d[0]) in df_barcodes.columns]
    flipPairs = [list(fp) for fp in list(set(flipPairs))]
    # subtract lower of two pair counts to get the lineage defining mutations
    for fp in flipPairs:
        df_barcodes[fp] = df_barcodes[fp].subtract(df_barcodes[fp].min(axis=1),
                                                   axis=0)
    # drop all unused mutations (i.e. paired mutations with reversions)
    df_barcodes = df_barcodes.drop(
                columns=df_barcodes.columns[df_barcodes.sum(axis=0) == 0])
    return df_barcodes


if __name__ == '__main__':

    fn = sys.argv[1]
    df = pd.read_csv(fn, sep='\t')
    df = parse_tree_paths(df)
    df_barcodes = convert_to_barcodes(df)
    df_barcodes = reversion_checking(df_barcodes)
    # df_barcodes.to_csv('data/usher_barcodes.csv')
