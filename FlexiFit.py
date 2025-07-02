import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from subprocess import call
from tkinter import messagebox, filedialog

import customtkinter as ctk
import matplotlib
import matplotlib.dates as mdates
from PIL import Image
from PIL.ImageTk import PhotoImage
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import random

workout_data = pd.read_csv(r"workoutsplit.csv")
# Replace 'your_file.csv' with the actual file path

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

matplotlib.use("TkAgg")

if os.name == 'nt':
    path = os.path.join(os.getenv("APPDATA"), "FlexiFit", "workouts")
    main_path = os.path.join(os.getenv("APPDATA"), "FlexiFit")

else:
    path = os.path.join(os.getenv("HOME"), "FlexiFit", "workouts")
    main_path = os.path.join(os.getenv("HOME"), "FlexiFit")

# Global variables
version = "0.6.2"
exercise_index = 0
info_index = 0
exercise_list = []
info_list = []



def check_files():
    # Check whether the specified path exists or not
    if not os.path.exists(path):
        os.makedirs(path)
        print("DIRECTORY CREATED")
    # Check if at least one workout file exists. If not, create a default workout.
    if len(get_stored_workouts()) == 0:
        workout_file = Path(os.path.join(path, "default.json"))
        workout_file.touch(exist_ok=True)
        if os.path.getsize(os.path.join(path, "default.json")) == 0:
            with open(os.path.join(path, "default.json"), "a") as file:
                file.write(
                    '{ "Push-ups": [ "10", "5", "" ], "Leg Raises": [ "30", "1", "" ], "Hip raises": [ "30", "1", "" ], "Toe touches": [ "30", "1", "" ], "Flutter kicks": [ "30", "1", "" ], "Sit-ups": [ "30", "1", "" ], "Pull-ups": [ "10", "1", "" ], "Chin-ups": [ "10", "1", "" ], "Biceps": [ "10", "1", "" ], "Forward fly": [ "10", "1", "" ], "Side fly": [ "10", "1", "" ], "Forearms": [ "50", "2", "" ] }')
    # Check if the user has updated from v0.2.0 to v0.3.0 or newer. If this is the case, the default exercise needs to be updated and all old exercises will be removed to prevent a startup crash.
    files = get_stored_workouts()
    filename = files[0]
    exercises = get_workout_data(os.path.join(path, filename + ".json"))
    if "exercises" in exercises:
        remove_files()
        check_files()
    # Check if the settings file exists. Create one if it doesn't.
    settings_path = Path(os.path.join(main_path, "settings.json"))
    settings_path.touch(exist_ok=True)
    if os.path.getsize(os.path.join(main_path, "settings.json")) == 0:
        print("CREATING SETTINGS FILE")
        with open(os.path.join(main_path, "settings.json"), "w") as file:
            settings = {
                "theme": "Dark"
            }
            json.dump(settings, file)
    # Check if the personal records file exists. Create one if it doesn't.
    pr_path = Path(os.path.join(main_path, "personal_records.json"))
    pr_path.touch(exist_ok=True)
    if os.path.getsize(os.path.join(main_path, "personal_records.json")) == 0:
        print("CREATING PERSONAL_RECORDS FILE")
        with open(os.path.join(main_path, "personal_records.json"), "w") as file:
            settings = {}
            json.dump(settings, file)


def export_workouts():
    save_path = filedialog.askdirectory(title="Choose export location")
    if save_path:
        shutil.make_archive(os.path.join(save_path, "FlexiFit_export"), "zip", path)
        messagebox.showinfo("FlexiFit", "Export complete")


def import_workouts():
    zip_file = filedialog.askopenfilename()
    filename, extension = os.path.splitext(zip_file)
    if zip_file:
        if extension != ".zip":
            messagebox.showerror("FlexiFit", "Selected file is not a .zip file")
        else:
            shutil.unpack_archive(zip_file, path, "zip")
            messagebox.showinfo("FlexiFit", "Import complete")
        workout_option_menu.configure(values=get_stored_workouts())


def create_new_workout_file():
    dialog = ctk.CTkInputDialog(text="Type in workout name:", title="New workout")
    dialog_input = dialog.get_input()
    if dialog_input is None or dialog_input == "":
        return
    if len(dialog_input) > 100:
        messagebox.showerror("FlexiFit", "Workout name too long")
        return
    if str(dialog_input).lower() in get_stored_workouts():
        messagebox.showerror("FlexiFit", "Workout with this name already exists")
        return
    filename = str(dialog_input + ".json")
    print("filename = " + filename)
    workout_file = Path(os.path.join(path, filename))
    workout_file.touch(exist_ok=True)
    workout_option_menu.configure(values=get_stored_workouts())
    workout_option_menu.set(filename.replace(".json", ""))
    view_workout()


def get_stored_workouts():
    found_workouts = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    found_workouts_not_hidden = []
    for workout in found_workouts:
        if workout[0] != "." and workout != "settings.json":
            found_workouts_not_hidden.append(workout.replace(".json", ""))
    print(f"found workouts: {found_workouts_not_hidden}")
    return found_workouts_not_hidden


def get_workout_steps_names():
    exercises = get_workout_data(os.path.join(path, workout_option_menu.get()) + ".json")
    print(str(exercises))
    keys = list(exercises)
    return keys


def get_pr_names():
    with open(os.path.join(main_path, "personal_records.json"), "r") as file:
        data = file.read()
    exercises = json.loads(data)
    print(str(exercises))
    keys = list(exercises)
    return keys


def get_workout_data(filename):
    with open(filename, "r") as file:
        return json.load(file)


def workout_option_menu_selection(choice):
    view_workout()


def stored_workout_menu_selection(choice):
    update_entries()


def pr_menu_selection(choice):
    return


def theme_option_selection(choice):
    print(f"Selected theme {choice}")
    change_theme(choice)


def change_theme(theme):
    print(f"CHANGING THEME TO {theme}")
    with open(os.path.join(main_path, "settings.json"), "r") as file:
        settings = json.load(file)
    settings["theme"] = str(theme)
    with open(os.path.join(main_path, "settings.json"), "w") as outfile:
        json.dump(settings, outfile)
    ctk.set_appearance_mode(str(theme).lower())
    if select_graph_menu.get() != "Select personal record":
        generate_graph()


def update_entries():
    print("UPDATING ENTRIES")
    exercises = get_workout_data(os.path.join(path, workout_option_menu.get()) + ".json")
    key = select_workout_step_menu.get()
    if key == "Select workout step":
        return
    clear_edit_entries()
    edit_name_exercise_entry.insert(0, key)
    edit_reps_entry.insert(0, exercises[key][0])
    edit_sets_entry.insert(0, exercises[key][1])
    if exercises[key][2] != "":
        edit_weight_entry.insert(0, exercises[key][2])


def reset_workout_view():
    exercise_text.configure(text="")
    reps_text.configure(text="")
    sets_text.configure(text="")
    weight_text.configure(text="")


def reset_pr_view():
    pr_exercise_text.configure(text="")
    pr_weight_text.configure(text="")
    pr_date_text.configure(text="")


def view_workout():
    reset_workout_view()
    print("VIEW WORKOUT")
    with open(os.path.join(path, workout_option_menu.get()) + ".json", "r") as file:
        data = file.read()
    if data != '{}' and len(data) > 0:
        exercises = json.loads(data)
        keys = list(exercises)
        exercise = ""
        reps = ""
        sets = ""
        weight = ""
        for key in keys:
            exercise += key + "\n"
            reps += str(exercises[key][0]) + "\n"
            sets += str(exercises[key][1]) + "\n"
            weight += str(exercises[key][2]) + "\n"
        exercise_text.configure(text=exercise)
        reps_text.configure(text=reps)
        sets_text.configure(text=sets)
        weight_text.configure(text=weight)
    elif len(data) == 0:
        with open(os.path.join(path, workout_option_menu.get() + ".json"), "w") as file:
            file.write('{}')
        print("ADDED INITIAL JSON DATA TO FILE")
        exercise_text.configure(text="(empty)")

    else:
        exercise_text.configure(text="(empty)")
    clear_edit_entries()
    select_workout_step_menu.configure(values=get_workout_steps_names())
    select_workout_step_menu.set("Select workout step")


def view_pr():
    reset_pr_view()
    print("VIEW PR")
    with open(os.path.join(main_path, "personal_records.json"), "r") as file:
        data = file.read()
    if data != '{}' and len(data) > 0:
        exercises = json.loads(data)
        keys = list(exercises)
        exercise = ""
        weight = ""
        date = ""
        for key in keys:
            exercise += key + "\n"
            weight += str(list(list(exercises[key])[1])[-1]) + "\n"
            date += str(list(list(exercises[key])[0])[-1]) + "\n"
        pr_exercise_text.configure(text=exercise)
        pr_weight_text.configure(text=weight)
        pr_date_text.configure(text=date)
    else:
        pr_exercise_text.configure(text="(no records)")
    clear_pr_entries()
    select_pr_menu.configure(values=get_pr_names())
    select_pr_menu.set("Select personal record")
    select_graph_menu.set("Select personal record")


def add_workout_step():
    name = name_exercise_entry.get()
    reps = reps_entry.get()
    sets = sets_entry.get()
    weight = weight_entry.get()
    if name == "" or reps == "" or sets == "":
        messagebox.showerror("FlexiFit", "One or more of the required fields are empty")
    elif not reps.isnumeric():
        messagebox.showerror("FlexiFit", "reps is not a number")
    elif not sets.isnumeric():
        messagebox.showerror("FlexiFit", "sets is not a number")
    else:
        exercises = get_workout_data(os.path.join(path, workout_option_menu.get() + ".json"))
        keys = list(exercises)
        if name in keys:
            messagebox.showerror("FlexiFit", "Exercise already exists")
            return
        exercises[name] = [str(reps), str(sets), str(weight)]
        with open(os.path.join(path, workout_option_menu.get() + ".json"), "w") as outfile:
            json.dump(exercises, outfile)
        view_workout()
        clear_entries()
        select_workout_step_menu.configure(values=get_workout_steps_names())


def remove_workout_step():
    name = select_workout_step_menu.get()
    exercises = get_workout_data(os.path.join(path, workout_option_menu.get() + ".json"))
    if name == "Select workout step":
        messagebox.showerror("FlexiFit", "No workout step selected")
        return
    del exercises[name]
    with open(os.path.join(path, workout_option_menu.get() + ".json"), "w") as outfile:
        json.dump(exercises, outfile)
    view_workout()
    clear_edit_entries()
    select_workout_step_menu.configure(values=get_workout_steps_names())
    select_workout_step_menu.set("Select workout step")


def edit_workout_step():
    name = edit_name_exercise_entry.get()
    reps = edit_reps_entry.get()
    sets = edit_sets_entry.get()
    weight = edit_weight_entry.get()
    if name == "":
        messagebox.showerror("FlexiFit", "No workout step selected")
    elif reps == "" or sets == "":
        messagebox.showerror("FlexiFit", "One or more of the required fields are empty")
    elif not reps.isnumeric():
        messagebox.showerror("FlexiFit", "reps is not a number")
    elif not sets.isnumeric():
        messagebox.showerror("FlexiFit", "sets is not a number")
    elif weight != "" and not weight.isnumeric():
        messagebox.showerror("FlexiFit", "weight is not a number")
    else:
        exercises = get_workout_data(os.path.join(path, workout_option_menu.get() + ".json"))
        keys = list(exercises)
        if name not in keys:
            messagebox.showerror("FlexiFit", "You can't change the exercise name")
            edit_name_exercise_entry.delete(0, 'end')
            edit_name_exercise_entry.insert(0, select_workout_step_menu.get())
            return
        exercises[name] = [str(reps), str(sets), str(weight)]
        with open(os.path.join(path, workout_option_menu.get() + ".json"), "w") as outfile:
            json.dump(exercises, outfile)
        view_workout()
        clear_edit_entries()
        select_workout_step_menu.configure(values=get_workout_steps_names())
        select_workout_step_menu.set("Select workout step")


