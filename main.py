import cv2
import mediapipe as mp
import numpy as np
import pyttsx3
import threading
import gradio as gr
import time
from datetime import datetime  
import pandas as pd
import base64
import os
from dotenv import load_dotenv
import pyttsx3
import speech_recognition as sr
import openai
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder
)
from pymongo import MongoClient


# Initialize Mediapipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
camera_active = False
cap = None
reps = 0
# Initialize TTS engine once
engine = None

def init_tts():
    global engine
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)

init_tts()

# MongoDB Connection
client = MongoClient("mongodb+srv://shravya7321:lVMFwzt9AcGBwXhg@cluster0.hblvkf7.mongodb.net/", tlsAllowInvalidCertificates=True)
db = client["gym_app"]
user_data_collection = db["user_data"]

# Global variable for storing email
user_email = ""

# def authenticate(email):
#     global user_email
#     if email:
#         user_email = email
#         return gr.update(visible=True), gr.update(visible=False)
#     return gr.update(visible=False), gr.update(visible=True, value="Please enter a valid email.")


def authenticate(email):
    global user_email
    if email:
        user_email = email
        return (
            gr.update(visible=True),   # Show main_ui
            gr.update(visible=False),  # Hide error_message
            gr.update(visible=False)   # Hide login_section
        )
    return (
        gr.update(visible=False),      # Hide main_ui
        gr.update(visible=True, value="Please enter a valid email."),  # Show error
        gr.update(visible=True)        # Keep login_section visible
    )


# Exercise state tracking
exercise_state = None
exercise_reps = 0
feedback_message = ""
feedback_color = (0, 255, 0)
last_rep_time = time.time()
exercise_started = False

water_intake = 0
water_goal = 2000  

def speak_feedback(text):
    global user_email
    def _speak():
        engine.say(text)
        try:
            engine.runAndWait()
        except RuntimeError:
            engine.endLoop()
            init_tts()
            engine.say(text)
            engine.runAndWait()
    
    threading.Thread(target=_speak, daemon=True).start()

def calculate_angle(a, b, c):
    """Calculate the angle between three points."""
    global user_email
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return angle if angle <= 180.0 else 360.0 - angle

