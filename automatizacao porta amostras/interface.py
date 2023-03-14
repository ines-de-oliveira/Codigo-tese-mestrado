import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import serial
import time
import threading
import sys
import tkinter.font as font
from PIL import ImageTk, Image
import numpy as np

####################################### GLOBAL VARIABLES ###########################################

#Linear feedthrough
mm_per_step =  0.0003175 #steps_per_mm = 3150  (=1.000125 mm)

#Rotatory platform
degrees_per_step = 0.0018008 #steps_per_degree = 555.3

#Other variables
last_position = [0.00, 0.00] # Last position of the system:
                             # last_position[0] = z and last_position[1] = theta

############################################ ARDUINO ###############################################

arduino = serial.Serial('COM4', 115200) # Connect to arduino

def Steps(steps_x, dir_x, steps_y, dir_y):
    """Transmit step sequence to arduino: dir_x/steps_x/dir_y/steps_y/*"""    
    
    info = [steps_x, dir_x, steps_y, dir_y] 

    print(info) # CHECK
    
    arduino.write((str(dir_x) + "/"
                 + str(steps_x) + "/" 
                 + str(dir_y) + "/"
                 + str(steps_y) + "/"
                 + "*").encode())
       
    return info

################################### READ/WRITE LastPos.txt file ####################################

def read_last_position():
    """Read the information on LastPos.txt file and save it to data."""

    with open('LastPos.txt', "r") as f:
        global data
        data = f.readlines()
        last_position[0] = float(data[1].strip("\n").strip("z: "))
        last_position[1] = float(data[2].strip("\n").strip("theta: "))

def write_last_position():
    """Write the updated last position in LastPos.txt file."""

    with open('LastPos.txt', 'w') as f:
        data[1] = str("z: ") + str(round(last_position[0],6)) + "\n" 
        data[2] = str("theta: ") + str(round(last_position[1],6)) + "\n"
        f.writelines(data)

########################################### INTERFACE ##############################################

class Interface(tk.Tk): # Inherit methods of tk.Tk
    # Create the window "Interface". This window will be the container of all interface frames.

    read_last_position() # From LastPos.txt
    print("Last position: z = %s mm, theta = %s deg." % (last_position[0], last_position[1])) #CHECK

    def __init__(self):
        tk.Tk.__init__(self)
        
        # Configuration of the interface window
        self.resizable(False, False) # Window size can't be changed
        self.title("Sample-holder contoller")
        
        self.frame = None
        self.switch_frame(Samples) # Switch to the first frame

      
    def switch_frame(self, frame_class):
        """Destroys the current frame and replaces it with a new one."""
        
        new_frame = frame_class(self)
        if self.frame is not None:
            self.frame.destroy()
        self.frame = new_frame
        self.frame.pack(fill="both", expand=True)

    def on_closing(self):
        """Creates a window to ask the user if he wants to quit.
        It is activated when the user clicks the cancel button."""

        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            arduino.write("s".encode()) # send the char "s" to arduino so it stops the steps loop
            Steps(0,0,0,0) # send 0/0/0/0/* to arduino to set all directions to 0
            write_last_position() # write the last position in the LastPos.txt file
            self.destroy() # Destroy main window, i.e., destroy the app
            arduino.close() # End communication with arduino