def add_pr():
    name = pr_add_name_entry.get()
    weight = pr_add_weight_entry.get()
    if name == "" or weight == "":
        messagebox.showerror("FlexiFit", "One or more of the required fields are empty")
    elif not weight.isnumeric():
        messagebox.showerror("FlexiFit", "weight is not a number")
    else:
        with open(os.path.join(main_path, "personal_records.json"), "r") as file:
            data = file.read()
        exercises = json.loads(data)
        keys = list(exercises)
        if name in keys:
            messagebox.showerror("FlexiFit", "Personal record already exists")
            return
        exercises[name] = [[datetime.today().strftime('%d-%m-%Y')], [str(weight)]]
        with open(os.path.join(main_path, "personal_records.json"), "w") as outfile:
            json.dump(exercises, outfile)
        view_pr()
        clear_pr_entries()
        select_pr_menu.configure(values=get_pr_names())
        select_graph_menu.configure(values=get_pr_names())


def edit_pr():
    dialog = ctk.CTkInputDialog(text="Type in new record weight:", title="Update record")
    dialog_input = dialog.get_input()
    if dialog_input is None or dialog_input == "":
        return
    if len(dialog_input) > 100:
        messagebox.showerror("FlexiFit", "Record weight too long")
        return
    else:
        with open(os.path.join(main_path, "personal_records.json"), "r") as file:
            data = file.read()
        exercises = json.loads(data)
        keys = list(exercises)
        name = select_pr_menu.get()
        weight = dialog_input
        # "benchpress" : [[date, date, date], [weight weight weight]]

        record_dates = exercises[name][0]
        if datetime.today().strftime('%d-%m-%Y') in record_dates:
            print("Record for today already exists, replacing old record...")
            record_weights = exercises[name][1]
            record_weights[-1] = str(weight)
        else:
            record_dates.append(datetime.today().strftime('%d-%m-%Y'))
            record_weights = exercises[name][1]
            record_weights.append(str(weight))

        print(f"--------------NEW PR VALUE: {str([record_dates, record_weights])}")
        exercises[name] = [record_dates, record_weights]
        with open(os.path.join(main_path, "personal_records.json"), "w") as outfile:
            json.dump(exercises, outfile)
        view_pr()
        clear_pr_entries()
        select_pr_menu.configure(values=get_pr_names())
        select_graph_menu.configure(values=get_pr_names())


def remove_pr():
    name = select_pr_menu.get()
    if name == "Select personal record":
        messagebox.showerror("FlexiFit", "No record selected")
        return
    with open(os.path.join(main_path, "personal_records.json"), "r") as file:
        data = file.read()
    exercises = json.loads(data)
    del exercises[name]
    with open(os.path.join(main_path, "personal_records.json"), "w") as outfile:
        json.dump(exercises, outfile)
    clear_pr_entries()
    view_pr()
    select_pr_menu.configure(values=get_pr_names())
    select_graph_menu.configure(values=get_pr_names())
    messagebox.showinfo("FlexiFit", f'"{name}" record has been removed')


def remove_workout():
    workouts = get_stored_workouts()
    if len(workouts) == 1:
        messagebox.showerror("FlexiFit", f'You must have at least 1 workout')
        return
    name = workout_option_menu.get()
    print(f"filename = {name}")
    os.remove(os.path.join(path, name + ".json"))
    workout_option_menu.configure(values=get_stored_workouts())
    workout_option_menu.set(get_stored_workouts()[0])
    app.update()
    messagebox.showinfo("FlexiFit", f'"{name}" has been removed')
    view_workout()


def create_exercises_lists():
    global exercise_index
    global info_index
    global exercise_list
    global info_list
    global target_reps
    total_reps = 0
    total_volume = 0
    exercise_index = 0
    info_index = 0
    exercise_list = []
    info_list = []
    next_step_button.configure(text="START")
    exercises = get_workout_data(os.path.join(path, workout_option_menu.get() + ".json"))
    keys = list(exercises)
    
    for key in keys:
        reps = int(exercises[key][0])  # Target number of reps
        sets = int(exercises[key][1])
        for i in range(0, sets):
            exercise_list.append(f"{reps}x {key}")  # Add target reps and exercise to the list
            total_volume += reps * int(exercises[key][2]) if exercises[key][2] else 0
            info_list.append(f"Next up: {exercise_list[-1]}")
            info_list.append(f"Set {i + 1} of {sets}")
            exercise_list.append("Rest")
    
    exercise_list.append("Workout finished!")
    
    if total_volume > 0:
        info_list.append(f"You've done {total_reps} reps\nYour total volume is {total_volume}kg")
    else:
        info_list.append(f"You've done {total_reps} reps")
    
    info_label.configure(text=info_list[info_index])
    info_index += 1
    print(f"total reps = {total_reps}, total volume = {total_volume}")
    target_reps = int(exercise_list[exercise_index].split('x')[0])  # Initial target reps for the first exercise



# def create_exercises_lists():
#     global exercise_index
#     global info_index
#     global exercise_list
#     global info_list
#     total_reps = 0
#     total_volume = 0
#     exercise_index = 0
#     info_index = 0
#     exercise_list = []
#     info_list = []
#     next_step_button.configure(text="START")
#     exercises = get_workout_data(os.path.join(path, workout_option_menu.get() + ".json"))
#     keys = list(exercises)

#     for key in keys:
#         #edit
#         reps = int(exercises[key][0])  # First element: number of reps
#         sets = int(exercises[key][1])
#         for i in range(0, int(exercises[key][1])):
#             if exercises[key][2] == "":
#                 exercise_list.append(f"{exercises[key][0]}x {key}")
#             else:
#                 exercise_list.append(f"{exercises[key][0]}x {key} ({exercises[key][2]}kg)")
#                 total_volume += int(exercises[key][0]) * int(exercises[key][2])
#             total_reps += int(exercises[key][0])
#             info_list.append(f"Next up: {exercise_list[-1]}")
#             info_list.append(f"Set {i + 1} of {exercises[key][1]}")
#             exercise_list.append("Rest")
#     exercise_list[-1] = "Workout finished!"
#     if total_volume > 0:
#         info_list.append(f"You've done {total_reps} reps\nYour total volume is {total_volume}kg")
#     else:
#         info_list.append(f"You've done {total_reps} reps")
#     info_label.configure(text=info_list[info_index])
#     info_index += 1
#     print(f"total reps = {total_reps}, total volume = {total_volume}")


def next_step():
    global exercise_index
    global info_index
    global exercise_list
    global info_list
    progressbar.configure(width=app.winfo_width())
    progressbar.set(info_index / len(exercise_list))
    next_step_button.configure(text="Next step")
    if info_index == len(info_list):
        raise_main_frame()
        return
    if int(len(exercise_list[exercise_index])) > 25:
        current_workout_step_label.cget("font").configure(size=50)
    else:
        current_workout_step_label.cget("font").configure(size=100)
    #edit
    current_exercise = exercise_list[exercise_index]
    current_workout_step_label.configure(text=current_exercise)
    #edit
    exercise_name = current_exercise.split('x')[1].strip()  # Get the exercise name after the reps

    exercise_index += 1
    info_label.configure(text=info_list[info_index])
    info_index += 1
    if info_index == len(info_list):
        next_step_button.configure(text="Finish")
    #edit
    function_call(exercise_name)


def generate_graph():
    for widget in graph_frame.winfo_children():
        widget.destroy()

    with open(os.path.join(main_path, "settings.json")) as settings_file_graph:
        settings_data_graph = json.load(settings_file_graph)

    if str(settings_data_graph["theme"]).lower() == "light":
        background_color = "#e2e2e2"
        graph_color = "black"
    else:
        background_color = "#333333"
        graph_color = "white"

    dates = []
    records = []

    with open(os.path.join(main_path, "personal_records.json"), "r") as file:
        data = file.read()
    if data != '{}' and len(data) > 0 and select_graph_menu.get() != "Select personal record":
        exercises = json.loads(data)
    else:
        messagebox.showerror("FlexiFit", "No personal record selected. Select a record or add a new one.")
        return

    dates_list_string = exercises[select_graph_menu.get()][0]
    for date in dates_list_string:
        dates.append(datetime.strptime(date, '%d-%m-%Y'))

    records_list_string = exercises[select_graph_menu.get()][1]
    for record in records_list_string:
        records.append(int(record))

    f, a = plt.subplots(figsize=(6, 5), dpi=100)
    a.plot(dates, records, linestyle="solid", color="#3C99DC")

    plt.xlabel('Date')
    plt.ylabel('Weight (kg)')

    date_format = mdates.DateFormatter('%b-%y')
    a.xaxis.set_major_formatter(date_format)
    a.xaxis.set_major_locator(mdates.MonthLocator(interval=1))

    a.set_facecolor(background_color)
    f.patch.set_facecolor(background_color)
    a.spines['top'].set_color(background_color)
    a.spines['right'].set_color(background_color)
    a.spines['bottom'].set_color(graph_color)
    a.spines['left'].set_color(graph_color)
    a.xaxis.label.set_color(graph_color)
    a.yaxis.label.set_color(graph_color)
    a.tick_params(axis='x', colors=graph_color)
    a.tick_params(axis='y', colors=graph_color)

    canvas = FigureCanvasTkAgg(f, graph_frame)

    canvas.get_tk_widget().pack(side=ctk.TOP, fill=ctk.BOTH, expand=False)
    img = PhotoImage(file='media/icon.ico')
    app.tk.call('wm', 'iconphoto', app._w, img)


# def check_connection():
#     connection = httplib.HTTPConnection("www.github.com", timeout=5)
#     try:
#         # only header requested for fast operation
#         connection.request("HEAD", "/")
#         connection.close()
#         print("Internet On")
#         return True
#     except Exception as exep:
#         print(exep)
#         return False


# def check_for_updates(alert_when_no_update=False):
#     print("CHECKING FOR UPDATES")
#     if not check_connection():
#         if alert_when_no_update:
#             messagebox.showerror("FlexiFit", "Unable to check for updates: no internet connection")
#         return
#     tag = requests.get("https://api.github.com/repos/MrBananaPants/FlexiFit/releases/latest").text
#     tag = json.loads(tag)
#     print(str(tag))
#     if list(tag)[0] != "url":
#         if alert_when_no_update:
#             messagebox.showerror("FlexiFit", "API rate limit exceeded, press OK to manually download the newest version")
#             webbrowser.open('https://github.com/MrBananaPants/FlexiFit/releases/latest', new=2)
#         return None
#     latest_version = int(str(tag["tag_name"]).lstrip('0').replace(".", ""))
#     current_version = int(str(version).lstrip('0').replace(".", ""))
#     latest_version_formatted = str(tag["tag_name"])
#     print(f"latest: {latest_version}, installed: {current_version}")

#     if latest_version > current_version:
#         if messagebox.askyesno("FlexiFit", f"An update is available (v{latest_version_formatted}). Do you want to download this update?"):
#             save_path = filedialog.askdirectory(title="Select save location")
#             try:
#                 if os.name == 'nt':
#                     urllib.request.urlretrieve(f"https://github.com/MrBananaPants/FlexiFit/releases/download/{latest_version_formatted}/FlexiFit.exe",
#                                                os.path.join(save_path, "FlexiFit.exe"))
#                     messagebox.showinfo("FlexiFit", "The latest version has been downloaded")
#                     os.startfile(save_path)
#                 else:
#                     urllib.request.urlretrieve(f"https://github.com/MrBananaPants/FlexiFit/releases/download/{latest_version_formatted}/FlexiFit.dmg",
#                                                os.path.join(save_path, "FlexiFit.dmg"))
#                     messagebox.showinfo("FlexiFit", "The latest version has been downloaded")
#                     call(["open", "-R", os.path.join(save_path, "FlexiFit.dmg")])

#             except urllib.error.HTTPError:
#                 messagebox.showerror("FlexiFit", "Cannot download latest version. Press OK to manually download the newest version")
#                 webbrowser.open('https://github.com/MrBananaPants/FlexiFit/releases/latest', new=2)

#     elif alert_when_no_update:
#         messagebox.showinfo("FlexiFit", "You already have the latest version installed")


def reset():
    if messagebox.askyesno("FlexiFit",
                           f"Are you sure you want to continue? This will remove all custom workouts, personal records and reset all settings to their default value."):
        clear_entries()
        clear_edit_entries()
        remove_files()
        check_files()
        workout_option_menu.configure(values=get_stored_workouts())
        workout_option_menu.set(get_stored_workouts()[0])
        select_workout_step_menu.configure(values=get_workout_steps_names())
        select_workout_step_menu.set(get_workout_steps_names()[0])
        tabview.set("Home")
        ctk.set_appearance_mode("dark")
        theme_selection.set("Dark")
        app.update()
        view_workout()
        view_pr()
        for widget in graph_frame.winfo_children():
            widget.destroy()
        messagebox.showinfo("FlexiFit", "Reset complete")


