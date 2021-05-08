import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
from PIL import Image
from pathlib import Path

import Model
import Data
from evaluation.util import evaluate_model_single_tag

physical_devices = tf.config.list_physical_devices('GPU')
tf.config.experimental.set_memory_growth(physical_devices[0], True)
# Enable/disable GPU
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))

'''
n = 2
d = 56
s = 12
m = 0
dim = 120
dataset = "funiegan"
# dataset = "flowers"
data = Data.import_images(loc="./training_images/" + dataset + "/",split = 0.1, LR=dim, HR=dim*2)

model = Model.create_model(dim, n, d, s, m)
model = Model.train_model(model, data, epochs=20, batch_size=32) #, working_dir=".")

model = Model.load_model("saved_models/high_res")
HR, LR, b = Model.predict_model(model, "training_images/charuco/charuco_36-18-0.jpg", 250)
HR.save("./charuco_zoom.jpg")
HR.show(title="HR")
LR.show(title="LR")
b.show(title="Antialias")
'''

# example parameters
model_name = Path("saved_models/high_res")
model_input_size = 250
eval_im_folder = Path("evaluation_images/isolated_tags/charuco_CH1_35-15_500_png")
eval_im_format = ("png", "jpg")

# call evaluation function
evaluate_model_single_tag(
    model_name, 
    model_input_size, 
    eval_im_folder, 
    eval_im_format,
    eval_sample_frac=0.2 # sample size: fraction of evalutation data used
    )