class Samples(tk.Frame):
    #Create the frame "Samples". In this frame the user specifices
    #the label and position of the samples to be analyzed.

    #Class variables
    nr_samples = 1 # nr of samples
    label = {} # labels dictionary {sample nr: label}
    z = {} # z coordenates dictionary {sample nr: z}
    theta = {} # theta coordenates dictionary {sample nr: theta}
    samples = [label, z, theta] # list with all info
    
    def __init__(self, parent):
        tk.Frame.__init__(self, parent) # class Interface is the parent

        #parent.geometry("430x400") # resize Interface window

        ####################################### SUB FRAMES #########################################
        
        # Create top buttons area
        self.buttons_area = tk.Frame(self)
        self.buttons_area.pack(side="top", fill="x", padx=2, pady=4)

        # Define main area
        self.input_area = tk.LabelFrame(self, text="Samples")
        self.input_area.pack(side="left", padx=3, pady=3)

        # Define scrollable area to put samples' info
        self.main_frame = tk.LabelFrame(self.input_area, borderwidth=0, bordercolor=None)
        self.main_frame.pack(side="left", ipadx=3, ipady=3)
        self.my_canvas = tk.Canvas(self.main_frame, height=400, width=400)
        self.my_canvas.pack(side="left", fill="x")
        # Add a scrollbar to the canvas
        self.my_scrollbar = tk.Scrollbar(self.main_frame, orient="vertical",
                                         command=self.my_canvas.yview)
        self.my_scrollbar.pack(side="right", fill="y")
        # Configure the canvas
        self.my_canvas.configure(yscrollcommand=self.my_scrollbar.set)
        self.my_canvas.bind('<Configure>', lambda e: 
                            self.my_canvas.configure(scrollregion = self.my_canvas.bbox("all")))
        # Create another frame inside the canvas
        self.second_frame = tk.Frame(self.my_canvas)
        # Add that new frame to a window in the canvas
        self.my_canvas.create_window((0, 0), window=self.second_frame, anchor="nw")

        # Add and delete sample buttons area
        self.side_area = tk.LabelFrame(self, borderwidth=0, bordercolor=None)
        self.side_area.pack(side="right", ipadx=3, ipady=3, fill="both")

        ######################################### BUTTONS ##########################################

        #Create Start button
        self.btn_start = tk.Button(self.side_area, text = "OK", background="light blue", 
                                   activebackground="dark green",
                                   command = lambda: self.save(parent))
        self.btn_start.pack(side="bottom", padx=4, pady=3)

        #Create Import button
        self.btn_import = tk.Button(self.buttons_area, text = "Import",
                                    command = lambda: self.import_from_file())
        self.btn_import.pack(side="left", padx=4, pady=3)

        #Create Save sample button
        self.btn_save = tk.Button(self.buttons_area, text = "Save", width=3,
                                  command = lambda: self.save_to_file())
        self.btn_save.pack(side="left", padx=4, pady=3)

        #Create "Standard 10" button
        self.btn_center_position_10 = tk.Button(self.buttons_area, text = "Standard 10", command = 
                                                lambda: self.fill_with_center_positions_10())
        self.btn_center_position_10.pack(side="left", padx=4, pady=3)

        #Create "Standard 16" button
        self.btn_center_position_16 = tk.Button(self.buttons_area, text = "Standard 16", command =
                                                lambda: self.fill_with_center_positions_16())
        self.btn_center_position_16.pack(side="left", padx=4, pady=3)

        #Create "Standard 10" button
        self.info = tk.Button(self.buttons_area, text = "Info",
                              command = lambda: self.show_image_with_directions())
        self.info.pack(side="left", padx=4, pady=3)

        #Create add new sample button
        self.btn_add_sample = tk.Button(self.side_area, text = "+", width=3,
                                        command = lambda: self.add_sample())
        self.btn_add_sample.pack(side="top", padx=4, pady=10)

        #Create delete sample button
        self.btn_delete = tk.Button(self.side_area, text = "-", width=3,
                                    command = lambda: self.erase_sample())
        self.btn_delete.pack(side="top", padx=4, pady=0)

        ######################################### LABELS ###########################################

        #Define labels permanent labels
        tk.Label(self.second_frame, text="Nr.").grid(row=0, column=0)
        tk.Label(self.second_frame, text="label (optional)").grid(row=0, column=1)
        tk.Label(self.second_frame, text="z in mm").grid(row=0, column=2)
        tk.Label(self.second_frame, text= u"\u03B8 in \N{DEGREE SIGN}").grid(row=0, column=3)
        
        ######################################### ENTRIES ##########################################

        # Define lists to store user entires
        self.ent_label = []
        self.ent_z = []
        self.ent_theta = []
        self.ent = [self.ent_label, self.ent_z, self.ent_theta]
        
        # Define list to store the nr of sample
        self.lbl_nr = []
        
        # Define the 1st sample fields
        self.nr_samples = 1
        self.lbl_nr.append(tk.Label(self.second_frame, text="%2d: " % self.nr_samples))
        self.lbl_nr[0].grid(row=1, column=0)
        self.ent[0].append(tk.Entry(self.second_frame))
        self.ent[1].append(tk.Entry(self.second_frame))
        self.ent[2].append(tk.Entry(self.second_frame))
        self.ent[0][0].grid(row=self.nr_samples, column=1)
        self.ent[1][0].grid(row=self.nr_samples, column=2)
        self.ent[2][0].grid(row=self.nr_samples, column=3)
    
    ############################## FUNCTIONS ACTIVATED BY THE BUTTONS ##############################

    def save(self, parent):
        """Save the samples information (label, z and theta) to the Sample class variables. 
        This way they can be accessed by other classes such as "Move", the next frame."""

        self.check_entry_filling()
        
        # Store values of label, z and theta
        for i_list in range(0, 3):
            for i, e in enumerate(self.ent[i_list]):
                if i_list == 1 or i_list == 2:
                    Samples.samples[i_list][i+1] = float(e.get())
                else:
                    if(e.get() == ""):
                        Samples.samples[i_list][i+1] = "-" # If no label is given the label is "-" 
                    else:
                        Samples.samples[i_list][i+1] = e.get()                        

        print(f"List of samples label: {Samples.samples[0]}")  # CHECK
        print(f"List of samples z: {Samples.samples[1]}")      # CHECK
        print(f"List of samples theta: {Samples.samples[2]}")  # CHECK
        print("Number of samples: %s" % (Samples.nr_samples))  # CHECK

        parent.switch_frame(Move) # Switch to next frame

    def import_from_file(self):
        """Import the sample information from a .txt file such as the file "ExampleData.txt.
        The entry fields will be automatically filled with the information from the file."""

        info = []
        file_name = filedialog.askopenfilename()

        if file_name == '':
            return None

        with open(file_name, 'r') as f:
            f.readline()
            for line in f.readlines():
                info.append(line.split(","))
            print(info) # CHECK

            # Clear all current entry fields
            for i in range(0, self.nr_samples): 
                self.ent[0][i].delete(0, tk.END) 
                self.ent[1][i].delete(0, tk.END)
                self.ent[2][i].delete(0, tk.END)
            
            # Create new entry fields if the file has more samples than current number
            # of samples. Fill the entries with the info in the file.
            if self.nr_samples < len(info):
                print("Sample nr: " + str(self.nr_samples)) # CHECK
                print("Lenght of info: " + str(len(info))) # CHECK
                for i in range(0, len(info) - self.nr_samples):
                    self.nr_samples = self.nr_samples + 1
                    self.lbl_nr.append(tk.Label(self.second_frame, text="%2d: " % self.nr_samples))
                    self.lbl_nr[self.nr_samples-1].grid(row=self.nr_samples, column=0)
                    self.ent[0].append(tk.Entry(self.second_frame))
                    self.ent[1].append(tk.Entry(self.second_frame))
                    self.ent[2].append(tk.Entry(self.second_frame))
                    self.ent[0][self.nr_samples-1].grid(row=self.nr_samples, column=1)
                    self.ent[1][self.nr_samples-1].grid(row=self.nr_samples, column=2)
                    self.ent[2][self.nr_samples-1].grid(row=self.nr_samples, column=3)
                    print(i) # CHECK

            Samples.nr_samples = self.nr_samples
            
            for i in range(0, len(info)):
                self.ent[0][i].delete(0, tk.END)
                self.ent[0][i].insert(0, info[i][1])
                self.ent[1][i].delete(0, tk.END)
                self.ent[1][i].insert(0, info[i][2])
                self.ent[2][i].delete(0, tk.END)
                self.ent[2][i].insert(0, info[i][3])
    
    def save_to_file(self):
        """Save the information in the entry fields to a .txt file. This file will have the same
        structure as the ExampleData.txt file and it can be imported to the program."""

        self.check_entry_filling()

        f = filedialog.asksaveasfile(mode='w', defaultextension=".txt")
        if f != None:

            f.write("Nr\tLabel\tz(mm)\ttheta(degrees)\n")
            for i in range(0, Samples.nr_samples):
                if self.ent[0][i].get() == "":
                    self.ent[0][i].insert(0, "-") 
                f.write('%s\t%s\t%s\t%s\n' % (i+1, self.ent[0][i].get(), self.ent[1][i].get(),
                        self.ent[2][i].get()))
                self.ent[0][i].insert(0, "") 

    def erase_sample(self):
        """Erase last sample entry fields."""

        if self.nr_samples > 1:
            self.nr_samples = self.nr_samples - 1
            Samples.nr_samples = self.nr_samples
            print(self.nr_samples)
       
            self.lbl_nr[-1].destroy() 
            self.lbl_nr.pop(-1)
        
            for i_list in range(0, 3):
                self.ent[i_list][-1].destroy()
                self.ent[i_list].pop(-1)

        self.my_canvas.configure(scrollregion=self.my_canvas.bbox("all"))

    def add_sample(self):
        """Add a new sample entry fields after the last sample entry fields."""

        self.nr_samples = self.nr_samples + 1
        Samples.nr_samples = self.nr_samples
        print(self.nr_samples)

        self.lbl_nr.append(tk.Label(self.second_frame, text="%2d: " % (self.nr_samples)))       
        self.ent[0].append(tk.Entry(self.second_frame))
        self.ent[1].append(tk.Entry(self.second_frame))
        self.ent[2].append(tk.Entry(self.second_frame))
        
        self.lbl_nr[self.nr_samples-1].grid(row=self.nr_samples, column=0)
        self.ent[0][self.nr_samples-1].grid(row=self.nr_samples, column=1)
        self.ent[1][self.nr_samples-1].grid(row=self.nr_samples, column=2)
        self.ent[2][self.nr_samples-1].grid(row=self.nr_samples, column=3)
        
        self.my_canvas.configure(scrollregion=self.my_canvas.bbox("all"))

    def fill_with_center_positions_10(self):
        """Fill the z and theta fields of the first 15 samples with the coordenates
        of the position of the centers of 30mmx10mm standard sample pieces."""

        if len(self.ent[1]) > 15:
            nr = 15
        else:
            nr = len(self.ent[1])

        for i in range(0, nr):

            if(i == 0):
                z = 5
                theta = 0
            elif(i % 4 == 0):
                z = 5
                theta += 120
            else:
                z += 10

            self.ent[1][i].delete(0, tk.END)
            self.ent[1][i].insert(0, str(z))
            self.ent[2][i].delete(0, tk.END)
            self.ent[2][i].insert(0, str(theta))

    def fill_with_center_positions_16(self):
        """Fill the z and theta fields of the first 12 samples with the coordenates
        of the position of the centers of 30mmx16mm standard sample pieces."""

        if len(self.ent[1]) > 12:
            nr = 12
        else:
            nr = len(self.ent[1])

        for i in range(0, nr):

            if(i == 0):
                z = 8
                theta = 0
            elif(i % 4 == 0):
                z = 8
                theta += 120
            else:
                z += 16

            self.ent[1][i].delete(0, tk.END)
            self.ent[1][i].insert(0, str(z))
            self.ent[2][i].delete(0, tk.END)
            self.ent[2][i].insert(0, str(theta))

    def show_image_with_directions(self):
        """Creates a window where it shows an image with the direction of rotation of the
        sample-holder and the scale of vertical movement."""

        self.info_wd = tk.Toplevel(self)
        self.info_wd.lift()
        
        # Create an object of tkinter ImageTk
        self.img = ImageTk.PhotoImage(Image.open("porta_amostras.jpg").resize((400,400)))
        # Create a label to display the image
        self.label = tk.Label(self.info_wd, image = self.img)
        self.label.pack()

    ###################################### AUXILIAR FUNCTIONS ######################################

    def check_entry_filling(self):
        """Check if the values of z and theta are numbers and if so get those entries."""

        for i_list in range(1, 3):
            for i, e in enumerate(self.ent[i_list]):
                try:
                    float(e.get()) # z entry
                    float(e.get()) # theta entry
                except ValueError: 
                    messagebox.showerror("Error: Invalid entry",
                                         "Please make sure all z and theta" +
                                         "fields are filled with numbers.")
                    return None # Exit the save function

