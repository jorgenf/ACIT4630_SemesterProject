"""
Trains the 


"""

from pathlib import Path
import joblib
import time

import numpy as np
from numpy.lib.histograms import histogram
from sklearn import svm
from sklearn.model_selection import train_test_split
from sklearn.metrics import average_precision_score
from sklearn.metrics import precision_recall_curve
from sklearn.metrics import plot_precision_recall_curve

import matplotlib.pyplot as plt

# from create_data.create_tag_dataset import create_dataset
from create_data.create_fft_dataset import create_dataset

def train_model(valid, rejects, dims):

    # create dataset
    x_data, y_label = create_dataset(valid, rejects, dims=dims)

    # split into test and train data
    x_train, x_test, y_train, y_test = train_test_split(
        x_data, y_label,
        test_size=0.3
        # random_state=1
    )

    # create model
    clf = svm.SVC().fit(x_train, y_train)

    y_score = clf.decision_function(x_test)
    avg_precision = average_precision_score(y_test, y_score)
    print(f"Avg. precision-recall score: {avg_precision:.2f}")

    disp = plot_precision_recall_curve(clf, x_test, y_test)
    disp.ax_.set_title("Precision-recall curve")
    plt.show()
        
    return clf, clf.score(x_test, y_test)

def batch_test_parameters(n, dim_range, valid, rejects):
    from tqdm import trange
    # n = 1000
    for dims in dim_range:
        # score = [train_and_score(dims) for x in range(n)]
        bin_total_score = 0
        # for i in trange(n):
        for i in range(n):
            model, score = train_model(valid, rejects, dims)
            bin_total_score += score
        print(f"Dimensions: {dims}\t Acc: {bin_total_score/n:.5f}")

# def get_scores(dims, valid, rejects):
#     model, score = train_model(valid, rejects, dims)
#     y_score = model.decision_function(x_test)
#     avg_precision = average_precision_score(y_test, y_score)



if __name__ == "__main__":

    """ dataset """
    # create dataset
    # valid = "evaluation_images/valid_tags/charuco_CH1_35-15_x_png"
    # rejects = "evaluation_images/rejected_tags/charuco_CH1_35-15_sorted"
    valid = "evaluation_images/categorizer_training/valid"
    rejects = "evaluation_images/categorizer_training/reject"

    # test the model performance for different parameters
    # test_dims = [(4, 4), (8, 8), (16, 16,), (32, 32)]
    # batch_test_parameters(10, test_dims, valid, rejects)

    # bins in histogram
    dims = (16, 16)

    # save model to path
    save_path = Path("evaluation/classifier_models")
    Path(save_path).mkdir(parents=True, exist_ok=True)
    model_name = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())

    # create and save model
    model, test_score = train_model(valid, rejects, dims)
    joblib.dump(model, f"{save_path}/{model_name}.joblib")
    print(f"Accuracy: {test_score}")
    print(f"Saved to path \"{save_path}/{model_name}\"")