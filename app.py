import cv2
import numpy as np

from flask import Flask, Response, render_template

app = Flask(__name__)

# This function calculates the average of detected circles.
def avg_circles(circles, b):
    avg_x = 0
    avg_y = 0
    avg_r = 0
    for i in range(b):
        avg_x += circles[0][i][0]
        avg_y += circles[0][i][1]
        avg_r += circles[0][i][2]
    avg_x = int(avg_x / b)
    avg_y = int(avg_y / b)
    avg_r = int(avg_r / b)
    return avg_x, avg_y, avg_r

# This function calculates the Euclidean distance between two points.
def dist_2_pts(x1, y1, x2, y2):
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

# This function calibrates the circle to draw lines and text labels around it.
def calibrate_circle(frame, center, radius, separation=10):
    p1 = []
    p2 = []
    for i in range(0, 360, separation):
        angle_rad = np.deg2rad(i)
        p1.append((int(center[0] + 0.9 * radius * np.cos(angle_rad)), int(center[1] + 0.9 * radius * np.sin(angle_rad))))
        p2.append((int(center[0] + radius * np.cos(angle_rad)), int(center[1] + radius * np.sin(angle_rad))))
    for i in range(len(p1)):
        cv2.line(frame, p1[i], p2[i], (0, 255, 0), 2)
        cv2.putText(frame, str(i*separation), p2[i], cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1, cv2.LINE_AA)