class Move(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        parent.geometry("260x300")
        parent.protocol("WM_DELETE_WINDOW", parent.on_closing)   

        self.top_area = tk.Frame(self)
        self.top_area.pack(side="top", fill="x")

        self.btn_samples_info = tk.Button(self.top_area, text="Info",
                                          command = lambda: self.open_samples_info_window())
        self.btn_samples_info.pack(side="left", padx=2, pady=2)

        self.move_area = tk.LabelFrame(self, text="Move")
        self.move_area.pack(side="top", expand=True, fill="both")

        #Define main area
        self.sample_area = tk.Frame(self.move_area)
        self.sample_area.pack(side="top", expand=True)

        self.nr = 0 #sample number

        self.btn_previous = tk.Button(self.sample_area, text="<",
                                      command = lambda: self.go_to_previous_sample()) 
        self.btn_previous.grid(row=0, column=0, padx=2, rowspan=2)

        self.current_sample_area = tk.Frame(self.sample_area)
        self.current_sample_area.grid(row=0, column=1, padx=4, pady=2)
        tk.Label(self.current_sample_area, text="Sample number: ").grid(row=0, column=0)
        self.lbl_nr = tk.Label(self.current_sample_area, text=self.nr)
        self.lbl_nr.grid(row=0, column=1)
        tk.Label(self.current_sample_area, text="of").grid(row=0, column=2)
        tk.Label(self.current_sample_area, text=Samples.nr_samples).grid(row=0, column=3)
        self.current_label_area = tk.Frame(self.sample_area)
        self.current_label_area.grid(row=1, column=1, padx=4, pady=2)
        self.lbl_label = tk.Label(self.current_label_area, text="-")
        self.lbl_label.grid(row=0, column=1, rowspan=3)

        self.btn_next = tk.Button(self.sample_area, text=">",
                                  command = lambda: self.go_to_next_sample()) 
        self.btn_next.grid(row=0, column=2, padx=2, rowspan=2)

        #z and theta coordinates monitor area
        self.coordinates_area = tk.LabelFrame(self, text="Current position")
        self.coordinates_area.pack(fill="both", expand=True, side="top")
        
        self.coordinates = tk.Frame(self.coordinates_area)
        self.coordinates.pack(anchor='c', expand=True)

        # z coordenate monitor
        self.z_coordinate = tk.Frame(self.coordinates)
        self.z_coordinate.pack(side='left')
        tk.Label(self.z_coordinate, text="z:").grid(row=0, column=0, padx = 2)
        self.lbl_z = tk.Label(self.z_coordinate, text="{:.1f}".format(last_position[0]),
                              relief="ridge", bg="black", fg="yellow", font=("Arial", 15))
        if(last_position[0] == 0):
            self.lbl_z.config(text="0.0")
        self.lbl_z.grid(row=0, column=1)

        # theta coordenate monitor
        self.theta_coordinate = tk.Frame(self.coordinates)
        self.theta_coordinate.pack(side='left', padx=10)
        tk.Label(self.theta_coordinate, text="\u03b8:").grid(row=0, column=2, padx = 2)
        self.lbl_theta = tk.Label(self.theta_coordinate, text="{:.1f}".format(last_position[1]),
                                  relief="ridge", bg="black", fg="yellow", font=("Arial", 15))
        if(last_position[1] == 0):
            self.lbl_theta.config(text="0.0")
        self.lbl_theta.grid(row=0, column=3)

        #go to area
        self.coordinates_area_2 = tk.LabelFrame(self, text="Go to")
        self.coordinates_area_2.pack(fill="both", expand=True, side="top")
        
        self.coordinates_2 = tk.Frame(self.coordinates_area_2)
        self.coordinates_2.pack(expand=True)

        tk.Label(self.coordinates_2, text="z:").grid(row=0, column=0, pady=4)
        self.ent_z_2 = tk.Entry(self.coordinates_2)
        self.ent_z_2.grid(row=0, column=1, pady=4)
        tk.Label(self.coordinates_2, text="mm").grid(row=0, column=2, pady=4)

        tk.Label(self.coordinates_2, text="\u03b8:").grid(row=1, column=0, pady=4)
        self.ent_theta_2 = tk.Entry(self.coordinates_2)
        self.ent_theta_2.grid(row=1, column=1, pady=4)
        tk.Label(self.coordinates_2, text="\N{DEGREE SIGN}").grid(row=1, column=2,
                                                                  pady=4, sticky='w')

        self.btn_go = tk.Button(self.coordinates_2, text="Go", command = lambda: self.go_to()) 
        self.btn_go.grid(row=0, column=3, padx=6, rowspan=2)

        self.background(self.receive_from_arduino) # Begin thread

    ############################ FUNCTIONS ACTIVATED BY THE BUTTONS ################################

    def open_samples_info_window(self):
        """Creates a window with info about each mode.""" 
        
        self.info_wd = tk.Toplevel(self)
        self.info_wd.grab_set()
        self.info_wd.lift()
        self.info_wd.resizable(False, False) # Window size can't be changed

        tk.Label(self.info_wd, text="Nr").grid(row=0, column=0)
        tk.Label(self.info_wd, text="Label").grid(row=0, column=1)
        tk.Label(self.info_wd, text="z (mm)").grid(row=0, column=2)
        tk.Label(self.info_wd, text="\u03b8 (degrees)").grid(row=0, column=3)

        for i in range(0, Samples.nr_samples):
            tk.Label(self.info_wd, text=str(i+1)).grid(row=i+1, column=0)
            tk.Label(self.info_wd, text=Samples.samples[0][i+1]).grid(row=i+1, column=1)
            tk.Label(self.info_wd, text=str(Samples.samples[1][i+1])).grid(row=i+1, column=2)
            tk.Label(self.info_wd, text=str(Samples.samples[2][i+1])).grid(row=i+1, column=3)

    def go_to_previous_sample(self):
        """Go to previous sample: move the sample-holder so that the previous sample is positioned
        in the beam line and actualize lbl_nr and lbl_label to values of the previous sample."""

        if self.nr > 1:

            # Get sequence of steps and direction to transmit to motors
            self.generate_motor_steps(last_position[0], float(Samples.samples[1][self.nr-1]),
                                      last_position[1], float(Samples.samples[2][self.nr-1]))
            
            # Actualize fields
            self.nr -= 1
            self.lbl_nr.config(text=self.nr)
            self.lbl_label.config(text=Samples.samples[0][self.nr])         

            self.btn_previous.config(state = 'disabled')
            self.btn_next.config(state = 'disabled') 
            self.btn_go.config(state = 'disabled')

    def go_to_next_sample(self):
        """Go to next sample: move the samples-holder so that the next sample is positioned
        in the beam line and actualize lbl_nr and lbl_label to values of next sample."""
                
        if self.nr < Samples.nr_samples:     
            
            #Get sequence of steps and direction to transmit to motors
            self.generate_motor_steps(last_position[0], float(Samples.samples[1][self.nr+1]),
                                      last_position[1], float(Samples.samples[2][self.nr+1]))
    
            #Actualize fields
            self.nr += 1
            self.lbl_nr.config(text=self.nr)
            self.lbl_label.config(text=Samples.samples[0][self.nr]) 

            self.btn_previous.config(state = 'disabled')
            self.btn_next.config(state = 'disabled') 
            self.btn_go.config(state = 'disabled')

    def go_to(self):
        """Go to a new position entered by the user."""
        
        # Store values of z and theta entries
        try:
            next_z = float(self.ent_z_2.get())
            next_theta = float(self.ent_theta_2.get())
        except ValueError: 
            messagebox.showerror("Error: Invalid entry")
            return None # Exit the go_to function

        # Get sequence of steps and direction to transmit to motors
        self.generate_motor_steps(last_position[0], next_z,
                                  last_position[1], next_theta)

        if Samples.nr_samples == 1:
            self.nr = 0

        self.btn_previous.config(state = 'disabled')
        self.btn_next.config(state = 'disabled') 
        self.btn_go.config(state = 'disabled')

    ##################################### AUXILIAR FUNCTIONS #######################################

    def generate_motor_steps(self, current_z, next_z, current_theta, next_theta):
        """Define motor steps to move to next sample"""

        steps_x = round(abs(next_z - current_z) / mm_per_step)
        steps_y = round(abs(next_theta - current_theta) / degrees_per_step)
        print("motor steps y: " + str(steps_y * degrees_per_step))
            
        if(current_z < next_z):
            dir_x = 1
        else:
            dir_x = 0

        if(current_theta < next_theta):
            dir_y = 0
        else:
            dir_y = 1

        Steps(steps_x, dir_x, steps_y, dir_y)

        print("VERTICAL MOVEMENT ------------------------------")
        print("Inicial position: %s" % (current_z))                 # CHECK
        print("Final position: %s" % (next_z))                      # CHECK
        print("Distance: %s" % (abs(next_z - current_z)))           # CHECK
        print("ROTATIONAL MOVEMENT ------------------------------")
        print("Inicial position: %s" % (current_theta))             # CHECK
        print("Final position: %s" % (next_theta))                  # CHECK
        print("Distance: %s" % (abs(next_theta - current_theta)))   # CHECK

    ################################## POSITION MONITOR FUNCTIONS ##################################

    def background(self, func):
        global th
        th = threading.Thread(target=func)
        th.daemon = True # Daemon threads run in the background and end when the program is exited
        th.start()

    def receive_from_arduino(self):
        """Recieves the information sent to arduino's Serial Monitor and controls the z and theta
        position monitors in the interface."""

        rotate = False
        clockwise = False
        down = True

        while(True): # Endless loop activated by Daemon thread

            if(arduino.inWaiting() > 0):

                rc = arduino.readline().decode("utf-8").strip('\n').strip('\r')

                if(rc == 'v'):
                    rotate = False
                    continue

                if(rc == 'r'):
                    rotate = True
                    continue

                if(rc == 'd'):
                    down = True
                    continue

                if(rc == 'u'):
                    down = False
                    continue

                if(rc == 'n'):
                    positive = False
                    continue

                if(rc == 'p'):
                    positive = True
                    continue

                if(rc == 'f'):
                    self.btn_previous.config(state = 'normal')
                    self.btn_next.config(state = 'normal')
                    self.btn_go.config(state = 'normal')
                    continue

                if(rotate == False):
                    if(down):
                        last_position[0] = last_position[0] + (mm_per_step * int(rc)) 
                        if(round(last_position[0],1) == 0):
                            self.lbl_z.config(text = "0.0")
                        else:
                            self.lbl_z.config(text = "{:.1f}".format(last_position[0]))

                    if(down == False):
                        last_position[0] = last_position[0] - (mm_per_step * int(rc))
                        if(round(last_position[0],1) == 0):
                            self.lbl_z.config(text = "0.0")
                        else:
                            self.lbl_z.config(text = "{:.1f}".format(last_position[0]))
                
                if(rotate):
                    if(positive):
                        last_position[1] = last_position[1] + (degrees_per_step * int(rc))
                        #print(last_position[1])
                        if(round(last_position[1],1) == 0):
                            self.lbl_theta.config(text = "0.0")
                        elif(round(last_position[1],1) == 360):
                            last_position[1] = 0.0
                        else:
                            self.lbl_theta.config(text = "{:.1f}".format(last_position[1]))

                    if(positive == False):
                        last_position[1] = last_position[1] - (degrees_per_step * int(rc))
                        #print(last_position[1])
                        if(round(last_position[1],1) == 0):
                            self.lbl_theta.config(text = "0.0")
                        elif(round(last_position[1],1) == 360):
                            last_position[1] = 0.0
                        else:
                            self.lbl_theta.config(text = "{:.1f}".format(last_position[1]))

                if(round(last_position[0],1) == 0):
                    self.lbl_z.config(text = "0.0")
                if(round(last_position[1],1) == 0):
                    self.lbl_theta.config(text = "0.0")

if __name__ == "__main__":
    app = Interface()
    app.mainloop()