def process_exercise_landmarks(landmarks, exercise_type, image):
    global user_email
    global user_email,exercise_reps, exercise_state, feedback_message, feedback_color, last_rep_time, exercise_started
    
    h, w, _ = image.shape
    
    # Get necessary body landmarks
    points = {
        'left_shoulder': [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x * w,
                          landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y * h],
        'right_shoulder': [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x * w,
                           landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y * h],
        'left_elbow': [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x * w,
                       landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y * h],
        'right_elbow': [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x * w,
                        landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y * h],
        'left_wrist': [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x * w,
                       landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y * h],
        'right_wrist': [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x * w,
                        landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y * h],
        'left_hip': [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x * w,
                     landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y * h],
        'right_hip': [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x * w,
                      landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y * h],
        'left_knee': [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x * w,
                      landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y * h],
        'right_knee': [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x * w,
                       landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y * h],
        'left_ankle': [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x * w,
                       landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y * h],
        'right_ankle': [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x * w,
                        landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y * h]
    }
    
    feedback = ""
    color = (0, 255, 0)  # Default: Green for correct posture
    
    if not exercise_started:
        exercise_started = True
        speak_feedback(f"Starting {exercise_map[exercise_type]} tracking")
    
    if exercise_type == 1:  # Squats
        left_knee_angle = calculate_angle(points['left_hip'], points['left_knee'], points['left_ankle'])
        right_knee_angle = calculate_angle(points['right_hip'], points['right_knee'], points['right_ankle'])
        avg_knee_angle = (left_knee_angle + right_knee_angle) / 2
        
        if avg_knee_angle > 160:
            exercise_state = "up"
            feedback = "Go lower!"
            color = (0, 0, 255)
        elif avg_knee_angle < 90:
            feedback = "Good depth!"
            if exercise_state == "up":
                exercise_state = "down"
                exercise_reps += 1
                last_rep_time = time.time()
        else:
            feedback = "Keep your posture!"
            
    elif exercise_type == 2:  # Push-ups
        left_elbow_angle = calculate_angle(points['left_shoulder'], points['left_elbow'], points['left_wrist'])
        right_elbow_angle = calculate_angle(points['right_shoulder'], points['right_elbow'], points['right_wrist'])
        avg_elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
        
        if avg_elbow_angle > 160:
            exercise_state = "up"
            feedback = "Lower your body!"
            color = (0, 0, 255)
        elif avg_elbow_angle < 90:
            feedback = "Good push-up!"
            if exercise_state == "up":
                exercise_state = "down"
                exercise_reps += 1
                last_rep_time = time.time()
        else:
            feedback = "Keep your posture!"
            
    elif exercise_type == 3:  # Shoulder press
        left_shoulder_angle = calculate_angle(points['left_elbow'], points['left_shoulder'], points['left_hip'])
        right_shoulder_angle = calculate_angle(points['right_elbow'], points['right_shoulder'], points['right_hip'])
        avg_shoulder_angle = (left_shoulder_angle + right_shoulder_angle) / 2
        
        if avg_shoulder_angle > 160:
            exercise_state = "down"
            feedback = "Lower the weights!"
            color = (0, 0, 255)
        elif avg_shoulder_angle < 90:
            feedback = "Great press!"
            if exercise_state == "down":
                exercise_state = "up"
                exercise_reps += 1
                last_rep_time = time.time()
        else:
            feedback = "Keep going!"
            
    elif exercise_type == 4:  # Lateral raise
        left_arm_angle = calculate_angle(points['left_shoulder'], points['left_elbow'], points['left_wrist'])
        right_arm_angle = calculate_angle(points['right_shoulder'], points['right_elbow'], points['right_wrist'])
        avg_arm_angle = (left_arm_angle + right_arm_angle) / 2
        
        if avg_arm_angle > 150:
            exercise_state = "down"
            feedback = "Raise your arms!"
            color = (0, 0, 255)
        elif avg_arm_angle < 90:
            feedback = "Good raise!"
            if exercise_state == "down":
                exercise_state = "up"
                exercise_reps += 1
                last_rep_time = time.time()
        else:
            feedback = "Maintain form!"
            
    elif exercise_type == 5:  # Tricep extension
        left_elbow_angle = calculate_angle(points['left_shoulder'], points['left_elbow'], points['left_wrist'])
        right_elbow_angle = calculate_angle(points['right_shoulder'], points['right_elbow'], points['right_wrist'])
        avg_elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
        
        if avg_elbow_angle > 160:
            exercise_state = "down"
            feedback = "Extend fully!"
            color = (0, 0, 255)
        elif avg_elbow_angle < 50:
            feedback = "Good extension!"
            if exercise_state == "down":
                exercise_state = "up"
                exercise_reps += 1
                last_rep_time = time.time()
        else:
            feedback = "Keep your posture!"
            
    elif exercise_type == 6:  # Crunch
        left_torso_angle = calculate_angle(points['left_hip'], points['left_shoulder'], points['left_knee'])
        right_torso_angle = calculate_angle(points['right_hip'], points['right_shoulder'], points['right_knee'])
        avg_torso_angle = (left_torso_angle + right_torso_angle) / 2
        
        if avg_torso_angle > 120:
            exercise_state = "down"
            feedback = "Curl up!"
            color = (0, 0, 255)
        elif avg_torso_angle < 90:
            feedback = "Great crunch!"
            if exercise_state == "down":
                exercise_state = "up"
                exercise_reps += 1
                last_rep_time = time.time()
        else:
            feedback = "Maintain core engagement!"
            
    elif exercise_type == 7:  # Jumping jack
        left_arm_angle = calculate_angle(points['left_shoulder'], points['left_elbow'], points['left_wrist'])
        right_arm_angle = calculate_angle(points['right_shoulder'], points['right_elbow'], points['right_wrist'])
        left_leg_angle = calculate_angle(points['left_hip'], points['left_knee'], points['left_ankle'])
        right_leg_angle = calculate_angle(points['right_hip'], points['right_knee'], points['right_ankle'])
        
        if left_arm_angle > 150 and right_arm_angle > 150 and left_leg_angle > 150 and right_leg_angle > 150:
            exercise_state = "down"
            feedback = "Jump up!"
            color = (0, 0, 255)
        elif left_arm_angle < 90 and right_arm_angle < 90 and left_leg_angle < 90 and right_leg_angle < 90:
            feedback = "Good Jump!"
            if exercise_state == "down":
                exercise_state = "up"
                exercise_reps += 1
                last_rep_time = time.time()
        else:
            feedback = "Keep going!"
            
    elif exercise_type == 8:  # Deadlift
        back_angle = calculate_angle(points['left_hip'], points['left_shoulder'], points['left_knee'])
        
        if back_angle > 160:
            exercise_state = "up"
            feedback = "Go down slowly!"
            color = (0, 0, 255)
        elif back_angle < 90:
            feedback = "Good lift!"
            if exercise_state == "up":
                exercise_state = "down"
                exercise_reps += 1
                last_rep_time = time.time()
        else:
            feedback = "Maintain a straight back!"
            
    elif exercise_type == 9:  # Pull-up
        left_elbow_angle = calculate_angle(points['left_shoulder'], points['left_elbow'], points['left_wrist'])
        right_elbow_angle = calculate_angle(points['right_shoulder'], points['right_elbow'], points['right_wrist'])
        avg_elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
        
        if avg_elbow_angle > 150:
            exercise_state = "down"
            feedback = "Pull up your body!"
            color = (0, 0, 255)
        elif avg_elbow_angle < 70:
            feedback = "Good pull-up!"
            if exercise_state == "down":
                exercise_state = "up"
                exercise_reps += 1
                last_rep_time = time.time()
        else:
            feedback = "Maintain steady form!"
    
    # Speak feedback - but not too often
    if feedback and feedback != feedback_message:
        speak_feedback(feedback)
        feedback_message = feedback
        feedback_color = color
    
    # Display feedback and repetitions
    cv2.putText(image, f"Reps: {exercise_reps}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(image, feedback, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    
    # Calculate and display exercise pace
    if exercise_reps > 0:
        elapsed_time = time.time() - last_rep_time
        cv2.putText(image, f"Time since last rep: {elapsed_time:.1f}s", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    return image

# Exercise mapping
exercise_map = {
    1: "Squat",
    2: "Push-up",
    3: "Shoulder Press",
    4: "Lateral Raise",
    5: "Tricep Extension",
    6: "Crunch",
    7: "Jumping Jack",
    8: "Deadlift",
    9: "Pull-up"
}

def reset_exercise():
    global user_email
    global exercise_reps, exercise_state, feedback_message, feedback_color, exercise_started
    exercise_reps = 0
    exercise_state = None
    feedback_message = ""
    feedback_color = (0, 255, 0)
    exercise_started = False
    return "Exercise reset! Ready for a new workout."



def save_to_db(email, exercise_name, reps):
    global user_email
    print(f"Saving to DB: email={email}, exercise={exercise_name}, reps={reps}")
    
    if email and exercise_name is not None and reps >= 0:
        try:
            # Check if user already exists
            user = user_data_collection.find_one({"email": email})
            
            workout_data = {
                "exercise": exercise_name.lower(),
                "reps": reps,
                "timestamp": datetime.now()
            }
            
            if user:
                # User exists, add workout to their array
                result = user_data_collection.update_one(
                    {"email": email},
                    {"$push": {"workouts": workout_data}}
                )
                print(f"Update result: {result.modified_count} documents modified")
            else:
                # Create new user with first workout
                result = user_data_collection.insert_one({
                    "email": email,
                    "workouts": [workout_data]
                })
                print(f"Insert result: {result.inserted_id}")
            
            return True
        except Exception as e:
            print(f"MongoDB error: {e}")
            return False
    print("Invalid data provided")
    return False


def process_webcam(exercise_type, flip_camera=True, audio_feedback=True):
    global user_email, engine, exercise_reps, exercise_state, feedback_message, feedback_color
    global exercise_started, camera_active, cap, reps
    
    # Convert exercise name to type number if needed
    if isinstance(exercise_type, str):
        for key, value in exercise_map.items():
            if value == exercise_type:
                exercise_type = key
                break
    
    # Setup variables and options
    if not audio_feedback:
        engine.setProperty('volume', 0)
    else:
        engine.setProperty('volume', 1)
    
    # Reset exercise state if new exercise selected
    if exercise_state is not None:
        reset_exercise()
    
    # Start webcam
    cap = cv2.VideoCapture(0)
    camera_active = True
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        camera_active = False
        return "Could not open camera"
    
    try:
        while camera_active:
            ret, frame = cap.read()
            if not ret:
                break
            
            if flip_camera:
                frame = cv2.flip(frame, 1)  # Flip for selfie view
            
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image)  # Pose detection
            
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                process_exercise_landmarks(results.pose_landmarks.landmark, exercise_type, image)
            else:
                # If no pose detected, display a message
                cv2.putText(image, "No pose detected - move in frame", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            # Add exercise name to the frame
            cv2.putText(image, f"Exercise: {exercise_map[exercise_type]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            yield cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    finally:
        if cap is not None:
            cap.release()
        camera_active = False
        
        # Save workout data when the function completes 
        exercise_name = exercise_map[exercise_type]
        save_to_db(user_email, exercise_name, exercise_reps)
        return f"Workout saved! {exercise_name}: {reps} reps"




# Load your workout_data DataFrame (ensure it is pre-loaded or loaded from a file)
workout_data = pd.read_csv("/Users/jaishree/Downloads/Final/workoutsplit.csv")  # Replace with actual path if needed

# Get phase from cycle day
def get_phase(cycle_day, length_of_cycle):
    if 1 <= cycle_day <= 5:
        return 'Menstrual'
    elif 6 <= cycle_day <= length_of_cycle // 2:
        return 'Follicular'
    elif (length_of_cycle // 2) < cycle_day <= (length_of_cycle // 2) + 3:
        return 'Ovulation'
    else:
        return 'Luteal'

# Get exercises based on phase
def get_exercises_for_phase(phase):
    if phase == 'Menstrual':
        return workout_data[workout_data['Difficulty Rating (Energy Consumption / 5)'] <= 2]
    elif phase == 'Follicular':
        return workout_data[(workout_data['Difficulty Rating (Energy Consumption / 5)'] > 2) &
                            (workout_data['Difficulty Rating (Energy Consumption / 5)'] <= 3)]
    elif phase == 'Ovulation':
        return workout_data[(workout_data['Difficulty Rating (Energy Consumption / 5)'] > 3) &
                            (workout_data['Difficulty Rating (Energy Consumption / 5)'] <= 4)]
    elif phase == 'Luteal':
        return workout_data[workout_data['Difficulty Rating (Energy Consumption / 5)'] >= 3]
    else:
        return pd.DataFrame()

# Step 1: Phase and muscle group list
def recommend_muscle_groups(cycle_day, cycle_length):
    try:
        cycle_day = int(cycle_day)
        cycle_length = int(cycle_length)
        
        if not (1 <= cycle_day <= cycle_length):
            return "Invalid cycle day. Please enter a valid range.", [], "", ""

        phase = get_phase(cycle_day, cycle_length)
        recommended_exercises = get_exercises_for_phase(phase)

        if recommended_exercises.empty:
            return f"You are in the {phase} phase.", [], "", "No exercises available for this phase."

        muscle_groups = list(recommended_exercises['Muscle Group'].unique())
        muscle_group_list = "\n".join([f"{i+1}. {mg}" for i, mg in enumerate(muscle_groups)])
        return f"You are in the {phase} phase.", muscle_groups, muscle_group_list, "Select a muscle group from the list."
    except:
        return "Invalid input.", [], "", ""

# Step 2: Recommend workout for chosen muscle group
def recommend_workout_for_muscle_group(cycle_day, cycle_length, muscle_choice, muscle_group_list):
    try:
        muscle_choice = int(muscle_choice)
        cycle_day = int(cycle_day)
        cycle_length = int(cycle_length)

        phase = get_phase(cycle_day, cycle_length)
        recommended_exercises = get_exercises_for_phase(phase)
        muscle_groups = list(recommended_exercises['Muscle Group'].unique())

        if muscle_choice < 1 or muscle_choice > len(muscle_groups):
            return "Invalid muscle group choice."

        chosen_muscle_group = muscle_groups[muscle_choice - 1]
        chosen_workout = recommended_exercises[recommended_exercises['Muscle Group'] == chosen_muscle_group]

        workout_plan = chosen_workout[['Muscle Group', 'Exercise', 'min reps', 'max reps', 'sets']]
        return f"Workout plan for {chosen_muscle_group}:\n{workout_plan.to_string(index=False)}"
    except:
        return "Invalid input."

# Gradio UI
def build_period_workout_ui():
    with gr.Blocks(title="Period-Based Workout Recommender") as app:
        gr.Markdown("## Personalized Workout Recommendations Based on Your Cycle Phase")

        with gr.Row():
            cycle_day_input = gr.Number(label="Enter your current cycle day")
            cycle_length_input = gr.Number(label="Enter your total cycle length (in days)", value=28)
        
        phase_output = gr.Textbox(label="Cycle Phase")
        muscle_group_list_output = gr.Textbox(label="Muscle Group Options")
        message_output = gr.Textbox(label="Message")

        muscle_group_hidden = gr.State()

        get_phase_btn = gr.Button("Get Muscle Groups")
        get_phase_btn.click(
            recommend_muscle_groups,
            inputs=[cycle_day_input, cycle_length_input],
            outputs=[phase_output, muscle_group_hidden, muscle_group_list_output, message_output]
        )

        muscle_choice_input = gr.Number(label="Enter the number of your muscle group choice")
        workout_output = gr.Textbox(label="Recommended Workout Plan", lines=10)

        get_workout_btn = gr.Button("Get Workout Plan")
        get_workout_btn.click(
            recommend_workout_for_muscle_group,
            inputs=[cycle_day_input, cycle_length_input, muscle_choice_input, muscle_group_hidden],
            outputs=workout_output
        )

    return app


# ⬇️ Refactor the function to return UI elements (not launch a standalone Blocks)
def period_tracker_tab():
    with gr.Column():
        gr.Markdown("## Personalized Workout Recommendations Based on Your Cycle Phase")

        with gr.Row():
            cycle_day_input = gr.Number(label="Enter your current cycle day")
            cycle_length_input = gr.Number(label="Enter your total cycle length (in days)", value=28)
        
        phase_output = gr.Textbox(label="Cycle Phase")
        muscle_group_list_output = gr.Textbox(label="Muscle Group Options")
        message_output = gr.Textbox(label="Message")

        muscle_group_hidden = gr.State()

        get_phase_btn = gr.Button("Get Muscle Groups")
        get_phase_btn.click(
            recommend_muscle_groups,
            inputs=[cycle_day_input, cycle_length_input],
            outputs=[phase_output, muscle_group_hidden, muscle_group_list_output, message_output]
        )

        muscle_choice_input = gr.Number(label="Enter the number of your muscle group choice")
        workout_output = gr.Textbox(label="Recommended Workout Plan", lines=10)

        get_workout_btn = gr.Button("Get Workout Plan")
        get_workout_btn.click(
            recommend_workout_for_muscle_group,
            inputs=[cycle_day_input, cycle_length_input, muscle_choice_input, muscle_group_hidden],
            outputs=workout_output
        )

#Water Tracker
import gradio as gr

# WaterTracker class (your logic)
import gradio as gr

# WaterTracker logic
import gradio as gr

# WaterTracker logic
class WaterTracker:
    def __init__(self, gender, activity_level):
        self.gender = gender
        self.activity_level = activity_level
        self.total_water_liters = self.calculate_daily_water_intake()
        self.glasses_per_liter = 4  # 1 glass = 250 ml
        self.total_glasses = int(self.total_water_liters * self.glasses_per_liter)
        self.remaining_glasses = self.total_glasses

    def calculate_daily_water_intake(self):
        if self.gender.lower() == 'male':
            return 3.7 if self.activity_level else 3.0
        elif self.gender.lower() == 'female':
            return 2.7 if self.activity_level else 2.2

    def drink_glass(self):
        if self.remaining_glasses > 0:
            self.remaining_glasses -= 1
        return self.get_status()

    def get_status(self):
        remaining_liters = self.remaining_glasses / self.glasses_per_liter
        if self.remaining_glasses > 0:
            return f"Total Target: {self.total_glasses} glasses ({self.total_water_liters:.1f} L)\n" + \
                   f"Remaining: {self.remaining_glasses} glasses ({remaining_liters:.2f} L)"
        else:
            return f"🎯 Target Reached! You completed {self.total_glasses} glasses ({self.total_water_liters:.1f} L)"

    def reset(self):
        self.remaining_glasses = self.total_glasses
        return self.get_status()


# Gradio functions
def create_tracker(gender, activity_level):
    tracker = WaterTracker(gender, activity_level == "Active")
    return tracker, tracker.get_status()

def drink_water(tracker):
    return tracker, tracker.drink_glass()

def reset_water(tracker):
    return tracker, tracker.reset()


# UI Builder
def build_water_tracker_ui():
    with gr.Blocks() as water_tab:
        gr.Markdown("## 💧 Water Intake Tracker")

        with gr.Row():
            gender_input = gr.Dropdown(label="Select Gender", choices=["Male", "Female"])
            activity_input = gr.Dropdown(label="Select Lifestyle", choices=["Active", "Inactive"])

        tracker_state = gr.State()
        status_box = gr.Textbox(label="Water Tracker Status", lines=2)

        with gr.Row():
            init_btn = gr.Button("Initialize Tracker")
            drink_btn = gr.Button("Drink a Glass")
            reset_btn = gr.Button("Reset Tracker")

        init_btn.click(fn=create_tracker,
                       inputs=[gender_input, activity_input],
                       outputs=[tracker_state, status_box])

        drink_btn.click(fn=drink_water,
                        inputs=tracker_state,
                        outputs=[tracker_state, status_box])

        reset_btn.click(fn=reset_water,
                        inputs=tracker_state,
                        outputs=[tracker_state, status_box])

    return water_tab


#Food Recommender

import random

# Load the food dataset
food_data = pd.read_csv(r"/Users/jaishree/Downloads/Final/food_data.csv", encoding='ISO-8859-1')

# Function to calculate BMI
def calculate_bmi(weight, height):
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

# Function to calculate daily calorie intake
def calculate_calories(weight, height, age, gender, activity_level, target_weight):
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

    # Adjust based on target
    if target_weight < weight:
        calories -= 500
    elif target_weight > weight:
        calories += 500
    
    return calories

# Function to create meal plan within calorie limit
def create_meal_plan(calories):
    breakfast = []
    lunch = []
    dinner = []
    total_calories = 0

    while total_calories < calories - 50 or total_calories > calories + 50:
        breakfast = random.sample(list(food_data.itertuples(index=False, name=None)), 1)
        lunch = random.sample(list(food_data.itertuples(index=False, name=None)), 2)
        dinner = random.sample(list(food_data.itertuples(index=False, name=None)), 1)

        total_calories = (
            sum(item[-1] for item in breakfast) +
            sum(item[-1] for item in lunch) +
            sum(item[-1] for item in dinner)
        )

    return breakfast, lunch, dinner, total_calories

# Function to recommend meal plan
def recommend_meal_plan(weight, height, age, gender, activity_level, target_weight):
    try:
        bmi, bmi_category = calculate_bmi(weight, height)
        calories = calculate_calories(weight, height, age, gender, activity_level, target_weight)
        breakfast, lunch, dinner, total_cals = create_meal_plan(calories)

        meal_text = f"✅ BMI: {bmi:.1f} ({bmi_category})\n"
        meal_text += f"🔢 Target Calories: {int(calories)} kcal\n\n"

        meal_text += "🍳 Breakfast:\n"
        for item in breakfast:
            meal_text += f"• {item[1]} - {item[-1]} kcal\n"

        meal_text += "\n🥗 Lunch:\n"
        for item in lunch:
            meal_text += f"• {item[1]} - {item[-1]} kcal\n"

        meal_text += "\n🍛 Dinner:\n"
        for item in dinner:
            meal_text += f"• {item[1]} - {item[-1]} kcal\n"

        meal_text += f"\nTotal Calories in Plan: {int(total_cals)} kcal"

        return meal_text

    except Exception as e:
        return f"Error: {str(e)}"


#Chatbot
    


load_dotenv()
openai_api_key = os.environ["OPENAI_API_KEY"]

# Load exercise dataset
exercise_data = pd.read_csv('/Users/jaishree/Downloads/Final/megaGymDataset.csv')


# Initialize chatbot
system_msg_template = SystemMessagePromptTemplate.from_template(
    template="Answer the question as truthfully as possible, even if you don't have all the information to provide a perfect solution. If the answer is not apparent, provide guidance on how the user might rephrase the question or find more information."
)
human_msg_template = HumanMessagePromptTemplate.from_template(template="{input}")
prompt_template = ChatPromptTemplate.from_messages([
    system_msg_template,
    MessagesPlaceholder(variable_name="history"),
    human_msg_template
])

chatbot_chain = ConversationChain(
    memory=ConversationBufferWindowMemory(k=3, return_messages=True),
    prompt=prompt_template,
    llm=ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=openai_api_key)
)

chat_history = []

# Text-to-Speech
engine = pyttsx3.init()

from threading import Thread

def speak(text):
    def run():
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    
    t = Thread(target=run)
    t.start()


# Speech Recognition
is_listening = False

def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        try:
            audio = recognizer.listen(source)
            query = recognizer.recognize_google(audio)
            print(f"You said: {query}")
            return query
        except sr.UnknownValueError:
            return "Could not understand audio."
        except sr.RequestError:
            return "Request error. Check your internet connection."

def process_chatbot_input(user_input, goal, experience, restrictions):
    global chat_history
    try:
        preferences_str = f"Your goals are {goal}, your experience level is {experience}, and you noted the following restrictions: {restrictions}. "
        history_summary = ""
        if chat_history:
            history_summary = "You previously mentioned the following: " + \
                " ".join([f"- You asked: {q}. I responded: {a}." for q, a in chat_history])

        prompt = f"You are a helpful fitness expert. {history_summary} {preferences_str} Please answer the following question: {user_input}."
        response = chatbot_chain.predict(input=prompt)
        chat_history.append((user_input, response))
        speak(response)
        return response, user_input
    except Exception as e:
        return f"An error occurred: {e}. Please try again.", ""

def chatbot_interface():
    with gr.Row():
        goal = gr.Dropdown(label="Fitness Goal", choices=["Weight Loss", "Build Muscle", "Endurance", "General Fitness"], value="General Fitness")
        experience = gr.Dropdown(label="Experience Level", choices=["Beginner", "Intermediate", "Advanced"], value="Beginner")
        restrictions = gr.Dropdown(label="Any injuries or limitations?", choices=["None", "Back Pain", "Knee Issues", "Shoulder Pain", "Other"], value="None")

    chatbot_output = gr.Chatbot(label="FlexiFit Chat", type='messages')
    chatbot_input = gr.Textbox(label="Type your question", placeholder="Ask me anything about your fitness journey", lines=1)
    send_button = gr.Button("Send")
    speak_button = gr.Button("🎤 Speak", variant="secondary")

    transcript_display = gr.Textbox(label="Recognized Speech", interactive=False)

    def on_click(user_input, goal, experience, restrictions):
        response, _ = process_chatbot_input(user_input, goal, experience, restrictions)
        return chatbot_output.value + [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": response}
        ], ""

    def on_speak(goal, experience, restrictions):
        speak_button.value = "🛑 Stop"
        transcript = listen()
        response, _ = process_chatbot_input(transcript, goal, experience, restrictions)
        return chatbot_output.value + [
            {"role": "user", "content": transcript},
            {"role": "assistant", "content": response}
        ], transcript, "🎤 Speak"

    send_button.click(fn=on_click, inputs=[chatbot_input, goal, experience, restrictions], outputs=[chatbot_output, chatbot_input])
    speak_button.click(fn=on_speak, inputs=[goal, experience, restrictions], outputs=[chatbot_output, transcript_display, speak_button])

    return gr.Column([
        goal,
        experience,
        restrictions,
        chatbot_output,
        gr.Row([chatbot_input, send_button, speak_button]),
        transcript_display
    ])



#Calorie Estimator

def calorie_estimator_ui():
    def input_image_setup(image):
        if image is not None:
            image.thumbnail((512, 512))
            image.save("temp_image.jpg", format="JPEG")
            with open("temp_image.jpg", "rb") as temp_file:
                base64_encoded_data = base64.b64encode(temp_file.read()).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{base64_encoded_data}"
            return data_url
        else:
            return None

    def analyze(image):
        input_prompt = """
        You are an expert in nutrition where you need to analyze the food items from the image,
        calculate the total calories, and provide details of each food item with its calorie intake in the following format:

        1. Item 1 - number of calories
        2. Item 2 - number of calories
        ----
        ----
        Finally, mention whether the food is healthy, balanced, or not healthy. Also, suggest additional healthy food items 
        that can be added to the diet.
        """
        image_data_url = input_image_setup(image)
        if image_data_url is None:
            return "❌ Failed to process the image. Please try again."
        try:
            client = openai.OpenAI(api_key=openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert nutritionist."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": input_prompt},
                            {"type": "image_url", "image_url": {"url": image_data_url}}
                        ]
                    }
                ],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

    image_input = gr.Image(type="pil", label="Upload a food image")
    analyze_button = gr.Button("🔍 Analyze Calories")
    analysis_output = gr.Textbox(label="Calorie Analysis", lines=10)

    analyze_button.click(fn=analyze, inputs=image_input, outputs=analysis_output)

    return gr.Column([
        image_input,
        analyze_button,
        analysis_output
    ])


