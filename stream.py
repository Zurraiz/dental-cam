import streamlit as st
import cv2
import os
import time
import requests
import numpy as np

def get_frame_from_esp32(url, retries=3):
    for _ in range(retries):
        try:
            response = requests.get(url, stream=True, timeout=5)
            if response.status_code == 200:
                bytes_data = bytes()
                for chunk in response.iter_content(chunk_size=1024):
                    bytes_data += chunk
                    a = bytes_data.find(b'\xff\xd8')
                    b = bytes_data.find(b'\xff\xd9')
                    if a != -1 and b != -1:
                        jpg = bytes_data[a:b+2]
                        bytes_data = bytes_data[b+2:]
                        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        return frame
            else:
                st.error(f"Failed to fetch frame from ESP32-CAM. Status code: {response.status_code}")
                return None
        except requests.exceptions.ReadTimeout:
            st.warning("Read timeout while fetching frame from ESP32-CAM. Retrying...")
            continue
        except requests.exceptions.ConnectionError:
            st.error("Connection error while fetching frame from ESP32-CAM. Retrying...")
            continue
        except Exception as e:
            st.error(f"Error: {e}")
            return None
    st.error(f"Failed to fetch frame from ESP32-CAM after {retries} retries.")
    return None

def save_video(frames, output_dir):
    if not frames:
        st.warning("No frames to save.")
        return None
    
    video_file = os.path.join(output_dir, 'saved_video.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_file, fourcc, 20, (frames[0].shape[1], frames[0].shape[0]))  # Use 20 FPS or higher
    for frame in frames:
        out.write(frame)
    out.release()
    return video_file

def main():
    st.title("ESP32-CAM Video Stream")

    if "streaming" not in st.session_state:
        st.session_state["streaming"] = False
    if "frames" not in st.session_state:
        st.session_state["frames"] = []

    esp32_cam_url = st.text_input("ESP32-CAM Stream URL", value="http://192.168.10.46:81/stream")
    output_dir = st.text_input("Output Directory", value="", help="Enter the directory where you want to save the video or leave empty for default (Downloads folder).")

    start_button = st.button("Start Streaming")
    stop_button = st.button("Stop Streaming")

    if start_button:
        st.session_state["streaming"] = True
        st.session_state["frames"] = []

    if stop_button:
        st.session_state["streaming"] = False

        if len(st.session_state["frames"]) > 0:
            if output_dir == "":
                output_dir = os.path.expanduser("~/Downloads")
            video_file = save_video(st.session_state["frames"], output_dir)
            st.success(f"Video saved to: {video_file}")
            with open(video_file, "rb") as file:
                st.download_button(label="Download Video", data=file, file_name="saved_video.mp4")
        else:
            st.warning("No frames captured to save the video.")

    if st.session_state["streaming"]:
        placeholder = st.empty()
        while st.session_state["streaming"]:
            frame = get_frame_from_esp32(esp32_cam_url)
            if frame is not None:
                placeholder.image(frame, channels="BGR")
                st.session_state["frames"].append(frame)
            # No sleep to capture frames as fast as possible

if __name__ == "__main__":
    main()
