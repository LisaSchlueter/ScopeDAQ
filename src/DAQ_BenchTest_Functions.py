## packages
import shutil
import pyvisa
import csv
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import time
import struct 
import os as os
from datetime import datetime
from os.path import join
import h5py

## initializing resource manager for the electronics
rm = pyvisa.ResourceManager('@py')

## gives me pulser
def init_devices():
    ## connecting to pulse generator
    pulser = rm.open_resource('TCPIP0::169.254.7.108')
    # print(pulser.query('*IDN?'))

    ## connecting to the oscilloscope (essential for both detector tests and bench tests)
    scope = rm.open_resource('TCPIP0::169.254.7.109')
    # print(scope.query('*IDN?')) ## prints make and model of oscilloscope to verify connection

    return pulser, scope

## configures power supply to desired format
def configure_power_supply():
    channel = 3
    voltage = 2.8
    current_limit = 50
    
    # Select the channel
    supply.write(f'INST:NSEL {channel}')
    
    # Set voltage
    supply.write(f'VOLT {voltage}')
    
    # Set current limit
    supply.write(f'CURR {current_limit}')
    
    # Turn on the output
    supply.write('OUTP ON')
    
    # Read back current
    current = float(supply.query('MEAS:CURR?'))
    
    # Check if the current is within the desired range
    if .005 <= current <= .010:
        print(f'Current is within range: {current} A')
    else:
        print(f'Current is out of range: {current} A')


## changes voltage of pulser
def pulser_v(pulser, voltage): ## parameter in units of volts
    return pulser.write(f'C1:BSWV AMP, {voltage}') ## sets voltage of pulse generator to desired value

## changes vertical (voltage) scaling of oscilloscope, needed for optimizing resolution at diff voltages for bench test
def set_vert_scale(scope,channel, scale):
    scope.write(f':CH{channel}:SCALE {scale}')

## changes time scale of oscilloscope
def set_horizontal_scale(scale):
    scope.write(f':HOR:MAIN:SCALE {scale}')

## gets measurement from any of the measurement channels on oscilloscope
def get_measurement(scope, measurement_channel):
    # Query the value of the specified measurement channel
    measurement = scope.query(f':MEASU:MEAS{measurement_channel}:VALue?')
    return float(measurement)


## make sure to adjust which channel you want to use for the trigger
def set_trigger(scope, trigger_level):
    # Construct the SCPI command to set the trigger source
    scope.write('TRIGger:A:EDGE:SOURce CH1') ## makes sure the trigger is set to channel 1
        
    # Construct the SCPI command to set the trigger level
    scope.write(f'TRIGger:A:LEVel:CH1 {trigger_level}') ## set trigger as low as possible 



# getting waveform data from oscilloscope for a given channel
def get_waveform_data(channel, scope):
    # Select the channel
    scope.write(f':DATA:SOURCE CH{channel}')
    scope.write(f':WFMOutpre:BYT_Nr 2')
    scope.write(f':WFMOutpre:ENCdg BINARY')
    
    scope.write(':CURVE?')
    raw_data = scope.read_raw() # Use read_raw() to get binary data directly
    raw_data = raw_data[8:] 
    raw_data = raw_data[:-1]
    data = np.frombuffer(raw_data, dtype='>i2') 
    # print("First 10 data points:", data[:10])
    # print("Last 20 data points:", data[-20:])

# Horizontal scale settings to reconstruct time data
    x_increment = float(scope.query('WFMOutpre:XINcr?'))
    x_zero = float(scope.query('WFMOutpre:XZEro?'))
    x_offset = float(scope.query('WFMOutpre:PT_OFF?'))
    # print(x_increment)

# Get vertical scale settings to reconstruct voltage data
    y_multiplier = float(scope.query('WFMOutpre:YMUlt?'))
    y_offset = float(scope.query('WFMOutpre:YOFf?'))
    y_zero = float(scope.query('WFMOutpre:YZEro?'))
    # print(y_multiplier)
    