def finish_workout(exercise_name):
    global user_email, exercise_reps, camera_active, cap
    
    # Stop the camera
    camera_active = False
    if cap is not None:
        cap.release()
        cap = None
    
    # Look up the key for this exercise name if needed
    if isinstance(exercise_name, str):
        exercise_type = None
        for key, value in exercise_map.items():
            if value == exercise_name:
                exercise_type = key
                break
    else:
        exercise_type = exercise_name
        exercise_name = exercise_map.get(exercise_type, "Unknown Exercise")
    
    # Save the workout data
    try:
        db = client["gym_app"]
        user_data_collection = db["user_data"]
        
        result = save_to_db(user_email, exercise_name, exercise_reps)
        reset_exercise()  # Reset after saving
        
        if result:
            return f"Camera stopped. Workout saved! {exercise_name}: Checkout Workout History"
        else:
            return f"Camera stopped. Error saving workout data. Please try again."
    except Exception as e:
        print(f"Error in finish_workout: {e}")
        reset_exercise()
        return f"Camera stopped. Error: {str(e)}"
   


def fetch_workout_history():
    """Retrieve and format the workout history from MongoDB."""
    global user_email
    user = user_data_collection.find_one({"email": user_email})
    if not user or "workouts" not in user:
        return "No workout history found."
    
    history = "Workout History:\n"
    for workout in user["workouts"]:
        formatted_time = workout["timestamp"].strftime("%B %d, %Y at %I:%M %p")  # Directly format the datetime object
        history += f"🟢 Exercise: {workout['exercise']}\n   🔹 Reps: {workout['reps']}\n   ⏰ Time: {formatted_time}\n\n"
    
    return history



