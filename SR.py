import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import datetime
from PIL import Image
import time
import Model_util

# Creates and returns the model based of specified parameters.
def create_model(dim, n, d, s, m, activation="relu"):
    # Input layer. Takes the image shape and one channel for greyscale images.
    inputs = keras.Input(shape=(dim,dim,1,))

    # The convolutional layers of the model. Keeps size of feature maps constant with same padding.
    # Feature extraction
    f_1 = 5
    n_1 = d
    conv56_5 = layers.Conv2D(filters=n_1, kernel_size=(f_1,f_1), strides=(1,1), padding="same", kernel_initializer=tf.initializers.random_normal(0.1))
    x = conv56_5(inputs)
    if activation=="relu":
        relu1 = keras.activations.relu
        x = relu1(x)
    elif activation=="lrelu":
        lrelu1 = keras.layers.LeakyReLU(alpha=0.3)
        x = lrelu1(x)
    elif activation == "prelu":
        prelu1 = layers.PReLU(alpha_initializer=tf.random_normal_initializer(0.1), shared_axes=[1,2,3])
        x = prelu1(x)
    else:
        raise Exception("No valid activation function chosen...")

    # Shrinking
    f_2 = 1
    n_2 = s
    conv12_1 = layers.Conv2D(filters=n_2, kernel_size=(f_2,f_2), strides=(1,1), padding="same", kernel_initializer=tf.initializers.random_normal(0.1))
    x = conv12_1(x)
    if activation=="relu":
        relu2 = keras.activations.relu
        x = relu2(x)
    elif activation=="lrelu":
        lrelu2 = keras.layers.LeakyReLU(alpha=0.3)
        x = lrelu2(x)
    elif activation == "prelu":
        prelu2 = layers.PReLU(alpha_initializer=tf.random_normal_initializer(0.1), shared_axes=[1,2,3])
        x = prelu2(x)
    else:
        raise Exception("No valid activation function chosen...")

    # Non-linear mapping
    f_3 = 3
    n_3 = s
    for l in range(0,m):
        conv56_1 = layers.Conv2D(filters=n_3, kernel_size=(f_3,f_3), strides=(1,1), padding="same", kernel_initializer=tf.initializers.random_normal(0.1))
        x = conv56_1(x)
        if activation == "relu":
            relu3 = keras.activations.relu
            x = relu3(x)
        elif activation == "lrelu":
            lrelu3 = keras.layers.LeakyReLU(alpha=0.3)
            x = lrelu3(x)
        elif activation == "prelu":
            prelu3 = layers.PReLU(alpha_initializer=tf.random_normal_initializer(0.1), shared_axes=[1,2,3])
            x = prelu3(x)
        else:
            raise Exception("No valid activation function chosen...")

    # Expanding
    f_4 = 1
    n_4 = d
    conv12_1 = layers.Conv2D(filters=n_4, kernel_size=(f_4,f_4), strides=(1,1), padding="same", kernel_initializer=tf.initializers.random_normal(0.1))
    x = conv12_1(x)
    if activation=="relu":
        relu4 = keras.activations.relu
        x = relu4(x)
    elif activation=="lrelu":
        lrelu4 = keras.layers.LeakyReLU(alpha=0.3)
        x = lrelu4(x)
    elif activation=="prelu":
        prelu4 = layers.PReLU(alpha_initializer=tf.random_normal_initializer(0.1), shared_axes=[1,2,3])
        x = prelu4(x)
    else:
        raise Exception("No valid activation function chosen...")

    # Deconvolution
    f_5 = 9
    n_5 = 1
    deconv1_9 = layers.Conv2DTranspose(filters=1, kernel_size=(f_5,f_5), strides=(n,n), padding="same", kernel_initializer=tf.initializers.random_normal(0.1))
    outputs = deconv1_9(x)

    # Creates the model by assigning the input and output layer.
    model = keras.Model(inputs=inputs, outputs=outputs, name="FSRCNN")
    # Returns model information.
    model.summary()

    # Compiles model with selected features.
    model.compile(loss=keras.losses.mean_squared_error, optimizer=keras.optimizers.Adam(), metrics=["mean_squared_error"])
    return model

