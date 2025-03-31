import stable_whisper
import time
import re
from datetime import datetime, timedelta
import os
import platform

# check for macOS, then configure ffmpeg path + homebrew path (ensures that script works on M1 Macs)
if platform.system() == 'Darwin':
   os.environ['FFMPEG'] = '/opt/homebrew/bin/ffmpeg'
   os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ['PATH']

# some element IDs
winID = "com.blackmagicdesign.resolve.AutoSubsGen"   # should be unique for single instancing
textID = "TextEdit"
addSubsID = "AddSubs"
transcribeID = "Transcribe"
executeAllID = "ExecuteAll"
browseFilesID = "BrowseButton"

# create the UI
ui = fusion.UIManager
dispatcher = bmd.UIDispatcher(ui)

# get the storage path for the settings file and other files
settingsName = "settings.txt"
if platform.system() == 'Darwin':
   # MacOS
   storagePath = os.path.expandvars("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/")
elif platform.system() == 'Linux':
   # Linux
   storagePath = os.path.expandvars("$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility/")
elif platform.system() == 'Windows':
   # Windows
   storagePath = os.path.expandvars("%APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\Utility\\")
else:
   storagePath = fusion.MapPath(r"Scripts:/Utility/")

# check for existing instance
win = ui.FindWindow(winID)
if win:
   win.Show()
   win.Raise()
   exit()
# otherwise, we set up a new window