def remove_files():
    shutil.rmtree(main_path)


def clear_entries():
    name_exercise_entry.delete(0, 'end')
    name_exercise_entry.configure(placeholder_text="Exercise name")
    reps_entry.delete(0, 'end')
    reps_entry.configure(placeholder_text="Amount of reps")
    sets_entry.delete(0, 'end')
    sets_entry.configure(placeholder_text="Amount of sets")
    weight_entry.delete(0, 'end')
    weight_entry.configure(placeholder_text="Weight (leave blank for no weight)")


def clear_pr_entries():
    pr_add_name_entry.delete(0, 'end')
    pr_add_name_entry.configure(placeholder_text="Record name")
    pr_add_weight_entry.delete(0, 'end')
    pr_add_weight_entry.configure(placeholder_text="Record weight")


def clear_edit_entries():
    edit_name_exercise_entry.delete(0, 'end')
    edit_name_exercise_entry.configure(placeholder_text="Exercise name")
    edit_reps_entry.delete(0, 'end')
    edit_reps_entry.configure(placeholder_text="Amount of reps")
    edit_sets_entry.delete(0, 'end')
    edit_sets_entry.configure(placeholder_text="Amount of sets")
    edit_weight_entry.delete(0, 'end')
    edit_weight_entry.configure(placeholder_text="Weight (no weight for selected step)")


def raise_main_frame():
    main_frame.pack(anchor="w", fill="both", expand=True)
    workout_frame.pack_forget()


#Period Tracker

def get_phase(cycle_day, length_of_cycle):
    if 1 <= cycle_day <= 5:
        return 'Menstrual'
    elif 6 <= cycle_day <= length_of_cycle // 2:
        return 'Follicular'
    elif (length_of_cycle // 2) < cycle_day <= (length_of_cycle // 2) + 3:
        return 'Ovulation'
    else:
        return 'Luteal'

def get_exercises_for_phase(phase):
    if phase == 'Menstrual':
        # Low to moderate difficulty exercises
        return workout_data[workout_data['Difficulty Rating (Energy Consumption / 5)'] <= 2]
    elif phase == 'Follicular':
        # Moderate difficulty exercises
        return workout_data[(workout_data['Difficulty Rating (Energy Consumption / 5)'] > 2) & 
                            (workout_data['Difficulty Rating (Energy Consumption / 5)'] <= 3)]
    elif phase == 'Ovulation':
        # High difficulty exercises
        return workout_data[(workout_data['Difficulty Rating (Energy Consumption / 5)'] > 3) & 
                            (workout_data['Difficulty Rating (Energy Consumption / 5)'] <= 4)]
    elif phase == 'Luteal':
        # Mix of moderate to high difficulty exercises
        return workout_data[workout_data['Difficulty Rating (Energy Consumption / 5)'] >= 3]
    else:
        return pd.DataFrame()  # Return an empty DataFrame if the phase is not recognized
    
def get_recommended_workout():
    try:
        current_cycle_day = int(cycle_day_entry.get())
        cycle_length = int(cycle_length_entry.get())

        if current_cycle_day < 1 or current_cycle_day > cycle_length:
            results_label.configure(text="Invalid cycle day. Please enter a day within the range of your cycle length.")
            return

        # Identify the cycle phase
        phase = get_phase(current_cycle_day, cycle_length)
        results_label.configure(text=f"You are in the {phase} phase of your cycle.")

        # Get and display the recommended workout plan
        recommended_exercises = get_exercises_for_phase(phase)

        if not recommended_exercises.empty:
            # Display unique muscle groups available for the current phase
            muscle_groups = recommended_exercises['Muscle Group'].unique()
            muscle_group_options = "\n".join([f"{idx + 1}. {muscle}" for idx, muscle in enumerate(muscle_groups)])
            results_label.configure(text=f"You can focus on:\n{muscle_group_options}\n\nEnter the number of the muscle group you want to work on:")

            # Clear the muscle group entry field for user input
            muscle_group_entry.delete(0, 'end')  # Clear current entry
        else:
            results_label.configure(text="No recommended exercises found for this phase.")
    except ValueError:
        results_label.configure(text="Invalid input. Please enter numeric values for the cycle day and length.")

# Function to handle muscle group selection
def handle_muscle_group_selection():
    try:
        muscle_choice = int(muscle_group_entry.get())
        current_cycle_day = int(cycle_day_entry.get())
        cycle_length = int(cycle_length_entry.get())
        phase = get_phase(current_cycle_day, cycle_length)

        recommended_exercises = get_exercises_for_phase(phase)
        muscle_groups = recommended_exercises['Muscle Group'].unique()

        if muscle_choice < 1 or muscle_choice > len(muscle_groups):
            results_label .configure(text="Invalid muscle group choice. Please enter a valid number corresponding to the muscle group.")
            return

        chosen_muscle_group = muscle_groups[muscle_choice - 1]

        # Filter the workout plan based on the chosen muscle group
        chosen_workout_plan = recommended_exercises[recommended_exercises['Muscle Group'] == chosen_muscle_group]

        # Display the chosen workout split
        workout_plan = chosen_workout_plan[['Muscle Group', 'Exercise', 'min reps', 'max reps', 'sets']]
        results_label.configure(text=f"Recommended workout plan for the {chosen_muscle_group} muscle group:\n{workout_plan.to_string(index=False)}")
    except ValueError:
        results_label.configure(text="Invalid input. Please enter a numeric value for the muscle group.")

def reset_fields():
    cycle_day_entry.delete(0, 'end')
    cycle_length_entry.delete(0, 'end')
    muscle_group_entry.delete(0, 'end')
    results_label.configure(text="")
    

# #water tracker
# class WaterTracker:
#     def __init__(self, gender, activity_level):
#         self.gender = gender
#         self.activity_level = activity_level
#         self.total_water_liters = self.calculate_daily_water_intake()
#         self.glasses_per_liter = 4  # Assuming 1 glass = 250 ml
#         self.total_glasses = int(self.total_water_liters * self.glasses_per_liter)
#         self.remaining_glasses = self.total_glasses

#     def calculate_daily_water_intake(self):
#         if self.gender.lower() == 'male':
#             return 3.7 if self.activity_level else 3.0  # Liters for active/inactive males
#         elif self.gender.lower() == 'female':
#             return 2.7 if self.activity_level else 2.2  # Liters for active/inactive females
#         else:
#             raise ValueError("Invalid gender input. Please enter 'male' or 'female'.")

#     def drink_glass(self):
#         if self.remaining_glasses > 0:
#             self.remaining_glasses -= 1
#             remaining_liters = self.remaining_glasses / self.glasses_per_liter
#             return f"You drank a glass of water. Remaining: {self.remaining_glasses} glasses ({remaining_liters:.2f} liters)."
#         else:
#             return "Target reached! You have met your daily water intake goal."

#     def display_status(self):
#         remaining_liters = self.remaining_glasses / self.glasses_per_liter
#         if self.remaining_glasses > 0:
#             return f"Remaining: {self.remaining_glasses} glasses ({remaining_liters:.2f} liters)."
#         else:
#             return "Congratulations! You have completed your daily water intake."

# # Example usage
# if __name__ == "__main__":
#     # Create an instance of WaterTracker
#     tracker = WaterTracker(gender='male', activity_level=True)

#     # Display initial status
#     print(tracker.display_status())

#     # Drink a glass of water
#     print(tracker.drink_glass())

#     # Display status again
#     print(tracker.display_status())

# #Water Tracker
# class WaterTracker:
#     def __init__(self, gender, activity_level):
#         self.gender = gender
#         self.activity_level = activity_level
#         self.total_water_liters = self.calculate_daily_water_intake()
#         self.glasses_per_liter = 4  # Assuming 1 glass = 250 ml
#         self.total_glasses = int(self.total_water_liters * self.glasses_per_liter)
#         self.remaining_glasses = self.total_glasses

#     def calculate_daily_water_intake(self):
#         # Daily water intake based on gender and activity level
#         if self.gender.lower() == 'male':
#             return 3.7 if self.activity_level else 3.0  # Liters for active/inactive males
#         elif self.gender.lower() == 'female':
#             return 2.7 if self.activity_level else 2.2  # Liters for active/inactive females
#         else:
#             raise ValueError("Invalid gender input. Please enter 'male' or 'female'.")

#     def drink_glass(self):
#         if self.remaining_glasses > 0:
#             self.remaining_glasses -= 1
#             remaining_liters = self.remaining_glasses / self.glasses_per_liter
#             return f"You drank a glass of water. Remaining: {self.remaining_glasses} glasses ({remaining_liters:.2f} liters)."
#         else:
#             return "Target reached! You have met your daily water intake goal."

#     def display_status(self):
#         remaining_liters = self.remaining_glasses / self.glasses_per_liter
#         if self.remaining_glasses > 0:
#             return f"Remaining: {self.remaining_glasses} glasses ({remaining_liters:.2f} liters)."
#         else:
#             return "Congratulations! You have completed your daily water intake."



#Food tracker
def calculate_bmi(weight, height):
    print("calculate bmi")
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    if bmi < 18.5:
        category = "Underweight"
    elif 18.5 <= bmi < 24.9:
        category = "Normal weight"
    elif 25 <= bmi < 29.9:
        category = "Overweight"
    else:
        category = "Obese"
    return bmi, category

# Function to calculate recommended daily calorie intake
def calculate_calories(weight, height, age, gender, activity_level, target_weight):
    print("Calculate calories")
    if gender.lower() == 'male':
        bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
    
    activity_factors = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very active': 1.9
    }
    calories = bmr * activity_factors[activity_level.lower()]

    # Adjust for target weight: deficit or surplus
    if target_weight < weight:
        calories -= 500  # Calorie deficit for weight loss
    elif target_weight > weight:
        calories += 500  # Calorie surplus for weight gain
    
    return calories


import random

import pandas as pd
import random

# Assuming food_data is already loaded as a DataFrame
food_data = pd.read_csv(r"food_data.csv", encoding='ISO-8859-1')  # or 'latin1'

def generate_meal_plan():
    try:
        weight_str = weight_entry.get().strip()
        height_str = height_entry.get().strip()
        age_str = age_entry.get().strip()
        target_weight_str = target_weight_entry.get().strip()

        # Check if any of the fields are empty
        if not weight_str or not height_str or not age_str or not target_weight_str:
            raise ValueError("All fields must be filled out.")

        # Convert inputs to appropriate types
        weight = float(weight_str)
        height = float(height_str)
        age = int(age_str)
        gender = gender_entry.get().strip().lower()
        activity_level = activity_entry.get().strip().lower()

        # Calculate daily calorie intake
        calories = calculate_calories(weight, height, age, gender, activity_level, float(target_weight_str))

        # Generate meal plan
        breakfast, lunch, dinner, total_calories = create_meal_plan(calories, food_data)

        # Update UI labels with meal plan details
        breakfast_label.configure(text="Breakfast:\n" + "\n".join(f"- {item[1]}: {item[8]} calories" for item in breakfast))
        lunch_label.configure(text="Lunch:\n" + "\n".join(f"- {item[1]}: {item[8]} calories" for item in lunch))
        dinner_label.configure(text="Dinner:\n" + "\n".join(f"- {item[1]}: {item[8]} calories" for item in dinner))
        total_calories_label.configure(text=f"Total Calories: {total_calories}")

    except ValueError as ve:
        output_label.configure(text=f"Error: {ve}")
    except Exception as e:
        output_label.configure(text="Error generating meal plan. Please check your inputs.")

def create_meal_plan(calories, food_data):
    breakfast = []
    lunch = []
    dinner = []
    total_calories = 0

    # Adjusting the while loop to ensure we get a meal plan within the desired calorie range
    while (total_calories < calories - 50 or total_calories > calories + 50):
        breakfast = random.sample(list(food_data.itertuples(index=False, name=None)), 1)  # Sample one item for breakfast
        lunch = random.sample(list(food_data.itertuples(index=False, name=None)), 2)  # Sample two items for lunch
        dinner = random.sample(list(food_data.itertuples(index=False, name=None)), 1)  # Sample one item for dinner

        total_calories = (
            sum(item[-1] for item in breakfast) +
            sum(item[-1] for item in lunch) +
            sum(item[-1] for item in dinner)
        )

    return breakfast, lunch, dinner, total_calories

# def create_meal_plan(calories, food_data):
#     breakfast = []
#     lunch = []
#     dinner = []
#     total_calories = 0


