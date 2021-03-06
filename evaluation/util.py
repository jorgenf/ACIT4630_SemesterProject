"""
Inputs:
    - a enhancement model and its magnification coefficient
    - folder path to evaluation images

Outputs:
    - metrics on how many many tags that were detected
"""

import time
import random
import glob
from PIL import Image
import sys
import os
from pathlib import Path

# make tf less verbose
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# necessary for importing SR, DN and Model module when running the script independently
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

import cv2
import cv2.aruco as aruco
import numpy as np
from tqdm import tqdm
import tensorflow as tf

import SR
import DN
import Model


def evaluate_model_single_tag(
    model_name, # model name and input size
    model_type,
    eval_im_folder, eval_im_format, # path to folder of evaluation images and their format (.jpg, .png etc)
    eval_sample_frac=1.0, # fraction of images in "eval_im_folder" checked
    second_model_name=None,
    verify_id = False
    ): 
    
    # aruco parameters 
    ARUCO_DICT = aruco.DICT_6X6_250 
    aruco_dict = aruco.Dictionary_get(ARUCO_DICT)
    arucoParameters = aruco.DetectorParameters_create() # default values

    # find images in folder
    evaluation_images = [] 
    for im_format in eval_im_format:
        evaluation_images += glob.glob(f"{eval_im_folder}/*.{im_format}")
        if len(evaluation_images) == 0:
            print(f"No .{im_format} files in \"{eval_im_folder}\"")

    # load model
    if model_type == "SR" or model_type == "DN":
        model = Model.load_model(model_name)
        model2 = None
    elif model_type == "SRDN" or model_type == "DNSR":
        model = Model.load_model(model_name)
        model2 = Model.load_model(second_model_name)
    else:
        raise Exception("No valid model type chosen.")

    # count tags. assumes input is a greyscale image
    def find_tags(input_image, true_tag_id, input_im_name):
        # feed grayscale image into aruco-algorithm
        _, ids, _ = aruco.detectMarkers(
            input_image, aruco_dict, parameters=arucoParameters)
        
        # count the number of correct tags identified:
        if ids is not None:
            if (len(ids) == 1) and verify_id:
                if ids[0][0] == true_tag_id:
                    return 1
                else:
                    print(f"Warning: {input_im_name} wrongly identified ID {true_tag_id} as a {ids[0][0]}")
                    return 0
            elif len(ids) == 1:
                return 1
            elif len(ids) > 1:
                print(f"Warning: {input_im_name} identified more than 1 one ID: {len(ids)}")
                return 0
            else:
                print(f"Warning: {len(ids)}\n{ids}")
                return 0
        else:
            return 0

    # metrics
    n_images = 0
    n_ground_truth_detected = 0
    n_lr_detected = 0
    n_hr_detected = 0
    n_bicubic_detected = 0
    n_denoised_detected = 0
    n_original_detected = 0
    n_denoised_HR_detected = 0
    n_denoised_BI_detected = 0

    # predict and evaluate images
    random.shuffle(evaluation_images)
    start_t = time.time()
    for image_path in tqdm(evaluation_images[:int(eval_sample_frac * len(evaluation_images))]):
        # find tag id
        if verify_id:
            im_tag = int(image_path[image_path.rfind("_")+1 : image_path.rfind(".")])
        else:
            im_tag = 0

        im_name = Path(image_path).name

        # for image_path in evaluation_images:
        if model_type == "SR":
            HR, LR, bicubic = SR.predict_model(model, image_path)
            image = np.array(Image.open(image_path).convert("L"))
            n_ground_truth_detected += find_tags(image, im_tag, im_name)
            n_lr_detected += find_tags(np.array(LR), im_tag, im_name)
            n_hr_detected += find_tags(np.array(HR), im_tag, im_name)
            n_bicubic_detected += find_tags(np.array(bicubic), im_tag, im_name)
        elif model_type == "DN":
            denoised, original = DN.predict_model(model, image_path)
            n_denoised_detected += find_tags(np.array(denoised), im_tag, im_name)
            n_original_detected += find_tags(np.array(original), im_tag, im_name)
        elif model_type == "SRDN":
            HR, LR, bicubic = SR.predict_model(model, image_path)
            image = np.array(Image.open(image_path).convert("L"))
            n_ground_truth_detected += find_tags(image, im_tag, im_name)
            n_lr_detected += find_tags(np.array(LR), im_tag, im_name)
            n_hr_detected += find_tags(np.array(HR), im_tag, im_name)
            n_bicubic_detected += find_tags(np.array(bicubic), im_tag, im_name)
            denoised_HR, original_HR = DN.predict_model(model2, HR)
            denoised_BI, original_BI = DN.predict_model(model2, bicubic)
            n_denoised_HR_detected += find_tags(np.array(denoised_HR), im_tag, im_name)
            n_denoised_BI_detected += find_tags(np.array(denoised_BI), im_tag, im_name)
        elif model_type == "DNSR":
            denoised, original = DN.predict_model(model, image_path)
            image = Image.open(image_path).convert("L")
            denoised_HR, denoised_LR, denoised_BI = SR.predict_model(model2, denoised)
            n_denoised_HR_detected += find_tags(np.array(denoised_HR), im_tag, im_name)
            n_denoised_BI_detected += find_tags(np.array(denoised_BI), im_tag, im_name)
            HR, LR, bicubic = SR.predict_model(model2, image)
            n_hr_detected += find_tags(np.array(HR), im_tag, im_name)
            n_bicubic_detected += find_tags(np.array(bicubic), im_tag, im_name)
        else:
            raise Exception("No valid model type chosen.")
        # convert images to openCV format and detect markers
        # image = cv2.imread(image_path, 0)

        n_images += 1

    # print evaluation
    # n_images = len(evaluation_images)
    print(f"\nEvaluated {n_images} images")
    print("Detection rates:")
    print("------------------------")
    if model_type == "SR":
        print(f"Ground truth\t{n_ground_truth_detected / n_images * 100:.2f} %")
        print(f"LR\t\t{n_lr_detected / n_images * 100:.2f} %")
        print(f"HR\t\t{n_hr_detected / n_images * 100:.2f} %")
        print(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %")
    elif model_type == "DN":
        print(f"Original\t\t{n_original_detected / n_images * 100:.2f} %")
        print(f"Denoised\t\t{n_denoised_detected / n_images * 100:.2f} %")
    elif model_type == "SRDN":
        print(f"Ground truth\t{n_ground_truth_detected / n_images * 100:.2f} %")
        print(f"LR\t\t{n_lr_detected / n_images * 100:.2f} %")
        print(f"HR\t\t{n_hr_detected / n_images * 100:.2f} %")
        print(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %")
        print(f"Denoised bicubic\t\t{n_denoised_BI_detected / n_images * 100:.2f} %")
        print(f"Denoised HR\t\t{n_denoised_HR_detected / n_images * 100:.2f} %")
    elif model_type == "DNSR":
        print(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %")
        print(f"HR\t\t{n_hr_detected/ n_images * 100:.2f} %")
        print(f"Denoised bicubic\t\t{n_denoised_BI_detected / n_images * 100:.2f} %")
        print(f"Denoised HR\t\t{n_denoised_HR_detected / n_images * 100:.2f} %")
    else:
        raise Exception("No valid model type chosen.")
    print("------------------------")
    print(f"Finished in {time.time() - start_t:.1f} s")

    if model_type == "SR" or model_type == "DN":
        directory = Path(f"{model_name}/assets/evaluation.txt")
    elif model_type == "SRDN" or model_type == "DNSR":
        n1 = os.path.basename(os.path.normpath(model_name))
        n2 = os.path.basename(os.path.normpath(second_model_name))
        if model_type == "SRDN":
            path = Path(f"saved_models/SRDN/{n1}_{n2}")
        else:
            path = Path(f"saved_models/DNSR/{n1}_{n2}")
        try:
            # os.mkdir(path)
            path.mkdir(parents=True, exist_ok=True)
        except:
            raise Exception(f"Failed to create directory \"{dir}\" ")
        directory = Path(f"{path}/summary.txt")
    else:
        raise Exception("No valid model type chosen.")
    with open(directory, 'w') as info:
        info.write(f"Evaluated {n_images} images\n")
        info.write("Detection rates:\n")
        info.write("------------------------\n")
        if model_type == "SR":
            info.write(f"Ground truth\t{n_ground_truth_detected / n_images * 100:.2f} %\n")
            info.write(f"LR\t\t{n_lr_detected / n_images * 100:.2f} %\n")
            info.write(f"HR\t\t{n_hr_detected / n_images * 100:.2f} %\n")
            info.write(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %\n")
        elif model_type == "DN":
            info.write(f"Original\t\t{n_original_detected / n_images * 100:.2f} %\n")
            info.write(f"Denoised\t\t{n_denoised_detected / n_images * 100:.2f} %\n")
        elif model_type == "SRDN":
            info.write(f"Ground truth\t{n_ground_truth_detected / n_images * 100:.2f} %\n")
            info.write(f"LR\t\t{n_lr_detected / n_images * 100:.2f} %\n")
            info.write(f"HR\t\t{n_hr_detected / n_images * 100:.2f} %\n")
            info.write(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %\n")
            info.write(f"Denoised bicubic\t\t{n_denoised_BI_detected / n_images * 100:.2f} %\n")
            info.write(f"Denoised HR\t\t{n_denoised_HR_detected / n_images * 100:.2f} %\n")
        elif model_type == "DNSR":
            info.write(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %\n")
            info.write(f"HR\t\t{n_hr_detected / n_images * 100:.2f} %\n")
            info.write(f"Denoised bicubic\t\t{n_denoised_BI_detected / n_images * 100:.2f} %\n")
            info.write(f"Denoised HR\t\t{n_denoised_HR_detected / n_images * 100:.2f} %\n")
        else:
            raise Exception("No valid model type chosen.")
        info.write("------------------------\n")
        info.write(f"Finished in {time.time() - start_t:.1f} s\n")
        info.close()


def evaluate_model_false_negative_tag(
    model_name, # model name and input size
    model_type,
    eval_im_folder, eval_im_format, # path to folder of evaluation images and their format (.jpg, .png etc)
    eval_sample_frac=1.0, # fraction of images in "eval_im_folder" checked
    second_model_name=None
    ): 
    
    # aruco parameters 
    ARUCO_DICT = aruco.DICT_6X6_250 
    aruco_dict = aruco.Dictionary_get(ARUCO_DICT)
    arucoParameters = aruco.DetectorParameters_create() # default values

    # find images in folder
    evaluation_images = [] 
    for im_format in eval_im_format:
        evaluation_images += glob.glob(f"{eval_im_folder}/*.{im_format}")
        if len(evaluation_images) == 0:
            print(f"No .{im_format} files in \"{eval_im_folder}\"")

    # load model
    if model_type == "SR" or model_type == "DN":
        model = Model.load_model(model_name)
        model2 = None
    elif model_type == "SRDN" or model_type == "DNSR":
        model = Model.load_model(model_name)
        model2 = Model.load_model(second_model_name)
    else:
        raise Exception("No valid model type chosen.")

    # count tags. assumes input is a greyscale image
    def find_tags(input_image, true_tag_id, input_im_name):
        # feed grayscale image into aruco-algorithm
        _, ids, _ = aruco.detectMarkers(
            input_image, aruco_dict, parameters=arucoParameters)
        
        # count the number of correct tags identified:
        if ids is not None:
            if len(ids) == 1:
                return 1
            elif len(ids) > 1:
                print(f"Warning: {input_im_name} identified more than one ID: {len(ids)}")
                return 0
            else:
                print(f"Warning: {len(ids)}\n{ids}")
                return 0
        else:
            return 0

    # metrics
    n_images = 0
    n_ground_truth_detected = 0
    n_lr_detected = 0
    n_hr_detected = 0
    n_bicubic_detected = 0
    n_denoised_detected = 0
    n_original_detected = 0
    n_denoised_HR_detected = 0
    n_denoised_BI_detected = 0

    # predict and evaluate images
    random.shuffle(evaluation_images)
    start_t = time.time()
    for image_path in tqdm(evaluation_images[:int(eval_sample_frac * len(evaluation_images))]):
        im_tag = 0
        im_name = Path(image_path).name
        img = cv2.imread(image_path)

        # for image_path in evaluation_images:
        if model_type == "SR":
            # converts from openCV -> PIL (greyscale) -> openCV
            # (this is the process that also happends inside the mode)
            ground_truth = np.array(Image.fromarray(img).convert("L"))
            n_ground_truth_detected += find_tags(ground_truth, im_tag, im_name)

            HR = SR.predict(model, img)
            n_hr_detected += find_tags(np.array(HR), im_tag, im_name)
            
            # converts from openCV -> PIL (greyscale, resize) -> openCV
            resized = Image.fromarray(img).convert("L").resize(
                [round(x * 2) for x in reversed(img.shape[:2])], resample=Image.BICUBIC
                )
            n_bicubic_detected += find_tags(np.array(resized), im_tag, im_name)

        elif model_type == "DN":
            denoised, original = DN.predict_model(model, image_path)
            n_denoised_detected += find_tags(np.array(denoised), im_tag, im_name)
            n_original_detected += find_tags(np.array(original), im_tag, im_name)
        elif model_type == "SRDN":
            # converts from openCV -> PIL (greyscale) -> openCV
            # (this is the process that also happends inside the mode)
            ground_truth = np.array(Image.fromarray(img).convert("L"))
            n_ground_truth_detected += find_tags(ground_truth, im_tag, im_name)

            HR = SR.predict(model, img)
            n_hr_detected += find_tags(np.array(HR), im_tag, im_name)
            
            # converts from openCV -> PIL (greyscale, resize) -> openCV
            resized = Image.fromarray(img).convert("L").resize(
                [round(x * 2) for x in reversed(img.shape[:2])], resample=Image.BICUBIC
                )
            n_bicubic_detected += find_tags(np.array(resized), im_tag, im_name)

            # HR, LR, bicubic = SR.predict_model(model, image_path)
            # image = np.array(Image.open(image_path).convert("L"))
            # n_ground_truth_detected += find_tags(image, im_tag, im_name)
            # n_lr_detected += find_tags(np.array(LR), im_tag, im_name)
            # n_hr_detected += find_tags(np.array(HR), im_tag, im_name)
            # n_bicubic_detected += find_tags(np.array(bicubic), im_tag, im_name)
            denoised_HR, original_HR = DN.predict_model(model2, HR)
            denoised_BI, original_BI = DN.predict_model(model2, resized)
            n_denoised_HR_detected += find_tags(np.array(denoised_HR), im_tag, im_name)
            n_denoised_BI_detected += find_tags(np.array(denoised_BI), im_tag, im_name)
        elif model_type == "DNSR":

            denoised, original = DN.predict_model(model, Image.fromarray(img))
            denoised_HR = SR.predict(model2, np.array(denoised))
            # image = Image.open(image_path).convert("L")
            # denoised_HR, denoised_LR, denoised_BI = SR.predict_model(model2, denoised)
            
            # n_hr_detected += find_tags(np.array(HR), im_tag, im_name)
            
            # converts from openCV -> PIL (greyscale, resize) -> openCV
            resized = denoised.resize(
                [round(x * 2) for x in reversed(denoised.shape[:2])], resample=Image.BICUBIC
                )
            n_denoised_HR_detected += find_tags(np.array(denoised_HR), im_tag, im_name)
            # n_denoised_BI_detected += find_tags(np.array(denoised_BI), im_tag, im_name)
            n_bicubic_detected += find_tags(np.array(resized), im_tag, im_name)
            
            # HR, LR, bicubic = SR.predict_model(model2, image)
            # n_hr_detected += find_tags(np.array(HR), im_tag, im_name)
            # n_bicubic_detected += find_tags(np.array(bicubic), im_tag, im_name)
        else:
            raise Exception("No valid model type chosen.")
        # convert images to openCV format and detect markers
        # image = cv2.imread(image_path, 0)

        n_images += 1

    # print evaluation
    # n_images = len(evaluation_images)
    print(f"\nEvaluated {n_images} images")
    print("Detection rates:")
    print("------------------------")
    if model_type == "SR":
        print(f"Ground truth\t{n_ground_truth_detected / n_images * 100:.2f} %")
        print(f"LR\t\t{n_lr_detected / n_images * 100:.2f} %")
        print(f"HR\t\t{n_hr_detected / n_images * 100:.2f} %")
        print(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %")
    elif model_type == "DN":
        print(f"Original\t\t{n_original_detected / n_images * 100:.2f} %")
        print(f"Denoised\t\t{n_denoised_detected / n_images * 100:.2f} %")
    elif model_type == "SRDN":
        print(f"Ground truth\t{n_ground_truth_detected / n_images * 100:.2f} %")
        print(f"LR\t\t{n_lr_detected / n_images * 100:.2f} %")
        print(f"HR\t\t{n_hr_detected / n_images * 100:.2f} %")
        print(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %")
        print(f"Denoised bicubic\t\t{n_denoised_BI_detected / n_images * 100:.2f} %")
        print(f"Denoised HR\t\t{n_denoised_HR_detected / n_images * 100:.2f} %")
    elif model_type == "DNSR":
        print(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %")
        # print(f"HR\t\t{n_hr_detected/ n_images * 100:.2f} %")
        # print(f"Denoised bicubic\t\t{n_denoised_BI_detected / n_images * 100:.2f} %")
        print(f"Denoised HR\t\t{n_denoised_HR_detected / n_images * 100:.2f} %")
    else:
        raise Exception("No valid model type chosen.")
    print("------------------------")
    print(f"Finished in {time.time() - start_t:.1f} s")

    if model_type == "SR" or model_type == "DN":
        directory = Path(f"{model_name}/assets/evaluation.txt")
    elif model_type == "SRDN" or model_type == "DNSR":
        n1 = os.path.basename(os.path.normpath(model_name))
        n2 = os.path.basename(os.path.normpath(second_model_name))
        if model_type == "SRDN":
            path = Path(f"saved_models/SRDN/{n1}_{n2}")
        else:
            path = Path(f"saved_models/DNSR/{n1}_{n2}")
        try:
            # os.mkdir(path)
            path.mkdir(parents=True, exist_ok=True)
        except:
            raise Exception(f"Failed to create directory \"{dir}\" ")
        directory = Path(f"{path}/summary.txt")
    else:
        raise Exception("No valid model type chosen.")
    with open(directory, 'w') as info:
        info.write(f"Evaluated {n_images} images\n")
        info.write("Detection rates:\n")
        info.write("------------------------\n")
        if model_type == "SR":
            info.write(f"Ground truth\t{n_ground_truth_detected / n_images * 100:.2f} %\n")
            info.write(f"LR\t\t{n_lr_detected / n_images * 100:.2f} %\n")
            info.write(f"HR\t\t{n_hr_detected / n_images * 100:.2f} %\n")
            info.write(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %\n")
        elif model_type == "DN":
            info.write(f"Original\t\t{n_original_detected / n_images * 100:.2f} %\n")
            info.write(f"Denoised\t\t{n_denoised_detected / n_images * 100:.2f} %\n")
        elif model_type == "SRDN":
            info.write(f"Ground truth\t{n_ground_truth_detected / n_images * 100:.2f} %\n")
            info.write(f"LR\t\t{n_lr_detected / n_images * 100:.2f} %\n")
            info.write(f"HR\t\t{n_hr_detected / n_images * 100:.2f} %\n")
            info.write(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %\n")
            info.write(f"Denoised bicubic\t\t{n_denoised_BI_detected / n_images * 100:.2f} %\n")
            info.write(f"Denoised HR\t\t{n_denoised_HR_detected / n_images * 100:.2f} %\n")
        elif model_type == "DNSR":
            info.write(f"Bicubic\t\t{n_bicubic_detected / n_images * 100:.2f} %\n")
            info.write(f"HR\t\t{n_hr_detected / n_images * 100:.2f} %\n")
            info.write(f"Denoised bicubic\t\t{n_denoised_BI_detected / n_images * 100:.2f} %\n")
            info.write(f"Denoised HR\t\t{n_denoised_HR_detected / n_images * 100:.2f} %\n")
        else:
            raise Exception("No valid model type chosen.")
        info.write("------------------------\n")
        info.write(f"Finished in {time.time() - start_t:.1f} s\n")
        info.close()

# run module independently
if __name__ == "__main__":
    # seems necessary to avoid crashing the model
    physical_devices = tf.config.list_physical_devices('GPU')
    tf.config.experimental.set_memory_growth(physical_devices[0], True)
    
    # Enable/disable GPU
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))

    # example parameters 
    sr_model = Path("saved_models/SR/best") # SR
    dn_model = Path("saved_models/256_20210515-221533_best") # DN
    model_type = "SR"
    # model_input_size = 128
    eval_im_folder = Path("evaluation_images/final_test_datasets/single_image/false_negative_tags_128px-padding_png") # with ID validation
    # eval_im_folder = Path("evaluation_images/final_test_datasets/single_image/true_positive_tags_256px-padding_png") # without ID validation
    eval_im_format = ("png", "jpg")

    # call evaluation function
    evaluate_model_false_negative_tag(
    # (
    # evaluate_model_single_tag(
        sr_model, 
        model_type, 
        eval_im_folder, 
        eval_im_format,
        eval_sample_frac=0.01,
        second_model_name=None,
        # verify_id=False
        )