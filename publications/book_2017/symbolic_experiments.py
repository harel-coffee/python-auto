import os
import numpy as np
import time
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
sns.set(style="white", color_codes=True)
from tools import AnalysisTools, TextWriter
from sklearn.ensemble import RandomForestClassifier
import scipy.stats

__author__ = 'Jakob Abesser'


class SymbolicAnalysisExperiments:

    def __init__(self,
                 dir_data,
                 dir_results,
                 fontsize=14,
                 num_features_to_select=20,
                 min_feature_importance=0.01,
                 min_effect_size=0.5,
                 num_estimators=250):
        self.dir_results = dir_results
        self.dir_data = dir_data

        # data loading & preparation
        self.raw_data, \
        self.metadata_feature_labels, \
        self.metadata_features, \
        self.numeric_feature_labels, \
        self.numeric_features = self.load_data()

        self.extractors = {'feature_selection': [self.performer_subset_feature_selection]}
        # self.extractors = {'feature_selection': [self.one_vs_n_feature_selection]}
        self.fontsize = fontsize
        self.num_features_to_select = num_features_to_select
        self.min_feature_importance = min_feature_importance
        self.min_effect_size = min_effect_size
        self.num_estimators = num_estimators
        self.text_writer = TextWriter()
        self.tools = AnalysisTools
        self.clf = RandomForestClassifier(n_estimators=self.num_estimators)

    def load_data(self):
        """ Load features exported with MeloSpySuite GUI and split it into metadata and numeric features """
        fn_csv = os.path.join(self.dir_data, 'classification_features_chorus_level.csv')
        raw_data = pd.read_csv(fn_csv, sep=';')

        # split features into metadata features and numeric features
        metadata_feature_labels = ['full_title',
                                   'id',
                                   'instrument',
                                   'performer',
                                   'rhythmfeel',
                                   'seg_id',
                                   'seg_type',
                                   'style',
                                   'title',
                                   'tonality_type']
        metadata_features = raw_data.filter(metadata_feature_labels, axis=1).as_matrix()

        numeric_feature_labels = [_ for _ in list(raw_data.columns) if _ not in metadata_feature_labels]
        numeric_features = raw_data.filter(numeric_feature_labels, axis=1).as_matrix()

        return raw_data, metadata_feature_labels, metadata_features, numeric_feature_labels, numeric_features

    def run(self):
        for category in self.extractors.keys():
            for extractor in self.extractors[category]:
                extractor()
        print('Finished all experiments :)')

    def performer_subset_feature_selection(self):

        # prepare class id
        metadata_feat_idx = self.metadata_feature_labels.index('performer')
        all_feature_values = self.metadata_features[:, metadata_feat_idx]
        class_id, unique_class_values = SymbolicAnalysisExperiments.create_class_ids(all_feature_values)

        cool_group_1 = ['Gerry Mulligan',
                        'Stan Getz',
                        'Zoot Sims']
        cool_group_2 = ['Lee Konitz',
                        'Warne Marsh']

        configs = [[['Paul Desmond'],
                    ['Chet Baker'],
                    'PD_vs_CB'],
                   [['Paul Desmond'],
                    cool_group_1 + cool_group_2,
                    'PD_vs_Cool_1_2'],
                   [['Chet Baker'],
                    cool_group_1 + cool_group_2,
                    'CB_vs_Cool_1_2'],
                   [['Paul Desmond'],
                    cool_group_1,
                    'PD_vs_Cool_1'],
                   [['Chet Baker'],
                    cool_group_1,
                    'CB_vs_Cool_1'],
                   [['Paul Desmond'],
                    cool_group_2,
                    'PD_vs_Cool_2'],
                   [['Chet Baker'],
                    cool_group_2,
                    'CB_vs_Cool_2']
                   ]


        # iterate over class configurations
        for config in configs:

            print('Feature selection for config %s' % config[2])

            self.text_writer.reset()

            class_id_curr = -1*np.ones_like(class_id)

            # define class IDs for current config
            for cid in (0, 1):
                class_id_curr[np.in1d(all_feature_values, np.array(config[cid]))] = cid
            assert len(np.unique(class_id_curr)) == 3

            class_label = ['-'.join(config[_]) for _ in (0, 1)]
            SymbolicAnalysisExperiments.analyze_features_for_two_classes(self.clf,
                                                                         self.text_writer,
                                                                         self.numeric_features,
                                                                         self.numeric_feature_labels,
                                                                         class_id_curr,
                                                                         class_label,
                                                                         num_features_to_select=self.num_features_to_select,
                                                                         min_feature_importance=self.min_feature_importance,
                                                                         min_effect_size=self.min_effect_size)

            self.text_writer.save(os.path.join(self.dir_results, 'feature_selection_benjaming_%s.csv' % config[2]))


    def one_vs_n_feature_selection(self):
        """ Perform 1-vs-N feature selection to identify most characteristic properties
            of individual classes """
        # feature check
        assert np.all(np.logical_not(np.isnan(self.numeric_features)))

        num_items, num_features = self.numeric_features.shape



        # attributes of interest
        class_type_labels = ['instrument', 'performer', 'rhythmfeel', 'style', 'tonality_type']

        for ctid, class_type in enumerate(class_type_labels):

            print('Run 1-vs-N feature selection experiment for class type = %s' % class_type)

            # prepare class id
            metadata_feat_idx = self.metadata_feature_labels.index(class_type)
            all_feature_values = self.metadata_features[:, metadata_feat_idx]
            class_id, unique_class_values = SymbolicAnalysisExperiments.create_class_ids(all_feature_values)

            self.text_writer.reset()

            class_one_label = 'all'

            for class_label in unique_class_values:

                cid = np.where(np.array(unique_class_values) == class_label)[0][0]

                # define 1-vs-N class IDs
                class_id_curr = np.ones(num_items, dtype=int)
                class_id_curr[class_id == cid] = 0

                SymbolicAnalysisExperiments.analyze_features_for_two_classes(self.clf,
                                                                             self.text_writer,
                                                                             self.numeric_features,
                                                                             self.numeric_feature_labels,
                                                                             class_id_curr,
                                                                             [class_label, class_one_label],
                                                                             num_features_to_select=self.num_features_to_select,
                                                                             min_feature_importance=self.min_feature_importance,
                                                                             min_effect_size=self.min_effect_size)

            self.text_writer.save(os.path.join(self.dir_results, 'symbolic_analysis_1_vs_N_feature_selection_%s.csv' % class_type))

    @staticmethod
    def create_class_ids(all_vals):
        """ Generate class ID vector from given set of item-wise values.
        Args:
            all_vals (ndarray): Item-wise annotations (num_items)
        Returns:
            unique_vals (ndarray): Unique annotations (num_classes)
            class_id (ndarray): Item-wise class ids (num_items)
        """
        class_id = np.zeros(len(all_vals), dtype=int)
        unique_vals = np.unique(all_vals)
        for i, val in enumerate(unique_vals):
            class_id[all_vals == val] = i
        return class_id, unique_vals

    @staticmethod
    def analyze_feature(feat_vec, class_id):
        """ Analyze feature vector for given 2-class class ID vector.
            Other class ID values than (0, 1) are ignored
        Args:
            feat_vec (ndarray): Feature vector
            class_id (ndarray): Class ID values
        Returns:
            t (float): t-Statistic
            p (float): two-tailed p-value
            d (float): Cohen's D measure of effect size
        """

        # t-test
        t, p = scipy.stats.ttest_ind(feat_vec[class_id == 0],
                                     feat_vec[class_id == 1])

        # effect strength (Cohen's D)
        d = AnalysisTools.cohens_d(feat_vec[class_id == 0],
                                   feat_vec[class_id == 1])

        class_means = [float(np.mean(feat_vec[class_id == cid])) for cid in [0, 1]]

        return t, p, d, class_means

    @staticmethod
    def analyze_features_for_two_classes(clf,
                                         text_writer,
                                         feat_mat,
                                         feature_labels,
                                         class_id,
                                         class_labels,
                                         num_features_to_select=20,
                                         min_feature_importance=0.01,
                                         min_effect_size=0.5):
        """ Find most discriminating features for two class partition
        Args:
            clf (scikit-learn classifier): Classifier (e.g. Random Forest) from scikit-learn package
            text_writer (TextWriter): Instance of text writer to save results for later text output
            feat_mat (2d ndarray): Feature matrix (num_items x num_features)
            feature_labels (list of string): Feature labels
            class_id (ndarray): Class ID values (num_items)
            class_labels (list of string): Labels for class ID = (0, 1)
            num_features_to_select (int): Number of features to select from initial feature selection
            min_feature_importance (float): Selection threshold (feature importance from RandomForest)
            min_effect_size (float): Selection threshold for effect size (Cohen's D)
        """

        text_writer.add("%s vs. %s; (N = %d vs. %d)" % (class_labels[0],
                                                        class_labels[1],
                                                        int(np.sum(class_id == 0)),
                                                        int(np.sum(class_id == 1))))

        text_writer.add("Rank; Feature; Mean (class); Mean (others); Significance (t-test); Cohen's D")

        clf.fit(feat_mat, class_id)

        # indices of best features
        feature_importance = clf.feature_importances_
        best_feat_idx = np.argsort(feature_importance)[::-1][:num_features_to_select]
        best_feat_idx = best_feat_idx[feature_importance[best_feat_idx] >= min_feature_importance]

        # t-test for significance
        for fid, numeric_feat_idx in enumerate(best_feat_idx):

            # analyze current feature
            t, p, d, class_means = SymbolicAnalysisExperiments.analyze_feature(feat_mat[:, numeric_feat_idx],
                                                                               class_id)

            label = feature_labels[numeric_feat_idx]

            # emphasize features which are significant or have at least a medium effect size
            if p < 0.05 or np.abs(d) >= min_effect_size:
                label = '!! ' + label

            text_writer.add('%d; %s; %f; %f; %s; %f' % (fid,
                                                        label,
                                                        class_means[0],
                                                        class_means[1],
                                                        AnalysisTools.generate_p_value_string(p),
                                                        d))
