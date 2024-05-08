"""
Assays module
"""

import numpy as np
import pandas as pd

from .phenoscore import runPhenoScore
from .utils import ann_score_df
from copy import copy


class PooledScreens(object):
    """
    pooledScreens class for processing CRISPR screen datasets
    """

    def __init__(self, adata, transformation='log2(x+1)', test='ttest', n_reps=3):
        """
        Args:
            adata (AnnData): AnnData object with adata.X as a matrix of sgRNA counts
            transformation (str): transformation to apply to the data before calculating phenotype scores
            test (str): statistical test to use for calculating phenotype scores
        """
        self.adata = adata
        self.transformation = transformation
        self.test = test
        self.n_reps = n_reps
        self.phenotypes = {}
        self.phenotype_names = []

    # def __repr__(self):
    #     descriptions = ''
    #     for score_level in self.phenotypes.keys():
    #         scores = "', '".join(self.phenotypes[score_level].columns.get_level_values(0).unique().to_list())
    #         descriptions += f"Phenotypes in score_level = '{score_level}':\n    scores: '{scores}'\n"

    #     return f'obs->samples\nvar->elementss\n\n{self.__repr__()}\n\n{descriptions}'

    def copy(self):
        return copy(self)

    def _add_phenotype_results(self, phenotype_name):
        if phenotype_name in self.phenotype_names:
            raise ValueError(f"Phenotype '{phenotype_name}' already exists in self.phenotype_names!")
        self.phenotype_names.append(phenotype_name)

    def calculateDrugScreen(self, t0, untreated, treated, db_untreated, db_treated, score_level, run_name=None):
        """
        Calculate `gamma`, `rho`, and `tau` phenotype scores for a drug screen dataset in a given `score_level`.
        To normalize by growth rate, the doubling rate of the untreated and treated conditions are required.

        Args:
            t0 (str): name of the untreated condition
            untreated (str): name of the untreated condition
            treated (str): name of the treated condition
            db_untreated (float): doubling rate of the untreated condition
            db_treated (float): doubling rate of the treated condition
            score_level (str): name of the score level
            run_name (str): name for the phenotype calculation run
        """
        # calculate phenotype scores: gamma, tau, rho
        gamma_name, gamma = runPhenoScore(
            self.adata, cond1=t0, cond2=untreated, growth_rate=db_untreated,
            n_reps=self.n_reps,
            transformation=self.transformation, test=self.test, score_level=score_level
        )
        tau_name, tau = runPhenoScore(
            self.adata, cond1=t0, cond2=treated, growth_rate=db_treated,
            n_reps=self.n_reps,
            transformation=self.transformation, test=self.test, score_level=score_level
        )
        # TO-DO: warning / error if db_untreated and db_treated are too close, i.e. growth_rate ~= 0.
        rho_name, rho = runPhenoScore(
            self.adata, cond1=untreated, cond2=treated, growth_rate=np.abs(db_untreated - db_treated),
            n_reps=self.n_reps,
            transformation=self.transformation, test=self.test, score_level=score_level
        )

        if not run_name: run_name = score_level
        # save all results into a multi-index dataframe
        self.phenotypes[run_name] = pd.concat({
            f'gamma:{gamma_name}': gamma, f'tau:{tau_name}': tau, f'rho:{rho_name}': rho
        }, axis=1)

        # save phenotype name for reference
        self._add_phenotype_results(f'gamma:{gamma_name}')
        self._add_phenotype_results(f'tau:{tau_name}')
        self._add_phenotype_results(f'rho:{rho_name}')
        
    def calculateFlowBasedScreen(self, low_bin, high_bin, score_level, run_name=None):
        """
        Calculate phenotype scores for a flow-based screen dataset.

        Args:
            low_bin (str): name of the low bin condition
            high_bin (str): name of the high bin condition
            score_level (str): name of the score level
            run_name (str): name for the phenotype calculation run
        """
        # calculate phenotype scores
        delta_name, delta = runPhenoScore(
            self.adata, cond1=low_bin, cond2=high_bin, n_reps=self.n_reps,
            transformation=self.transformation, test=self.test, score_level=score_level
        )

        if not run_name: run_name = score_level
        # save all results into a multi-index dataframe
        self.phenotypes[run_name] = pd.concat({
            f'delta:{delta_name}': delta
        }, axis=1)

        # save phenotype name for reference
        self._add_phenotype_results(f'delta:{delta_name}')

    def getPhenotypeScores(self, run_name, score_name, threshold=5, ctrl_label='negCtrl', target_col='target',pvalue_column='ttest pvalue', score_column='score'):
        """
        Get phenotype scores for a given score level

        Args:
            run_name (str): name of the phenotype calculation run to retrieve
            score_name (str): name of the score to retrieve, e.g. 'gamma', 'tau', 'rho', 'delta'
            threshold (float): threshold for filtering significant hits, default is 5
            ctrl_label (str): label for the negative control, default is 'negCtrl'
            target_col (str): column name for the target gene, default is 'target'
            pvalue_column (str): column name for the p-value, default is 'ttest pvalue'
            score_column (str): column name for the score, default is 'score'
        """
        if score_name not in self.phenotype_names:
            raise ValueError(f"Phenotype '{score_name}' not found in self.phenotype_names")
        
        keep_col = [target_col, pvalue_column, score_column]

        out = ann_score_df(
            self.phenotypes[run_name][score_name].loc[:,keep_col].set_index('target').rename(columns={pvalue_column:'pvalue'}),
            ctrl_label=ctrl_label, 
            threshold=threshold
        )

        return out


class GImaps(object):
    pass