#     while (total_calories < calories - 50 or total_calories > calories + 50):
#         breakfast = random.sample(list(food_data.itertuples(index=False, name=None)), 5)
#         lunch = random.sample(list(food_data.itertuples(index=False, name=None)), 10)
#         dinner = random.sample(list(food_data.itertuples(index=False, name=None)), 5)

#         total_calories = (
#             sum(item[-1] for item in breakfast) +
#             sum(item[-1] for item in lunch) +
#             sum(item[-1] for item in dinner)
#         )

#         # Debugging output to see the total calories for each attempt
#         print(f"Attempt {attempts + 1}: Total Calories = {total_calories}")

#         attempts += 1
#     return breakfast, lunch, dinner, total_calories

# # Function to create a detailed meal plan
# def create_meal_plan(calories, food_data):
#     breakfast = []
#     lunch = []
#     dinner = []
#     total_calories = 0

#     max_attempts = 1000  # Set a reasonable limit
#     attempts = 0

#     while (total_calories < calories - 20 or total_calories > calories + 20) and attempts < max_attempts:
#         breakfast = random.sample(list(food_data.itertuples(index=False, name=None)), 5)
#         lunch = random.sample(list(food_data.itertuples(index=False, name=None)), 10)
#         dinner = random.sample(list(food_data.itertuples(index=False, name=None)), 5)

#         total_calories = (
#             sum(item[-1] for item in breakfast) +
#             sum(item[-1] for item in lunch) +
#             sum(item[-1] for item in dinner)
#         )
#         attempts += 1

#     if attempts == max_attempts:
#         raise ValueError("Unable to generate a meal plan within the calorie range.")

#     return breakfast, lunch, dinner, total_calories

# def generate_meal_plan():
#     print("Generate Meal Plan button clicked")  # Check if the function is called
#     try:
#         # Get user inputs
#         weight_str = weight_entry.get().strip()  # Strip whitespace
#         height_str = height_entry.get().strip()  # Strip whitespace
#         age_str = age_entry.get().strip()  # Strip whitespace
#         target_weight_str = target_weight_entry.get().strip()  # Strip whitespace

#         # Debugging: Print the values retrieved from the input fields
#         print(f"Weight input: '{weight_str}', Height input: '{height_str}', Age input: '{age_str}', Target Weight input: '{target_weight_str}'")

#         # Check if any of the fields are empty
#         if not weight_str or not height_str or not age_str or not target_weight_str:
#             raise ValueError("All fields must be filled out.")

#         # Convert inputs to appropriate types
#         weight = float(weight_str)
#         height = float(height_str)
#         age = int(age_str)
#         gender = gender_entry.get().strip().lower()
#         activity_level = activity_entry.get().strip().lower()

#         print(f"Weight: {weight}, Height: {height}, Age: {age}, Gender: {gender}, Activity Level: {activity_level}, Target Weight: {target_weight_str}")

#         # Check if food_data exists and is not empty
#         if 'food_data' not in globals() or food_data.empty:
#             raise ValueError("food_data is not defined or is empty.")

#         # Calculate daily calorie intake
#         calories = calculate_calories(weight, height, age, gender, activity_level, float(target_weight_str))
#         print(f"Calories calculated: {calories}")  # Debugging output

#         # Generate meal plan
#         breakfast, lunch, dinner, total_calories = create_meal_plan(calories, food_data)
#         print(f"Breakfast items: {breakfast}")  # Debugging output
#         print(f"Lunch items: {lunch}")  # Debugging output
#         print(f"Dinner items: {dinner}")  # Debugging output
#         print(f"Total calories: {total_calories}")  # Debugging output

#         # Update UI labels with meal plan details
#         breakfast_label.configure(text="Breakfast:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in breakfast))
#         lunch_label.configure(text="Lunch:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in lunch))
#         dinner_label.configure(text="Dinner:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in dinner))
#         total_calories_label.configure(text=f"Total Calories: {total_calories}")

#     except ValueError as ve:
#         print(f"ValueError: {ve}")  # Print the specific value error
#         output_label.configure(text=f"Error: {ve}")  # Use configure instead of config
#     except Exception as e:
#         print(f"Error: {e}")  # Print any other errors
#         output_label.configure(text="Error generating meal plan. Please check your inputs.")

# def generate_meal_plan():
#     print("Generate Meal Plan button clicked")  # Check if the function is called
#     try:
#         # Get user inputs
#         weight_str = weight_entry.get().strip()  # Strip whitespace
#         height_str = height_entry.get().strip()  # Strip whitespace
#         age_str = age_entry.get().strip()  # Strip whitespace
#         target_weight_str = target_weight_entry.get().strip()  # Strip whitespace

#         # Debugging: Print the values retrieved from the input fields
#         print(f"Weight input: '{weight_str}', Height input: '{height_str}', Age input: '{age_str}', Target Weight input: '{target_weight_str}'")

#         # Check if any of the fields are empty
#         if not weight_str or not height_str or not age_str or not target_weight_str:
#             raise ValueError("All fields must be filled out.")

#         # Convert inputs to appropriate types
#         weight = float(weight_str)
#         height = float(height_str)
#         age = int(age_str)
#         gender = gender_entry.get().strip().lower()
#         activity_level = activity_entry.get().strip().lower()

#         print(f"Weight: {weight}, Height: {height}, Age: {age}, Gender: {gender}, Activity Level: {activity_level}, Target Weight: {target_weight_str}")

#         # Check if food_data exists and is not empty
#         if 'food_data' not in globals() or food_data.empty:
#             raise ValueError("food_data is not defined or is empty.")

#         # Calculate daily calorie intake
#         calories = calculate_calories(weight, height, age, gender, activity_level, float(target_weight_str))
#         print(f"Calories calculated: {calories}")  # Debugging output
        
#         # Generate meal plan
#         breakfast, lunch, dinner, total_calories = create_meal_plan(calories, food_data)
#         print(f"Breakfast items: {breakfast}")  # Debugging output
#         print(f"Lunch items: {lunch}")  # Debugging output
#         print(f"Dinner items: {dinner}")  # Debugging output
#         print(f"Total calories: {total_calories}")  # Debugging output

#         # Update UI labels with meal plan details
#         breakfast_label.configure(text="Breakfast:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in breakfast))
#         lunch_label.configure(text="Lunch:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in lunch))
#         dinner_label.configure(text="Dinner:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in dinner))
#         total_calories_label.configure(text=f"Total Calories: {total_calories}")

#     except ValueError as ve:
#         print(f"ValueError: {ve}")  # Print the specific value error
#         output_label.configure(text=f"Error: {ve}")  # Use configure instead of config
#     except Exception as e:
#         print(f"Error: {e}")  # Print any other errors
#         output_label.configure(text="Error generating meal plan. Please check your inputs.")

# def generate_meal_plan():
#     print("Generate Meal Plan button clicked")  # Check if the function is called
#     try:
#         # Get user inputs and validate them
#         weight_str = weight_entry.get()
#         height_str = height_entry.get()
#         age_str = age_entry.get()
#         target_weight_str = target_weight_entry.get()

#         # Check if any of the fields are empty
#         if not weight_str or not height_str or not age_str or not target_weight_str:
#             raise ValueError("All fields must be filled out.")

#         weight = float(weight_str)
#         height = float(height_str)
#         age = int(age_str)
#         gender = gender_entry.get().strip().lower()
#         activity_level = activity_entry.get().strip().lower()

#         print(f"Weight: {weight}, Height: {height}, Age: {age}, Gender: {gender}, Activity Level: {activity_level}, Target Weight: {target_weight_str}")

#         # Check if food_data exists and is not empty
#         if 'food_data' not in globals() or food_data.empty:
#             raise ValueError("food_data is not defined or is empty.")

#         # Calculate daily calorie intake
#         calories = calculate_calories(weight, height, age, gender, activity_level, float(target_weight_str))
#         print(f"Calories calculated: {calories}")  # Debugging output
        
#         # Generate meal plan
#         breakfast, lunch, dinner, total_calories = create_meal_plan(calories, food_data)
#         print(f"Breakfast items: {breakfast}")  # Debugging output
#         print(f"Lunch items: {lunch}")  # Debugging output
#         print(f"Dinner items: {dinner}")  # Debugging output
#         print(f"Total calories: {total_calories}")  # Debugging output

#         # Update UI labels with meal plan details
#         breakfast_label.configure(text="Breakfast:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in breakfast))
#         lunch_label.configure(text="Lunch:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in lunch))
#         dinner_label.configure(text="Dinner:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in dinner))
#         total_calories_label.configure(text=f"Total Calories: {total_calories}")

#     except ValueError as ve:
#         print(f"ValueError: {ve}")  # Print the specific value error
#         output_label.configure(text=f"Error: {ve}")  # Use configure instead of config
#     except Exception as e:
#         print(f"Error: {e}")  # Print any other errors
#         output_label.configure(text="Error generating meal plan. Please check your inputs.")

# def generate_meal_plan():
#     print("Generate Meal Plan button clicked")

#     try:
#         weight = float(weight_entry.get())
#         height = float(height_entry.get())
#         age = int(age_entry.get())
#         gender = gender_entry.get().strip().lower()
#         activity_level = activity_entry.get().strip().lower()
#         target_weight = float(target_weight_entry.get())

#         # Check if food_data exists and is not empty
#         if 'food_data' not in globals() or food_data.empty:
#             raise ValueError("food_data is not defined or is empty.")

#         # Calculate daily calorie intake
#         calories = calculate_calories(weight, height, age, gender, activity_level, target_weight)
        
#         # Generate meal plan
#         breakfast, lunch, dinner, total_calories = create_meal_plan(calories, food_data)

#         # Update UI labels with meal plan details
#         breakfast_label.configure(text="Breakfast:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in breakfast))
#         lunch_label.configure(text="Lunch:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in lunch))
#         dinner_label.configure(text="Dinner:\n" + "\n".join(f"- {item[1]}: {item[2]} calories" for item in dinner))
#         total_calories_label.configure(text=f"Total Calories: {total_calories}")

#         print(f"Calories calculated: {calories}")
#         print(f"Breakfast items: {breakfast}")
#         print(f"Lunch items: {lunch}")
#         print(f"Dinner items: {dinner}")
#         print(f"Total calories: {total_calories}")

#     except Exception as e:
#         print(f"Error: {e}")
#         output_label.configure(text="Error generating meal plan. Please check your inputs.")




    

# def get_recommended_workout():
#     try:
#         current_cycle_day = int(cycle_day_entry.get())
#         cycle_length = int(cycle_length_entry.get())

#         if current_cycle_day < 1 or current_cycle_day > cycle_length:
#             results_label.configure(text="Invalid cycle day. Please enter a day within the range of your cycle length.")
#             return

#         # Identify the cycle phase
#         phase = get_phase(current_cycle_day, cycle_length)
#         results_label.configure(text=f"You are in the {phase} phase of your cycle.")

#         # Get and display the recommended workout plan
#         recommended_exercises = get_exercises_for_phase(phase)

#         if not recommended_exercises.empty:
#             # Display unique muscle groups available for the current phase
#             muscle_groups = recommended_exercises['Muscle Group'].unique()
#             muscle_group_options = "\n".join([f"{idx + 1}. {muscle}" for idx, muscle in enumerate(muscle_groups)])
#             results_label.configure(text=f"You can focus on:\n{muscle_group_options}\n\nEnter the number of the muscle group you want to work on:")

#             # Take user input for the muscle group they want to focus on
#             muscle_choice = int(input("Enter the number corresponding to the muscle group you want to work on: "))
#             chosen_muscle_group = muscle_groups[muscle_choice - 1]

#             # Filter the workout plan based on the chosen muscle group
#             chosen_workout_plan = recommended_exercises[recommended_exercises['Muscle Group'] == chosen_muscle_group]

#             # Display the chosen workout split
#             workout_plan = chosen_workout_plan[['Muscle Group', 'Exercise', 'min reps', 'max reps', 'sets']]
#             results_label.configure(text=f"Recommended workout plan for the {chosen_muscle_group} muscle group:\n{workout_plan.to_string(index=False)}")
#         else:
#             results_label.configure(text="No recommended exercises found for this phase.")
#     except ValueError:
#         results_label.configure(text="Invalid input. Please enter numeric values for the cycle day and length.")