# This function captures the frame from the camera, processes it to find circles and lines, and then calculates the measurements.
def take_measure(threshold_img, threshold_ln, minLineLength, maxLineGap, diff1LowerBound, diff1UpperBound, diff2LowerBound, diff2UpperBound, min_angle, max_angle, min_value, max_value, units):
    cap = cv2.VideoCapture(0)  # 0 for the default camera, you can change the index if you have multiple cameras

    while True:
        ret, frame = cap.read()  # Capture frame-by-frame
        if not ret:
            print("Error: Failed to capture frame")
            break

        img = frame.copy()
        img2 = frame.copy()

        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20)

        if circles is not None:
            a, b, c = circles.shape
            x, y, r = avg_circles(circles, b)

            # Draw center and circle
            cv2.circle(img, (x, y), r, (0, 255, 0), 3, cv2.LINE_AA)  # draw circle
            cv2.circle(img, (x, y), 2, (0, 255, 0), 3, cv2.LINE_AA)  # draw center of circle

            # Calibrate circle
            calibrate_circle(img, (x, y), r)

            separation = 10.0  # in degrees
            interval = int(360 / separation)
            p1 = np.zeros((interval, 2))  # set empty arrays
            p2 = np.zeros((interval, 2))
            p_text = np.zeros((interval, 2))
            for i in range(0, interval):
                for j in range(0, 2):
                    if (j % 2 == 0):
                        p1[i][j] = x + 0.9 * r * np.cos(separation * i * 3.14 / 180)  # point for lines
                    else:
                        p1[i][j] = y + 0.9 * r * np.sin(separation * i * 3.14 / 180)
            text_offset_x = 10
            text_offset_y = 5
            for i in range(0, interval):
                for j in range(0, 2):
                    if (j % 2 == 0):
                        p2[i][j] = x + r * np.cos(separation * i * 3.14 / 180)
                        p_text[i][j] = x - text_offset_x + 1.2 * r * np.cos(
                            (separation) * (i + 9) * 3.14 / 180)  # point for text labels, i+9 rotates the labels by 90 degrees
                    else:
                        p2[i][j] = y + r * np.sin(separation * i * 3.14 / 180)
                        p_text[i][j] = y + text_offset_y + 1.2 * r * np.sin(
                            (separation) * (i + 9) * 3.14 / 180)  # point for text labels, i+9 rotates the labels by 90 degrees

            # Lines and labels
            for i in range(0, interval):
                cv2.line(img, (int(p1[i][0]), int(p1[i][1])), (int(p2[i][0]), int(p2[i][1])), (0, 255, 0), 2)
                cv2.putText(img, '%s' % (int(i * separation)), (int(p_text[i][0]), int(p_text[i][1])),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1, cv2.LINE_AA)

            cv2.putText(img, "Gauge OK!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2, cv2.LINE_AA)

            gray3 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            maxValue = 255

            # Threshold image to take better measurements
            th, dst2 = cv2.threshold(gray3, threshold_img, maxValue, cv2.THRESH_BINARY_INV)

            in_loop = 0
            lines = cv2.HoughLinesP(image=dst2, rho=3, theta=np.pi / 180, threshold=threshold_ln,
                                     minLineLength=minLineLength, maxLineGap=maxLineGap)
            final_line_list = []

            for i in range(0, len(lines)):
                for x1, y1, x2, y2 in lines[i]:
                    diff1 = dist_2_pts(x, y, x1, y1)  # x, y is center of circle
                    diff2 = dist_2_pts(x, y, x2, y2)  # x, y is center of circle

                    if (diff1 > diff2):
                        temp = diff1
                        diff1 = diff2
                        diff2 = temp

                    # Check if line is in range of circle
                    if (((diff1 < diff1UpperBound * r) and (diff1 > diff1LowerBound * r) and (
                            diff2 < diff2UpperBound * r)) and (diff2 > diff2LowerBound * r)):
                        line_length = dist_2_pts(x1, y1, x2, y2)
                        final_line_list.append([x1, y1, x2, y2])
                        in_loop = 1

            if (in_loop == 1):
                x1 = final_line_list[0][0]
                y1 = final_line_list[0][1]
                x2 = final_line_list[0][2]
                y2 = final_line_list[0][3]
                cv2.line(img2, (x1, y1), (x2, y2), (0, 255, 255), 2)
                dist_pt_0 = dist_2_pts(x, y, x1, y1)
                dist_pt_1 = dist_2_pts(x, y, x2, y2)
                if (dist_pt_0 > dist_pt_1):
                    x_angle = x1 - x
                    y_angle = y - y1
                else:
                    x_angle = x2 - x
                    y_angle = y - y2

                # Finding angle using the arc tan of y/x
                res = np.arctan(np.divide(float(y_angle), float(x_angle)))

                # Converting to degrees
                res = np.rad2deg(res)
                if x_angle > 0 and y_angle > 0:  # in quadrant I
                    final_angle = 270 - res
                if x_angle < 0 and y_angle > 0:  # in quadrant II
                    final_angle = 90 - res
                if x_angle < 0 and y_angle < 0:  # in quadrant III
                    final_angle = 90 - res
                if x_angle > 0 and y_angle < 0:  # in quadrant IV
                    final_angle = 270 - res

				#print final_angle

                old_min = float(min_angle)
                old_max = float(max_angle)

                new_min = float(min_value)
                new_max = float(max_value)

                old_value = final_angle
                old_range = (old_max - old_min)
                new_range = (new_max - new_min)
				
                new_value = (((old_value - old_min) * new_range) / old_range) + new_min
				
                val = new_value

                cv2.putText(img2, "Indicator OK!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2, cv2.LINE_AA)
                
				#////////////////////////////////////////////////////////////////////////////////////// 
                print ("Current reading: %s %s" %(("%.2f" % val), units))
            else:
                cv2.putText(img2, "Can't find the indicator!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2, cv2.LINE_AA)

            # Encode the modified frame
            (flag, encodedImage) = cv2.imencode(".jpg", frame)
            if not flag:
                continue
            
            # Yield the frame to the browser
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

        else:
            cv2.putText(img, "Can't see the gauge!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.imshow('test', img)
        cv2.imshow('test2', img2)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Parameters
threshold_img = 120
threshold_ln = 200
minLineLength = 40
maxLineGap = 8

# Distance from center coefficients
diff1LowerBound = 0.15
diff1UpperBound = 0.25

# Distance from circle coefficients
diff2LowerBound = 0.5
diff2UpperBound = 1.0

# Parameters specific to the gauge
min_angle = 60
max_angle = 300
min_value = 0
max_value = 160
units = "miles"


# These are Flask routes for the web application. The '/' route renders the HTML template, 
# and the '/video_feed' route returns the video feed generated by the take_measure function. 
# Finally, it starts the Flask application if the script is run directly.

@app.route('/')
def index():
    reading = take_measure(threshold_img, threshold_ln, minLineLength, maxLineGap,
                           diff1LowerBound, diff1UpperBound, diff2LowerBound, diff2UpperBound,
                           min_angle, max_angle, min_value, max_value, units)
    return render_template('index.html', reading=reading)

@app.route('/video_feed')
def video_feed():
    return Response(take_measure(threshold_img, threshold_ln, minLineLength, maxLineGap, 
                                 diff1LowerBound, diff1UpperBound, diff2LowerBound, diff2UpperBound, 
                                 min_angle, max_angle, min_value, max_value, units), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)


