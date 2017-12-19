# -*- coding: utf-8 -*-
# La ligne precedente est l� que pour les accents.
#!/usr/bin/python
##
## PhotoMaton V4.0 by Alain Gauche (V2 from Nicolas Cot)
##
## 15/12/2017 | V4.0 | Change resol to 4Mp, add black background for text, add photo number for user
## 06/05/2017 | V3.0 | Usb detection, Overlay color issue
## 28/05/2017 | V3.1 | Local dir removal (USB drive mandatory); Show photo number
## xx/xx/XXXX | VX.x | Save date and Photo number in sdcard; Add buttons +- to see last photos
##

#Import
import RPi.GPIO as GPIO
import datetime
import time
import os
import subprocess
import atexit
import threading
import psutil #Added for USB key detection
#import exifread
import sys #Added for sys.exit function call.
from PIL import Image
from picamera import PiCamera
from picamera import Color #Added for Black background
from time import sleep

#Configurations defines
# IO Pin define
SWITCH = 23
RESET = 25
PRINT_LED = 22
POSE_LED = 17
BUTTON_LED = 27
FLASH_L = 12
FLASH_R = 13
# Long press button setup
HOLDTIME = 5                        # Duration for button hold (shutdown)
TAPTIME = 0.01                      # Debounce time for button taps
USBCHECKTIME = 1                    # Periodic USB check
CAM_ANGLE = 0                       # camera angle in degre
TEXT_SIZE = 60                      # on screen text size
POSTVIEW_TIME = 4                   # time to display the new picture
SHUTTER_SPEED = 0                   # temps d'expo (0 = AUTO)
FLASH_POWER   = 50                  # puissance du Flash de 0% a 100%
AWB_VALUE = 'fluorescent'           # mode de la balance des blancs automatique
EXPOSURE_MODE = 'antishake'         # type d'exposition

DEFAULT_PI_PHOTO_DIR = '/media/USB_DISK' #'/home/pi/photobooth_images/Photos' #Default directory if no USB key is detected. Just to not break the program
PI_DIR_ERROR = 'ERROR'

# Resolutions are (Width,Height)
RESOLUTION_5MP      = (2592,1944)
#RESOLUTION_5MP     = (2560,1920)
RESOLUTION_4MP     = (2592,1520)
RESOLUTION_3MP     = (2048,1536)
RESOLUTION_1080PHD = (1920,1080)   # 16:9
RESOLUTION_2MP     = (1600,1200)
RESOLUTION_1_3MP   = (1280,1024)
RESOLUTION_960PHD  = (1280,960)
RESOLUTION_XGA     = (1024,768)
RESOLUTION_SVGA    = (800,600)
RESOLUTION_VGA     = (640,480)
RESOLUTION_CGA     = (320,200)


def detect_USB():
    x = PI_DIR_ERROR
    for path in psutil.disk_partitions():
        if path.mountpoint.count('/media/')>0:
           #print('la cle est detectee : {}' .format(path.mountpoint))
           x = '{}'.format(path.mountpoint)
           break
    return x

def count_photos(path):
    NbPhotos = 0
    # find existing pictures
    while os.path.isfile('%s/image_%s.jpg' %(directory,NbPhotos+1)):
        NbPhotos += 1
    #print('> %s pictures already in directory' %(NbPhotos))
    return NbPhotos

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(RESET, GPIO.IN)
GPIO.setup(POSE_LED, GPIO.OUT)
GPIO.setup(BUTTON_LED, GPIO.OUT)
GPIO.setup(PRINT_LED, GPIO.OUT)
GPIO.setup(FLASH_L, GPIO.OUT)
GPIO.setup(FLASH_R, GPIO.OUT)
  
#GPIO Inits
GPIO.output(POSE_LED, False)
GPIO.output(BUTTON_LED, False)
GPIO.output(PRINT_LED, False)
F1 = GPIO.PWM(FLASH_L, 200)
F2 = GPIO.PWM(FLASH_R, 200)
F1.start(0)
F2.start(0)


nbphoto = 0

print("> Python script started ...")
sleep(1)
# init file path
directory = detect_USB()
#print ("dir:"+directory)
if directory != PI_DIR_ERROR:
   print("> found USb drive folder: "+ directory)
   nbphoto = count_photos(directory)
   
@atexit.register


def cleanup():
  GPIO.output(BUTTON_LED, False)
  #GPIO.output(POSE_LED, False)
  GPIO.cleanup()

################ Flash swing function #######################################################################################

