import whisper
import os
import cv2
from moviepy.editor import ImageSequenceClip, AudioFileClip, VideoFileClip
from tqdm import tqdm
import streamlit as st

FONT = cv2.FONT_HERSHEY_TRIPLEX
FONT_SCALE = 0.8
FONT_THICKNESS = 2

def empty_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

class VideoTranscriber:
    def __init__(self, model_path, video_path):
        self.model = whisper.load_model(model_path)
        self.video_path = video_path
        self.audio_path = ''
        self.text_array = []
        self.fps = 0
        self.char_width = 0

    def transcribe_video(self):
        print('Transcribing video')

        result = self.model.transcribe(self.audio_path)

        text = result["segments"][0]["text"]
        textsize = cv2.getTextSize(text, FONT, FONT_SCALE, FONT_THICKNESS)[0]

        cap = cv2.VideoCapture(self.video_path)

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        width -= width * 0.1
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        asp = 16/9
        ret, frame = cap.read()
        
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        self.char_width = int(textsize[0] / len(text))
        
        
        for j in tqdm(result["segments"]):
            lines = []
            text = j["text"]
            end = j["end"]
            start = j["start"]
            total_frames = int((end - start) * self.fps)
            start = start * self.fps
            total_chars = len(text)
            words = text.split(" ")
            i = 0            
            while i < len(words):
                words[i] = words[i].strip()
                if words[i] == "":
                    i += 1
                    continue
                length_in_pixels = len(words[i]) * self.char_width
                remaining_pixels = width - length_in_pixels
                line = words[i] 
                
                while remaining_pixels > 0:
                    i += 1 
                    if i >= len(words):
                        break
                    length_in_pixels = len(words[i]) * self.char_width
                    remaining_pixels -= length_in_pixels
                    if remaining_pixels < 0:
                        continue
                    else:
                        line += " " + words[i]
                
                line_array = [line, int(start) + 15, int(len(line) / total_chars * total_frames) + int(start) + 15]
                start = int(len(line) / total_chars * total_frames) + int(start)
                lines.append(line_array)
                self.text_array.append(line_array)
        
        cap.release()
        print('Transcription complete')
    
    def extract_audio(self, output_audio_path):
        print('Extracting audio')
        video = VideoFileClip(self.video_path)
        audio = video.audio 
        audio.write_audiofile(output_audio_path)
        self.audio_path = output_audio_path
        print('Audio extracted')
    
    def extract_frames(self, output_folder):
        print('Extracting frames')
        cap = cv2.VideoCapture(self.video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        N_frames = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                        
            for i in self.text_array:
                if N_frames >= i[1] and N_frames <= i[2]:
                    text = i[0]
                    text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                    text_x = int((frame.shape[1] - text_size[0]) / 2)                    
                    text_y = int(height/1.5)
                    
                    words = text.split()
                    if len(words) > 3:
                        mid = len(words) // 2
                        line1 = ' '.join(words[:mid])
                        line2 = ' '.join(words[mid:])
                        
                        line1_x, _ = cv2.getTextSize(line1, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                        line2_x, _ = cv2.getTextSize(line2, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)

                        line1_x = int((width - line1_x[0])/2)
                        line2_x = int((width - line2_x[0])/2)

                        cv2.putText(frame, line1, (line1_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                        cv2.putText(frame, line2, (line2_x, text_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                    else:
                        cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                    break
            
            cv2.imwrite(os.path.join(output_folder, str(N_frames) + ".jpg"), frame)
            N_frames += 1
        
        cap.release()
        print('Frames extracted')

    def create_video(self, output_video_path):
        print('Creating video')
        image_folder = os.path.join(os.path.dirname(self.video_path), "frames")
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)
        else:
            empty_folder(image_folder)
        
        self.extract_frames(image_folder)
        
        print("Video saved at:", output_video_path)
        images = [img for img in os.listdir(image_folder) if img.endswith(".jpg")]
        images.sort(key=lambda x: int(x.split(".")[0]))
        
        frame = cv2.imread(os.path.join(image_folder, images[0]))
        height, width, layers = frame.shape
        
        clip = ImageSequenceClip([os.path.join(image_folder, image) for image in images], fps=self.fps)
        audio = AudioFileClip(self.audio_path)
        clip = clip.set_audio(audio)
        clip.write_videofile(output_video_path)


st.title('Generate subtitles for your video')
uploaded_file = st.file_uploader("Choose a video")
if uploaded_file is not None:
    with open(uploaded_file.name, "wb") as f:
        f.write(uploaded_file.getvalue())
    model_path = "base"
    video_path = uploaded_file.name
    output_video_path = "output.mp4"
    output_audio_path = "audio.mp3"

    with st.spinner('We are processing your video..'):
        transcriber = VideoTranscriber(model_path, video_path)
        transcriber.extract_audio(output_audio_path=output_audio_path)
        transcriber.transcribe_video()
        transcriber.create_video(output_video_path)

        st.success('Your video: ', icon="✅")

        video_file = open(output_video_path, 'rb')
        video_bytes = video_file.read()
        st.video(video_bytes)