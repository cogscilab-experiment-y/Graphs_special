import atexit
import csv
import random
import time
from os.path import join
import pandas as pd
from psychopy import visual, event, core
import string

from code.load_data import load_config, load_images, prepare_block_stimulus
from code.screen_misc import get_screen_res
from code.show_info import part_info, show_info
from code.check_exit import check_exit

RESULTS = []
PART_ID = ""


@atexit.register
def save_beh_results():
    num = random.randint(100, 999)
    with open(join('results', '{}_beh_{}.csv'.format(PART_ID, num)), 'w', newline='') as beh_file:
        dict_writer = csv.DictWriter(beh_file, RESULTS[0].keys())
        dict_writer.writeheader()
        dict_writer.writerows(RESULTS)


def draw_stim_list(stim_list, flag):
    for elem in stim_list:
        elem.setAutoDraw(flag)


def show_stim(stim, stim_time, clock, win):
    win.callOnFlip(clock.reset)
    win.callOnFlip(event.clearEvents)
    while clock.getTime() < stim_time:
        if stim is not None:
            stim.draw()
        check_exit()
        win.flip()
    win.callOnFlip(event.clearEvents)
    win.flip()


def show_clock(clock_image, clock, config):
    if config["show_clock"] and clock.getTime() > config["clock_show_time"]:
        clock_image.draw()


def show_timer(timer, clock, config):
    if config["show_timer"]:
        timer.setText(config["answer_time"] - int(clock.getTime()))
        timer.draw()


def block(config, images, block_type, win, fixation, clock, screen_res, answers, answers_buttons, mouse, feedback,
          extra_text, clock_image, timer):
    show_info(win, join('.', 'messages', f'instruction_{block_type}.txt'), text_color=config["text_color"],
              text_size=config["text_size"], screen_res=screen_res)

    n = -1
    if config["fixation_time"] == -1:
        fixation.setAutoDraw(True)
        win.flip()
        time.sleep(1)

    for trial in images:
        answer = ""
        reaction_time = None
        acc = -1
        n += 1

        # fixation
        if config["fixation_time"] > 0:
            show_stim(fixation, config["fixation_time"], clock, win)

        draw_stim_list(extra_text, True)
        win.callOnFlip(clock.reset)
        win.callOnFlip(event.clearEvents)

        show_stim(trial["stimulus_no_numbers"], config["stimulus_time"], clock, win)
        clock.reset()

        # draw trial for answers_type == keyboard
        if config["answers_type"] == "keyboard":
            while clock.getTime() < config["answer_time"]:
                trial["stimulus_with_numbers"].draw()
                show_clock(clock_image, clock, config)
                show_timer(timer, clock, config)

                answer = event.getKeys(keyList=config["reaction_keys"])
                if answer:
                    reaction_time = clock.getTime()
                    answer = answer[0]
                    break
                check_exit()
                win.flip()

        # draw trial for answer_type == mouse
        elif config["answers_type"] == "mouse":
            draw_stim_list(answers_buttons.values(), True)
            while clock.getTime() < config["answer_time"] and answer == "":
                trial["stimulus_with_numbers"].draw()
                show_clock(clock_image, clock, config)
                show_timer(timer, clock, config)
                for k, ans_button in answers_buttons.items():
                    if mouse.isPressedIn(ans_button):
                        reaction_time = clock.getTime()
                        answer = str(k)
                        break
                    elif ans_button.contains(mouse):
                        ans_button.borderWidth = config["answer_box_width"]
                    else:
                        ans_button.borderWidth = 0
                check_exit()
                win.flip()
            draw_stim_list(answers_buttons.values(), False)
        elif config["answers_type"] == "text":
            if config["text_box_text_type"] == "integer":
                allowed_keys = list(string.digits)
            elif config["text_box_text_type"] == "letters":
                allowed_keys = list(string.ascii_lowercase) + list(string.ascii_uppercase)
            elif config["text_box_text_type"] == "custom":
                allowed_keys = config["text_box_symbols"]
            else:
                raise Exception("Wrong text_box_symbols in config. Choose from letters, integer, or custom")
            while clock.getTime() < config["answer_time"]:
                trial["stimulus_with_numbers"].draw()
                show_clock(clock_image, clock, config)
                show_timer(timer, clock, config)
                answers_buttons[1].draw()
                answers_buttons[0].setText("".join(answer))
                answers_buttons[0].draw()

                check_exit()
                if event.getKeys(['backspace']):
                    answer = answer[:-1]
                elif event.getKeys(config["text_box_accept_key"]):
                    reaction_time = clock.getTime()
                    break
                elif len(answer) < config["text_box_max_elem"]:
                    for letter in allowed_keys:
                        if event.getKeys([letter]):
                            answer += letter
                else:
                    event.getKeys()
                win.flip()
        else:
            raise Exception("Wrong answers_type in config. Choose from keyboard, mouse, or text")

        # cleaning
        draw_stim_list(extra_text, False)
        trial["stimulus_with_numbers"].setAutoDraw(False)
        win.callOnFlip(clock.reset)
        win.callOnFlip(event.clearEvents)
        win.flip()

        correct_answer = str(answers.loc[answers['item_id'] == trial["image_ID"]]['answer'].iloc[0])
        item_type = answers.loc[answers['item_id'] == trial["image_ID"]]['item_type'].iloc[0]
        if answer:
            acc = 1 if answer == correct_answer else 0
        trial_results = {"n": n, "block_type": block_type,
                         "rt": reaction_time, "acc": acc,
                         "stimulus": trial["image_name"],
                         "answer": answer,
                         "correct_answer": correct_answer,
                         "item_type": item_type}
        RESULTS.append(trial_results)

        if config[f"fdbk_{block_type}"]:
            show_stim(feedback[acc], config["fdbk_show_time"], clock, win)

        wait_time = config["wait_time"] + random.random() * config["wait_jitter"]
        show_stim(None, wait_time, clock, win)

    if config["fixation_time"] == -1:
        fixation.setAutoDraw(False)
        win.flip()