# define the window UI layout
win = dispatcher.AddWindow({
   'ID': winID,
   'Geometry': [ 100,100, 910, 980 ],
   'WindowTitle': "Resolve AI Subtitles",
   },
   ui.VGroup({"ID": "root",},[
      ui.HGroup({'Weight': 1.0},[
         ui.HGap(10),
         ui.VGroup({'Weight': 0.0, 'MinimumSize': [400, 960]},[
            ui.VGap(4),
            ui.Label({ 'Text': "♆ AutoSubs", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 22, 'Bold': True}) }),
            ui.VGap(35),
            ui.Label({ 'ID': 'DialogBox', 'Text': "Waiting for Task", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 24, 'Italic': True }), 'Alignment': { 'AlignHCenter': True } }),
            ui.VGap(40),
            ui.Label({ 'Text': "1. Add Text+ subtitle template to Media Pool.", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 15, 'Bold': True }), 'Alignment': { 'AlignHCenter': True } }),
            ui.Label({ 'Text': "2. Mark In + Out of area to subtitle with \"I\" + \"O\" keys.", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 15, 'Bold': True }), 'Alignment': { 'AlignHCenter': True } }),
            ui.VGap(2),
            ui.Button({ 
               'ID': executeAllID,
               'Text': "  Generate Subtitles", 
               'MinimumSize': [150, 40],
               'MaximumSize': [1000, 40], 
               'IconSize': [17, 17], 
               'Font': ui.Font({'PixelSize': 15}),
               'Icon': ui.Icon({'File': 'AllData:../Support/Developer/Workflow Integrations/Examples/SamplePlugin/img/logo.png'}),}),
            ui.VGap(1),
            ui.HGroup({'Weight': 0.0,},[
               ui.Button({ 'ID': transcribeID, 'Text': "➔  Get Subtitles File", 'MinimumSize': [120, 35], 'MaximumSize': [1000, 35], 'Font': ui.Font({'PixelSize': 14}),}),
               ui.Button({ 'ID': addSubsID, 'Text': "☇ Revert all changes", 'MinimumSize': [120, 35], 'MaximumSize': [1000, 35], 'Font': ui.Font({'PixelSize': 14}),}),
            ]),
            ui.VGap(12),
            ui.Label({ 'Text': "Basic Settings:", 'Weight': 1, 'Font': ui.Font({ 'PixelSize': 20 }) }),
            ui.VGap(1),
            ui.Label({ 'Text': "Video Track for Subtitles", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 14 }) }),
            ui.SpinBox({"ID": "TrackSelector", "Min": 1, "Value": 2, 'MaximumSize': [2000, 40]}),
            ui.VGap(1),
            ui.Label({ 'Text': "Select Template Text", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 14 })}),
            ui.ComboBox({"ID": "Template", 'MaximumSize': [2000, 55]}),
            ui.VGap(1),
            ui.Label({ 'Text': "Transcription Model", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 14 })}),
            ui.ComboBox({"ID": "WhisperModel", 'MaximumSize': [2000, 55]}),
            ui.VGap(3),
            ui.Label({ 'Text': "Output Mode  (spoken language is auto detected)", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 14 })}),
            ui.ComboBox({"ID": "SubsOutput", 'MaximumSize': [2000, 55]}),
            ui.VGap(1),
            ui.CheckBox({"ID": "RefineSubs", "Text": "Refine Timestamps - may improve timing (slower)", "Checked": True, 'Font': ui.Font({ 'PixelSize': 14 })}),
            ui.VGap(15),
            ui.Label({ 'Text': "Advanced Settings:", 'Weight': 1, 'Font': ui.Font({ 'PixelSize': 20 }) }),
            ui.VGap(1),
            ui.Label({'ID': 'Label', 'Text': 'Use Your Own Subtitles File ( .srt )', 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 14 }) }),
            ui.HGroup({'Weight': 0.0, 'MinimumSize': [200, 25]},[
		      	ui.LineEdit({'ID': 'FileLineTxt', 'Text': '', 'PlaceholderText': 'Please Enter a filepath', 'Weight': 0.9}),
		      	ui.Button({'ID': 'BrowseButton', 'Text': 'Browse', 'Weight': 0.1}),
		      ]),
            ui.VGap(3),
            ui.HGroup({'Weight': 0.0},[
               ui.VGroup({'Weight': 0.0, 'MinimumSize': [140, 48]},[
                  ui.Label({ 'Text': "Max Words", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 13 }) }),
                  ui.SpinBox({"ID": "MaxWords", "Min": 1, "Value": 6}),
               ]),
               ui.VGroup({'Weight': 0.0, 'MinimumSize': [140, 48]},[
                  ui.Label({ 'Text': "Max Characters", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 13 }) }),
                  ui.SpinBox({"ID": "MaxChars", "Min": 1, "Value": 20}),
               ]),
               ui.VGroup({'Weight': 0.0, 'MinimumSize': [140, 48]},[
                  ui.Label({ 'Text': "Split by Gap (seconds)", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 13 }) }),
                  ui.DoubleSpinBox({"ID": "SplitByGap", "Min": 0.1, "Value": 0.4}),
               ]),
            ]),
            ui.VGap(1),
            ui.Label({'ID': 'Label', 'Text': 'Censored Words (comma separated list)', 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 14 }) }),
            ui.LineEdit({'ID': 'CensorList', 'Text': '', 'PlaceholderText': 'e.g. bombing = b***ing', 'Weight': 0, 'MinimumSize': [200, 30]}),
            ui.VGap(1),
            ui.Label({ 'Text': "Format Text", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 14 }) }),
            ui.ComboBox({"ID": "FormatText", 'MaximumSize': [2000, 30]}),
            ui.VGap(1),
            ui.CheckBox({"ID": "RemovePunc", "Text": "Remove commas , and full stops .", "Checked": False, 'Font': ui.Font({ 'PixelSize': 14 })}),
            ui.VGap(10),
         ]),
         ui.HGap(20),
         ui.VGroup({'Weight': 1.0},[
            ui.VGap(4),
            ui.Label({ 'Text': "Subtitles on Timeline:", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 20 }) }),
            ui.Label({ 'Text': "Click on a subtitle to jump to its position in the timeline.", 'Weight': 0, 'Font': ui.Font({ 'PixelSize': 15 }) }),
            ui.VGap(1),
            ui.Tree({
			      "ID": "Tree",
			      "SortingEnabled": False,
			      "Events": {
			      	"CurrentItemChanged": True,
			      	"ItemActivated": True,
			      	"ItemClicked": True,
			      	"ItemDoubleClicked": True,
			      },
		      }),     
            ui.VGap(1),
            ui.Button({ 'ID': 'RefreshSubs', 'Text': "♺  Refresh + Show Latest Changes", 'MinimumSize': [200, 40], 'MaximumSize': [1000, 40], 'Font': ui.Font({'PixelSize': 15}),}),
            ui.VGap(1),
         ]),
      ]),
   ])
)

