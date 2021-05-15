import time
import random
import glob
from PIL import Image
import sys
import os
from pathlib import Path

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
sys.path.append("/home/wehak/code/ACIT4630_SemesterProject")

import cv2
import cv2.aruco as aruco
import numpy as np
from tqdm import tqdm
import tensorflow as tf

import Model

"""
Inputs:
    - a superres model and its magnification coefficient
    - folder path to evaluation images

Outputs:
    - metrics on how many many tags that were detected
    - metrics on image quality
"""
def evaluate_model_single_tag(
    model_name, model_input_size, # model name and input size
    eval_im_folder, eval_im_format, # path to folder of evaluation images and their format (.jpg, .png etc)
    eval_sample_frac=1.0, # fraction of images in "eval_im_folder" checked
    verify_tag=False # search filename for tag identity
    ): 
    
    # aruco parameters 
    ARUCO_DICT = aruco.DICT_6X6_250 
    aruco_dict = aruco.Dictionary_get(ARUCO_DICT)
    arucoParameters = aruco.DetectorParameters_create() # default values

    # find images in folder
    evaluation_images = list(glob.glob(f"{eval_im_folder}/*.{eval_im_format}"))
    if len(evaluation_images) == 0:
        print(f"No .{eval_im_format} files in \"{eval_im_folder}\"")

    # load model
    model = Model.load_model(model_name)

    # count tags. assumes input is a greyscale image
    def find_tags(input_image):
        # feed grayscale image into aruco-algorithm
        _, ids, _ = aruco.detectMarkers(
            input_image, aruco_dict, parameters=arucoParameters)
        
        if ids is not None:
            return len(ids)
        else:
            return 0

    # metrics
    n_ground_truth_detected = 0
    n_lr_detected = 0
    n_hr_detected = 0
    n_bicubic_detected = 0
    n_images = 0

    # predict and evaluate images
    random.shuffle(evaluation_images)
    start_t = time.time()
    for image_path in tqdm(evaluation_images[:int(eval_sample_frac * len(evaluation_images))]):
        # find tag id
        if verify_tag:
            im_tag = int(image_path[image_path.rfind("_")+1 : image_path.rfind(".")])
            im_name = Path(image_path).name

        # for image_path in evaluation_images:
        HR, LR, bicubic = Model.predict_model_real(model, image_path, model_input_size)

        # convert images to openCV format and detect markers
        # image = cv2.imread(image_path, 0)
        image = np.array(Image.open(image_path).convert("L"))
        n_ground_truth_detected += find_tags(image)
        n_lr_detected += find_tags(np.array(LR))
        n_hr_detected += find_tags(np.array(HR))
        n_bicubic_detected += find_tags(np.array(bicubic))

        n_images += 1

    # print evaluation
    # n_images = len(evaluation_images)
    print(f"\nEvaluated {n_images} images")
    print("Detection rates:")
    print("------------------------")
    print(f"Ground truth\t{n_ground_truth_detected / n_images * 100:.2f} %")
    print(f"LR\t\t{n_lr_detected / n_images * 100:.2f} %")
    print(f"HR\t\t{n_hr_detected / n_images * 100:.2f} %")
    print(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %")
    print("------------------------")
    print(f"Finished in {time.time() - start_t:.1f} s")


# run module independently
if __name__ == "__main__":
    # seems necessary to avoid crashing the model
    physical_devices = tf.config.list_physical_devices('GPU')
    tf.config.experimental.set_memory_growth(physical_devices[0], True)
    
    # Enable/disable GPU
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))

    # example parameters
    model_name = Path("saved_models/high_res")
    model_input_size = 250
    eval_im_folder = Path("evaluation_images/isolated_tags/charuco_36-18_250")
    # eval_im_folder = Path("/home/wehak/code/ACIT4630_SemesterProject/evaluation_images/isolated_tags/250px-padding_jpg")
    eval_im_format = "jpg"

    # call evaluation function
    evaluate_model_single_tag(
        model_name, 
        model_input_size, 
        eval_im_folder, 
        eval_im_format,
        eval_sample_frac=1,
        verify_tag=False
        )