def flashSwing():
  F1.ChangeDutyCycle(0.1)
  F2.ChangeDutyCycle(0.1)
  time.sleep(1)
  for i in range(5):
    F1.ChangeDutyCycle(0.3)
    F2.ChangeDutyCycle(0)
    time.sleep(0.4)
    F1.ChangeDutyCycle(0)
    F2.ChangeDutyCycle(0.3)
    time.sleep(0.4)
  F1.ChangeDutyCycle(0)
  F2.ChangeDutyCycle(0)  

################ blink pose led function NOT USED ############################################################################

def blinkPoseLed():
  GPIO.output(POSE_LED, True)
  time.sleep(1.5)
  for i in range(5):
    GPIO.output(POSE_LED, False)
    time.sleep(0.4)
    GPIO.output(POSE_LED, True)
    time.sleep(0.4)
  for i in range(5):
    GPIO.output(POSE_LED, False)
    time.sleep(0.1)
    GPIO.output(POSE_LED, True)
    time.sleep(0.1)
  GPIO.output(POSE_LED, False)

################ start picture capture ######################################################################################
def snapPhoto():

    global nbphoto
    nbphoto += 1 
    print("snap started")
    camera.annotate_text = " Photo %s dans 5 sec. " %nbphoto
    time.sleep(1)
    camera.annotate_text = " Photo dans 4 sec. "
    time.sleep(1)
    camera.annotate_text = " Photo dans 3 sec. "
    time.sleep(1)
    camera.annotate_text = " Photo dans 2 sec. "
    time.sleep(1)
    camera.annotate_text = " Photo dans 1 sec. "
    time.sleep(1)
    camera.annotate_text = " Clic ! "

    F1.ChangeDutyCycle(FLASH_POWER)
    F2.ChangeDutyCycle(FLASH_POWER)
    camera.annotate_text = ""
    #camera.resolution = RESOLUTION_4MP
    camera.capture('%s/image_%s.jpg' %(directory, nbphoto), 'jpeg')
    #camera.resolution = (1280,800) 
    #camera.annotate_text = "Photo N° %s" %nbphoto

    F1.ChangeDutyCycle(0)
    F2.ChangeDutyCycle(0)

################ photo requested function  ##################################################################################
def tap():

  global nbphoto
  GPIO.output(BUTTON_LED, False)

#start threads    
  #blink = threading.Thread(target=blinkPoseLed)
  snap = threading.Thread(target=snapPhoto)
  fSwing = threading.Thread(target=flashSwing)
  #blink.start()
  snap.start()
  fSwing.start()
  #blink.join()
  snap.join()
  fSwing.join()