# Reconstruct time and voltage data
    time_data = x_zero + (np.arange(len(data)) - x_offset) * x_increment
    voltage_data = y_zero + (data - y_offset)*y_multiplier

    return time_data, voltage_data




def correct_y_scaling(scope, wave_amplitude):
    if 0.0 <= wave_amplitude < .003: ## 0 to 3 mV
        set_vert_scale(scope, 1, .0005)
        set_vert_scale(scope, 4, .0005)
        set_trigger(scope, 0.00056)
    elif .003 <= wave_amplitude < .007: ## 3 to 7 mV
        set_vert_scale(scope, 1, .0008)
        set_vert_scale(scope, 4, .0008)
    elif .007 <= wave_amplitude < .013: ## 7 to 13 mV
        set_vert_scale(scope, 1, .0016)
        set_vert_scale(scope, 4, .0016)
        set_trigger(scope, 0.00096)
    elif .013 <= wave_amplitude < .022: ## 13 to 22 mV
        set_vert_scale(scope, 1, .0024)
        set_vert_scale(scope, 4, .0024)
    elif .022 <= wave_amplitude < .032: ## 22 to 32 mV
        set_vert_scale(scope, 1, .0036)
        set_vert_scale(scope, 4, .0036)
    elif .032 <= wave_amplitude < .050: ##  32 to 50 mV
        set_vert_scale(scope, 1, .0055)
        set_vert_scale(scope, 4, .0055)
        set_trigger(scope, 0.0015)
    elif .050 <= wave_amplitude < .070: ## 50 to 70 mV  
        set_vert_scale(scope, 1, .0075)
        set_vert_scale(scope, 4, .0075)
        set_trigger(scope, 0.0025)
    elif .070 <= wave_amplitude < .110: ## 70 to 110 mV 
        set_vert_scale(scope, 1, .014)
        set_vert_scale(scope, 4, .014)
    elif .110 <= wave_amplitude < .170: ## 110 to 170 mV    
        set_vert_scale(scope, 1, .02)
        set_vert_scale(scope, 4, .02)
        set_trigger(scope, .031)
    elif .170 <= wave_amplitude < .250: ## 170 to 250 mV
        set_vert_scale(scope, 1, .03)
        set_vert_scale(scope, 4, .03)
    elif .250 <= wave_amplitude < .350: ## 250 to 350 mV
        set_vert_scale(scope, 1, .04)
        set_vert_scale(scope, 4, .04)
        set_trigger(scope, .05)
    elif .350 <= wave_amplitude < .520: ## 350 to 520 mV
        set_vert_scale(scope, 1, .06)
        set_vert_scale(scope, 4, .06)
    elif .520 <= wave_amplitude < .800: ## 520 to 800 mV
        set_vert_scale(scope, 1, .09)
        set_vert_scale(scope, 4, .09)
        set_trigger(scope, .160)
    elif .800 <= wave_amplitude < 1: ## 800 mV to 1 V
        set_vert_scale(scope, 1, .12)
        set_vert_scale(scope, 4, .12)
        set_trigger(scope, .270)
    elif 1 <= wave_amplitude < 1.4: ## 1 to 1.4 V
        set_vert_scale(scope, 1, .16)
        set_vert_scale(scope, 4, .16)
        set_trigger(scope, .400)