def main():
    global PART_ID
    config = load_config()
    info, PART_ID = part_info(test=config["procedure_test"])

    screen_res = dict(get_screen_res())
    win = visual.Window(list(screen_res.values()), fullscr=True, units='pix', screen=0, color=config["screen_color"])

    clock = core.Clock()
    fixation = visual.TextBox2(win, color=config["fixation_color"], text=config["fixation_text"],
                               letterHeight=config["fixation_size"], pos=config["fixation_pos"],
                               alignment="center")

    clock_image = visual.ImageStim(win, image=join('images', 'clock.png'), interpolate=True,
                                   size=config['clock_size'], pos=config['clock_pos'])

    timer = visual.TextBox2(win, color=config["timer_color"], text=config["answer_time"],
                            letterHeight=config["timer_size"], pos=config["timer_pos"], alignment="center")

    extra_text = [visual.TextBox2(win, color=text["color"], text=text["text"], letterHeight=text["size"],
                                  pos=text["pos"], alignment="center")
                  for text in config["extra_text_to_show"]]

    if config["answers_type"] == "mouse":
        mouse = event.Mouse(visible=True)
        answers_buttons = {i: visual.ButtonStim(win, color=config["answer_color"], text=config["answer_symbols"][i],
                                                letterHeight=config["answer_size"], pos=config["answer_pos"][i],
                                                borderColor=config["answer_box_color"], borderWidth=0,
                                                size=config["answer_box_size"], fillColor=config["answer_fill_color"])
                           for i in config["answer_symbols"]}
    elif config["answers_type"] == "text":
        mouse = event.Mouse(visible=False)
        answers_buttons = [visual.TextBox2(win, color=config["text_box_text_color"], pos=config["text_box_pos"],
                                           letterHeight=config["text_box_text_size"], text="", alignment="center"),
                           visual.Rect(win, pos=config["text_box_pos"], height=config["text_box_height"],
                                       width=config["text_box_width"],
                                       fillColor=config["text_box_fill_color"],
                                       lineColor=config["text_box_line_color"],
                                       lineWidth=config["text_box_line_width"])]
    else:
        mouse = event.Mouse(visible=False)
        answers_buttons = None

    feedback_text = (config["fdbk_incorrect"], config["fdbk_no_answer"], config["fdbk_correct"])
    feedback = {i: visual.TextBox2(win, color=config["fdbk_color"], text=text, letterHeight=config["fdbk_size"],
                                   alignment="center")
                for (i, text) in zip([0, -1, 1], feedback_text)}

    # load data and prepare trials
    answers = pd.read_csv(join("images", "answers.csv"))
    training_images, experimental_images = load_images(randomize=config["randomize_trails"])
    training_images = prepare_block_stimulus(training_images, win, config, folder="training")
    experimental_images = prepare_block_stimulus(experimental_images, win, config, folder="experiment")

    # run blocks
    block(config=config, images=training_images, block_type="training", win=win, fixation=fixation, mouse=mouse,
          clock=clock, screen_res=screen_res, answers=answers, answers_buttons=answers_buttons, feedback=feedback,
          extra_text=extra_text, clock_image=clock_image, timer=timer)
    block(config=config, images=experimental_images, block_type="experiment", win=win, fixation=fixation, mouse=mouse,
          clock=clock, screen_res=screen_res, answers=answers, answers_buttons=answers_buttons, feedback=feedback,
          extra_text=extra_text, clock_image=clock_image, timer=timer)

    # end info
    show_info(win, join('.', 'messages', f'end.txt'), text_color=config["text_color"],
              text_size=config["text_size"], screen_res=screen_res)


if __name__ == "__main__":
    main()
