import codecs
import yaml
import os
import random
import re
from psychopy import visual


def load_config():
    try:
        with open(os.path.join("config.yaml"), encoding='utf8') as yaml_file:
            doc = yaml.safe_load(yaml_file)
        return doc
    except:
        raise Exception("Can't load config file")


def read_text_from_file(file_name, insert=''):
    """
    Method that read message from text file, and optionally add some
    dynamically generated info.
    :param file_name: Name of file to read
    :param insert: dynamically generated info
    :return: message
    """
    if not isinstance(file_name, str):
        raise TypeError('file_name must be a string')
    msg = list()
    with codecs.open(file_name, encoding='utf-8', mode='r') as data_file:
        for line in data_file:
            if not line.startswith('#'):  # if not commented line
                if line.startswith('<--insert-->'):
                    if insert:
                        msg.append(insert)
                else:
                    msg.append(line)
    return ''.join(msg)


def load_images(randomize):
    def my_digit_sort(my_list):
        return list(map(int, re.findall(r'\d+', my_list)))[0]

    training_images_no_numbers = os.listdir(os.path.join("images", "training", "without_numbers"))
    training_images_with_numbers = os.listdir(os.path.join("images", "training", "with_numbers"))
    training_images = list(zip(training_images_no_numbers, training_images_with_numbers))
    experimental_images_no_numbers = os.listdir(os.path.join("images", "experiment", "without_numbers"))
    experimental_images_with_numbers = os.listdir(os.path.join("images", "experiment", "with_numbers"))

    experimental_images_no_numbers.sort(key=my_digit_sort)
    experimental_images_with_numbers.sort(key=my_digit_sort)

    experimental_images = list(zip(experimental_images_no_numbers, experimental_images_with_numbers))

    if randomize:
        random.shuffle(training_images)
        random.shuffle(experimental_images)

    return training_images, experimental_images


def prepare_block_stimulus(images, win, config, folder):
    result = []
    for (image1, image2) in images:
        stim1 = visual.image.ImageStim(win=win, image=os.path.join("images", folder, "without_numbers", image1),
                                       pos=config["stimulus_pos"], interpolate=True)
        stim2 = visual.image.ImageStim(win=win, image=os.path.join("images", folder, "with_numbers", image2),
                                       pos=config["stimulus_pos"], interpolate=True)
        if image1.find("_") != -1:
            image_id = int(image1.split("_")[0])
        else:
            image_id = image1.split(".")[0]
        result.append({"image_ID": image_id,
                       "stimulus_no_numbers": stim1,
                       "stimulus_with_numbers": stim2,
                       "image_name": image1})
    return result
