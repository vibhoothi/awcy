#!/usr/bin/env python3

from __future__ import print_function

from collections import defaultdict
from numpy import *
import numpy as np
from scipy import *
from scipy._lib._util import _asarray_validated
import sys
import os
import argparse
import json
import csv
import simplejson
from copy import deepcopy
from bd_rate_report import bdrate
from bd_rate_report import PchipInterpolator_new, PchipInterpolator_old
from bd_rate_report import met_index, met_name


parser = argparse.ArgumentParser(
    description='Produce local minima per-clip for lambda based on bd-rate')
parser.add_argument('run', nargs='+', help='Run folders to compare')
parser.add_argument(
    '--suffix', help='Metric data suffix (default is .out)', default='.out')
parser.add_argument('--format', help='Format of output', default='text')
parser.add_argument('--fullrange', action='store_true',
                    help='Use full range of QPs instead of 20-55')
parser.add_argument('--old-pchip', action='store_true')


def get_video_names_in_json_obj(json_obj):
    return list(json_obj["metric_data"].keys())


def get_metric_names_in_json_obj(json_obj):
    return json_obj["metric_names"]


def get_task_names_in_json_obj(json_obj):
    return json_obj['task']


def assert_video_names_are_same(json_objs):
    video_names_in_first_json_obj = get_video_names_in_json_obj(json_objs[0])
    assert len(video_names_in_first_json_obj) == len(
        set(video_names_in_first_json_obj)), "video names are not unique"
    video_names_in_first_json_obj = set(video_names_in_first_json_obj)

    for json_obj in json_objs[1:]:
        video_names_in_json_obj = get_video_names_in_json_obj(json_obj)
        assert len(video_names_in_json_obj) == len(
            set(video_names_in_json_obj)), "video names are not unique"
        video_names_in_json_obj = set(video_names_in_json_obj)
        assert video_names_in_first_json_obj == video_names_in_json_obj, "video names are not the same across objects"


def assert_task_names_are_same(task_names):
    task_name_in_first_json_obj = get_task_names_in_json_obj(task_names[0])
    for task_idx, task_name in task_names.items():
        task_names_in_obj = get_task_names_in_json_obj(task_name)
        assert task_name_in_first_json_obj == task_names_in_obj, "Task names do not match between given runs"


def assert_metric_names_are_in_order(json_objs):
    metric_names_in_first_obj = get_metric_names_in_json_obj(json_objs[0])
    assert len(metric_names_in_first_obj) == len(
        set(metric_names_in_first_obj)), "metric names are not unique"

    for json_obj in json_objs[1:]:
        metric_names_in_obj = get_metric_names_in_json_obj(json_obj)
        assert len(metric_names_in_obj) == len(
            set(metric_names_in_obj)), "metric names are not unique"
        assert metric_names_in_obj == metric_names_in_first_obj, "metric names are not the same across objects"


def return_info_data_from_runs(runs):
    try:
        info_data = {}
        for run_no, run_name in enumerate(runs):
            info_data[run_no] = json.load(open(run_name+'/info.json'))
        assert_task_names_are_same(info_data)
    except FileNotFoundError:
        print('Could not open', runs[0])
        info_data = None
    return info_data, info_data[0]['task']


def return_video_info(task_info, task):
    sets = json.load(
        open(os.path.join(os.getenv("CONFIG_DIR", "rd_tool"), "sets.json")))
    videos = sets[task]["sources"]
    return sets, videos


def return_metric_data(run_a, run_b, info_data, videos, task, sets):
    avg = {}
    categories = {}
    metric_data = {}
    for video in videos:
        metric_data[video] = bdrate(run_a+'/'+task+'/'+video+args.suffix,
                                    run_b+'/'+task+'/'+video+args.suffix, None, args.fullrange)
    for m in range(0, len(met_index)):
        avg[m] = mean([metric_data[x][m] for x in metric_data])
    if 'categories' in sets[task]:
        for category_name in sets[task]['categories']:
            category = {}
            for m in range(0, len(met_index)):
                category[m] = mean([metric_data[x][m]
                                    for x in sets[task]['categories'][category_name]])
            categories[category_name] = category
    return metric_data, avg, categories


