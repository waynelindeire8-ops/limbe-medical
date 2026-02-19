#!/usr/bin/env python3
"""
GUI Launcher for Limbe Medical Clinic - Hospital Management System
Initializes the Tkinter interface and displays the main window.
"""

import tkinter as tk
import sys
import os

# Ensure the project root is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import HospitalGUI

def main():
    root = tk.Tk()
    
    # Set window icon if available (optional)
    # try:
    #     root.iconbitmap('assets/icons/hospital.ico')
    # except:
    #     pass
        
    app = HospitalGUI(root)
    
    # Center the window on screen
    window_width = 1024
    window_height = 768
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    center_x = int(screen_width/2 - window_width/2)
    center_y = int(screen_height/2 - window_height/2)
    
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()
