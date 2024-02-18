from cam import *
from model import *
from LED import *
from ultrasonic import *
import time


#over here, it is necessary to initialize the main operating loop
#control is done as following:
# 1. Check ultrasonic sensor for the distance measurement. (a) = distance > 3cm; (b) distance <=3cm
# 2 b. Notify compartment fullness using the notification LED
# 2 a. Check camera for image
# 3 a. Bring in the image into the script. At this point, the image frame is always saved in the local directory as image.jpg
# 4 a. Send this image to learn for classification. Predict returns the classification, with which we will light up the correct LED
# 5 a. delay for some time.
# 6 a. Repeat the process
if __name__ == '__main__':
	delay = 2
	learn = load_model()  #load the model in the learn variable
	cam_capture = camInit()  #load capture into the code
	filename = "image.jpg"  #constant filename for saving image to be classified
	fullness_init()
	LED_init()
	print("I am here")
	try:
		print("I am here A")
		while(True):
			print("I am here B")
#			fullness_init()
#			LED_init()
			compartment1 = fullness_measure_recycle()
			compartment2 = fullness_measure_organic()
			print("I am here C")
			print(compartment1)
			print(compartment2)
			if(compartment1 or compartment2):
				if(compartment1 and compartment2):
					GPIO.output(fullness_LED_organic, 1) #switch on fullness LED_organic
					GPIO.output(fullness_LED_re, 1) #switch on fullness LED_re
				if(compartment1 and not compartment2):
					GPIO.output(fullness_LED_organic, 1) #switch on fullness LED_organic
					GPIO.output(fullness_LED_re, 0) #switch off fullness LED_re
				if(compartment2 and not compartment1):
					GPIO.output(fullness_LED_re, 1) #switch on fullness LED_re
					GPIO.output(fullness_LED_organic, 0) #swtich off fullness LED_organic
				time.sleep(delay)
				continue
			GPIO.output(fullness_LED_organic, 0)#switch off fullness LED_organic
			GPIO.output(fullness_LED_re, 0)#switch off fullness LED_re
			#take picture
			clickPicture(cam_capture, filename)
			prediction = predict(learn, filename) #make prediction
			if(prediction == "organic"):
				GPIO.output(classify_LED_organic, 1) #switch on LED_organic
				GPIO.output(classify_LED_re, 0) #switch off LED_re
			elif(prediction == "recyclable"):
				GPIO.output(classify_LED_re, 1) #switch on LED_re
				GPIO.output(classify_LED_organic, 0) #switch off LED_organic
			else:
				#switch on LED_organic and LED_re
				GPIO.output(classify_LED_organic, 1)
				GPIO.output(classify_LED_re, 1)

			#sleep for some time - 10secs
			time.sleep(delay)

	except KeyboardInterrupt:
			print("Measurement stopped by User")
			GPIO.cleanup()
			exitCam(cam_capture)