## creates folder for .csv files to be inserted into. The folder is automatically created in this directory
## in the folder I have called ./Data.
## GIVE THE FOLDER A NAME IN THE ALGORITHMS
def create_folder(base_dir='./Data', name = None, run_type = None, n_runs = None, subfolder = None):
    # If a subfolder is specified, use it directly without generating a new folder name
    if subfolder:
        folder_path = os.path.join(base_dir, subfolder)
    else:
        # Generate a folder name if 'name' is not provided and 'subfolder' is not specified
        if name is None:
            name = f'ASIC_data_{int(time.time())}'
        else:
            current_date = datetime.datetime.now().strftime('%Y%m%d')
            name = f'{name}_{current_date}'
        folder_path = os.path.join(base_dir, name)
    
    # Create the folder (or subfolder) path
    os.makedirs(folder_path, exist_ok=True)
    # print(f'Folder created: {folder_path}')
    
    ## create a .csv file with important metadata for main data collection folders
    if not subfolder:
        info_filename = 'run_info.csv'
        info_filepath = os.path.join(folder_path, info_filename)
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.datetime.now().strftime('%H:%M:%S')

        with open(info_filepath, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Oscilloscope: TEKTRONIX MSO44B', 'Pulser: TELEDYNE T3AFG500'])
            csvwriter.writerow([f'Date: {current_date}', f'Time: {current_time}'])
            csvwriter.writerow(['Time units: microseconds', 'Voltage units: Volts'])


            if run_type:
                csvwriter.writerow([f'Run type: {run_type}'])

            if n_runs:
                csvwriter.writerow([f'# of iterations at each voltage: {n_runs}'])
    
    return folder_path



## saves ASIC time data, voltage data, pulser voltage data to .csv file as well as other parameters
def save_to_csv(path, time_data, device_voltage_data, pulser_voltage_data, pulser_voltage, asic_voltage, counter = None):
    
    filename = f'ASIC_A{asic_voltage:.3f}V_P{pulser_voltage:.3f}V_{counter:03d}.csv'.replace('.','p',2)  
    fullpath = os.path.join(path, filename)
    
    with open(fullpath, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        
        csvwriter.writerow([f'Pulser Voltage: {pulser_voltage:.3f}V', f'ASIC Peak Voltage: {asic_voltage:.3f}V' ])
        csvwriter.writerow(['Time (s)', 'ASIC Voltage (V)','Pulser Voltage (V)'])  # Header row
        for t, v, q in zip(time_data, device_voltage_data, pulser_voltage_data):
            csvwriter.writerow([t, v, q])
   


## data to write a waveform into an hdf5 file
def write_waveform_to_hdf5(hdf_file, group_name, time_data, voltage_data, run_num):
    """
    Writes waveform data to HDF5 file under the specified group.

    Parameters:
    hdf_file (h5py.File): The open HDF5 file object.
    group_name (str): The name of the group (e.g., voltage level).
    time_data (list or np.array): The time data points.
    voltage_data (list or np.array): The corresponding voltage data points.
    run_num (int): The current run number to name the dataset.
    """
    # Combine the time and voltage data into a 2D array
    waveform_data = np.vstack((time_data, voltage_data)).T
    
    # Create a dataset for the waveform in the specified group
    dataset_name = f"waveform_{run_num:05d}"
    
    # Write the dataset with compression
    hdf_file[group_name].create_dataset(dataset_name, data=waveform_data, compression="gzip")
    
    """Optional print statement for debugging and tracking."""
    # print(f"Waveform {run_num + 1} saved to group {group_name}.")



    ## Function to automatically upload data to google drive






### need to update path based on what laptop you are working on
def save_hdf5_to_drive(hdf_file_path):
    
    
    ## constructing the path to the file you want to upload to the google drive
    source_path = hdf_file_path
    
    ## constructing path to the google drive
    google_drive_path = google_drive_path = r"/Users/ilvuoto/Library/CloudStorage/GoogleDrive-dvbowen@lbl.gov/Shared drives/LEGEND-1000/DATA/BenchTestData"

    ## moving the source file to the google drive
    shutil.copy(source_path, google_drive_path)
    
    # print(f"Copied data file to {google_drive_path}.")
    

### function to write important metadata into each file

def write_hdf5_metadata_osci(hdf_file, channel, scope):    
    ### METADATA
    # hdf_file.attrs['DEVICE_NAME'] = 'LBNL GFET distributed CSA'
    # hdf_file.attrs['DEVICE_VOLTAGE'] = '1.0 V'
    # hdf_file.attrs['V_MID'] = '0.8 V'
    # hdf_file.attrs['POWER_SUPPLY_PARAMETERS'] = ['5V, 3mA and -5V, 3mA']
    # hdf_file.attrs['SCOPE_PARAMETERS'] = ['AC termination, 75 Ohms']
    # hdf_file.attrs['HPGe_LBNL_PPC_BIAS_VOLTAGE'] = ['2 kV']
    scope_group = hdf_file.create_group('oscilloscope')
    
    # scope.write(f':CHANnel{channel}:IMPedance?')
    # input_impedance = scope.query(f':CHANnel{channel}:IMP?')

    # scope.write(f':CHANnel{channel}:COUPling?')
    coupling_mode = scope.query(f':CHANnel{channel}:COUPling?')
    
     # Add to file 
    scope_group.create_dataset('input_impedance', data=input_impedance)
    scope_group.create_dataset('coupling_mode', data=coupling_mode)
    # hdf_file.attrs['INPUT_IMPEDANCE'] = input_impedance
    # hdf_file.attrs['COUPLING_MODE'] = coupling_mode
    
    # if run_type:
    #     hdf_file.attrs['RUN_TYPE'] = run_type


def collect_data_hdf5(scope, pulser, channel, ampl_meas, voltage_array, num_runs, file_name=None, run_title=None, bulk_size = 20):
    """
    Collects waveform data over multiple runs at different voltages and saves them in an HDF5 file.
    
    Parameters:
    voltage_array (list): Array of voltages to test.
    num_runs (int): Number of runs per voltage.
    file_name (str): Name of the HDF5 file.
    run_title (str): Optional title for the run, used to name the group in the HDF5 file.
                     If None, default will be 'ASIC_bench_test_{timestamp}'.
    """
    # Ensure the file is created in the ./Data directory by default
    base_dir = './Data'
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)  # Create the directory if it doesn't exist

    if file_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"ASIC_BenchTest_{timestamp}.hdf5"

    # Build the full path by appending the file name to the ./Data directory
    hdf5_file_path = os.path.join(base_dir, file_name)

    # Generate a default run title with a timestamp if run_title is not provided
    if run_title is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_title = f"ASIC_benchtest_{timestamp}"

    # Open or create the HDF5 file
    with h5py.File(hdf5_file_path, 'a') as hdf_file:

        #create a dataset containing the time data, namely the step size
        t_step = float(scope.query('WFMOutpre:XINcr?'))
        time_data = hdf_file.create_dataset('time_step', data=t_step)
        t_unit = scope.query('WFMOutpre:XUNit?')
        time_data.attrs['unit'] = f'{t_unit}'
        
        # Iterating over each voltage in the voltage array
        for volt in voltage_array:
            # Create a group name for each voltage level
            voltage_group_name = f"PulserVoltage_{volt:.3f}V".replace('.', 'p', 1)

            # Ensure the group is created if it doesn't exist
            if voltage_group_name not in hdf_file:
                hdf_file.create_group(voltage_group_name)

            correct_y_scaling(scope, volt) # guess correct scaling based on voltage
            pulser_v(pulser, volt) # change voltage on pulser
            time.sleep(.5)  # Delay for waveform stabilization
            asic_amplitude = get_measurement(scope, ampl_meas) # get amplitude through ASIC
            correct_y_scaling(scope, asic_amplitude) # properly adjust Y-scaling for ASIC amplitude

            # Collect num_runs waveforms at this voltage
            voltage_waves = []
            for run_num in range(num_runs):
                # Get the waveform data
                _, voltage_wave = get_waveform_data(channel, scope)
                voltage_waves.append(voltage_wave)
                
                # Save in bulk every bulk_size runs
                if (run_num + 1) % bulk_size == 0 or (run_num + 1) == num_runs:
                    dataset_name = f"run_{run_num // bulk_size * bulk_size}_{run_num}"
                    hdf_file[voltage_group_name].create_dataset(dataset_name, data=voltage_waves, compression="gzip")
                    y_unit = scope.query('WFMOutpre:YUNit?')
                    dataset.attrs['y_units'] = f'{y_unit}'
                    voltage_waves = []  # Clear the list after savingum_runs} complete for voltage {volt:.3f}V.")

    save_hdf5_to_drive(hdf5_file_path)
    print(f"Data collection complete. Results saved to {hdf5_file_path}")


