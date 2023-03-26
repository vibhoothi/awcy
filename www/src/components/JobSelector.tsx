import * as React from "react";
import { appStore, AppDispatcher, Jobs, Job, metricNames, AnalyzeFile } from "../stores/Stores";
import { Option, arraysEqual } from "./Widgets";
declare var require: any;
let Select = require('react-select');

interface JobSelectorProps {
  jobs: Job [];
  video: string;
  metric: string;
  set: string;
  preset: string;
  onChange?: (metric?: string, video?: string, set?: string, preset?: string) => void;
}

export let ctc_sets_mandatory = [
  "aomctc-a1-4k",
  "aomctc-a2-2k",
  "aomctc-a3-720p",
  "aomctc-a4-360p",
  "aomctc-a5-270p",
  "aomctc-b1-syn",
  "aomctc-b2-syn"];
export let ctc_sets_mandatory_ai = [...ctc_sets_mandatory, "aomctc-f1-hires", "aomctc-f2-midres"];
export let ctc_sets_mandatory_ld = ctc_sets_mandatory.filter(x => x !== 'aomctc-a1-4k');
export let ctc_sets_optional = ["aomctc-g1-hdr-4k",
"aomctc-g2-hdr-2k", "aomctc-e-nonpristine"];
export class JobSelectorComponent extends React.Component<JobSelectorProps, {
  video: Option;
  videos: Option[];
  metric: Option;
  metrics: Option[];
  preset: Option;
  presets: Option[];
  set: Option;
  sets: Option[];
}> {
  constructor() {
    super();
    this.state = {
      video: null,
      metric: null,
      preset: null,
      set: null,
      metrics: metricNames.map(name => {
        return { value: name, label: name };
      }),
      videos: [],
      presets: [],
      sets: [],
    };
  }
  componentWillReceiveProps(nextProps: JobSelectorProps, nextContext: any) {
    if (!arraysEqual(this.props.jobs, nextProps.jobs)) {
      this.resetJobs(nextProps.jobs.slice(0));
    }
  }
  resetJobs(jobs: Job []) {
    // Get the CTC information
    let presets = [];
    // Handle Presets (Different codec configs)
    if (jobs[0].ctcPresets.length == 0) {
      presets = [jobs[0].task]
    }
    else if ((jobs[0].ctcPresets[0].includes('av2-all'))) {
      presets = ['av2-ra-st', 'av2-ai', 'av2-ld']
    }
    else {
      presets = jobs[0].ctcPresets;
    }
    presets = presets.map(preset_name => { return { value: preset_name, label: preset_name }; });
    this.setState({presets} as any);
    // Handle Sets (Different video classes)
    let sets = [];
    if ((jobs[0].ctcSets.length == 1) && (jobs[0].ctcSets[0] == 'aomctc-all')) {
      let this_codec = jobs[0].codec.toLowerCase();
      if (this_codec.includes('ra'))
        sets = [...ctc_sets_mandatory, ...ctc_sets_optional];
      else if (this_codec.includes('ld'))
        sets = ctc_sets_mandatory_ld;
      else if (this_codec.includes('ai'))
        sets = [...ctc_sets_mandatory_ai, ...ctc_sets_optional];
    }
    else if ((jobs[0].ctcSets.length == 1) && (jobs[0].ctcSets[0] == 'aomctc-mandatory')) {
      let this_codec = jobs[0].codec.toLowerCase();
      if (this_codec.includes('ra'))
        sets = ctc_sets_mandatory;
      else if (this_codec.includes('ld'))
        sets = ctc_sets_mandatory_ld;
      else if (this_codec.includes('ai'))
        sets = ctc_sets_mandatory_ai;
    }
    else if (jobs[0].ctcSets.length == 0) {
      sets = [jobs[0].task]
    }
    else {
      sets = jobs[0].ctcSets;
    }
    sets = sets.map(set_name => { return { value: set_name, label: set_name }; });
    this.setState({sets} as any);
    // Handle Videos
    let videos = [];
    if (jobs[0].codec == 'av2-as' || jobs[0].codec == 'av2-as-st') {
      videos = Object.keys(jobs[0].report).reduce((acc, name) => {
        return acc.concat([ { value: name, label: name },
          { value: name + ' - Convex Hull', label: name + ' - Convex Hull' }
        ]);
      }, []).filter(video => {
        if (jobs[0].codec == 'av2-as' || jobs[0].codec == 'av2-as-st') {
            return video.value.includes("3840x2160");
        } else {
          return true;
        }
      });
    } else {
      videos = Object.keys(jobs[0].report).map(name => {
        return { value: name, label: name };
      }).filter(video => {
        if (jobs[0].codec == 'av2-as' || jobs[0].codec == 'av2-as-st') {
          return video.value.includes("3840x2160");
        } else {
          return true;
        }
      });
    }
    videos.unshift({ value: "All", label: "All" });
    this.setState({videos} as any);
  }
  componentWillMount() {
    this.resetJobs(this.props.jobs.slice(0));
    let metric = { value: this.props.metric, label: this.props.metric };
    let video = { value: this.props.video, label: this.props.video };
    let set = { value: this.props.set, label: this.props.set };
    let preset = { value: this.props.preset, label: this.props.preset };
    this.setState({metric, video, set, preset} as any);
  }
  onChange() {
    if (!this.props.onChange) {
      return;
    }
    this.props.onChange(
      this.state.metric.value,
      this.state.video.value,
      this.state.set.value,
      this.state.preset.value
    );
  }
  onChangeMetrics(metric) {
    this.setState({metric} as any, () => {
      this.onChange();
    });
  }
  onChangeVideos(video) {
    this.setState({video} as any, () => {
      this.onChange();
    });
 // this.props.jobs[0]['']
  }

  onChangeSets(set) {
    this.setState({set} as any, () => {
      this.onChange();
    });
    // Update the video list here
    let set_data = Job.sets[set.value.valueOf()].sources.map(set_name => { return { value: set_name, label: set_name }; });
    set_data.unshift({ value: "All", label: "All" });
    this.state.videos = set_data;
    this.props.jobs[0]['task'] = set.value.valueOf();
    this.props.jobs[0].loadReport()

  }
  onChangePresets(preset) {
    this.setState({preset} as any, () => {
      this.onChange();
    });
  // Handle the new list of video-sets on change of preset from the user in the
  // frontend, config-state: {0: nothing, 1: mandatory, 2: all}
  let job_info = this.props.jobs[0];
  let config_state = 0;
  if (job_info['ctcPresets'][0].valueOf().includes('all'))
    config_state = 2;
  else if (job_info['ctcPresets'][0].valueOf().includes('mandatory'))
    config_state = 1;
  else
    config_state = 0;
  let updated_sets = [];
  if (preset.value.includes('ra')){
    if (config_state == 2)
      updated_sets = [...ctc_sets_mandatory, ...ctc_sets_optional];
    else if (config_state == 1)
      updated_sets = ctc_sets_mandatory;
  }
  else if (preset.value.includes('ld')){
    if ((config_state == 2) || (config_state == 1))
      updated_sets = ctc_sets_mandatory_ld;
  }
  if (preset.value.includes('ai')){
    if (config_state == 2)
      updated_sets = [...ctc_sets_mandatory_ai, ...ctc_sets_optional];
    else if (config_state == 1)
      updated_sets = ctc_sets_mandatory_ai;
  }
  this.state.sets = updated_sets.map(set_name => { return { value: set_name, label: set_name }; });
  this.props.jobs[0]['codec'] = preset.value.valueOf();
  }
  render() {
    console.debug("Rendering Job Selector");
    return <div>
      <div className="row">
        <div className="col-xs-12">
          <div className="row">
            <div className="col-xs-4">
              <div className="selectTitle">Metric</div>
              <Select ref="metricSelect" autofocus value={this.state.metric} options={this.state.metrics} onChange={this.onChangeMetrics.bind(this)} clearable={false}/>
            </div>
            <div className="col-xs-2">
              <div className="selectTitle">Config</div>
              <Select ref="videoSelect" value={this.state.preset} options={this.state.presets} onChange={this.onChangePresets.bind(this)} clearable={false}/>
            </div>
            <div className="col-xs-2">
              <div className="selectTitle">Sets</div>
              <Select ref="videoSelect" value={this.state.set} options={this.state.sets} onChange={this.onChangeSets.bind(this)} clearable={false}/>
            </div>
            <div className="col-xs-4">
              <div className="selectTitle">Video</div>
              <Select ref="videoSelect" value={this.state.video} options={this.state.videos} onChange={this.onChangeVideos.bind(this)} clearable={false}/>
            </div>
          </div>
        </div>
      </div>
    </div>
  }
}
