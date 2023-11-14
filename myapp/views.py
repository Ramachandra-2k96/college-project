from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
import qrcode
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm, LoginForm,LoginForm_Q
from django.contrib.auth.views import LoginView
from django.contrib import messages
from qrcode.image.pil import PilImage
from io import BytesIO
import secrets
from .models import UserProfile
from django.contrib.auth.models import User
import os
import cv2
from pyzbar.pyzbar import decode
import numpy as np

from django.shortcuts import render
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from pprint import pprint

class CustomLoginView(LoginView):
    def get(self, request, *args, **kwargs):
        redirect_url = '/custom_login'
        return redirect(redirect_url)

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)



def generate_qr_code(user_profile):
    new_token = secrets.token_urlsafe(200)

    # Ensure the generated token is unique for the user profile
    while UserProfile.objects.filter(id=user_profile.id, token=new_token).exists():
        new_token = secrets.token_urlsafe(200)

    user_profile.token = new_token
    user_profile.save()

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(new_token)
    qr.make(fit=True)

    # Use a specific class from qrcode.image module
    img = qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)

    return img
  
  
  
def custom_login(request):
    login_form = LoginForm()
    signup_form = SignUpForm()

    if request.method == 'POST':
        if 'login-submit' in request.POST:
            form = LoginForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['username']
                password = form.cleaned_data['password']
                user = authenticate(request, username=email, password=password)
                if user is not None:
                    auth_login(request, user)
                    messages.success(request, 'Login successful!')
                    return redirect('home')  # Change 'home' to the desired URL after login
                else:
                    messages.error(request, 'Invalid username or password')
            else:
                messages.error(request, 'Login form is not valid')
                print(form.errors)
        elif 'signup-submit' in request.POST:
            form = SignUpForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        user = form.save(commit=False)
                        user.save()

                        user_profile, created = UserProfile.objects.get_or_create(user=user)
                        img = generate_qr_code(user_profile)

                        # Save QR code to the static folder
                        static_storage = FileSystemStorage(location='static')
                        filename = f"qr_code_{user.username}.png"

                        # Use BytesIO to save the image to a file-like object
                        img_file = BytesIO()
                        img.save(img_file, format="PNG")
                        img_file.seek(0)

                        # Save the file to the storage
                        static_storage.save(filename, img_file)

                        auth_login(request, user)
                        messages.success(request, 'Signup successful!')
                        return redirect('home')

                except Exception as e:
                    messages.error(request, f'Error generating QR code: {str(e)}')
                    user.delete()

            else:
                messages.error(request, 'Signup form is not valid')
                print(form.errors)

    return render(request, 'login.html', {'login_form': login_form, 'signup_form': signup_form})



def qr_decode(image_path):
    image = cv2.imread(image_path)
    decoded_objects = decode(image)
    code = []
    for obj in decoded_objects:
        code.append(f'{obj.data.decode("utf-8")}')
    return "".join(code)

def QR_login(request):
    if request.method == "POST":
        image = request.FILES.get('image')
        if image:
            image_path = uploaded_image(image)
            decoded_code = qr_decode(image_path)
            try:
                user_profile = UserProfile.objects.get(token=decoded_code)
                user = user_profile.user
                auth_login(request, user)
                return redirect('home') 
            except UserProfile.DoesNotExist:
                pass

    return render(request, 'qr.html')

def uploaded_image(image):
    img_path = os.path.join("static", "usr", image.name)
    with open(img_path, 'wb+') as i:
        for chunk in image.chunks():
            i.write(chunk)
    return img_path

@login_required
def home(request):
    return render(request, 'home.html')


from django.http import StreamingHttpResponse, HttpResponse
from django.template import loader
from django.views.decorators import gzip
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="cv2")

import cv2
import numpy as np
from pyzbar.pyzbar import decode

class VideoCamera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.qr_counts = {}
        self.detected_qr_codes = set()
        self.stopped = False  # Added the 'stopped' attribute

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

    def stop(self):
        self.stopped = True

    def get_frame(self):
        if not self.cap.isOpened() or self.stopped:
            return None

        ret, frame = self.cap.read()
        if not ret or frame is None or frame.size == 0:
            return None

        # Decode QR code and update counts
        decoded_frame = self.decode_qr_code(frame)

        return decoded_frame

    def decode_qr_code(self, frame):
        if frame is None or frame.size == 0:
            return frame

        # Convert the frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Use pyzbar to decode QR codes
        decoded_objects = decode(gray)

        # Loop through the decoded objects and print the data
        for obj in decoded_objects:
            qr_data = obj.data.decode('utf-8')

            # Check if the QR code has already been detected
            if qr_data not in self.detected_qr_codes:
                decoded_data = qr_data 

                # Draw a rectangle around the QR code
                points = obj.polygon
                if len(points) > 4:
                    hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                    points = hull
                num_of_points = len(points)
                for j in range(num_of_points):
                    cv2.line(frame, tuple(points[j]), tuple(points[(j+1) % num_of_points]), (0, 0, 255), 2)

                # Count occurrences of each QR code
                self.qr_counts[qr_data] = self.qr_counts.get(qr_data, 0) + 1

                # Add the QR code to the list of detected codes
                self.detected_qr_codes.add(qr_data)

        return frame

@gzip.gzip_page
def video_feed(request):
    return StreamingHttpResponse(gen(VideoCamera()), content_type='multipart/x-mixed-replace; boundary=frame')

def qr_code_decoder(request):
    template = loader.get_template('qr_code_decoder.html')
    return HttpResponse(template.render({}, request))

def gen(camera):
    while not camera.stopped:
        frame = camera.get_frame()
        if frame is not None:
            _, jpeg = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
        else:
            break  # Break the loop if camera is stopped or an error occurs
