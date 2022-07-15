import pyrealsense2 as rs
import numpy as np
import cv2
import pandas as pd
import os

import time
 
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 0, 848, 100, rs.format.z16, 300)
config.enable_stream(rs.stream.infrared, 1, 848, 100, rs.format.y8, 300)

ctx = rs.context()
devices = ctx.query_devices()
for dev in devices:
    sensors = dev.query_sensors()

# exp = sensors[0].get_option(rs.option.exposure) # Get exposure
# fr=sensors[0].get_option(rs.option.frames_queue_size) # Get frames queue size
# gn = sensors[0].get_option(rs.option.gain) # Get gain
# emit = sensors[0].get_option(rs.option.emitter_enabled) # Get emitter status
    
sensors[0].set_option(rs.option.exposure, 1.0) # Changing the exposure value
sensors[0].set_option(rs.option.enable_auto_exposure,True) # Example to Enable/disable auto exposure
sensors[1].set_option(rs.option.auto_exposure_priority,False) # Disable/Enable the Auto Exposure Priority
         

def stream(): 
        # used to record the time when we processed last frame
        prev_frame_time = 0
        
        # used to record the time at which we processed current frame
        new_frame_time = 0
        
        pipeline.start(config)
        
        # Start streaming
        
        
        try:
            while True:
        
                # Wait for a coherent pair of frames: depth and color
                frames = pipeline.wait_for_frames()
                depth_frame = frames.get_depth_frame()
                infrared_frame = frames.get_infrared_frame()
                
                if not depth_frame:
                    continue
        
        # Estimating depth and saving it to csv file

                
                # Convert images to numpy arrays
                depth_image = np.asanyarray(depth_frame.get_data())
                infrared_image = np.asanyarray(infrared_frame.get_data())
               
                # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
                depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

                new_frame_time = time.time()

                fps = 1/(new_frame_time-prev_frame_time)
                prev_frame_time = new_frame_time
                fps = int(fps)
                print(fps)
        
                # Stack both images horizontally
                # images = np.hstack((infrared_image, depth_colormap))
        
                # Show images
                # cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
                cv2.imshow('RealSense1', infrared_image)
                # cv2.putText(gray, fps, (7, 70), font, 3, (100, 255, 0), 3, cv2.LINE_AA)
                cv2.imshow('RealSense2', depth_colormap)
                key = cv2.waitKey(1)
             # Press esc or 'q' to close the image window
                if key & 0xFF == ord('q') or key == 27:
                    cv2.destroyAllWindows()
                    break
        
        finally:
        
               # Stop streaming
               pipeline.stop()
            #    data = pd.DataFrame(columns = ['Left', 'Right','Frame','Time_Stamp']) 
            #    data['Left']=pd.Series(left)
            #    data['Right']=pd.Series(right)
            #    data['Frame']=pd.Series(framek)
            #    data['Time_Stamp']=pd.Series(tstamp)
            #    data.to_csv(r'test_New.csv')


if __name__ == '__main__':
    stream()