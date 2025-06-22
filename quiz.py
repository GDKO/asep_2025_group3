#!/usr/bin/env python
"""Asep 2025 Quiz"""

import tkinter as tk
from tkinter import messagebox
import re
import sys
import json
import random
import platform
import time
import os
import numpy as np

def resource_path(relative_path):
    """ Get absolute path to resource (works for dev and PyInstaller) """
    try:
        base_path = sys._MEIPASS  # PyInstaller sets this at runtime
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_user_data_dir():
    """Return a directory path where user data can be safely stored."""
    home = os.path.expanduser("~")
    appname = "AsepQuiz"

    if platform.system() == "Darwin":  # macOS
        path = os.path.join(home, "Library", "Application Support", appname)
    elif platform.system() == "Windows":
        path = os.path.join(os.environ.get("APPDATA", home), appname)
    else:  # Linux and others
        path = os.path.join(home, f".{appname}")

    os.makedirs(path, exist_ok=True)
    return path

QUESTIONS_FILE = resource_path("./questions.json")
USER_DATA_FILE = os.path.join(get_user_data_dir(), "user_data_g3.json")
NUM_QUESTIONS = 25
QUIZ_DURATION = 25 * 60  # seconds

class QuizApp(tk.Tk):
    """Quiz class"""
    def __init__(self):
        super().__init__()
        self.title("Quiz Application")
        self.geometry("1200x700")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.username = None
        self.user_data = {}

        self.user_info = None
        self.quiz_frame = None
        self.timer_label = None
        self.question_label = None
        self.var_answer = None
        self.radio_buttons = None
        self.next_button = None
        self.feedback_label = None


        self.questions = []
        self.selected_questions = []
        self.current_index = 0
        self.score = 0
        self.quiz_start_time = None
        self.remaining_time = QUIZ_DURATION

        self.load_questions()
        self.load_user_data()

        self.create_login_screen()

    def load_questions(self):
        """Load questions from the json file"""
        try:
            with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
                self.questions = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("File Error", f"Questions file '{QUESTIONS_FILE}' not found.")
            self.destroy()
        except json.JSONDecodeError:
            messagebox.showerror("File Error", f"Questions file '{QUESTIONS_FILE}' is not valid JSON.")
            self.destroy()

    def load_user_data(self):
        """Load user data from file"""
        if os.path.exists(USER_DATA_FILE):
            try:
                with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                    self.user_data = json.load(f)
            except json.JSONDecodeError:
                messagebox.showwarning("Data Warning", f"User data file '{USER_DATA_FILE}' is corrupted. Starting fresh.")
                self.user_data = {}
        else:
            self.user_data = {}

    def save_user_data(self):
        """Save user data to file"""
        try:
            with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.user_data, f, indent=4, ensure_ascii=False)
        except (OSError, IOError, PermissionError) as e:
            messagebox.showerror("Save Error", f"Failed to save user data: {str(e)}")

    def select_weighted_questions(self, user_adj_weights, k=NUM_QUESTIONS):
        """Select questions based on the adjusted weights"""
        k = min(k, len(self.questions))
        weights = np.array([user_adj_weights.get(str(q["id"]), q.get("adj_weight", 1)) for q in self.questions], dtype=float)
        weights /= weights.sum()
        chosen_indices = np.random.choice(len(self.questions), size=k, replace=False, p=weights)
        selected = [self.questions[i] for i in chosen_indices]
        return selected

    def update_weights(self, user_weights, user_adj, user_adj_weights, user_times_chosen, user_correct_answers, question, correct):
        """Update the questions metadata"""
        current = user_weights.get(question, 1)
        current_tc = user_times_chosen.get(question, 1)
        current_ca = user_correct_answers.get(question, 1)
        user_weights[question] = max(2, int(current * 3/4)) if correct else min(500, current * 2)
        user_times_chosen[question] = current_tc + 1
        if correct:
            user_correct_answers[question] = current_ca + 1
        user_adj[question] = 1
        user_adj_weights[question] = user_adj[question]*user_weights[question]

    def create_login_screen(self):
        """Login screen"""
        self.clear_widgets()
        self.login_frame = tk.Frame(self)
        self.login_frame.pack(expand=True)

        tk.Label(self.login_frame, text="Asep Quiz Group 3", font=("Arial", 16)).pack(pady=20)

        tk.Label(self.login_frame, text="Enter Username:", font=("Arial", 16)).pack(pady=20)
        self.username_entry = tk.Entry(self.login_frame, font=("Arial", 14))
        self.username_entry.pack(pady=10)
        self.username_entry.focus()

        login_btn = tk.Button(self.login_frame, text="Start Quiz", font=("Arial", 14), command=self.start_quiz)
        login_btn.pack(pady=10)

    def start_quiz(self):
        """Start the quiz"""
        username = self.username_entry.get().strip().lower()
        if not username:
            messagebox.showwarning("Input error", "Please enter a username.")
            return

        if not self.validate_username(username):
            messagebox.showwarning("Input error", "Username must be 3-20 chars long and only contain letters, numbers, underscores, or dashes.")
            return

        self.username = username

        if username not in self.user_data:
            # Initialize user data
            weights = {str(q["id"]): 100 for q in self.questions}
            times_chosen = {str(q["id"]): 0 for q in self.questions}
            correct_answers = {str(q["id"]): 0 for q in self.questions}
            adj = {str(q["id"]): 1 for q in self.questions}
            adj_weights = {str(q["id"]): 100 for q in self.questions}
            self.user_data[username] = {
                "weights": weights,
                "times_chosen": times_chosen,
                "correct_answers": correct_answers,
                "adj": adj,
                "adj_weights": adj_weights,
                "scores": []
            }
            self.save_user_data()

        self.user_info = self.user_data[username]

        # Update adj and adj_weights
        for q in self.questions:
            self.user_info["adj"][str(q["id"])] += 1
            self.user_info["adj_weights"][str(q["id"])] = self.user_info["adj"][str(q["id"])] * self.user_info["weights"][str(q["id"])]

        self.save_user_data()

        self.selected_questions = self.select_weighted_questions(self.user_info["adj_weights"], NUM_QUESTIONS)
        for q in self.selected_questions:
            random.shuffle(q["choices"])

        self.current_index = 0
        self.score = 0
        self.quiz_start_time = time.time()
        self.remaining_time = QUIZ_DURATION

        self.create_quiz_screen()
        self.update_timer()

    def validate_username(self, username):
        """Username must contain only alphanum and _ chars"""
        pattern = r'^[a-zA-Z0-9_-]{3,20}$'
        return re.match(pattern, username) is not None

    def create_quiz_screen(self):
        """Create the quiz window"""
        self.clear_widgets()
        self.quiz_frame = tk.Frame(self)
        self.quiz_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.timer_label = tk.Label(self.quiz_frame, text="", font=("Arial", 14), fg="red")
        self.timer_label.pack(pady=10)

        self.question_label = tk.Label(self.quiz_frame, text="", font=("Arial", 16), wraplength=850, justify="left")
        self.question_label.pack(pady=20)

        self.var_answer = tk.StringVar(value=None)
        self.radio_buttons = []

        for _ in range(4):  # max 4 choices
            rb = tk.Radiobutton(self.quiz_frame, text="", variable=self.var_answer, value="", font=("Arial", 14), anchor="w", justify="left", wraplength=1000)
            rb.pack(fill="x", padx=20, pady=5)
            self.radio_buttons.append(rb)

        self.bind("1", lambda event: self.select_option(0))
        self.bind("2", lambda event: self.select_option(1))
        self.bind("3", lambda event: self.select_option(2))
        self.bind("4", lambda event: self.select_option(3))

        self.next_button = tk.Button(self.quiz_frame, text="Επόμενη ερώτηση", font=("Arial", 14), command=self.next_question, state="disabled")
        self.next_button.pack(anchor="w", pady=10, padx=20)
        self.bind('<Return>', self.on_enter_pressed)

        self.feedback_label = tk.Label(self.quiz_frame, text="", font=("Arial", 14), wraplength=1000, justify="left")
        self.feedback_label.pack(anchor="w", pady=10, padx=20)

        self.load_question()

    def on_enter_pressed(self, _event):
        """Enter will not advance to next question unless a choice has been made"""
        if self.var_answer.get() == "None":
            return "break"

        self.next_question()
        return "break"

    def select_option(self, index):
        """Selects the option"""
        if 0 <= index < len(self.radio_buttons):
            self.radio_buttons[index].invoke()

    def load_question(self):
        """Load the question"""
        if self.current_index >= len(self.selected_questions):
            self.show_results()
            return

        q = self.selected_questions[self.current_index]
        q_string = re.sub(r'\d+\.','',q['question'], count=1)
        q_string = q_string.strip()
        self.question_label.config(text=f"Q{self.current_index + 1}: {q_string}")
        self.var_answer.set(None)

        for i, choice in enumerate(q["choices"]):
            self.radio_buttons[i].config(text=choice, value=choice, state="normal")
            self.radio_buttons[i].pack()
        # Hide any extra radios if fewer choices
        for j in range(len(q["choices"]), 4):
            self.radio_buttons[j].pack_forget()

        self.feedback_label.config(text="")
        self.next_button.config(state="disabled")

        # Bind radiobuttons for answer checking
        for rb in self.radio_buttons:
            rb.config(command=self.check_answer)

    def check_answer(self):
        """Check the answer"""
        selected = self.var_answer.get()
        if not selected:
            return

        q = self.selected_questions[self.current_index]
        correct = selected.strip() == q["answer"].strip()

        times_chosen = self.user_info["times_chosen"].get(str(q["id"]), 0) + 1
        correct_answers = self.user_info["correct_answers"].get(str(q["id"]), 0)

        if correct:
            self.feedback_label.config(text=f"[{correct_answers + 1}/{times_chosen}] ✅ Σωστά!")
            self.feedback_label.config(fg="green")
            self.score += 1
        else:
            self.feedback_label.config(text=f"[{correct_answers}/{times_chosen}] ❌ Λάθος. Σωστή απάντηση: {q['answer']}")
            self.feedback_label.config(fg="red")

        # Update weights for question
        self.update_weights(
            self.user_info["weights"],
            self.user_info["adj"],
            self.user_info["adj_weights"],
            self.user_info["times_chosen"],
            self.user_info["correct_answers"],
            str(q["id"]),
            correct
        )
        self.save_user_data()

        self.next_button.config(state="normal")
        # Disable radiobuttons after answer
        for rb in self.radio_buttons:
            rb.config(state="disabled")

    def next_question(self):
        """Goes to next question"""
        self.current_index += 1
        if self.current_index >= len(self.selected_questions):
            self.show_results()
        else:
            self.load_question()

    def update_timer(self):
        """Updates the time"""
        if self.current_index >= len(self.selected_questions):
            return  # Quiz ended

        elapsed = int(time.time() - self.quiz_start_time)
        self.remaining_time = QUIZ_DURATION - elapsed

        if self.remaining_time <= 0:
            messagebox.showinfo("Time's up!", "⏰ Time's up! The quiz will end now.")
            self.show_results()
            return

        mins, secs = divmod(self.remaining_time, 60)
        self.timer_label.config(text=f"Time left: {mins:02d}:{secs:02d}")
        self.after(1000, self.update_timer)

    def draw_score_plot(self, canvas, scores, max_score):
        """Draws a simple score history line chart using tkinter.Canvas"""
        if not scores:
            return

        w, h = int(canvas["width"]), int(canvas["height"])
        margin = 40
        plot_w, plot_h = w - 2 * margin, h - 2 * margin

        # Scale scores
        max_score = max(max_score, 1)
        x_spacing = plot_w / max(1, len(scores) - 1)
        y_scale = plot_h / max_score

        # Compute points
        points = []
        for i, score in enumerate(scores):
            x = margin + i * x_spacing
            y = h - margin - score * y_scale
            points.append((x, y))
            # Draw dot
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="blue")

        # Draw lines
        for i in range(len(points) - 1):
            canvas.create_line(*points[i], *points[i + 1], fill="blue", width=2)

        # Y-axis lines and labels
        for i in range(0, max_score + 1, max(1, max_score // 5)):
            y = h - margin - i * y_scale
            canvas.create_line(margin - 5, y, margin, y)
            canvas.create_text(margin - 10, y, text=str(i), anchor="e", font=("Arial", 10))

        # X-axis labels
        for i in range(len(scores)):
            x = margin + i * x_spacing
            canvas.create_line(x, h - margin, x, h - margin + 5)
            canvas.create_text(x, h - margin + 15, text=str(i + 1), anchor="n", font=("Arial", 10))

        # Draw axes
        canvas.create_line(margin, margin, margin, h - margin, width=2)  # Y axis
        canvas.create_line(margin, h - margin, w - margin, h - margin, width=2)  # X axis

        # Title
        canvas.create_text(w // 2, margin // 2, text="Ιστορικό αποτελεσμάτων", font=("Arial", 14, "bold"))


    def show_results(self):
        """Results window"""
        #Unbind the keys
        self.bind("<Return>", lambda event: None)
        self.bind("1", lambda event: None)
        self.bind("2", lambda event: None)
        self.bind("3", lambda event: None)
        self.bind("4", lambda event: None)

        self.clear_widgets()

        self.user_info["scores"].append(self.score)
        self.save_user_data()

        chosen = 0
        for q,t in self.user_info["times_chosen"].items():
            if t > 0:
                chosen += 1

        chosen_correct = 0
        for q,t in self.user_info["correct_answers"].items():
            if t > 0:
                chosen_correct += 1

        total = len(self.selected_questions)
        duration = int(time.time() - self.quiz_start_time) if self.quiz_start_time else 0

        result_frame = tk.Frame(self)
        result_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Score summary
        result_text = (
            f"Το Quiz ολοκληρώθηκε!\n\n"
            f"Αποτέλεσμα: {self.score} / {total}\n\n"
            f"Διάρκεια: {duration // 60} min {duration % 60} sec, "
            f"ανά ερώτηση: {duration // total // 60} min {duration // total % 60} sec\n\n"
            f"{chosen} / 400 ερωτήσεις έχουν επιλεχθεί ({round(100*chosen/400,4)}%)\n"
            f"{chosen_correct} / {chosen} έχουν απαντηθεί σωστά ({round(100*chosen_correct/chosen,4)}%)"
        )
        tk.Label(result_frame, text=result_text, font=("Arial", 16), justify="center").pack(pady=10)

        # Graph of score history
        canvas = tk.Canvas(result_frame, width=800, height=300, bg="white", highlightthickness=1, highlightbackground="#ccc")
        canvas.pack(pady=10)
        self.draw_score_plot(canvas, self.user_info["scores"], total)

        # Buttons
        retry_btn = tk.Button(result_frame, text="Επόμενο Quiz", font=("Arial", 14), command=self.create_login_screen)
        retry_btn.pack(pady=5)

        quit_btn = tk.Button(result_frame, text="Έξοδος", font=("Arial", 14), command=self.quit)
        quit_btn.pack(pady=5)


    def clear_widgets(self):
        """Clear step"""
        for widget in self.winfo_children():
            widget.destroy()

    def on_close(self):
        """Bye bye"""
        if messagebox.askokcancel("Quit", "Do you want to quit the quiz?"):
            self.destroy()


if __name__ == "__main__":
    app = QuizApp()
    app.mainloop()
