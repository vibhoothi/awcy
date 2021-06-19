from time import sleep
import requests
import os
import subprocess
import scipy.optimize
from bd_rate_report import bdrate
import json
import math
import sys


def return_video_info(task):
    sets = json.load(
        open(
            os.path.join(
                '/home/mindfreeze/awcy/rd_tool',
                "sets.json")))  # To-Do: Use CONFIG_DIR
    videos = sets[task]["sources"]
    return sets, videos


def return_run_status(run_id):
    run_status = open('runs/' + run_id + '/status.txt', 'r').read()
    return run_status


url = "http://awcy.mindfreeze.tk/run_status.json"
build_status_url = "http://awcy.mindfreeze.tk/build_job_queue.json"
job_status_url = "http://awcy.mindfreeze.tk/list.json"
# The baserun should be programtically done, right now doing as hardcoded
base_run = 'av1-directopt-vimeo-single-acbr-s9-baserun-2021-06-17_211114-4fb45ab04'

current_run_status = []

sucessful_runs = False


def submit_new_run(prefix, extra_options):
    # python3 ../submit_awcy_sig.py -prefix av1-directopt-vimeo-single-acbr-s9-baserun
    # -commit 4fb45ab04 -set "vimeo-corpus-10s-single" -nick mindfreeze -extra_options "--alm_k=1 --alm_step=0 --cpu-used=9"
    # -encoding_mode bitrate
    temp_process = subprocess.Popen(['python3',
                                     '/home/mindfreeze/awcy/submit_awcy_sig.py',
                                     '-prefix',
                                     prefix,
                                     '-commit',
                                     '4fb45ab04',
                                     '-set',
                                     "vimeo-corpus-10s-single",
                                     '-nick',
                                     'mindfreeze',
                                     '-extra_options',
                                     extra_options,
                                     '-encoding_mode',
                                     'bitrate'],
                                    cwd='/home/mindfreeze/awcy/av1',
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
    stdout, stderr = temp_process.communicate()
    if not stderr:
        run_id = stdout.decode('utf-8').split('\n')[0]
        task_name = stdout.decode('utf-8').split('\n')[1]
        return run_id, task_name
    else:
        return 0


def poll_current_server(current_run_id):
    # Three state of runs 1. New 2. Build 3. Running. Need to handle them
    # seperately

    while True:
        # New state
        job_list = requests.get(job_status_url).json()
        current_run_status = [item['status']
                              for item in job_list if item['run_id'] == current_run_id]
        current_run_status = current_run_status[0]
        # New stage
        if current_run_status.lower() == 'new':
            print("DEBUG: Run is new, will poll again")
        # Building stage
        if current_run_status.lower() == 'building' or requests.get(build_status_url).json():
            print("DEBUG: Building")
            sleep(120)
        # Running stage
        if current_run_status.lower() == 'running' or requests.get(url).json():
            print("DEBUG: Running")
            sleep(90)
            # current_run_data = requests.get(url).json() commenting for now
        # Fail stage
        if current_run_status.lower() == 'failed':
            print("ERR: Run Failed")
            sucessful_runs = False
            break
        # Compile time error stage
        if current_run_status.lower() == 'buildfailed':
            print("ERR: FATAL BUILD FAILED Aborting")
            sys.exit(1)
        # Completed stage
        if current_run_status.lower() == 'completed':
            sucessful_runs = True
            return sucessful_runs
        # DEBUG: 30, Prod; 60/120, with difference sleep times for different
        # cases
        sleep(30)


def return_server_status():
    if not requests.get(url).json():
        return True     # Returns True if the server queue is empty
    return False


encode_run_counter = 0
bdrate_pair = {}


def cost_function(x):
    if return_server_status():
        n1, n2 = divmod(x, 1)
        new_x = math.floor(n1)
        new_y = math.floor(n2 * 10)
        new_z = math.floor(n2 * 100) % 10
        run_options = '--alm_k=' + \
            str(new_x) + ' --alm_step=' + str(new_y) + ' --cpu-used=9'
        k_value = math.floor(x * 10) / 10
        print("DEBUG: brent_x: ", x, ", k_value: ", k_value)
        # Saves lot of CPU cycles as Data will be redudant by checking
        #  bdrate with this logic of {k_value:bd_rate}
        if k_value in bdrate_pair:
            return bdrate_pair[k_value]
        else:
            global encode_run_counter
            encode_run_counter += 1
            run_prefix = "av1-directopt-vimeo-single-acbr-s9-" + str(k_value)
            current_run_id, current_task_name = submit_new_run(
                run_prefix, run_options)
            sleep(10)  # Replace with 200 Response from the submission
            sucessful_runs = poll_current_server(current_run_id)
            if sucessful_runs:
                metric_data = {}
                sets, videos = return_video_info(current_task_name)
                for video in videos:
                    metric_data[video] = bdrate(
                        'runs/' +
                        base_run +
                        '/' +
                        current_task_name +
                        '/' +
                        video +
                        '-daala.out',
                        'runs/' +
                        current_run_id +
                        '/' +
                        current_task_name +
                        '/' +
                        video +
                        '-daala.out',
                        None,
                        True)
                bdrate_value = metric_data[videos[0]][17]
                bdrate_pair[k_value] = bdrate_value
                print("DEBUG: ", str(bdrate_value))
                # Replace with cost and max(metrics without encoding time)
                return bdrate_value


opt_k = scipy.optimize.fminbound(cost_function, 0.1, 4, full_output=True)
print("DONE CONGRATS")
print(opt_k)
print("Total Number of Actual Encoding Cycles:", encode_run_counter)
