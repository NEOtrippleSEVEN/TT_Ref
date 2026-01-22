#!/usr/bin/env python3
"""
Ping Pong Ball Detection System
Detects a white ping-pong ball using color filtering and displays real-time video.
"""

# Import required libraries
import cv2  # OpenCV for image processing and camera handling
import numpy as np  # NumPy for numerical operations on arrays

# ============================================
# CONFIGURATION SECTION
# ============================================

# HSV color range for white ping-pong ball
# HSV = Hue, Saturation, Value (better for color detection than RGB)
# White has low saturation and high value in HSV
# Adjust these if your ball appears different under your lighting
LOWER_WHITE = np.array([0, 0, 200])      # Lower boundary: grayish-white
UPPER_WHITE = np.array([180, 30, 255])   # Upper boundary: pure white

# Minimum area (in pixels) to consider as a valid ball detection
# This filters out small noise/artifacts in the image
MIN_BALL_AREA = 200  # Increased to filter more noise

# Maximum area to filter out large white surfaces (walls, ceiling)
MAX_BALL_AREA = 8000  # Reduced to be stricter

# Circularity threshold (0-1, where 1 is a perfect circle)
# This helps distinguish round balls from rectangular reflections
MIN_CIRCULARITY = 0.75  # Slightly stricter

# Smoothing factor for position (0-1, higher = smoother but slower response)
SMOOTHING = 0.3

# Maximum jump distance (pixels) - helps reject sudden position changes
MAX_JUMP_DISTANCE = 150

# Camera resolution settings
FRAME_WIDTH = 640   # Width in pixels
FRAME_HEIGHT = 480  # Height in pixels

# ============================================
# MAIN PROGRAM
# ============================================

