import cv2
import tkinter as tk
import time
import random
import threading
import numpy as np

class VehicleDetector:
    def __init__(self, cascade_path):
        """Initialize the vehicle detector with a cascade classifier."""
        self.car_cascade = cv2.CascadeClassifier(cascade_path)
        self.total_cars_detected = 0
        self.cars_per_direction = {'north': 0, 'south': 0, 'east': 0, 'west': 0}
        self.current_direction = 'north'  # Default direction for detection
        
    def detect_vehicles(self, frame):
        """Detect vehicles in a frame and return the count."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cars = self.car_cascade.detectMultiScale(gray, 1.1, 1)
        
        # Draw rectangles around detected cars
        for (x, y, w, h) in cars:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            
        # Update the total count and direction count
        car_count = len(cars)
        self.total_cars_detected += car_count
        self.cars_per_direction[self.current_direction] += car_count
        
        return frame, car_count
    
    def set_direction(self, direction):
        """Set the current direction for vehicle counting."""
        if direction in self.cars_per_direction:
            self.current_direction = direction
    
    def get_cars_count(self, direction=None):
        """Get the count of cars for a specific direction or all directions."""
        if direction:
            return self.cars_per_direction.get(direction, 0)
        return self.total_cars_detected
    
    def reset_counts(self):
        """Reset all car counts."""
        self.total_cars_detected = 0
        for direction in self.cars_per_direction:
            self.cars_per_direction[direction] = 0


class TrafficSignal:
    def __init__(self, root, direction):
        """Initialize a traffic signal for a specific direction."""
        self.root = root
        self.direction = direction
        self.frame = tk.Frame(root, padx=10, pady=10)
        
        # Create a label for the direction
        tk.Label(self.frame, text=direction.upper()).pack()
        
        # Create canvas for traffic light
        self.canvas = tk.Canvas(self.frame, width=50, height=120, bg='black')
        self.canvas.pack(pady=5)
        
        # Create traffic light circles
        self.red_light = self.canvas.create_oval(10, 10, 40, 40, fill='grey')
        self.yellow_light = self.canvas.create_oval(10, 45, 40, 75, fill='grey')
        self.green_light = self.canvas.create_oval(10, 80, 40, 110, fill='grey')
        
        # Car count label
        self.count_label = tk.Label(self.frame, text="Cars: 0")
        self.count_label.pack()
        
        # Place the frame according to direction
        if direction == 'north':
            self.frame.grid(row=0, column=1)
        elif direction == 'south':
            self.frame.grid(row=2, column=1)
        elif direction == 'east':
            self.frame.grid(row=1, column=2)
        elif direction == 'west':
            self.frame.grid(row=1, column=0)
    
    def set_green(self):
        """Set the traffic light to green."""
        self.canvas.itemconfig(self.red_light, fill='grey')
        self.canvas.itemconfig(self.yellow_light, fill='grey')
        self.canvas.itemconfig(self.green_light, fill='green')
    
    def set_yellow(self):
        """Set the traffic light to yellow."""
        self.canvas.itemconfig(self.red_light, fill='grey')
        self.canvas.itemconfig(self.yellow_light, fill='yellow')
        self.canvas.itemconfig(self.green_light, fill='grey')
    
    def set_red(self):
        """Set the traffic light to red."""
        self.canvas.itemconfig(self.red_light, fill='red')
        self.canvas.itemconfig(self.yellow_light, fill='grey')
        self.canvas.itemconfig(self.green_light, fill='grey')
    
    def update_count(self, count):
        """Update the car count display."""
        self.count_label.config(text=f"Cars: {count}")


class TrafficController:
    def __init__(self, root, cascade_path, video_source=0):
        """Initialize the traffic controller system."""
        self.root = root
        self.root.title("Automatic Traffic Signal Indicator")
        self.root.geometry("800x600")
        
        # Create a grid layout
        for i in range(3):
            root.grid_rowconfigure(i, weight=1)
        for i in range(3):
            root.grid_columnconfigure(i, weight=1)
        
        # Create traffic signals for each direction
        self.signals = {}
        for direction in ['north', 'south', 'east', 'west']:
            self.signals[direction] = TrafficSignal(root, direction)
        
        # Information panel in the center
        info_frame = tk.Frame(root, bg='lightgray', padx=20, pady=20)
        info_frame.grid(row=1, column=1, sticky="nsew")
        
        self.time_left_label = tk.Label(info_frame, text="Time Left: 0s", font=("Arial", 14))
        self.time_left_label.pack(pady=10)
        
        self.current_state_label = tk.Label(info_frame, text="Current: None", font=("Arial", 12))
        self.current_state_label.pack(pady=5)
        
        self.next_state_label = tk.Label(info_frame, text="Next: None", font=("Arial", 12))
        self.next_state_label.pack(pady=5)
        
        # Video display
        self.video_label = tk.Label(info_frame)
        self.video_label.pack(pady=10)
        
        # Control buttons
        control_frame = tk.Frame(info_frame)
        control_frame.pack(pady=10)
        
        tk.Button(control_frame, text="Start", command=self.start_system).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Stop", command=self.stop_system).pack(side=tk.LEFT, padx=5)
        
        # Initialize vehicle detector
        self.detector = VehicleDetector(cascade_path)
        
        # Video capture
        self.video_source = video_source
        self.cap = None
        if self.video_source != 0:  # If not webcam
            try:
                self.cap = cv2.VideoCapture(self.video_source)
            except:
                print(f"Error opening video source: {video_source}")
        
        self.running = False
        self.current_direction = None
        self.next_direction = None
        self.time_remaining = 0
        
    def start_system(self):
        """Start the traffic control system."""
        if self.running:
            return
            
        self.running = True
        
        # Start the video capture if it's not already open
        if self.cap is None or not self.cap.isOpened():
            try:
                self.cap = cv2.VideoCapture(self.video_source)
            except:
                print(f"Error opening video source: {self.video_source}")
                self.running = False
                return
        
        # Start the traffic control in a separate thread
        threading.Thread(target=self.run_traffic_control, daemon=True).start()
        # Start the video processing in a separate thread
        threading.Thread(target=self.process_video, daemon=True).start()
    
    def stop_system(self):
        """Stop the traffic control system."""
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None
    
    def run_traffic_control(self):
        """Run the traffic control logic."""
        while self.running:
            # Reset car counts for a new cycle
            self.detector.reset_counts()
            
            # Sample car counts for each direction (in real implementation, this would be from video)
            for direction in self.signals:
                # In a real system, this would be determined by analyzing video for each direction
                # Here we'll simulate with random counts
                count = random.randint(0, 10)
                self.detector.cars_per_direction[direction] = count
                self.signals[direction].update_count(count)
            
            # Sort directions by car count to prioritize
            sequence = sorted(self.detector.cars_per_direction.items(), key=lambda x: x[1], reverse=True)
            sequence = [direction for direction, _ in sequence]
            
            for i, direction in enumerate(sequence):
                if not self.running:
                    break
                    
                # Set current and next direction
                self.current_direction = direction
                self.next_direction = sequence[(i + 1) % len(sequence)]
                
                # Set detector direction
                self.detector.set_direction(direction)
                
                # Update labels
                self.current_state_label.config(text=f"Current: {direction.upper()}")
                self.next_state_label.config(text=f"Next: {self.next_direction.upper()}")
                
                # Set all signals to red except current
                for d in self.signals:
                    if d != direction:
                        self.signals[d].set_red()
                
                # Set current signal to green
                self.signals[direction].set_green()
                
                # Green light timing based on car count (min 10 seconds, max 30)
                green_time = max(10, min(30, self.detector.get_cars_count(direction) * 3))
                
                # Countdown timer
                for remaining in range(green_time, 0, -1):
                    if not self.running:
                        break
                    self.time_remaining = remaining
                    self.time_left_label.config(text=f"Time Left: {remaining}s - {direction.upper()}")
                    time.sleep(1)
                
                if not self.running:
                    break
                    
                # Yellow light
                self.signals[direction].set_yellow()
                self.time_left_label.config(text=f"Time Left: 3s - {direction.upper()} (Yellow)")
                time.sleep(3)
                
                # Red light
                self.signals[direction].set_red()
    
    def process_video(self):
        """Process video frames for vehicle detection."""
        if not self.cap or not self.cap.isOpened():
            return
            
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                # Restart video if it ends
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
                
            # Resize frame for display
            frame = cv2.resize(frame, (320, 240))
            
            # Process frame with vehicle detector
            processed_frame, car_count = self.detector.detect_vehicles(frame)
            
            # Convert to format for tkinter
            cv_image = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            img = tk.PhotoImage(data=cv2.imencode('.png', cv_image)[1].tobytes())
            
            # Update video display
            self.video_label.config(image=img)
            self.video_label.image = img  # Keep a reference
            
            # Update car count display for current direction
            if self.current_direction:
                self.signals[self.current_direction].update_count(self.detector.get_cars_count(self.current_direction))
            
            time.sleep(0.03)  # ~30 fps
    
    def run(self):
        """Run the tkinter main loop."""
        self.root.mainloop()
        
        # Cleanup
        if self.cap and self.cap.isOpened():
            self.cap.release()


if __name__ == "__main__":
    # Path to cascade classifier
    cascade_path = "haarcascades/cars.xml"
    
    # Path to video file (or 0 for webcam)
    video_path = "traffic_video.mp4"  # Replace with your video file
    
    # Create the root window
    root = tk.Tk()
    
    # Create and run the traffic controller
    controller = TrafficController(root, cascade_path, video_path)
    controller.run()