# Traines the model based on specified parameters.
def train_model(model, data, epochs, batch_size, directory=".", model_alias=None):
    if model_alias is None:
        model_alias = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    # Normalize data
    X_train, Y_train, X_test, Y_test = Model_util.normalize_data(data)

    # Infer image dimensions by initial layer.
    dim = Model_util.get_model_dimension(model)

    # Creates directory
    dir, log_dir = Model_util.create_model_directory(directory, "SR", dim, model_alias)


    # Adds tensorboard
    tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)

    # Trains the model.
    history = model.fit(
        X_train, 
        Y_train, 
        batch_size=batch_size, 
        epochs=epochs, 
        validation_split=0.2,
        callbacks=[tensorboard_callback])

    # Evaluates model with test data.
    test_scores = model.evaluate(X_test, Y_test, verbose=2)
    print("Test loss:", test_scores[0])
    print("Test accuracy:", test_scores[1])

    # Saved model in separate directory
    model.save(dir + "/")

    # Saves info about model
    Model_util.save_model_info(dir, data, model, epochs, batch_size)
    model_name = f"{dim}_{model_alias}"
    return model, model_name

# Makes prediction using model.
def predict_model(model, image_dir, scale=2):
    input_dim = Model_util.get_model_dimension(model)
    # Allows the model to take both a directory string and an image as input.
    if isinstance(image_dir, str):
        LR = Image.open(image_dir)
    else:
        LR = image_dir
    LR = LR.convert("L")
    w, h = LR.size
    LR = LR.crop((0, 0, min(w, h), min(w, h)))
    LR = LR.resize((input_dim, input_dim), resample=Image.BICUBIC)
    x = tf.keras.preprocessing.image.img_to_array(LR)
    x = x / 255
    x = tf.reshape(x, (1, input_dim, input_dim,))
    y = model.predict(x)
    y = tf.reshape(y, (input_dim * scale, input_dim * scale, 1)) * 255
    HR = tf.keras.preprocessing.image.array_to_img(y)
    bicubic = LR.resize((input_dim * scale, input_dim * scale), resample=Image.BICUBIC)
    return HR, LR, bicubic


def predict(model, image_dir, scale=2):
    input_dim = model.layers[0].get_input_at(0).get_shape().as_list()[1]
    # LR = Image.open(image_dir)
    # LR = LR.convert("L")
    # w, h = LR.size
    # LR = LR.crop((0, 0, min(w, h), min(w, h)))
    # LR = LR.resize((input_dim, input_dim), resample=Image.BICUBIC)

    LR = Image.fromarray(image_dir)
    LR = LR.convert("L")
    w, h = LR.size
    LR = LR.crop((0, 0, min(w, h), min(w, h)))

    x = tf.keras.preprocessing.image.img_to_array(LR)
    x = x / 255
    x = tf.reshape(x, (1, input_dim, input_dim,))
    start = time.time()
    y = model.predict(x)
    stop = time.time()
    # print("Elapsed time: " + str(stop-start))
    y = tf.reshape(y, (input_dim * scale, input_dim * scale, 1)) * 255
    HR = tf.keras.preprocessing.image.array_to_img(y)
    return HR



# if __name__ == "__main__":
#     n = 2
#     d = 56
#     s = 12
#     m = 0
#     dim = 100
#     # dataset = "FunieGanData"
#     dataset = "CH1_frames"
#     data = Data.import_SR_images(loc="training_images/" + dataset + "/", split = 0.1, LR=dim, HR=dim * 2)

#     model = create_model(dim, n, d, s, m)
#     model = train_model(model, data, epochs=10, batch_size=32, model_alias="tester")
