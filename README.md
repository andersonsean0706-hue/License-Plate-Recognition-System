# License-Plate-Recognition-System
Smart Parking Motorcycle License Plate Recognition and Automatic Payment System using OpenCV, EasyOCR, and Tkinter GUI.
# Smart Parking Motorcycle License Plate Recognition and Automatic Payment System

This project is a smart parking system for motorcycle license plate recognition and automatic payment query. The system uses OpenCV for image preprocessing and license plate region detection, EasyOCR for license plate text recognition, and Tkinter to build a graphical user interface.

The main application scenario of this project is a campus motorcycle parking lot. After the system recognizes a valid motorcycle license plate, users can enter their plate number in the GUI to check the parking duration, payment amount, and corresponding vehicle image.

## Project Features

* Motorcycle license plate image processing
* License plate region detection using OpenCV
* OCR text recognition using EasyOCR
* Taiwan new-style motorcycle license plate format filtering
* Simple parking duration and payment calculation
* Tkinter graphical user interface
* Vehicle image display after successful query

## System Workflow

The system workflow is as follows:

1. Read motorcycle images from the folder.
2. Convert the image to grayscale.
3. Apply Gaussian blur to reduce noise.
4. Use Canny edge detection to extract edges.
5. Detect contours and find possible license plate regions.
6. Crop the possible license plate region.
7. Use EasyOCR to recognize the license plate text.
8. Filter OCR results using the Taiwan motorcycle license plate format.
9. Store valid plate data in a simple parking database.
10. Use the GUI to query parking duration, payment amount, and vehicle image.

## License Plate Format Rule

This project focuses on Taiwan new-style motorcycle license plates.
To reduce false recognition, the system only accepts plate numbers that match the following rule:

```text
N / M / P + two English letters + four digits
```

Examples of valid plate numbers:

```text
NVK0306
NDM3960
PFW7708
```

OCR results that do not start with `N`, `M`, or `P` are rejected, even if they contain three letters and four digits.

## Parking Fee Rule

The parking fee is calculated using the following rule:

```text
First 30 minutes: Free
After 30 minutes: 10 NT dollars per hour
Less than one full hour is counted as one hour
```

Example:

```text
Parking duration: 595 minutes
Payment amount: 100 NT dollars
```

## GUI Function

The GUI is built using Tkinter. Users can enter their motorcycle license plate number into the input field and click the query button. If the plate number exists in the parking database, the system will display:

* License plate number
* Parking duration
* Payment amount
* Corresponding vehicle image

If the plate number is not found, the system will show an error message asking the user to check the input again.

## YOLO Testing

YOLO was also tested in this project as a possible license plate detection method. The purpose was to use a trained object detection model to detect the license plate region directly.

However, during testing, some YOLO detection boxes included extra background areas such as screws, stickers, motorcycle body parts, or background text. In some cases, the detection box was too large or too small, which affected the EasyOCR recognition result.

After comparison, the final system uses OpenCV-based image processing and EasyOCR as the main workflow because it is easier to control for the current dataset and project scope.

## Technologies Used

* Python
* OpenCV
* EasyOCR
* Tkinter
* Pillow
* NumPy
* Regular Expression
* PyTorch
* YOLO testing

## How to Run

1. Install the required Python packages.

```bash
pip install opencv-python easyocr pillow numpy
```

2. Put the motorcycle images in the same folder as the Python file.

3. Run the program.

```bash
python "License Plate Recognition System (V.最終版).py"
```

4. After recognition is completed, the GUI will open.

5. Enter a recognized license plate number to query the parking fee.

## Example Result

The system can recognize a motorcycle license plate such as:

```text
NVK0306
```

After entering the plate number in the GUI, the system displays the parking duration, payment amount, and opens the corresponding vehicle image with the detected license plate region.

## Reflection

Through this project, I learned how to apply computer vision and image processing techniques to a practical smart parking application. I practiced grayscale conversion, Gaussian blur, Canny edge detection, contour detection, image cropping, OCR recognition, and GUI design. I also learned that OCR recognition needs format filtering to reduce incorrect results. This project helped me understand the importance of debugging, system integration, and practical application design.

## References

[1] PyTorch Installation and Usage Tutorial, YouTube.
https://www.youtube.com/watch?v=1s1Jq0iVPX

[2] LonelyCaesar, “OpenCV License Plate Recognition,” GitHub.
https://github.com/LonelyCaesar/OpenCV-license-plate-recognition

[3] YOLO Car License Plate Training Tutorial.
https://mahaljsp.ddns.net/yolo_car/

[4] Vehicle Registration Plates of Taiwan, Wikipedia.
https://zh.wikipedia.org/zh-tw/臺灣車輛牌照

[5] OpenCV Documentation.
https://docs.opencv.org/

[6] EasyOCR GitHub Repository.
https://github.com/JaidedAI/EasyOCR

[7] Ultralytics YOLO Documentation.
https://docs.ultralytics.com/

[8] PyTorch Documentation.
https://pytorch.org/
