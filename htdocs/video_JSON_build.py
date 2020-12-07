import os
import json

# VIDEO_PATH = '/home/arian/aakash/10minVid/static/video1'
VIDEO_PATH = './all'
TOTAL_SEGMENTS = 5
TOTAL_BITRATES = 10

properties = {}
properties['total_segments'] = TOTAL_SEGMENTS
properties['framePerSegment'] = 97
properties['total_representations'] = TOTAL_BITRATES
properties['bitrates'] = [214915, 562660, 990946, 1520727, 2963872,214915, 562660, 990946, 1520727, 2963872] #bits per second
properties['total_duration'] = 15 #seconds

# media file details such as file name, segment duration, start index of segments
# change $REPID$ with representation ID and $Number$ with segment number to download.
properties['iFrame'] = 'video_segment_$segNum$_frame_$frameNum$.p'
properties['pFrame'] = f'video_track_$trackNum$_segment_$segNum$_frame_$frameNum$.p'
properties['iFrameFrequency'] = 12
properties['duration'] = 3000
properties['timescale'] = 1000
properties['start_number'] = 1

# video segment sizes
# segments_size = []
# for i in range(0,TOTAL_SEGMENTS):
#     seg_size = []
#     for j in range(TOTAL_BITRATES):
#         fp = VIDEO_PATH + '/' + 'video_$q$_dash$n$.zip'.replace('$q$',str(j+1)).replace('$n$',str(i))
#         s = os.path.getsize(fp)
#         seg_size.append(s)
    
#     segments_size.append(seg_size)
# properties['segment_size_bytes'] = segments_size

# writes dict to file
with open('.' + '/all/video_properties.json','w') as f :
    json.dump(properties, f)