itm = win.GetItems()
#itm['WhisperModel'].SetCurrentText("small") # set default model to small
projectManager = resolve.GetProjectManager()
project = projectManager.GetCurrentProject()

# Event handlers
def OnClose(ev):
   saveSettings()
   dispatcher.ExitLoop()

def OnBrowseFiles(ev):
	selectedPath = fusion.RequestFile()
	if selectedPath:
		itm['FileLineTxt'].Text = str(selectedPath)
                
# Transcribe + Generate Subtitles on Timeline
def OnSubsGen(ev):
   timeline = project.GetCurrentTimeline()
   if itm['TrackSelector'].Value > timeline.GetTrackCount('video'):
      print("Track", itm['TrackSelector'].Value ,"does not exist - please select a valid track number ( 1 - ", timeline.GetTrackCount('video'), ")")
      itm['DialogBox'].Text = "Error: track " + str(itm['TrackSelector'].Value) + " does not exist!"
      return
   
   if itm['FileLineTxt'].Text == '':
      OnTranscribe(ev)
   OnGenerate(ev)

def AudioToSRT(ev):
   #OnTranscribe(ev)
   # Show the file in the Media Storage
   mediaStorage = resolve.GetMediaStorage()
   fileList = mediaStorage.GetFileList(storagePath)
   for filePath in fileList:
      if 'audio.srt' in filePath:
         mediaStorage.RevealInStorage(filePath)
         itm['DialogBox'].Text = "Storage folder of \"audio.srt\" opened!"
         break

def adjust_subtitle_timestamps(srt_content, time_delta):
    # Define a regular expression pattern to match the timestamps in the SRT file
    timestamp_pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})')

    # Function to adjust the timestamps by adding the specified time_delta
    def adjust_timestamp(match):
        start_time = datetime.strptime(match.group(1), '%H:%M:%S,%f')
        end_time = datetime.strptime(match.group(2), '%H:%M:%S,%f')
        adjusted_start_time = start_time + time_delta
        adjusted_end_time = end_time + time_delta

        return f"{adjusted_start_time.strftime('%H:%M:%S,%f')[:-3]} --> {adjusted_end_time.strftime('%H:%M:%S,%f')[:-3]}"

    # Use the re.sub function to replace timestamps with adjusted timestamps
    adjusted_srt_content = re.sub(timestamp_pattern, adjust_timestamp, srt_content)

    return adjusted_srt_content

# Transcribe Timeline to SRT file              
def OnTranscribe(ev):
   # Choose Transcription Model
   chosenModel = "small" # default model
   if itm['WhisperModel'].CurrentIndex == 1:
      chosenModel = "tiny"
   elif itm['WhisperModel'].CurrentIndex == 2:
      chosenModel = "base"
   elif itm['WhisperModel'].CurrentIndex == 3:
      chosenModel = "small"
   elif itm['WhisperModel'].CurrentIndex == 4:
      chosenModel = "medium"
   elif itm['WhisperModel'].CurrentIndex == 5:
      chosenModel = "turbo"
   
   if itm['SubsOutput'].CurrentIndex == 0 and itm['WhisperModel'].CurrentIndex != 5: # use english only model and not large models (no en)
      chosenModel = chosenModel + ".en"

   print("Using model -> [", chosenModel, "]")

   if not project:
      print("No project is loaded")
      return
   
   resolve.OpenPage("edit")

   timeline = project.GetCurrentTimeline()
   if not timeline:
      if project.GetTimelineCount() > 0:
         timeline = project.GetTimelineByIndex(1)
         project.SetCurrentTimeline(timeline)
      else:
         print("Current project has no timelines")
         return
   
   frame_rate = int(timeline.GetSetting("timelineFrameRate")) # get timeline framerate (sometimes returned as string so must cast to int)