# #user info
# # User Info Section in Settings
# def display_user_info():
#     user_info = get_user_info()
#     if user_info:
#         user_info_text = f"Gender: {user_info.get('gender', 'N/A')}\n" \
#                          f"Age: {user_info.get('age', 'N/A')}\n" \
#                          f"Weight: {user_info.get('weight', 'N/A')}\n" \
#                          f"Height: {user_info.get('height', 'N/A')}"
#         user_info_label.configure(text=user_info_text)
#     else:
#         user_info_label.configure(text="No user information available.")

# def update_user_info_dialog():
#     if not get_user_info():
#         # Prompt for new user information
#         gender = ctk.CTkInputDialog(text="Enter your gender:", title="User  Info")
#         age = ctk.CTkInputDialog(text="Enter your age:", title="User  Info")
#         weight = ctk.CTkInputDialog(text="Enter your weight:", title="User  Info")
#         height = ctk.CTkInputDialog(text="Enter your height:", title="User  Info")

#         if gender and age and weight and height:
#             update_user_info(gender, age, weight, height)
#             display_user_info()  # Refresh display after update
#     else:
#         # If user info already exists, ask to update
#         if messagebox.askyesno("Update User Info", "User  information already exists. Do you want to update it?"):
#             update_user_info_dialog()

# # UI Elements for User Info in Settings


# # Call display_user_info on loading settings
# def get_user_info():
#     settings_path = Path(os.path.join(main_path, "settings.json"))
#     with open(settings_path, "r") as file:
#         settings = json.load(file)
#     return settings.get("user_info", {})

# def update_user_info(gender, age, weight, height):
#     settings_path = Path(os.path.join(main_path, "settings.json"))
#     with open(settings_path, "r") as file:
#         settings = json.load(file)

#     settings["user_info"] = {
#         "gender": gender,
#         "age": age,
#         "weight": weight,
#         "height": height
#     }

#     with open(settings_path, "w") as outfile:
#         json.dump(settings, outfile)
#     messagebox.showinfo("FlexiFit", "User  information updated successfully")

# def update_user_info_dialog():
#     gender = gender_entry.get()
#     age = age_entry.get()
#     weight = weight_entry.get()
#     height = height_entry.get()

#     if gender and age and weight and height:
#         update_user_info(gender, age, weight, height)
#     else:
#         messagebox.showerror("FlexiFit", "Please fill in all fields.")


#shravya codeeeeeeeeeeee
    

def calculate_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle



