import scanpy as sc
from anndata import read_h5ad
import pandas as pd
import numpy as np
import os
from os.path import join
import time
import argparse

# inhouse tools
import scTRS.util as util
import scTRS.data_loader as dl
import scTRS.method as md


"""
# Fixit
- 
"""

def convert_species_name(species):
    if species in ['Mouse', 'mouse', 'Mus_musculus', 'mus_musculus', 'mmusculus']:
        return 'mmusculus'
    if species in ['Human', 'human', 'Homo_sapiens', 'homo_sapiens', 'hsapiens']:
        return 'hsapiens'
    raise ValueError('# species name %s not supported'%species)


def main(args):
    sys_start_time = time.time()
        
    ###########################################################################################    
    ######                                    Parse Options                              ######
    ###########################################################################################    
    H5AD_FILE=args.h5ad_file
    H5AD_SPECIES=args.h5ad_species
    GS_FILE=args.gs_file
    GS_SPECIES=args.gs_species
    FLAG_FILTER=args.flag_filter=='True'
    FLAG_RAW_COUNT=args.flag_raw_count=='True'
    FLAG_RETURN_CTRL_RAW_SCORE=args.flag_return_ctrl_raw_score=='True'
    FLAG_RETURN_CTRL_NORM_SCORE=args.flag_return_ctrl_norm_score=='True'
    OUT_FOLDER=args.out_folder
    
    if H5AD_SPECIES!=GS_SPECIES:
        H5AD_SPECIES=convert_species_name(H5AD_SPECIES)
        GS_SPECIES=convert_species_name(GS_SPECIES)
    
    print('# H5AD_FILE: ', H5AD_FILE)
    print('# H5AD_SPECIES: ', H5AD_SPECIES)
    print('# GS_FILE: ', GS_FILE)
    print('# GS_SPECIES: ', GS_SPECIES)
    print('# OUT_FOLDER: ', OUT_FOLDER)
    print('# FLAG_FILTER: ', FLAG_FILTER)
    print('# FLAG_RAW_COUNT: ', FLAG_RAW_COUNT)
    print('# FLAG_RETURN_CTRL_RAW_SCORE: ', FLAG_RETURN_CTRL_RAW_SCORE)
    print('# FLAG_RETURN_CTRL_NORM_SCORE: ', FLAG_RETURN_CTRL_NORM_SCORE)
        
    ###########################################################################################    
    ######                                   Data Loading                                ######
    ###########################################################################################
    
    # Load .h5ad file 
    adata = read_h5ad(H5AD_FILE)
    if FLAG_FILTER:
        sc.pp.filter_cells(adata, min_genes=250)
        sc.pp.filter_genes(adata, min_cells=50)
    if FLAG_RAW_COUNT:
        sc.pp.normalize_per_cell(adata, counts_per_cell_after=1e4)
        sc.pp.log1p(adata)
    print('# H5AD_FILE loaded: ', adata.shape)
    
    # Load .gs file 
    df_gs = pd.read_csv(GS_FILE, sep='\t')
    df_gs.index = df_gs['TRAIT']
    print('# GS_FILE loaded: ', df_gs.shape)
    
    # Convert df_gs genes to H5AD_SPECIES genes
    if H5AD_SPECIES!=GS_SPECIES:
        # Load homolog file 
        df_hom = pd.read_csv('/n/holystore01/LABS/price_lab/Users/mjzhang/scTRS_data/gene_annotation/'
                             'mouse_human_homologs.txt', sep='\t')
        if (GS_SPECIES=='hsapiens') & (H5AD_SPECIES=='mmusculus'):
            dic_map = {x:y for x,y in zip(df_hom['HUMAN_GENE_SYM'], df_hom['MOUSE_GENE_SYM'])}
        elif (GS_SPECIES=='mmusculus') & (H5AD_SPECIES=='hsapiens'):
            dic_map = {x:y for x,y in zip(df_hom['MOUSE_GENE_SYM'], df_hom['HUMAN_GENE_SYM'])}
        else:
            raise ValueError('# Gene conversion from %s to %s is not supported'%(GS_SPECIES, H5AD_SPECIES))
            
        for trait in df_gs.index:
            human_gene_list = df_gs.loc[trait, 'GENESET'].split(',')
            mouse_gene_list = [dic_map[x] for x in set(human_gene_list)&set(dic_map.keys())]
            df_gs.loc[trait, 'GENESET'] = ','.join(mouse_gene_list)
        print('# GS_FILE converted from %s to %s genes'%(GS_SPECIES, H5AD_SPECIES))
    print('# sys_time=%0.1fs'%(time.time()-sys_start_time))
    
    ###########################################################################################    
    ######                                  Computation                                  ######
    ###########################################################################################
    
    # Compute score 
    for trait in df_gs.index:
        gene_list = df_gs.loc[trait,'GENESET'].split(',')
        df_res = md.score_cell(adata, gene_list, n_ctrl=500, 
                               return_ctrl_raw_score=FLAG_RETURN_CTRL_RAW_SCORE, 
                               return_ctrl_norm_score=FLAG_RETURN_CTRL_NORM_SCORE,
                               verbose=False)
        df_res.iloc[:,0:6].to_csv(join(OUT_FOLDER, '%s.score.gz'%trait), sep='\t', index=True, compression='gzip')
        if FLAG_RETURN_CTRL_RAW_SCORE|FLAG_RETURN_CTRL_NORM_SCORE:
            df_res.to_csv(join(OUT_FOLDER, '%s.full_score.gz'%trait), sep='\t', index=True, compression='gzip')
        print('# Score computed for %s (%d genes), sys_time=%0.1fs'%(trait, len(gene_list), time.time()-sys_start_time))
        
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='compute score')
    
    parser.add_argument('--h5ad_file', type=str, default=None)
    parser.add_argument('--h5ad_species', type=str, default=None)
    parser.add_argument('--gs_file', type=str, default=None)
    parser.add_argument('--gs_species', type=str, default=None)
    parser.add_argument('--flag_filter', type=str, default=None)
    parser.add_argument('--flag_raw_count', type=str, default=None)
    parser.add_argument('--flag_return_ctrl_raw_score', type=str, default=None)
    parser.add_argument('--flag_return_ctrl_norm_score', type=str, default=None)
    parser.add_argument('--out_folder', type=str, default=None)
    
    args = parser.parse_args()
    main(args)