args = parser.parse_args()
if args.old_pchip:
    pchip = PchipInterpolator_old
else:
    pchip = PchipInterpolator_new
metric_data = {}
error_strings = []
q_not_found = False
runs_list = args.run
info_data, task = return_info_data_from_runs(runs_list)
sets, videos = return_video_info(info_data, task)
filename_len = 40

if len(runs_list) > 2:
    outputs = []
    base_run = runs_list[0]
    key_count = 0
    for run in runs_list[1:]:
        metric_data, avg, categories = return_metric_data(
            base_run, run, info_data, videos, task, sets)
        output = {}
        output['metric_names'] = met_name
        output['metric_data'] = metric_data
        output['average'] = avg.copy
        output['categories'] = categories
        output['error_strings'] = error_strings
        extra_options = {item[0].strip("--"): item[1] for item in [tmp.split("=")
                                                                   for tmp in info_data[key_count+1]['extra_options'].split(" ") if len(tmp) != 0]}
        k_value = np.format_float_positional(np.add(int(
            extra_options['alm_k']), np.multiply(int(extra_options['alm_step']), 0.10)), 1)
        output['k_value'] = float(k_value)
        outputs.append(output)
        key_count = key_count + 1
else:
    metric_data, avg, categories = return_metric_data(
        runs_list[0], runs_list[1], info_data, videos, task, sets)
    output = {}
    output['metric_names'] = met_name
    output['metric_data'] = metric_data
    output['average'] = avg
    output['categories'] = categories
    output['error_strings'] = error_strings
    extra_options = {item[0].strip("--"): item[1] for item in [tmp.split("=")
                                                               for tmp in info_data[1]['extra_options'].split(" ") if len(tmp) != 0]}
    k_value = np.format_float_positional(np.add(int(
        extra_options['alm_k']), np.multiply(int(extra_options['alm_step']), 0.10)), 1)
    output['k_value'] = k_value

assert len(outputs) > 0, "Atleast one file should be given as input"

assert_video_names_are_same(outputs)
assert_metric_names_are_in_order(outputs)
video_names_in_first_json_obj = get_video_names_in_json_obj(outputs[0])
metric_names_in_first_obj = get_metric_names_in_json_obj(outputs[0])
per_clip_bdr = {}
per_clip_bdr["metric_names"] = met_name
for video_name in video_names_in_first_json_obj:
    temp_clip_metric = {}
    for metric_idx, metric_name in enumerate(metric_names_in_first_obj):
        min_metric_value = float("inf")
        best_k_value = None
        for json_obj_idx, json_obj in enumerate(outputs):
            metric_value_of_video_in_json_obj = json_obj["metric_data"][video_name][metric_idx]
            if metric_value_of_video_in_json_obj != None and metric_value_of_video_in_json_obj < min_metric_value:
                min_metric_value = metric_value_of_video_in_json_obj
                best_k_value = json_obj['k_value']
        if min_metric_value == float("inf"):
            temp_clip_metric[metric_name] = [NaN, NaN]
        else:
            temp_clip_metric[metric_name] = [min_metric_value, best_k_value]
    per_clip_bdr[video_name] = temp_clip_metric

if args.format == 'json':
    print(json.dumps(per_clip_bdr, indent=2))
elif args.format == 'csv':
    csvwriter = csv.DictWriter(sys.stdout, fieldnames=[
                               "filename"] + met_name + [x + "_k" for x in met_name])
    csvwriter.writeheader()
    for video_name, video_bdr in per_clip_bdr.items():
        temp_buffer = {}
        if video_name == 'metric_names':
            continue
        temp_buffer["filename"] = video_name
        for bdr_obj in met_name:
            bdr_idx = video_bdr[bdr_obj]
            temp_buffer[bdr_obj] = bdr_idx[0]
            temp_buffer[bdr_obj + '_k'] = bdr_idx[1]
        csvwriter.writerow(temp_buffer)
elif args.format == "text":
    print("Calculation completed, please re-run with --format=json/csv to see the output ")
    print("Text output is not yet implemented")