def main():
    """
    Main function that runs the ball detection loop.
    """
    
    # Variables to track previous ball position for smoothing
    prev_x = None
    prev_y = None
    prev_radius = None
    
    # Initialize the camera
    # cv2.VideoCapture(0) opens the default camera (index 0)
    # If you have multiple cameras, try 1, 2, etc.
    print("Initializing camera...")
    camera = cv2.VideoCapture(0)
    
    # Check if camera opened successfully
    if not camera.isOpened():
        print("ERROR: Could not open camera!")
        print("Make sure your camera is connected and not being used by another program.")
        return
    
    # Set camera properties for consistent performance
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    print("Camera initialized successfully!")
    print("Press 'q' to quit the program.")
    print("-" * 50)
    
    # Main detection loop - runs until user presses 'q'
    while True:
        # Read a frame from the camera
        # ret = True if frame was read successfully, False otherwise
        # frame = the actual image data as a NumPy array
        ret, frame = camera.read()
        
        # Check if frame was captured successfully
        if not ret:
            print("ERROR: Failed to grab frame from camera")
            break
        
        # ====================================
        # STEP 1: Convert frame to HSV color space
        # ====================================
        # HSV is better for color detection because it separates color (Hue)
        # from brightness (Value), making it more robust to lighting changes
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # ====================================
        # STEP 2: Create a mask for white color
        # ====================================
        # cv2.inRange creates a binary mask where pixels within the color range
        # are white (255) and pixels outside the range are black (0)
        mask = cv2.inRange(hsv_frame, LOWER_WHITE, UPPER_WHITE)
        
        # Optional: Apply morphological operations to reduce noise
        # Erosion removes small white noise, dilation fills small holes
        kernel = np.ones((5, 5), np.uint8)  # 5x5 structuring element
        mask = cv2.erode(mask, kernel, iterations=1)   # Remove noise
        mask = cv2.dilate(mask, kernel, iterations=2)  # Fill gaps
        
        # ====================================
        # STEP 3: Find contours in the mask
        # ====================================
        # Contours are the boundaries of white regions in the binary mask
        # cv2.RETR_EXTERNAL = retrieve only outer contours
        # cv2.CHAIN_APPROX_SIMPLE = compress contour points to save memory
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # ====================================
        # STEP 4: Process contours and find the ball
        # ====================================
        ball_detected = False  # Flag to track if we found a valid ball
        current_x = None
        current_y = None
        current_radius = None
        
        if len(contours) > 0:
            # Sort contours by area (largest first) and check each one
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            # Variable to store the best candidate
            best_candidate = None
            best_score = 0
            
            # Check each contour to find one that looks like a ball
            for contour in contours:
                # Calculate the area of the contour
                area = cv2.contourArea(contour)
                
                # Skip if too small (noise) or too large (wall/reflection)
                if area < MIN_BALL_AREA or area > MAX_BALL_AREA:
                    continue
                
                # Calculate circularity to check if it's round like a ball
                # Formula: circularity = 4π * area / perimeter²
                # Perfect circle = 1.0, square ≈ 0.785, random shape < 0.7
                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                
                # Only accept circular objects (balls are round!)
                if circularity < MIN_CIRCULARITY:
                    continue
                
                # Get position of this candidate
                (x, y), radius = cv2.minEnclosingCircle(contour)
                
                # If we have a previous position, prefer candidates close to it
                # This prevents jumping between different white objects
                score = circularity  # Base score is circularity
                
                if prev_x is not None and prev_y is not None:
                    # Calculate distance from previous position
                    distance = np.sqrt((x - prev_x)**2 + (y - prev_y)**2)
                    
                    # Skip if jump is too large (likely a different object)
                    if distance > MAX_JUMP_DISTANCE:
                        continue
                    
                    # Bonus score for being close to previous position
                    # Closer = higher score (max bonus = 0.5)
                    proximity_bonus = 0.5 * (1 - min(distance / MAX_JUMP_DISTANCE, 1))
                    score += proximity_bonus
                
                # Keep track of the best candidate
                if score > best_score:
                    best_score = score
                    best_candidate = {
                        'x': x,
                        'y': y,
                        'radius': radius,
                        'area': area,
                        'circularity': circularity,
                        'contour': contour
                    }
            
            # If we found a good candidate, use it
            if best_candidate is not None:
                ball_detected = True
                current_x = best_candidate['x']
                current_y = best_candidate['y']
                current_radius = best_candidate['radius']
                
                # Apply smoothing to reduce jitter
                # Smoothed position = old_position * (1-SMOOTHING) + new_position * SMOOTHING
                if prev_x is not None:
                    current_x = prev_x * (1 - SMOOTHING) + current_x * SMOOTHING
                    current_y = prev_y * (1 - SMOOTHING) + current_y * SMOOTHING
                    current_radius = prev_radius * (1 - SMOOTHING) + current_radius * SMOOTHING
                
                # Convert to integers for drawing and printing
                center_x = int(current_x)
                center_y = int(current_y)
                radius = int(current_radius)
                
                # Update previous position for next frame
                prev_x = current_x
                prev_y = current_y
                prev_radius = current_radius
                
                # Draw a green circle around the detected ball
                # (frame, center, radius, color_BGR, thickness)
                cv2.circle(frame, (center_x, center_y), radius, (0, 255, 0), 2)
                
                # Draw a small red dot at the center point
                cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                
                # Add text showing coordinates on the frame
                text = f"Ball: ({center_x}, {center_y})"
                cv2.putText(frame, text, (center_x - 50, center_y - radius - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Print coordinates and circularity to console
                print(f"Ball detected at X: {center_x}, Y: {center_y}, Radius: {radius}, "
                      f"Area: {best_candidate['area']:.0f}, Circularity: {best_candidate['circularity']:.2f}")
        
        # If no ball was detected, inform the user
        if not ball_detected:
            # Display "No Ball" message on frame
            cv2.putText(frame, "No ball detected", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # ====================================
        # STEP 5: Display the results
        # ====================================
        # Show the original frame with annotations
        cv2.imshow('Ball Detection', frame)
        
        # Optionally show the mask (useful for debugging)
        # Uncomment the line below to see what the camera sees as "white"
        # cv2.imshow('White Mask', mask)
        
        # ====================================
        # STEP 6: Check for quit command
        # ====================================
        # cv2.waitKey(1) waits 1 millisecond for a key press
        # & 0xFF gets the last 8 bits of the key code
        # ord('q') is the ASCII code for the 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nQuitting program...")
            break
    
    # ====================================
    # CLEANUP
    # ====================================
    # Release the camera resource
    camera.release()
    
    # Close all OpenCV windows
    cv2.destroyAllWindows()
    
    print("Camera released. Program ended successfully.")


# ============================================
# PROGRAM ENTRY POINT
# ============================================
# This ensures main() only runs when the script is executed directly
# (not when imported as a module)
if __name__ == "__main__":
    main()