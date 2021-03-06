import numpy as np
import cv2

def overlay(img1, img2):

	# I want to put logo on top-left corner, So I create a ROI
	rows,cols,channels = img2.shape
	roi = img1[0:rows, 0:cols ]

	# Now create a mask of logo and create its inverse mask also
	img2gray = cv2.cvtColor(img2,cv2.COLOR_BGR2GRAY)
	ret, mask = cv2.threshold(img2gray, 10, 255, cv2.THRESH_BINARY)
	mask_inv = cv2.bitwise_not(mask)

	# Now black-out the area of logo in ROI
	img1_bg = cv2.bitwise_and(roi,roi,mask = mask_inv)

	# Take only region of logo from logo image.
	img2_fg = cv2.bitwise_and(img2,img2,mask = mask)

	# Put logo in ROI and modify the main image
	dst = cv2.add(img1_bg,img2_fg)
	img1[0:rows, 0:cols ] = dst

	return dst

cap = cv2.VideoCapture('serenity.mp4')
overlay_image = cv2.imread('2.png')

while(cap.isOpened()):
	
	ret, frame = cap.read()

	frame = overlay(frame,overlay_image)

	cv2.imshow('frame',frame)
	if cv2.waitKey(1) & 0xFF == ord('q'):
		break

cap.release()
cv2.destroyAllWindows()