# Display the new photo
  img = Image.open('%s/image_%s.jpg' %(directory, nbphoto) )
  r, g, b = img.split()             # PATCH : Je ne sais pas pourquoi, la gestion de l'overlay inverse les couleurs.
  img=Image.merge('RGB', (b, g, r)) # PATCH : Je les remets donc dans le bon ordre avant de les afficher...
 
  # Create an image padded to the required size with
  # mode 'RGB'
  pad = Image.new('RGB', (
    ((img.size[0] + 31) // 32) * 32,
    ((img.size[1] + 15) // 16) * 16,
    ))
  # Paste the original image into the padded one
  pad.paste(img, (0, 0))
  # Add the overlay with the padded image as the source,
  # but the original image's dimensions
  photoOverlay = camera.add_overlay(pad.tostring(), size=img.size)
  # By default, the overlay is in layer 0, beneath the
  # preview (which defaults to layer 2). Here we make
  # the new overlay semi-transparent, then move it above
  # the preview
  photoOverlay.alpha = 255
  photoOverlay.layer = 3

  sleep(POSTVIEW_TIME)
  camera.remove_overlay(photoOverlay)

# reinit for the next round  
  #print("ready for next round")
  camera.annotate_text = " Pret pour la prise de vue %s " %(nbphoto+1)
  #camera.onnotate_text = " path %s ", %directory
  #GPIO.output(PRINT_LED, False)
  GPIO.output(BUTTON_LED, True)

####################### shutdown detected function ##########################################################################
def hold():
  print("long pressed button! Shutting down system")
  camera.annotate_text = "Deconnection de la cle USB..."
  subprocess.call("sudo umount %s" %(directory), shell=True)
  sleep(2)
  if GPIO.input(SWITCH)!=0: # Le bouton a ete relache... on peut tout arreter 
    camera.annotate_text = "Extinction ... Bye"
    sleep(5)
    camera.stop_preview()
    subprocess.call("sudo shutdown -hP now", shell=True)
  else:                      # Sinon, on redonne la main a l'utilisateur...
    camera.annotate_text = "Developper mode activated"
    sleep(5)
    camera.stop_preview()
  sys.exit()

################################ MAIN #######################################################################################

## initial states for detect long or normal pressed button
prevButtonState = GPIO.input(SWITCH)
prevTime        = time.time()
prevUsbTime     = time.time()
tapEnable       = False
holdEnable      = False

## wait for camera to be connected
camera = PiCamera()
camera.rotation = CAM_ANGLE
camera.annotate_text_size = TEXT_SIZE
camera.annotate_background = Color('black')
camera.shutter_speed  = SHUTTER_SPEED
camera.awb_mode = AWB_VALUE
camera.exposure_mode = EXPOSURE_MODE
#camera.hflip = True
camera.vflip = True
camera.resolution = RESOLUTION_4MP #(1280,800) # (1920, 1200)
#camera.framerate = 15
## Camera is now connected
print("> camera is now connected ...")
sleep(4)

#start on screen preview
print("> Start preview...")
camera.exif_tags['IFD0.Artist'] = 'RDOTeam'
camera.exif_tags['IFD0.Copyright'] = 'RDO Continental'
camera.start_preview(resolution=(1280,800))
if directory != PI_DIR_ERROR:
  camera.annotate_text = " Pret pour la prise de vue "
  GPIO.output(BUTTON_LED, True)
else:
  camera.annotate_text = " Pas de cle USB detectee "
  GPIO.output(BUTTON_LED, False)
# effect and B&W
#camera.image_effect='sketch'
#camera.image_effect = 'colorswap' #pour inverser les couleur pour trouver le probleme de l'overlay
#camera.image_effect_params = 1 # avec param = RGB ==> BRG
#camera.color_effects = (128,128)

#background
while True:

  buttonState = GPIO.input(SWITCH)
  t           = time.time()
    
  #ici, on verifie toutes les secondes que la cle est bien connectee.
  if (t - prevUsbTime) >= USBCHECKTIME:
    if directory == PI_DIR_ERROR: #Si c'etait en erreur, on regarde s'il y a reconnexion
      directory = detect_USB()
      if directory != PI_DIR_ERROR: #Cle detectee : On doit recompter le nombre de photos...
        camera.annotate_text = " Cle USB detectee ! "
        sleep(2)
        nbphoto = count_photos(directory)
        camera.annotate_text = " %s Photos detectees ! " % nbphoto
	sleep(2)
	camera.annotate_text = " Pret pour la prise de vue "
	GPIO.output(BUTTON_LED, True) #On peut rallumer le bouton
    else: #Si ce n'etait pas en erreur
      directory = detect_USB()
      if directory == PI_DIR_ERROR: # on regarde que la cle n'est pas ete enlevee.
        GPIO.output(BUTTON_LED, False) #On etteint le bouton
	camera.annotate_text = " Cle USB retiree ! "
        sleep(2)
	camera.annotate_text = " Pas de cle USB detectee "
    prevUsbTime = t
    
  if directory != PI_DIR_ERROR:
    # camera.annotate_text = "Bouton: %s" % buttonState
    # Has button state changed
    if buttonState != prevButtonState:
      prevButtonState = buttonState   # Yes, save new state/time
      prevTime        = t
    else:                             # Button state unchanged
      if (t - prevTime) >= HOLDTIME:  # Button held more than 'HOLDTIME'
        # Yes it has.  Is the hold action as-yet untriggered?
        if holdEnable == True:        # Yep!
          camera.annotate_text = "Hold detected"
          hold()                      # Perform hold action (usu. shutdown)
          holdEnable = False          # 1 shot...don't repeat hold action
          tapEnable  = False          # Don't do tap action on release
      elif (t - prevTime) >= TAPTIME: # Not HOLDTIME.  TAPTIME elapsed?
        # Yes.  Debounced press or release...
        if buttonState == True:      # Button released?
          if tapEnable == True:       # Ignore if prior hold()
            #camera.annotate_text = "Bouton relache"
            tap()                     # Tap triggered (button released)
            tapEnable  = False        # Disable tap and hold
            holdEnable = False
        else:                         # Button pressed
          tapEnable  = True           # Enable tap and hold actions
          holdEnable = True
  else: #Attente detection cle
    camera.annotate_text = " Pas de cle USB detectee "
      
  

