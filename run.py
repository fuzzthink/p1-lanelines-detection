import matplotlib.image as mpimg
import cv2, sys, os, time
from math import sqrt
from pipeline import process_image
from moviepy.editor import VideoFileClip


video_in = None
video_out = 'video-out.mp4'
menu = 'python run.py [in.mp4 [out.mp4]]  ## no arguments to run preprocessors on test images' 

if len(sys.argv) > 1:
    arg = sys.argv[1]
    if arg.endswith('help') or arg=='-h' or arg.startswith('--h'):
        print(menu)
        exit()
    video_in = arg
    if len(sys.argv) > 2:
        video_out = sys.argv[2]

if video_in:
    t = time.time()
    clip = VideoFileClip(video_in)

    clipped = clip.fl_image(process_image)
    clipped.write_videofile(video_out, audio=False)
    t2 = time.time()

    m, s = divmod(t2 - t, 60)
    print("%d:%02d to process video" % (m, s))
    if len(sys.argv) <= 1:
        print("You can run other files via> "+menu)

else:
    ## run process_image on test images
    imgs_path = 'test_images/'
    out_path = 'output_images/'
    dbg = False #True

    for imgname in os.listdir(imgs_path):
        name, ext = imgname.split('.')
        outimg, canny = process_image(mpimg.imread(imgs_path+imgname), True, dbg)
        cv2.imwrite(out_path+name+'-canny.jpg', canny)
        cv2.imwrite(out_path+imgname, cv2.cvtColor(outimg, cv2.COLOR_RGB2BGR))