def function_call(selected_exercise):
    global exercise_index
    cap = cv2.VideoCapture(0)
    counter = 0
    stage = None
    #target_reps = int(exercise_list[exercise_index].split('x')[0])  # Get target reps from the exercise list

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = pose.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            try:
                landmarks = results.pose_landmarks.landmark

                # Define key landmarks for both sides
                left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                                 landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                left_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                              landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
                left_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                              landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
                left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                            landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
                left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                             landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                              landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]

                right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                                  landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                right_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                               landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
                right_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                               landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
                right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                             landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
                right_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x,
                              landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
                right_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x,
                               landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]

                # Exercise-specific logic
                if selected_exercise == "squat":
                    left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)
                    right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
                    if left_knee_angle > 160 and right_knee_angle > 160:
                        stage = "up"
                    if left_knee_angle < 70 and right_knee_angle < 70 and stage == 'up':
                        stage = "down"
                        counter += 1
                        print(f"Squat Reps: {counter}")

                elif selected_exercise == "lateral_raise":
                    left_arm_raised = abs(left_wrist[1] - left_shoulder[1]) > 0.15
                    right_arm_raised = abs(right_wrist[1] - right_shoulder[1]) > 0.15
                    if left_arm_raised and right_arm_raised:
                        stage = "up"
                    if not left_arm_raised and not right_arm_raised and stage == 'up':
                        stage = "down"
                        counter += 1
                        print(f"Lateral Raise Reps: {counter}")

                elif selected_exercise == "overhead_press":
                    left_elbow_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
                    right_elbow_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
                    if left_elbow_angle > 160 and right_elbow_angle > 160:
                        stage = "up"
                    if left_elbow_angle < 90 and right_elbow_angle < 90 and stage == "up":
                        stage = "down"
                        counter += 1
                        print(f"Overhead Press Reps: {counter}")

                elif selected_exercise == "tricep_extension":
                    left_elbow_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
                    right_elbow_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
                    if left_elbow_angle < 50 and right_elbow_angle < 50:
                        stage = "down"
                    if left_elbow_angle > 160 and right_elbow_angle > 160 and stage == "down":
                        stage = "up"
                        counter += 1
                        print(f"Tricep Extension Reps: {counter}")

                elif selected_exercise == "crunch":
                    left_shoulder_hip_dist = abs(left_shoulder[1] - left_hip[1])
                    right_shoulder_hip_dist = abs(right_shoulder[1] - right_hip[1])
                    if left_shoulder_hip_dist < 0.1 and right_shoulder_hip_dist < 0.1:
                        stage = "down"
                    if left_shoulder_hip_dist > 0.3 and right_shoulder_hip_dist > 0.3 and stage == "down":
                        stage = "up"
                        counter += 1
                        print(f"Crunch Reps: {counter}")

                elif selected_exercise == "pushup":
                    left_elbow_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
                    right_elbow_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
                    if left_elbow_angle > 160 and right_elbow_angle > 160:
                        stage = "up"
                    if left_elbow_angle < 90 and right_elbow_angle < 90 and stage == "up":
                        stage = "down"
                        counter += 1
                        print(f"Pushup Reps: {counter}")

                elif selected_exercise == "pullup":
                    left_wrist_shoulder_dist = abs(left_wrist[1] - left_shoulder[1])
                    right_wrist_shoulder_dist = abs(right_wrist[1] - right_shoulder[1])
                    if left_wrist_shoulder_dist < 0.05 and right_wrist_shoulder_dist < 0.05:
                        stage = "up"
                    if left_wrist_shoulder_dist > 0.2 and right_wrist_shoulder_dist > 0.2 and stage == "up":
                        stage = "down"
                        counter += 1
                        print(f"Pullup Reps: {counter}")

                elif selected_exercise == "jumping_jack":
                    if abs(left_shoulder[0] - left_ankle[0]) > 0.2 and abs(right_shoulder[0] - right_ankle[0]) > 0.2:
                        stage = "out"
                    if abs(left_shoulder[0] - left_ankle[0]) < 0.1 and abs(right_shoulder[0] - right_ankle[0]) < 0.1 and stage == "out":
                        stage = "in"
                        counter += 1
                        print(f"Jumping Jack Reps: {counter}")

                elif selected_exercise == "deadlift":
                    left_hip_angle = calculate_angle(left_knee, left_hip, left_shoulder)
                    right_hip_angle = calculate_angle(right_knee, right_hip, right_shoulder)
                    if left_hip_angle > 160 and right_hip_angle > 160:
                        stage = "up"
                    if left_hip_angle < 90 and right_hip_angle < 90 and stage == "up":
                        stage = "down"
                        counter += 1
                        print(f"Deadlift Reps: {counter}")

                elif selected_exercise == "dumbbell_row":
                    left_elbow_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
                    right_elbow_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
                    if left_elbow_angle > 150 and right_elbow_angle > 150:
                        stage = "down"
                    if left_elbow_angle < 90 and right_elbow_angle < 90 and stage == "down":
                        stage = "up"
                        counter += 1
                        print(f"Dumbbell Row Reps: {counter}")
                if counter >= target_reps:
                    print(f"Completed {target_reps} reps! Moving to the next exercise.")
                    exercise_index += 1  # Move to next exercise
                    break  # Exit the loop to handle next exercise
            # except Exception as e:
            #     print(e)
            except:
                pass

            # Display count and exercise name on video feed
            cv2.rectangle(image, (0, 0), (250, 80), (245, 117, 16), -1)
            cv2.putText(image, f'{selected_exercise.replace("_", " ").title()} Reps: {counter}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

            cv2.imshow('Exercise Counter', image)

            if cv2.waitKey(10) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        # Release the video capture and close all windows


        # Display the total reps completed in the console
        print(f"Total {selected_exercise.replace('_', ' ').title()} Reps Completed: {counter}")




def raise_workout_frame():
    data = get_workout_data(os.path.join(path, workout_option_menu.get() + ".json"))
    if str(data) != "{}":
        progressbar.set(0)
        current_workout_step_label.configure(text="Press START to begin")
        info_label.configure(text="")
        # next_step_button.configure(text="START")
        next_step_button.configure(text="START", command=function_call())

        workout_frame.pack(anchor="w", fill="both", expand=True)
        main_frame.pack_forget()
        create_exercises_lists()
    else:
        messagebox.showerror("FlexiFit", "The selected workout doesn't contain any data.\nSelect another workout or edit the current one.")


def quit_me():
    print('quit')
    app.quit()
    app.destroy()


def main():
    #check_for_updates(False)
    view_workout()
    view_pr()
    #get_user_info()
    #display_user_info()
    app.mainloop()


check_files()


# App settings + layout
app = ctk.CTk()

width = 1280
height = 720

width_screen = app.winfo_screenwidth()
height_screen = app.winfo_screenheight()

spawn_x = int((width_screen / 2) - (width / 2))
spawn_y = int((height_screen / 2) - (height / 2))

app.geometry(f"{width}x{height}+{spawn_x}+{spawn_y}")
app.title("FlexiFit")

with open(os.path.join(main_path, "settings.json")) as settings_file:
    settings_data = json.load(settings_file)

print(f'setting theme to {str(settings_data["theme"]).lower()}')
ctk.set_appearance_mode(str(settings_data["theme"]).lower())

app.configure(bg=("#f2f2f2", "#202020"))
app.resizable(False, False)

app.protocol("WM_DELETE_WINDOW", quit_me)

img = PhotoImage(file='media/icon.ico')
app.tk.call('wm', 'iconphoto', app._w, img)

# Initialize fonts
FlexiFit_label_font = ctk.CTkFont(family="Segoe UI", size=40)
current_workout_step_label_font = ctk.CTkFont(family="Segoe UI", size=100)
info_label_font = ctk.CTkFont(family="Segoe UI", size=50)
return_button_font = ctk.CTkFont(family="Segoe UI", size=18)

# Initialize icons
settings_icon = ctk.CTkImage(light_image=Image.open("media/icons/settings_black.png"),
                             dark_image=Image.open("media/icons/settings_white.png"),
                             size=(19, 19))

dumbbell_icon = ctk.CTkImage(light_image=Image.open("media/icons/dumbbell_black.png"),
                             dark_image=Image.open("media/icons/dumbbell_white.png"),
                             size=(19, 19))

edit_icon = ctk.CTkImage(light_image=Image.open("media/icons/edit_black.png"),
                         dark_image=Image.open("media/icons/edit_white.png"),
                         size=(19, 19))

export_icon = ctk.CTkImage(light_image=Image.open("media/icons/export_black.png"),
                           dark_image=Image.open("media/icons/export_white.png"),
                           size=(19, 19))

import_icon = ctk.CTkImage(light_image=Image.open("media/icons/import_black.png"),
                           dark_image=Image.open("media/icons/import_white.png"),
                           size=(19, 19))

delete_icon = ctk.CTkImage(light_image=Image.open("media/icons/delete_black.png"),
                           dark_image=Image.open("media/icons/delete_white.png"),
                           size=(19, 19))

update_icon = ctk.CTkImage(light_image=Image.open("media/icons/update_black.png"),
                           dark_image=Image.open("media/icons/update_white.png"),
                           size=(19, 19))

reset_icon = ctk.CTkImage(light_image=Image.open("media/icons/reset_black.png"),
                          dark_image=Image.open("media/icons/reset_white.png"),
                          size=(19, 19))

add_icon = ctk.CTkImage(light_image=Image.open("media/icons/add_black.png"),
                        dark_image=Image.open("media/icons/add_white.png"),
                        size=(19, 19))

back_icon = ctk.CTkImage(light_image=Image.open("media/icons/back_black.png"),
                         dark_image=Image.open("media/icons/back_white.png"),
                         size=(19, 19))

# mainFrame view
main_frame = ctk.CTkFrame(app, fg_color=("#f2f2f2", "#202020"))
main_frame.pack(anchor="w", fill="both", expand=True)

# Tabview

tabview = ctk.CTkTabview(master=main_frame, fg_color=("#e2e2e2", "#333333"), segmented_button_selected_color="#3C99DC", text_color=("black", "white"),
                         corner_radius=10, width=600)
tabview.pack(anchor="w", fill="y", expand=True, side="left", padx=20, pady=(2, 20))

tabview.add("Home")
tabview.add("Personal records")
tabview.add("Records history")
tabview.add("Period Tracker")
tabview.add("Water Tracker")
tabview.add("Food Recommender")
tabview.add("Settings")
tabview.set("Home")

viewer_frame = ctk.CTkFrame(master=main_frame, fg_color=("#e2e2e2", "#333333"), corner_radius=10, width=600)
viewer_frame.pack(anchor="w", fill="y", expand=True, side="right", padx=20, pady=20)

FlexiFit_label = ctk.CTkLabel(master=tabview.tab("Home"), text=f"FlexiFit", font=FlexiFit_label_font)
FlexiFit_label.place(relx=0.5, rely=0.04, anchor=ctk.CENTER)

select_workout_label = ctk.CTkLabel(master=tabview.tab("Home"), text_color=("black", "white"), text="Select workout: ")
select_workout_label.place(relx=0.03, rely=0.095, anchor=ctk.W)

workout_option_menu = ctk.CTkOptionMenu(master=tabview.tab("Home"), fg_color="#3C99DC", text_color=("black", "white"), dynamic_resizing=False,
                                        values=get_stored_workouts(),
                                        command=workout_option_menu_selection)
workout_option_menu.place(relx=0.03, rely=0.145, anchor=ctk.W)

create_new_workout_button = ctk.CTkButton(master=tabview.tab("Home"), fg_color="#3C99DC", image=add_icon, compound="left", text_color=("black", "white"),
                                          text="Create new workout",
                                          command=create_new_workout_file)
create_new_workout_button.place(relx=0.425, rely=0.145, anchor=ctk.CENTER)

remove_workout_button = ctk.CTkButton(master=tabview.tab("Home"), width=80, fg_color="#3C99DC", image=delete_icon, compound="left",
                                      text_color=("black", "white"),
                                      text="Remove",
                                      command=remove_workout)
remove_workout_button.place(relx=0.66, rely=0.145, anchor=ctk.CENTER)

# Add new step to workout
add_new_step_label = ctk.CTkLabel(master=tabview.tab("Home"), text="Add new step to workout: ")
add_new_step_label.place(relx=0.03, rely=0.22, anchor=ctk.W)
name_exercise_entry = ctk.CTkEntry(master=tabview.tab("Home"), border_color=("#b2b2b2", "#535353"), placeholder_text_color=("#858585", "#afafaf"),
                                   text_color=("black", "white"), fg_color=("white", "#414141"), width=292, placeholder_text="Exercise name")
name_exercise_entry.place(relx=0.03, rely=0.27, anchor=ctk.W)
reps_entry = ctk.CTkEntry(master=tabview.tab("Home"), border_color=("#b2b2b2", "#535353"), placeholder_text_color=("#858585", "#afafaf"),
                          text_color=("black", "white"), fg_color=("white", "#414141"), width=292, placeholder_text="Amount of reps")
reps_entry.place(relx=0.03, rely=0.32, anchor=ctk.W)
sets_entry = ctk.CTkEntry(master=tabview.tab("Home"), border_color=("#b2b2b2", "#535353"), placeholder_text_color=("#858585", "#afafaf"),
                          text_color=("black", "white"),
                          fg_color=("white", "#414141"), width=292, placeholder_text="Amount of sets")
sets_entry.place(relx=0.03, rely=0.37, anchor=ctk.W)
weight_entry = ctk.CTkEntry(master=tabview.tab("Home"), border_color=("#b2b2b2", "#535353"), placeholder_text_color=("#858585", "#afafaf"),
                            text_color=("black", "white"),
                            fg_color=("white", "#414141"), width=292, placeholder_text="Weight (leave blank for no weight)")
weight_entry.place(relx=0.03, rely=0.42, anchor=ctk.W)

add_step_button = ctk.CTkButton(master=tabview.tab("Home"), width=292, fg_color="#3C99DC", image=add_icon, compound="left", text_color=("black", "white"),
                                text="Add step",
                                command=add_workout_step)
add_step_button.place(relx=0.03, rely=0.47, anchor=ctk.W)

# Edit or remove workout step
edit_remove_step_label = ctk.CTkLabel(master=tabview.tab("Home"), text="Edit or remove step: ")
edit_remove_step_label.place(relx=0.03, rely=0.545, anchor=ctk.W)

select_workout_step_menu = ctk.CTkOptionMenu(master=tabview.tab("Home"), width=292, fg_color="#3C99DC", text_color=("black", "white"), dynamic_resizing=False,
                                             values=get_workout_steps_names(),
                                             command=stored_workout_menu_selection)
select_workout_step_menu.place(relx=0.03, rely=0.595, anchor=ctk.W)

edit_name_exercise_entry = ctk.CTkEntry(master=tabview.tab("Home"), border_color=("#b2b2b2", "#535353"), placeholder_text_color=("#858585", "#afafaf"),
                                        text_color=("black", "white"),
                                        fg_color=("white", "#414141"), width=292, placeholder_text="Exercise name")
edit_name_exercise_entry.place(relx=0.03, rely=0.645, anchor=ctk.W)
edit_reps_entry = ctk.CTkEntry(master=tabview.tab("Home"), border_color=("#b2b2b2", "#535353"), placeholder_text_color=("#858585", "#afafaf"),
                               text_color=("black", "white"),
                               fg_color=("white", "#414141"), width=292,
                               placeholder_text="Amount of reps")
edit_reps_entry.place(relx=0.03, rely=0.695, anchor=ctk.W)
edit_sets_entry = ctk.CTkEntry(master=tabview.tab("Home"), border_color=("#b2b2b2", "#535353"), placeholder_text_color=("#858585", "#afafaf"),
                               text_color=("black", "white"),
                               fg_color=("white", "#414141"), width=292,
                               placeholder_text="Amount of sets")
edit_sets_entry.place(relx=0.03, rely=0.745, anchor=ctk.W)
edit_weight_entry = ctk.CTkEntry(master=tabview.tab("Home"), border_color=("#b2b2b2", "#535353"), placeholder_text_color=("#858585", "#afafaf"),
                                 text_color=("black", "white"),
                                 fg_color=("white", "#414141"),
                                 width=292, placeholder_text="Weight (no weight for selected step)")
edit_weight_entry.place(relx=0.03, rely=0.795, anchor=ctk.W)

edit_step_button = ctk.CTkButton(master=tabview.tab("Home"), fg_color="#3C99DC", image=edit_icon, compound="left", text_color=("black", "white"),
                                 text="Edit step",
                                 command=edit_workout_step)
edit_step_button.place(relx=0.03, rely=0.845, anchor=ctk.W)

remove_step_button = ctk.CTkButton(master=tabview.tab("Home"), fg_color="#3C99DC", image=delete_icon, compound="left", text_color=("black", "white"),
                                   text="Remove step",
                                   command=remove_workout_step)
remove_step_button.place(relx=0.29, rely=0.845, anchor=ctk.W)

start_workout_button = ctk.CTkButton(master=tabview.tab("Home"), fg_color="#3C99DC", image=dumbbell_icon, compound="left", text_color=("black", "white"),
                                     text="Start workout",command=lambda: [create_exercises_lists(),next_step()])
                                     #command=raise_workout_frame)
start_workout_button.place(relx=0.5, rely=0.935, anchor=ctk.CENTER)

workout_label = ctk.CTkLabel(master=viewer_frame, text="Exercise")
workout_label.place(relx=0.20, rely=0.0325, anchor=ctk.CENTER)

reps_label = ctk.CTkLabel(master=viewer_frame, text="Reps")
reps_label.place(relx=0.45, rely=0.0325, anchor=ctk.CENTER)

sets_label = ctk.CTkLabel(master=viewer_frame, text="Sets")
sets_label.place(relx=0.65, rely=0.0325, anchor=ctk.CENTER)

weight_label = ctk.CTkLabel(master=viewer_frame, text="Weight (kg)")
weight_label.place(relx=0.85, rely=0.0325, anchor=ctk.CENTER)

exercise_text = ctk.CTkLabel(master=viewer_frame, width=150, height=200, text="", bg_color=("#e2e2e2", "#333333"), justify="left", anchor="nw")
exercise_text.place(relx=0.25, rely=0.075, anchor=ctk.N)

reps_text = ctk.CTkLabel(master=viewer_frame, width=80, text="", bg_color=("#e2e2e2", "#333333"), justify="center")
reps_text.place(relx=0.45, rely=0.075, anchor=ctk.N)

sets_text = ctk.CTkLabel(master=viewer_frame, text="", bg_color=("#e2e2e2", "#333333"), justify="center")
sets_text.place(relx=0.65, rely=0.075, anchor=ctk.N)

weight_text = ctk.CTkLabel(master=viewer_frame, text="", bg_color=("#e2e2e2", "#333333"), justify="center")
weight_text.place(relx=0.85, rely=0.075, anchor=ctk.N)

# workoutFrame view
workout_frame = ctk.CTkFrame(app, fg_color=("#f2f2f2", "#202020"))

progressbar = ctk.CTkProgressBar(master=workout_frame, fg_color=("#e2e2e2", "#333333"), progress_color="#3C99DC", height=15, width=app.winfo_width())
progressbar.place(relx=0.5, rely=0, anchor=ctk.N)

current_workout_step_label = ctk.CTkLabel(workout_frame, text="Press START to begin", font=current_workout_step_label_font)
current_workout_step_label.place(relx=0.50, rely=0.3, anchor=ctk.CENTER)
info_label = ctk.CTkLabel(workout_frame, text="", font=info_label_font)
info_label.place(relx=0.50, rely=0.5, anchor=ctk.CENTER)

next_step_button = ctk.CTkButton(master=workout_frame, fg_color="#3C99DC", width=300, height=125, text_color=("black", "white"), text="START",
                                 font=info_label_font, command=next_step)
next_step_button.place(relx=0.5, rely=0.85, anchor=ctk.CENTER)

return_button = ctk.CTkButton(master=workout_frame, fg_color="#3C99DC", width=50, height=25, text_color=("black", "white"), text="Return",
                              font=return_button_font,
                              command=raise_main_frame)
return_button.place(relx=0.0375, rely=0.055, anchor=ctk.CENTER)

# SettingsFrame view
# SettingsFrame view
settings_frame = ctk.CTkFrame(master=main_frame, fg_color=("#e2e2e2", "#333333"), corner_radius=10)

settings_label = ctk.CTkLabel(master=tabview.tab("Settings"), text=f"Settings", font=FlexiFit_label_font)
settings_label.place(relx=0.5, rely=0.04, anchor=ctk.CENTER)

theme_selection_default = str(settings_data["theme"])

select_theme_label = ctk.CTkLabel(master=tabview.tab("Settings"), text_color=("black", "white"), text="Choose theme: ")
select_theme_label.place(relx=0.03, rely=0.095, anchor=ctk.W)

theme_selection = ctk.CTkOptionMenu(master=tabview.tab("Settings"), fg_color="#3C99DC", text_color=("black", "white"), dynamic_resizing=False,
                                    values=["Light", "Dark", "System"],
                                    command=theme_option_selection)
theme_selection.place(relx=0.03, rely=0.145, anchor=ctk.W)
theme_selection.set(theme_selection_default)

reset_app_label = ctk.CTkLabel(master=tabview.tab("Settings"), text_color=("black", "white"), text="Reset to factory settings:")
reset_app_label.place(relx=0.03, rely=0.22, anchor=ctk.W)

reset_app_button = ctk.CTkButton(master=tabview.tab("Settings"), fg_color="#3C99DC", image=reset_icon, compound="left", text_color=("black", "white"),
                                 text="Reset app",
                                 command=reset)
reset_app_button.place(relx=0.03, rely=0.27, anchor=ctk.W)

import_export_label = ctk.CTkLabel(master=tabview.tab("Settings"), text_color=("black", "white"), text="Import or export workouts:")
import_export_label.place(relx=0.03, rely=0.32, anchor=ctk.W)

import_exercises_button = ctk.CTkButton(master=tabview.tab("Settings"), fg_color="#3C99DC", image=import_icon, compound="left", text_color=("black", "white"),
                                        text="Import workouts",
                                        command=import_workouts)
import_exercises_button.place(relx=0.03, rely=0.37, anchor=ctk.W)

export_exercises_button = ctk.CTkButton(master=tabview.tab("Settings"), fg_color="#3C99DC", image=export_icon, compound="left", text_color=("black", "white"),
                                        text="Export workouts",
                                        command=export_workouts)
export_exercises_button.place(relx=0.415, rely=0.37, anchor=ctk.CENTER)

about_label = ctk.CTkLabel(master=tabview.tab("Settings"), text=f"FlexiFit v{version}")
about_label.place(relx=0.5, rely=0.87, anchor=ctk.CENTER)

# #userinfo

# # Create labels and entries for user info
# user_info_label = ctk.CTkLabel(master=tabview.tab("Settings"), text="User  Information")
# user_info_label.place(relx=0.5, rely=0.05, anchor=ctk.CENTER)

# gender_label = ctk.CTkLabel(master=tabview.tab("Settings"), text="Gender:")
# gender_label.place(relx=0.03, rely=0.1, anchor=ctk.W)
# gender_entry = ctk.CTkEntry(master=tabview.tab("Settings"), placeholder_text="Enter your gender")
# gender_entry.place(relx=0.2, rely=0.1, anchor=ctk.W)

# age_label = ctk.CTkLabel(master=tabview.tab("Settings"), text="Age:")
# age_label.place(relx=0.03, rely=0.15, anchor=ctk.W)
# age_entry = ctk.CTkEntry(master=tabview.tab("Settings"), placeholder_text="Enter your age")
# age_entry.place(relx=0.2, rely=0.15, anchor=ctk.W)

# weight_label = ctk.CTkLabel(master=tabview.tab("Settings"), text="Weight (kg):")
# weight_label.place(relx=0.03, rely=0.2, anchor=ctk.W)
# weight_entry = ctk.CTkEntry(master=tabview.tab("Settings"), placeholder_text="Enter your weight")
# weight_entry.place(relx=0.2, rely=0.2, anchor=ctk.W)

# height_label = ctk.CTkLabel(master=tabview.tab("Settings"), text="Height (cm):")
# height_label.place(relx=0.03, rely=0.25, anchor=ctk.W)
# height_entry = ctk.CTkEntry(master=tabview.tab("Settings"), placeholder_text="Enter your height")
# height_entry.place(relx=0.2, rely=0.25, anchor=ctk.W)

# user_info_label = ctk.CTkLabel(master=tabview.tab("Settings"), text="", justify="left")
# user_info_label.pack(pady=10)

# update_user_info_button = ctk.CTkButton(master=tabview.tab("Settings"), text="Update User Info", command=update_user_info_dialog)
# update_user_info_button.pack(pady=10)

# # Update button
# update_user_info_button = ctk.CTkButton(master=tabview.tab("Settings"), text="Update User Info", command=update_user_info_dialog)
# update_user_info_button.place(relx=0.5, rely=0.35, anchor=ctk.CENTER)


# Personal records view
personal_records_label = ctk.CTkLabel(master=tabview.tab("Personal records"), text=f"Personal records", font=FlexiFit_label_font)
personal_records_label.place(relx=0.5, rely=0.04, anchor=ctk.CENTER)

pr_exercise_label = ctk.CTkLabel(master=tabview.tab("Personal records"), text="Exercise")
pr_exercise_label.place(relx=0.1, rely=0.125, anchor=ctk.W)

pr_weight_label = ctk.CTkLabel(master=tabview.tab("Personal records"), text="Weight (kg)")
pr_weight_label.place(relx=0.5, rely=0.125, anchor=ctk.CENTER)

pr_date_label = ctk.CTkLabel(master=tabview.tab("Personal records"), text="Date")
pr_date_label.place(relx=0.8, rely=0.125, anchor=ctk.CENTER)

pr_exercise_text = ctk.CTkLabel(master=tabview.tab("Personal records"), width=225, height=200, text="", bg_color=("#e2e2e2", "#333333"), justify="left",
                                anchor="nw")
pr_exercise_text.place(relx=0.225, rely=0.175, anchor=ctk.N)

pr_weight_text = ctk.CTkLabel(master=tabview.tab("Personal records"), width=80, text="", bg_color=("#e2e2e2", "#333333"), justify="center")
pr_weight_text.place(relx=0.50, rely=0.175, anchor=ctk.N)

pr_date_text = ctk.CTkLabel(master=tabview.tab("Personal records"), width=80, text="", bg_color=("#e2e2e2", "#333333"), justify="center")
pr_date_text.place(relx=0.8, rely=0.175, anchor=ctk.N)

# Add new record
pr_add_label = ctk.CTkLabel(master=tabview.tab("Personal records"), text_color=("black", "white"), text="Add new record:")
pr_add_label.place(relx=0.03, rely=0.600, anchor=ctk.W)

pr_add_name_entry = ctk.CTkEntry(master=tabview.tab("Personal records"), border_color=("#b2b2b2", "#535353"), placeholder_text_color=("#858585", "#afafaf"),
                                 text_color=("black", "white"),
                                 fg_color=("white", "#414141"), width=292, placeholder_text="Record name")
pr_add_name_entry.place(relx=0.03, rely=0.650, anchor=ctk.W)
pr_add_weight_entry = ctk.CTkEntry(master=tabview.tab("Personal records"), border_color=("#b2b2b2", "#535353"), placeholder_text_color=("#858585", "#afafaf"),
                                   text_color=("black", "white"),
                                   fg_color=("white", "#414141"), width=292,
                                   placeholder_text="Record weight")
pr_add_weight_entry.place(relx=0.03, rely=0.700, anchor=ctk.W)

pr_add_record_button = ctk.CTkButton(master=tabview.tab("Personal records"), fg_color="#3C99DC", width=292, image=add_icon, compound="left",
                                     text_color=("black", "white"), text="Add record",
                                     command=add_pr)
pr_add_record_button.place(relx=0.03, rely=0.750, anchor=ctk.W)

# Edit or remove record
pr_edit_label = ctk.CTkLabel(master=tabview.tab("Personal records"), text_color=("black", "white"), text="Update or remove record:")
pr_edit_label.place(relx=0.03, rely=0.825, anchor=ctk.W)

select_pr_menu = ctk.CTkOptionMenu(master=tabview.tab("Personal records"), width=292, fg_color="#3C99DC", text_color=("black", "white"), dynamic_resizing=False,
                                   values=get_pr_names(),
                                   command=pr_menu_selection)
select_pr_menu.place(relx=0.03, rely=0.875, anchor=ctk.W)

pr_edit_record_button = ctk.CTkButton(master=tabview.tab("Personal records"), fg_color="#3C99DC", image=edit_icon, compound="left",
                                      text_color=("black", "white"), text="Update record",
                                      command=edit_pr)
pr_edit_record_button.place(relx=0.03, rely=0.925, anchor=ctk.W)

pr_remove_record_button = ctk.CTkButton(master=tabview.tab("Personal records"), fg_color="#3C99DC", image=delete_icon, compound="left",
                                        text_color=("black", "white"),
                                        text="Remove record",
                                        command=remove_pr)
pr_remove_record_button.place(relx=0.29, rely=0.925, anchor=ctk.W)

# Records history view
history_label = ctk.CTkLabel(master=tabview.tab("Records history"), text=f"Records history", font=FlexiFit_label_font)
history_label.place(relx=0.5, rely=0.04, anchor=ctk.CENTER)

select_graph_menu = ctk.CTkOptionMenu(master=tabview.tab("Records history"), width=200, fg_color="#3C99DC", text_color=("black", "white"),
                                      dynamic_resizing=False,
                                      values=get_pr_names(), command=print("generate graph"))
select_graph_menu.place(relx=0.03, rely=0.125, anchor=ctk.W)

generate_graph_button = ctk.CTkButton(master=tabview.tab("Records history"), fg_color="#3C99DC", image=update_icon, compound="left",
                                      text_color=("black", "white"), text="Generate graph", command=generate_graph)
generate_graph_button.place(relx=0.39, rely=0.125, anchor=ctk.W)

graph_frame = ctk.CTkFrame(master=tabview.tab("Records history"), fg_color=("#e2e2e2", "#333333"), height=525, width=300)
graph_frame.place(relx=0.5, rely=0.975, anchor=ctk.S)
# generate_graph

#Period Tracker
# Period Tracker view
period_tracker_label = ctk.CTkLabel(master=tabview.tab("Period Tracker"), text="Period Tracker", font=FlexiFit_label_font)
period_tracker_label.place(relx=0.5, rely=0.04, anchor=ctk.CENTER)

# Cycle Day Input
cycle_day_label = ctk.CTkLabel(master=tabview.tab("Period Tracker"), text="Current Cycle Day:")
cycle_day_label.place(relx=0.03, rely=0.1, anchor=ctk.W)
cycle_day_entry = ctk.CTkEntry(master=tabview.tab("Period Tracker"), placeholder_text="Enter cycle day ")
cycle_day_entry.place(relx=0.3, rely=0.1, anchor=ctk.W)

# Cycle Length Input
cycle_length_label = ctk.CTkLabel(master=tabview.tab("Period Tracker"), text="Cycle Length:")
cycle_length_label.place(relx=0.03, rely=0.15, anchor=ctk.W)
cycle_length_entry = ctk.CTkEntry(master=tabview.tab("Period Tracker"), placeholder_text="Enter cycle length")
cycle_length_entry.place(relx=0.3, rely=0.15, anchor=ctk.W)

# Button to get recommended workout plan
get_workout_button = ctk.CTkButton(master=tabview.tab("Period Tracker"), text="Get Recommended Workout", command=lambda: get_recommended_workout())
get_workout_button.place(relx=0.03, rely=0.24, anchor=ctk.W)

# Label to display results
results_label = ctk.CTkLabel(master=tabview.tab("Period Tracker"), text="", wraplength=400)
results_label.place(relx=0.03, rely=0.46, anchor=ctk.W)  # Adjusted position for better visibility

# Add some vertical space before the muscle group input
muscle_group_label = ctk.CTkLabel(master=tabview.tab("Period Tracker"), text="Muscle Group Choice:")
muscle_group_label.place(relx=0.03, rely=0.65, anchor=ctk.W)  # Adjusted position for better visibility
muscle_group_entry = ctk.CTkEntry(master=tabview.tab("Period Tracker"), placeholder_text="Enter muscle group")
muscle_group_entry.place(relx=0.3, rely=0.65, anchor=ctk.W)  # Adjusted position for better visibility

# Button to confirm muscle group selection
confirm_muscle_group_button = ctk.CTkButton(master=tabview.tab("Period Tracker"), text="Confirm Muscle Group", command=handle_muscle_group_selection)
confirm_muscle_group_button.place(relx=0.03, rely=0.75, anchor=ctk.W)  # Adjusted position for better visibility

# Reset Button
reset_button = ctk.CTkButton(master=tabview.tab("Period Tracker"), text="Reset", command=lambda: reset_fields())
reset_button.place(relx=0.3, rely=0.8, anchor=ctk.W)

#water tracker

water_tracker_tab = tabview.tab("Water Tracker")

# Water Tracker view
water_tracker_label = ctk.CTkLabel(master=tabview.tab("Water Tracker"), text="Water Tracker", font=FlexiFit_label_font)
water_tracker_label.place(relx=0.5, rely=0.04, anchor=ctk.CENTER)

# Gender Input
gender_label = ctk.CTkLabel(master=water_tracker_tab, text="Enter your gender (male/female):")
gender_label.place(relx=0.03, rely=0.125, anchor=ctk.W)
gender_entry = ctk.CTkEntry(master=water_tracker_tab, placeholder_text="Gender")
gender_entry.place(relx=0.35, rely=0.125, anchor=ctk.W)

# Activity Level Input
activity_label = ctk.CTkLabel(master=water_tracker_tab, text="Are you working out today? (yes/no):")
activity_label.place(relx=0.03, rely=0.165, anchor=ctk.W)
activity_entry = ctk.CTkEntry(master=water_tracker_tab, placeholder_text="yes/no")
activity_entry.place(relx=0.35, rely=0.165, anchor=ctk.W)

# Button to start tracking
start_button = ctk.CTkButton(master=water_tracker_tab, text="Start Tracking", command=lambda: start_tracking())
start_button.place(relx=0.03, rely=0.24, anchor=ctk.W)

# Status Label
status_label = ctk.CTkLabel(master=water_tracker_tab, text="")
status_label.place(relx=0.03, rely=0.34, anchor=ctk.W)

# Drink Glass Button
drink_button = ctk.CTkButton(master=water_tracker_tab, text="Drink a Glass", command=lambda: drink_glass())
drink_button.place(relx=0.03, rely=0.4, anchor=ctk.W)

# Display Status Button
display_status_button = ctk.CTkButton(master=water_tracker_tab, text="Check Status", command=lambda: check_status())
display_status_button.place(relx=0.24, rely=0.4, anchor=ctk.W)

# Reset Button
reset_button = ctk.CTkButton(master=water_tracker_tab, text="Reset", command=lambda: reset_tracker())
reset_button.place(relx=0.03, rely=0.5, anchor=ctk.W)

# Initialize WaterTracker instance
tracker = None


#Food Recommender

# Food Recommender Tab
food_tracker_tab = tabview.tab("Food Recommender")


# Water Tracker view
food_tracker_label = ctk.CTkLabel(master=tabview.tab("Food Recommender"), text="Food Recommender", font=FlexiFit_label_font)
food_tracker_label.place(relx=0.5, rely=0.04, anchor=ctk.CENTER)

# Input Fields
weight_label = ctk.CTkLabel(master=food_tracker_tab, text="Enter your current weight (kg):")
weight_label.place(relx=0.03, rely=0.1, anchor=ctk.W)
weight_entry = ctk.CTkEntry(master=food_tracker_tab, placeholder_text="Weight (kg)")
weight_entry.place(relx=0.35, rely=0.1, anchor=ctk.W)

height_label = ctk.CTkLabel(master=food_tracker_tab, text="Enter your height (cm):")
height_label.place(relx=0.03, rely=0.15, anchor=ctk.W)
height_entry = ctk.CTkEntry(master=food_tracker_tab, placeholder_text="Height (cm)")
height_entry.place(relx=0.35, rely=0.15, anchor=ctk.W)

age_label = ctk.CTkLabel(master=food_tracker_tab, text="Enter your age:")
age_label.place(relx=0.03, rely=0.2, anchor=ctk.W)
age_entry = ctk.CTkEntry(master=food_tracker_tab, placeholder_text="Age")
age_entry.place(relx=0.35, rely=0.2, anchor=ctk.W)

gender_label = ctk.CTkLabel(master=food_tracker_tab, text="Enter your gender (male/female): ")
gender_label.place(relx=0.03, rely=0.25, anchor=ctk.W)
gender_entry = ctk.CTkEntry(master=food_tracker_tab, placeholder_text="Gender")
gender_entry.place(relx=0.35, rely=0.25, anchor=ctk.W)

activity_label = ctk.CTkLabel(master=food_tracker_tab, text="Select your activity level:")
activity_label.place(relx=0.03, rely=0.3, anchor=ctk.W)
activity_entry = ctk.CTkEntry(master=food_tracker_tab, placeholder_text="Activity Level (sedentary/light/moderate/active/very active)")
activity_entry.place(relx=0.35, rely=0.3, anchor=ctk.W)

target_weight_label = ctk.CTkLabel(master=food_tracker_tab, text="Enter your target weight (kg):")
target_weight_label.place(relx=0.03, rely=0.35, anchor=ctk.W)
target_weight_entry = ctk.CTkEntry(master=food_tracker_tab, placeholder_text="Target Weight (kg)")
target_weight_entry.place(relx=0.35, rely=0.35, anchor=ctk.W)

# Output Labels
output_label = ctk.CTkLabel(master=food_tracker_tab, text="Meal Plan Output:")
output_label.place(relx=0.03, rely=0.45, anchor=ctk.W)

# Labels for meal plan output
breakfast_label = ctk.CTkLabel(master=food_tracker_tab, text="")
breakfast_label.place(relx=0.03, rely=0.55, anchor=ctk.W)

lunch_label = ctk.CTkLabel(master=food_tracker_tab, text="")
lunch_label.place(relx=0.03, rely=0.65, anchor=ctk.W)

dinner_label = ctk.CTkLabel(master=food_tracker_tab, text="")
dinner_label.place(relx=0.03, rely=0.75, anchor=ctk.W)

total_calories_label = ctk.CTkLabel(master=food_tracker_tab, text="")
total_calories_label.place(relx=0.03, rely=0.85, anchor=ctk.W)

# Generate Meal Plan Button

generate_button = ctk.CTkButton(master=food_tracker_tab, text="Generate Meal Plan", command=generate_meal_plan)
generate_button.place(relx=0.03, rely=0.95, anchor=ctk.W)


# # Period Tracker view
# period_tracker_label = ctk.CTkLabel(master=tabview.tab("Period Tracker"), text="Period Tracker", font=FlexiFit_label_font)
# period_tracker_label.place(relx=0.5, rely=0.04, anchor=ctk.CENTER)

# # Cycle Day Input
# cycle_day_label = ctk.CTkLabel(master=tabview.tab("Period Tracker"), text="Current Cycle Day:")
# cycle_day_label.place(relx=0.03, rely=0.1, anchor=ctk.W)
# cycle_day_entry = ctk.CTkEntry(master=tabview.tab("Period Tracker"), placeholder_text="Enter cycle day (1-28)")
# cycle_day_entry.place(relx=0.2, rely=0.1, anchor=ctk.W)

# # Cycle Length Input
# cycle_length_label = ctk.CTkLabel(master=tabview.tab("Period Tracker"), text="Cycle Length:")
# cycle_length_label.place(relx=0.03, rely=0.15, anchor=ctk.W)
# cycle_length_entry = ctk.CTkEntry(master=tabview.tab("Period Tracker"), placeholder_text="Enter cycle length (e.g., 28)")
# cycle_length_entry.place(relx=0.2, rely=0.15, anchor=ctk.W)

# # Button to get recommended workout plan
# get_workout_button = ctk.CTkButton(master=tabview.tab("Period Tracker"), text="Get Recommended Workout", command=lambda: get_recommended_workout())
# get_workout_button.place(relx=0.03, rely=0.2, anchor=ctk.W)

# # Label to display results
# results_label = ctk.CTkLabel(master=tabview.tab("Period Tracker"), text="", wraplength=400)
# results_label.place(relx=0.03, rely=0.3, anchor=ctk.W)


# # Example of running the function in isolation
# if __name__ == "__main__":
#     # Simulate user input
#     weight = 70.0
#     height = 175.0
#     age = 30
#     gender = 'male'
#     activity_level = 'moderate'
#     target_weight = 65.0

#     # Simulate food_data
#     food_data = pd.DataFrame({
#         'Food': ['Food1', 'Food2', 'Food3'],
#         'Calories': [200, 300, 400]
#     })

#     # Call the function directly
#     generate_meal_plan()

# # Water Tracker Class Definition
# class WaterTracker:
#     def __init__(self, gender, activity_level):
#         self.gender = gender
#         self.activity_level = activity_level
#         self.total_water_liters = self.calculate_daily_water_intake()
#         self.glasses_per_liter = 4  # Assuming 1 glass = 250 ml
#         self.total_glasses = int(self.total_water_liters * self.glasses_per_liter)
#         self.remaining_glasses = self.total_glasses

#     def calculate_daily_water_intake(self):
#         # Daily water intake based on gender and activity level
#         if self.gender.lower() == 'male':
#             return 3.7 if self.activity_level else 3.0  # Liters for active/inactive males
#         elif self.gender.lower() == 'female':
#             return 2.7 if self.activity_level else 2.2  # Liters for active/inactive females
#         else:
#             raise ValueError("Invalid gender input. Please enter 'male' or 'female'.")

#     def drink_glass(self):
#         if self.remaining_glasses > 0:
#             self.remaining_glasses -= 1
#             remaining_liters = self.remaining_glasses / self.glasses_per_liter
#             return f"You drank a glass of water. Remaining: {self.remaining_glasses} glasses ({remaining_liters:.2f} liters)."
#         else:
#             return "Target reached! You have met your daily water intake goal."

#     def display_status(self):
#         remaining_liters = self.remaining_glasses / self.glasses_per_liter
#         if self.remaining_glasses > 0:
#             return f"Remaining: {self.remaining_glasses} glasses ({remaining_liters:.2f} liters)."
#         else:
#             return "Congratulations! You have completed your daily water intake."


# def start_tracking():
#     global tracker
#     gender = gender_entry.get().strip()  # Get gender input from the entry
#     activity = activity_entry.get().strip().lower() == 'yes'  # Convert activity input to boolean
    
#     print(f"Gender input: '{gender}'")  # Debugging statement
#     print(f"Activity input: '{activity}'")  # Debugging statement
    
#     try:
#         tracker = WaterTracker(gender, activity)
#         status_label.configure(text=f"Your daily water intake goal is {tracker.total_glasses} glasses ({tracker.total_water_liters:.2f} liters).")
#     except ValueError as e:
#         status_label.configure(text=str(e))
# # def start_tracking():
# #     global tracker
# #     gender = gender_entry.get().strip()
# #     activity = activity_entry.get().strip().lower() == 'yes'
    
# #     try:
# #         tracker = WaterTracker(gender, activity)
# #         status_label.configure(text=f"Your daily water intake goal is {tracker .total_glasses} glasses ({tracker.total_water_liters:.2f} liters).")
# #     except ValueError as e:
# #         status_label.configure(text=str(e))

# def drink_glass():
#     if tracker:
#         message = tracker.drink_glass()
#         status_label.configure(text=message)
#     else:
#         status_label.configure(text="Please start tracking first.")

# def check_status():
#     if tracker:
#         message = tracker.display_status()
#         status_label.configure(text=message)
#     else:
#         status_label.configure(text="Please start tracking first.")

# def reset_tracker():
#     global tracker
#     tracker = None
#     gender_entry.delete(0, 'end')
#     activity_entry.delete(0, 'end')
#     status_label.configure(text="")


# Water Tracker Class Definition
class WaterTracker:
    def __init__(self, gender, activity_level):
        self.gender = gender
        self.activity_level = activity_level
        self.total_water_liters = self.calculate_daily_water_intake()
        self.glasses_per_liter = 4  # Assuming 1 glass = 250 ml
        self.total_glasses = int(self.total_water_liters * self.glasses_per_liter)
        self.remaining_glasses = self.total_glasses

    def calculate_daily_water_intake(self):
        # Daily water intake based on gender and activity level
        if self.gender.lower() == 'male':
            return 3.7 if self.activity_level else 3.0  # Liters for active/inactive males
        elif self.gender.lower() == 'female':
            return 2.7 if self.activity_level else 2.2  # Liters for active/inactive females
        # else:
        #     raise ValueError("Invalid gender input. Please enter 'male' or 'female'.")

    def drink_glass(self):
        if self.remaining_glasses > 0:
            self.remaining_glasses -= 1
            remaining_liters = self.remaining_glasses / self.glasses_per_liter
            return f"You drank a glass of water. Remaining: {self.remaining_glasses} glasses ({remaining_liters:.2f} liters)."
        else:
            return "Target reached! You have met your daily water intake goal."

    def display_status(self):
        remaining_liters = self.remaining_glasses / self.glasses_per_liter
        if self.remaining_glasses > 0:
            return f"Remaining: {self.remaining_glasses} glasses ({remaining_liters:.2f} liters)."
        else:
            return "Congratulations! You have completed your daily water intake."


# GUI Setup
def start_tracking():
    global tracker
    gender = gender_entry.get().strip()  # Get gender input from the entry
    activity = activity_entry.get().strip().lower() == 'yes'  # Convert activity input to boolean
    
    print(f"Gender input: '{gender}'")  # Debugging statement
    print(f"Activity input: '{activity}'")  # Debugging statement
    
    try:
        tracker = WaterTracker(gender, activity)
        status_label.configure(text=f"Your daily water intake goal is {tracker.total_glasses} glasses ({tracker.total_water_liters:.2f} liters).")
    except ValueError as e:
        status_label.configure(text=str(e))

def drink_glass():
    if tracker:
        message = tracker.drink_glass()
        status_label.configure(text=message)
    else:
        status_label.configure(text="Please start tracking first.")

def check_status():
    if tracker:
        message = tracker.display_status()
        status_label.configure(text=message)
    else:
        status_label.configure(text="Please start tracking first.")

def reset_tracker():
    global tracker
    tracker = None
    gender_entry.delete(0, 'end')
    activity_entry.delete(0, 'end')
    status_label.configure(text="")
# Test the WaterTracker class
try:
    # Create an instance for an active male
    tracker = WaterTracker(gender='male', activity_level=True)
    print(tracker.display_status())  # Check initial status

    # Drink some water
    print(tracker.drink_glass())
    print(tracker.display_status())  # Check status after drinking




except ValueError as e:
    print(e)

if __name__ == "__main__":
    main()