#Gradio Interface
def gradio_exercise_tracker():
    with gr.Blocks(title="FlexiFit") as app:
        gr.Markdown("# FlexiFit")
        
        with gr.Row(visible=True) as login_section:
            email_input = gr.Textbox(label="Enter Your Email")
            login_button = gr.Button("Login")
            error_message = gr.Textbox(visible=False, interactive=False)

        with gr.Tabs(visible=False) as main_ui:
            with gr.Tab("Home"):
                gr.Markdown("## Welcome to Your Personalized Gym App!")

        # Exercise Tracker Tab
            with gr.Tab("Exercise Tracker"):
                gr.Markdown("Select an exercise and position yourself in front of the camera to start tracking.")
            
                with gr.Row():
                    with gr.Column(scale=2):
                        # Exercise selection
                        exercise_dropdown = gr.Dropdown(
                            choices=list(exercise_map.values()),
                            value="Squat",
                            label="Choose Exercise"
                        )
                    
                        # Options
                        flip_camera = gr.Checkbox(label="Flip Camera (Selfie Mode)", value=True)
                        audio_feedback = gr.Checkbox(label="Audio Feedback", value=True)
                    
                        # Reset button
                        reset_btn = gr.Button("Reset Exercise Counter")
                        reset_output = gr.Textbox(label="Status")
                        reset_btn.click(reset_exercise, inputs=None, outputs=reset_output)
                    
                        # Exercise instructions
                        instruction_text = gr.Markdown("""
                        ## How to use:
                        1. Select an exercise from the dropdown
                        2. Position yourself so the camera can see your full body
                        3. Click 'Start Tracking'
                        4. The system will count reps and provide feedback
                        5. Use the reset button to start a new set
                        """)
                
                    with gr.Column(scale=3):
                        # Video input
                        video_output = gr.Image(label="Exercise Tracking", streaming=True)
            
                # Start tracking button
                start_btn = gr.Button("Start Tracking")
                start_btn.click(
                    process_webcam,
                    inputs=[exercise_dropdown, flip_camera, audio_feedback],
                    outputs=video_output
                )
                process_button = gr.Button("Finish")
                output_text = gr.Textbox(label="Output")
                process_button.click(
                    finish_workout, 
                    inputs=[exercise_dropdown], 
                    outputs=[output_text]
                )            # Water Tracker Tab
            with gr.Tab("Water Tracker"):
                build_water_tracker_ui()
                
            # Period Tracker Tab
            with gr.Tab("Period Tracker"):
                period_tracker_tab()
               
                
            
            
            with gr.Tab("Food Recommender"):
                gr.Markdown("### 🥗 Personalized Meal Plan Based on Your Body & Goals")

                with gr.Row():
                    weight = gr.Number(label="Weight (kg)")
                    height = gr.Number(label="Height (cm)")
                    age = gr.Number(label="Age")

                with gr.Row():
                    gender = gr.Dropdown(["Male", "Female"], label="Gender")
                    activity = gr.Dropdown(["Sedentary", "Light", "Moderate", "Active", "Very Active"], label="Lifestyle")

                target_weight = gr.Number(label="Target Weight (kg)")

                with gr.Row():
                    generate_button = gr.Button("🍽️ Generate Meal Plan")
                    reset_button = gr.Button("🔄 Reset")

                output = gr.Textbox(label="Meal Plan & Calorie Summary", lines=15)

                def reset_fields():
                    return None, None, None, None, None, None, ""

                generate_button.click(
                    recommend_meal_plan,
                    inputs=[weight, height, age, gender, activity, target_weight],
                    outputs=[output]
                )

                reset_button.click(
                    fn=reset_fields,
                    inputs=[],
                    outputs=[weight, height, age, gender, activity, target_weight, output]
                )
            
            with gr.Tab("Calorie Estimator"):
                calorie_estimator_ui()

            with gr.Tab("Chatbot"):
                chatbot_interface()
                
            with gr.Tab("Workout History"):
                gr.Markdown("## Your Workout History")
                history_output = gr.Textbox(label="Workout History", interactive=False)
                refresh_button = gr.Button("Refresh History")
                refresh_button.click(fetch_workout_history, inputs=[], outputs=[history_output])   
            login_button.click(
                authenticate,
                inputs=[email_input],
                outputs=[main_ui, error_message, login_section]
            )

        return app


    


# Launch the Gradio app
if __name__ == "__main__":
    app = gradio_exercise_tracker()  # This line creates the app
    app.launch(share=False)